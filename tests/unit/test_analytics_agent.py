# ============================================================================
# Unit Tests for Analytics Agent
# ============================================================================
# Purpose: Test KPI tracking, event collection, and metrics aggregation
#
# Test Categories:
# 1. Event Processing - Validate different event types are handled correctly
# 2. KPI Calculations - Test automation rate, response time, confidence scores
# 3. Sentiment Tracking - Verify sentiment distribution updates
# 4. Escalation Tracking - Test escalation reason categorization
# 5. Demo Messages - Verify demo mode produces valid events
# 6. KPI Report Generation - Test comprehensive report output
#
# Related Documentation:
# - Analytics Agent: agents/analytics/agent.py
# - KPI Definitions: docs/PHASE-5-COMPLETION-CHECKLIST.md
# ============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.analytics.agent import AnalyticsAgent
from shared.models import AnalyticsEvent, generate_message_id


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def analytics_agent():
    """Create an analytics agent for testing."""
    with patch("agents.analytics.agent.httpx.AsyncClient"):
        agent = AnalyticsAgent()
        yield agent
        # Clean up
        try:
            asyncio.get_event_loop().run_until_complete(agent.http_client.aclose())
        except Exception:
            pass


@pytest.fixture
def sample_conversation_started_event():
    """Sample conversation started event."""
    return {
        "contextId": "test-ctx-001",
        "parts": [
            {
                "type": "text",
                "content": {
                    "event_type": "conversation_started",
                    "agent_source": "system",
                    "metrics": {},
                },
            }
        ],
    }


@pytest.fixture
def sample_intent_classified_event():
    """Sample intent classification event."""
    return {
        "contextId": "test-ctx-001",
        "parts": [
            {
                "type": "text",
                "content": {
                    "event_type": "intent_classified",
                    "agent_source": "intent-classifier",
                    "metrics": {"intent": "order_status", "confidence": 0.92},
                },
            }
        ],
    }


@pytest.fixture
def sample_sentiment_event():
    """Sample sentiment detection event."""
    return {
        "contextId": "test-ctx-001",
        "parts": [
            {
                "type": "text",
                "content": {
                    "event_type": "sentiment_detected",
                    "agent_source": "intent-classifier",
                    "metrics": {"sentiment": "negative"},
                },
            }
        ],
    }


@pytest.fixture
def sample_escalation_event():
    """Sample escalation decision event."""
    return {
        "contextId": "test-ctx-001",
        "parts": [
            {
                "type": "text",
                "content": {
                    "event_type": "escalation_decision",
                    "agent_source": "escalation",
                    "metrics": {
                        "should_escalate": True,
                        "reason": "Brewer defect - technical support needed",
                    },
                },
            }
        ],
    }


@pytest.fixture
def sample_auto_approval_event():
    """Sample auto-approval event."""
    return {
        "contextId": "test-ctx-002",
        "parts": [
            {
                "type": "text",
                "content": {
                    "event_type": "escalation_decision",
                    "agent_source": "escalation",
                    "metrics": {
                        "should_escalate": False,
                        "reason": "Refund auto-approved",
                        "auto_approved": True,
                    },
                },
            }
        ],
    }


@pytest.fixture
def sample_response_generated_event():
    """Sample response generated event."""
    return {
        "contextId": "test-ctx-001",
        "parts": [
            {
                "type": "text",
                "content": {
                    "event_type": "response_generated",
                    "agent_source": "response-generator",
                    "metrics": {"confidence": 0.88},
                },
            }
        ],
    }


# =============================================================================
# Test: Agent Initialization
# =============================================================================


