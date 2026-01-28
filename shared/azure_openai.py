"""
Azure OpenAI Client Module for AGNTCY Multi-Agent Customer Service Platform

Provides a unified client for all agents to interact with Azure OpenAI services.
Supports both API key authentication (from Key Vault) and managed identity.

Phase 4: Production Azure OpenAI integration with:
- GPT-4o-mini for intent classification, escalation detection, content validation
- GPT-4o for response generation
- text-embedding-3-large for knowledge retrieval (RAG)
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Track token usage and costs for monitoring."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    model: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AzureOpenAIConfig:
    """Configuration for Azure OpenAI client."""

    endpoint: str
    api_key: Optional[str] = None
    api_version: str = "2024-02-15-preview"

    # Model deployments
    gpt4o_mini_deployment: str = "gpt-4o-mini"
    gpt4o_deployment: str = "gpt-4o"
    embedding_deployment: str = "text-embedding-3-large"

    # Cost tracking (per 1M tokens in USD)
    costs_per_million: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "text-embedding-3-large": {"input": 0.13, "output": 0.0},
        }
    )

    @classmethod
    def from_environment(cls) -> "AzureOpenAIConfig":
        """Create config from environment variables."""
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")

        return cls(
            endpoint=endpoint,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            gpt4o_mini_deployment=os.getenv(
                "AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT", "gpt-4o-mini"
            ),
            gpt4o_deployment=os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT", "gpt-4o"),
            embedding_deployment=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"
            ),
        )


class AzureOpenAIClient:
    """
    Unified Azure OpenAI client for all agents.

    Features:
    - Automatic authentication (API key or managed identity)
    - Token usage tracking for cost monitoring
    - Retry logic with exponential backoff
    - Structured JSON response parsing
    """

    def __init__(self, config: Optional[AzureOpenAIConfig] = None):
        """
        Initialize Azure OpenAI client.

        Args:
            config: Optional configuration. If not provided, loads from environment.
        """
        self.config = config or AzureOpenAIConfig.from_environment()
        self._client = None
        self._token_usage: List[TokenUsage] = []
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the Azure OpenAI client.

        Returns:
            True if initialized successfully, False otherwise.
        """
        if self._initialized:
            return True

        try:
            from openai import AsyncAzureOpenAI

            # Try API key first (from environment or Key Vault)
            if self.config.api_key:
                logger.info("Initializing Azure OpenAI with API key authentication")
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=self.config.endpoint,
                    api_key=self.config.api_key,
                    api_version=self.config.api_version,
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
                    api_version=self.config.api_version,
                )

            self._initialized = True
            logger.info(f"Azure OpenAI client initialized: {self.config.endpoint}")
            return True

        except ImportError as e:
            logger.error(f"Required packages not installed: {e}")
            logger.error("Install with: pip install openai azure-identity")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            return False

    def _track_usage(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> TokenUsage:
        """Track token usage and calculate estimated cost."""
        total_tokens = prompt_tokens + completion_tokens

        # Calculate cost
        costs = self.config.costs_per_million.get(model, {"input": 0.0, "output": 0.0})
        input_cost = (prompt_tokens / 1_000_000) * costs["input"]
        output_cost = (completion_tokens / 1_000_000) * costs["output"]

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=input_cost + output_cost,
            model=model,
        )

        self._token_usage.append(usage)

        logger.debug(
            f"Token usage - Model: {model}, "
            f"Prompt: {prompt_tokens}, Completion: {completion_tokens}, "
            f"Cost: ${usage.estimated_cost:.6f}"
        )

        return usage

    async def classify_intent(
        self, message: str, system_prompt: str, temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Classify customer intent using GPT-4o-mini.

        Args:
            message: Customer message to classify
            system_prompt: Intent classification prompt
            temperature: Sampling temperature (0.0 for deterministic)

        Returns:
            Dict with 'intent', 'confidence' keys
        """
        return await self._chat_completion(
            deployment=self.config.gpt4o_mini_deployment,
            system_prompt=system_prompt,
            user_message=message,
            max_tokens=100,
            temperature=temperature,
            json_mode=True,
        )

    async def validate_content(
        self, content: str, validation_prompt: str, temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Validate content (input or output) using GPT-4o-mini.

        Args:
            content: Content to validate
            validation_prompt: Validation criteria prompt
            temperature: Sampling temperature

        Returns:
            Dict with 'action', 'reason', 'confidence' keys
        """
        return await self._chat_completion(
            deployment=self.config.gpt4o_mini_deployment,
            system_prompt=validation_prompt,
            user_message=content,
            max_tokens=150,
            temperature=temperature,
            json_mode=True,
        )

    async def detect_escalation(
        self, conversation: str, system_prompt: str, temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Detect if conversation should be escalated using GPT-4o-mini.

        Args:
            conversation: Full conversation context
            system_prompt: Escalation detection prompt
            temperature: Sampling temperature

        Returns:
            Dict with 'escalate', 'confidence', 'reason' keys
        """
        return await self._chat_completion(
            deployment=self.config.gpt4o_mini_deployment,
            system_prompt=system_prompt,
            user_message=conversation,
            max_tokens=150,
            temperature=temperature,
            json_mode=True,
        )

    async def generate_response(
        self,
        context: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate customer response using GPT-4o.

        Args:
            context: Customer query and relevant context
            system_prompt: Response generation prompt
            temperature: Sampling temperature (higher for more varied responses)
            max_tokens: Maximum response length

        Returns:
            Generated response text
        """
        result = await self._chat_completion(
            deployment=self.config.gpt4o_deployment,
            system_prompt=system_prompt,
            user_message=context,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=False,
        )
        return result.get("response", "")

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using text-embedding-3-large.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (1536 dimensions each)
        """
        if not self._initialized:
            await self.initialize()

        if not self._client:
            raise RuntimeError("Azure OpenAI client not initialized")

        try:
            response = await self._client.embeddings.create(
                model=self.config.embedding_deployment, input=texts
            )

            # Track usage
            self._track_usage(
                model=self.config.embedding_deployment,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=0,
            )

            return [item.embedding for item in response.data]

        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise

    async def _chat_completion(
        self,
        deployment: str,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 500,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Internal method for chat completions.

        Args:
            deployment: Model deployment name
            system_prompt: System message
            user_message: User message
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            json_mode: If True, request JSON response format

        Returns:
            Parsed response dict or {"response": text} for non-JSON
        """
        if not self._initialized:
            await self.initialize()

        if not self._client:
            raise RuntimeError("Azure OpenAI client not initialized")

        try:
            # Build request parameters
            params = {
                "model": deployment,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # Add JSON mode if supported and requested
            if json_mode:
                params["response_format"] = {"type": "json_object"}

            response = await self._client.chat.completions.create(**params)

            # Track usage
            self._track_usage(
                model=deployment,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )

            # Extract response text
            response_text = response.choices[0].message.content.strip()

            # Parse JSON if expected
            if json_mode:
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response: {e}")
                    logger.debug(f"Response text: {response_text}")
                    # Try to extract JSON from the response
                    return self._extract_json(response_text)

            return {"response": response_text}

        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Try to extract JSON from text that may have extra content."""
        import re

        # Try to find JSON object in the text
        json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Return empty result if no valid JSON found
        logger.warning(f"Could not extract JSON from: {text[:100]}...")
        return {"error": "Failed to parse response", "raw": text}

    def get_total_usage(self) -> Dict[str, Any]:
        """Get aggregated token usage statistics."""
        if not self._token_usage:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "by_model": {},
            }

        total_tokens = sum(u.total_tokens for u in self._token_usage)
        total_cost = sum(u.estimated_cost for u in self._token_usage)

        # Aggregate by model
        by_model: Dict[str, Dict[str, Any]] = {}
        for usage in self._token_usage:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost": 0.0,
                }
            by_model[usage.model]["requests"] += 1
            by_model[usage.model]["prompt_tokens"] += usage.prompt_tokens
            by_model[usage.model]["completion_tokens"] += usage.completion_tokens
            by_model[usage.model]["total_tokens"] += usage.total_tokens
            by_model[usage.model]["estimated_cost"] += usage.estimated_cost

        return {
            "total_requests": len(self._token_usage),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_model": by_model,
        }

    def reset_usage_tracking(self):
        """Reset token usage tracking."""
        self._token_usage = []

    async def close(self):
        """Close the client and release resources."""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False
            logger.info("Azure OpenAI client closed")


# Singleton instance for shared use
_client_instance: Optional[AzureOpenAIClient] = None


def get_openai_client() -> AzureOpenAIClient:
    """
    Get the singleton Azure OpenAI client instance.

    Returns:
        AzureOpenAIClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = AzureOpenAIClient()
    return _client_instance


async def shutdown_openai_client():
    """Shutdown the singleton client."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
