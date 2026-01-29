"""
Unit tests for AGNTCY Factory Singleton.

Tests the factory module functionality:
- Singleton pattern
- Configuration loading
- Transport creation (SLIM, NATS)
- Client creation (A2A, MCP)
- App session management
- Shutdown and cleanup

Target: 85%+ coverage for shared/factory.py
"""

import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

import shared.factory as factory_module
from shared.factory import (
    AgntcyFactorySingleton,
    get_factory,
    shutdown_factory,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton state before each test."""
    # Store original state
    original_instance = AgntcyFactorySingleton._instance
    original_initialized = AgntcyFactorySingleton._initialized

    # Reset singleton
    AgntcyFactorySingleton._instance = None
    AgntcyFactorySingleton._initialized = False

    yield

    # Restore original state
    AgntcyFactorySingleton._instance = original_instance
    AgntcyFactorySingleton._initialized = original_initialized


@pytest.fixture
def mock_sdk_available():
    """Mock SDK availability to True."""
    with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
        yield


@pytest.fixture
def mock_sdk_unavailable():
    """Mock SDK availability to False."""
    with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", False):
        yield


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestSingletonPattern:
    """Tests for singleton pattern implementation."""

    def test_singleton_returns_same_instance(self, mock_sdk_unavailable):
        """Verify singleton returns same instance."""
        factory1 = AgntcyFactorySingleton()
        factory2 = AgntcyFactorySingleton()

        assert factory1 is factory2

    def test_singleton_thread_safe(self, mock_sdk_unavailable):
        """Verify singleton is thread-safe."""
        import threading

        instances = []

        def create_instance():
            instances.append(AgntcyFactorySingleton())

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same
        assert len(set(id(i) for i in instances)) == 1


# ============================================================================
# Initialization Tests (SDK Not Available)
# ============================================================================


class TestInitializationNoSDK:
    """Tests for initialization when SDK is not available."""

    def test_init_without_sdk(self, mock_sdk_unavailable):
        """Verify initialization without SDK sets mock mode."""
        factory = AgntcyFactorySingleton()

        assert factory._initialized is True
        assert factory._sdk_factory is None

    def test_sdk_factory_property_none_without_sdk(self, mock_sdk_unavailable):
        """Verify sdk_factory property returns None without SDK."""
        factory = AgntcyFactorySingleton()

        assert factory.sdk_factory is None

    def test_only_initializes_once(self, mock_sdk_unavailable):
        """Verify initialization only happens once."""
        factory = AgntcyFactorySingleton()
        factory._initialized = True

        # Second call should not re-initialize
        factory2 = AgntcyFactorySingleton()

        assert factory is factory2


# ============================================================================
# Initialization Tests (SDK Available)
# ============================================================================


class TestInitializationWithSDK:
    """Tests for initialization when SDK is available."""

    def test_init_with_sdk_success(self):
        """Verify initialization with SDK creates factory."""
        mock_sdk_factory = MagicMock()

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                assert factory._initialized is True
                assert factory._sdk_factory is mock_sdk_factory

    def test_init_with_sdk_exception(self):
        """Verify initialization handles SDK exceptions."""
        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", side_effect=Exception("SDK error")):
                with pytest.raises(Exception, match="SDK error"):
                    AgntcyFactorySingleton()


# ============================================================================
# Configuration Tests
# ============================================================================


class TestConfiguration:
    """Tests for configuration loading."""

    def test_load_config_defaults(self):
        """Verify default configuration values."""
        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=MagicMock()):
                with patch.dict(os.environ, {}, clear=True):
                    factory = AgntcyFactorySingleton()

                    config = factory.config
                    assert config["enable_tracing"] is True
                    assert config["log_level"] == "INFO"
                    assert config["slim_endpoint"] == "http://slim:46357"
                    assert config["nats_endpoint"] == "nats://nats:4222"

    def test_load_config_from_environment(self):
        """Verify configuration from environment variables."""
        env_vars = {
            "AGNTCY_ENABLE_TRACING": "false",
            "LOG_LEVEL": "debug",
            "OTLP_HTTP_ENDPOINT": "http://custom-otel:4318",
            "SLIM_ENDPOINT": "http://custom-slim:8080",
            "SLIM_GATEWAY_PASSWORD": "custom-password",
            "NATS_ENDPOINT": "nats://custom-nats:4222",
        }

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=MagicMock()):
                with patch.dict(os.environ, env_vars, clear=False):
                    factory = AgntcyFactorySingleton()

                    config = factory.config
                    assert config["enable_tracing"] is False
                    assert config["log_level"] == "DEBUG"
                    assert config["slim_endpoint"] == "http://custom-slim:8080"
                    assert config["slim_password"] == "custom-password"
                    assert config["nats_endpoint"] == "nats://custom-nats:4222"


# ============================================================================
# Transport Creation Tests (No SDK)
# ============================================================================


class TestTransportCreationNoSDK:
    """Tests for transport creation without SDK."""

    def test_create_slim_transport_no_sdk(self, mock_sdk_unavailable):
        """Verify SLIM transport returns None without SDK."""
        factory = AgntcyFactorySingleton()

        result = factory.create_slim_transport()

        assert result is None

    def test_create_nats_transport_no_sdk(self, mock_sdk_unavailable):
        """Verify NATS transport returns None without SDK."""
        factory = AgntcyFactorySingleton()

        result = factory.create_nats_transport()

        assert result is None


# ============================================================================
# Transport Creation Tests (With SDK)
# ============================================================================


class TestTransportCreationWithSDK:
    """Tests for transport creation with SDK."""

    def test_create_slim_transport_success(self):
        """Verify SLIM transport creation."""
        mock_sdk_factory = MagicMock()
        mock_transport = MagicMock()
        mock_sdk_factory.create_transport.return_value = mock_transport

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                result = factory.create_slim_transport(name="test-slim")

                assert result is mock_transport
                mock_sdk_factory.create_transport.assert_called_once()
                call_kwargs = mock_sdk_factory.create_transport.call_args[1]
                assert call_kwargs["transport"] == "SLIM"
                assert call_kwargs["name"] == "test-slim"

    def test_create_slim_transport_custom_endpoint(self):
        """Verify SLIM transport with custom endpoint."""
        mock_sdk_factory = MagicMock()

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                factory.create_slim_transport(
                    name="custom",
                    endpoint="http://custom:8080",
                    gateway_password="custom-pass",
                )

                call_kwargs = mock_sdk_factory.create_transport.call_args[1]
                assert call_kwargs["endpoint"] == "http://custom:8080"
                assert call_kwargs["gateway_password"] == "custom-pass"

    def test_create_slim_transport_exception(self):
        """Verify SLIM transport exception handling."""
        mock_sdk_factory = MagicMock()
        mock_sdk_factory.create_transport.side_effect = Exception("Transport error")

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                with pytest.raises(Exception, match="Transport error"):
                    factory.create_slim_transport()

    def test_create_nats_transport_success(self):
        """Verify NATS transport creation."""
        mock_sdk_factory = MagicMock()
        mock_transport = MagicMock()
        mock_sdk_factory.create_transport.return_value = mock_transport

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                result = factory.create_nats_transport(name="test-nats")

                assert result is mock_transport
                call_kwargs = mock_sdk_factory.create_transport.call_args[1]
                assert call_kwargs["transport"] == "NATS"

    def test_create_nats_transport_exception(self):
        """Verify NATS transport exception handling."""
        mock_sdk_factory = MagicMock()
        mock_sdk_factory.create_transport.side_effect = Exception("NATS error")

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                with pytest.raises(Exception, match="NATS error"):
                    factory.create_nats_transport()


# ============================================================================
# Client Creation Tests (No SDK)
# ============================================================================


class TestClientCreationNoSDK:
    """Tests for client creation without SDK."""

    def test_create_a2a_client_no_sdk(self, mock_sdk_unavailable):
        """Verify A2A client returns None without SDK."""
        factory = AgntcyFactorySingleton()

        result = factory.create_a2a_client("test-topic", MagicMock())

        assert result is None

    def test_create_mcp_client_no_sdk(self, mock_sdk_unavailable):
        """Verify MCP client returns None without SDK."""
        factory = AgntcyFactorySingleton()

        result = factory.create_mcp_client("test-topic", MagicMock())

        assert result is None


# ============================================================================
# Client Creation Tests (With SDK)
# ============================================================================


class TestClientCreationWithSDK:
    """Tests for client creation with SDK."""

    def test_create_a2a_client_success(self):
        """Verify A2A client creation."""
        mock_sdk_factory = MagicMock()
        mock_client = MagicMock()
        mock_sdk_factory.create_client.return_value = mock_client
        mock_transport = MagicMock()

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                result = factory.create_a2a_client("intent-classifier", mock_transport)

                assert result is mock_client
                call_kwargs = mock_sdk_factory.create_client.call_args[1]
                assert call_kwargs["protocol"] == "A2A"
                assert call_kwargs["agent_topic"] == "intent-classifier"
                assert call_kwargs["transport"] is mock_transport

    def test_create_a2a_client_exception(self):
        """Verify A2A client exception handling."""
        mock_sdk_factory = MagicMock()
        mock_sdk_factory.create_client.side_effect = Exception("Client error")

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                with pytest.raises(Exception, match="Client error"):
                    factory.create_a2a_client("test", MagicMock())

    def test_create_mcp_client_success(self):
        """Verify MCP client creation."""
        mock_sdk_factory = MagicMock()
        mock_client = MagicMock()
        mock_sdk_factory.create_client.return_value = mock_client
        mock_transport = MagicMock()

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                result = factory.create_mcp_client("knowledge-retrieval", mock_transport)

                assert result is mock_client
                call_kwargs = mock_sdk_factory.create_client.call_args[1]
                assert call_kwargs["protocol"] == "MCP"

    def test_create_mcp_client_exception(self):
        """Verify MCP client exception handling."""
        mock_sdk_factory = MagicMock()
        mock_sdk_factory.create_client.side_effect = Exception("MCP error")

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                with pytest.raises(Exception, match="MCP error"):
                    factory.create_mcp_client("test", MagicMock())


# ============================================================================
# App Session Tests
# ============================================================================


class TestAppSession:
    """Tests for app session creation."""

    def test_create_app_session_no_sdk(self, mock_sdk_unavailable):
        """Verify app session returns None without SDK."""
        factory = AgntcyFactorySingleton()

        result = factory.create_app_session()

        assert result is None

    def test_create_app_session_success(self):
        """Verify app session creation."""
        mock_sdk_factory = MagicMock()
        mock_session = MagicMock()
        mock_sdk_factory.create_app_session.return_value = mock_session

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                result = factory.create_app_session(max_sessions=100)

                assert result is mock_session
                mock_sdk_factory.create_app_session.assert_called_once_with(max_sessions=100)

    def test_create_app_session_exception(self):
        """Verify app session exception handling."""
        mock_sdk_factory = MagicMock()
        mock_sdk_factory.create_app_session.side_effect = Exception("Session error")

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                with pytest.raises(Exception, match="Session error"):
                    factory.create_app_session()


# ============================================================================
# Protocol and Transport Information Tests
# ============================================================================


class TestProtocolTransportInfo:
    """Tests for protocol and transport information methods."""

    def test_registered_protocols_no_sdk(self, mock_sdk_unavailable):
        """Verify registered protocols returns empty list without SDK."""
        factory = AgntcyFactorySingleton()

        result = factory.registered_protocols()

        assert result == []

    def test_registered_protocols_with_sdk(self):
        """Verify registered protocols with SDK."""
        mock_sdk_factory = MagicMock()
        mock_sdk_factory.registered_protocols.return_value = ["A2A", "MCP"]

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                result = factory.registered_protocols()

                assert result == ["A2A", "MCP"]

    def test_registered_transports_no_sdk(self, mock_sdk_unavailable):
        """Verify registered transports returns empty list without SDK."""
        factory = AgntcyFactorySingleton()

        result = factory.registered_transports()

        assert result == []

    def test_registered_transports_with_sdk(self):
        """Verify registered transports with SDK."""
        mock_sdk_factory = MagicMock()
        mock_sdk_factory.registered_transports.return_value = ["SLIM", "NATS"]

        with patch.object(factory_module, "AGNTCY_SDK_AVAILABLE", True):
            with patch.object(factory_module, "SDK_Factory", return_value=mock_sdk_factory):
                factory = AgntcyFactorySingleton()

                result = factory.registered_transports()

                assert result == ["SLIM", "NATS"]


# ============================================================================
# Shutdown Tests
# ============================================================================


class TestShutdown:
    """Tests for shutdown functionality."""

    def test_shutdown_not_initialized(self, mock_sdk_unavailable):
        """Verify shutdown when not initialized does nothing."""
        factory = AgntcyFactorySingleton()
        factory._initialized = False

        # Should not raise
        factory.shutdown()

    def test_shutdown_resets_initialized(self, mock_sdk_unavailable):
        """Verify shutdown resets initialized flag."""
        factory = AgntcyFactorySingleton()
        assert factory._initialized is True

        factory.shutdown()

        assert factory._initialized is False


# ============================================================================
# Module-Level Function Tests
# ============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_factory_returns_singleton(self, mock_sdk_unavailable):
        """Verify get_factory returns singleton instance."""
        factory1 = get_factory()
        factory2 = get_factory()

        assert factory1 is factory2
        assert isinstance(factory1, AgntcyFactorySingleton)

    def test_shutdown_factory_calls_shutdown(self, mock_sdk_unavailable):
        """Verify shutdown_factory calls shutdown on singleton."""
        factory = get_factory()
        factory._initialized = True

        shutdown_factory()

        assert factory._initialized is False
