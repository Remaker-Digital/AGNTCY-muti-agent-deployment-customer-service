"""
Base Agent Class - Shared functionality for all AGNTCY agents

Reduces code duplication across agents by providing:
- Common initialization patterns (factory, transport, client)
- Azure OpenAI client initialization and fallback
- Graceful shutdown and cleanup
- Demo mode structure
- Statistics tracking

Usage:
    class MyAgent(BaseAgent):
        agent_name = "my-agent"
        default_topic = "my-topic"

        async def process_message(self, content: dict, message: dict) -> dict:
            # Agent-specific logic here
            return {"result": "..."}

        def get_demo_messages(self) -> list:
            return [{"contextId": "demo", "parts": [...]}]
"""

import sys
import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add shared utilities to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.factory import get_factory, shutdown_factory
from shared.utils import setup_logging, load_config, handle_graceful_shutdown
from shared.models import (
    create_a2a_message,
    extract_message_content,
    generate_context_id,
)


class BaseAgent(ABC):
    """
    Abstract base class for all AGNTCY agents.

    Provides common initialization, cleanup, and message handling patterns.
    Subclasses must implement process_message() and get_demo_messages().
    """

    # Override in subclass
    agent_name: str = "base-agent"
    default_topic: str = "agent"

    def __init__(self, topic: Optional[str] = None):
        """
        Initialize the agent with common configuration.

        Args:
            topic: Optional override for agent topic (defaults to default_topic)
        """
        # Load configuration
        self.config = load_config()
        self.agent_topic = topic or self.config.get("agent_topic", self.default_topic)

        # Setup logging
        self.logger = setup_logging(
            name=self.agent_topic, level=self.config.get("log_level", "INFO")
        )

        self.logger.info(f"Initializing {self.agent_name} on topic: {self.agent_topic}")

        # Get AGNTCY factory singleton
        self.factory = get_factory()

        # AGNTCY components (initialized in initialize())
        self.transport = None
        self.client = None
        self.container = None

        # Azure OpenAI client
        self.openai_client = None
        self._use_openai = os.getenv("USE_AZURE_OPENAI", "true").lower() == "true"

        # Statistics
        self.messages_processed = 0
        self.openai_calls = 0
        self.fallback_calls = 0

    async def initialize(self) -> None:
        """
        Initialize AGNTCY SDK and Azure OpenAI components.

        Creates SLIM transport and A2A client. Falls back to demo mode
        if SDK is not available.
        """
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
                    agent_topic=self.agent_topic, transport=self.transport
                )

                if self.client:
                    self.logger.info(
                        f"A2A client created for topic: {self.agent_topic}"
                    )

            # Initialize Azure OpenAI client (Phase 4+)
            if self._use_openai:
                await self._initialize_openai()

            self.logger.info("Agent initialization complete")

        except Exception as e:
            self.logger.error(
                f"Failed to initialize AGNTCY components: {e}", exc_info=True
            )
            raise

    async def _initialize_openai(self) -> None:
        """
        Initialize Azure OpenAI client.

        Falls back gracefully if Azure OpenAI is not configured.
        """
        try:
            from shared.azure_openai import get_openai_client

            self.openai_client = get_openai_client()
            success = await self.openai_client.initialize()

            if success:
                self.logger.info("Azure OpenAI client initialized")
            else:
                self.logger.warning("Azure OpenAI not available. Using fallback mode.")
                self.openai_client = None

        except ImportError:
            self.logger.warning(
                "Azure OpenAI package not installed. Using fallback mode."
            )
            self.openai_client = None
        except Exception as e:
            self.logger.warning(
                f"Failed to initialize Azure OpenAI: {e}. Using fallback mode."
            )
            self.openai_client = None

    async def handle_message(self, message: dict) -> dict:
        """
        Handle incoming A2A message.

        Extracts content, delegates to process_message(), and wraps response.

        Args:
            message: AGNTCY A2A message

        Returns:
            A2A response message
        """
        self.messages_processed += 1
        context_id = message.get("contextId", generate_context_id())

        try:
            # Extract message content
            content = extract_message_content(message)
            self.logger.debug(f"Received message: {content}")

            # Delegate to subclass-specific processing
            result = await self.process_message(content, message)

            # Track method used
            if self.openai_client:
                self.openai_calls += 1
            else:
                self.fallback_calls += 1

            # Wrap result in A2A message
            return create_a2a_message(
                role="assistant",
                content=result,
                context_id=context_id,
                task_id=message.get("taskId"),
                metadata={
                    "agent": self.agent_topic,
                    "processed_count": self.messages_processed,
                    "method": "openai" if self.openai_client else "fallback",
                },
            )

        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)
            return create_a2a_message(
                role="assistant", content={"error": str(e)}, context_id=context_id
            )

    @abstractmethod
    async def process_message(self, content: dict, message: dict) -> dict:
        """
        Process message content and return result.

        Must be implemented by subclasses.

        Args:
            content: Extracted message content
            message: Full A2A message (for context_id, task_id, etc.)

        Returns:
            Processing result (will be wrapped in A2A message)
        """
        pass

    @abstractmethod
    def get_demo_messages(self) -> List[dict]:
        """
        Return sample messages for demo mode.

        Must be implemented by subclasses.

        Returns:
            List of A2A messages for demo testing
        """
        pass

    def cleanup(self) -> None:
        """
        Cleanup resources on shutdown.

        Reports statistics, stops container, and shuts down factory.
        """
        self.logger.info("Cleaning up agent resources...")

        # Report statistics
        self.logger.info(
            f"Statistics - Processed: {self.messages_processed}, "
            f"OpenAI: {self.openai_calls}, Fallback: {self.fallback_calls}"
        )

        # Report OpenAI token usage if available
        if self.openai_client:
            try:
                usage = self.openai_client.get_total_usage()
                self.logger.info(
                    f"Token usage - Total: {usage['total_tokens']}, "
                    f"Cost: ${usage['total_cost']:.4f}"
                )
            except Exception as e:
                self.logger.debug(f"Could not get token usage: {e}")

        # Stop container if running
        if self.container:
            try:
                self.container.stop()
                self.logger.info("Container stopped")
            except Exception as e:
                self.logger.error(f"Error stopping container: {e}")

        shutdown_factory()
        self.logger.info("Cleanup complete")

    async def run_demo_mode(self) -> None:
        """
        Run in demo mode without SDK (for testing).

        Processes sample messages from get_demo_messages().
        """
        self.logger.info("Running in DEMO MODE (no SDK connection)")
        self.logger.info(
            f"Processing method: {'Azure OpenAI' if self.openai_client else 'Fallback'}"
        )

        # Get demo messages from subclass
        sample_messages = self.get_demo_messages()

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
                self.logger.debug(
                    f"Heartbeat - {self.messages_processed} messages processed"
                )
        except asyncio.CancelledError:
            self.logger.info("Demo mode cancelled")

    async def run(self) -> None:
        """
        Main entry point to run the agent.

        Initializes, then either runs demo mode or waits for messages.
        """
        # Setup graceful shutdown
        handle_graceful_shutdown(self.logger, cleanup_callback=self.cleanup)

        try:
            # Initialize AGNTCY components
            await self.initialize()

            # If SDK not available, run demo mode
            if self.client is None:
                await self.run_demo_mode()
            else:
                # Production mode: Wait for messages
                self.logger.info("Agent ready and waiting for messages...")

                # Keep alive - in production handled by AppContainer.loop_forever()
                while True:
                    await asyncio.sleep(10)
                    self.logger.debug("Agent alive - waiting for messages")

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Agent crashed: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.cleanup()


def run_agent(agent_class: type) -> None:
    """
    Convenience function to run an agent.

    Usage:
        if __name__ == "__main__":
            run_agent(MyAgent)
    """
    agent = agent_class()
    asyncio.run(agent.run())
