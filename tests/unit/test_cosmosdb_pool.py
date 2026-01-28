# ============================================================================
# Unit Tests for Cosmos DB Client Wrapper
# ============================================================================
# Purpose: Verify Cosmos DB client configuration, initialization, container
# access, and singleton pattern functionality.
#
# Test Categories:
# 1. Configuration - Validate CosmosConfig dataclass
# 2. Client Lifecycle - Initialize, close states
# 3. Container Access - Get container, caching behavior
# 4. Health Status - Verify health reporting
# 5. Global Singleton - Test init/get/close pattern
# 6. Factory Functions - Environment-based creation
#
# Related Documentation:
# - Source Module: shared/cosmosdb_pool.py
# - Architecture: docs/AUTO-SCALING-ARCHITECTURE.md
# - Work Item: docs/AUTO-SCALING-WORK-ITEM-EVALUATION.md (WI-2)
#
# Test Data:
# - Uses mock Cosmos DB client (no real Azure calls)
# ============================================================================

import pytest
import pytest_asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import asdict

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.cosmosdb_pool import (
    CosmosConfig,
    CosmosDBClient,
    init_cosmos_client,
    get_cosmos_client,
    close_cosmos_client,
    create_cosmos_client_from_env,
    get_conversation_container,
    get_analytics_container,
    get_knowledge_container,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def default_config():
    """Default Cosmos configuration for testing."""
    return CosmosConfig(
        endpoint="https://test-cosmos.documents.azure.com:443/",
        key="test-key-12345",
        database_name="test-db",
    )


@pytest.fixture
def custom_config():
    """Custom Cosmos configuration with all options."""
    return CosmosConfig(
        endpoint="https://test-cosmos.documents.azure.com:443/",
        key="test-key-12345",
        database_name="test-db",
        preferred_regions=["East US 2", "West US"],
        max_retry_attempts=5,
        max_retry_wait_time=60.0,
        enable_endpoint_discovery=True,
        connection_mode="Gateway",
    )


@pytest.fixture
def mock_cosmos_client():
    """Mock Cosmos DB client."""
    client = AsyncMock()

    # Mock database client
    database = AsyncMock()
    database.read = AsyncMock(return_value={"id": "test-db"})

    # Mock container client
    container = AsyncMock()
    container.read_item = AsyncMock(return_value={"id": "item-1"})
    database.get_container_client = Mock(return_value=container)

    client.get_database_client = Mock(return_value=database)
    client.close = AsyncMock()

    return client


@pytest_asyncio.fixture
async def client_with_mocks(default_config, mock_cosmos_client):
    """Create a Cosmos client with mocked SDK."""
    with patch("azure.cosmos.aio.CosmosClient", return_value=mock_cosmos_client):
        client = CosmosDBClient(default_config)
        await client.initialize()
        yield client
        await client.close()


# =============================================================================
# Test: Cosmos Configuration
# =============================================================================


class TestCosmosConfig:
    """Tests for CosmosConfig dataclass."""

    def test_required_fields(self, default_config):
        """Verify required fields are set."""
        assert default_config.endpoint == "https://test-cosmos.documents.azure.com:443/"
        assert default_config.key == "test-key-12345"
        assert default_config.database_name == "test-db"

    def test_default_values(self, default_config):
        """Verify default configuration values."""
        assert default_config.preferred_regions is None
        assert default_config.max_retry_attempts == 9
        assert default_config.max_retry_wait_time == 30.0
        assert default_config.enable_endpoint_discovery is True
        assert default_config.connection_mode == "Gateway"

    def test_custom_values(self, custom_config):
        """Verify custom configuration values are applied."""
        assert custom_config.preferred_regions == ["East US 2", "West US"]
        assert custom_config.max_retry_attempts == 5
        assert custom_config.max_retry_wait_time == 60.0

    def test_config_is_dataclass(self, default_config):
        """Verify CosmosConfig can be converted to dict."""
        config_dict = asdict(default_config)
        assert isinstance(config_dict, dict)
        assert config_dict["endpoint"] == default_config.endpoint


# =============================================================================
# Test: Client Lifecycle
# =============================================================================


class TestClientLifecycle:
    """Tests for client initialization and shutdown."""

    def test_client_creation(self, default_config):
        """Verify client creation without initialization."""
        client = CosmosDBClient(default_config)
        assert client.is_initialized is False
        assert client.config == default_config

    @pytest.mark.asyncio
    async def test_client_initialize(self, default_config, mock_cosmos_client):
        """Verify client initializes correctly."""
        with patch(
            "azure.cosmos.aio.CosmosClient", return_value=mock_cosmos_client
        ):
            client = CosmosDBClient(default_config)
            await client.initialize()

            assert client.is_initialized is True
            mock_cosmos_client.get_database_client.assert_called_once_with(
                default_config.database_name
            )

            await client.close()

    @pytest.mark.asyncio
    async def test_client_close(self, client_with_mocks):
        """Verify client closes cleanly."""
        assert client_with_mocks.is_initialized is True
        await client_with_mocks.close()
        assert client_with_mocks.is_initialized is False

    @pytest.mark.asyncio
    async def test_client_double_initialize(self, default_config, mock_cosmos_client):
        """Verify initialize is idempotent."""
        with patch(
            "azure.cosmos.aio.CosmosClient", return_value=mock_cosmos_client
        ):
            client = CosmosDBClient(default_config)
            await client.initialize()
            await client.initialize()  # Should not raise or re-initialize

            # Client constructor should only be called once
            assert client.is_initialized is True
            await client.close()

    @pytest.mark.asyncio
    async def test_client_initialize_failure(self, default_config):
        """Verify initialization failure is handled."""
        mock_client = AsyncMock()
        mock_database = AsyncMock()
        mock_database.read = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.get_database_client = Mock(return_value=mock_database)

        with patch("azure.cosmos.aio.CosmosClient", return_value=mock_client):
            client = CosmosDBClient(default_config)

            with pytest.raises(Exception, match="Connection failed"):
                await client.initialize()

            assert client.is_initialized is False


# =============================================================================
# Test: Container Access
# =============================================================================


class TestContainerAccess:
    """Tests for container access and caching."""

    @pytest.mark.asyncio
    async def test_get_container(self, client_with_mocks):
        """Verify get_container returns container client."""
        container = client_with_mocks.get_container("test-container")
        assert container is not None

    @pytest.mark.asyncio
    async def test_get_container_caching(self, client_with_mocks):
        """Verify container references are cached."""
        container1 = client_with_mocks.get_container("test-container")
        container2 = client_with_mocks.get_container("test-container")
        assert container1 is container2

    @pytest.mark.asyncio
    async def test_get_different_containers(self, client_with_mocks):
        """Verify different containers are separate."""
        container1 = client_with_mocks.get_container("container-1")
        container2 = client_with_mocks.get_container("container-2")
        # They may be the same mock, but the names should differ
        assert "container-1" in client_with_mocks._containers
        assert "container-2" in client_with_mocks._containers

    def test_get_container_before_init_fails(self, default_config):
        """Verify get_container fails before initialization."""
        client = CosmosDBClient(default_config)

        with pytest.raises(RuntimeError, match="not initialized"):
            client.get_container("test-container")


# =============================================================================
# Test: Container Helpers
# =============================================================================


class TestContainerHelpers:
    """Tests for container-specific helper functions."""

    @pytest.mark.asyncio
    async def test_get_conversation_container(self, client_with_mocks):
        """Verify conversation container helper."""
        container = await get_conversation_container(client_with_mocks)
        assert container is not None
        assert "conversations" in client_with_mocks._containers

    @pytest.mark.asyncio
    async def test_get_analytics_container(self, client_with_mocks):
        """Verify analytics container helper."""
        container = await get_analytics_container(client_with_mocks)
        assert container is not None
        assert "analytics" in client_with_mocks._containers

    @pytest.mark.asyncio
    async def test_get_knowledge_container(self, client_with_mocks):
        """Verify knowledge container helper."""
        container = await get_knowledge_container(client_with_mocks)
        assert container is not None
        assert "knowledge" in client_with_mocks._containers


# =============================================================================
# Test: Health Status
# =============================================================================


class TestHealthStatus:
    """Tests for health status reporting."""

    @pytest.mark.asyncio
    async def test_health_status_initialized(self, client_with_mocks):
        """Verify health status when initialized."""
        status = await client_with_mocks.get_health_status()

        assert status["initialized"] is True
        assert status["connected"] is True
        assert "endpoint" in status
        assert "database" in status
        assert "containers_cached" in status

    @pytest.mark.asyncio
    async def test_health_status_uninitialized(self, default_config):
        """Verify health status when not initialized."""
        client = CosmosDBClient(default_config)
        status = await client.get_health_status()

        assert status["initialized"] is False
        assert status["connected"] is False


# =============================================================================
# Test: Global Singleton Pattern
# =============================================================================


class TestGlobalSingleton:
    """Tests for global client singleton functions."""

    @pytest.mark.asyncio
    async def test_get_client_before_init_fails(self):
        """Verify get_cosmos_client fails before initialization."""
        import shared.cosmosdb_pool as cosmos_module

        cosmos_module._global_cosmos = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_cosmos_client()

    @pytest.mark.asyncio
    async def test_init_and_get_client(self, default_config, mock_cosmos_client):
        """Verify init and get work together."""
        import shared.cosmosdb_pool as cosmos_module

        cosmos_module._global_cosmos = None

        with patch(
            "azure.cosmos.aio.CosmosClient", return_value=mock_cosmos_client
        ):
            client = await init_cosmos_client(default_config)
            retrieved_client = get_cosmos_client()

            assert retrieved_client is client
            await close_cosmos_client()

    @pytest.mark.asyncio
    async def test_close_client_clears_global(self, default_config, mock_cosmos_client):
        """Verify close_cosmos_client clears global state."""
        import shared.cosmosdb_pool as cosmos_module

        cosmos_module._global_cosmos = None

        with patch(
            "azure.cosmos.aio.CosmosClient", return_value=mock_cosmos_client
        ):
            await init_cosmos_client(default_config)
            await close_cosmos_client()

            with pytest.raises(RuntimeError):
                get_cosmos_client()

    @pytest.mark.asyncio
    async def test_double_init_returns_existing(
        self, default_config, mock_cosmos_client
    ):
        """Verify double init returns existing client."""
        import shared.cosmosdb_pool as cosmos_module

        cosmos_module._global_cosmos = None

        with patch(
            "azure.cosmos.aio.CosmosClient", return_value=mock_cosmos_client
        ):
            client1 = await init_cosmos_client(default_config)
            client2 = await init_cosmos_client(default_config)

            assert client1 is client2
            await close_cosmos_client()


# =============================================================================
# Test: Factory Functions
# =============================================================================


class TestFactoryFunctions:
    """Tests for environment-based client creation."""

    @pytest.mark.asyncio
    async def test_create_from_env_success(self, mock_cosmos_client):
        """Verify create_cosmos_client_from_env works with env vars."""
        import shared.cosmosdb_pool as cosmos_module

        cosmos_module._global_cosmos = None

        env_vars = {
            "COSMOS_ENDPOINT": "https://test.documents.azure.com:443/",
            "COSMOS_KEY": "test-key-from-env",
            "COSMOS_DATABASE": "test-db-from-env",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch(
                "azure.cosmos.aio.CosmosClient", return_value=mock_cosmos_client
            ):
                client = await create_cosmos_client_from_env()

                assert client.is_initialized is True
                assert client.config.database_name == "test-db-from-env"

                await close_cosmos_client()

    @pytest.mark.asyncio
    async def test_create_from_env_default_database(self, mock_cosmos_client):
        """Verify default database name is used when not specified."""
        import shared.cosmosdb_pool as cosmos_module

        cosmos_module._global_cosmos = None

        env_vars = {
            "COSMOS_ENDPOINT": "https://test.documents.azure.com:443/",
            "COSMOS_KEY": "test-key-from-env",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Remove COSMOS_DATABASE if it exists
            with patch.dict(os.environ, {"COSMOS_DATABASE": ""}, clear=False):
                os.environ.pop("COSMOS_DATABASE", None)

            with patch(
                "azure.cosmos.aio.CosmosClient", return_value=mock_cosmos_client
            ):
                client = await create_cosmos_client_from_env()

                assert client.config.database_name == "agntcy-cs"

                await close_cosmos_client()

    @pytest.mark.asyncio
    async def test_create_from_env_missing_endpoint_fails(self):
        """Verify missing endpoint raises error."""
        import shared.cosmosdb_pool as cosmos_module

        cosmos_module._global_cosmos = None

        env_vars = {
            "COSMOS_KEY": "test-key-from-env",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="COSMOS_ENDPOINT"):
                await create_cosmos_client_from_env()

    @pytest.mark.asyncio
    async def test_create_from_env_missing_key_fails(self):
        """Verify missing key raises error."""
        import shared.cosmosdb_pool as cosmos_module

        cosmos_module._global_cosmos = None

        env_vars = {
            "COSMOS_ENDPOINT": "https://test.documents.azure.com:443/",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="COSMOS_KEY"):
                await create_cosmos_client_from_env()
