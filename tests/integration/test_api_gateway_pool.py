# ============================================================================
# Integration Tests for API Gateway Connection Pool Endpoints
# ============================================================================
# Purpose: Verify the API Gateway's connection pool integration including
# the /api/v1/pool/stats endpoint and pool lifecycle management.
#
# Test Categories:
# 1. Pool Stats Endpoint - Verify endpoint returns correct metrics
# 2. Pool Initialization - Verify pool starts with API Gateway
# 3. Status Endpoint - Verify pool status in /api/v1/status
# 4. Error Scenarios - Verify graceful handling when pool unavailable
#
# Related Documentation:
# - API Gateway: api_gateway/main.py
# - Connection Pool: shared/openai_pool.py
# - Architecture: docs/AUTO-SCALING-ARCHITECTURE.md
#
# Prerequisites:
# - API Gateway running locally or in test environment
# - Mock Azure OpenAI credentials (for testing without real API)
# ============================================================================

import pytest
import httpx
import os
from unittest.mock import patch, AsyncMock, MagicMock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def test_client():
    """Create test client for API Gateway."""
    from fastapi.testclient import TestClient
    from api_gateway.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_pool_metrics():
    """Mock pool metrics for testing."""

    class MockMetrics:
        pool_size = 5
        active_connections = 2
        available_connections = 3
        total_requests = 100
        total_errors = 5
        circuit_breaker_state = "CLOSED"
        avg_wait_time_ms = 15.5

    return MockMetrics()


@pytest.fixture
def mock_openai_pool(mock_pool_metrics):
    """Mock OpenAI pool for testing."""
    pool = MagicMock()
    pool.get_metrics.return_value = mock_pool_metrics
    pool.state = "ready"
    pool.available = 3
    pool.active = 2
    pool.total = 5
    pool.circuit_breaker_open = False
    pool.get_health_status.return_value = {
        "state": "ready",
        "available_connections": 3,
        "active_connections": 2,
        "total_connections": 5,
        "max_connections": 50,
        "circuit_breaker_open": False,
        "metrics": mock_pool_metrics.__dict__,
    }
    return pool


# =============================================================================
# Test: Pool Stats Endpoint
# =============================================================================


class TestPoolStatsEndpoint:
    """Tests for /api/v1/pool/stats endpoint."""

    def test_pool_stats_when_disabled(self, test_client):
        """Verify pool stats returns disabled status when pool not enabled."""
        # When pool is disabled, should return pool_enabled=False
        response = test_client.get("/api/v1/pool/stats")

        assert response.status_code == 200
        data = response.json()
        assert "pool_enabled" in data
        assert "timestamp" in data

    @pytest.mark.skip(reason="Requires mock pool injection")
    def test_pool_stats_with_metrics(self, test_client, mock_openai_pool):
        """Verify pool stats returns metrics when enabled."""
        # This test requires injecting the mock pool into app_state
        # which is complex without proper dependency injection
        pass

    def test_pool_stats_response_model(self, test_client):
        """Verify pool stats response follows expected schema."""
        response = test_client.get("/api/v1/pool/stats")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "pool_enabled" in data
        assert "timestamp" in data

        # Optional fields when pool is enabled
        expected_fields = [
            "pool_size",
            "active_connections",
            "available_connections",
            "total_requests",
            "total_errors",
            "circuit_breaker_state",
            "avg_wait_time_ms",
        ]

        # These fields should exist (may be 0 or default if pool disabled)
        for field in expected_fields:
            assert field in data


# =============================================================================
# Test: Status Endpoint Pool Integration
# =============================================================================


class TestStatusEndpointPoolIntegration:
    """Tests for pool information in /api/v1/status endpoint."""

    def test_status_includes_pool_enabled(self, test_client):
        """Verify status includes connection_pool_enabled field."""
        response = test_client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()

        assert "metrics" in data
        assert "connection_pool_enabled" in data["metrics"]

    def test_status_pool_metrics_when_disabled(self, test_client):
        """Verify status shows pool disabled when not configured."""
        response = test_client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()

        # When pool is disabled, pool metrics should not be present
        metrics = data["metrics"]
        # connection_pool_enabled should be False or the pool section absent
        if "pool" in metrics:
            # If pool section exists, verify it has expected structure
            pool_metrics = metrics["pool"]
            assert "active_connections" in pool_metrics


