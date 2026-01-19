"""
AGNTCY Factory Singleton for Multi-Agent Customer Service Platform

Provides centralized access to AGNTCY SDK components:
- Factory for creating clients, transports, and protocols
- Singleton pattern ensures consistent configuration across agents
- Handles initialization and cleanup of SDK resources

Phase 1: Local development with SLIM transport
Phase 4+: Production with Azure-specific configurations
"""

import os
import logging
from typing import Optional, Dict, Any
from threading import Lock

# AGNTCY SDK imports
try:
    from agntcy_app_sdk.factory import AgntcyFactory as SDK_Factory
    from agntcy_app_sdk.transports import SlimTransport, NatsTransport
    from agntcy_app_sdk.protocols import A2AProtocol, MCPProtocol
    AGNTCY_SDK_AVAILABLE = True
except ImportError:
    AGNTCY_SDK_AVAILABLE = False
    # Fallback for testing without SDK
    SDK_Factory = None
    SlimTransport = None
    NatsTransport = None
    A2AProtocol = None
    MCPProtocol = None


logger = logging.getLogger(__name__)


# =============================================================================
# Singleton Factory Instance
# =============================================================================

class AgntcyFactorySingleton:
    """
    Thread-safe singleton wrapper for AGNTCY SDK Factory.

    Ensures only one factory instance exists across all agents in the application.
    This prevents duplicate transport connections and inconsistent configurations.

    Usage:
        factory = get_factory()
        transport = factory.create_slim_transport()
        client = factory.create_a2a_client("my-agent", transport)
    """

    _instance: Optional['AgntcyFactorySingleton'] = None
    _lock: Lock = Lock()
    _initialized: bool = False

    def __new__(cls):
        """Thread-safe singleton instantiation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize factory with configuration from environment."""
        # Only initialize once
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            logger.info("Initializing AGNTCY Factory singleton...")

            # Check if SDK is available
            if not AGNTCY_SDK_AVAILABLE:
                logger.warning(
                    "AGNTCY SDK not installed. Factory will operate in mock mode. "
                    "Install with: pip install agntcy-app-sdk"
                )
                self._sdk_factory = None
                self._initialized = True
                return

            # Load configuration from environment
            self._config = self._load_config()

            # Create SDK factory instance
            try:
                self._sdk_factory = SDK_Factory(
                    name="CustomerServiceFactory",
                    enable_tracing=self._config["enable_tracing"],
                    log_level=self._config["log_level"]
                )
                logger.info(
                    f"AGNTCY Factory initialized successfully. "
                    f"Tracing: {self._config['enable_tracing']}, "
                    f"Log Level: {self._config['log_level']}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize AGNTCY Factory: {e}", exc_info=True)
                raise

            self._initialized = True

    def _load_config(self) -> Dict[str, Any]:
        """Load factory configuration from environment variables."""
        return {
            # Observability
            "enable_tracing": os.getenv("AGNTCY_ENABLE_TRACING", "true").lower() == "true",
            "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
            "otlp_endpoint": os.getenv("OTLP_HTTP_ENDPOINT", "http://otel-collector:4318"),

            # Transport endpoints
            "slim_endpoint": os.getenv("SLIM_ENDPOINT", "http://slim:46357"),
            "slim_password": os.getenv("SLIM_GATEWAY_PASSWORD", "changeme_local_dev_password"),
            "nats_endpoint": os.getenv("NATS_ENDPOINT", "nats://nats:4222"),
        }

    @property
    def sdk_factory(self) -> Optional[Any]:
        """
        Access underlying AGNTCY SDK factory.

        Returns None if SDK not available (testing mode).
        """
        return self._sdk_factory

    @property
    def config(self) -> Dict[str, Any]:
        """Get factory configuration."""
        return self._config

    # =========================================================================
    # Transport Creation Methods
    # =========================================================================

    def create_slim_transport(
        self,
        name: str = "slim-transport",
        **kwargs
    ):
        """
        Create SLIM transport for secure low-latency messaging.

        SLIM is the recommended transport for production deployments.
        Provides gateway authentication and TLS support.

        Args:
            name: Transport instance name
            **kwargs: Additional SLIM-specific configuration

        Returns:
            Configured SLIM transport instance

        Example:
            transport = factory.create_slim_transport(name="intent-classifier-slim")
        """
        if not self._sdk_factory:
            logger.warning("SDK not available - returning None transport")
            return None

        endpoint = kwargs.pop("endpoint", self._config["slim_endpoint"])
        gateway_password = kwargs.pop("gateway_password", self._config["slim_password"])

        logger.debug(f"Creating SLIM transport: {name} -> {endpoint}")

        try:
            return self._sdk_factory.create_transport(
                transport="SLIM",
                endpoint=endpoint,
                name=name,
                gateway_password=gateway_password,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create SLIM transport: {e}", exc_info=True)
            raise

    def create_nats_transport(
        self,
        name: str = "nats-transport",
        **kwargs
    ):
        """
        Create NATS transport for high-throughput messaging.

        NATS is ideal for high-volume scenarios like analytics collection.
        Supports clustering and advanced pub-sub patterns.

        Args:
            name: Transport instance name
            **kwargs: Additional NATS-specific configuration

        Returns:
            Configured NATS transport instance

        Example:
            transport = factory.create_nats_transport(name="analytics-nats")
        """
        if not self._sdk_factory:
            logger.warning("SDK not available - returning None transport")
            return None

        endpoint = kwargs.pop("endpoint", self._config["nats_endpoint"])

        logger.debug(f"Creating NATS transport: {name} -> {endpoint}")

        try:
            return self._sdk_factory.create_transport(
                transport="NATS",
                endpoint=endpoint,
                name=name,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create NATS transport: {e}", exc_info=True)
            raise

    # =========================================================================
    # Client Creation Methods
    # =========================================================================

    def create_a2a_client(
        self,
        agent_topic: str,
        transport,
        **kwargs
    ):
        """
        Create A2A (Agent-to-Agent) protocol client.

        Use A2A for custom agent logic and direct peer-to-peer communication.
        Ideal for intent classification, response generation, escalation decisions.

        Args:
            agent_topic: Agent's topic name (must be unique)
            transport: Transport instance (SLIM or NATS)
            **kwargs: Additional A2A-specific configuration

        Returns:
            Configured A2A client instance

        Example:
            transport = factory.create_slim_transport()
            client = factory.create_a2a_client(
                agent_topic="intent-classifier",
                transport=transport
            )
        """
        if not self._sdk_factory:
            logger.warning("SDK not available - returning None client")
            return None

        logger.debug(f"Creating A2A client for topic: {agent_topic}")

        try:
            return self._sdk_factory.create_client(
                protocol="A2A",
                agent_topic=agent_topic,
                transport=transport,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create A2A client for {agent_topic}: {e}", exc_info=True)
            raise

    def create_mcp_client(
        self,
        agent_topic: str,
        transport,
        **kwargs
    ):
        """
        Create MCP (Model Context Protocol) client.

        Use MCP for standardized tool interfaces and external service integrations.
        Ideal for knowledge retrieval agents accessing search APIs.

        Args:
            agent_topic: Agent's topic name (must be unique)
            transport: Transport instance (SLIM or NATS)
            **kwargs: Additional MCP-specific configuration

        Returns:
            Configured MCP client instance

        Example:
            transport = factory.create_slim_transport()
            client = factory.create_mcp_client(
                agent_topic="knowledge-retrieval",
                transport=transport
            )
        """
        if not self._sdk_factory:
            logger.warning("SDK not available - returning None client")
            return None

        logger.debug(f"Creating MCP client for topic: {agent_topic}")

        try:
            return self._sdk_factory.create_client(
                protocol="MCP",
                agent_topic=agent_topic,
                transport=transport,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create MCP client for {agent_topic}: {e}", exc_info=True)
            raise

    # =========================================================================
    # App Session Management
    # =========================================================================

    def create_app_session(self, max_sessions: int = 10):
        """
        Create AppSession for managing multiple agent containers.

        AppSession handles lifecycle management for multiple concurrent
        customer conversations, each with its own agent instances.

        Args:
            max_sessions: Maximum number of concurrent sessions

        Returns:
            AppSession instance

        Example:
            session = factory.create_app_session(max_sessions=100)
            session.add_app_container(session_id, container)
            session.start_all_sessions()
        """
        if not self._sdk_factory:
            logger.warning("SDK not available - returning None session")
            return None

        logger.debug(f"Creating AppSession with max_sessions={max_sessions}")

        try:
            return self._sdk_factory.create_app_session(max_sessions=max_sessions)
        except Exception as e:
            logger.error(f"Failed to create AppSession: {e}", exc_info=True)
            raise

    # =========================================================================
    # Protocol and Transport Information
    # =========================================================================

    def registered_protocols(self):
        """Get list of registered protocol types."""
        if not self._sdk_factory:
            return []
        return self._sdk_factory.registered_protocols()

    def registered_transports(self):
        """Get list of registered transport types."""
        if not self._sdk_factory:
            return []
        return self._sdk_factory.registered_transports()

    # =========================================================================
    # Cleanup
    # =========================================================================

    def shutdown(self):
        """
        Shutdown factory and cleanup resources.

        Should be called on application exit to properly close connections
        and flush telemetry data.
        """
        if not self._initialized:
            return

        logger.info("Shutting down AGNTCY Factory...")

        # SDK factory cleanup (if needed)
        # Note: Individual transports and clients should be cleaned up by agents

        self._initialized = False
        logger.info("AGNTCY Factory shutdown complete")


# =============================================================================
# Module-Level Functions (Preferred API)
# =============================================================================

def get_factory() -> AgntcyFactorySingleton:
    """
    Get the singleton AGNTCY Factory instance.

    This is the preferred way to access the factory across all agents.

    Returns:
        AgntcyFactorySingleton instance

    Example:
        from shared import get_factory

        factory = get_factory()
        transport = factory.create_slim_transport()
        client = factory.create_a2a_client("my-agent", transport)
    """
    return AgntcyFactorySingleton()


def shutdown_factory():
    """
    Shutdown the singleton factory and cleanup resources.

    Call this during application shutdown to ensure proper cleanup.

    Example:
        from shared import shutdown_factory
        import atexit

        atexit.register(shutdown_factory)
    """
    factory = AgntcyFactorySingleton()
    factory.shutdown()


# =============================================================================
# Initialization Message
# =============================================================================

# Log factory availability on module import
if AGNTCY_SDK_AVAILABLE:
    logger.info("AGNTCY SDK factory module loaded successfully")
else:
    logger.warning(
        "AGNTCY SDK not available. Install with: pip install agntcy-app-sdk"
    )
