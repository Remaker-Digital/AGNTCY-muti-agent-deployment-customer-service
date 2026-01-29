# ============================================================================
# Base LLM Provider Abstract Class
# ============================================================================
# Purpose: Define the interface that all LLM providers must implement
#
# Why an abstract base class?
# - Enforces consistent interface across providers
# - Enables type checking and IDE support
# - Simplifies provider switching in router
# - Supports testing with mock implementations
#
# Architecture Decision:
# - Abstract methods for core operations (chat, embeddings)
# - Concrete methods for common functionality (health checks)
# - Template method pattern for initialization
#
# Related Documentation:
# - docs/architecture-requirements-phase2-5.md#rag-differentiated-models
# - shared/azure_openai.py - Reference implementation patterns
# ============================================================================

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from .models import (
    LLMProvider,
    ProviderConfig,
    ModelConfig,
    LLMRequest,
    LLMResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All concrete providers must implement:
    - chat_completion(): Generate chat responses
    - generate_embeddings(): Generate text embeddings
    - get_available_models(): List available models
    - health_check(): Verify provider connectivity

    Concrete providers can optionally override:
    - _pre_request_hook(): Called before each request
    - _post_request_hook(): Called after each request
    - _handle_error(): Custom error handling

    Usage:
        class MyProvider(BaseLLMProvider):
            async def chat_completion(self, request: LLMRequest) -> LLMResponse:
                # Implement provider-specific logic
                pass

    Thread Safety:
    - All methods are async and safe for concurrent access
    - Providers should use internal locks for shared state
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize the provider with configuration.

        Args:
            config: Provider configuration including endpoint, API key, etc.
        """
        self.config = config
        self.provider_type = config.provider
        self._initialized = False
        self._client = None

        # Circuit breaker state
        self._consecutive_failures = 0
        self._last_failure_time: Optional[float] = None
        self._circuit_open = False
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 30.0

        # Metrics
        self._total_requests = 0
        self._successful_requests = 0
        self._total_latency_ms = 0.0

        # Rate limiting (sliding window)
        self._request_timestamps: List[float] = []

        logger.info(
            f"{self.provider_type.value} provider created: "
            f"endpoint={config.endpoint[:30]}... priority={config.priority}"
        )

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider client.

        Must be called before any operations.
        Idempotent - safe to call multiple times.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        pass

    @abstractmethod
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a chat completion.

        Args:
            request: Unified LLM request with messages, model, etc.

        Returns:
            LLMResponse with generated content and metadata.

        Raises:
            RuntimeError: If provider not initialized or circuit open.
            Exception: Provider-specific errors.
        """
        pass

    @abstractmethod
    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate text embeddings.

        Args:
            request: Embedding request with texts and model.

        Returns:
            EmbeddingResponse with embedding vectors.

        Raises:
            RuntimeError: If provider not initialized or model doesn't support embeddings.
            Exception: Provider-specific errors.
        """
        pass

    @abstractmethod
    async def get_available_models(self) -> List[ModelConfig]:
        """
        Get list of available models for this provider.

        Returns:
            List of ModelConfig objects for available deployments.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and responsive.

        Should make a lightweight API call to verify connectivity.

        Returns:
            True if healthy, False otherwise.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the provider and release resources.

        Should close any open connections, clear caches, etc.
        Safe to call multiple times.
        """
        pass

    # =========================================================================
    # Concrete methods (shared functionality)
    # =========================================================================

    async def _pre_request_hook(self, request: LLMRequest) -> None:
        """
        Hook called before each request.

        Override for custom pre-request logic (logging, validation, etc.).
        """
        # Check circuit breaker
        if self._circuit_open:
            if self._should_attempt_recovery():
                logger.info(f"{self.provider_type.value}: Attempting circuit recovery")
                self._circuit_open = False
            else:
                raise RuntimeError(
                    f"{self.provider_type.value} circuit breaker is open"
                )

        # Check rate limiting
        await self._check_rate_limit()

    async def _post_request_hook(
        self, request: LLMRequest, response: LLMResponse, latency_ms: float
    ) -> None:
        """
        Hook called after each successful request.

        Override for custom post-request logic (metrics, logging, etc.).
        """
        self._total_requests += 1
        self._successful_requests += 1
        self._total_latency_ms += latency_ms
        self._consecutive_failures = 0

        # Track request for rate limiting
        self._request_timestamps.append(time.time())

        logger.debug(
            f"{self.provider_type.value}: Request completed in {latency_ms:.1f}ms, "
            f"tokens={response.total_tokens}"
        )

    async def _handle_error(self, request: LLMRequest, error: Exception) -> None:
        """
        Handle request errors for circuit breaker logic.

        Override for custom error handling.
        """
        self._total_requests += 1
        self._consecutive_failures += 1
        self._last_failure_time = time.time()

        if self._consecutive_failures >= self._circuit_breaker_threshold:
            self._circuit_open = True
            logger.warning(
                f"{self.provider_type.value}: Circuit breaker OPEN after "
                f"{self._consecutive_failures} consecutive failures"
            )

        logger.error(f"{self.provider_type.value}: Request failed: {error}")

    def _should_attempt_recovery(self) -> bool:
        """Check if circuit breaker timeout has elapsed."""
        if self._last_failure_time is None:
            return True

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self._circuit_breaker_timeout

    async def _check_rate_limit(self) -> None:
        """
        Check and enforce rate limiting.

        Uses sliding window algorithm to track requests per minute.
        """
        now = time.time()
        window_start = now - 60  # 1 minute window

        # Remove old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > window_start
        ]

        if len(self._request_timestamps) >= self.config.rate_limit_rpm:
            wait_time = self._request_timestamps[0] - window_start + 0.1
            logger.warning(
                f"{self.provider_type.value}: Rate limit reached, waiting {wait_time:.1f}s"
            )
            await asyncio.sleep(wait_time)

    def get_status(self) -> ProviderStatus:
        """
        Get current provider status for monitoring.

        Returns:
            ProviderStatus with health and performance metrics.
        """
        success_rate = (
            self._successful_requests / self._total_requests
            if self._total_requests > 0
            else 1.0
        )
        avg_latency = (
            self._total_latency_ms / self._successful_requests
            if self._successful_requests > 0
            else 0.0
        )

        # Count recent requests for current RPM
        now = time.time()
        recent = [ts for ts in self._request_timestamps if ts > now - 60]

        return ProviderStatus(
            provider=self.provider_type,
            is_healthy=self._initialized and not self._circuit_open,
            is_enabled=self.config.enabled,
            consecutive_failures=self._consecutive_failures,
            last_failure_time=(
                asyncio.get_event_loop().time() - self._last_failure_time
                if self._last_failure_time
                else None
            ),
            circuit_open=self._circuit_open,
            avg_latency_ms=avg_latency,
            success_rate=success_rate,
            total_requests=self._total_requests,
            current_rpm=len(recent),
            rate_limit_rpm=self.config.rate_limit_rpm,
        )

    @property
    def is_available(self) -> bool:
        """Check if provider is available for requests."""
        return (
            self._initialized
            and self.config.enabled
            and not self._circuit_open
        )

    @property
    def priority(self) -> int:
        """Get provider priority for routing decisions."""
        return self.config.priority
