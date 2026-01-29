# ============================================================================
# Model Router Abstraction Layer - Module Exports
# ============================================================================
# Purpose: Unified interface for multiple LLM providers with fallback support
#
# Phase 6 - Issue #168: Model Router Abstraction Layer
# - Abstract LLM provider interface
# - Support for Azure OpenAI, Anthropic, local models
# - Automatic fallback and load balancing
# - Cost tracking per model
#
# Architecture Decision:
# - Strategy pattern for provider implementations
# - Chain of responsibility for fallback logic
# - Observer pattern for cost tracking integration
#
# Related Documentation:
# - CLAUDE.md#model-router-abstraction-layer
# - docs/architecture-requirements-phase2-5.md#rag-differentiated-models
# - shared/azure_openai.py - Existing Azure OpenAI client
# - shared/cost_monitor.py - Cost tracking integration
#
# Cost Impact:
# - Enables provider switching for cost optimization
# - Anthropic Claude via Azure: $3-15/1M tokens (varies by model)
# - Local models: $0 (inference cost only)
# - Fallback reduces failed request costs
# ============================================================================

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

from .router import (
    ModelRouter,
    init_model_router,
    get_model_router,
    shutdown_model_router,
)

from .cost_tracker import (
    ModelCostTracker,
    get_model_cost_tracker,
)

__all__ = [
    # Models and enums
    "LLMProvider",
    "ModelCapability",
    "ProviderConfig",
    "ModelConfig",
    "LLMRequest",
    "LLMResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "ProviderStatus",
    "FallbackStrategy",
    # Base class
    "BaseLLMProvider",
    # Providers
    "AzureOpenAIProvider",
    "AnthropicProvider",
    "MockProvider",
    # Router
    "ModelRouter",
    "init_model_router",
    "get_model_router",
    "shutdown_model_router",
    # Cost tracking
    "ModelCostTracker",
    "get_model_cost_tracker",
]