class TestAnalyticsAgentInit:
    """Tests for analytics agent initialization."""

    def test_agent_name(self, analytics_agent):
        """Verify agent has correct name."""
        assert analytics_agent.agent_name == "analytics-agent"

    def test_default_topic(self, analytics_agent):
        """Verify agent has correct default topic."""
        assert analytics_agent.default_topic == "analytics"

    def test_kpis_initialized(self, analytics_agent):
        """Verify KPI dictionary is properly initialized."""
        assert "total_conversations" in analytics_agent.kpis
        assert "automated_conversations" in analytics_agent.kpis
        assert "escalated_conversations" in analytics_agent.kpis
        assert "intents_classified" in analytics_agent.kpis
        assert "sentiment_distribution" in analytics_agent.kpis
        assert "escalation_reasons" in analytics_agent.kpis
        assert "auto_approvals" in analytics_agent.kpis

    def test_initial_kpi_values(self, analytics_agent):
        """Verify initial KPI values are zero."""
        assert analytics_agent.kpis["total_conversations"] == 0
        assert analytics_agent.kpis["automated_conversations"] == 0
        assert analytics_agent.kpis["escalated_conversations"] == 0
        assert analytics_agent.kpis["auto_approvals"] == 0

    def test_sentiment_distribution_initialized(self, analytics_agent):
        """Verify sentiment distribution has all categories."""
        sentiment = analytics_agent.kpis["sentiment_distribution"]
        assert "positive" in sentiment
        assert "neutral" in sentiment
        assert "negative" in sentiment
        assert "very_negative" in sentiment


# =============================================================================
# Test: KPI Update - Conversation Started
# =============================================================================


class TestConversationStartedEvent:
    """Tests for conversation started event processing."""

    def test_conversation_count_increments(self, analytics_agent):
        """Verify total conversations increments."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="conversation_started",
            context_id="ctx-001",
            agent_source="system",
            metrics={},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["total_conversations"] == 1

    def test_multiple_conversations(self, analytics_agent):
        """Verify multiple conversations are tracked."""
        for i in range(5):
            event = AnalyticsEvent(
                event_id=f"evt-{i}",
                event_type="conversation_started",
                context_id=f"ctx-{i}",
                agent_source="system",
                metrics={},
            )
            analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["total_conversations"] == 5

    def test_start_time_recorded(self, analytics_agent):
        """Verify conversation start time is recorded."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="conversation_started",
            context_id="ctx-001",
            agent_source="system",
            metrics={},
        )
        analytics_agent._update_kpis(event)
        assert "ctx-001" in analytics_agent.conversation_start_times


# =============================================================================
# Test: KPI Update - Intent Classification
# =============================================================================


class TestIntentClassificationEvent:
    """Tests for intent classification event processing."""

    def test_intent_counted(self, analytics_agent):
        """Verify intent is counted in distribution."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="intent_classified",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"intent": "order_status", "confidence": 0.92},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["intents_classified"]["order_status"] == 1

    def test_multiple_same_intent(self, analytics_agent):
        """Verify same intent accumulates."""
        for i in range(3):
            event = AnalyticsEvent(
                event_id=f"evt-{i}",
                event_type="intent_classified",
                context_id=f"ctx-{i}",
                agent_source="intent-classifier",
                metrics={"intent": "product_info", "confidence": 0.85},
            )
            analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["intents_classified"]["product_info"] == 3

    def test_different_intents(self, analytics_agent):
        """Verify different intents are tracked separately."""
        intents = ["order_status", "product_info", "refund_status", "brewer_support"]
        for i, intent in enumerate(intents):
            event = AnalyticsEvent(
                event_id=f"evt-{i}",
                event_type="intent_classified",
                context_id=f"ctx-{i}",
                agent_source="intent-classifier",
                metrics={"intent": intent, "confidence": 0.90},
            )
            analytics_agent._update_kpis(event)

        assert len(analytics_agent.kpis["intents_classified"]) == 4
        for intent in intents:
            assert analytics_agent.kpis["intents_classified"][intent] == 1

    def test_confidence_tracked(self, analytics_agent):
        """Verify confidence scores are tracked."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="intent_classified",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"intent": "order_status", "confidence": 0.92},
        )
        analytics_agent._update_kpis(event)
        assert 0.92 in analytics_agent.kpis["avg_confidence"]

    def test_zero_confidence_not_tracked(self, analytics_agent):
        """Verify zero confidence is not added to average."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="intent_classified",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"intent": "unknown", "confidence": 0},
        )
        analytics_agent._update_kpis(event)
        assert len(analytics_agent.kpis["avg_confidence"]) == 0


# =============================================================================
# Test: KPI Update - Sentiment Detection
# =============================================================================


class TestSentimentDetectionEvent:
    """Tests for sentiment detection event processing."""

    def test_positive_sentiment(self, analytics_agent):
        """Verify positive sentiment is tracked."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="sentiment_detected",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"sentiment": "positive"},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["sentiment_distribution"]["positive"] == 1

    def test_negative_sentiment(self, analytics_agent):
        """Verify negative sentiment is tracked."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="sentiment_detected",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"sentiment": "negative"},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["sentiment_distribution"]["negative"] == 1

    def test_very_negative_sentiment(self, analytics_agent):
        """Verify very negative sentiment is tracked."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="sentiment_detected",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"sentiment": "very_negative"},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["sentiment_distribution"]["very_negative"] == 1

    def test_neutral_sentiment(self, analytics_agent):
        """Verify neutral sentiment is tracked."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="sentiment_detected",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"sentiment": "neutral"},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["sentiment_distribution"]["neutral"] == 1

    def test_unknown_sentiment_ignored(self, analytics_agent):
        """Verify unknown sentiment doesn't affect distribution."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="sentiment_detected",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"sentiment": "confused"},  # Not a valid category
        )
        analytics_agent._update_kpis(event)
        # All categories should still be 0
        assert sum(analytics_agent.kpis["sentiment_distribution"].values()) == 0


