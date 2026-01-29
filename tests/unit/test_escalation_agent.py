# ============================================================================
# Unit Tests for Escalation Agent
# ============================================================================
# Purpose: Test escalation decision logic, sentiment detection, and business rules
#
# Test Categories:
# 1. Sentiment Detection - Verify sentiment classification accuracy
# 2. Rule-Based Escalation - Test Phase 2 business rules
# 3. Auto-Approval Logic - Test refund auto-approval (<$50, <30 days)
# 4. Priority Assignment - Verify priority mapping
# 5. Demo Messages - Verify demo mode produces valid messages
# 6. Zendesk Integration - Test ticket creation
#
# Business Rules (from PHASE-2-IMPLEMENTATION-PLAN.md):
# - Missing/stolen deliveries: Always escalate
# - Refund auto-approval: <$50 AND within 30 days
# - Product defects: Always escalate
# - Health/safety: IMMEDIATE escalation
#
# Related Documentation:
# - Escalation Agent: agents/escalation/agent.py
# - Business Rules: docs/PHASE-2-IMPLEMENTATION-PLAN.md
# ============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.escalation.agent import EscalationAgent
from shared.models import Sentiment, Priority, EscalationDecision


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def escalation_agent():
    """Create an escalation agent for testing."""
    with patch("agents.escalation.agent.httpx.AsyncClient"):
        agent = EscalationAgent()
        yield agent
        # Clean up
        try:
            asyncio.get_event_loop().run_until_complete(agent.http_client.aclose())
        except Exception:
            pass


@pytest.fixture
def order_context_under_50():
    """Order context for refund under $50."""
    order_date = (datetime.now() - timedelta(days=10)).isoformat() + "Z"
    return [
        {
            "type": "order",
            "order_number": "10001",
            "total": 35.99,
            "order_date": order_date,
        }
    ]


@pytest.fixture
def order_context_over_50():
    """Order context for refund over $50."""
    order_date = (datetime.now() - timedelta(days=10)).isoformat() + "Z"
    return [
        {
            "type": "order",
            "order_number": "10002",
            "total": 75.00,
            "order_date": order_date,
        }
    ]


@pytest.fixture
def order_context_old_order():
    """Order context for old order (>30 days)."""
    order_date = (datetime.now() - timedelta(days=45)).isoformat() + "Z"
    return [
        {
            "type": "order",
            "order_number": "10003",
            "total": 25.00,
            "order_date": order_date,
        }
    ]


# =============================================================================
# Test: Agent Initialization
# =============================================================================


class TestEscalationAgentInit:
    """Tests for escalation agent initialization."""

    def test_agent_name(self, escalation_agent):
        """Verify agent has correct name."""
        assert escalation_agent.agent_name == "escalation-agent"

    def test_default_topic(self, escalation_agent):
        """Verify agent has correct default topic."""
        assert escalation_agent.default_topic == "escalation"

    def test_counters_initialized(self, escalation_agent):
        """Verify counters are initialized to zero."""
        assert escalation_agent.openai_decisions == 0
        assert escalation_agent.rule_decisions == 0
        assert escalation_agent.escalations_triggered == 0


# =============================================================================
# Test: Sentiment Detection
# =============================================================================


