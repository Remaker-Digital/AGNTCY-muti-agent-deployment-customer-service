"""
Intent Classification Agent
Routes incoming customer requests to appropriate handlers based on intent analysis

Phase 1-3: Mock classification logic with keyword matching
Phase 4+: Azure OpenAI GPT-4o-mini for real intent classification
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Add shared utilities to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import (
    get_factory,
    shutdown_factory,
    setup_logging,
    load_config,
    handle_graceful_shutdown,
    get_openai_client,
    shutdown_openai_client
)
from shared.models import (
    CustomerMessage,
    IntentClassificationResult,
    Intent,
    Language,
    create_a2a_message,
    extract_message_content,
    generate_message_id,
    generate_context_id
)


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


class IntentClassificationAgent:
    """
    Intent Classification Agent - Routes customer messages to appropriate handlers.

    Uses AGNTCY SDK A2A protocol over SLIM transport for agent-to-agent communication.
    Phase 4+: Uses Azure OpenAI GPT-4o-mini for intent classification.
    """

    def __init__(self):
        """Initialize the Intent Classification Agent."""
        # Load configuration
        self.config = load_config()
        self.agent_topic = self.config.get("agent_topic", "intent-classifier")

        # Setup logging
        self.logger = setup_logging(
            name=self.agent_topic,
            level=self.config.get("log_level", "INFO")
        )

        self.logger.info(f"Initializing Intent Classification Agent on topic: {self.agent_topic}")

        # Get AGNTCY factory singleton
        self.factory = get_factory()

        # Create transport and client
        self.transport = None
        self.client = None
        self.container = None

        # Azure OpenAI client
        self.openai_client = None
        self._use_openai = os.getenv("USE_AZURE_OPENAI", "true").lower() == "true"

        # Message counters
        self.messages_processed = 0
        self.openai_classifications = 0
        self.mock_classifications = 0

    async def initialize(self):
        """Initialize AGNTCY SDK and Azure OpenAI components."""
        self.logger.info("Creating SLIM transport...")

        try:
            # Create SLIM transport
            self.transport = self.factory.create_slim_transport(
                name=f"{self.agent_topic}-transport"
            )

            if self.transport is None:
                self.logger.warning(
                    "SLIM transport not created (SDK may not be available). "
                    "Running in demo mode."
                )
            else:
                self.logger.info(f"SLIM transport created: {self.transport}")

                # Create A2A client for custom agent logic
                self.logger.info("Creating A2A client...")
                self.client = self.factory.create_a2a_client(
                    agent_topic=self.agent_topic,
                    transport=self.transport
                )

                if self.client:
                    self.logger.info(f"A2A client created for topic: {self.agent_topic}")

            # Initialize Azure OpenAI client (Phase 4+)
            if self._use_openai:
                await self._initialize_openai()

            self.logger.info("Agent initialization complete")

        except Exception as e:
            self.logger.error(f"Failed to initialize AGNTCY components: {e}", exc_info=True)
            raise

    async def _initialize_openai(self):
        """Initialize Azure OpenAI client for intent classification."""
        try:
            self.openai_client = get_openai_client()
            success = await self.openai_client.initialize()

            if success:
                self.logger.info("Azure OpenAI client initialized for intent classification")
            else:
                self.logger.warning("Azure OpenAI not available. Using mock classification.")
                self.openai_client = None

        except Exception as e:
            self.logger.warning(f"Failed to initialize Azure OpenAI: {e}. Using mock classification.")
            self.openai_client = None

    async def handle_message(self, message: dict) -> dict:
        """
        Handle incoming customer message and classify intent.

        Args:
            message: AGNTCY A2A message with customer input

        Returns:
            IntentClassificationResult as A2A message
        """
        self.messages_processed += 1

        try:
            # Extract customer message content
            content = extract_message_content(message)
            self.logger.debug(f"Received message: {content}")

            # Parse as CustomerMessage
            customer_msg = CustomerMessage(
                message_id=content.get("message_id", generate_message_id()),
                customer_id=content.get("customer_id", "unknown"),
                content=content.get("content", ""),
                channel=content.get("channel", "chat"),
                context_id=message.get("contextId", generate_context_id()),
                language=Language(content.get("language", "en")),
                metadata=content.get("metadata", {})
            )

            self.logger.info(
                f"Processing message {customer_msg.message_id} from customer {customer_msg.customer_id}"
            )

            # Classify intent using Azure OpenAI or mock
            if self.openai_client:
                intent, confidence, entities = await self._classify_intent_openai(customer_msg.content)
                self.openai_classifications += 1
            else:
                intent, confidence, entities = self._classify_intent_mock(customer_msg.content)
                self.mock_classifications += 1

            # Create classification result
            result = IntentClassificationResult(
                message_id=customer_msg.message_id,
                context_id=customer_msg.context_id,
                intent=intent,
                confidence=confidence,
                extracted_entities=entities,
                language=customer_msg.language,
                routing_suggestion=self._determine_routing(intent)
            )

            self.logger.info(
                f"Classified intent: {intent.value} (confidence: {confidence:.2f}) "
                f"-> route to: {result.routing_suggestion}"
            )

            # Create A2A response message
            response = create_a2a_message(
                role="assistant",
                content=result,
                context_id=customer_msg.context_id,
                task_id=message.get("taskId"),
                metadata={
                    "agent": self.agent_topic,
                    "processed_count": self.messages_processed,
                    "classification_method": "openai" if self.openai_client else "mock"
                }
            )

            return response

        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)
            # Return error response
            return create_a2a_message(
                role="assistant",
                content={"error": str(e), "intent": Intent.UNKNOWN.value},
                context_id=message.get("contextId", generate_context_id())
            )

    async def _classify_intent_openai(self, message_text: str) -> Tuple[Intent, float, Dict[str, Any]]:
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
                temperature=0.0
            )

            # Extract intent from response
            intent_str = result.get("intent", "GENERAL_INQUIRY")
            confidence = result.get("confidence", 0.5)

            # Map to internal Intent enum
            intent = INTENT_MAPPING.get(intent_str, Intent.GENERAL_INQUIRY)

            # Extract entities (basic extraction for now)
            entities = self._extract_entities(message_text)
            entities["raw_intent"] = intent_str  # Store original classification

            self.logger.debug(f"OpenAI classification: {intent_str} -> {intent.value} ({confidence:.2f})")

            return intent, confidence, entities

        except Exception as e:
            self.logger.error(f"OpenAI classification error: {e}")
            # Fall back to mock classification
            return self._classify_intent_mock(message_text)

    def _extract_entities(self, message_text: str) -> Dict[str, Any]:
        """Extract entities from message text."""
        import re
        entities = {}

        # Extract order number - support formats: ORD-10234, #10234, 10234
        order_match = re.search(r'(?:ORD-|#)?(\d{4,6})', message_text, re.IGNORECASE)
        if order_match:
            entities["order_number"] = order_match.group(1)

        # Extract email address
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message_text)
        if email_match:
            entities["email"] = email_match.group()

        # Extract phone number (basic US format)
        phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', message_text)
        if phone_match:
            entities["phone"] = phone_match.group()

        return entities

    def _classify_intent_mock(self, message_text: str) -> Tuple[Intent, float, Dict[str, Any]]:
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
        import re

        # Priority 1: Escalation triggers (health & safety)
        if any(word in message_lower for word in [
            "allerg", "rash", "medical", "sick", "poison", "reaction", "emergency"
        ]):
            self.logger.warning(f"CRITICAL: Health/safety escalation detected in message")
            return Intent.ESCALATION_NEEDED, 0.95, {"escalation_reason": "health_safety"}

        # Priority 2: Frustration detection
        frustration_words = ["frustrated", "angry", "upset", "annoyed", "ridiculous", "terrible", "awful", "hate"]
        if any(word in message_lower for word in frustration_words):
            entities["escalation_reason"] = "customer_frustration"
            return Intent.ESCALATION_NEEDED, 0.85, entities

        # Return/refund requests
        if any(word in message_lower for word in ["return", "refund", "send back", "money back", "exchange"]):
            order_match = re.search(r'(?:ORD-|#)?(\d{4,6})', message_text, re.IGNORECASE)
            if order_match:
                entities["order_number"] = order_match.group(1)
            return Intent.RETURN_REQUEST, 0.85, entities

        # Order status queries
        if any(word in message_lower for word in [
            "where is my order", "where's my order", "track", "tracking", "shipment", "delivery",
            "shipped", "arrive", "status of order", "status of my order", "order status",
            "been delivered", "has my order"
        ]):
            order_match = re.search(r'(?:ORD-|#)?(\d{4,6})', message_text, re.IGNORECASE)
            if order_match:
                entities["order_number"] = order_match.group(1)
            return Intent.ORDER_STATUS, 0.90, entities

        # Subscription management
        if any(word in message_lower for word in [
            "subscription", "auto-delivery", "auto delivery", "pause", "skip", "cancel subscription",
            "change frequency", "add to next order", "change my subscription", "modify subscription"
        ]):
            return Intent.AUTO_DELIVERY_MANAGEMENT, 0.85, entities

        # Product information
        if any(word in message_lower for word in [
            "product", "item", "details", "features", "specification", "ingredients"
        ]):
            return Intent.PRODUCT_INFO, 0.80, entities

        # Shipping questions
        if any(word in message_lower for word in [
            "shipping", "ship to", "how fast", "delivery time", "free shipping", "international"
        ]):
            return Intent.SHIPPING_QUESTION, 0.75, entities

        # Loyalty program
        if any(word in message_lower for word in [
            "loyalty", "points", "rewards", "credit", "glow rewards"
        ]):
            return Intent.LOYALTY_PROGRAM, 0.80, entities

        # General inquiry - catch-all
        return Intent.GENERAL_INQUIRY, 0.50, entities

    def _determine_routing(self, intent: Intent) -> str:
        """
        Determine which agent topic to route to based on intent.

        Args:
            intent: Classified intent

        Returns:
            Target agent topic name
        """
        # Immediate escalation intents
        if intent == Intent.ESCALATION_NEEDED:
            return "escalation"

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
            Intent.GENERAL_INQUIRY
        ]

        if intent in knowledge_intents:
            return "knowledge-retrieval"

        # Default to knowledge retrieval
        return "knowledge-retrieval"

    def cleanup(self):
        """Cleanup resources on shutdown."""
        self.logger.info("Cleaning up Intent Classification Agent...")
        self.logger.info(
            f"Statistics - Total: {self.messages_processed}, "
            f"OpenAI: {self.openai_classifications}, "
            f"Mock: {self.mock_classifications}"
        )

        # Log token usage if available
        if self.openai_client:
            usage = self.openai_client.get_total_usage()
            self.logger.info(
                f"Token usage - Total: {usage['total_tokens']}, "
                f"Cost: ${usage['total_cost']:.4f}"
            )

        if self.container:
            try:
                self.container.stop()
                self.logger.info("Container stopped")
            except Exception as e:
                self.logger.error(f"Error stopping container: {e}")

        shutdown_factory()
        self.logger.info("Cleanup complete")

    async def run_demo_mode(self):
        """
        Run in demo mode without SDK (for testing).

        Simulates receiving and processing messages.
        """
        self.logger.info("Running in DEMO MODE (no SDK connection)")
        self.logger.info(f"Classification method: {'Azure OpenAI' if self.openai_client else 'Mock'}")

        # Demo: Process sample messages
        sample_messages = [
            {
                "contextId": "demo-ctx-001",
                "taskId": "demo-task-001",
                "parts": [{
                    "type": "text",
                    "content": {
                        "message_id": "msg-001",
                        "customer_id": "cust-123",
                        "content": "Where is my order #12345?",
                        "channel": "chat"
                    }
                }]
            },
            {
                "contextId": "demo-ctx-002",
                "taskId": "demo-task-002",
                "parts": [{
                    "type": "text",
                    "content": {
                        "message_id": "msg-002",
                        "customer_id": "cust-456",
                        "content": "I want to return the blue sweater I ordered",
                        "channel": "email"
                    }
                }]
            },
            {
                "contextId": "demo-ctx-003",
                "taskId": "demo-task-003",
                "parts": [{
                    "type": "text",
                    "content": {
                        "message_id": "msg-003",
                        "customer_id": "cust-789",
                        "content": "This is the third time I've contacted you about this issue!",
                        "channel": "chat"
                    }
                }]
            },
            {
                "contextId": "demo-ctx-004",
                "taskId": "demo-task-004",
                "parts": [{
                    "type": "text",
                    "content": {
                        "message_id": "msg-004",
                        "customer_id": "cust-101",
                        "content": "Do you ship to Canada?",
                        "channel": "chat"
                    }
                }]
            }
        ]

        for msg in sample_messages:
            self.logger.info("=" * 60)
            result = await self.handle_message(msg)
            content = extract_message_content(result)
            self.logger.info(f"Demo Result: {content}")
            await asyncio.sleep(2)

        # Keep alive for container health
        self.logger.info("Demo complete. Keeping alive for health checks...")
        try:
            while True:
                await asyncio.sleep(30)
                self.logger.debug(f"Heartbeat - {self.messages_processed} messages processed")
        except asyncio.CancelledError:
            self.logger.info("Demo mode cancelled")


async def main():
    """Main entry point for Intent Classification Agent."""
    agent = IntentClassificationAgent()

    # Setup graceful shutdown
    handle_graceful_shutdown(agent.logger, cleanup_callback=agent.cleanup)

    try:
        # Initialize AGNTCY components
        await agent.initialize()

        # If SDK not available, run demo mode
        if agent.client is None:
            await agent.run_demo_mode()
        else:
            # Production mode: Wait for messages
            agent.logger.info("Agent ready and waiting for messages...")

            # Keep alive - in production this would be handled by AppContainer.loop_forever()
            while True:
                await asyncio.sleep(10)
                agent.logger.debug("Agent alive - waiting for messages")

    except KeyboardInterrupt:
        agent.logger.info("Received keyboard interrupt")
    except Exception as e:
        agent.logger.error(f"Agent crashed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
