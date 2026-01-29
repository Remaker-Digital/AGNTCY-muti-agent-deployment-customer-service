# ============================================================================
# Model Router with Fallback and Load Balancing
# ============================================================================
# Purpose: Unified interface for routing LLM requests across multiple providers
#
# Why a router?
# - Abstracts provider selection from application code
# - Enables automatic fallback when primary provider fails
# - Supports load balancing across providers
# - Centralizes cost tracking and monitoring
#
# Architecture Decision:
# - Strategy pattern for fallback strategies
# - Chain of responsibility for provider selection
# - Observer pattern for cost tracking
# - Singleton pattern for global access
#
# Related Documentation:
# - CLAUDE.md#model-router-abstraction-layer
# - shared/openai_pool.py - Connection pooling reference
# - shared/cost_monitor.py - Cost tracking integration
#
# Cost Impact:
# - Fallback reduces wasted API calls on failures
# - Load balancing optimizes provider utilization
# - Centralized tracking enables budget management
# ============================================================================

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List

from .models import (
    LLMProvider,
    ModelCapability,
    ProviderConfig,
    ModelConfig,
    LLMRequest,
    LLMResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderStatus,
    FallbackStrategy,
)
from .base import BaseLLMProvider
from .providers import (
    AzureOpenAIProvider,
    AnthropicProvider,
    MockProvider,
)

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Central router for LLM requests with fallback and load balancing.

    Features:
    - Multiple provider support (Azure OpenAI, Anthropic, Mock)
    - Automatic fallback on provider failure
    - Priority-based provider selection
    - Round-robin load balancing (optional)
    - Centralized cost tracking
    - Health monitoring for all providers

    Usage:
        router = ModelRouter()
        router.add_provider(azure_config)
        router.add_provider(anthropic_config)
        await router.initialize()

        # Simple request (uses priority-based selection)
        response = await router.chat_completion(LLMRequest(...))

        # Force specific provider
        response = await router.chat_completion(
            LLMRequest(...),
            provider=LLMProvider.ANTHROPIC
        )

    Thread Safety:
    - All methods are async and safe for concurrent access
    - Provider list modifications should happen before initialization
    """

    def __init__(
        self,
        fallback_strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL,
        max_fallback_attempts: int = 3,
    ):
        """
        Initialize the model router.

        Args:
            fallback_strategy: How to handle provider failures
            max_fallback_attempts: Maximum providers to try before giving up
        """
        self.fallback_strategy = fallback_strategy
        self.max_fallback_attempts = max_fallback_attempts

        self._providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self._provider_configs: Dict[LLMProvider, ProviderConfig] = {}
        self._initialized = False

        # Round-robin state
        self._round_robin_index = 0
        self._round_robin_lock = asyncio.Lock()

        # Cost tracking callback
        self._cost_callback: Optional[callable] = None

        logger.info(
            f"ModelRouter created: strategy={fallback_strategy.value}, "
            f"max_attempts={max_fallback_attempts}"
        )

    def add_provider(self, config: ProviderConfig) -> None:
        """
        Add a provider configuration.

        Must be called before initialize().

        Args:
            config: Provider configuration
        """
        if self._initialized:
            raise RuntimeError("Cannot add providers after initialization")

        self._provider_configs[config.provider] = config
        logger.info(
            f"Added provider config: {config.provider.value} "
            f"priority={config.priority} enabled={config.enabled}"
        )

    async def initialize(self) -> bool:
        """
        Initialize all configured providers.

        Returns:
            True if at least one provider initialized successfully.
        """
        if self._initialized:
            return True

        if not self._provider_configs:
            logger.warning("No providers configured, using mock provider")
            mock_config = ProviderConfig(
                provider=LLMProvider.LOCAL,
                endpoint="mock://localhost",
                priority=99,
            )
            self._provider_configs[LLMProvider.LOCAL] = mock_config

        # Initialize each provider
        success_count = 0
        for provider_type, config in self._provider_configs.items():
            if not config.enabled:
                logger.info(f"Skipping disabled provider: {provider_type.value}")
                continue

            provider = self._create_provider(config)
            if provider and await provider.initialize():
                self._providers[provider_type] = provider
                success_count += 1
                logger.info(f"Initialized provider: {provider_type.value}")
            else:
                logger.warning(f"Failed to initialize provider: {provider_type.value}")

        self._initialized = success_count > 0

        if self._initialized:
            logger.info(
                f"ModelRouter initialized with {success_count} providers: "
                f"{[p.value for p in self._providers.keys()]}"
            )
        else:
            logger.error("ModelRouter failed to initialize: no providers available")

        return self._initialized

    def _create_provider(self, config: ProviderConfig) -> Optional[BaseLLMProvider]:
        """
        Create a provider instance from config.

        Args:
            config: Provider configuration

        Returns:
            Provider instance or None if creation failed.
        """
        try:
            if config.provider == LLMProvider.AZURE_OPENAI:
                return AzureOpenAIProvider(config)
            elif config.provider == LLMProvider.ANTHROPIC:
                return AnthropicProvider(config)
            elif config.provider == LLMProvider.LOCAL:
                return MockProvider(config)
            else:
                logger.error(f"Unknown provider type: {config.provider}")
                return None
        except Exception as e:
            logger.error(f"Failed to create provider {config.provider.value}: {e}")
            return None

    def _get_providers_by_priority(self) -> List[BaseLLMProvider]:
        """
        Get available providers sorted by priority.

        Returns:
            List of providers sorted by priority (lower = higher priority).
        """
        available = [p for p in self._providers.values() if p.is_available]
        return sorted(available, key=lambda p: p.priority)

    async def _select_provider(
        self,
        preferred_provider: Optional[LLMProvider] = None,
    ) -> BaseLLMProvider:
        """
        Select a provider based on strategy.

        Args:
            preferred_provider: If specified, try this provider first.

        Returns:
            Selected provider.

        Raises:
            RuntimeError: If no providers are available.
        """
        # If specific provider requested, use it
        if preferred_provider and preferred_provider in self._providers:
            provider = self._providers[preferred_provider]
            if provider.is_available:
                return provider
            logger.warning(
                f"Requested provider {preferred_provider.value} not available"
            )

        # Get available providers
        available = self._get_providers_by_priority()
        if not available:
            raise RuntimeError("No LLM providers available")

        # Select based on strategy
        if self.fallback_strategy == FallbackStrategy.ROUND_ROBIN:
            async with self._round_robin_lock:
                self._round_robin_index = self._round_robin_index % len(available)
                provider = available[self._round_robin_index]
                self._round_robin_index += 1
                return provider
        else:
            # SEQUENTIAL or FAILOVER_ONLY: use highest priority
            return available[0]

    async def chat_completion(
        self,
        request: LLMRequest,
        provider: Optional[LLMProvider] = None,
    ) -> LLMResponse:
        """
        Generate a chat completion with automatic fallback.

        Args:
            request: LLM request
            provider: Optional specific provider to use

        Returns:
            LLMResponse from the successful provider.

        Raises:
            RuntimeError: If all providers fail.
        """
        if not self._initialized:
            raise RuntimeError("ModelRouter not initialized")

        errors = []
        attempted_providers = []

        # Get providers to try
        if provider:
            # Specific provider requested
            providers_to_try = [self._providers.get(provider)]
            if not providers_to_try[0]:
                raise RuntimeError(f"Provider {provider.value} not configured")
        elif self.fallback_strategy == FallbackStrategy.ROUND_ROBIN:
            # For round-robin, select provider and then get fallbacks
            primary = await self._select_provider()
            providers_to_try = [primary] + [
                p for p in self._get_providers_by_priority()
                if p != primary
            ]
        else:
            providers_to_try = self._get_providers_by_priority()

        # Try providers with fallback
        for i, p in enumerate(providers_to_try):
            if i >= self.max_fallback_attempts:
                break

            if not p.is_available:
                continue

            attempted_providers.append(p.provider_type)

            try:
                response = await p.chat_completion(request)

                # Track cost if callback registered
                if self._cost_callback:
                    await self._cost_callback(
                        agent_name=request.agent_name or "unknown",
                        model=request.model,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                        estimated_cost=response.estimated_cost,
                        provider=response.provider,
                    )

                # Mark if fallback was used
                if i > 0:
                    response.fallback_used = True
                    response.original_provider = attempted_providers[0]

                return response

            except Exception as e:
                errors.append((p.provider_type, str(e)))
                logger.warning(
                    f"Provider {p.provider_type.value} failed: {e}"
                )

                # For FAILOVER_ONLY, only try fallback on specific errors
                if self.fallback_strategy == FallbackStrategy.FAILOVER_ONLY:
                    if "rate limit" not in str(e).lower() and "timeout" not in str(e).lower():
                        raise

        # All providers failed
        error_summary = "; ".join(f"{p.value}: {e}" for p, e in errors)
        raise RuntimeError(
            f"All providers failed after {len(attempted_providers)} attempts: {error_summary}"
        )

    async def generate_embeddings(
        self,
        request: EmbeddingRequest,
        provider: Optional[LLMProvider] = None,
    ) -> EmbeddingResponse:
        """
        Generate embeddings with automatic fallback.

        Args:
            request: Embedding request
            provider: Optional specific provider to use

        Returns:
            EmbeddingResponse from the successful provider.

        Raises:
            RuntimeError: If all providers fail.
        """
        if not self._initialized:
            raise RuntimeError("ModelRouter not initialized")

        # Get providers that support embeddings
        if provider:
            providers_to_try = [self._providers.get(provider)]
            if not providers_to_try[0]:
                raise RuntimeError(f"Provider {provider.value} not configured")
        else:
            providers_to_try = [
                p for p in self._get_providers_by_priority()
                if any(
                    m.capability == ModelCapability.EMBEDDING
                    for m in await p.get_available_models()
                )
            ]

        if not providers_to_try:
            raise RuntimeError("No providers support embeddings")

        errors = []
        for i, p in enumerate(providers_to_try):
            if i >= self.max_fallback_attempts:
                break

            try:
                response = await p.generate_embeddings(request)

                # Track cost
                if self._cost_callback:
                    await self._cost_callback(
                        agent_name=request.agent_name or "unknown",
                        model=request.model,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=0,
                        estimated_cost=response.estimated_cost,
                        provider=response.provider,
                    )

                return response

            except NotImplementedError:
                # Provider doesn't support embeddings, try next
                continue
            except Exception as e:
                errors.append((p.provider_type, str(e)))
                logger.warning(f"Embedding generation failed: {e}")

        error_summary = "; ".join(f"{p.value}: {e}" for p, e in errors)
        raise RuntimeError(f"Embedding generation failed: {error_summary}")

    async def get_available_models(
        self,
        provider: Optional[LLMProvider] = None,
        capability: Optional[ModelCapability] = None,
    ) -> List[ModelConfig]:
        """
        Get available models across providers.

        Args:
            provider: Filter by provider
            capability: Filter by capability

        Returns:
            List of available ModelConfig objects.
        """
        models = []

        providers_to_check = (
            [self._providers[provider]] if provider and provider in self._providers
            else self._providers.values()
        )

        for p in providers_to_check:
            try:
                provider_models = await p.get_available_models()
                for m in provider_models:
                    if capability is None or m.capability == capability:
                        models.append(m)
            except Exception as e:
                logger.warning(f"Failed to get models from {p.provider_type.value}: {e}")

        return models

    async def health_check(self) -> Dict[str, ProviderStatus]:
        """
        Check health of all providers.

        Returns:
            Dict mapping provider name to ProviderStatus.
        """
        status = {}
        for provider_type, provider in self._providers.items():
            is_healthy = await provider.health_check()
            provider_status = provider.get_status()
            provider_status.is_healthy = is_healthy
            status[provider_type.value] = provider_status
        return status

    def get_provider_status(self) -> Dict[str, Any]:
        """
        Get status summary for all providers.

        Returns:
            Dict with provider status information.
        """
        return {
            "initialized": self._initialized,
            "fallback_strategy": self.fallback_strategy.value,
            "max_fallback_attempts": self.max_fallback_attempts,
            "providers": {
                p.value: {
                    "enabled": p in self._providers,
                    "available": self._providers[p].is_available if p in self._providers else False,
                    "priority": self._provider_configs[p].priority if p in self._provider_configs else None,
                }
                for p in LLMProvider
            },
        }

    def set_cost_callback(self, callback: callable) -> None:
        """
        Set callback for cost tracking.

        Args:
            callback: Async function(agent_name, model, prompt_tokens,
                     completion_tokens, estimated_cost, provider)
        """
        self._cost_callback = callback

    async def shutdown(self) -> None:
        """
        Shutdown all providers and release resources.
        """
        for provider_type, provider in self._providers.items():
            try:
                await provider.shutdown()
                logger.info(f"Shutdown provider: {provider_type.value}")
            except Exception as e:
                logger.warning(f"Error shutting down {provider_type.value}: {e}")

        self._providers.clear()
        self._initialized = False
        logger.info("ModelRouter shutdown complete")


# ============================================================================
# Global Router Instance (Singleton Pattern)
# ============================================================================
# Why singleton?
# - Centralized provider management
# - Consistent fallback behavior across agents
# - Shared cost tracking
# - Simplified dependency injection
# ============================================================================

_global_router: Optional[ModelRouter] = None


async def init_model_router(
    providers: Optional[List[ProviderConfig]] = None,
    fallback_strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL,
    max_fallback_attempts: int = 3,
) -> ModelRouter:
    """
    Initialize the global model router.

    If no providers specified, auto-configures from environment variables.

    Args:
        providers: List of provider configurations
        fallback_strategy: Fallback strategy
        max_fallback_attempts: Max providers to try

    Returns:
        Initialized ModelRouter instance.
    """
    global _global_router

    if _global_router is not None and _global_router._initialized:
        logger.warning("Global router already initialized")
        return _global_router

    _global_router = ModelRouter(
        fallback_strategy=fallback_strategy,
        max_fallback_attempts=max_fallback_attempts,
    )

    # Add provided configs or auto-configure
    if providers:
        for config in providers:
            _global_router.add_provider(config)
    else:
        # Auto-configure from environment
        _auto_configure_providers(_global_router)

    await _global_router.initialize()
    return _global_router


def _auto_configure_providers(router: ModelRouter) -> None:
    """
    Auto-configure providers from environment variables.

    Environment variables:
    - AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY
    - ANTHROPIC_API_KEY
    - USE_MOCK_LLM (if "true", adds mock provider)
    """
    # Azure OpenAI (primary)
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    if azure_endpoint:
        router.add_provider(ProviderConfig(
            provider=LLMProvider.AZURE_OPENAI,
            endpoint=azure_endpoint,
            api_key=azure_key,
            priority=1,
            enabled=True,
        ))

    # Anthropic (secondary)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        router.add_provider(ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            endpoint="https://api.anthropic.com",
            api_key=anthropic_key,
            priority=2,
            enabled=True,
        ))

    # Mock provider (for development/testing)
    use_mock = os.getenv("USE_MOCK_LLM", "").lower() == "true"
    if use_mock or (not azure_endpoint and not anthropic_key):
        router.add_provider(ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
            priority=99,
            enabled=True,
        ))


def get_model_router() -> ModelRouter:
    """
    Get the global model router instance.

    Raises:
        RuntimeError: If router not initialized.

    Returns:
        The global ModelRouter instance.
    """
    if _global_router is None:
        raise RuntimeError(
            "Model router not initialized. Call init_model_router() first."
        )
    return _global_router


async def shutdown_model_router() -> None:
    """
    Shutdown the global model router.
    """
    global _global_router

    if _global_router is not None:
        await _global_router.shutdown()
        _global_router = None
