"""
Cost Monitoring Module for AGNTCY Multi-Agent Customer Service Platform

Tracks Azure OpenAI token usage and costs across all agents.
Provides aggregated metrics for budget monitoring and optimization.

Phase 4: Production cost tracking with:
- Per-agent token usage tracking
- Real-time cost estimation
- Budget alerts
- Usage reports
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentUsage:
    """Track usage for a single agent."""

    agent_name: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    request_count: int = 0
    last_request: Optional[datetime] = None


@dataclass
class CostReport:
    """Aggregated cost report."""

    report_time: datetime
    period_start: datetime
    period_end: datetime
    total_tokens: int
    total_cost: float
    by_agent: Dict[str, AgentUsage]
    by_model: Dict[str, Dict[str, Any]]
    budget_limit: float
    budget_remaining: float
    budget_alert: bool


class CostMonitor:
    """
    Centralized cost monitoring for Azure OpenAI usage.

    Tracks costs across all agents and provides budget alerts.
    """

    # Cost per 1M tokens (as of Jan 2026)
    COSTS_PER_MILLION = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    }

    # Monthly budget limits (Phase 4: $48-62/month for AI)
    DEFAULT_MONTHLY_BUDGET = 60.00
    ALERT_THRESHOLD = 0.80  # Alert at 80% of budget

    def __init__(self, budget: float = None):
        """
        Initialize cost monitor.

        Args:
            budget: Optional monthly budget override
        """
        self.monthly_budget = budget or float(
            os.getenv("AZURE_OPENAI_MONTHLY_BUDGET", self.DEFAULT_MONTHLY_BUDGET)
        )
        self.usage_by_agent: Dict[str, AgentUsage] = {}
        self.usage_by_model: Dict[str, Dict[str, Any]] = {}
        self.total_cost = 0.0
        self.total_tokens = 0
        self.period_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        self._alerts_sent: List[str] = []

    def record_usage(
        self, agent_name: str, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """
        Record token usage and return estimated cost.

        Args:
            agent_name: Name of the agent
            model: Model used (e.g., 'gpt-4o-mini')
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost for this request
        """
        # Calculate cost
        costs = self.COSTS_PER_MILLION.get(model, {"input": 0.0, "output": 0.0})
        input_cost = (prompt_tokens / 1_000_000) * costs["input"]
        output_cost = (completion_tokens / 1_000_000) * costs["output"]
        request_cost = input_cost + output_cost

        # Update agent usage
        if agent_name not in self.usage_by_agent:
            self.usage_by_agent[agent_name] = AgentUsage(
                agent_name=agent_name, model=model
            )

        agent = self.usage_by_agent[agent_name]
        agent.prompt_tokens += prompt_tokens
        agent.completion_tokens += completion_tokens
        agent.total_tokens += prompt_tokens + completion_tokens
        agent.estimated_cost += request_cost
        agent.request_count += 1
        agent.last_request = datetime.utcnow()

        # Update model usage
        if model not in self.usage_by_model:
            self.usage_by_model[model] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
                "request_count": 0,
            }

        self.usage_by_model[model]["prompt_tokens"] += prompt_tokens
        self.usage_by_model[model]["completion_tokens"] += completion_tokens
        self.usage_by_model[model]["total_tokens"] += prompt_tokens + completion_tokens
        self.usage_by_model[model]["estimated_cost"] += request_cost
        self.usage_by_model[model]["request_count"] += 1

        # Update totals
        self.total_cost += request_cost
        self.total_tokens += prompt_tokens + completion_tokens

        # Check budget alerts
        self._check_budget_alerts()

        return request_cost

    def _check_budget_alerts(self):
        """Check and trigger budget alerts."""
        budget_used_pct = (
            self.total_cost / self.monthly_budget if self.monthly_budget > 0 else 0
        )

        # Alert at 80% budget
        if budget_used_pct >= self.ALERT_THRESHOLD and "80%" not in self._alerts_sent:
            logger.warning(
                f"BUDGET ALERT: Azure OpenAI costs at {budget_used_pct:.1%} of monthly budget "
                f"(${self.total_cost:.2f} / ${self.monthly_budget:.2f})"
            )
            self._alerts_sent.append("80%")

        # Alert at 100% budget
        if budget_used_pct >= 1.0 and "100%" not in self._alerts_sent:
            logger.error(
                f"BUDGET EXCEEDED: Azure OpenAI costs at {budget_used_pct:.1%} of monthly budget "
                f"(${self.total_cost:.2f} / ${self.monthly_budget:.2f})"
            )
            self._alerts_sent.append("100%")

    def get_report(self) -> CostReport:
        """Generate cost report."""
        budget_remaining = max(0, self.monthly_budget - self.total_cost)
        budget_alert = self.total_cost >= (self.monthly_budget * self.ALERT_THRESHOLD)

        return CostReport(
            report_time=datetime.utcnow(),
            period_start=self.period_start,
            period_end=datetime.utcnow(),
            total_tokens=self.total_tokens,
            total_cost=self.total_cost,
            by_agent=self.usage_by_agent,
            by_model=self.usage_by_model,
            budget_limit=self.monthly_budget,
            budget_remaining=budget_remaining,
            budget_alert=budget_alert,
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "budget_limit": self.monthly_budget,
            "budget_remaining": round(max(0, self.monthly_budget - self.total_cost), 2),
            "budget_used_pct": (
                round(self.total_cost / self.monthly_budget * 100, 1)
                if self.monthly_budget > 0
                else 0
            ),
            "agents_active": len(self.usage_by_agent),
            "models_used": list(self.usage_by_model.keys()),
            "period_start": self.period_start.isoformat(),
            "report_time": datetime.utcnow().isoformat(),
        }

    def get_agent_summary(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get summary for a specific agent."""
        if agent_name not in self.usage_by_agent:
            return None

        agent = self.usage_by_agent[agent_name]
        return {
            "agent_name": agent.agent_name,
            "model": agent.model,
            "total_tokens": agent.total_tokens,
            "estimated_cost": round(agent.estimated_cost, 4),
            "request_count": agent.request_count,
            "avg_tokens_per_request": (
                round(agent.total_tokens / agent.request_count, 1)
                if agent.request_count > 0
                else 0
            ),
            "last_request": (
                agent.last_request.isoformat() if agent.last_request else None
            ),
        }

    def export_report(self, filepath: str = None) -> str:
        """Export report to JSON file."""
        if filepath is None:
            filepath = f"cost_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        report = self.get_report()

        # Convert to serializable format
        report_dict = {
            "report_time": report.report_time.isoformat(),
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "total_tokens": report.total_tokens,
            "total_cost": round(report.total_cost, 4),
            "budget_limit": report.budget_limit,
            "budget_remaining": round(report.budget_remaining, 2),
            "budget_alert": report.budget_alert,
            "by_agent": {
                name: {
                    "agent_name": usage.agent_name,
                    "model": usage.model,
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "estimated_cost": round(usage.estimated_cost, 4),
                    "request_count": usage.request_count,
                }
                for name, usage in report.by_agent.items()
            },
            "by_model": report.by_model,
        }

        with open(filepath, "w") as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Cost report exported to {filepath}")
        return filepath

    def reset(self):
        """Reset all counters (for new billing period)."""
        self.usage_by_agent = {}
        self.usage_by_model = {}
        self.total_cost = 0.0
        self.total_tokens = 0
        self.period_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        self._alerts_sent = []
        logger.info("Cost monitor reset for new billing period")


# Singleton instance for global usage
_monitor_instance: Optional[CostMonitor] = None


def get_cost_monitor() -> CostMonitor:
    """
    Get the singleton cost monitor instance.

    Returns:
        CostMonitor instance
    """
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = CostMonitor()
    return _monitor_instance


def record_openai_usage(
    agent_name: str, model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """
    Convenience function to record usage.

    Args:
        agent_name: Name of the agent
        model: Model used
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens

    Returns:
        Estimated cost for this request
    """
    monitor = get_cost_monitor()
    return monitor.record_usage(agent_name, model, prompt_tokens, completion_tokens)


def get_cost_summary() -> Dict[str, Any]:
    """
    Get current cost summary.

    Returns:
        Summary dictionary with costs and usage
    """
    monitor = get_cost_monitor()
    return monitor.get_summary()