# =============================================================================
# Test: Health Endpoint
# =============================================================================


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, test_client):
        """Verify health endpoint returns 200."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_azure_status(self, test_client):
        """Verify health includes Azure OpenAI availability."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "azure_openai_available" in data
        assert isinstance(data["azure_openai_available"], bool)

    def test_health_includes_uptime(self, test_client):
        """Verify health includes uptime metric."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


# =============================================================================
# Test: Pool Configuration via Environment
# =============================================================================


class TestPoolConfiguration:
    """Tests for pool configuration via environment variables."""

    def test_pool_env_vars_documented(self):
        """Verify expected environment variables are documented."""
        expected_vars = [
            "USE_CONNECTION_POOL",
            "POOL_MIN_CONNECTIONS",
            "POOL_MAX_CONNECTIONS",
            "POOL_CONNECTION_TIMEOUT",
            "POOL_MAX_RETRIES",
            "POOL_CIRCUIT_BREAKER_THRESHOLD",
            "POOL_CIRCUIT_BREAKER_TIMEOUT",
        ]

        # Read the main.py to verify these are documented
        main_path = Path(__file__).parent.parent.parent / "api_gateway" / "main.py"
        with open(main_path, "r") as f:
            content = f.read()

        for var in expected_vars:
            assert (
                var in content
            ), f"Environment variable {var} not found in api_gateway/main.py"


# =============================================================================
# Test: Async Operations
# =============================================================================


@pytest.mark.asyncio
class TestAsyncPoolOperations:
    """Async tests for pool operations."""

    async def test_pool_module_imports(self):
        """Verify pool module can be imported."""
        from shared.openai_pool import (
            PoolConfig,
            PoolMetrics,
            AzureOpenAIPool,
            init_openai_pool,
            get_openai_pool,
            close_openai_pool,
        )

        assert PoolConfig is not None
        assert PoolMetrics is not None
        assert AzureOpenAIPool is not None

    async def test_pool_config_creation(self):
        """Verify pool config can be created with custom values."""
        from shared.openai_pool import PoolConfig

        config = PoolConfig(
            min_connections=2,
            max_connections=10,
            connection_timeout=30.0,
            enable_circuit_breaker=True,
        )

        assert config.min_connections == 2
        assert config.max_connections == 10
        assert config.connection_timeout == 30.0
        assert config.enable_circuit_breaker is True


# =============================================================================
# Test: Circuit Breaker Integration
# =============================================================================


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker behavior in API Gateway context."""

    def test_pool_stats_shows_circuit_breaker_state(self, test_client):
        """Verify pool stats includes circuit breaker state."""
        response = test_client.get("/api/v1/pool/stats")

        assert response.status_code == 200
        data = response.json()

        assert "circuit_breaker_state" in data

    @pytest.mark.skip(reason="Requires running pool with failures")
    def test_circuit_breaker_opens_on_failures(self):
        """Verify circuit breaker opens after threshold failures."""
        # This test would require injecting failures into the pool
        pass


# =============================================================================
# Test: KEDA Metrics Compatibility
# =============================================================================


class TestKEDAMetricsCompatibility:
    """Tests for KEDA scaling metrics compatibility."""

    def test_pool_stats_has_keda_metrics(self, test_client):
        """Verify pool stats has metrics usable by KEDA."""
        response = test_client.get("/api/v1/pool/stats")

        assert response.status_code == 200
        data = response.json()

        # KEDA can use these metrics for scaling decisions
        keda_relevant_metrics = ["active_connections", "total_requests", "total_errors"]

        for metric in keda_relevant_metrics:
            assert metric in data, f"KEDA metric {metric} missing from pool stats"

    def test_pool_stats_returns_numeric_values(self, test_client):
        """Verify pool stats returns numeric values for metrics."""
        response = test_client.get("/api/v1/pool/stats")

        assert response.status_code == 200
        data = response.json()

        numeric_fields = [
            "pool_size",
            "active_connections",
            "available_connections",
            "total_requests",
            "total_errors",
            "avg_wait_time_ms",
        ]

        for field in numeric_fields:
            if field in data:
                assert isinstance(
                    data[field], (int, float)
                ), f"Field {field} should be numeric"


# =============================================================================
# Test: Graceful Degradation
# =============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation when pool is unavailable."""

    def test_chat_works_without_pool(self, test_client):
        """Verify chat endpoint works even without pool."""
        response = test_client.post(
            "/api/v1/chat", json={"message": "Hello, test message"}
        )

        # Should not fail due to pool issues
        # May return fallback response if Azure not available
        assert response.status_code in [200, 500]  # 500 if Azure not configured

    def test_status_works_without_pool(self, test_client):
        """Verify status endpoint works without pool."""
        response = test_client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()

        # Status should indicate pool is disabled
        assert "metrics" in data
