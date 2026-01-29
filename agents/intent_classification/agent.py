"""
Intent Classification Agent
Routes incoming customer requests to appropriate handlers based on intent analysis

Phase 1-3: Mock classification logic with keyword matching
Phase 4+: Azure OpenAI GPT-4o-mini for real intent classification
Phase 6+: Session-aware routing with tiered access control

Session Integration (Phase 6):
- Receives session context with each message
- Routes based on auth level (Anonymous/Identified/Authenticated)
- Extracts customer info for personalized classification
- Upgrades sessions to Identified when email/phone detected

Refactored to use BaseAgent pattern for reduced code duplication.
"""

import re
from typing import Tuple, Dict, Any, List, Optional

from shared.base_agent import BaseAgent, run_agent
from shared.models import (
    CustomerMessage,
    IntentClassificationResult,
    Intent,
    Language,
    create_a2a_message,
    extract_message_content,
    generate_message_id,
    generate_context_id,
)

# Session integration (Phase 6)
try:
    from shared.auth.models import AuthLevel, CustomerSession
    from shared.auth.session_manager import get_session_manager

    SESSION_SUPPORT = True
except ImportError:
    SESSION_SUPPORT = False
    AuthLevel = None
    CustomerSession = None

# Production intent classification prompt from Phase 3.5 optimization
# Achieved 98% accuracy in evaluation (target was >85%)
INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a customer service platform.

TASK:
Classify the customer message into exactly ONE of these 17 intents:

- ORDER_STATUS: Questions about order location, delivery status, arrival time
- RETURN_REQUEST: Customer wants to return an item for refund (NOT exchange)
- REFUND_STATUS: Questions about refund processing, timing (asking about existing refund)
- PRODUCT_INQUIRY: Questions about product details, availability, features
- SHIPPING_ESTIMATE: Questions about shipping times, costs, options, availability to locations
- TRACKING_UPDATE: Requests for tracking information or updates
- COMPLAINT: Strong dissatisfaction where venting is PRIMARY purpose, no clear resolution request
- BILLING_ISSUE: Payment problems, incorrect charges, billing questions
- ACCOUNT_HELP: Account access, settings, profile updates
- SUBSCRIPTION_MANAGEMENT: Subscription changes, cancellation, upgrades
- TECHNICAL_SUPPORT: Website/app issues, technical problems
- FEEDBACK: Positive or constructive feedback (not angry complaints)
- GENERAL_INQUIRY: General questions about company, policies, store hours
- CANCELLATION: Request to cancel an order before shipping
- EXCHANGE: Return item AND get different item/size/color (swap, not just return)
- LOYALTY_PROGRAM: Questions about rewards, points, member benefits
- ESCALATION_REQUEST: Request to speak with human/manager, OR repeated contact frustration

DECISION RULES:

1. EXCHANGE vs RETURN_REQUEST:
   - EXCHANGE: Customer explicitly wants a DIFFERENT item ("get something else", "different size/color", "swap")
   - RETURN_REQUEST: Customer just wants to return/send back (may or may not mention refund)
   - Key signal: "get something else" or "exchange for" = EXCHANGE

2. COMPLAINT vs actionable intents:
   - COMPLAINT: Extreme anger/frustration is the DOMINANT emotion, profanity or insults present
   - Even if they mention refund, if the message is primarily venting rage = COMPLAINT
   - Example: "garbage", "terrible", "worst ever", "ridiculous" with intense emotion = COMPLAINT

3. ESCALATION_REQUEST (explicit OR implied):
   - Explicit: "speak to manager", "talk to human", "supervisor"
   - Implied: "this is the Nth time", "I've contacted you multiple times", repeated contact frustration
   - Key signal: Frustration about REPEATED unsuccessful contacts = ESCALATION_REQUEST

4. SHIPPING_ESTIMATE includes:
   - "Do you ship to [location]?" (availability)
   - "How long/much for shipping?"

5. Choose the MOST SPECIFIC intent that captures what the customer NEEDS

EXAMPLES:

"I ordered the wrong thing, can I send it back and get something else?"
-> EXCHANGE (wants different item)

"I want to return this sweater"
-> RETURN_REQUEST (just returning, no exchange mentioned)

"Your product is absolute garbage and I want a full refund"
-> COMPLAINT (rage/insult is dominant, "garbage" signals venting)

"This is the third time I've contacted you about this issue"
-> ESCALATION_REQUEST (repeated contact frustration = implied escalation)

