# ============================================================================
# Azure OpenAI Provider Implementation
# ============================================================================
# Purpose: LLM provider implementation for Azure OpenAI Service
#
# Why Azure OpenAI?
# - Primary provider (within Azure secure perimeter)
# - No PII tokenization required (data stays in Azure)
# - Cost-effective models (GPT-4o-mini at $0.15/1M tokens)
# - Supports JSON mode for structured outputs
#
# Architecture Decision:
# - Uses existing AzureOpenAIPool for connection management
# - Integrates with cost_monitor for budget tracking
# - Supports both API key and managed identity auth
#
# Related Documentation:
# - Azure OpenAI Quotas: https://learn.microsoft.com/azure/ai-services/openai/quotas-limits
# - shared/openai_pool.py - Connection pooling
# - shared/azure_openai.py - Existing client patterns
#
# Cost Impact:
# - GPT-4o-mini: $0.15 input, $0.60 output per 1M tokens
# - GPT-4o: $2.50 input, $10.00 output per 1M tokens
# - text-embedding-3-large: $0.13 per 1M tokens
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


class AzureOpenAIProvider(BaseLLMProvider):
    """
    Azure OpenAI Service provider implementation.

    Features:
    - Async HTTP client with connection pooling
    - Automatic token tracking for cost monitoring
    - JSON mode support for structured outputs
    - Managed identity or API key authentication
    - Retry logic with exponential backoff

    Usage:
        config = ProviderConfig(
            provider=LLMProvider.AZURE_OPENAI,
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        )
        provider = AzureOpenAIProvider(config)
        await provider.initialize()

        response = await provider.chat_completion(LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o-mini",
        ))
    """

    # Model configurations with cost tracking
    # Costs per 1M tokens (Jan 2026 pricing)
    DEFAULT_MODELS = {
        "gpt-4o-mini": ModelConfig(
            name="gpt-4o-mini",
            provider=LLMProvider.AZURE_OPENAI,
            capability=ModelCapability.CHAT,
            max_tokens=128000,
            supports_json_mode=True,
            cost_per_million_input=0.15,
            cost_per_million_output=0.60,
            default_temperature=0.0,
        ),
        "gpt-4o": ModelConfig(
            name="gpt-4o",
            provider=LLMProvider.AZURE_OPENAI,
            capability=ModelCapability.CHAT,
            max_tokens=128000,
            supports_json_mode=True,
            cost_per_million_input=2.50,
            cost_per_million_output=10.00,
            default_temperature=0.7,
        ),
        "text-embedding-3-large": ModelConfig(
            name="text-embedding-3-large",
            provider=LLMProvider.AZURE_OPENAI,
            capability=ModelCapability.EMBEDDING,
            max_tokens=8191,
            supports_json_mode=False,
            supports_streaming=False,
            cost_per_million_input=0.13,
            cost_per_million_output=0.0,
        ),
    }

    def __init__(self, config: ProviderConfig):
        """
        Initialize Azure OpenAI provider.

        Args:
            config: Provider configuration with endpoint and credentials.
        """
        super().__init__(config)
        self._models: Dict[str, ModelConfig] = {}
        self._api_version = config.api_version or "2024-02-15-preview"

        # Deployment name mappings (can be customized via extra_config)
        self._deployments = config.extra_config.get("deployments", {})

    async def initialize(self) -> bool:
        """
        Initialize the Azure OpenAI async client.

        Returns:
            True if initialization succeeded.
        """
        if self._initialized:
            return True

        try:
            from openai import AsyncAzureOpenAI
            import httpx

            # Configure HTTP client with connection pooling
            http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=20,
                    keepalive_expiry=30.0,
                ),
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=self.config.timeout,
                    write=10.0,
                    pool=5.0,
                ),
            )

            # Initialize client
            if self.config.api_key:
                logger.info("Initializing Azure OpenAI with API key")
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=self.config.endpoint,
                    api_key=self.config.api_key,
                    api_version=self._api_version,
                    http_client=http_client,
                    max_retries=self.config.max_retries,
                )
            else:
                # Fall back to managed identity
                logger.info("Initializing Azure OpenAI with managed identity")
                from azure.identity.aio import DefaultAzureCredential

                credential = DefaultAzureCredential()
                token = await credential.get_token(
                    "https://cognitiveservices.azure.com/.default"
                )

                self._client = AsyncAzureOpenAI(
                    azure_endpoint=self.config.endpoint,
                    azure_ad_token=token.token,
                    api_version=self._api_version,
                    http_client=http_client,
                    max_retries=self.config.max_retries,
                )

            # Load available models
            await self._load_models()

            self._initialized = True
            logger.info(
                f"Azure OpenAI provider initialized: {self.config.endpoint[:30]}..."
            )
            return True

        except ImportError as e:
            logger.error(f"Required packages not installed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI: {e}")
            return False

    async def _load_models(self) -> None:
        """Load available model configurations."""
        # Start with default models
        self._models = dict(self.DEFAULT_MODELS)

        # Override with custom deployments from config
        for name, deployment in self._deployments.items():
            if name in self._models:
                self._models[name].name = deployment

        logger.debug(f"Loaded {len(self._models)} model configurations")

    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a chat completion using Azure OpenAI.

        Args:
            request: LLMRequest with messages, model, and parameters.

        Returns:
            LLMResponse with generated content and token usage.

        Raises:
            RuntimeError: If provider not initialized.
            Exception: API errors from Azure OpenAI.
        """
        if not self._initialized:
            raise RuntimeError("Azure OpenAI provider not initialized")

        await self._pre_request_hook(request)
        start_time = time.time()

        try:
            # Get model config
            model_config = self._models.get(request.model, self.DEFAULT_MODELS.get("gpt-4o-mini"))

            # Build request parameters
            params: Dict[str, Any] = {
                "model": self._deployments.get(request.model, request.model),
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }

            # Add JSON mode if requested and supported
            if request.json_mode and model_config.supports_json_mode:
                params["response_format"] = {"type": "json_object"}

            # Make API call
            response = await self._client.chat.completions.create(**params)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Extract response
            content = response.choices[0].message.content.strip()
            finish_reason = response.choices[0].finish_reason

            # Calculate cost
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens

            input_cost = (prompt_tokens / 1_000_000) * model_config.cost_per_million_input
            output_cost = (completion_tokens / 1_000_000) * model_config.cost_per_million_output
            estimated_cost = input_cost + output_cost

            # Build response
            llm_response = LLMResponse(
                content=content,
                model=request.model,
                provider=LLMProvider.AZURE_OPENAI,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
                request_id=request.request_id,
                finish_reason=finish_reason,
                latency_ms=latency_ms,
            )

            await self._post_request_hook(request, llm_response, latency_ms)

            return llm_response

        except Exception as e:
            await self._handle_error(request, e)
            raise

    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate text embeddings using Azure OpenAI.

        Args:
            request: EmbeddingRequest with texts and model.

        Returns:
            EmbeddingResponse with embedding vectors.

        Raises:
            RuntimeError: If provider not initialized.
            Exception: API errors from Azure OpenAI.
        """
        if not self._initialized:
            raise RuntimeError("Azure OpenAI provider not initialized")

        start_time = time.time()

        try:
            # Get model config
            model_config = self._models.get(
                request.model, self.DEFAULT_MODELS.get("text-embedding-3-large")
            )

            # Make API call
            response = await self._client.embeddings.create(
                model=self._deployments.get(request.model, request.model),
                input=request.texts,
            )

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            dimensions = len(embeddings[0]) if embeddings else 0

            # Calculate cost
            prompt_tokens = response.usage.prompt_tokens
            estimated_cost = (prompt_tokens / 1_000_000) * model_config.cost_per_million_input

            return EmbeddingResponse(
                embeddings=embeddings,
                model=request.model,
                provider=LLMProvider.AZURE_OPENAI,
                dimensions=dimensions,
                prompt_tokens=prompt_tokens,
                estimated_cost=estimated_cost,
                request_id=request.request_id,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def get_available_models(self) -> List[ModelConfig]:
        """
        Get list of available models.

        Returns:
            List of ModelConfig objects.
        """
        return list(self._models.values())

    async def health_check(self) -> bool:
        """
        Check if Azure OpenAI is healthy.

        Makes a lightweight API call to verify connectivity.

        Returns:
            True if healthy, False otherwise.
        """
        if not self._initialized:
            return False

        try:
            # Make a minimal API call
            response = await self._client.chat.completions.create(
                model=self._deployments.get("gpt-4o-mini", "gpt-4o-mini"),
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return response.choices[0].message.content is not None

        except Exception as e:
            logger.warning(f"Azure OpenAI health check failed: {e}")
            return False

    async def shutdown(self) -> None:
        """
        Shutdown the provider and release resources.
        """
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False
            logger.info("Azure OpenAI provider shutdown")