class TestSentimentDetection:
    """Tests for sentiment detection."""

    def test_very_negative_sentiment_angry(self, escalation_agent):
        """Verify 'angry' triggers very negative sentiment."""
        sentiment = escalation_agent._detect_sentiment("I am so angry about this!")
        assert sentiment == Sentiment.VERY_NEGATIVE

    def test_very_negative_sentiment_furious(self, escalation_agent):
        """Verify 'furious' triggers very negative sentiment."""
        sentiment = escalation_agent._detect_sentiment("I am absolutely furious!")
        assert sentiment == Sentiment.VERY_NEGATIVE

    def test_very_negative_sentiment_worst(self, escalation_agent):
        """Verify 'worst' triggers very negative sentiment."""
        sentiment = escalation_agent._detect_sentiment(
            "This is the worst service ever"
        )
        assert sentiment == Sentiment.VERY_NEGATIVE

    def test_very_negative_sentiment_unacceptable(self, escalation_agent):
        """Verify 'unacceptable' triggers very negative sentiment."""
        sentiment = escalation_agent._detect_sentiment("This is unacceptable")
        assert sentiment == Sentiment.VERY_NEGATIVE

    def test_negative_sentiment_problem(self, escalation_agent):
        """Verify 'problem' triggers negative sentiment."""
        sentiment = escalation_agent._detect_sentiment(
            "I have a problem with my order"
        )
        assert sentiment == Sentiment.NEGATIVE

    def test_negative_sentiment_frustrated(self, escalation_agent):
        """Verify 'frustrated' triggers negative sentiment."""
        sentiment = escalation_agent._detect_sentiment(
            "I'm frustrated with the delay"
        )
        assert sentiment == Sentiment.NEGATIVE

    def test_negative_sentiment_not_working(self, escalation_agent):
        """Verify 'not working' triggers negative sentiment."""
        sentiment = escalation_agent._detect_sentiment("My brewer is not working")
        assert sentiment == Sentiment.NEGATIVE

    def test_positive_sentiment_thanks(self, escalation_agent):
        """Verify 'thanks' triggers positive sentiment."""
        sentiment = escalation_agent._detect_sentiment("Thanks for your help!")
        assert sentiment == Sentiment.POSITIVE

    def test_positive_sentiment_great(self, escalation_agent):
        """Verify 'great' triggers positive sentiment."""
        sentiment = escalation_agent._detect_sentiment("That's great news!")
        assert sentiment == Sentiment.POSITIVE

    def test_positive_sentiment_love(self, escalation_agent):
        """Verify 'love' triggers positive sentiment."""
        sentiment = escalation_agent._detect_sentiment("I love this product")
        assert sentiment == Sentiment.POSITIVE

    def test_neutral_sentiment_default(self, escalation_agent):
        """Verify neutral sentiment for standard messages."""
        sentiment = escalation_agent._detect_sentiment(
            "Can I check my order status?"
        )
        assert sentiment == Sentiment.NEUTRAL

    def test_sentiment_case_insensitive(self, escalation_agent):
        """Verify sentiment detection is case insensitive."""
        sentiment = escalation_agent._detect_sentiment("I am ANGRY about this")
        assert sentiment == Sentiment.VERY_NEGATIVE


# =============================================================================
# Test: Rule-Based Escalation - Health/Safety
# =============================================================================


class TestHealthSafetyEscalation:
    """Tests for health/safety escalation rules."""

    def test_health_safety_escalates(self, escalation_agent):
        """Verify health/safety concerns trigger immediate escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I had an allergic reaction to the coffee",
            intent="complaint",
            escalation_reason="health_safety",
            knowledge_context=[],
        )
        assert result["should_escalate"] is True
        assert result["priority"] == Priority.URGENT
        assert "health" in result["reason"].lower() or "safety" in result["reason"].lower()

    def test_health_safety_complexity_score(self, escalation_agent):
        """Verify health/safety has highest complexity score."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="Medical emergency",
            intent="complaint",
            escalation_reason="health_safety",
            knowledge_context=[],
        )
        assert result["complexity_score"] == 1.0


# =============================================================================
# Test: Rule-Based Escalation - Customer Frustration
# =============================================================================


class TestCustomerFrustrationEscalation:
    """Tests for customer frustration escalation rules."""

    def test_customer_frustration_escalates(self, escalation_agent):
        """Verify customer frustration triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I've explained this three times already!",
            intent="complaint",
            escalation_reason="customer_frustration",
            knowledge_context=[],
        )
        assert result["should_escalate"] is True
        assert result["priority"] == Priority.URGENT

    def test_frustration_reason_message(self, escalation_agent):
        """Verify frustration escalation includes correct reason."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="This is ridiculous",
            intent="complaint",
            escalation_reason="customer_frustration",
            knowledge_context=[],
        )
        assert "frustration" in result["reason"].lower()


