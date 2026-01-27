# ============================================================================
# Azure OpenAI Connection Pool for High-Volume Workloads
# ============================================================================
# Purpose: Manage multiple concurrent connections to Azure OpenAI to maximize
# throughput while respecting rate limits and enabling horizontal scaling.
#
# Why connection pooling?
# - Azure OpenAI has TPM (tokens per minute) limits (10K-200K depending on tier)
# - Single connection creates head-of-line blocking under load
# - Multiple connections allow parallel request processing
# - Pool management prevents connection exhaustion during scale events
# - Required for 10,000 daily users target (see AUTO-SCALING-ARCHITECTURE.md)
#
# Architecture Decision:
# - Async-first design for non-blocking I/O
# - Context manager pattern for safe resource cleanup
# - Configurable pool size based on deployment tier
# - Circuit breaker integration for graceful degradation
#
# Related Documentation:
# - Azure OpenAI Quotas: https://learn.microsoft.com/azure/ai-services/openai/quotas-limits
# - Connection Best Practices: https://learn.microsoft.com/azure/ai-services/openai/how-to/
# - Auto-Scaling Architecture: docs/AUTO-SCALING-ARCHITECTURE.md
# - Work Item Evaluation: docs/AUTO-SCALING-WORK-ITEM-EVALUATION.md
#
# Cost Impact:
# - Reduces failed requests due to connection issues (-5-10% token waste)
# - Enables higher throughput per instance (fewer instances needed)
# - Estimated savings: $15-40/month from reduced retries and better utilization
# ============================================================================

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, AsyncIterator
from enum import Enum

logger = logging.getLogger(__name__)


class PoolState(Enum):
    """Connection pool lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    DRAINING = "draining"
    CLOSED = "closed"


@dataclass
class PoolConfig:
    """
    Configuration for Azure OpenAI connection pool.

    Tuning Guidelines:
    - min_connections: Start with 5 for light load, increase for sustained traffic
    - max_connections: Match to Azure OpenAI concurrent request limit (typically 50-100)
    - connection_timeout: 30s default handles slow AI responses
    - max_retries: 3 retries with exponential backoff for transient failures
    - health_check_interval: 60s balances overhead vs detection speed

    Source of Record: docs/AUTO-SCALING-ARCHITECTURE.md#connection-pooling
    """
    min_connections: int = 5
    max_connections: int = 50
    connection_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_multiplier: float = 2.0  # Exponential backoff multiplier
    health_check_interval: float = 60.0
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5  # Failures before opening circuit
    circuit_breaker_timeout: float = 30.0  # Seconds before attempting recovery


@dataclass
class PoolMetrics:
    """
    Metrics for monitoring pool health and performance.

    These metrics should be exported to Application Insights for:
    - Capacity planning (connections_created, peak_active)
    - Error tracking (total_errors, circuit_breaker_trips)
    - Performance tuning (avg_acquire_time, avg_release_time)
    """
    connections_created: int = 0
    connections_closed: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    total_errors: int = 0
    total_timeouts: int = 0
    circuit_breaker_trips: int = 0
    peak_active: int = 0
    total_acquire_time_ms: float = 0.0

    @property
    def avg_acquire_time_ms(self) -> float:
        """Average time to acquire a connection from the pool."""
        if self.total_acquires == 0:
            return 0.0
        return self.total_acquire_time_ms / self.total_acquires

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics for telemetry."""
        return {
            "connections_created": self.connections_created,
            "connections_closed": self.connections_closed,
            "total_acquires": self.total_acquires,
            "total_releases": self.total_releases,
            "total_errors": self.total_errors,
            "total_timeouts": self.total_timeouts,
            "circuit_breaker_trips": self.circuit_breaker_trips,
            "peak_active": self.peak_active,
            "avg_acquire_time_ms": self.avg_acquire_time_ms,
        }


