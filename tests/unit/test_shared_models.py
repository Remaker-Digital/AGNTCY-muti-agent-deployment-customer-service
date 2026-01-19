"""
Unit tests for shared/models.py
Tests data models, enums, and message wrappers
"""

import pytest
from datetime import datetime

from shared.models import (
    Intent, Sentiment, Priority, Language,
    AgentCard, CustomerMessage, IntentClassificationResult,
    KnowledgeQuery, KnowledgeResult, ResponseRequest, GeneratedResponse,
    EscalationDecision, AnalyticsEvent,
    create_a2a_message, extract_message_content,
    generate_message_id, generate_context_id, generate_task_id
)


class TestEnums:
    """Tests for enumeration types."""

    def test_intent_values(self):
        """Test Intent enum values."""
        assert Intent.ORDER_STATUS.value == "order_status"
        assert Intent.PRODUCT_INQUIRY.value == "product_inquiry"
        assert Intent.RETURN_REQUEST.value == "return_request"

    def test_sentiment_values(self):
        """Test Sentiment enum values."""
        assert Sentiment.POSITIVE.value == "positive"
        assert Sentiment.NEUTRAL.value == "neutral"
        assert Sentiment.NEGATIVE.value == "negative"
        assert Sentiment.VERY_NEGATIVE.value == "very_negative"

    def test_priority_values(self):
        """Test Priority enum values."""
        assert Priority.LOW.value == "low"
        assert Priority.NORMAL.value == "normal"
        assert Priority.HIGH.value == "high"
        assert Priority.URGENT.value == "urgent"

    def test_language_values(self):
        """Test Language enum values."""
        assert Language.EN.value == "en"
        assert Language.FR_CA.value == "fr-ca"
        assert Language.ES.value == "es"


class TestAgentCard:
    """Tests for AgentCard model."""

    def test_agent_card_creation(self):
        """Test creating an AgentCard."""
        card = AgentCard(
            name="Intent Classifier",
            topic="intent-classifier",
            protocol="A2A",
            transport="SLIM",
            description="Routes customer messages"
        )
        assert card.name == "Intent Classifier"
        assert card.topic == "intent-classifier"
        assert card.protocol == "A2A"
        assert card.transport == "SLIM"

    def test_agent_card_to_dict(self):
        """Test AgentCard serialization."""
        card = AgentCard(
            name="Test Agent",
            topic="test-agent",
            protocol="MCP",
            transport="NATS",
            description="Test description",
            capabilities=["search", "analyze"]
        )
        data = card.to_dict()
        assert isinstance(data, dict)
        assert data["name"] == "Test Agent"
        assert data["capabilities"] == ["search", "analyze"]


class TestCustomerMessage:
    """Tests for CustomerMessage model."""

    def test_customer_message_creation(self, sample_customer_message):
        """Test creating a CustomerMessage."""
        msg = CustomerMessage(**sample_customer_message)
        assert msg.message_id == "msg-test-001"
        assert msg.customer_id == "cust-test-123"
        assert msg.content == "Where is my order #12345?"
        assert msg.channel == "chat"

    def test_customer_message_timestamp(self):
        """Test that timestamp is auto-generated."""
        msg = CustomerMessage(
            message_id="msg-001",
            customer_id="cust-001",
            content="Test message",
            channel="email"
        )
        assert msg.timestamp is not None
        assert isinstance(msg.timestamp, str)

    def test_customer_message_to_dict(self, sample_customer_message):
        """Test CustomerMessage serialization."""
        msg = CustomerMessage(**sample_customer_message)
        data = msg.to_dict()
        assert isinstance(data, dict)
        assert data["content"] == sample_customer_message["content"]


class TestIntentClassificationResult:
    """Tests for IntentClassificationResult model."""

    def test_intent_result_creation(self):
        """Test creating IntentClassificationResult."""
        result = IntentClassificationResult(
            message_id="msg-001",
            context_id="ctx-001",
            intent=Intent.ORDER_STATUS,
            confidence=0.85,
            extracted_entities={"order_number": "12345"}
        )
        assert result.intent == Intent.ORDER_STATUS
        assert result.confidence == 0.85
        assert result.extracted_entities["order_number"] == "12345"

    def test_intent_result_defaults(self):
        """Test IntentClassificationResult default values."""
        result = IntentClassificationResult(
            message_id="msg-001",
            context_id="ctx-001",
            intent=Intent.GENERAL_INQUIRY,
            confidence=0.5
        )
        assert result.extracted_entities == {}
        assert result.language == Language.EN


class TestKnowledgeModels:
    """Tests for Knowledge Query and Result models."""

    def test_knowledge_query_creation(self, sample_knowledge_query):
        """Test creating KnowledgeQuery."""
        query = KnowledgeQuery(**sample_knowledge_query)
        assert query.query_text == "wireless headphones"
        assert query.intent == Intent.PRODUCT_INQUIRY
        assert query.max_results == 5

    def test_knowledge_result_creation(self):
        """Test creating KnowledgeResult."""
        result = KnowledgeResult(
            query_id="q-001",
            context_id="ctx-001",
            results=[{"title": "Product 1"}, {"title": "Product 2"}],
            total_results=2,
            search_time_ms=150.5,
            confidence=0.75
        )
        assert len(result.results) == 2
        assert result.total_results == 2
        assert result.search_time_ms == 150.5