# =============================================================================
# Test: KPI Update - Escalation Decision
# =============================================================================


class TestEscalationDecisionEvent:
    """Tests for escalation decision event processing."""

    def test_escalation_counted(self, analytics_agent):
        """Verify escalation is counted."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="escalation_decision",
            context_id="ctx-001",
            agent_source="escalation",
            metrics={"should_escalate": True, "reason": "Technical issue"},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["escalated_conversations"] == 1
        assert analytics_agent.kpis["automated_conversations"] == 0

    def test_no_escalation_counted(self, analytics_agent):
        """Verify non-escalation is counted as automated."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="escalation_decision",
            context_id="ctx-001",
            agent_source="escalation",
            metrics={"should_escalate": False, "reason": "Standard query"},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["automated_conversations"] == 1
        assert analytics_agent.kpis["escalated_conversations"] == 0

    def test_escalation_reason_tracked(self, analytics_agent):
        """Verify escalation reasons are tracked."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="escalation_decision",
            context_id="ctx-001",
            agent_source="escalation",
            metrics={"should_escalate": True, "reason": "Brewer defect"},
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["escalation_reasons"]["Brewer defect"] == 1

    def test_multiple_same_reason(self, analytics_agent):
        """Verify same reason accumulates."""
        for i in range(3):
            event = AnalyticsEvent(
                event_id=f"evt-{i}",
                event_type="escalation_decision",
                context_id=f"ctx-{i}",
                agent_source="escalation",
                metrics={"should_escalate": True, "reason": "Customer angry"},
            )
            analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["escalation_reasons"]["Customer angry"] == 3

    def test_auto_approval_tracked(self, analytics_agent):
        """Verify auto-approvals are tracked."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="escalation_decision",
            context_id="ctx-001",
            agent_source="escalation",
            metrics={
                "should_escalate": False,
                "reason": "Auto-approved",
                "auto_approved": True,
            },
        )
        analytics_agent._update_kpis(event)
        assert analytics_agent.kpis["auto_approvals"] == 1
        assert analytics_agent.kpis["automated_conversations"] == 1


# =============================================================================
# Test: KPI Update - Response Generated
# =============================================================================


