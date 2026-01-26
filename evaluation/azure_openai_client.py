"""
Azure OpenAI API client wrapper for Phase 3.5 evaluation.

This module provides a thin wrapper around the Azure OpenAI API that:
- Tracks token usage and costs
- Provides consistent error handling
- Supports both chat completions and embeddings
- Logs all interactions for analysis

Usage:
    from evaluation.azure_openai_client import AzureOpenAIClient

    client = AzureOpenAIClient.from_env()
    response = client.chat_completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print(f"Response: {response.content}")
    print(f"Cost: ${response.cost:.4f}")
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json

try:
    from openai import AzureOpenAI
except ImportError:
    AzureOpenAI = None
    print("WARNING: openai package not installed. Run: pip install openai")

from evaluation.config import Config, ModelConfig


@dataclass
class ChatResponse:
    """Response from a chat completion request."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    latency_ms: float
    raw_response: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class EmbeddingResponse:
    """Response from an embedding request."""
    embeddings: list[list[float]]
    model: str
    total_tokens: int
    cost: float
    latency_ms: float
    error: Optional[str] = None


@dataclass
class UsageTracker:
    """Tracks cumulative token usage and costs across all requests."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_embedding_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    def add_chat_usage(self, input_tokens: int, output_tokens: int, cost: float) -> None:
        """Record usage from a chat completion."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.request_count += 1

    def add_embedding_usage(self, tokens: int, cost: float) -> None:
        """Record usage from an embedding request."""
        self.total_embedding_tokens += tokens
        self.total_cost += cost
        self.request_count += 1

    def to_dict(self) -> dict:
        """Convert usage stats to dictionary."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_embedding_tokens": self.total_embedding_tokens,
            "total_cost": round(self.total_cost, 4),
            "request_count": self.request_count,
            "session_duration_seconds": (datetime.now() - self.start_time).total_seconds(),
        }


class AzureOpenAIClient:
    """
    Azure OpenAI API client with usage tracking.

    This client wraps the official Azure OpenAI SDK to provide:
    - Automatic token counting and cost calculation
    - Latency measurement
    - Error handling with retries
    - Usage tracking across sessions

    Example:
        client = AzureOpenAIClient.from_env()

        # Chat completion
        response = client.chat_completion(
            model="gpt-4o-mini",
            system_prompt="You are a helpful assistant.",
            user_message="What is 2+2?"
        )

        # Get embeddings
        embeddings = client.get_embeddings(["Hello world", "Goodbye"])
    """

    def __init__(self, config: Config):
        """
        Initialize client with configuration.

        Args:
            config: Configuration object with Azure credentials.
        """
        self.config = config
        self.usage = UsageTracker()
        self._client: Optional[AzureOpenAI] = None

        if AzureOpenAI is None:
            raise ImportError("openai package required. Install with: pip install openai")

    @classmethod
    def from_env(cls) -> "AzureOpenAIClient":
        """Create client from environment variables."""
        config = Config.from_env()
        return cls(config)

    @property
    def client(self) -> AzureOpenAI:
        """Lazy initialization of Azure OpenAI client."""
        if self._client is None:
            if not self.config.is_valid():
                raise ValueError(f"Invalid configuration: {self.config.validate()}")

            self._client = AzureOpenAI(
                azure_endpoint=self.config.azure_endpoint,
                api_key=self.config.azure_api_key,
                api_version=self.config.azure_api_version,
            )
        return self._client

    def _get_model_config(self, model: str) -> ModelConfig:
        """Get model configuration by name."""
        model_lower = model.lower()
        if "4o-mini" in model_lower or "gpt4o-mini" in model_lower:
            return self.config.gpt4o_mini
        elif "4o" in model_lower or "gpt4o" in model_lower:
            return self.config.gpt4o
        elif "embedding" in model_lower:
            return self.config.embedding
        else:
            # Default to gpt-4o-mini for unknown models
            return self.config.gpt4o_mini

    def _calculate_cost(
        self,
        model_config: ModelConfig,
        input_tokens: int,
        output_tokens: int = 0
    ) -> float:
        """Calculate cost for a request."""
        input_cost = (input_tokens / 1000) * model_config.cost_per_1k_input
        output_cost = (output_tokens / 1000) * model_config.cost_per_1k_output
        return input_cost + output_cost

    def chat_completion(
        self,
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None,
        user_message: str = "",
        messages: Optional[list[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> ChatResponse:
        """
        Send a chat completion request.

        Args:
            model: Model name (gpt-4o-mini, gpt-4o)
            system_prompt: System message content
            user_message: User message content
            messages: Full messages array (overrides system_prompt/user_message)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 = deterministic)
            json_mode: Whether to request JSON output

        Returns:
            ChatResponse with content, tokens, cost, and latency.
        """
        model_config = self._get_model_config(model)

        # Build messages
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})

        # Set defaults from model config
        if max_tokens is None:
            max_tokens = model_config.max_tokens
        if temperature is None:
            temperature = model_config.temperature

        # Prepare request
        request_params = {
            "model": model_config.deployment_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if json_mode:
            request_params["response_format"] = {"type": "json_object"}

        # Send request with timing
        start_time = time.perf_counter()
        try:
            response = self.client.chat.completions.create(**request_params)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract response data
            content = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            cost = self._calculate_cost(model_config, input_tokens, output_tokens)

            # Track usage
            self.usage.add_chat_usage(input_tokens, output_tokens, cost)

            return ChatResponse(
                content=content,
                model=model_config.deployment_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ChatResponse(
                content="",
                model=model_config.deployment_name,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost=0.0,
                latency_ms=latency_ms,
                error=str(e),
            )

    def get_embeddings(
        self,
        texts: list[str],
        model: str = "text-embedding-3-large",
    ) -> EmbeddingResponse:
        """
        Get embeddings for a list of texts.

        Args:
            texts: List of strings to embed
            model: Embedding model name

        Returns:
            EmbeddingResponse with embeddings, tokens, cost, and latency.
        """
        model_config = self._get_model_config(model)

        start_time = time.perf_counter()
        try:
            response = self.client.embeddings.create(
                model=model_config.deployment_name,
                input=texts,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            total_tokens = response.usage.total_tokens
            cost = self._calculate_cost(model_config, total_tokens)

            # Track usage
            self.usage.add_embedding_usage(total_tokens, cost)

            return EmbeddingResponse(
                embeddings=embeddings,
                model=model_config.deployment_name,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return EmbeddingResponse(
                embeddings=[],
                model=model_config.deployment_name,
                total_tokens=0,
                cost=0.0,
                latency_ms=latency_ms,
                error=str(e),
            )

    def get_usage_stats(self) -> dict:
        """Get cumulative usage statistics."""
        return self.usage.to_dict()

    def reset_usage(self) -> None:
        """Reset usage tracking."""
        self.usage = UsageTracker()

    def check_budget(self) -> tuple[bool, str]:
        """
        Check if current usage is within budget.

        Returns:
            Tuple of (within_budget, message)
        """
        current_cost = self.usage.total_cost
        limit = self.config.budget_limit
        threshold = self.config.alert_threshold

        if current_cost >= limit:
            return False, f"BUDGET EXCEEDED: ${current_cost:.2f} >= ${limit:.2f}"
        elif current_cost >= limit * threshold:
            return True, f"BUDGET WARNING: ${current_cost:.2f} ({current_cost/limit*100:.1f}% of ${limit:.2f})"
        else:
            return True, f"Budget OK: ${current_cost:.2f} ({current_cost/limit*100:.1f}% of ${limit:.2f})"

    def test_connection(self) -> tuple[bool, str]:
        """
        Test API connection with a minimal request.

        Returns:
            Tuple of (success, message)
        """
        try:
            response = self.chat_completion(
                model="gpt-4o-mini",
                user_message="Reply with exactly: OK",
                max_tokens=5,
            )

            if response.error:
                return False, f"API Error: {response.error}"

            if "OK" in response.content.upper():
                return True, f"Connection successful! Latency: {response.latency_ms:.0f}ms"
            else:
                return True, f"Connection working. Response: {response.content[:50]}"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"


if __name__ == "__main__":
    # Test the client
    print("Testing Azure OpenAI Client...")
    print("-" * 40)

    try:
        client = AzureOpenAIClient.from_env()

        # Test connection
        success, message = client.test_connection()
        print(f"Connection test: {message}")

        if success:
            # Test chat completion
            print("\nTesting chat completion...")
            response = client.chat_completion(
                model="gpt-4o-mini",
                system_prompt="You are a helpful customer service agent.",
                user_message="Where is my order #12345?",
            )
            print(f"Response: {response.content[:100]}...")
            print(f"Tokens: {response.total_tokens}, Cost: ${response.cost:.4f}")
            print(f"Latency: {response.latency_ms:.0f}ms")

            # Print usage
            print(f"\nUsage stats: {json.dumps(client.get_usage_stats(), indent=2)}")

            # Check budget
            within_budget, budget_msg = client.check_budget()
            print(f"Budget: {budget_msg}")

    except Exception as e:
        print(f"Error: {e}")
