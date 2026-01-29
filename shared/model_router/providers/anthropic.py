# ============================================================================
# Anthropic Provider Implementation
# ============================================================================
# Purpose: LLM provider implementation for Anthropic Claude models
#
# Why Anthropic?
# - Alternative provider for specialized tasks
# - Claude models excel at nuanced reasoning
# - Available via Azure Foundry (stays in Azure perimeter)
# - Direct API also supported for development
#
# Architecture Decision:
# - Supports both Azure Foundry (via Azure OpenAI API) and direct Anthropic API
# - Translates Anthropic message format to/from unified format
# - Same cost tracking integration as other providers
#
# Related Documentation:
# - Anthropic API: https://docs.anthropic.com/claude/reference/
# - Azure Foundry Models: https://learn.microsoft.com/azure/ai-foundry/
# - CLAUDE.md#pii-tokenization - PII handling for direct API calls
#
# Cost Impact (per 1M tokens, Jan 2026):
# - Claude 3 Haiku: $0.25 input, $1.25 output
# - Claude 3 Sonnet: $3.00 input, $15.00 output
# - Claude 3 Opus: $15.00 input, $75.00 output
# ============================================================================

import json
import logging
import os
import time
from typing import Optional, List, Dict, Any

from ..models import (
    LLMProvider,
    ModelCapability,
    ProviderConfig,
    ModelConfig,
    LLMRequest,
    LLMResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from ..base import BaseLLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider implementation.

    Supports:
    - Direct Anthropic API access
    - Azure Foundry (Claude via Azure)

    Note: Anthropic does not natively support embeddings.
    For embeddings, use Azure OpenAI or another provider.

    Usage:
        config = ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            endpoint="https://api.anthropic.com",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        provider = AnthropicProvider(config)
        await provider.initialize()

        response = await provider.chat_completion(LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-3-haiku-20240307",
        ))
    """

    # Model configurations with cost tracking
    # Costs per 1M tokens (Jan 2026 pricing)
    DEFAULT_MODELS = {
        "claude-3-haiku-20240307": ModelConfig(
            name="claude-3-haiku-20240307",
            provider=LLMProvider.ANTHROPIC,
            capability=ModelCapability.CHAT,
            max_tokens=200000,
            supports_json_mode=False,  # Anthropic uses different approach
            cost_per_million_input=0.25,
            cost_per_million_output=1.25,
            default_temperature=0.0,
        ),
        "claude-3-sonnet-20240229": ModelConfig(
            name="claude-3-sonnet-20240229",
            provider=LLMProvider.ANTHROPIC,
            capability=ModelCapability.CHAT,
            max_tokens=200000,
            supports_json_mode=False,
            cost_per_million_input=3.00,
            cost_per_million_output=15.00,
            default_temperature=0.7,
        ),
        "claude-3-opus-20240229": ModelConfig(
            name="claude-3-opus-20240229",
            provider=LLMProvider.ANTHROPIC,
            capability=ModelCapability.CHAT,
            max_tokens=200000,
            supports_json_mode=False,
            cost_per_million_input=15.00,
            cost_per_million_output=75.00,
            default_temperature=0.7,
        ),
        # Shorter aliases
        "claude-3-haiku": ModelConfig(
            name="claude-3-haiku-20240307",
            provider=LLMProvider.ANTHROPIC,
            capability=ModelCapability.CHAT,
            max_tokens=200000,
            supports_json_mode=False,
            cost_per_million_input=0.25,
            cost_per_million_output=1.25,
            default_temperature=0.0,
        ),
        "claude-3-sonnet": ModelConfig(
            name="claude-3-sonnet-20240229",
            provider=LLMProvider.ANTHROPIC,
            capability=ModelCapability.CHAT,
            max_tokens=200000,
            supports_json_mode=False,
            cost_per_million_input=3.00,
            cost_per_million_output=15.00,
            default_temperature=0.7,
        ),
    }

    def __init__(self, config: ProviderConfig):
        """
        Initialize Anthropic provider.

        Args:
            config: Provider configuration with endpoint and API key.
        """
        super().__init__(config)
        self._models: Dict[str, ModelConfig] = {}
        self._is_azure_foundry = "azure" in config.endpoint.lower()

    async def initialize(self) -> bool:
        """
        Initialize the Anthropic client.

        Returns:
            True if initialization succeeded.
        """
        if self._initialized:
            return True

        try:
            from anthropic import AsyncAnthropic

            # Initialize client
            self._client = AsyncAnthropic(
                api_key=self.config.api_key,
                max_retries=self.config.max_retries,
                timeout=self.config.timeout,
            )

            # Load models
            self._models = dict(self.DEFAULT_MODELS)

            self._initialized = True
            logger.info("Anthropic provider initialized")
            return True

        except ImportError as e:
            logger.error(f"anthropic package not installed: {e}")
            logger.error("Install with: pip install anthropic")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic: {e}")
            return False

    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple:
        """
        Convert unified message format to Anthropic format.

        Anthropic uses:
        - Separate system parameter (not in messages)
        - messages list with user/assistant roles only

        Args:
            messages: List of {"role": "system/user/assistant", "content": "..."}

        Returns:
            Tuple of (system_message, anthropic_messages)
        """
        system_message = ""
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                # Anthropic takes system as separate parameter
                system_message = content
            else:
                # Map role to Anthropic format
                anthropic_role = "user" if role == "user" else "assistant"
                anthropic_messages.append({
                    "role": anthropic_role,
                    "content": content,
                })

        return system_message, anthropic_messages

    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a chat completion using Anthropic Claude.

        Args:
            request: LLMRequest with messages, model, and parameters.

        Returns:
            LLMResponse with generated content and token usage.

        Raises:
            RuntimeError: If provider not initialized.
            Exception: API errors from Anthropic.
        """
        if not self._initialized:
            raise RuntimeError("Anthropic provider not initialized")

        await self._pre_request_hook(request)
        start_time = time.time()

        try:
            # Get model config
            model_config = self._models.get(
                request.model, self.DEFAULT_MODELS.get("claude-3-haiku")
            )

            # Convert messages to Anthropic format
            system_message, anthropic_messages = self._convert_messages(request.messages)

            # Build request parameters
            params: Dict[str, Any] = {
                "model": model_config.name,
                "messages": anthropic_messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }

            # Add system message if present
            if system_message:
                params["system"] = system_message

            # Make API call
            response = await self._client.messages.create(**params)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Extract response
            content = ""
            if response.content and len(response.content) > 0:
                content = response.content[0].text

            # Get token usage
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens

            # Calculate cost
            input_cost = (prompt_tokens / 1_000_000) * model_config.cost_per_million_input
            output_cost = (completion_tokens / 1_000_000) * model_config.cost_per_million_output
            estimated_cost = input_cost + output_cost

            # Build response
            llm_response = LLMResponse(
                content=content,
                model=request.model,
                provider=LLMProvider.ANTHROPIC,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
                request_id=request.request_id,
                finish_reason=response.stop_reason,
                latency_ms=latency_ms,
            )

            await self._post_request_hook(request, llm_response, latency_ms)

            return llm_response

        except Exception as e:
            await self._handle_error(request, e)
            raise

    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings (not supported by Anthropic).

        Anthropic does not natively support embeddings.
        Use Azure OpenAI or another provider for embeddings.

        Args:
            request: EmbeddingRequest (ignored).

        Raises:
            NotImplementedError: Always, as Anthropic doesn't support embeddings.
        """
        raise NotImplementedError(
            "Anthropic does not support embeddings. "
            "Use Azure OpenAI (text-embedding-3-large) instead."
        )

    async def get_available_models(self) -> List[ModelConfig]:
        """
        Get list of available models.

        Returns:
            List of ModelConfig objects.
        """
        return list(self._models.values())

    async def health_check(self) -> bool:
        """
        Check if Anthropic is healthy.

        Makes a lightweight API call to verify connectivity.

        Returns:
            True if healthy, False otherwise.
        """
        if not self._initialized:
            return False

        try:
            # Make a minimal API call
            response = await self._client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return response.content is not None

        except Exception as e:
            logger.warning(f"Anthropic health check failed: {e}")
            return False

    async def shutdown(self) -> None:
        """
        Shutdown the provider and release resources.
        """
        if self._client:
            # AsyncAnthropic doesn't require explicit close
            self._client = None
            self._initialized = False
            logger.info("Anthropic provider shutdown")