class TestResponseGeneratedEvent:
    """Tests for response generated event processing."""

    def test_response_time_calculated(self, analytics_agent):
        """Verify response time is calculated when start time exists."""
        # First, record conversation start
        start_event = AnalyticsEvent(
            event_id="evt-001",
            event_type="conversation_started",
            context_id="ctx-001",
            agent_source="system",
            metrics={},
        )
        analytics_agent._update_kpis(start_event)

        # Then, response generated
        response_event = AnalyticsEvent(
            event_id="evt-002",
            event_type="response_generated",
            context_id="ctx-001",
            agent_source="response-generator",
            metrics={"confidence": 0.88},
        )
        analytics_agent._update_kpis(response_event)

        # Response time should be tracked
        assert analytics_agent.kpis["total_response_time_ms"] > 0

    def test_response_without_start_no_error(self, analytics_agent):
        """Verify response without start time doesn't cause error."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="response_generated",
            context_id="ctx-unknown",
            agent_source="response-generator",
            metrics={"confidence": 0.88},
        )
        # Should not raise exception
        analytics_agent._update_kpis(event)
        # Response time should remain 0
        assert analytics_agent.kpis["total_response_time_ms"] == 0


# =============================================================================
# Test: KPI Report Generation
# =============================================================================


class TestKPIReportGeneration:
    """Tests for KPI report generation."""

    def test_empty_report(self, analytics_agent):
        """Verify empty report has correct structure."""
        report = analytics_agent.get_kpi_report()

        assert "total_conversations" in report
        assert "automated_conversations" in report
        assert "escalated_conversations" in report
        assert "automation_rate_percent" in report
        assert "escalation_rate_percent" in report
        assert "auto_approvals" in report
        assert "avg_response_time_ms" in report
        assert "avg_confidence" in report
        assert "intents_distribution" in report
        assert "sentiment_distribution" in report
        assert "escalation_reasons" in report
        assert "events_collected" in report

    def test_automation_rate_calculation(self, analytics_agent):
        """Verify automation rate is calculated correctly."""
        # Simulate 10 conversations: 7 automated, 3 escalated
        for i in range(10):
            analytics_agent.kpis["total_conversations"] += 1

        analytics_agent.kpis["automated_conversations"] = 7
        analytics_agent.kpis["escalated_conversations"] = 3

        report = analytics_agent.get_kpi_report()
        assert report["automation_rate_percent"] == 70.0
        assert report["escalation_rate_percent"] == 30.0

    def test_average_confidence_calculation(self, analytics_agent):
        """Verify average confidence is calculated correctly."""
        analytics_agent.kpis["avg_confidence"] = [0.90, 0.85, 0.95, 0.80]

        report = analytics_agent.get_kpi_report()
        # (0.90 + 0.85 + 0.95 + 0.80) / 4 = 0.875
        assert report["avg_confidence"] == 0.875

    def test_empty_confidence_returns_zero(self, analytics_agent):
        """Verify empty confidence list returns zero."""
        report = analytics_agent.get_kpi_report()
        assert report["avg_confidence"] == 0

    def test_zero_conversations_no_division_error(self, analytics_agent):
        """Verify zero conversations doesn't cause division error."""
        report = analytics_agent.get_kpi_report()
        assert report["automation_rate_percent"] == 0
        assert report["escalation_rate_percent"] == 0
        assert report["avg_response_time_ms"] == 0


# =============================================================================
# Test: Demo Messages
# =============================================================================


class TestDemoMessages:
    """Tests for demo message generation."""

    def test_demo_messages_returned(self, analytics_agent):
        """Verify demo messages are returned."""
        messages = analytics_agent.get_demo_messages()
        assert len(messages) > 0

    def test_demo_messages_structure(self, analytics_agent):
        """Verify demo messages have correct structure."""
        messages = analytics_agent.get_demo_messages()
        for msg in messages:
            assert "contextId" in msg
            assert "parts" in msg
            assert len(msg["parts"]) > 0

    def test_demo_includes_multiple_event_types(self, analytics_agent):
        """Verify demo includes various event types."""
        messages = analytics_agent.get_demo_messages()
        event_types = set()
        for msg in messages:
            content = msg["parts"][0]["content"]
            event_types.add(content["event_type"])

        assert "conversation_started" in event_types
        assert "intent_classified" in event_types
        assert "response_generated" in event_types
        assert "escalation_decision" in event_types

    def test_demo_includes_escalated_conversation(self, analytics_agent):
        """Verify demo includes an escalated conversation."""
        messages = analytics_agent.get_demo_messages()
        escalated = False
        for msg in messages:
            content = msg["parts"][0]["content"]
            if content["event_type"] == "escalation_decision":
                if content["metrics"].get("should_escalate"):
                    escalated = True
                    break
        assert escalated

    def test_demo_includes_auto_approval(self, analytics_agent):
        """Verify demo includes an auto-approval."""
        messages = analytics_agent.get_demo_messages()
        auto_approved = False
        for msg in messages:
            content = msg["parts"][0]["content"]
            if content["event_type"] == "escalation_decision":
                if content["metrics"].get("auto_approved"):
                    auto_approved = True
                    break
        assert auto_approved


