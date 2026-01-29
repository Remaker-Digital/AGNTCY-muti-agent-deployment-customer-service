# ============================================================================
# Unit Tests for Base Agent
# ============================================================================
# Purpose: Test shared agent functionality and patterns
#
# Test Categories:
# 1. Agent Initialization - Verify setup and configuration
# 2. Message Handling - Test A2A message processing
# 3. OpenAI Integration - Test Azure OpenAI client fallback
# 4. Statistics Tracking - Verify metrics tracking
# 5. Demo Mode - Test demo/standalone operation
# 6. Cleanup - Test resource cleanup
# 7. Abstract Methods - Verify interface enforcement
#
# Related Documentation:
# - Base Agent: shared/base_agent.py
# - AGNTCY SDK Patterns: AGNTCY-REVIEW.md#factory-pattern
# ============================================================================

import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from typing import List, Dict, Any

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.base_agent import BaseAgent, run_agent


# =============================================================================
# Test Fixtures
# =============================================================================


class ConcreteTestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    agent_name = "test-agent"
    default_topic = "test-topic"

    def __init__(self, topic=None):
        # Patch config and logging before super().__init__
        with patch("shared.base_agent.load_config", return_value={}):
            with patch("shared.base_agent.setup_logging") as mock_logging:
                mock_logging.return_value = MagicMock()
                with patch("shared.base_agent.get_factory") as mock_factory:
                    mock_factory.return_value = MagicMock()
                    super().__init__(topic)

    async def process_message(self, content: dict, message: dict) -> dict:
        """Test implementation of process_message."""
        return {"processed": True, "input": content}

    def get_demo_messages(self) -> List[dict]:
        """Test implementation of get_demo_messages."""
        return [
            {
                "contextId": "demo-ctx-1",
                "parts": [{"text": "Demo message 1"}],
            },
            {
                "contextId": "demo-ctx-2",
                "parts": [{"text": "Demo message 2"}],
            },
        ]


@pytest.fixture
def test_agent():
    """Create a test agent instance."""
    return ConcreteTestAgent()


@pytest.fixture
def sample_a2a_message():
    """Sample A2A message for testing."""
    return {
        "contextId": "ctx-12345",
        "taskId": "task-67890",
        "role": "user",
        "parts": [{"text": "Hello, agent!"}],
        "metadata": {"channel": "test"},
    }


# =============================================================================
# Test: Agent Initialization
# =============================================================================


class TestAgentInitialization:
    """Tests for agent initialization."""

    def test_agent_creation(self, test_agent):
        """Verify agent is created with correct attributes."""
        assert test_agent.agent_name == "test-agent"
        assert test_agent.default_topic == "test-topic"
        assert test_agent.agent_topic == "test-topic"

    def test_agent_with_custom_topic(self):
        """Verify custom topic override."""
        agent = ConcreteTestAgent(topic="custom-topic")
        assert agent.agent_topic == "custom-topic"

    def test_initial_statistics(self, test_agent):
        """Verify initial statistics are zero."""
        assert test_agent.messages_processed == 0
        assert test_agent.openai_calls == 0
        assert test_agent.fallback_calls == 0

    def test_components_initially_none(self, test_agent):
        """Verify AGNTCY components are initially None."""
        assert test_agent.transport is None
        assert test_agent.client is None
        assert test_agent.container is None
        assert test_agent.openai_client is None


class TestAgentInitializeMethod:
    """Tests for the initialize() method."""

    @pytest.mark.asyncio
    async def test_initialize_creates_transport(self, test_agent):
        """Verify initialize creates SLIM transport."""
        mock_transport = MagicMock()
        test_agent.factory.create_slim_transport = MagicMock(return_value=mock_transport)
        test_agent.factory.create_a2a_client = MagicMock(return_value=MagicMock())
        test_agent._use_openai = False

        await test_agent.initialize()

        test_agent.factory.create_slim_transport.assert_called_once()
        assert test_agent.transport == mock_transport

    @pytest.mark.asyncio
    async def test_initialize_creates_a2a_client(self, test_agent):
        """Verify initialize creates A2A client."""
        mock_transport = MagicMock()
        mock_client = MagicMock()
        test_agent.factory.create_slim_transport = MagicMock(return_value=mock_transport)
        test_agent.factory.create_a2a_client = MagicMock(return_value=mock_client)
        test_agent._use_openai = False

        await test_agent.initialize()

        test_agent.factory.create_a2a_client.assert_called_once()
        assert test_agent.client == mock_client

    @pytest.mark.asyncio
    async def test_initialize_handles_no_transport(self, test_agent):
        """Verify demo mode when transport not available."""
        test_agent.factory.create_slim_transport = MagicMock(return_value=None)
        test_agent._use_openai = False

        await test_agent.initialize()

        assert test_agent.transport is None
        assert test_agent.client is None

    @pytest.mark.asyncio
    async def test_initialize_with_openai(self, test_agent):
        """Verify OpenAI client initialization when enabled."""
        test_agent.factory.create_slim_transport = MagicMock(return_value=None)
        test_agent._use_openai = True

        mock_openai = MagicMock()
        mock_openai.initialize = AsyncMock(return_value=True)

        # Patch at the module where it's imported from
        with patch("shared.azure_openai.get_openai_client", return_value=mock_openai):
            await test_agent.initialize()
            assert test_agent.openai_client == mock_openai

    @pytest.mark.asyncio
    async def test_initialize_openai_fallback_on_failure(self, test_agent):
        """Verify fallback when OpenAI initialization fails."""
        test_agent.factory.create_slim_transport = MagicMock(return_value=None)
        test_agent._use_openai = True

        mock_openai = MagicMock()
        mock_openai.initialize = AsyncMock(return_value=False)

        with patch("shared.azure_openai.get_openai_client", return_value=mock_openai):
            await test_agent.initialize()
            assert test_agent.openai_client is None

    @pytest.mark.asyncio
    async def test_initialize_openai_import_error(self, test_agent):
        """Verify graceful handling of ImportError."""
        test_agent.factory.create_slim_transport = MagicMock(return_value=None)
        test_agent._use_openai = True

        # Patch the entire import to raise ImportError
        with patch.dict("sys.modules", {"shared.azure_openai": None}):
            # Should not raise, just log warning
            await test_agent.initialize()
            assert test_agent.openai_client is None


# =============================================================================
# Test: Message Handling
# =============================================================================


class TestMessageHandling:
    """Tests for message handling."""

    @pytest.mark.asyncio
    async def test_handle_message_increments_counter(
        self, test_agent, sample_a2a_message
    ):
        """Verify message counter is incremented."""
        test_agent.openai_client = None  # Use fallback mode

        with patch("shared.base_agent.extract_message_content", return_value={"text": "test"}):
            with patch("shared.base_agent.create_a2a_message", return_value={}):
                await test_agent.handle_message(sample_a2a_message)

        assert test_agent.messages_processed == 1

    @pytest.mark.asyncio
    async def test_handle_message_tracks_openai_calls(
        self, test_agent, sample_a2a_message
    ):
        """Verify OpenAI call counter when client available."""
        test_agent.openai_client = MagicMock()  # Enable OpenAI mode

        with patch("shared.base_agent.extract_message_content", return_value={"text": "test"}):
            with patch("shared.base_agent.create_a2a_message", return_value={}):
                await test_agent.handle_message(sample_a2a_message)

        assert test_agent.openai_calls == 1
        assert test_agent.fallback_calls == 0

    @pytest.mark.asyncio
    async def test_handle_message_tracks_fallback_calls(
        self, test_agent, sample_a2a_message
    ):
        """Verify fallback call counter when no OpenAI client."""
        test_agent.openai_client = None

        with patch("shared.base_agent.extract_message_content", return_value={"text": "test"}):
            with patch("shared.base_agent.create_a2a_message", return_value={}):
                await test_agent.handle_message(sample_a2a_message)

        assert test_agent.openai_calls == 0
        assert test_agent.fallback_calls == 1

    @pytest.mark.asyncio
    async def test_handle_message_preserves_context_id(
        self, test_agent, sample_a2a_message
    ):
        """Verify context ID is preserved."""
        test_agent.openai_client = None

        with patch("shared.base_agent.extract_message_content", return_value={"text": "test"}):
            with patch("shared.base_agent.create_a2a_message") as mock_create:
                mock_create.return_value = {}
                await test_agent.handle_message(sample_a2a_message)

                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["context_id"] == "ctx-12345"

    @pytest.mark.asyncio
    async def test_handle_message_generates_context_id_if_missing(self, test_agent):
        """Verify context ID is generated if not present."""
        message_without_context = {"parts": [{"text": "test"}]}
        test_agent.openai_client = None

        with patch("shared.base_agent.extract_message_content", return_value={"text": "test"}):
            with patch("shared.base_agent.create_a2a_message") as mock_create:
                with patch("shared.base_agent.generate_context_id", return_value="gen-ctx-123"):
                    mock_create.return_value = {}
                    await test_agent.handle_message(message_without_context)

                    call_kwargs = mock_create.call_args[1]
                    assert call_kwargs["context_id"] == "gen-ctx-123"

    @pytest.mark.asyncio
    async def test_handle_message_error_handling(self, test_agent, sample_a2a_message):
        """Verify error is handled gracefully."""
        test_agent.openai_client = None

        with patch(
            "shared.base_agent.extract_message_content",
            side_effect=Exception("Parse error"),
        ):
            with patch("shared.base_agent.create_a2a_message") as mock_create:
                mock_create.return_value = {"error": "Parse error"}
                result = await test_agent.handle_message(sample_a2a_message)

                # Should return error message, not raise
                assert result == {"error": "Parse error"}


# =============================================================================
# Test: Process Message (Abstract Method)
# =============================================================================


class TestProcessMessage:
    """Tests for process_message implementation."""

    @pytest.mark.asyncio
    async def test_process_message_returns_result(self, test_agent):
        """Verify process_message returns expected result."""
        content = {"text": "Hello"}
        message = {"contextId": "test"}

        result = await test_agent.process_message(content, message)

        assert result["processed"] is True
        assert result["input"] == content


# =============================================================================
# Test: Demo Messages (Abstract Method)
# =============================================================================


class TestDemoMessages:
    """Tests for get_demo_messages implementation."""

    def test_get_demo_messages_returns_list(self, test_agent):
        """Verify get_demo_messages returns list of messages."""
        messages = test_agent.get_demo_messages()

        assert isinstance(messages, list)
        assert len(messages) == 2

    def test_demo_messages_have_context_id(self, test_agent):
        """Verify demo messages have contextId."""
        messages = test_agent.get_demo_messages()

        for msg in messages:
            assert "contextId" in msg


# =============================================================================
# Test: Cleanup
# =============================================================================


class TestCleanup:
    """Tests for cleanup method."""

    def test_cleanup_logs_statistics(self, test_agent):
        """Verify cleanup logs message statistics."""
        test_agent.messages_processed = 10
        test_agent.openai_calls = 7
        test_agent.fallback_calls = 3

        with patch("shared.base_agent.shutdown_factory"):
            test_agent.cleanup()

        # Logger should have been called with statistics
        test_agent.logger.info.assert_called()

    def test_cleanup_stops_container(self, test_agent):
        """Verify cleanup stops container if running."""
        mock_container = MagicMock()
        test_agent.container = mock_container

        with patch("shared.base_agent.shutdown_factory"):
            test_agent.cleanup()

        mock_container.stop.assert_called_once()

    def test_cleanup_handles_container_stop_error(self, test_agent):
        """Verify cleanup handles container stop error gracefully."""
        mock_container = MagicMock()
        mock_container.stop.side_effect = Exception("Container error")
        test_agent.container = mock_container

        with patch("shared.base_agent.shutdown_factory"):
            # Should not raise
            test_agent.cleanup()

    def test_cleanup_reports_openai_usage(self, test_agent):
        """Verify cleanup reports OpenAI token usage."""
        mock_openai = MagicMock()
        mock_openai.get_total_usage.return_value = {
            "total_tokens": 1500,
            "total_cost": 0.05,
        }
        test_agent.openai_client = mock_openai

        with patch("shared.base_agent.shutdown_factory"):
            test_agent.cleanup()

        mock_openai.get_total_usage.assert_called_once()

    def test_cleanup_handles_openai_usage_error(self, test_agent):
        """Verify cleanup handles OpenAI usage error gracefully."""
        mock_openai = MagicMock()
        mock_openai.get_total_usage.side_effect = Exception("Usage error")
        test_agent.openai_client = mock_openai

        with patch("shared.base_agent.shutdown_factory"):
            # Should not raise
            test_agent.cleanup()

    def test_cleanup_calls_shutdown_factory(self, test_agent):
        """Verify cleanup calls shutdown_factory."""
        with patch("shared.base_agent.shutdown_factory") as mock_shutdown:
            test_agent.cleanup()

        mock_shutdown.assert_called_once()


# =============================================================================
# Test: Demo Mode
# =============================================================================


class TestDemoMode:
    """Tests for demo mode operation."""

    @pytest.mark.asyncio
    async def test_run_demo_mode_processes_messages(self, test_agent):
        """Verify demo mode processes sample messages."""
        test_agent.openai_client = None

        # Track calls to handle_message
        original_handle = test_agent.handle_message
        call_count = [0]

        async def tracked_handle(msg):
            call_count[0] += 1
            return await original_handle(msg)

        test_agent.handle_message = tracked_handle

        # Mock asyncio.sleep to be fast and cancel after messages processed
        sleep_count = [0]

        async def mock_sleep(duration):
            sleep_count[0] += 1
            # After demo messages processed, cancel the wait loop
            if sleep_count[0] > 3:
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch("shared.base_agent.extract_message_content", return_value={}):
                with patch("shared.base_agent.create_a2a_message", return_value={}):
                    try:
                        await test_agent.run_demo_mode()
                    except asyncio.CancelledError:
                        pass

        # Should have processed demo messages (2 in our test agent)
        assert call_count[0] >= 2


# =============================================================================
# Test: Abstract Method Enforcement
# =============================================================================


