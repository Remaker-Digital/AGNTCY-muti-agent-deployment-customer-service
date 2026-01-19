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

        Phase 1: Basic keyword rules
        Phase 2: Replace with real NLP model (Azure Language Service, OpenAI, etc.)

        Args:
            message_text: Customer message content

        Returns:
            Tuple of (intent, confidence, extracted_entities)
        """
        message_lower = message_text.lower()
        entities = {}

        # Order status keywords
        if any(word in message_lower for word in ["order", "tracking", "shipment", "delivery"]):
            # Try to extract order number
            import re
            order_match = re.search(r'#?(\d{4,6})', message_text)
            if order_match:
                entities["order_number"] = order_match.group(1)
            return Intent.ORDER_STATUS, 0.85, entities

        # Return/refund keywords
        if any(word in message_lower for word in ["return", "refund", "exchange", "send back"]):
            return Intent.RETURN_REQUEST, 0.80, entities

        # Product inquiry keywords
        if any(word in message_lower for word in ["product", "item", "available", "stock", "price"]):
            return Intent.PRODUCT_INQUIRY, 0.75, entities

        # Shipping keywords
        if any(word in message_lower for word in ["shipping", "delivery time", "when will"]):
            return Intent.SHIPPING_QUESTION, 0.70, entities

        # Payment keywords
        if any(word in message_lower for word in ["payment", "credit card", "charged", "billing"]):
            return Intent.PAYMENT_ISSUE, 0.75, entities

        # Account keywords
        if any(word in message_lower for word in ["account", "login", "password", "profile"]):
            return Intent.ACCOUNT_SUPPORT, 0.70, entities

        # Complaint keywords
        if any(word in message_lower for word in ["complaint", "problem", "issue", "angry", "upset"]):
            return Intent.COMPLAINT, 0.80, entities

        # Default to general inquiry
        return Intent.GENERAL_INQUIRY, 0.50, entities

    def _determine_routing(self, intent: Intent) -> str:
        """
        Determine which agent topic to route to based on intent.

        Args:
            intent: Classified intent

        Returns:
            Target agent topic name
        """
        # All intents route to knowledge retrieval first for context
        # In Phase 2, this can be more sophisticated
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
