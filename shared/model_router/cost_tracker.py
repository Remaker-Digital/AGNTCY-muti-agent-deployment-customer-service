# ============================================================================
# Model Router Cost Tracker
# ============================================================================
# Purpose: Cost tracking integration for the model router
#
# Why a separate cost tracker?
# - Extends existing cost_monitor.py with provider-aware tracking
# - Tracks costs by provider, model, and agent
# - Enables cost comparison across providers
# - Supports budget alerts per provider
#
# Architecture Decision:
# - Integrates with existing CostMonitor singleton
# - Adds provider dimension to cost tracking
# - Provides comparison metrics for optimization
#
# Related Documentation:
# - shared/cost_monitor.py - Base cost monitoring
# - CLAUDE.md#cost-optimization-principles - Budget management
# - docs/AUTO-SCALING-ARCHITECTURE.md - Cost targets
#
# Cost Impact:
# - Enables data-driven provider selection
# - Supports cost optimization decisions
# - Provides budget visibility across providers
# ============================================================================

import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .models import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderCostRecord:
    """Cost record for a single provider."""

    provider: LLMProvider
    total_requests: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0
    fallback_requests: int = 0  # Requests that fell back from another provider
    failed_requests: int = 0

    # By model breakdown
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # By agent breakdown
    by_agent: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class CostComparison:
    """Comparison of costs across providers."""

    report_time: datetime
    providers: Dict[str, ProviderCostRecord]
    total_cost: float
    total_requests: int
    total_tokens: int

    # Recommendations
    cheapest_provider: Optional[str] = None
    most_reliable_provider: Optional[str] = None
    recommended_provider: Optional[str] = None


