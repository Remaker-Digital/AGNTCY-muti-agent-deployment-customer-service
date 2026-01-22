"""
Intent Classification Agent
Routes incoming customer requests to appropriate handlers based on intent analysis

Phase 1: AGNTCY SDK integration with mock classification logic
Phase 2: Implement real NLP-based classification
"""

import sys
import asyncio
from pathlib import Path

# Add shared utilities to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import (
    get_factory,
    shutdown_factory,
    setup_logging,
    load_config,
    handle_graceful_shutdown
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


class IntentClassificationAgent:
    """
    Intent Classification Agent - Routes customer messages to appropriate handlers.

    Uses AGNTCY SDK A2A protocol over SLIM transport for agent-to-agent communication.
    In Phase 1, uses simple keyword matching for classification.
    """

    def __init__(self):
        """Initialize the Intent Classification Agent."""
        # Load configuration
        self.config = load_config()
        self.agent_topic = self.config["agent_topic"]

        # Setup logging
        self.logger = setup_logging(
            name=self.agent_topic,
            level=self.config["log_level"]
        )

        self.logger.info(f"Initializing Intent Classification Agent on topic: {self.agent_topic}")

        # Get AGNTCY factory singleton
        self.factory = get_factory()

        # Create transport and client
        self.transport = None
        self.client = None
        self.container = None

        # Message counters for Phase 1 demonstration
        self.messages_processed = 0

    async def initialize(self):
        """Initialize AGNTCY SDK components."""
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
                return

            self.logger.info(f"SLIM transport created: {self.transport}")

            # Create A2A client for custom agent logic
            self.logger.info("Creating A2A client...")
            self.client = self.factory.create_a2a_client(
                agent_topic=self.agent_topic,
                transport=self.transport
            )

            if self.client is None:
                self.logger.warning("A2A client not created. Running in demo mode.")
                return

            self.logger.info(f"A2A client created for topic: {self.agent_topic}")

            # Register message handler
            # Note: Actual handler registration depends on SDK version
            # This is the conceptual pattern - adjust based on SDK API
            self.logger.info("Agent initialization complete")

        except Exception as e:
            self.logger.error(f"Failed to initialize AGNTCY components: {e}", exc_info=True)
            raise

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

            # Classify intent (Phase 1: Simple keyword matching)
            intent, confidence, entities = self._classify_intent_mock(customer_msg.content)

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
                f"→ route to: {result.routing_suggestion}"
            )

            # Create A2A response message
            response = create_a2a_message(
                role="assistant",
                content=result,
                context_id=customer_msg.context_id,
                task_id=message.get("taskId"),
                metadata={
                    "agent": self.agent_topic,
                    "processed_count": self.messages_processed
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

    def _classify_intent_mock(self, message_text: str) -> tuple:
        """
        Mock intent classification using simple keyword matching.

        Phase 2 implementation with coffee/brewing specific intents.
        Phase 3+: Replace with real NLP model (Azure Language Service, OpenAI, etc.)

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

        # Priority 2: Frustration detection (after 3 attempts - Phase 2 TODO: track conversation history)
        frustration_words = ["frustrated", "angry", "upset", "annoyed", "ridiculous", "terrible", "awful", "hate"]
        if any(word in message_lower for word in frustration_words):
            entities["escalation_reason"] = "customer_frustration"
            return Intent.ESCALATION_NEEDED, 0.85, entities

        # Order status queries (highest priority for Week 1-2 demo)
        if any(word in message_lower for word in [
            "where is my order", "track", "tracking", "shipment", "delivery", "shipped", "arrive"
        ]):
            # Extract order number - support formats: ORD-10234, #10234, 10234
            order_match = re.search(r'(?:ORD-|#)?(\d{4,6})', message_text, re.IGNORECASE)
            if order_match:
                entities["order_number"] = order_match.group(1)
            return Intent.ORDER_STATUS, 0.90, entities

        # Brewer support/troubleshooting
        if any(word in message_lower for word in [
            "brewer", "machine", "won't turn on", "not working", "broken", "red light",
            "error", "beeping", "clean", "descale", "maintenance"
        ]):
            # Check if it's a defect (escalate) vs. general support
            if any(word in message_lower for word in [
                "broken", "defect", "stopped working", "never worked", "won't turn on"
            ]):
                entities["escalation_reason"] = "brewer_defect"
                return Intent.ESCALATION_NEEDED, 0.85, entities
            return Intent.BREWER_SUPPORT, 0.80, entities

        # Return/refund requests
        if any(word in message_lower for word in ["return", "refund", "send back", "money back", "exchange"]):
            # Try to extract amount for auto-approval logic
            amount_match = re.search(r'\$?(\d+(?:\.\d{2})?)', message_text)
            if amount_match:
                entities["refund_amount"] = float(amount_match.group(1))
            return Intent.RETURN_REQUEST, 0.85, entities

        # Damaged delivery
        if any(word in message_lower for word in [
            "damaged", "crushed", "broken box", "leaked", "spilled", "missing items"
        ]):
            entities["escalation_reason"] = "damaged_delivery"
            return Intent.ESCALATION_NEEDED, 0.90, entities

        # Product defect/quality issues
        if any(word in message_lower for word in [
            "defect", "quality", "stale", "taste", "bad coffee", "weak coffee", "expired"
        ]):
            entities["escalation_reason"] = "product_quality"
            return Intent.ESCALATION_NEEDED, 0.85, entities

        # Auto-delivery/subscription management
        if any(word in message_lower for word in [
            "subscription", "auto-delivery", "auto delivery", "pause", "skip", "cancel subscription",
            "change frequency", "add to next order"
        ]):
            return Intent.AUTO_DELIVERY_MANAGEMENT, 0.85, entities

        # Product information (biodegradable pods, roasts, ingredients)
        if any(word in message_lower for word in [
            "biodegradable", "eco-friendly", "guilt free toss", "roast", "light roast", "dark roast",
            "medium roast", "ingredients", "organic", "fair trade", "caffeine", "decaf"
        ]):
            return Intent.PRODUCT_INFO, 0.80, entities

        # Product recommendations
        if any(word in message_lower for word in [
            "recommend", "suggestion", "best", "good for", "which", "what's good", "favorite",
            "popular", "best seller"
        ]):
            return Intent.PRODUCT_RECOMMENDATION, 0.75, entities

        # Product comparison
        if any(word in message_lower for word in [
            "difference between", "compare", "vs", "versus", "better than", "which one"
        ]):
            return Intent.PRODUCT_COMPARISON, 0.80, entities

        # Shipping questions
        if any(word in message_lower for word in [
            "shipping", "ship to", "how fast", "delivery time", "free shipping", "international"
        ]):
            return Intent.SHIPPING_QUESTION, 0.75, entities

        # Order modifications
        if any(word in message_lower for word in [
            "cancel order", "change address", "update order", "modify order"
        ]):
            return Intent.ORDER_MODIFICATION, 0.85, entities

        # Gift cards
        if any(word in message_lower for word in ["gift card", "gift certificate", "balance"]):
            return Intent.GIFT_CARD, 0.80, entities

        # Loyalty program
        if any(word in message_lower for word in [
            "loyalty", "points", "rewards", "credit", "glow rewards"
        ]):
            return Intent.LOYALTY_PROGRAM, 0.80, entities

        # Wholesale/B2B inquiries (escalate to sales)
        if any(word in message_lower for word in [
            "wholesale", "bulk order", "office", "business", "commercial", "net 30",
            "volume discount", "corporate"
        ]):
            entities["escalation_reason"] = "b2b_sales_opportunity"
            return Intent.ESCALATION_NEEDED, 0.90, entities

        # Refund status
        if any(word in message_lower for word in ["refund status", "where's my refund", "refund processed"]):
            return Intent.REFUND_STATUS, 0.85, entities

        # General inquiry - catch-all
        return Intent.GENERAL_INQUIRY, 0.50, entities

    def _determine_routing(self, intent: Intent) -> str:
        """
        Determine which agent topic to route to based on intent.

        Phase 2: Route based on intent type for optimized handling.

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
            Intent.LOYALTY_PROGRAM
        ]

        if intent in knowledge_intents:
            return "knowledge-retrieval"

        # Order modifications may need escalation but check knowledge base first
        if intent == Intent.ORDER_MODIFICATION:
            return "knowledge-retrieval"

        # General inquiries go to knowledge retrieval
        return "knowledge-retrieval"

    def cleanup(self):
        """Cleanup resources on shutdown."""
        self.logger.info("Cleaning up Intent Classification Agent...")

        if self.container:
            try:
                self.container.stop()
                self.logger.info("Container stopped")
            except Exception as e:
                self.logger.error(f"Error stopping container: {e}")

        if self.client:
            # Client cleanup if needed
            pass

        if self.transport:
            # Transport cleanup if needed
            pass

        shutdown_factory()
        self.logger.info("Cleanup complete")

    async def run_demo_mode(self):
        """
        Run in demo mode without SDK (for Phase 1 testing).

        Simulates receiving and processing messages.
        """
        self.logger.info("Running in DEMO MODE (no SDK connection)")
        self.logger.info("Simulating message processing...")

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