class TestResponseModels:
    """Tests for Response Request and Generation models."""

    def test_response_request_creation(self):
        """Test creating ResponseRequest."""
        request = ResponseRequest(
            request_id="req-001",
            context_id="ctx-001",
            customer_message="Test message",
            intent=Intent.PRODUCT_INQUIRY,
            knowledge_context=[{"source": "faq", "content": "Answer"}]
        )
        assert request.intent == Intent.PRODUCT_INQUIRY
        assert len(request.knowledge_context) == 1

    def test_generated_response_creation(self):
        """Test creating GeneratedResponse."""
        response = GeneratedResponse(
            request_id="req-001",
            context_id="ctx-001",
            response_text="Thank you for your inquiry",
            confidence=0.8,
            requires_escalation=False
        )
        assert response.response_text == "Thank you for your inquiry"
        assert response.confidence == 0.8
        assert not response.requires_escalation


class TestEscalationDecision:
    """Tests for EscalationDecision model."""

    def test_escalation_decision_creation(self):
        """Test creating EscalationDecision."""
        decision = EscalationDecision(
            decision_id="dec-001",
            context_id="ctx-001",
            should_escalate=True,
            reason="Very negative sentiment detected",
            priority=Priority.URGENT,
            sentiment=Sentiment.VERY_NEGATIVE,
            complexity_score=0.9
        )
        assert decision.should_escalate is True
        assert decision.priority == Priority.URGENT
        assert decision.sentiment == Sentiment.VERY_NEGATIVE

    def test_escalation_decision_with_ticket(self):
        """Test EscalationDecision with Zendesk ticket."""
        decision = EscalationDecision(
            decision_id="dec-001",
            context_id="ctx-001",
            should_escalate=True,
            reason="Test",
            priority=Priority.HIGH,
            sentiment=Sentiment.NEGATIVE,
            complexity_score=0.7,
            zendesk_ticket_id=12345
        )
        assert decision.zendesk_ticket_id == 12345


class TestAnalyticsEvent:
    """Tests for AnalyticsEvent model."""

    def test_analytics_event_creation(self):
        """Test creating AnalyticsEvent."""
        event = AnalyticsEvent(
            event_id="evt-001",
            event_type="intent_classified",
            context_id="ctx-001",
            agent_source="intent-classifier",
            metrics={"confidence": 0.85, "processing_time_ms": 150}
        )
        assert event.event_type == "intent_classified"
        assert event.agent_source == "intent-classifier"
        assert event.metrics["confidence"] == 0.85


class TestMessageWrappers:
    """Tests for A2A message creation and extraction."""

    def test_create_a2a_message(self):
        """Test creating A2A message."""
        content = {"test": "data"}
        message = create_a2a_message(
            role="assistant",
            content=content,
            context_id="ctx-001",
            task_id="task-001"
        )

        assert message["role"] == "assistant"
        assert message["contextId"] == "ctx-001"
        assert message["taskId"] == "task-001"
        assert "messageId" in message
        assert len(message["parts"]) == 1

    def test_create_a2a_message_with_dataclass(self):
        """Test creating A2A message with dataclass content."""
        result = IntentClassificationResult(
            message_id="msg-001",
            context_id="ctx-001",
            intent=Intent.ORDER_STATUS,
            confidence=0.85
        )

        message = create_a2a_message(
            role="assistant",
            content=result,
            context_id="ctx-001"
        )

        extracted = extract_message_content(message)
        assert extracted["intent"] == "order_status"
        assert extracted["confidence"] == 0.85

    def test_extract_message_content(self, sample_a2a_message):
        """Test extracting content from A2A message."""
        content = extract_message_content(sample_a2a_message)

        assert isinstance(content, dict)
        assert content["customer_id"] == "cust-123"
        assert content["content"] == "I want to return my order"

    def test_extract_message_content_empty(self):
        """Test extracting content from empty message."""
        message = {"parts": []}
        content = extract_message_content(message)
        assert content == {}


class TestIDGenerators:
    """Tests for ID generation functions."""

    def test_generate_message_id(self):
        """Test message ID generation."""
        msg_id = generate_message_id()
        assert msg_id.startswith("msg-")
        assert len(msg_id) > 10

    def test_generate_context_id(self):
        """Test context ID generation."""
        ctx_id = generate_context_id()
        assert ctx_id.startswith("ctx-")
        assert len(ctx_id) > 10

    def test_generate_task_id(self):
        """Test task ID generation."""
        task_id = generate_task_id()
        assert task_id.startswith("task-")
        assert len(task_id) > 10

    def test_ids_are_unique(self):
        """Test that generated IDs are unique."""
        ids = [generate_message_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique
