"""
Unit tests for shared/utils.py
Tests logging, configuration, and helper functions
"""

import pytest
import logging
import os
from pathlib import Path

from shared.utils import (
    setup_logging,
    load_config,
    get_env_or_raise,
    get_env_or_default,
    validate_topic_name,
    get_project_root,
    format_agent_name,
    handle_graceful_shutdown,
    AgentError,
    ConfigurationError,
    CommunicationError,
    ExternalServiceError
)


class TestLogging:
    """Tests for logging setup."""

    def test_setup_logging_creates_logger(self):
        """Test that setup_logging creates a logger."""
        logger = setup_logging("test-agent", level="DEBUG")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test-agent"
        assert logger.level == logging.DEBUG

    def test_setup_logging_info_level(self):
        """Test INFO level logging."""
        logger = setup_logging("test-info", level="INFO")
        assert logger.level == logging.INFO

    def test_setup_logging_custom_format(self):
        """Test custom format string."""
        logger = setup_logging(
            "test-custom",
            format_string="%(name)s - %(message)s"
        )
        assert logger is not None


class TestConfiguration:
    """Tests for configuration loading."""

    def test_load_config_returns_dict(self):
        """Test that load_config returns a dictionary."""
        config = load_config()
        assert isinstance(config, dict)

    def test_load_config_has_required_keys(self):
        """Test that config has all required keys."""
        config = load_config()
        required_keys = [
            "slim_endpoint",
            "slim_password",
            "nats_endpoint",
            "otlp_endpoint",
            "enable_tracing",
            "agent_topic",
            "log_level",
            "shopify_url",
            "zendesk_url",
            "mailchimp_url",
            "google_analytics_url"
        ]
        for key in required_keys:
            assert key in config, f"Missing config key: {key}"

    def test_load_config_default_values(self):
        """Test default configuration values."""
        config = load_config()
        assert config["slim_endpoint"] == "http://slim:46357"
        assert config["nats_endpoint"] == "nats://nats:4222"
        assert config["log_level"] == "INFO"

    def test_load_config_with_env_override(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("AGENT_TOPIC", "custom-agent")

        config = load_config()
        assert config["log_level"] == "DEBUG"
        assert config["agent_topic"] == "custom-agent"


class TestEnvironmentVariables:
    """Tests for environment variable helpers."""

    def test_get_env_or_raise_success(self, monkeypatch):
        """Test getting existing environment variable."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        value = get_env_or_raise("TEST_VAR")
        assert value == "test_value"

    def test_get_env_or_raise_missing_raises(self):
        """Test that missing env var raises ValueError."""
        with pytest.raises(ValueError, match="Required environment variable"):
            get_env_or_raise("NONEXISTENT_VAR_12345")

    def test_get_env_or_default_with_value(self, monkeypatch):
        """Test getting env var with default when value exists."""
        monkeypatch.setenv("TEST_DEFAULT", "actual_value")
        value = get_env_or_default("TEST_DEFAULT", "default_value")
        assert value == "actual_value"

    def test_get_env_or_default_returns_default(self):
        """Test that default is returned when env var missing."""
        value = get_env_or_default("NONEXISTENT_VAR_67890", "my_default")
        assert value == "my_default"


class TestTopicValidation:
    """Tests for topic name validation."""

    def test_validate_topic_valid_names(self):
        """Test valid topic names."""
        valid_topics = [
            "intent-classifier",
            "knowledge-retrieval",
            "response-generator-en",
            "agent123",
            "my-agent-v2"
        ]
        for topic in valid_topics:
            assert validate_topic_name(topic), f"Should be valid: {topic}"

    def test_validate_topic_invalid_names(self):
        """Test invalid topic names."""
        invalid_topics = [
            "Intent Classifier",  # Spaces
            "agent_name",  # Underscores
            "AGENT",  # Uppercase
            "ab",  # Too short
            "a" * 51,  # Too long
            "agent!",  # Special chars
            "-agent",  # Starts with hyphen
            "agent-",  # Ends with hyphen
        ]
        for topic in invalid_topics:
            assert not validate_topic_name(topic), f"Should be invalid: {topic}"


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_project_root_returns_path(self):
        """Test that get_project_root returns a Path."""
        root = get_project_root()
        assert isinstance(root, Path)

    def test_get_project_root_exists(self):
        """Test that project root directory exists."""
        root = get_project_root()
        assert root.exists()

    def test_get_project_root_has_shared(self):
        """Test that project root contains shared directory."""
        root = get_project_root()
        shared_dir = root / "shared"
        assert shared_dir.exists()


class TestAgentNameFormatting:
    """Tests for agent name formatting."""

    def test_format_agent_name_simple(self):
        """Test formatting simple agent names."""
        assert format_agent_name("intent-classifier") == "Intent Classifier"
        assert format_agent_name("knowledge-retrieval") == "Knowledge Retrieval"

    def test_format_agent_name_multi_part(self):
        """Test formatting complex agent names."""
        assert format_agent_name("response-generator-en") == "Response Generator En"
        assert format_agent_name("my-agent-v2") == "My Agent V2"


class TestGracefulShutdown:
    """Tests for graceful shutdown handling."""

    def test_graceful_shutdown_registers_handlers(self, sample_logger):
        """Test that graceful shutdown registers signal handlers."""
        import signal

        # Store original handlers
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)

        try:
            handle_graceful_shutdown(sample_logger)

            # Handlers should be registered
            assert signal.getsignal(signal.SIGTERM) != original_sigterm
            assert signal.getsignal(signal.SIGINT) != original_sigint

        finally:
            # Restore original handlers
            signal.signal(signal.SIGTERM, original_sigterm)
            signal.signal(signal.SIGINT, original_sigint)

    def test_graceful_shutdown_with_cleanup_callback(self, sample_logger):
        """Test graceful shutdown calls cleanup callback."""
        import signal

        cleanup_called = []

        def cleanup():
            cleanup_called.append(True)

        # Store original handler
        original_sigterm = signal.getsignal(signal.SIGTERM)

        try:
            handle_graceful_shutdown(sample_logger, cleanup_callback=cleanup)

            # Get the registered handler
            handler = signal.getsignal(signal.SIGTERM)

            # Simulate signal (handler will exit, catch it)
            try:
                handler(signal.SIGTERM, None)
            except SystemExit:
                pass  # Expected

            # Cleanup should have been called
            assert len(cleanup_called) > 0

        finally:
            signal.signal(signal.SIGTERM, original_sigterm)

    def test_graceful_shutdown_handles_cleanup_error(self, sample_logger):
        """Test graceful shutdown handles errors in cleanup callback."""
        import signal

        def failing_cleanup():
            raise ValueError("Cleanup failed")

        original_sigterm = signal.getsignal(signal.SIGTERM)

        try:
            handle_graceful_shutdown(sample_logger, cleanup_callback=failing_cleanup)

            handler = signal.getsignal(signal.SIGTERM)

            # Should not raise, even if cleanup fails
            try:
                handler(signal.SIGTERM, None)
            except SystemExit:
                pass  # Expected
            except ValueError:
                pytest.fail("Cleanup error should be caught")

        finally:
            signal.signal(signal.SIGTERM, original_sigterm)


class TestCustomExceptions:
    """Tests for custom exception hierarchy."""

    def test_agent_error_base_class(self):
        """Test AgentError base exception."""
        error = AgentError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        error = ConfigurationError("Invalid config")
        assert isinstance(error, AgentError)
        assert str(error) == "Invalid config"

    def test_communication_error(self):
        """Test CommunicationError exception."""
        error = CommunicationError("Connection failed")
        assert isinstance(error, AgentError)

    def test_external_service_error(self):
        """Test ExternalServiceError exception."""
        error = ExternalServiceError("API call failed")
        assert isinstance(error, AgentError)

    def test_exception_inheritance(self):
        """Test that all custom exceptions inherit from AgentError."""
        assert issubclass(ConfigurationError, AgentError)
        assert issubclass(CommunicationError, AgentError)
        assert issubclass(ExternalServiceError, AgentError)