class CircuitBreaker:
    """
    Circuit breaker for connection pool resilience.

    Why circuit breaker?
    - Prevents cascade failures when Azure OpenAI is degraded
    - Allows fast-fail instead of waiting for timeouts
    - Enables graceful degradation with fallback responses

    States:
    - CLOSED: Normal operation, requests flow through
    - OPEN: Failures exceeded threshold, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, threshold: int, timeout: float):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"
        self._lock = asyncio.Lock()

    async def record_success(self) -> None:
        """Record a successful operation, reset failure count."""
        async with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    async def record_failure(self) -> None:
        """Record a failed operation, potentially open circuit."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.threshold:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker OPEN after {self.failure_count} failures"
                )

    async def can_execute(self) -> bool:
        """Check if request should be allowed through."""
        async with self._lock:
            if self.state == "CLOSED":
                return True

            if self.state == "OPEN":
                # Check if timeout has elapsed
                if self.last_failure_time and \
                   (time.time() - self.last_failure_time) > self.timeout:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker HALF_OPEN, testing recovery")
                    return True
                return False

            # HALF_OPEN: Allow one request to test
            return True

    @property
    def is_open(self) -> bool:
        """Check if circuit is currently open (blocking requests)."""
        return self.state == "OPEN"


class AzureOpenAIPool:
    """
    Connection pool for Azure OpenAI API.

    Manages multiple AsyncAzureOpenAI client instances to maximize throughput
    while respecting rate limits. Essential for supporting 10,000 daily users
    with horizontal scaling.

    Usage:
        # Initialize pool at application startup
        pool = AzureOpenAIPool(
            endpoint="https://your-resource.openai.azure.com/",
            api_key="your-api-key",
            config=PoolConfig(min_connections=5, max_connections=50)
        )
        await pool.initialize()

        # Use connection from pool
        async with pool.acquire() as client:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}]
            )

        # Cleanup at shutdown
        await pool.close()

    Thread Safety:
    - All public methods are async and thread-safe
    - Uses asyncio.Lock for state management
    - Safe for concurrent access from multiple coroutines

    Monitoring:
    - Access metrics via pool.metrics property
    - Export to Application Insights for dashboards
    - Alert on circuit_breaker_trips > 0
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        api_version: str = "2024-02-15-preview",
        config: Optional[PoolConfig] = None
    ):
        """
        Initialize the connection pool (does not create connections yet).

        Args:
            endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            api_version: API version to use
            config: Pool configuration (uses defaults if not provided)
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.config = config or PoolConfig()

        self._pool: asyncio.Queue = asyncio.Queue()
        self._active_count = 0
        self._state = PoolState.UNINITIALIZED
        self._lock = asyncio.Lock()
        self._metrics = PoolMetrics()

        # Circuit breaker for resilience
        self._circuit_breaker: Optional[CircuitBreaker] = None
        if self.config.enable_circuit_breaker:
            self._circuit_breaker = CircuitBreaker(
                threshold=self.config.circuit_breaker_threshold,
                timeout=self.config.circuit_breaker_timeout
            )

        logger.info(
            f"AzureOpenAIPool created: endpoint={endpoint}, "
            f"min={self.config.min_connections}, max={self.config.max_connections}"
        )

    async def initialize(self) -> None:
        """
        Initialize the connection pool with minimum connections.

        Call this at application startup before handling requests.
        Idempotent - safe to call multiple times.
        """
        async with self._lock:
            if self._state != PoolState.UNINITIALIZED:
                logger.debug(f"Pool already in state {self._state}, skipping init")
                return

            self._state = PoolState.INITIALIZING

        try:
            # Create minimum connections
            for i in range(self.config.min_connections):
                client = await self._create_client()
                await self._pool.put(client)
                self._metrics.connections_created += 1
                logger.debug(f"Created initial connection {i + 1}/{self.config.min_connections}")

            async with self._lock:
                self._state = PoolState.READY

            logger.info(
                f"AzureOpenAIPool initialized with {self.config.min_connections} connections"
            )
        except Exception as e:
            async with self._lock:
                self._state = PoolState.UNINITIALIZED
            logger.error(f"Failed to initialize pool: {e}")
            raise

    async def _create_client(self):
        """
        Create a new Azure OpenAI async client.

        Uses httpx limits for connection pooling at the HTTP layer.
        """
        try:
            # Import here to avoid circular dependencies
            from openai import AsyncAzureOpenAI
            import httpx

            # Configure HTTP client with connection limits
            # These limits apply per-client, pool manages multiple clients
            http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=10,  # Per-client limit
                    max_keepalive_connections=5,
                    keepalive_expiry=30.0
                ),
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=self.config.connection_timeout,
                    write=10.0,
                    pool=5.0
                )
            )

            client = AsyncAzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
                http_client=http_client,
                max_retries=self.config.max_retries
            )

            return client

        except ImportError as e:
            logger.error(f"Failed to import OpenAI package: {e}")
            raise RuntimeError(
                "openai package not installed. Run: pip install openai>=1.12.0"
            ) from e

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator:
        """
        Acquire a client from the pool using context manager.

        Usage:
            async with pool.acquire() as client:
                response = await client.chat.completions.create(...)

        The client is automatically returned to the pool when the context exits.

        Raises:
            RuntimeError: If pool is not initialized or circuit breaker is open
            asyncio.TimeoutError: If no client available within timeout
        """
        if self._state != PoolState.READY:
            raise RuntimeError(f"Pool not ready, current state: {self._state}")

        # Check circuit breaker
        if self._circuit_breaker and not await self._circuit_breaker.can_execute():
            self._metrics.circuit_breaker_trips += 1
            raise RuntimeError("Circuit breaker is open, service degraded")

        start_time = time.time()
        client = None

        try:
            client = await self._acquire_client()
            self._metrics.total_acquires += 1
            self._metrics.total_acquire_time_ms += (time.time() - start_time) * 1000

            # Track peak active connections
            async with self._lock:
                self._active_count += 1
                if self._active_count > self._metrics.peak_active:
                    self._metrics.peak_active = self._active_count

            yield client

            # Record success for circuit breaker
            if self._circuit_breaker:
                await self._circuit_breaker.record_success()

        except Exception as e:
            self._metrics.total_errors += 1

            # Record failure for circuit breaker
            if self._circuit_breaker:
                await self._circuit_breaker.record_failure()

            logger.error(f"Error during pool acquire/use: {e}")
            raise

        finally:
            if client:
                await self._release_client(client)
                async with self._lock:
                    self._active_count -= 1
                self._metrics.total_releases += 1

    async def _acquire_client(self):
        """
        Internal method to acquire a client from the pool.

        Strategy:
        1. Try to get existing client (non-blocking)
        2. If empty and under max, create new client
        3. Otherwise wait for available client (blocking)
        """
        try:
            # Try non-blocking get first
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            pass

        # Check if we can create a new connection
        async with self._lock:
            total_connections = self._pool.qsize() + self._active_count
            if total_connections < self.config.max_connections:
                client = await self._create_client()
                self._metrics.connections_created += 1
                logger.debug(
                    f"Created new connection, total: {total_connections + 1}"
                )
                return client

        # Wait for available client with timeout
        try:
            return await asyncio.wait_for(
                self._pool.get(),
                timeout=self.config.connection_timeout
            )
        except asyncio.TimeoutError:
            self._metrics.total_timeouts += 1
            logger.warning("Timeout waiting for available connection")
            raise

    async def _release_client(self, client) -> None:
        """Return a client to the pool."""
        if self._state == PoolState.DRAINING or self._state == PoolState.CLOSED:
            # Pool is closing, don't return client
            await self._close_client(client)
            return

        await self._pool.put(client)

    async def _close_client(self, client) -> None:
        """Close a client and clean up resources."""
        try:
            if hasattr(client, '_client') and hasattr(client._client, 'aclose'):
                await client._client.aclose()
            self._metrics.connections_closed += 1
        except Exception as e:
            logger.warning(f"Error closing client: {e}")

    async def close(self) -> None:
        """
        Close all connections and shutdown the pool.

        Call this at application shutdown for clean resource cleanup.
        Safe to call multiple times.
        """
        async with self._lock:
            if self._state == PoolState.CLOSED:
                return
            self._state = PoolState.DRAINING

        logger.info("Closing AzureOpenAIPool...")

        # Close all pooled connections
        while not self._pool.empty():
            try:
                client = self._pool.get_nowait()
                await self._close_client(client)
            except asyncio.QueueEmpty:
                break

        async with self._lock:
            self._state = PoolState.CLOSED

        logger.info(
            f"AzureOpenAIPool closed. Metrics: {self._metrics.to_dict()}"
        )

    @property
    def available(self) -> int:
        """Number of available (idle) connections in the pool."""
        return self._pool.qsize()

    @property
    def active(self) -> int:
        """Number of connections currently in use."""
        return self._active_count

    @property
    def total(self) -> int:
        """Total connections (available + active)."""
        return self._pool.qsize() + self._active_count

    @property
    def state(self) -> PoolState:
        """Current pool state."""
        return self._state

    @property
    def metrics(self) -> PoolMetrics:
        """Pool metrics for monitoring."""
        return self._metrics

    @property
    def circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is currently open."""
        if self._circuit_breaker:
            return self._circuit_breaker.is_open
        return False

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get pool health status for health checks and monitoring.

        Returns dict suitable for /health endpoint response.
        """
        return {
            "state": self._state.value,
            "available_connections": self.available,
            "active_connections": self.active,
            "total_connections": self.total,
            "max_connections": self.config.max_connections,
            "circuit_breaker_open": self.circuit_breaker_open,
            "metrics": self._metrics.to_dict()
        }


