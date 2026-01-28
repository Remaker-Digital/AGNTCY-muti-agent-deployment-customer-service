"""
Shared utility functions for AGNTCY Multi-Agent Customer Service Platform
Provides logging, configuration, and error handling helpers
"""

import logging
import os
import signal
import sys
from typing import Any, Dict, Optional
from pathlib import Path


def setup_logging(
    name: str, level: str = "INFO", format_string: Optional[str] = None
) -> logging.Logger:
    """
    Configure structured logging for an agent or service.

    Args:
        name: Logger name (typically agent or service name)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (optional)

    Returns:
        Configured logger instance

    Example:
        logger = setup_logging("intent-classifier", level="DEBUG")
        logger.info("Agent started", extra={"agent": "intent-classifier"})
    """
    # Default format includes timestamp, level, name, and message
    if format_string is None:
        format_string = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level, format=format_string, datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Create and return named logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    return logger


def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Returns a dictionary with common configuration values needed by agents.
    This centralizes environment variable access for consistency.

    Returns:
        Dictionary with configuration values

    Example config structure:
        {
            "slim_endpoint": "http://slim:46357",
            "slim_password": "secret",
            "otlp_endpoint": "http://otel-collector:4318",
            "enable_tracing": True,
            "log_level": "INFO",
            "agent_topic": "my-agent"
        }
    """
    return {
        # AGNTCY SDK configuration
        "slim_endpoint": os.getenv("SLIM_ENDPOINT", "http://slim:46357"),
        "slim_password": os.getenv(
            "SLIM_GATEWAY_PASSWORD", "changeme_local_dev_password"
        ),
        "nats_endpoint": os.getenv("NATS_ENDPOINT", "nats://nats:4222"),
        # Observability configuration
        "otlp_endpoint": os.getenv("OTLP_HTTP_ENDPOINT", "http://otel-collector:4318"),
        "enable_tracing": os.getenv("AGNTCY_ENABLE_TRACING", "true").lower() == "true",
        # Agent configuration
        "agent_topic": os.getenv("AGENT_TOPIC", "default-agent"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        # External service endpoints (for mock APIs in Phase 1)
        "shopify_url": os.getenv("SHOPIFY_URL", "http://mock-shopify:8000"),
        "zendesk_url": os.getenv("ZENDESK_URL", "http://mock-zendesk:8000"),
        "mailchimp_url": os.getenv("MAILCHIMP_URL", "http://mock-mailchimp:8000"),
        "google_analytics_url": os.getenv(
            "GOOGLE_ANALYTICS_URL", "http://mock-google-analytics:8000"
        ),
    }


def get_env_or_raise(key: str) -> str:
    """
    Get environment variable or raise descriptive error.

    Use this for required configuration values that have no sensible default.

    Args:
        key: Environment variable name

    Returns:
        Environment variable value

    Raises:
        ValueError: If environment variable is not set

    Example:
        api_key = get_env_or_raise("OPENAI_API_KEY")
    """
    value = os.getenv(key)
    if value is None:
        raise ValueError(
            f"Required environment variable '{key}' is not set. "
            f"Please set it in your .env file or environment."
        )
    return value


def get_env_or_default(key: str, default: str) -> str:
    """
    Get environment variable with a default fallback.

    Use this for optional configuration values.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Environment variable value or default

    Example:
        timeout = int(get_env_or_default("REQUEST_TIMEOUT", "30"))
    """
    return os.getenv(key, default)


def handle_graceful_shutdown(
    logger: logging.Logger, cleanup_callback: Optional[callable] = None
) -> None:
    """
    Set up graceful shutdown handlers for SIGTERM and SIGINT.

    This ensures agents can clean up resources (close connections, flush logs)
    before terminating. Critical for Docker container lifecycle management.

    Args:
        logger: Logger instance for shutdown messages
        cleanup_callback: Optional function to call before exit (e.g., close connections)

    Example:
        def cleanup():
            container.stop()
            logger.info("Agent stopped cleanly")

        handle_graceful_shutdown(logger, cleanup)
    """

    def signal_handler(sig, frame):
        signal_name = "SIGTERM" if sig == signal.SIGTERM else "SIGINT"
        logger.info(f"Received {signal_name}, initiating graceful shutdown...")

        # Call user-provided cleanup if available
        if cleanup_callback:
            try:
                cleanup_callback()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}", exc_info=True)

        logger.info("Shutdown complete")
        sys.exit(0)

    # Register handlers for both SIGTERM (Docker stop) and SIGINT (Ctrl+C)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.debug("Graceful shutdown handlers registered")


def validate_topic_name(topic: str) -> bool:
    """
    Validate AGNTCY topic name follows conventions.

    Topic names should be:
    - Lowercase with hyphens
    - No spaces or special characters
    - Descriptive and unique

    Args:
        topic: Topic name to validate

    Returns:
        True if valid, False otherwise

    Example:
        assert validate_topic_name("intent-classifier") == True
        assert validate_topic_name("Intent Classifier!") == False
    """
    import re

    # Topic must be lowercase alphanumeric with hyphens only
    pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"

    if not re.match(pattern, topic):
        return False

    # Topic should be between 3 and 50 characters
    if len(topic) < 3 or len(topic) > 50:
        return False

    return True


def get_project_root() -> Path:
    """
    Get the project root directory path.

    Useful for locating test data, configuration files, etc.

    Returns:
        Path to project root directory

    Example:
        root = get_project_root()
        test_data = root / "test-data" / "shopify" / "products.json"
    """
    # Assuming this file is in shared/, project root is one level up
    return Path(__file__).parent.parent


def format_agent_name(topic: str) -> str:
    """
    Convert topic name to human-readable agent name.

    Args:
        topic: Agent topic (e.g., "intent-classifier")

    Returns:
        Formatted name (e.g., "Intent Classifier")

    Example:
        name = format_agent_name("response-generator-en")
        # Returns: "Response Generator En"
    """
    return topic.replace("-", " ").title()


# Phase 1: Simple error handling
# Phase 2+: Can be extended with retry logic, circuit breakers, etc.
class AgentError(Exception):
    """Base exception for agent-related errors."""

    pass


class ConfigurationError(AgentError):
    """Raised when configuration is invalid or missing."""

    pass


class CommunicationError(AgentError):
    """Raised when inter-agent communication fails."""

    pass


class ExternalServiceError(AgentError):
    """Raised when external API calls fail (Shopify, Zendesk, etc.)."""

    pass
