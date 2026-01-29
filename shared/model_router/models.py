# ============================================================================
# Model Router Data Models
# ============================================================================
# Purpose: Data classes and enums for the model router abstraction layer
#
# Why these models?
# - Type safety for provider configurations
# - Consistent request/response format across providers
# - Support for different model capabilities (chat, embeddings, validation)
#
# Architecture Decision:
# - Dataclasses for immutable, typed configurations
# - Enums for type-safe provider and capability identification
# - Separate request/response models for chat vs embeddings
#
# Related Documentation:
# - docs/architecture-requirements-phase2-5.md#rag-differentiated-models
# - shared/azure_openai.py - AzureOpenAIConfig reference
# ============================================================================

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class LLMProvider(Enum):
    """
    Supported LLM providers.

    Why these providers?
    - AZURE_OPENAI: Primary provider (within Azure secure perimeter, no PII tokenization)
    - ANTHROPIC: Alternative for specialized tasks (Claude via Azure Foundry)
    - LOCAL: Mock/local models for testing and development
    """
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class ModelCapability(Enum):
    """
    Model capabilities for routing decisions.

    Why separate capabilities?
    - CHAT: Conversational tasks (intent, response generation)
    - EMBEDDING: Vector embeddings for RAG
    - CLASSIFICATION: Intent classification, content validation
    - CODE: Code generation/analysis (future use)
    """
    CHAT = "chat"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    CODE = "code"


class FallbackStrategy(Enum):
    """
    Fallback strategies when primary provider fails.

    Why multiple strategies?
    - SEQUENTIAL: Try providers in order (cost optimization)
    - ROUND_ROBIN: Distribute load across providers
    - FAILOVER_ONLY: Use secondary only when primary fails
    - NONE: No fallback, fail immediately
    """
    SEQUENTIAL = "sequential"
    ROUND_ROBIN = "round_robin"
    FAILOVER_ONLY = "failover_only"
    NONE = "none"


@dataclass
class ProviderConfig:
    """
    Configuration for an LLM provider.

    Tuning Guidelines:
    - timeout: Start with 30s, increase for complex generations
    - max_retries: 3 is standard, reduce for latency-sensitive tasks
    - priority: Lower number = higher priority (try first)
    - rate_limit_rpm: Requests per minute (Azure: 200, Anthropic: 50)

    Source of Record: CLAUDE.md#cost-optimization-principles
    """
    provider: LLMProvider
    endpoint: str
    api_key: Optional[str] = None
    api_version: str = "2024-02-15-preview"
    priority: int = 1  # Lower = higher priority
    enabled: bool = True
    timeout: float = 30.0
    max_retries: int = 3
    rate_limit_rpm: int = 200

    # Provider-specific settings
    extra_config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_environment(cls, provider: LLMProvider) -> "ProviderConfig":
        """
        Create config from environment variables.

        Environment variable naming convention:
        - Azure: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY
        - Anthropic: ANTHROPIC_ENDPOINT, ANTHROPIC_API_KEY
        - Local: LOCAL_MODEL_ENDPOINT
        """
        prefix = provider.value.upper()

        endpoint = os.getenv(f"{prefix}_ENDPOINT", "")
        api_key = os.getenv(f"{prefix}_API_KEY")

        # Default priority: Azure=1, Anthropic=2, Local=3
        default_priority = {
            LLMProvider.AZURE_OPENAI: 1,
            LLMProvider.ANTHROPIC: 2,
            LLMProvider.LOCAL: 3,
        }

        return cls(
            provider=provider,
            endpoint=endpoint,
            api_key=api_key,
            priority=default_priority.get(provider, 99),
            enabled=bool(endpoint),
        )


