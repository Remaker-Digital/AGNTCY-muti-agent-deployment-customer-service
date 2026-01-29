# ============================================================================
# Unit Tests for Cost Monitor
# ============================================================================
# Purpose: Test cost tracking and budget monitoring for Azure OpenAI
#
# Test Categories:
# 1. CostMonitor Initialization - Verify monitor setup
# 2. Usage Recording - Test token usage tracking
# 3. Cost Calculation - Verify cost estimation
# 4. Budget Alerts - Test budget threshold alerts
# 5. Usage Reports - Test aggregated reporting
#
# Related Documentation:
# - Cost Monitor: shared/cost_monitor.py
# - Budget Guidelines: CLAUDE.md#budget-constraints
# ============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.cost_monitor import CostMonitor, AgentUsage, CostReport


# =============================================================================
# Test: AgentUsage Dataclass
# =============================================================================


class TestAgentUsage:
    """Tests for AgentUsage dataclass."""

    def test_create_agent_usage(self):
        """Verify basic AgentUsage creation."""
        usage = AgentUsage(
            agent_name="intent-classifier",
            model="gpt-4o-mini",
        )
        assert usage.agent_name == "intent-classifier"
        assert usage.model == "gpt-4o-mini"
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0

    def test_agent_usage_with_values(self):
        """Verify AgentUsage with all values."""
        usage = AgentUsage(
            agent_name="response-generator",
            model="gpt-4o",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            estimated_cost=0.0275,
            request_count=5,
        )
        assert usage.total_tokens == 1500
        assert usage.estimated_cost == 0.0275
        assert usage.request_count == 5


# =============================================================================
# Test: CostMonitor Initialization
# =============================================================================


class TestCostMonitorInit:
    """Tests for CostMonitor initialization."""

    def test_default_initialization(self):
        """Verify default monitor initialization."""
        monitor = CostMonitor()
        assert monitor.monthly_budget == 60.00
        assert monitor.total_cost == 0.0
        assert monitor.total_tokens == 0
        assert len(monitor.usage_by_agent) == 0

    def test_custom_budget(self):
        """Verify custom budget is set."""
        monitor = CostMonitor(budget=100.0)
        assert monitor.monthly_budget == 100.0

    @patch.dict("os.environ", {"AZURE_OPENAI_MONTHLY_BUDGET": "75.00"})
    def test_budget_from_env(self):
        """Verify budget from environment variable."""
        monitor = CostMonitor()
        assert monitor.monthly_budget == 75.00

    def test_period_start_is_first_of_month(self):
        """Verify period starts at first of month."""
        monitor = CostMonitor()
        assert monitor.period_start.day == 1
        assert monitor.period_start.hour == 0
        assert monitor.period_start.minute == 0

    def test_cost_rates_defined(self):
        """Verify cost rates are defined for all models."""
        assert "gpt-4o-mini" in CostMonitor.COSTS_PER_MILLION
        assert "gpt-4o" in CostMonitor.COSTS_PER_MILLION
        assert "text-embedding-3-large" in CostMonitor.COSTS_PER_MILLION


# =============================================================================
# Test: Usage Recording
# =============================================================================