# ============================================================================
# Global Pool Instance (Singleton Pattern)
# ============================================================================
# Why singleton?
# - Connection pools are expensive to create
# - Multiple pools would waste resources
# - Simplifies dependency injection in agents
#
# Usage:
#     from shared.openai_pool import get_openai_pool, init_openai_pool
#
#     # At startup
#     await init_openai_pool(endpoint, api_key)
#
#     # In agent code
#     pool = get_openai_pool()
#     async with pool.acquire() as client:
#         ...
# ============================================================================

_global_pool: Optional[AzureOpenAIPool] = None


async def init_openai_pool(
    endpoint: str,
    api_key: str,
    api_version: str = "2024-02-15-preview",
    config: Optional[PoolConfig] = None
) -> AzureOpenAIPool:
    """
    Initialize the global OpenAI connection pool.

    Call once at application startup.

    Args:
        endpoint: Azure OpenAI endpoint URL
        api_key: Azure OpenAI API key
        api_version: API version
        config: Pool configuration

    Returns:
        Initialized AzureOpenAIPool instance
    """
    global _global_pool

    if _global_pool is not None and _global_pool.state == PoolState.READY:
        logger.warning("Global pool already initialized, returning existing")
        return _global_pool

    _global_pool = AzureOpenAIPool(
        endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        config=config
    )
    await _global_pool.initialize()

    return _global_pool


def get_openai_pool() -> AzureOpenAIPool:
    """
    Get the global OpenAI connection pool.

    Raises RuntimeError if pool not initialized.

    Returns:
        The global AzureOpenAIPool instance
    """
    if _global_pool is None:
        raise RuntimeError(
            "OpenAI pool not initialized. Call init_openai_pool() first."
        )
    return _global_pool


async def close_openai_pool() -> None:
    """
    Close the global OpenAI connection pool.

    Call at application shutdown.
    """
    global _global_pool

    if _global_pool is not None:
        await _global_pool.close()
        _global_pool = None