@dataclass
class ModelConfig:
    """
    Configuration for a specific model deployment.

    Why model-specific config?
    - Different models have different costs per token
    - Max tokens varies by model (4K to 128K)
    - Some models support JSON mode, others don't

    Cost Reference (per 1M tokens, Jan 2026):
    - gpt-4o-mini: $0.15 input, $0.60 output
    - gpt-4o: $2.50 input, $10.00 output
    - claude-3-haiku: $0.25 input, $1.25 output
    - claude-3-sonnet: $3.00 input, $15.00 output
    - text-embedding-3-large: $0.13 input
    """
    name: str  # Deployment name or model identifier
    provider: LLMProvider
    capability: ModelCapability
    max_tokens: int = 4096
    supports_json_mode: bool = True
    supports_streaming: bool = True

    # Cost tracking (per 1M tokens)
    cost_per_million_input: float = 0.0
    cost_per_million_output: float = 0.0

    # Temperature defaults by capability
    default_temperature: float = field(default=0.0)

    def __post_init__(self):
        """Set default temperatures based on capability."""
        if self.default_temperature == 0.0:
            # Classification tasks need deterministic output
            if self.capability == ModelCapability.CLASSIFICATION:
                self.default_temperature = 0.0
            # Chat tasks benefit from some variation
            elif self.capability == ModelCapability.CHAT:
                self.default_temperature = 0.7


@dataclass
class LLMRequest:
    """
    Unified request format for LLM providers.

    Why unified format?
    - Abstracts provider-specific request formats
    - Enables seamless provider switching
    - Simplifies agent code
    """
    messages: List[Dict[str, str]]  # [{"role": "system", "content": "..."}, ...]
    model: str
    max_tokens: int = 500
    temperature: float = 0.0
    json_mode: bool = False
    stream: bool = False

    # Request metadata
    request_id: Optional[str] = None
    agent_name: Optional[str] = None
    task_type: Optional[str] = None

    # Override defaults
    timeout: Optional[float] = None


@dataclass
class LLMResponse:
    """
    Unified response format from LLM providers.

    Why unified format?
    - Consistent response handling regardless of provider
    - Includes metadata for cost tracking and debugging
    - Supports both text and JSON responses
    """
    content: str
    model: str
    provider: LLMProvider

    # Token usage for cost tracking
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Cost tracking
    estimated_cost: float = 0.0

    # Metadata
    request_id: Optional[str] = None
    finish_reason: Optional[str] = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Error tracking (for fallback scenarios)
    fallback_used: bool = False
    original_provider: Optional[LLMProvider] = None
    error_message: Optional[str] = None


@dataclass
class EmbeddingRequest:
    """
    Request format for embedding generation.

    Why separate from LLMRequest?
    - Embeddings have different parameters (no temperature, no messages)
    - Batch processing is common for embeddings
    - Different cost structure
    """
    texts: List[str]
    model: str

    # Request metadata
    request_id: Optional[str] = None
    agent_name: Optional[str] = None


@dataclass
class EmbeddingResponse:
    """
    Response format for embedding generation.

    Why separate from LLMResponse?
    - Returns vectors instead of text
    - Different token counting (no completion tokens)
    - Batch results
    """
    embeddings: List[List[float]]
    model: str
    provider: LLMProvider
    dimensions: int

    # Token usage
    prompt_tokens: int = 0
    estimated_cost: float = 0.0

    # Metadata
    request_id: Optional[str] = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProviderStatus:
    """
    Health status for a provider.

    Why track status?
    - Enable circuit breaker logic
    - Track provider reliability over time
    - Inform fallback decisions
    """
    provider: LLMProvider
    is_healthy: bool
    is_enabled: bool

    # Circuit breaker state
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    circuit_open: bool = False

    # Performance metrics
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0

    # Capacity
    current_rpm: int = 0
    rate_limit_rpm: int = 200

    def to_dict(self) -> Dict[str, Any]:
        """Export status for monitoring."""
        return {
            "provider": self.provider.value,
            "is_healthy": self.is_healthy,
            "is_enabled": self.is_enabled,
            "circuit_open": self.circuit_open,
            "consecutive_failures": self.consecutive_failures,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": self.success_rate,
            "total_requests": self.total_requests,
            "current_rpm": self.current_rpm,
            "rate_limit_rpm": self.rate_limit_rpm,
        }
