# ============================================================================
# Mock Provider Implementation
# ============================================================================
# Purpose: Mock LLM provider for local development and testing
#
# Why a mock provider?
# - Enables local development without API costs ($0/month)
# - Consistent test fixtures for reproducible testing
# - Simulates various response scenarios (success, error, latency)
# - Validates agent logic independently of LLM behavior
#
# Architecture Decision:
# - Configurable canned responses for different intents
# - Simulated latency for realistic testing
# - Token counting to validate cost tracking
# - Error injection for resilience testing
#
# Related Documentation:
# - CLAUDE.md#phase-1-3-none - Local development with mocks
# - tests/unit/ - Unit tests use this provider
# - mocks/ - Other mock services in the project
#
# Cost Impact: $0 (no API calls)
# ============================================================================

import asyncio
import hashlib
import json
import logging
import random
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


class MockProvider(BaseLLMProvider):
    """
    Mock LLM provider for testing and local development.

    Features:
    - Configurable canned responses
    - Simulated latency
    - Token counting (approximate)
    - Error injection for testing
    - Deterministic or random response modes

    Usage:
        config = ProviderConfig(
            provider=LLMProvider.LOCAL,
            endpoint="mock://localhost",
            extra_config={
                "latency_ms": 100,
                "error_rate": 0.0,
                "responses": {
                    "intent": {"intent": "order_status", "confidence": 0.95}
                }
            }
        )
        provider = MockProvider(config)
        await provider.initialize()

        response = await provider.chat_completion(LLMRequest(
            messages=[{"role": "user", "content": "Where is my order?"}],
            model="mock-gpt-4o-mini",
        ))
    """

    # Default canned responses by task type
    DEFAULT_RESPONSES = {
        "intent_classification": {
            "intent": "general_inquiry",
            "confidence": 0.85,
            "sub_intent": None,
        },
        "content_validation": {
            "action": "PASS",
            "reason": "Content is appropriate",
            "confidence": 0.95,
        },
        "escalation_detection": {
            "escalate": False,
            "confidence": 0.90,
            "reason": "Routine inquiry, no escalation needed",
        },
        "response_generation": {
            "response": "Thank you for contacting us! I'd be happy to help you with your inquiry. "
            "Let me look into that for you. Is there anything specific you'd like me to check?"
        },
        "default": {
            "response": "This is a mock response for testing purposes."
        },
    }

    # Mock model configurations
    DEFAULT_MODELS = {
        "mock-gpt-4o-mini": ModelConfig(
            name="mock-gpt-4o-mini",
            provider=LLMProvider.LOCAL,
            capability=ModelCapability.CHAT,
            max_tokens=4096,
            supports_json_mode=True,
            cost_per_million_input=0.0,
            cost_per_million_output=0.0,
            default_temperature=0.0,
        ),
        "mock-gpt-4o": ModelConfig(
            name="mock-gpt-4o",
            provider=LLMProvider.LOCAL,
            capability=ModelCapability.CHAT,
            max_tokens=4096,
            supports_json_mode=True,
            cost_per_million_input=0.0,
            cost_per_million_output=0.0,
            default_temperature=0.7,
        ),
        "mock-embedding": ModelConfig(
            name="mock-embedding",
            provider=LLMProvider.LOCAL,
            capability=ModelCapability.EMBEDDING,
            max_tokens=8191,
            supports_json_mode=False,
            supports_streaming=False,
            cost_per_million_input=0.0,
            cost_per_million_output=0.0,
        ),
    }

    def __init__(self, config: ProviderConfig):
        """
        Initialize mock provider.

        Args:
            config: Provider configuration with optional extra_config:
                - latency_ms: Simulated latency in milliseconds (default: 50)
                - error_rate: Probability of simulated errors (default: 0.0)
                - responses: Custom canned responses by task type
                - deterministic: If True, responses are consistent (default: True)
        """
        super().__init__(config)

        # Extract mock-specific config
        extra = config.extra_config or {}
        self._latency_ms = extra.get("latency_ms", 50)
        self._error_rate = extra.get("error_rate", 0.0)
        self._custom_responses = extra.get("responses", {})
        self._deterministic = extra.get("deterministic", True)

        # Merge custom responses with defaults
        self._responses = dict(self.DEFAULT_RESPONSES)
        self._responses.update(self._custom_responses)

        self._models: Dict[str, ModelConfig] = {}
        self._embedding_dimension = 1536  # Match text-embedding-3-large

    async def initialize(self) -> bool:
        """
        Initialize the mock provider.

        Returns:
            True always (mock doesn't need real initialization).
        """
        if self._initialized:
            return True

        self._models = dict(self.DEFAULT_MODELS)
        self._initialized = True
        logger.info(
            f"Mock provider initialized: latency={self._latency_ms}ms, "
            f"error_rate={self._error_rate}"
        )
        return True

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses ~4 characters per token approximation.
        """
        return max(1, len(text) // 4)

    def _detect_task_type(self, request: LLMRequest) -> str:
        """
        Detect task type from request to select appropriate response.

        Args:
            request: The LLM request.

        Returns:
            Task type string (e.g., "intent_classification", "response_generation").
        """
        # Check task_type hint
        if request.task_type:
            return request.task_type

        # Check system message for hints
        system_content = ""
        for msg in request.messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "").lower()
                break

        # Pattern matching on system prompt
        if "intent" in system_content or "classify" in system_content:
            return "intent_classification"
        elif "validate" in system_content or "content" in system_content:
            return "content_validation"
        elif "escalat" in system_content:
            return "escalation_detection"
        elif "response" in system_content or "generate" in system_content:
            return "response_generation"

        return "default"

    def _get_response_content(self, request: LLMRequest) -> str:
        """
        Get response content based on task type.

        Args:
            request: The LLM request.

        Returns:
            Response content string (may be JSON).
        """
        task_type = self._detect_task_type(request)
        response_data = self._responses.get(task_type, self._responses["default"])

        # If JSON mode, return JSON string
        if request.json_mode:
            return json.dumps(response_data)

        # For non-JSON, return as string
        if isinstance(response_data, dict):
            return response_data.get("response", json.dumps(response_data))

        return str(response_data)

    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a mock chat completion.

        Args:
            request: LLMRequest with messages, model, and parameters.

        Returns:
            LLMResponse with mock content and simulated token usage.

        Raises:
            RuntimeError: If error injection is triggered.
        """
        if not self._initialized:
            raise RuntimeError("Mock provider not initialized")

        await self._pre_request_hook(request)
        start_time = time.time()

        try:
            # Check for error injection
            if self._error_rate > 0 and random.random() < self._error_rate:
                raise RuntimeError("Mock provider simulated error")

            # Simulate latency
            if self._latency_ms > 0:
                # Add some variation if not deterministic
                latency = self._latency_ms
                if not self._deterministic:
                    latency = int(latency * (0.5 + random.random()))
                await asyncio.sleep(latency / 1000)

            # Get response content
            content = self._get_response_content(request)

            # Calculate simulated latency
            latency_ms = (time.time() - start_time) * 1000

            # Estimate tokens
            prompt_text = " ".join(msg.get("content", "") for msg in request.messages)
            prompt_tokens = self._estimate_tokens(prompt_text)
            completion_tokens = self._estimate_tokens(content)
            total_tokens = prompt_tokens + completion_tokens

            # Build response
            llm_response = LLMResponse(
                content=content,
                model=request.model,
                provider=LLMProvider.LOCAL,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=0.0,  # Mock is free
                request_id=request.request_id,
                finish_reason="stop",
                latency_ms=latency_ms,
            )

            await self._post_request_hook(request, llm_response, latency_ms)

            return llm_response

        except Exception as e:
            await self._handle_error(request, e)
            raise

    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate mock embeddings.

        Creates deterministic embeddings based on text content.
        Uses hash of text to generate consistent pseudo-random vectors.

        Args:
            request: EmbeddingRequest with texts.

        Returns:
            EmbeddingResponse with mock embedding vectors.
        """
        if not self._initialized:
            raise RuntimeError("Mock provider not initialized")

        start_time = time.time()

        # Simulate latency
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000)

        embeddings = []
        total_tokens = 0

        for text in request.texts:
            # Generate deterministic embedding from text hash
            embedding = self._generate_deterministic_embedding(text)
            embeddings.append(embedding)
            total_tokens += self._estimate_tokens(text)

        latency_ms = (time.time() - start_time) * 1000

        return EmbeddingResponse(
            embeddings=embeddings,
            model=request.model,
            provider=LLMProvider.LOCAL,
            dimensions=self._embedding_dimension,
            prompt_tokens=total_tokens,
            estimated_cost=0.0,
            request_id=request.request_id,
            latency_ms=latency_ms,
        )

    def _generate_deterministic_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic embedding vector from text.

        Uses SHA-256 hash to seed a random generator for consistency.
        """
        # Use hash of text to seed random generator
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)
        rng = random.Random(seed)

        # Generate normalized embedding vector
        embedding = [rng.gauss(0, 1) for _ in range(self._embedding_dimension)]

        # Normalize to unit length
        magnitude = sum(x * x for x in embedding) ** 0.5
        return [x / magnitude for x in embedding]

    async def get_available_models(self) -> List[ModelConfig]:
        """
        Get list of available mock models.

        Returns:
            List of ModelConfig objects.
        """
        return list(self._models.values())

    async def health_check(self) -> bool:
        """
        Check if mock provider is healthy.

        Returns:
            True always (mock is always healthy unless disabled).
        """
        return self._initialized and self.config.enabled

    async def shutdown(self) -> None:
        """
        Shutdown the mock provider.
        """
        self._initialized = False
        logger.info("Mock provider shutdown")

    # =========================================================================
    # Test helper methods
    # =========================================================================

    def set_response(self, task_type: str, response: Any) -> None:
        """
        Set a custom response for a task type (for testing).

        Args:
            task_type: Task type (e.g., "intent_classification")
            response: Response data (dict or string)
        """
        self._responses[task_type] = response

    def set_error_rate(self, rate: float) -> None:
        """
        Set error injection rate (for testing).

        Args:
            rate: Probability of error (0.0 to 1.0)
        """
        self._error_rate = max(0.0, min(1.0, rate))

    def set_latency(self, latency_ms: int) -> None:
        """
        Set simulated latency (for testing).

        Args:
            latency_ms: Latency in milliseconds
        """
        self._latency_ms = max(0, latency_ms)

    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._total_requests = 0
        self._successful_requests = 0
        self._total_latency_ms = 0.0
        self._consecutive_failures = 0
        self._request_timestamps = []
