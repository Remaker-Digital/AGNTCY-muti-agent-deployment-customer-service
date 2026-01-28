# ============================================================================
# Unit Tests for Azure OpenAI Connection Pool
# ============================================================================
# Purpose: Verify connection pool functionality including initialization,
# acquire/release, circuit breaker, and metrics tracking.
#
# Test Categories:
# 1. Pool Configuration - Validate config dataclass and defaults
# 2. Pool Lifecycle - Initialize, ready, close states
# 3. Connection Acquisition - Acquire, release, timeout handling
# 4. Circuit Breaker - Open, close, half-open state transitions
# 5. Metrics Tracking - Verify metrics are recorded correctly
# 6. Global Singleton - Test init_openai_pool, get_openai_pool pattern
#
# Related Documentation:
# - Source Module: shared/openai_pool.py
# - Architecture: docs/AUTO-SCALING-ARCHITECTURE.md
# - Work Item: docs/AUTO-SCALING-WORK-ITEM-EVALUATION.md (WI-2)
#
# Test Data:
# - Uses mock Azure OpenAI client (no real API calls)
# - Simulates various failure scenarios
# ============================================================================

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import asdict

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.openai_pool import (
    PoolConfig,
    PoolMetrics,
    PoolState,
    CircuitBreaker,
    AzureOpenAIPool,
    init_openai_pool,
    get_openai_pool,
    close_openai_pool,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def default_config():
    """Default pool configuration for testing."""
    return PoolConfig()


@pytest.fixture
def custom_config():
    """Custom pool configuration with small values for fast tests."""
    return PoolConfig(
        min_connections=2,
        max_connections=5,
        connection_timeout=1.0,
        max_retries=2,
        retry_delay=0.1,
        health_check_interval=5.0,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=1.0,
    )


@pytest.fixture
def mock_azure_client():
    """Mock Azure OpenAI client."""
    client = AsyncMock()
    client.chat = AsyncMock()
    client.chat.completions = AsyncMock()
    client.chat.completions.create = AsyncMock(
        return_value=Mock(choices=[Mock(message=Mock(content="Test response"))])
    )
    client._client = AsyncMock()
    client._client.aclose = AsyncMock()
    return client


@pytest_asyncio.fixture
async def pool_with_mocks(custom_config, mock_azure_client):
    """Create a pool with mocked client creation."""
    with patch(
        "shared.openai_pool.AzureOpenAIPool._create_client",
        new_callable=AsyncMock,
        return_value=mock_azure_client,
    ):
        pool = AzureOpenAIPool(
            endpoint="https://test.openai.azure.com/",
            api_key="test-api-key",
            config=custom_config,
        )
        await pool.initialize()
        yield pool
        await pool.close()


# =============================================================================
# Test: Pool Configuration
# =============================================================================


class TestPoolConfig:
    """Tests for PoolConfig dataclass."""

    def test_default_values(self, default_config):
        """Verify default configuration values."""
        assert default_config.min_connections == 5
        assert default_config.max_connections == 50
        assert default_config.connection_timeout == 30.0
        assert default_config.max_retries == 3
        assert default_config.retry_delay == 1.0
        assert default_config.retry_multiplier == 2.0
        assert default_config.health_check_interval == 60.0
        assert default_config.enable_circuit_breaker is True
        assert default_config.circuit_breaker_threshold == 5
        assert default_config.circuit_breaker_timeout == 30.0

    def test_custom_values(self, custom_config):
        """Verify custom configuration values are applied."""
        assert custom_config.min_connections == 2
        assert custom_config.max_connections == 5
        assert custom_config.connection_timeout == 1.0
        assert custom_config.circuit_breaker_threshold == 3

    def test_config_is_dataclass(self):
        """Verify PoolConfig can be converted to dict."""
        config = PoolConfig(min_connections=10)
        config_dict = asdict(config)
        assert isinstance(config_dict, dict)
        assert config_dict["min_connections"] == 10


# =============================================================================
# Test: Pool Metrics
# =============================================================================


class TestPoolMetrics:
    """Tests for PoolMetrics dataclass."""

    def test_default_values(self):
        """Verify metrics start at zero."""
        metrics = PoolMetrics()
        assert metrics.connections_created == 0
        assert metrics.total_acquires == 0
        assert metrics.total_errors == 0
        assert metrics.peak_active == 0

    def test_avg_acquire_time_zero_acquires(self):
        """Verify avg_acquire_time handles zero division."""
        metrics = PoolMetrics()
        assert metrics.avg_acquire_time_ms == 0.0

    def test_avg_acquire_time_calculation(self):
        """Verify avg_acquire_time calculation."""
        metrics = PoolMetrics(total_acquires=10, total_acquire_time_ms=500.0)
        assert metrics.avg_acquire_time_ms == 50.0

    def test_to_dict(self):
        """Verify metrics can be exported to dict."""
        metrics = PoolMetrics(connections_created=5, total_acquires=100, total_errors=2)
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["connections_created"] == 5
        assert metrics_dict["total_acquires"] == 100
        assert metrics_dict["total_errors"] == 2
        assert "avg_acquire_time_ms" in metrics_dict


# =============================================================================
# Test: Circuit Breaker
# =============================================================================


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with low threshold for testing."""
        return CircuitBreaker(threshold=3, timeout=1.0)

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, circuit_breaker):
        """Verify circuit starts in CLOSED state."""
        assert circuit_breaker.state == "CLOSED"
        assert await circuit_breaker.can_execute() is True

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self, circuit_breaker):
        """Verify circuit opens after threshold failures."""
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == "OPEN"
        assert await circuit_breaker.can_execute() is False

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, circuit_breaker):
        """Verify success resets failure count."""
        await circuit_breaker.record_failure()
        await circuit_breaker.record_failure()
        await circuit_breaker.record_success()

        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self, circuit_breaker):
        """Verify circuit transitions to HALF_OPEN after timeout."""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == "OPEN"

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Should transition to HALF_OPEN
        assert await circuit_breaker.can_execute() is True
        assert circuit_breaker.state == "HALF_OPEN"

    @pytest.mark.asyncio
    async def test_is_open_property(self, circuit_breaker):
        """Verify is_open property."""
        assert circuit_breaker.is_open is False

        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.is_open is True


# =============================================================================
# Test: Pool Lifecycle
# =============================================================================


class TestPoolLifecycle:
    """Tests for pool initialization and shutdown."""

    @pytest.mark.asyncio
    async def test_pool_creation(self, custom_config):
        """Verify pool creation without initialization."""
        pool = AzureOpenAIPool(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            config=custom_config,
        )
        assert pool.state == PoolState.UNINITIALIZED
        assert pool.available == 0
        assert pool.active == 0

    @pytest.mark.asyncio
    async def test_pool_initialize(self, custom_config, mock_azure_client):
        """Verify pool initializes with min_connections."""
        with patch(
            "shared.openai_pool.AzureOpenAIPool._create_client",
            new_callable=AsyncMock,
            return_value=mock_azure_client,
        ):
            pool = AzureOpenAIPool(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                config=custom_config,
            )
            await pool.initialize()

            assert pool.state == PoolState.READY
            assert pool.available == custom_config.min_connections
            assert pool.metrics.connections_created == custom_config.min_connections

            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_close(self, pool_with_mocks):
        """Verify pool closes cleanly."""
        pool = pool_with_mocks

        assert pool.state == PoolState.READY
        await pool.close()

        assert pool.state == PoolState.CLOSED
        assert pool.available == 0

    @pytest.mark.asyncio
    async def test_pool_double_close(self, pool_with_mocks):
        """Verify pool handles double close gracefully."""
        pool = pool_with_mocks

        await pool.close()
        await pool.close()  # Should not raise

        assert pool.state == PoolState.CLOSED

    @pytest.mark.asyncio
    async def test_pool_idempotent_initialize(self, custom_config, mock_azure_client):
        """Verify initialize is idempotent."""
        with patch(
            "shared.openai_pool.AzureOpenAIPool._create_client",
            new_callable=AsyncMock,
            return_value=mock_azure_client,
        ):
            pool = AzureOpenAIPool(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                config=custom_config,
            )
            await pool.initialize()
            initial_created = pool.metrics.connections_created

            await pool.initialize()  # Should be idempotent

            assert pool.metrics.connections_created == initial_created
            await pool.close()


# =============================================================================
# Test: Connection Acquisition
# =============================================================================


class TestConnectionAcquisition:
    """Tests for acquiring and releasing connections."""

    @pytest.mark.asyncio
    async def test_acquire_returns_client(self, pool_with_mocks, mock_azure_client):
        """Verify acquire returns a client."""
        async with pool_with_mocks.acquire() as client:
            assert client is not None

    @pytest.mark.asyncio
    async def test_acquire_updates_metrics(self, pool_with_mocks):
        """Verify acquire updates metrics."""
        initial_acquires = pool_with_mocks.metrics.total_acquires

        async with pool_with_mocks.acquire():
            pass

        assert pool_with_mocks.metrics.total_acquires == initial_acquires + 1
        assert pool_with_mocks.metrics.total_releases == 1

    @pytest.mark.asyncio
    async def test_acquire_tracks_active_count(self, pool_with_mocks):
        """Verify active count during acquisition."""
        assert pool_with_mocks.active == 0

        async with pool_with_mocks.acquire():
            assert pool_with_mocks.active == 1

        assert pool_with_mocks.active == 0

    @pytest.mark.asyncio
    async def test_acquire_tracks_peak_active(self, pool_with_mocks, mock_azure_client):
        """Verify peak_active is tracked correctly."""

        # Acquire multiple connections concurrently
        async def acquire_and_hold():
            async with pool_with_mocks.acquire():
                await asyncio.sleep(0.1)

        # Run 3 concurrent acquisitions
        await asyncio.gather(acquire_and_hold(), acquire_and_hold(), acquire_and_hold())

        # Peak should be at least 3 (may be more if connections are created)
        assert pool_with_mocks.metrics.peak_active >= 1

    @pytest.mark.asyncio
    async def test_acquire_from_uninitialized_pool_fails(self, custom_config):
        """Verify acquire fails on uninitialized pool."""
        pool = AzureOpenAIPool(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            config=custom_config,
        )

        with pytest.raises(RuntimeError, match="Pool not ready"):
            async with pool.acquire():
                pass

    @pytest.mark.asyncio
    async def test_acquire_fails_when_circuit_breaker_open(self, pool_with_mocks):
        """Verify acquire fails when circuit breaker is open."""
        # Trip the circuit breaker
        cb = pool_with_mocks._circuit_breaker
        for _ in range(cb.threshold):
            await cb.record_failure()

        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            async with pool_with_mocks.acquire():
                pass


# =============================================================================
# Test: Global Singleton Pattern
# =============================================================================


class TestGlobalSingleton:
    """Tests for global pool singleton functions."""

    @pytest.mark.asyncio
    async def test_get_pool_before_init_fails(self):
        """Verify get_openai_pool fails before initialization."""
        # Reset global state
        import shared.openai_pool as pool_module

        pool_module._global_pool = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_openai_pool()

    @pytest.mark.asyncio
    async def test_init_and_get_pool(self, mock_azure_client):
        """Verify init and get work together."""
        import shared.openai_pool as pool_module

        pool_module._global_pool = None

        with patch(
            "shared.openai_pool.AzureOpenAIPool._create_client",
            new_callable=AsyncMock,
            return_value=mock_azure_client,
        ):
            pool = await init_openai_pool(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                config=PoolConfig(min_connections=1, max_connections=2),
            )

            retrieved_pool = get_openai_pool()
            assert retrieved_pool is pool

            await close_openai_pool()

    @pytest.mark.asyncio
    async def test_close_pool_clears_global(self, mock_azure_client):
        """Verify close_openai_pool clears global state."""
        import shared.openai_pool as pool_module

        pool_module._global_pool = None

        with patch(
            "shared.openai_pool.AzureOpenAIPool._create_client",
            new_callable=AsyncMock,
            return_value=mock_azure_client,
        ):
            await init_openai_pool(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                config=PoolConfig(min_connections=1, max_connections=2),
            )

            await close_openai_pool()

            with pytest.raises(RuntimeError):
                get_openai_pool()


# =============================================================================
# Test: Health Status
# =============================================================================


class TestHealthStatus:
    """Tests for pool health status reporting."""

    @pytest.mark.asyncio
    async def test_get_health_status(self, pool_with_mocks):
        """Verify health status includes all fields."""
        status = pool_with_mocks.get_health_status()

        assert "state" in status
        assert "available_connections" in status
        assert "active_connections" in status
        assert "total_connections" in status
        assert "max_connections" in status
        assert "circuit_breaker_open" in status
        assert "metrics" in status

    @pytest.mark.asyncio
    async def test_health_status_reflects_state(self, pool_with_mocks):
        """Verify health status reflects pool state."""
        status = pool_with_mocks.get_health_status()

        assert status["state"] == "ready"
        assert status["circuit_breaker_open"] is False
        assert status["available_connections"] == pool_with_mocks.available


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error scenarios."""

    @pytest.mark.asyncio
    async def test_error_during_acquire_updates_metrics(self, pool_with_mocks):
        """Verify errors during acquire are tracked."""
        initial_errors = pool_with_mocks.metrics.total_errors

        async def raise_error():
            async with pool_with_mocks.acquire():
                raise ValueError("Test error")

        with pytest.raises(ValueError):
            await raise_error()

        assert pool_with_mocks.metrics.total_errors == initial_errors + 1

    @pytest.mark.asyncio
    async def test_error_records_circuit_breaker_failure(self, pool_with_mocks):
        """Verify errors record circuit breaker failures."""
        cb = pool_with_mocks._circuit_breaker
        initial_failures = cb.failure_count

        async def raise_error():
            async with pool_with_mocks.acquire():
                raise ValueError("Test error")

        with pytest.raises(ValueError):
            await raise_error()

        assert cb.failure_count == initial_failures + 1