class TestUsageRecording:
    """Tests for usage recording."""

    def test_record_usage_creates_agent_entry(self):
        """Verify recording creates agent entry."""
        monitor = CostMonitor()
        monitor.record_usage(
            agent_name="test-agent",
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert "test-agent" in monitor.usage_by_agent

    def test_record_usage_accumulates(self):
        """Verify multiple recordings accumulate."""
        monitor = CostMonitor()

        monitor.record_usage("agent1", "gpt-4o-mini", 100, 50)
        monitor.record_usage("agent1", "gpt-4o-mini", 200, 100)

        agent_usage = monitor.usage_by_agent["agent1"]
        assert agent_usage.prompt_tokens == 300
        assert agent_usage.completion_tokens == 150
        assert agent_usage.request_count == 2

    def test_record_usage_tracks_total(self):
        """Verify total tokens are tracked."""
        monitor = CostMonitor()

        monitor.record_usage("agent1", "gpt-4o-mini", 100, 50)
        monitor.record_usage("agent2", "gpt-4o", 200, 100)

        assert monitor.total_tokens == 450

    def test_record_usage_returns_cost(self):
        """Verify record_usage returns cost."""
        monitor = CostMonitor()
        cost = monitor.record_usage("agent1", "gpt-4o-mini", 1000, 500)

        # Cost should be calculated
        assert cost >= 0

    def test_record_usage_multiple_agents(self):
        """Verify multiple agents are tracked separately."""
        monitor = CostMonitor()

        monitor.record_usage("agent1", "gpt-4o-mini", 100, 50)
        monitor.record_usage("agent2", "gpt-4o", 200, 100)
        monitor.record_usage("agent3", "text-embedding-3-large", 500, 0)

        assert len(monitor.usage_by_agent) == 3


# =============================================================================
# Test: Cost Calculation
# =============================================================================


class TestCostCalculation:
    """Tests for cost calculation."""

    def test_gpt4o_mini_cost(self):
        """Verify GPT-4o-mini cost calculation."""
        monitor = CostMonitor()

        # 1M prompt + 1M completion tokens
        cost = monitor.record_usage("agent", "gpt-4o-mini", 1_000_000, 1_000_000)

        # $0.15/1M input + $0.60/1M output = $0.75
        assert abs(cost - 0.75) < 0.01

    def test_gpt4o_cost(self):
        """Verify GPT-4o cost calculation."""
        monitor = CostMonitor()

        # 1M prompt + 1M completion tokens
        cost = monitor.record_usage("agent", "gpt-4o", 1_000_000, 1_000_000)

        # $2.50/1M input + $10.00/1M output = $12.50
        assert abs(cost - 12.50) < 0.01

    def test_embedding_cost(self):
        """Verify embedding cost calculation."""
        monitor = CostMonitor()

        # 1M tokens (embeddings are input only)
        cost = monitor.record_usage("agent", "text-embedding-3-large", 1_000_000, 0)

        # $0.13/1M
        assert abs(cost - 0.13) < 0.01

    def test_total_cost_accumulated(self):
        """Verify total cost is accumulated."""
        monitor = CostMonitor()

        monitor.record_usage("agent1", "gpt-4o-mini", 1_000_000, 1_000_000)
        monitor.record_usage("agent2", "gpt-4o", 1_000_000, 1_000_000)

        # 0.75 + 12.50 = 13.25
        assert abs(monitor.total_cost - 13.25) < 0.01

    def test_small_usage_cost(self):
        """Verify small usage cost calculation."""
        monitor = CostMonitor()

        # 1000 prompt + 500 completion tokens (typical single request)
        cost = monitor.record_usage("agent", "gpt-4o-mini", 1000, 500)

        # Very small cost
        assert cost > 0
        assert cost < 0.01


# =============================================================================
# Test: Budget Tracking
# =============================================================================


class TestBudgetTracking:
    """Tests for budget tracking."""

    def test_budget_remaining(self):
        """Verify budget remaining is calculated."""
        monitor = CostMonitor(budget=100.0)
        monitor.record_usage("agent", "gpt-4o", 1_000_000, 1_000_000)  # ~$12.50

        remaining = monitor.monthly_budget - monitor.total_cost
        assert remaining < 100.0
        assert remaining > 87.0  # Should have ~87.50 remaining

    def test_alert_threshold(self):
        """Verify alert threshold is defined."""
        assert CostMonitor.ALERT_THRESHOLD == 0.80


# =============================================================================
# Test: Model Tracking
# =============================================================================


class TestModelTracking:
    """Tests for per-model tracking."""

    def test_track_by_model(self):
        """Verify usage is tracked by model."""
        monitor = CostMonitor()

        monitor.record_usage("agent1", "gpt-4o-mini", 100, 50)
        monitor.record_usage("agent2", "gpt-4o-mini", 200, 100)
        monitor.record_usage("agent3", "gpt-4o", 300, 150)

        assert "gpt-4o-mini" in monitor.usage_by_model
        assert "gpt-4o" in monitor.usage_by_model


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_tokens(self):
        """Verify zero tokens are handled."""
        monitor = CostMonitor()
        cost = monitor.record_usage("agent", "gpt-4o-mini", 0, 0)

        assert cost == 0.0
        assert monitor.total_tokens == 0

    def test_completion_only(self):
        """Verify completion-only usage."""
        monitor = CostMonitor()
        cost = monitor.record_usage("agent", "gpt-4o-mini", 0, 1_000_000)

        # Only output cost: $0.60/1M
        assert abs(cost - 0.60) < 0.01

    def test_prompt_only(self):
        """Verify prompt-only usage."""
        monitor = CostMonitor()
        cost = monitor.record_usage("agent", "gpt-4o-mini", 1_000_000, 0)

        # Only input cost: $0.15/1M
        assert abs(cost - 0.15) < 0.01

    def test_unknown_model_fallback(self):
        """Verify unknown model uses fallback."""
        monitor = CostMonitor()

        # Unknown model should not raise
        cost = monitor.record_usage("agent", "unknown-model", 1000, 500)

        # Should return 0 or use a default
        assert cost >= 0

    def test_very_large_usage(self):
        """Verify very large token counts."""
        monitor = CostMonitor()

        # 100M tokens
        cost = monitor.record_usage("agent", "gpt-4o-mini", 100_000_000, 50_000_000)

        # Should calculate correctly
        assert cost > 0
        assert monitor.total_tokens == 150_000_000


# =============================================================================
# Test: Cost Rates
# =============================================================================


class TestCostRates:
    """Tests for cost rate definitions."""

    def test_gpt4o_mini_rates(self):
        """Verify GPT-4o-mini rates."""
        rates = CostMonitor.COSTS_PER_MILLION["gpt-4o-mini"]
        assert rates["input"] == 0.15
        assert rates["output"] == 0.60

    def test_gpt4o_rates(self):
        """Verify GPT-4o rates."""
        rates = CostMonitor.COSTS_PER_MILLION["gpt-4o"]
        assert rates["input"] == 2.50
        assert rates["output"] == 10.00

    def test_embedding_rates(self):
        """Verify embedding rates."""
        rates = CostMonitor.COSTS_PER_MILLION["text-embedding-3-large"]
        assert rates["input"] == 0.13
        assert rates["output"] == 0.0


# =============================================================================
# Test: Agent Usage Updates
# =============================================================================


class TestAgentUsageUpdates:
    """Tests for agent usage updates."""

    def test_last_request_updated(self):
        """Verify last request time is updated."""
        monitor = CostMonitor()

        before = datetime.utcnow()
        monitor.record_usage("agent", "gpt-4o-mini", 100, 50)
        after = datetime.utcnow()

        agent_usage = monitor.usage_by_agent["agent"]
        assert agent_usage.last_request >= before
        assert agent_usage.last_request <= after

    def test_total_tokens_updated(self):
        """Verify total tokens in agent usage."""
        monitor = CostMonitor()

        monitor.record_usage("agent", "gpt-4o-mini", 100, 50)
        monitor.record_usage("agent", "gpt-4o-mini", 200, 100)

        agent_usage = monitor.usage_by_agent["agent"]
        assert agent_usage.total_tokens == 450  # 100+50+200+100

    def test_estimated_cost_updated(self):
        """Verify estimated cost in agent usage."""
        monitor = CostMonitor()

        monitor.record_usage("agent", "gpt-4o-mini", 1_000_000, 1_000_000)

        agent_usage = monitor.usage_by_agent["agent"]
        assert agent_usage.estimated_cost > 0


# =============================================================================
# Test: Default Budget
# =============================================================================


class TestDefaultBudget:
    """Tests for default budget handling."""

    def test_default_budget_value(self):
        """Verify default budget value."""
        assert CostMonitor.DEFAULT_MONTHLY_BUDGET == 60.00

    def test_alert_threshold_value(self):
        """Verify alert threshold value."""
        assert CostMonitor.ALERT_THRESHOLD == 0.80


# =============================================================================
# Test: Budget Alerts
# =============================================================================


class TestBudgetAlerts:
    """Tests for budget alert functionality."""

    def test_alert_at_80_percent(self, caplog):
        """Verify warning alert at 80% budget usage."""
        import logging

        caplog.set_level(logging.WARNING)
        monitor = CostMonitor(budget=100.0)

        # Use exactly 80% of budget: need $80 worth of usage
        # gpt-4o: $2.50/1M input + $10/1M output = $12.50 total per 1M each
        # To get $80, we need about 6.4M tokens each (6.4 * 12.50 = $80)
        # Simpler: just do multiple calls
        for _ in range(8):
            monitor.record_usage("agent", "gpt-4o", 1_000_000, 1_000_000)  # $12.50 each

        # Should have triggered 80% alert
        assert "80%" in monitor._alerts_sent
        assert "BUDGET ALERT" in caplog.text

    def test_alert_at_100_percent(self, caplog):
        """Verify error alert at 100% budget usage."""
        import logging

        caplog.set_level(logging.ERROR)
        monitor = CostMonitor(budget=100.0)

        # Use more than 100% of budget
        for _ in range(10):
            monitor.record_usage("agent", "gpt-4o", 1_000_000, 1_000_000)  # $12.50 each = $125 total

        # Should have triggered 100% alert
        assert "100%" in monitor._alerts_sent
        assert "BUDGET EXCEEDED" in caplog.text

    def test_alert_not_sent_twice(self, caplog):
        """Verify alerts are only sent once per threshold."""
        import logging

        caplog.set_level(logging.WARNING)
        monitor = CostMonitor(budget=100.0)

        # Hit 80% threshold
        for _ in range(8):
            monitor.record_usage("agent", "gpt-4o", 1_000_000, 1_000_000)

        alert_count_80 = caplog.text.count("BUDGET ALERT")

        # Add more usage
        monitor.record_usage("agent", "gpt-4o", 1_000_000, 1_000_000)

        # Alert count should not increase
        assert caplog.text.count("BUDGET ALERT") == alert_count_80


# =============================================================================
# Test: Get Report
# =============================================================================


class TestGetReport:
    """Tests for get_report method."""

    def test_get_report_returns_cost_report(self):
        """Verify get_report returns CostReport."""
        monitor = CostMonitor(budget=100.0)
        monitor.record_usage("agent1", "gpt-4o-mini", 1000, 500)

        report = monitor.get_report()

        assert isinstance(report, CostReport)
        assert report.budget_limit == 100.0
        assert report.total_tokens > 0

    def test_get_report_budget_remaining(self):
        """Verify budget remaining in report."""
        monitor = CostMonitor(budget=100.0)
        monitor.record_usage("agent", "gpt-4o", 1_000_000, 1_000_000)  # $12.50

        report = monitor.get_report()

        assert report.budget_remaining == pytest.approx(87.50, abs=0.1)

    def test_get_report_budget_alert_flag(self):
        """Verify budget alert flag in report."""
        monitor = CostMonitor(budget=100.0)

        # Below threshold
        report_low = monitor.get_report()
        assert report_low.budget_alert is False

        # Above threshold
        for _ in range(8):
            monitor.record_usage("agent", "gpt-4o", 1_000_000, 1_000_000)

        report_high = monitor.get_report()
        assert report_high.budget_alert is True


# =============================================================================
# Test: Get Summary
# =============================================================================


class TestGetSummary:
    """Tests for get_summary method."""

    def test_get_summary_structure(self):
        """Verify summary structure."""
        monitor = CostMonitor(budget=100.0)
        monitor.record_usage("agent1", "gpt-4o-mini", 1000, 500)
        monitor.record_usage("agent2", "gpt-4o", 2000, 1000)

        summary = monitor.get_summary()

        assert "total_tokens" in summary
        assert "total_cost" in summary
        assert "budget_limit" in summary
        assert "budget_remaining" in summary
        assert "budget_used_pct" in summary
        assert "agents_active" in summary
        assert "models_used" in summary
        assert "period_start" in summary
        assert "report_time" in summary

    def test_get_summary_values(self):
        """Verify summary values."""
        monitor = CostMonitor(budget=100.0)
        monitor.record_usage("agent1", "gpt-4o-mini", 1000, 500)
        monitor.record_usage("agent2", "gpt-4o", 2000, 1000)

        summary = monitor.get_summary()

        assert summary["total_tokens"] == 4500  # 1000+500+2000+1000
        assert summary["agents_active"] == 2
        assert "gpt-4o-mini" in summary["models_used"]
        assert "gpt-4o" in summary["models_used"]

    def test_get_summary_zero_budget(self):
        """Verify summary with zero budget."""
        monitor = CostMonitor(budget=0.0)
        monitor.record_usage("agent", "gpt-4o-mini", 1000, 500)

        summary = monitor.get_summary()

        assert summary["budget_used_pct"] == 0  # No division by zero


# =============================================================================
# Test: Get Agent Summary
# =============================================================================


class TestGetAgentSummary:
    """Tests for get_agent_summary method."""

    def test_get_agent_summary_exists(self):
        """Verify agent summary for existing agent."""
        monitor = CostMonitor()
        monitor.record_usage("test-agent", "gpt-4o-mini", 1000, 500)
        monitor.record_usage("test-agent", "gpt-4o-mini", 2000, 1000)

        summary = monitor.get_agent_summary("test-agent")

        assert summary is not None
        assert summary["agent_name"] == "test-agent"
        assert summary["model"] == "gpt-4o-mini"
        assert summary["total_tokens"] == 4500
        assert summary["request_count"] == 2
        assert summary["avg_tokens_per_request"] == 2250.0

    def test_get_agent_summary_not_exists(self):
        """Verify None for non-existent agent."""
        monitor = CostMonitor()

        summary = monitor.get_agent_summary("non-existent")

        assert summary is None

    def test_get_agent_summary_cost(self):
        """Verify estimated cost in agent summary."""
        monitor = CostMonitor()
        monitor.record_usage("agent", "gpt-4o-mini", 1_000_000, 1_000_000)

        summary = monitor.get_agent_summary("agent")

        assert summary["estimated_cost"] == pytest.approx(0.75, abs=0.01)

    def test_get_agent_summary_last_request(self):
        """Verify last request time in agent summary."""
        monitor = CostMonitor()
        before = datetime.utcnow()
        monitor.record_usage("agent", "gpt-4o-mini", 1000, 500)

        summary = monitor.get_agent_summary("agent")

        assert summary["last_request"] is not None
        # Parse the ISO format
        last_request = datetime.fromisoformat(summary["last_request"])
        assert last_request >= before


# =============================================================================
# Test: Export Report
# =============================================================================


class TestExportReport:
    """Tests for export_report method."""

    def test_export_report_creates_file(self, tmp_path):
        """Verify export creates file."""
        import json

        monitor = CostMonitor(budget=100.0)
        monitor.record_usage("agent1", "gpt-4o-mini", 1000, 500)

        filepath = str(tmp_path / "test_report.json")
        result = monitor.export_report(filepath)

        assert result == filepath
        assert Path(filepath).exists()

    def test_export_report_content(self, tmp_path):
        """Verify exported content structure."""
        import json

        monitor = CostMonitor(budget=100.0)
        monitor.record_usage("agent1", "gpt-4o-mini", 1000, 500)
        monitor.record_usage("agent2", "gpt-4o", 2000, 1000)

        filepath = str(tmp_path / "test_report.json")
        monitor.export_report(filepath)

        with open(filepath) as f:
            data = json.load(f)

        assert "report_time" in data
        assert "period_start" in data
        assert "total_tokens" in data
        assert "total_cost" in data
        assert "budget_limit" in data
        assert "by_agent" in data
        assert "by_model" in data
        assert "agent1" in data["by_agent"]
        assert "agent2" in data["by_agent"]

    def test_export_report_default_filename(self, tmp_path, monkeypatch):
        """Verify default filename generation."""
        import os

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        monitor = CostMonitor()
        monitor.record_usage("agent", "gpt-4o-mini", 100, 50)

        filepath = monitor.export_report()

        assert filepath.startswith("cost_report_")
        assert filepath.endswith(".json")
        assert Path(filepath).exists()


# =============================================================================
# Test: Reset
# =============================================================================


class TestReset:
    """Tests for reset method."""

    def test_reset_clears_usage(self, caplog):
        """Verify reset clears all usage data."""
        import logging

        caplog.set_level(logging.INFO)
        monitor = CostMonitor()

        # Add some usage
        monitor.record_usage("agent1", "gpt-4o-mini", 1000, 500)
        monitor.record_usage("agent2", "gpt-4o", 2000, 1000)
        assert len(monitor.usage_by_agent) == 2

        # Reset
        monitor.reset()

        assert len(monitor.usage_by_agent) == 0
        assert len(monitor.usage_by_model) == 0
        assert monitor.total_cost == 0.0
        assert monitor.total_tokens == 0
        assert len(monitor._alerts_sent) == 0
        assert "reset for new billing period" in caplog.text

    def test_reset_updates_period_start(self):
        """Verify reset updates period start."""
        monitor = CostMonitor()
        old_period = monitor.period_start

        # Reset
        monitor.reset()

        # Period start should be first of current month
        assert monitor.period_start.day == 1


# =============================================================================
# Test: Singleton Functions
# =============================================================================


class TestSingletonFunctions:
    """Tests for singleton functions."""

    def test_get_cost_monitor_returns_monitor(self):
        """Verify get_cost_monitor returns CostMonitor instance."""
        from shared.cost_monitor import get_cost_monitor, _monitor_instance
        import shared.cost_monitor as cm

        # Reset singleton for clean test
        cm._monitor_instance = None

        monitor = get_cost_monitor()

        assert isinstance(monitor, CostMonitor)

    def test_get_cost_monitor_returns_same_instance(self):
        """Verify get_cost_monitor returns same instance."""
        from shared.cost_monitor import get_cost_monitor
        import shared.cost_monitor as cm

        # Reset singleton for clean test
        cm._monitor_instance = None

        monitor1 = get_cost_monitor()
        monitor2 = get_cost_monitor()

        assert monitor1 is monitor2

    def test_record_openai_usage_function(self):
        """Verify record_openai_usage convenience function."""
        from shared.cost_monitor import record_openai_usage, get_cost_monitor
        import shared.cost_monitor as cm

        # Reset singleton for clean test
        cm._monitor_instance = None

        cost = record_openai_usage("test-agent", "gpt-4o-mini", 1000, 500)

        assert cost >= 0
        monitor = get_cost_monitor()
        assert "test-agent" in monitor.usage_by_agent

    def test_get_cost_summary_function(self):
        """Verify get_cost_summary convenience function."""
        from shared.cost_monitor import get_cost_summary, record_openai_usage
        import shared.cost_monitor as cm

        # Reset singleton for clean test
        cm._monitor_instance = None

        record_openai_usage("agent", "gpt-4o-mini", 1000, 500)
        summary = get_cost_summary()

        assert "total_tokens" in summary
        assert summary["total_tokens"] > 0