# =============================================================================
# Test: Message Processing Integration
# =============================================================================


class TestMessageProcessingIntegration:
    """Integration tests for message processing."""

    @pytest.mark.asyncio
    async def test_process_message_returns_status(self, analytics_agent):
        """Verify process_message returns status."""
        content = {
            "event_type": "conversation_started",
            "agent_source": "system",
            "metrics": {},
        }
        message = {"contextId": "ctx-001"}

        # Mock the HTTP client
        analytics_agent.http_client.post = AsyncMock(
            return_value=MagicMock(status_code=200)
        )

        result = await analytics_agent.process_message(content, message)
        assert result["status"] == "collected"
        assert "event_id" in result

    @pytest.mark.asyncio
    async def test_process_message_updates_kpis(self, analytics_agent):
        """Verify process_message updates KPIs."""
        content = {
            "event_type": "conversation_started",
            "agent_source": "system",
            "metrics": {},
        }
        message = {"contextId": "ctx-001"}

        analytics_agent.http_client.post = AsyncMock(
            return_value=MagicMock(status_code=200)
        )

        await analytics_agent.process_message(content, message)
        assert analytics_agent.kpis["total_conversations"] == 1


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_missing_event_type(self, analytics_agent):
        """Verify missing event type is handled."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="unknown",
            context_id="ctx-001",
            agent_source="unknown",
            metrics={},
        )
        # Should not raise exception
        analytics_agent._update_kpis(event)

    def test_missing_metrics(self, analytics_agent):
        """Verify missing metrics are handled."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="intent_classified",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={},  # No intent or confidence
        )
        # Should not raise exception
        analytics_agent._update_kpis(event)
        # "unknown" should be added to intents
        assert "unknown" in analytics_agent.kpis["intents_classified"]

    def test_very_long_context_id(self, analytics_agent):
        """Verify long context ID is handled."""
        long_context = "ctx-" + "a" * 1000
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="conversation_started",
            context_id=long_context,
            agent_source="system",
            metrics={},
        )
        # Should not raise exception
        analytics_agent._update_kpis(event)
        assert long_context in analytics_agent.conversation_start_times

    def test_special_characters_in_reason(self, analytics_agent):
        """Verify special characters in escalation reason are handled."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="escalation_decision",
            context_id="ctx-001",
            agent_source="escalation",
            metrics={
                "should_escalate": True,
                "reason": "Customer said: 'This is $#@! broken!'",
            },
        )
        # Should not raise exception
        analytics_agent._update_kpis(event)
        assert (
            "Customer said: 'This is $#@! broken!'"
            in analytics_agent.kpis["escalation_reasons"]
        )


# =============================================================================
# Test: Log KPI Summary
# =============================================================================


class TestLogKPISummary:
    """Tests for KPI summary logging."""

    def test_log_summary_no_error_when_empty(self, analytics_agent):
        """Verify log summary doesn't error when KPIs are empty."""
        # Should not raise exception
        analytics_agent._log_kpi_summary()

    def test_log_summary_with_data(self, analytics_agent):
        """Verify log summary works with data."""
        analytics_agent.kpis["total_conversations"] = 10
        analytics_agent.kpis["automated_conversations"] = 7
        analytics_agent.kpis["escalated_conversations"] = 3
        analytics_agent.kpis["auto_approvals"] = 2
        analytics_agent.kpis["avg_confidence"] = [0.85, 0.90, 0.88]

        # Should not raise exception
        analytics_agent._log_kpi_summary()
