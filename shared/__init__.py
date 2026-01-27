"""
Shared utilities for AGNTCY Multi-Agent Customer Service Platform
Phase 1-4: Foundation for agent communication and coordination

This package provides:
- AgntcyFactory singleton for SDK integration
- Azure OpenAI client for LLM interactions (Phase 4+)
- Common message models and agent cards
- Logging, configuration, and error handling utilities
"""

from shared.factory import get_factory, shutdown_factory
from shared.base_agent import BaseAgent, run_agent
from shared.models import (
    AgentCard,
    CustomerMessage,
    IntentClassificationResult,
    KnowledgeQuery,
    KnowledgeResult,
    ResponseRequest,
    EscalationDecision,
    AnalyticsEvent
)
from shared.utils import (
    setup_logging,
    load_config,
    get_env_or_raise,
    get_env_or_default,
    handle_graceful_shutdown
)

# Azure OpenAI client (Phase 4+)
# Import conditionally to avoid errors if openai package not installed
try:
    from shared.azure_openai import (
        AzureOpenAIClient,
        AzureOpenAIConfig,
        get_openai_client,
        shutdown_openai_client,
        TokenUsage
    )
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False
    AzureOpenAIClient = None
    AzureOpenAIConfig = None
    get_openai_client = None
    shutdown_openai_client = None
    TokenUsage = None

# Cost monitoring (Phase 4+)
from shared.cost_monitor import (
    CostMonitor,
    get_cost_monitor,
    record_openai_usage,
    get_cost_summary
)

# PII Tokenization (Phase 4+)
from shared.tokenization import (
    PIITokenizer,
    PIIDetokenizer,
    PIIDetector,
    PIIField,
    PIIType,
    TokenizationResult,
    TokenStore,
    get_token_store,
)

__all__ = [
    # Factory
    "get_factory",
    "shutdown_factory",

    # Base Agent
    "BaseAgent",
    "run_agent",

    # Models
    "AgentCard",
    "CustomerMessage",
    "IntentClassificationResult",
    "KnowledgeQuery",
    "KnowledgeResult",
    "ResponseRequest",
    "EscalationDecision",
    "AnalyticsEvent",

    # Utils
    "setup_logging",
    "load_config",
    "get_env_or_raise",
    "get_env_or_default",
    "handle_graceful_shutdown",

    # Azure OpenAI (Phase 4+)
    "AzureOpenAIClient",
    "AzureOpenAIConfig",
    "get_openai_client",
    "shutdown_openai_client",
    "TokenUsage",

    # Cost Monitoring (Phase 4+)
    "CostMonitor",
    "get_cost_monitor",
    "record_openai_usage",
    "get_cost_summary",

    # PII Tokenization (Phase 4+)
    "PIITokenizer",
    "PIIDetokenizer",
    "PIIDetector",
    "PIIField",
    "PIIType",
    "TokenizationResult",
    "TokenStore",
    "get_token_store",
]

__version__ = "0.3.0"  # Phase 4: PII Tokenization
