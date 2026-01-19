"""
Shared utilities for AGNTCY Multi-Agent Customer Service Platform
Phase 1: Foundation for agent communication and coordination

This package provides:
- AgntcyFactory singleton for SDK integration
- Common message models and agent cards
- Logging, configuration, and error handling utilities
"""

from shared.factory import get_factory, shutdown_factory
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

__all__ = [
    # Factory
    "get_factory",
    "shutdown_factory",

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
]

__version__ = "0.1.0"