# =============================================================================
# Test: Rule-Based Escalation - Brewer Defect
# =============================================================================


class TestBrewerDefectEscalation:
    """Tests for brewer defect escalation rules."""

    def test_brewer_defect_escalates(self, escalation_agent):
        """Verify brewer defect triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="My brewer stopped working completely",
            intent="brewer_support",
            escalation_reason="brewer_defect",
            knowledge_context=[],
        )
        assert result["should_escalate"] is True
        assert result["priority"] == Priority.HIGH

    def test_brewer_defect_reason_message(self, escalation_agent):
        """Verify brewer defect includes warranty mention."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="Brewer is broken",
            intent="brewer_support",
            escalation_reason="brewer_defect",
            knowledge_context=[],
        )
        assert "warranty" in result["reason"].lower() or "technical" in result["reason"].lower()


# =============================================================================
# Test: Rule-Based Escalation - Missing/Stolen Delivery
# =============================================================================


class TestMissingStolenDeliveryEscalation:
    """Tests for missing/stolen delivery escalation rules."""

    def test_stolen_delivery_escalates(self, escalation_agent):
        """Verify 'stolen' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I think my package was stolen",
            intent="order_status",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True
        assert result["priority"] == Priority.HIGH

    def test_missing_delivery_escalates(self, escalation_agent):
        """Verify 'missing' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="My delivery is missing",
            intent="order_status",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True

    def test_never_received_escalates(self, escalation_agent):
        """Verify 'never received' triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I never received my order",
            intent="order_status",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True


# =============================================================================
# Test: Rule-Based Escalation - Refund Auto-Approval
# =============================================================================


class TestRefundAutoApproval:
    """Tests for refund auto-approval logic."""

    def test_auto_approve_under_50_recent(
        self, escalation_agent, order_context_under_50
    ):
        """Verify refund auto-approved when <$50 and <30 days."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I want a refund for my coffee pods",
            intent="refund_status",
            escalation_reason=None,
            knowledge_context=order_context_under_50,
        )
        assert result["should_escalate"] is False
        assert result["auto_approved_action"] == "refund_approved"
        assert "auto-approved" in result["reason"].lower()

    def test_escalate_over_50(self, escalation_agent, order_context_over_50):
        """Verify refund escalated when >$50."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I want a refund for my brewer",
            intent="refund_status",
            escalation_reason=None,
            knowledge_context=order_context_over_50,
        )
        assert result["should_escalate"] is True
        assert result.get("auto_approved_action") is None

    def test_escalate_old_order(self, escalation_agent, order_context_old_order):
        """Verify refund escalated when >30 days old."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I want a refund",
            intent="refund_status",
            escalation_reason=None,
            knowledge_context=order_context_old_order,
        )
        assert result["should_escalate"] is True

    def test_return_request_same_rules(
        self, escalation_agent, order_context_under_50
    ):
        """Verify return_request uses same auto-approval logic."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I want to return my order",
            intent="return_request",
            escalation_reason=None,
            knowledge_context=order_context_under_50,
        )
        assert result["should_escalate"] is False
        assert result["auto_approved_action"] == "refund_approved"


# =============================================================================
# Test: Rule-Based Escalation - Product Defects
# =============================================================================


class TestProductDefectEscalation:
    """Tests for product defect escalation rules."""

    def test_defect_keyword_escalates(self, escalation_agent):
        """Verify 'defect' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="There's a defect in my coffee pods",
            intent="complaint",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True
        assert result["priority"] == Priority.HIGH

    def test_damaged_keyword_escalates(self, escalation_agent):
        """Verify 'damaged' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="My package arrived damaged",
            intent="complaint",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True

    def test_broken_keyword_escalates(self, escalation_agent):
        """Verify 'broken' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="The seal was broken",
            intent="complaint",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True

    def test_leak_keyword_escalates(self, escalation_agent):
        """Verify 'leak' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="The pods have a leak",
            intent="complaint",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True


# =============================================================================
# Test: Rule-Based Escalation - B2B/Wholesale
# =============================================================================


class TestB2BWholesaleEscalation:
    """Tests for B2B/wholesale escalation rules."""

    def test_wholesale_keyword_escalates(self, escalation_agent):
        """Verify 'wholesale' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="Do you offer wholesale pricing?",
            intent="general_inquiry",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True
        assert "sales" in result["reason"].lower()

    def test_bulk_keyword_escalates(self, escalation_agent):
        """Verify 'bulk' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I need a bulk order for my office",
            intent="product_info",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True

    def test_business_keyword_escalates(self, escalation_agent):
        """Verify 'business' keyword triggers escalation."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I'm interested in ordering for my business",
            intent="product_info",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True