"I'd like a refund please"
-> RETURN_REQUEST (polite refund request, no anger)

"Do you ship to Canada?"
-> SHIPPING_ESTIMATE (shipping availability)

"I received the wrong item in my package"
-> RETURN_REQUEST (wrong item needs resolution)

OUTPUT FORMAT:
Respond with ONLY a JSON object:
{"intent": "INTENT_NAME", "confidence": 0.0-1.0}

No other text."""


# Mapping from OpenAI intents to internal Intent enum
INTENT_MAPPING = {
    "ORDER_STATUS": Intent.ORDER_STATUS,
    "RETURN_REQUEST": Intent.RETURN_REQUEST,
    "REFUND_STATUS": Intent.REFUND_STATUS,
    "PRODUCT_INQUIRY": Intent.PRODUCT_INFO,
    "SHIPPING_ESTIMATE": Intent.SHIPPING_QUESTION,
    "TRACKING_UPDATE": Intent.ORDER_STATUS,  # Map to order status for routing
    "COMPLAINT": Intent.ESCALATION_NEEDED,  # Complaints need escalation
    "BILLING_ISSUE": Intent.ESCALATION_NEEDED,  # Billing issues need escalation
    "ACCOUNT_HELP": Intent.GENERAL_INQUIRY,
    "SUBSCRIPTION_MANAGEMENT": Intent.AUTO_DELIVERY_MANAGEMENT,
    "TECHNICAL_SUPPORT": Intent.BREWER_SUPPORT,
    "FEEDBACK": Intent.GENERAL_INQUIRY,
    "GENERAL_INQUIRY": Intent.GENERAL_INQUIRY,
    "CANCELLATION": Intent.ORDER_MODIFICATION,
    "EXCHANGE": Intent.RETURN_REQUEST,  # Exchange handled through returns flow
    "LOYALTY_PROGRAM": Intent.LOYALTY_PROGRAM,
    "ESCALATION_REQUEST": Intent.ESCALATION_NEEDED,
}


class IntentClassificationAgent(BaseAgent):
    """
    Intent Classification Agent - Routes customer messages to appropriate handlers.

    Uses AGNTCY SDK A2A protocol over SLIM transport for agent-to-agent communication.
    Phase 4+: Uses Azure OpenAI GPT-4o-mini for intent classification.
    Phase 6+: Session-aware routing with tiered access control.

    Session Integration:
    - Receives session_id in message metadata
    - Retrieves session for auth level context
    - Adjusts routing based on permissions
    - Extracts email/phone to upgrade anonymous sessions
    """

    agent_name = "intent-classification-agent"
    default_topic = "intent-classifier"

    def __init__(self):
        """Initialize the Intent Classification Agent."""
        super().__init__()
        # Additional counters for classification tracking
        self.openai_classifications = 0
        self.mock_classifications = 0
        # Session manager (Phase 6)
        self._session_manager = None

    async def process_message(self, content: dict, message: dict) -> dict:
        """
        Process customer message and classify intent.

        Phase 6 Enhancement: Session-aware processing
        - Retrieves session context for auth level
        - Extracts email/phone to upgrade anonymous sessions
        - Includes session info in classification result

        Args:
            content: Extracted message content
            message: Full A2A message

        Returns:
            IntentClassificationResult as dict with session context
        """
        # Parse as CustomerMessage
        customer_msg = CustomerMessage(
            message_id=content.get("message_id", generate_message_id()),
            customer_id=content.get("customer_id", "unknown"),
            content=content.get("content", ""),
            channel=content.get("channel", "chat"),
            context_id=message.get("contextId", generate_context_id()),
            language=Language(content.get("language", "en")),
            metadata=content.get("metadata", {}),
        )

        self.logger.info(
            f"Processing message {customer_msg.message_id} from customer {customer_msg.customer_id}"
        )

        # Phase 6: Get session context if available
        session = await self._get_session_context(content, message)
        auth_level = self._get_auth_level(session)

        # Classify intent using Azure OpenAI or mock
        if self.openai_client:
            intent, confidence, entities = await self._classify_intent_openai(
                customer_msg.content
            )
            self.openai_classifications += 1
        else:
            intent, confidence, entities = self._classify_intent_mock(
                customer_msg.content
            )
            self.mock_classifications += 1

        # Phase 6: Check if extracted email/phone should upgrade session
        await self._maybe_upgrade_session(session, entities)

        # Phase 6: Adjust routing based on auth level and intent permissions
        routing = self._determine_routing(intent, auth_level, session)

        # Create classification result
        result = IntentClassificationResult(
            message_id=customer_msg.message_id,
            context_id=customer_msg.context_id,
            intent=intent,
            confidence=confidence,
            extracted_entities=entities,
            language=customer_msg.language,
            routing_suggestion=routing,
        )

        # Phase 6: Add session context to result
        if session:
            result.extracted_entities["session_id"] = session.session_id
            result.extracted_entities["auth_level"] = auth_level
            if session.customer:
                result.extracted_entities["customer_name"] = session.customer.full_name
                result.extracted_entities["is_vip"] = session.customer.is_vip

        self.logger.info(
            f"Classified intent: {intent.value} (confidence: {confidence:.2f}, "
            f"auth={auth_level}) -> route to: {result.routing_suggestion}"
        )

        return result

    async def _get_session_context(
        self, content: dict, message: dict
    ) -> Optional["CustomerSession"]:
        """
        Retrieve session context from session manager.

        Args:
            content: Message content (may contain session_id)
            message: Full message (may contain session_id in metadata)

        Returns:
            CustomerSession if found, None otherwise
        """
        if not SESSION_SUPPORT:
            return None

        # Look for session_id in multiple places
        session_id = (
            content.get("session_id")
            or content.get("metadata", {}).get("session_id")
            or message.get("metadata", {}).get("session_id")
        )

        if not session_id:
            return None

        try:
            # Get or initialize session manager
            if self._session_manager is None:
                try:
                    self._session_manager = get_session_manager()
                except RuntimeError:
                    # Session manager not initialized
                    self.logger.debug("Session manager not available")
                    return None

            session = await self._session_manager.get_session(session_id)
            if session:
                self.logger.debug(
                    f"Session context: {session_id} (auth={session.auth_level.value})"
                )
            return session

        except Exception as e:
            self.logger.warning(f"Failed to get session context: {e}")
            return None

    def _get_auth_level(self, session: Optional["CustomerSession"]) -> str:
        """Get auth level string from session or default to anonymous."""
        if session and SESSION_SUPPORT:
            return session.auth_level.value
        return "anonymous"

    async def _maybe_upgrade_session(
        self, session: Optional["CustomerSession"], entities: Dict[str, Any]
    ) -> None:
        """
        Upgrade session to IDENTIFIED if email/phone extracted.

        This enables order lookup without requiring full authentication.
        """
        if not session or not SESSION_SUPPORT or not self._session_manager:
            return

        # Only upgrade if currently anonymous
        if session.auth_level != AuthLevel.ANONYMOUS:
            return

        email = entities.get("email")
        phone = entities.get("phone")

        if email or phone:
            try:
                await self._session_manager.upgrade_to_identified(
                    session.session_id,
                    email=email,
                    phone=phone,
                )
                self.logger.info(
                    f"Upgraded session {session.session_id} to IDENTIFIED "
                    f"(email={bool(email)}, phone={bool(phone)})"
                )
            except Exception as e:
                self.logger.warning(f"Failed to upgrade session: {e}")

    def get_demo_messages(self) -> List[dict]:
        """Return sample messages for demo mode."""
        return [
            {
                "contextId": "demo-ctx-001",
                "taskId": "demo-task-001",
                "parts": [
                    {
                        "type": "text",
                        "content": {
                            "message_id": "msg-001",
                            "customer_id": "cust-123",
                            "content": "Where is my order #12345?",
                            "channel": "chat",
                        },
                    }
                ],
            },
            {
                "contextId": "demo-ctx-002",
                "taskId": "demo-task-002",
                "parts": [
                    {
                        "type": "text",
                        "content": {
                            "message_id": "msg-002",
                            "customer_id": "cust-456",
                            "content": "I want to return the blue sweater I ordered",
                            "channel": "email",
                        },
                    }
                ],
            },
            {
                "contextId": "demo-ctx-003",
                "taskId": "demo-task-003",
                "parts": [
                    {
                        "type": "text",
                        "content": {
                            "message_id": "msg-003",
                            "customer_id": "cust-789",
                            "content": "This is the third time I've contacted you about this issue!",
                            "channel": "chat",
                        },
                    }
                ],
            },
            {
                "contextId": "demo-ctx-004",
                "taskId": "demo-task-004",
                "parts": [
                    {
                        "type": "text",
                        "content": {
                            "message_id": "msg-004",
                            "customer_id": "cust-101",
                            "content": "Do you ship to Canada?",
                            "channel": "chat",
                        },
                    }
                ],
            },
        ]

    def cleanup(self) -> None:
        """Cleanup with additional classification stats."""
        self.logger.info(
            f"Classification stats - OpenAI: {self.openai_classifications}, "
            f"Mock: {self.mock_classifications}"
        )
        super().cleanup()

    async def _classify_intent_openai(
        self, message_text: str
    ) -> Tuple[Intent, float, Dict[str, Any]]:
        """
        Classify intent using Azure OpenAI GPT-4o-mini.

        Args:
            message_text: Customer message content

        Returns:
            Tuple of (intent, confidence, extracted_entities)
        """
        try:
            result = await self.openai_client.classify_intent(
                message=message_text,
                system_prompt=INTENT_CLASSIFICATION_PROMPT,
                temperature=0.0,
            )

            # Extract intent from response
            intent_str = result.get("intent", "GENERAL_INQUIRY")
            confidence = result.get("confidence", 0.5)

            # Map to internal Intent enum
            intent = INTENT_MAPPING.get(intent_str, Intent.GENERAL_INQUIRY)

            # Extract entities (basic extraction for now)
            entities = self._extract_entities(message_text)
            entities["raw_intent"] = intent_str  # Store original classification

            self.logger.debug(
                f"OpenAI classification: {intent_str} -> {intent.value} ({confidence:.2f})"
            )

            return intent, confidence, entities

        except Exception as e:
            self.logger.error(f"OpenAI classification error: {e}")
            # Fall back to mock classification
            return self._classify_intent_mock(message_text)

    def _extract_entities(self, message_text: str) -> Dict[str, Any]:
        """Extract entities from message text."""
        entities = {}

        # Extract order number - support formats: ORD-10234, #10234, 10234
        order_match = re.search(r"(?:ORD-|#)?(\d{4,6})", message_text, re.IGNORECASE)
        if order_match:
            entities["order_number"] = order_match.group(1)

        # Extract email address
        email_match = re.search(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", message_text
        )
        if email_match:
            entities["email"] = email_match.group()

        # Extract phone number (basic US format)
        phone_match = re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", message_text)
        if phone_match:
            entities["phone"] = phone_match.group()

        return entities

    def _classify_intent_mock(
        self, message_text: str
    ) -> Tuple[Intent, float, Dict[str, Any]]:
        """
        Mock intent classification using simple keyword matching.

        Used as fallback when Azure OpenAI is not available.

        Args:
            message_text: Customer message content

        Returns:
            Tuple of (intent, confidence, extracted_entities)
        """
        message_lower = message_text.lower()
        entities = {}

        # Priority 1: Escalation triggers (health & safety)
        if any(
            word in message_lower
            for word in [
                "allerg",
                "rash",
                "medical",
                "sick",
                "poison",
                "reaction",
                "emergency",
            ]
        ):
            self.logger.warning(
                f"CRITICAL: Health/safety escalation detected in message"
            )
            return (
                Intent.ESCALATION_NEEDED,
                0.95,
                {"escalation_reason": "health_safety"},
            )

        # Priority 2: Frustration detection
        frustration_words = [
            "frustrated",
            "angry",
            "upset",
            "annoyed",
            "ridiculous",
            "terrible",
            "awful",
            "hate",
        ]
        if any(word in message_lower for word in frustration_words):
            entities["escalation_reason"] = "customer_frustration"
            return Intent.ESCALATION_NEEDED, 0.85, entities

        # Return/refund requests
        if any(
            word in message_lower
            for word in ["return", "refund", "send back", "money back", "exchange"]
        ):
            order_match = re.search(
                r"(?:ORD-|#)?(\d{4,6})", message_text, re.IGNORECASE
            )
            if order_match:
                entities["order_number"] = order_match.group(1)
            return Intent.RETURN_REQUEST, 0.85, entities

        # Order status queries
        if any(
            word in message_lower
            for word in [
                "where is my order",
                "where's my order",
                "track",
                "tracking",
                "shipment",
                "delivery",
                "shipped",
                "arrive",
                "status of order",
                "status of my order",
                "order status",
                "been delivered",
                "has my order",
            ]
        ):
            order_match = re.search(
                r"(?:ORD-|#)?(\d{4,6})", message_text, re.IGNORECASE
            )
            if order_match:
                entities["order_number"] = order_match.group(1)
            return Intent.ORDER_STATUS, 0.90, entities

        # Subscription management
        if any(
            word in message_lower
            for word in [
                "subscription",
                "auto-delivery",
                "auto delivery",
                "pause",
                "skip",
                "cancel subscription",
                "change frequency",
                "add to next order",
                "change my subscription",
                "modify subscription",
            ]
        ):
            return Intent.AUTO_DELIVERY_MANAGEMENT, 0.85, entities

        # Product information
        if any(
            word in message_lower
            for word in [
                "product",
                "item",
                "details",
                "features",
                "specification",
                "ingredients",
            ]
        ):
            return Intent.PRODUCT_INFO, 0.80, entities

        # Shipping questions
        if any(
            word in message_lower
            for word in [
                "shipping",
                "ship to",
                "how fast",
                "delivery time",
                "free shipping",
                "international",
            ]
        ):
            return Intent.SHIPPING_QUESTION, 0.75, entities

        # Loyalty program
        if any(
            word in message_lower
            for word in ["loyalty", "points", "rewards", "credit", "glow rewards"]
        ):
            return Intent.LOYALTY_PROGRAM, 0.80, entities

        # General inquiry - catch-all
        return Intent.GENERAL_INQUIRY, 0.50, entities

    def _determine_routing(
        self,
        intent: Intent,
        auth_level: str = "anonymous",
        session: Optional["CustomerSession"] = None,
    ) -> str:
        """
        Determine which agent topic to route to based on intent and auth level.

        Phase 6 Enhancement: Auth-aware routing
        - Order modifications require authentication
        - Anonymous users prompted to authenticate for sensitive operations
        - VIP customers can have priority routing

        Args:
            intent: Classified intent
            auth_level: Current authentication level
            session: Optional session for additional context

        Returns:
            Target agent topic name
        """
        # Immediate escalation intents
        if intent == Intent.ESCALATION_NEEDED:
            return "escalation"

        # Phase 6: Intents requiring authentication
        # These need at least IDENTIFIED level for order lookup
        order_intents = [
            Intent.ORDER_STATUS,
            Intent.ORDER_MODIFICATION,
            Intent.RETURN_REQUEST,
            Intent.REFUND_STATUS,
            Intent.AUTO_DELIVERY_MANAGEMENT,
        ]

        # Phase 6: Check if intent requires auth but user is anonymous
        if intent in order_intents and auth_level == "anonymous":
            # Route to knowledge-retrieval which will prompt for email
            # The response will ask for email to look up their order
            self.logger.debug(
                f"Intent {intent.value} requires identification, routing to knowledge-retrieval"
            )
            return "knowledge-retrieval"

        # Phase 6: Intents that require AUTHENTICATED (not just IDENTIFIED)
        modify_intents = [
            Intent.ORDER_MODIFICATION,
        ]

        if intent in modify_intents and auth_level != "authenticated":
            # Route to escalation which can handle auth flow
            self.logger.debug(
                f"Intent {intent.value} requires authentication, routing to auth-prompt"
            )
            return "knowledge-retrieval"  # Will prompt for login

        # Phase 6: VIP priority routing (future enhancement)
        if session and SESSION_SUPPORT and session.customer and session.customer.is_vip:
            # VIP customers could get priority routing
            self.logger.debug(f"VIP customer detected, applying priority routing")
            # For now, same routing - future: dedicated VIP agent queue

        # Intents requiring knowledge retrieval (most common path)
        knowledge_intents = [
            Intent.ORDER_STATUS,
            Intent.PRODUCT_INFO,
            Intent.PRODUCT_RECOMMENDATION,
            Intent.PRODUCT_COMPARISON,
            Intent.SHIPPING_QUESTION,
            Intent.RETURN_REQUEST,
            Intent.REFUND_STATUS,
            Intent.AUTO_DELIVERY_MANAGEMENT,
            Intent.BREWER_SUPPORT,
            Intent.GIFT_CARD,
            Intent.LOYALTY_PROGRAM,
            Intent.ORDER_MODIFICATION,
            Intent.GENERAL_INQUIRY,
        ]

        if intent in knowledge_intents:
            return "knowledge-retrieval"

        # Default to knowledge retrieval
        return "knowledge-retrieval"


if __name__ == "__main__":
    run_agent(IntentClassificationAgent)