class ModelCostTracker:
    """
    Cost tracking for the model router with provider comparison.

    Features:
    - Track costs by provider, model, and agent
    - Compare costs across providers
    - Generate optimization recommendations
    - Budget alerting per provider

    Usage:
        tracker = ModelCostTracker()

        # Record usage
        await tracker.record_usage(
            agent_name="intent_classifier",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.00015,
            provider=LLMProvider.AZURE_OPENAI,
        )

        # Get comparison
        comparison = tracker.get_cost_comparison()
    """

    # Default monthly budgets per provider
    DEFAULT_BUDGETS = {
        LLMProvider.AZURE_OPENAI: 50.0,  # ~$48-62/month target
        LLMProvider.ANTHROPIC: 20.0,  # Secondary provider budget
        LLMProvider.LOCAL: 0.0,  # Mock is free
    }

    def __init__(self, budgets: Optional[Dict[LLMProvider, float]] = None):
        """
        Initialize the cost tracker.

        Args:
            budgets: Optional budget overrides per provider
        """
        self._budgets = budgets or dict(self.DEFAULT_BUDGETS)
        self._provider_costs: Dict[LLMProvider, ProviderCostRecord] = {}
        self._period_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        # Initialize records for all providers
        for provider in LLMProvider:
            self._provider_costs[provider] = ProviderCostRecord(provider=provider)

    async def record_usage(
        self,
        agent_name: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float,
        provider: LLMProvider,
        fallback_used: bool = False,
    ) -> None:
        """
        Record token usage for cost tracking.

        Args:
            agent_name: Name of the agent making the request
            model: Model used
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            estimated_cost: Cost in USD
            provider: Provider used
            fallback_used: If this was a fallback request
        """
        record = self._provider_costs[provider]

        # Update provider totals
        record.total_requests += 1
        record.total_tokens += prompt_tokens + completion_tokens
        record.prompt_tokens += prompt_tokens
        record.completion_tokens += completion_tokens
        record.estimated_cost += estimated_cost

        if fallback_used:
            record.fallback_requests += 1

        # Update by-model breakdown
        if model not in record.by_model:
            record.by_model[model] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0,
            }
        record.by_model[model]["requests"] += 1
        record.by_model[model]["tokens"] += prompt_tokens + completion_tokens
        record.by_model[model]["cost"] += estimated_cost

        # Update by-agent breakdown
        if agent_name not in record.by_agent:
            record.by_agent[agent_name] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0,
            }
        record.by_agent[agent_name]["requests"] += 1
        record.by_agent[agent_name]["tokens"] += prompt_tokens + completion_tokens
        record.by_agent[agent_name]["cost"] += estimated_cost

        # Check budget alerts
        self._check_budget_alerts(provider)

        logger.debug(
            f"Recorded usage: provider={provider.value}, model={model}, "
            f"tokens={prompt_tokens + completion_tokens}, cost=${estimated_cost:.6f}"
        )

    def record_failure(self, provider: LLMProvider) -> None:
        """
        Record a failed request for reliability tracking.

        Args:
            provider: Provider that failed
        """
        self._provider_costs[provider].failed_requests += 1

    def _check_budget_alerts(self, provider: LLMProvider) -> None:
        """Check and trigger budget alerts for a provider."""
        record = self._provider_costs[provider]
        budget = self._budgets.get(provider, 0)

        if budget <= 0:
            return

        usage_pct = record.estimated_cost / budget

        if usage_pct >= 0.8:
            logger.warning(
                f"BUDGET ALERT: {provider.value} at {usage_pct:.1%} "
                f"(${record.estimated_cost:.2f} / ${budget:.2f})"
            )

        if usage_pct >= 1.0:
            logger.error(
                f"BUDGET EXCEEDED: {provider.value} at {usage_pct:.1%} "
                f"(${record.estimated_cost:.2f} / ${budget:.2f})"
            )

    def get_provider_summary(self, provider: LLMProvider) -> Dict[str, Any]:
        """
        Get summary for a specific provider.

        Args:
            provider: Provider to summarize

        Returns:
            Summary dict with costs and usage.
        """
        record = self._provider_costs[provider]
        budget = self._budgets.get(provider, 0)

        return {
            "provider": provider.value,
            "total_requests": record.total_requests,
            "total_tokens": record.total_tokens,
            "estimated_cost": round(record.estimated_cost, 4),
            "budget": budget,
            "budget_remaining": round(max(0, budget - record.estimated_cost), 2),
            "budget_used_pct": (
                round(record.estimated_cost / budget * 100, 1) if budget > 0 else 0
            ),
            "fallback_requests": record.fallback_requests,
            "failed_requests": record.failed_requests,
            "success_rate": (
                round((record.total_requests - record.failed_requests)
                      / record.total_requests * 100, 1)
                if record.total_requests > 0
                else 100.0
            ),
            "by_model": record.by_model,
            "by_agent": record.by_agent,
        }

    def get_cost_comparison(self) -> CostComparison:
        """
        Compare costs across all providers.

        Returns:
            CostComparison with analysis and recommendations.
        """
        total_cost = sum(r.estimated_cost for r in self._provider_costs.values())
        total_requests = sum(r.total_requests for r in self._provider_costs.values())
        total_tokens = sum(r.total_tokens for r in self._provider_costs.values())

        # Find cheapest provider (with usage)
        cheapest = None
        cheapest_cost_per_token = float("inf")
        for provider, record in self._provider_costs.items():
            if record.total_tokens > 0:
                cost_per_token = record.estimated_cost / record.total_tokens
                if cost_per_token < cheapest_cost_per_token:
                    cheapest_cost_per_token = cost_per_token
                    cheapest = provider.value

        # Find most reliable provider
        most_reliable = None
        best_success_rate = 0.0
        for provider, record in self._provider_costs.items():
            if record.total_requests > 0:
                success_rate = (record.total_requests - record.failed_requests) / record.total_requests
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    most_reliable = provider.value

        # Recommendation: balance cost and reliability
        recommended = self._get_recommendation()

        return CostComparison(
            report_time=datetime.utcnow(),
            providers=self._provider_costs,
            total_cost=total_cost,
            total_requests=total_requests,
            total_tokens=total_tokens,
            cheapest_provider=cheapest,
            most_reliable_provider=most_reliable,
            recommended_provider=recommended,
        )

    def _get_recommendation(self) -> Optional[str]:
        """
        Get recommended provider based on cost and reliability.

        Uses weighted scoring: 60% reliability, 40% cost efficiency.
        """
        best_score = 0.0
        recommended = None

        for provider, record in self._provider_costs.items():
            if record.total_requests == 0:
                continue

            # Reliability score (0-1)
            reliability = (record.total_requests - record.failed_requests) / record.total_requests

            # Cost efficiency score (0-1, relative to budget)
            budget = self._budgets.get(provider, 1)
            cost_efficiency = 1 - min(1, record.estimated_cost / budget if budget > 0 else 0)

            # Weighted score
            score = (reliability * 0.6) + (cost_efficiency * 0.4)

            if score > best_score:
                best_score = score
                recommended = provider.value

        return recommended

    def get_summary(self) -> Dict[str, Any]:
        """
        Get overall cost summary.

        Returns:
            Summary dict with aggregated costs.
        """
        comparison = self.get_cost_comparison()

        return {
            "period_start": self._period_start.isoformat(),
            "report_time": datetime.utcnow().isoformat(),
            "total_cost": round(comparison.total_cost, 4),
            "total_requests": comparison.total_requests,
            "total_tokens": comparison.total_tokens,
            "by_provider": {
                p.value: self.get_provider_summary(p)
                for p in LLMProvider
                if self._provider_costs[p].total_requests > 0
            },
            "recommendations": {
                "cheapest_provider": comparison.cheapest_provider,
                "most_reliable_provider": comparison.most_reliable_provider,
                "recommended_provider": comparison.recommended_provider,
            },
        }

    def reset(self) -> None:
        """Reset all cost tracking for new billing period."""
        for provider in LLMProvider:
            self._provider_costs[provider] = ProviderCostRecord(provider=provider)
        self._period_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        logger.info("Cost tracker reset for new billing period")


# ============================================================================
# Global Cost Tracker Instance
# ============================================================================

_global_tracker: Optional[ModelCostTracker] = None


def get_model_cost_tracker() -> ModelCostTracker:
    """
    Get the global model cost tracker instance.

    Returns:
        ModelCostTracker instance (creates one if not exists).
    """
    global _global_tracker

    if _global_tracker is None:
        _global_tracker = ModelCostTracker()

    return _global_tracker


def reset_model_cost_tracker() -> None:
    """Reset the global cost tracker."""
    global _global_tracker

    if _global_tracker is not None:
        _global_tracker.reset()