# =============================================================================
# Test: Rule-Based Escalation - No Escalation Needed
# =============================================================================


class TestNoEscalationNeeded:
    """Tests for cases where no escalation is needed."""

    def test_standard_inquiry_no_escalation(self, escalation_agent):
        """Verify standard inquiry doesn't escalate."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="What's my order status?",
            intent="order_status",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is False
        assert result["priority"] == Priority.LOW

    def test_product_info_no_escalation(self, escalation_agent):
        """Verify product info request doesn't escalate."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="How much is the Premium Brewer?",
            intent="product_info",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is False


# =============================================================================
# Test: Demo Messages
# =============================================================================


class TestDemoMessages:
    """Tests for demo message generation."""

    def test_demo_messages_returned(self, escalation_agent):
        """Verify demo messages are returned."""
        messages = escalation_agent.get_demo_messages()
        assert len(messages) > 0

    def test_demo_messages_structure(self, escalation_agent):
        """Verify demo messages have correct structure."""
        messages = escalation_agent.get_demo_messages()
        for msg in messages:
            assert "contextId" in msg
            assert "parts" in msg
            assert len(msg["parts"]) > 0

    def test_demo_includes_refund_scenario(self, escalation_agent):
        """Verify demo includes refund scenario."""
        messages = escalation_agent.get_demo_messages()
        has_refund = any(
            "refund" in msg["parts"][0]["content"].get("customer_message", "").lower()
            for msg in messages
        )
        assert has_refund

    def test_demo_includes_health_safety_scenario(self, escalation_agent):
        """Verify demo includes health/safety scenario."""
        messages = escalation_agent.get_demo_messages()
        has_health = any(
            msg["parts"][0]["content"].get("escalation_reason") == "health_safety"
            for msg in messages
        )
        assert has_health


# =============================================================================
# Test: Helper Methods
# =============================================================================


class TestHelperMethods:
    """Tests for helper methods."""

    def test_extract_order_amount(self, escalation_agent, order_context_under_50):
        """Verify order amount extraction."""
        amount = escalation_agent._extract_order_amount(order_context_under_50)
        assert amount == 35.99

    def test_extract_order_amount_empty_context(self, escalation_agent):
        """Verify order amount returns None for empty context."""
        amount = escalation_agent._extract_order_amount([])
        assert amount is None

    def test_extract_days_since_order(self, escalation_agent, order_context_under_50):
        """Verify days since order extraction."""
        days = escalation_agent._extract_days_since_order(order_context_under_50)
        assert days is not None
        assert days >= 10  # We set it to 10 days ago

    def test_extract_days_since_order_empty_context(self, escalation_agent):
        """Verify days returns None for empty context."""
        days = escalation_agent._extract_days_since_order([])
        assert days is None

    def test_analyze_mock_returns_tuple(self, escalation_agent):
        """Verify legacy _analyze_mock returns sentiment and complexity."""
        sentiment, complexity = escalation_agent._analyze_mock("I'm angry about this")
        assert sentiment == Sentiment.VERY_NEGATIVE
        assert complexity >= 0.8  # High complexity for very negative

    def test_analyze_mock_positive(self, escalation_agent):
        """Verify positive sentiment has low complexity."""
        sentiment, complexity = escalation_agent._analyze_mock("Thanks for the help!")
        assert sentiment == Sentiment.POSITIVE
        assert complexity <= 0.4


