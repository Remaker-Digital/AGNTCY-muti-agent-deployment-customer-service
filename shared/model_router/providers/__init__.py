# ============================================================================
# LLM Provider Implementations
# ============================================================================
# Purpose: Concrete implementations of BaseLLMProvider for each supported provider
#
# Available Providers:
# - AzureOpenAIProvider: Azure OpenAI Service (primary)
# - AnthropicProvider: Anthropic Claude (via Azure Foundry or direct)
# - MockProvider: Local mock for testing/development
#
# Related Documentation:
# - shared/model_router/base.py - Base class definition
# - CLAUDE.md#rag-differentiated-models - Model selection rationale
# ============================================================================

from .azure_openai import AzureOpenAIProvider
from .anthropic import AnthropicProvider
from .mock import MockProvider

__all__ = [
    "AzureOpenAIProvider",
    "AnthropicProvider",
    "MockProvider",
]
