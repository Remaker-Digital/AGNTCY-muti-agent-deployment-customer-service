"""
Integration tests for agent message handling
Tests agents with AGNTCY SDK integration
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.integration
class TestIntentClassificationAgent:
    """Integration tests for Intent Classification Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that Intent Classification Agent initializes."""
        from agents.intent_classification.agent import IntentClassificationAgent

        agent = IntentClassificationAgent()
        assert agent.agent_topic is not None
        assert agent.logger is not None
        assert agent.factory is not None

    @pytest.mark.asyncio
    async def test_handle_message_order_status(self, sample_a2a_message):
        """Test handling order status message."""
        from agents.intent_classification.agent import IntentClassificationAgent
        from shared.models import extract_message_content, Intent

        agent = IntentClassificationAgent()

        # Modify message for order status
        sample_a2a_message["parts"][0]["content"][
            "content"
        ] = "Where is my order #12345?"

        result = await agent.handle_message(sample_a2a_message)

        assert result is not None
        content = extract_message_content(result)
        assert content["intent"] == Intent.ORDER_STATUS.value
        assert content["confidence"] > 0

    @pytest.mark.asyncio
    async def test_handle_message_return_request(self, sample_a2a_message):
        """Test handling return request message."""
        from agents.intent_classification.agent import IntentClassificationAgent
        from shared.models import extract_message_content, Intent

        agent = IntentClassificationAgent()

        # Modify message for return request
        sample_a2a_message["parts"][0]["content"][
            "content"
        ] = "I want to return my product"

        result = await agent.handle_message(sample_a2a_message)

        content = extract_message_content(result)
        assert content["intent"] == Intent.RETURN_REQUEST.value


@pytest.mark.integration
class TestKnowledgeRetrievalAgent:
    """Integration tests for Knowledge Retrieval Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that Knowledge Retrieval Agent initializes."""
        from agents.knowledge_retrieval.agent import KnowledgeRetrievalAgent

        agent = KnowledgeRetrievalAgent()
        assert agent.agent_topic is not None
        assert agent.logger is not None
        assert agent.http_client is not None

    @pytest.mark.asyncio
    async def test_classify_intent_mock(self):
        """Test mock intent classification."""
        from agents.intent_classification.agent import IntentClassificationAgent
        from shared.models import Intent

        agent = IntentClassificationAgent()

        # Test order status classification
        intent, confidence, entities = agent._classify_intent_mock(
            "Where is my order #12345?"
        )
        assert intent == Intent.ORDER_STATUS
        assert confidence > 0.8
        assert "order_number" in entities

        # Test return request classification
        intent, confidence, entities = agent._classify_intent_mock(
            "I want to return this item"
        )
        assert intent == Intent.RETURN_REQUEST


@pytest.mark.integration
class TestResponseGenerationAgent:
    """Integration tests for Response Generation Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that Response Generation Agent initializes."""
        from agents.response_generation.agent import ResponseGenerationAgent

        agent = ResponseGenerationAgent()
        assert agent.agent_topic is not None
        assert agent.logger is not None

    @pytest.mark.asyncio
    async def test_generate_template_response(self):
        """Test template response generation (Phase 2 canned responses)."""
        from agents.response_generation.agent import ResponseGenerationAgent
        from shared.models import ResponseRequest, Intent

        agent = ResponseGenerationAgent()

        request = ResponseRequest(
            request_id="req-001",
            context_id="ctx-001",
            customer_message="Test order status query",
            intent=Intent.ORDER_STATUS,
        )

        # Use template response (renamed from canned response in Phase 4)
        response_data = agent._generate_template_response(request)
        # Template response returns dict with response_text
        if isinstance(response_data, dict):
            assert "response_text" in response_data
            assert len(response_data["response_text"]) > 0
        else:
            # May return string directly in some modes
            assert isinstance(response_data, str)
            assert len(response_data) > 0


@pytest.mark.integration
class TestEscalationAgent:
    """Integration tests for Escalation Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that Escalation Agent initializes."""
        from agents.escalation.agent import EscalationAgent

        agent = EscalationAgent()
        assert agent.agent_topic is not None
        assert agent.logger is not None

    @pytest.mark.asyncio
    async def test_analyze_mock_negative_sentiment(self):
        """Test mock sentiment analysis for negative messages."""
        from agents.escalation.agent import EscalationAgent
        from shared.models import Sentiment

        agent = EscalationAgent()

        sentiment, complexity = agent._analyze_mock(
            "This is terrible and unacceptable!"
        )
        assert sentiment == Sentiment.VERY_NEGATIVE
        assert complexity > 0.8

    @pytest.mark.asyncio
    async def test_analyze_mock_positive_sentiment(self):
        """Test mock sentiment analysis for positive messages."""
        from agents.escalation.agent import EscalationAgent
        from shared.models import Sentiment

        agent = EscalationAgent()

        sentiment, complexity = agent._analyze_mock("Thanks! This is great!")
        assert sentiment == Sentiment.POSITIVE
        assert complexity < 0.5


@pytest.mark.integration
class TestAnalyticsAgent:
    """Integration tests for Analytics Agent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that Analytics Agent initializes."""
        from agents.analytics.agent import AnalyticsAgent

        agent = AnalyticsAgent()
        assert agent.agent_topic is not None
        assert agent.logger is not None
        assert agent.http_client is not None


@pytest.mark.integration
@pytest.mark.skip(reason="Requires Docker containers and AGNTCY SDK")
class TestEndToEndFlow:
    """End-to-end integration tests (requires full stack)."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test complete conversation flow through all agents."""
        # This would test:
        # Customer message → Intent Classification → Knowledge Retrieval
        # → Response Generation → (possibly) Escalation → Analytics
        pass