class TestAbstractMethodEnforcement:
    """Tests for abstract method enforcement."""

    def test_cannot_instantiate_base_agent_directly(self):
        """Verify BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            BaseAgent()

        assert "abstract" in str(exc_info.value).lower()

    def test_must_implement_process_message(self):
        """Verify subclass must implement process_message."""

        class IncompleteAgent(BaseAgent):
            agent_name = "incomplete"

            def get_demo_messages(self):
                return []

        with pytest.raises(TypeError):
            IncompleteAgent()

    def test_must_implement_get_demo_messages(self):
        """Verify subclass must implement get_demo_messages."""

        class IncompleteAgent(BaseAgent):
            agent_name = "incomplete"

            async def process_message(self, content, message):
                return {}

        with pytest.raises(TypeError):
            IncompleteAgent()


# =============================================================================
# Test: run_agent Function
# =============================================================================


class TestRunAgentFunction:
    """Tests for the run_agent convenience function."""

    def test_run_agent_creates_instance(self):
        """Verify run_agent creates agent and calls run."""
        with patch.object(ConcreteTestAgent, "run", new_callable=AsyncMock) as mock_run:
            with patch("asyncio.run") as mock_asyncio_run:
                # Capture the coroutine passed to asyncio.run
                def capture_coro(coro):
                    # The coroutine was created, we can verify agent was created
                    pass

                mock_asyncio_run.side_effect = capture_coro

                run_agent(ConcreteTestAgent)

                mock_asyncio_run.assert_called_once()


# =============================================================================
# Test: Statistics Tracking
# =============================================================================


class TestStatisticsTracking:
    """Tests for statistics tracking."""

    @pytest.mark.asyncio
    async def test_multiple_messages_increment_counter(self, test_agent):
        """Verify counter increments with each message."""
        test_agent.openai_client = None
        messages = [{"contextId": f"ctx-{i}", "parts": []} for i in range(5)]

        with patch("shared.base_agent.extract_message_content", return_value={}):
            with patch("shared.base_agent.create_a2a_message", return_value={}):
                for msg in messages:
                    await test_agent.handle_message(msg)

        assert test_agent.messages_processed == 5

    @pytest.mark.asyncio
    async def test_mixed_openai_and_fallback_tracking(self, test_agent):
        """Verify mixed OpenAI and fallback tracking."""
        test_agent.openai_client = MagicMock()
        messages = [{"contextId": f"ctx-{i}", "parts": []} for i in range(3)]

        with patch("shared.base_agent.extract_message_content", return_value={}):
            with patch("shared.base_agent.create_a2a_message", return_value={}):
                # Process with OpenAI
                for msg in messages:
                    await test_agent.handle_message(msg)

                # Switch to fallback
                test_agent.openai_client = None

                # Process with fallback
                for msg in messages:
                    await test_agent.handle_message(msg)

        assert test_agent.openai_calls == 3
        assert test_agent.fallback_calls == 3
        assert test_agent.messages_processed == 6


# =============================================================================
# Test: Configuration
# =============================================================================


class TestConfiguration:
    """Tests for agent configuration."""

    def test_config_from_load_config(self):
        """Verify config is loaded."""
        agent = ConcreteTestAgent()
        assert agent.config is not None

    def test_logger_is_created(self):
        """Verify logger is created."""
        agent = ConcreteTestAgent()
        assert agent.logger is not None

    def test_use_openai_default(self):
        """Verify _use_openai defaults from environment."""
        with patch.dict("os.environ", {"USE_AZURE_OPENAI": "false"}):
            with patch("shared.base_agent.load_config", return_value={}):
                with patch("shared.base_agent.setup_logging") as mock_logging:
                    mock_logging.return_value = MagicMock()
                    with patch("shared.base_agent.get_factory") as mock_factory:
                        mock_factory.return_value = MagicMock()
                        agent = ConcreteTestAgent()
                        assert agent._use_openai is False


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_message_handling(self, test_agent):
        """Verify empty message is handled."""
        empty_message = {}
        test_agent.openai_client = None

        with patch("shared.base_agent.extract_message_content", return_value={}):
            with patch("shared.base_agent.create_a2a_message", return_value={}):
                with patch("shared.base_agent.generate_context_id", return_value="gen-ctx"):
                    result = await test_agent.handle_message(empty_message)
                    # Should not raise, just return result
                    assert result is not None

    @pytest.mark.asyncio
    async def test_none_content_from_extraction(self, test_agent):
        """Verify handling of None content from extraction."""
        test_agent.openai_client = None

        with patch("shared.base_agent.extract_message_content", return_value=None):
            with patch("shared.base_agent.create_a2a_message", return_value={}):
                result = await test_agent.handle_message({"contextId": "test"})
                assert result is not None

    def test_agent_name_and_topic_class_attributes(self):
        """Verify class attributes are properly inherited."""
        assert ConcreteTestAgent.agent_name == "test-agent"
        assert ConcreteTestAgent.default_topic == "test-topic"