# =============================================================================
# Test: Process Message Integration
# =============================================================================


class TestProcessMessageIntegration:
    """Integration tests for process_message."""

    @pytest.mark.asyncio
    async def test_process_message_returns_decision(self, escalation_agent):
        """Verify process_message returns EscalationDecision."""
        content = {
            "customer_message": "What's my order status?",
            "intent": "order_status",
        }
        message = {"contextId": "ctx-001"}

        # Mock the HTTP client for Zendesk
        escalation_agent.http_client.post = AsyncMock(
            return_value=MagicMock(
                status_code=201, json=lambda: {"ticket": {"id": 12345}}
            )
        )

        result = await escalation_agent.process_message(content, message)

        # Result should be EscalationDecision or dict
        if isinstance(result, EscalationDecision):
            assert result.decision_id is not None
            assert result.context_id == "ctx-001"
        else:
            assert "decision_id" in result or hasattr(result, "decision_id")

    @pytest.mark.asyncio
    async def test_process_message_increments_rule_counter(self, escalation_agent):
        """Verify rule decisions are counted when no OpenAI."""
        content = {
            "customer_message": "What's my order status?",
            "intent": "order_status",
        }
        message = {"contextId": "ctx-001"}

        escalation_agent.http_client.post = AsyncMock(
            return_value=MagicMock(
                status_code=201, json=lambda: {"ticket": {"id": 12345}}
            )
        )

        await escalation_agent.process_message(content, message)
        assert escalation_agent.rule_decisions == 1


# =============================================================================
# Test: Zendesk Ticket Creation
# =============================================================================


class TestZendeskTicketCreation:
    """Tests for Zendesk ticket creation."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, escalation_agent):
        """Verify successful ticket creation."""
        escalation_agent.http_client.post = AsyncMock(
            return_value=MagicMock(
                status_code=201, json=lambda: {"ticket": {"id": 12345}}
            )
        )

        ticket_id = await escalation_agent._create_zendesk_ticket(
            customer_message="I need help",
            intent="complaint",
            reason="Customer frustrated",
            priority=Priority.HIGH,
            context=[],
        )

        assert ticket_id == 12345

    @pytest.mark.asyncio
    async def test_create_ticket_failure_returns_mock_id(self, escalation_agent):
        """Verify failed ticket creation returns mock ID."""
        escalation_agent.http_client.post = AsyncMock(side_effect=Exception("API error"))

        ticket_id = await escalation_agent._create_zendesk_ticket(
            customer_message="I need help",
            intent="complaint",
            reason="Customer frustrated",
            priority=Priority.HIGH,
            context=[],
        )

        assert ticket_id == 9999  # Mock ticket ID


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_message(self, escalation_agent):
        """Verify empty message is handled."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="",
            intent="unknown",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is False

    def test_unicode_message(self, escalation_agent):
        """Verify unicode characters are handled."""
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="Café ☕ problème avec ma commande",
            intent="complaint",
            escalation_reason=None,
            knowledge_context=[],
        )
        # Should not raise exception
        assert "should_escalate" in result

    def test_very_long_message(self, escalation_agent):
        """Verify very long message is handled without error."""
        long_message = "I have a problem " * 500
        result = escalation_agent._evaluate_escalation_rules(
            customer_message=long_message,
            intent="complaint",
            escalation_reason=None,
            knowledge_context=[],
        )
        # Should handle long message without error
        # "problem" alone doesn't trigger escalation - it's just a standard complaint
        assert "should_escalate" in result
        assert "priority" in result

    def test_multiple_keywords(self, escalation_agent):
        """Verify multiple escalation keywords handled correctly."""
        # Has both "stolen" and "angry" - should still escalate
        result = escalation_agent._evaluate_escalation_rules(
            customer_message="I'm angry because my package was stolen!",
            intent="complaint",
            escalation_reason=None,
            knowledge_context=[],
        )
        assert result["should_escalate"] is True
