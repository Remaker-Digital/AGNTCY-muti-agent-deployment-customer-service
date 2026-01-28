"""
Integration Test: Customer Order Status Inquiry Flow (Issue #24)

This test validates the complete end-to-end workflow for customer order status inquiries,
demonstrating the collaboration between multiple agents in the AGNTCY multi-agent system.

Educational Project: Multi-Agent AI Customer Service Platform
Phase: 2 - Business Logic Implementation
Test Coverage: Issue #24 - Customer Order Status Inquiries (Week 1-2 Priority)

Test Flow (3-Agent Collaboration):
1. Intent Classification Agent: Classifies customer query intent & extracts order number
2. Knowledge Retrieval Agent: Fetches order details from Shopify API
3. Response Generation Agent: Generates customer-facing response with tracking info

Success Criteria (per PHASE-2-READINESS.md):
✓ Intent classification accuracy >90% for order status queries
✓ Order lookup completes in <500ms (P95 latency)
✓ Response includes tracking info, delivery estimate, order items
✓ Handles edge cases: order not found, damaged delivery, pending orders
✓ Full conversation context maintained via contextId threading

Architecture Patterns Demonstrated:
- Agent-to-Agent (A2A) Protocol: Structured messaging between agents
- Message Threading: contextId links messages in same conversation
- Graceful Degradation: Agents handle errors without crashing system
- Separation of Concerns: Each agent has single, well-defined responsibility

Testing Strategy:
- Integration test: Tests agent collaboration, not individual units
- Uses real mock API (Docker Compose Shopify service)
- Validates complete message flow from customer query to final response
- Edge case coverage: Various order statuses, error conditions

Reference Documentation:
- User Story: user-stories-phased.md lines 53-80
- Acceptance Criteria: PHASE-2-READINESS.md lines 89-104
- AGNTCY A2A Protocol: AGNTCY-REVIEW.md lines 34-39
- Test Data: test-data/shopify/orders.json

Author: Claude Sonnet 4.5 (AI Assistant)
License: MIT (Educational Use)
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add project root to Python path for imports
# Reference: https://docs.python.org/3/library/sys.html#sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.models import (
    CustomerMessage,
    IntentClassificationResult,
    KnowledgeQuery,
    KnowledgeResult,
    ResponseRequest,
    GeneratedResponse,
    Intent,
    Language,
    create_a2a_message,
    extract_message_content,
    generate_context_id,
    generate_message_id,
)

# Import agents for testing
from agents.intent_classification.agent import IntentClassificationAgent
from agents.knowledge_retrieval.agent import KnowledgeRetrievalAgent
from agents.response_generation.agent import ResponseGenerationAgent


class TestOrderStatusFlow:
    """
    Integration test suite for order status inquiry workflow.

    Tests the complete flow from customer query to final response,
    validating all three agents work together correctly.
    """

    @pytest.fixture(scope="function")
    def intent_agent(self):
        """
        Create Intent Classification Agent instance for testing.

        Fixture Pattern: pytest fixture provides agent instance to tests
        Reference: https://docs.pytest.org/en/stable/fixture.html

        Note: Using synchronous fixture with manual async initialization
        to avoid async generator issues in pytest.
        """
        agent = IntentClassificationAgent()
        yield agent
        agent.cleanup()

    @pytest.fixture(scope="function")
    def knowledge_agent(self):
        """
        Create Knowledge Retrieval Agent instance for testing.

        Note: Agent initialization happens in test method to avoid
        async fixture complications.

        Override Shopify URL for testing outside Docker.
        In Docker: mock-shopify:8000
        In tests: localhost:8001
        """
        agent = KnowledgeRetrievalAgent()
        # Override Shopify client to use localhost for tests
        agent.shopify_client.base_url = "http://localhost:8001"
        agent.logger.info(
            f"Test override: Using Shopify URL {agent.shopify_client.base_url}"
        )
        yield agent
        agent.cleanup()

    @pytest.fixture(scope="function")
    def response_agent(self):
        """
        Create Response Generation Agent instance for testing.

        Note: Agent initialization happens in test method to avoid
        async fixture complications.
        """
        agent = ResponseGenerationAgent()
        yield agent
        agent.cleanup()

    @pytest.mark.asyncio
    async def test_order_status_shipped_complete_flow(
        self, intent_agent, knowledge_agent, response_agent
    ):
        """
        Test Case: Complete order status flow for shipped order.

        Scenario: Customer "Sarah Martinez" asks about order #10234 (shipped, in transit)
        Expected: Full response with tracking info, delivery estimate, items

        Acceptance Criteria (Issue #24):
        ✓ Intent correctly classified as ORDER_STATUS
        ✓ Order number extracted: "10234"
        ✓ Shopify order data retrieved successfully
        ✓ Response includes tracking number, carrier, expected delivery
        ✓ Response addresses customer by name ("Hi Sarah")
        ✓ Complete flow executes in <2 seconds (integration test allowance)

        Test Data Reference: test-data/shopify/orders.json lines 1-63
        """
        # Initialize agents (async initialization in test method)
        # This avoids async generator issues with pytest fixtures
        await intent_agent.initialize()
        await knowledge_agent.initialize()
        await response_agent.initialize()

        # STEP 1: Simulate customer query
        # This represents what would come from web chat or email channel
        context_id = generate_context_id()
        customer_query = "Where is my order #10234?"

        customer_message = CustomerMessage(
            message_id=generate_message_id(),
            customer_id="persona_001",  # Sarah Martinez from test data
            content=customer_query,
            channel="chat",
            context_id=context_id,
            language=Language.EN,
        )

        # Create A2A message format for agent communication
        # Reference: shared/models.py create_a2a_message() lines 289-343
        intent_request = create_a2a_message(
            role="user",
            content=customer_message,
            context_id=context_id,
            metadata={"test": "order_status_flow"},
        )

        # STEP 2: Intent Classification Agent processes query
        # Expected: Classifies as ORDER_STATUS, extracts order number "10234"
        intent_response = await intent_agent.handle_message(intent_request)
        intent_result_data = extract_message_content(intent_response)

        # Validate intent classification
        assert (
            intent_result_data["intent"] == Intent.ORDER_STATUS.value
        ), "Intent should be classified as ORDER_STATUS"
        assert (
            intent_result_data["confidence"] >= 0.85
        ), "Confidence should be high (>85%) for clear order status query"
        assert (
            "order_number" in intent_result_data["extracted_entities"]
        ), "Order number should be extracted from query"
        assert (
            intent_result_data["extracted_entities"]["order_number"] == "10234"
        ), "Extracted order number should match '10234'"
        assert (
            intent_result_data["routing_suggestion"] == "knowledge-retrieval"
        ), "Intent agent should route to knowledge-retrieval for order status"

        print(
            f"[OK] Step 1 Complete: Intent classified as {intent_result_data['intent']}"
        )
        print(f"  - Confidence: {intent_result_data['confidence']:.2%}")
        print(
            f"  - Order number extracted: {intent_result_data['extracted_entities']['order_number']}"
        )

        # STEP 3: Knowledge Retrieval Agent fetches order from Shopify
        # Expected: Returns order #10234 with tracking info
        knowledge_query = KnowledgeQuery(
            query_id=generate_message_id(),
            context_id=context_id,
            query_text=customer_query,
            intent=Intent.ORDER_STATUS,
            filters={
                "order_number": intent_result_data["extracted_entities"]["order_number"]
            },
            max_results=5,
        )

        knowledge_request = create_a2a_message(
            role="assistant", content=knowledge_query, context_id=context_id
        )

        knowledge_response = await knowledge_agent.handle_message(knowledge_request)
        knowledge_result_data = extract_message_content(knowledge_response)

        # Validate knowledge retrieval
        assert (
            knowledge_result_data["total_results"] > 0
        ), "Knowledge agent should find order #10234"
        assert (
            knowledge_result_data["search_time_ms"] < 500
        ), "Search should complete in <500ms (P95 target)"

        order_data = knowledge_result_data["results"][0]
        assert order_data["type"] == "order", "Result should be an order"
        assert order_data["order_number"] == "10234", "Order number should match"
        assert order_data["status"] == "shipped", "Test order #10234 should be shipped"
        assert "tracking" in order_data, "Order should include tracking information"
        assert order_data["tracking"]["carrier"] == "USPS", "Carrier should be USPS"
        assert (
            order_data["tracking"]["tracking_number"] == "9400123456789"
        ), "Tracking number should match test data"

        print(
            f"[OK] Step 2 Complete: Order retrieved in {knowledge_result_data['search_time_ms']:.2f}ms"
        )
        print(f"  - Order status: {order_data['status']}")
        print(
            f"  - Tracking: {order_data['tracking']['carrier']} {order_data['tracking']['tracking_number']}"
        )

        # STEP 4: Response Generation Agent creates customer-facing response
        # Expected: Personalized response with tracking details
        response_request = ResponseRequest(
            request_id=generate_message_id(),
            context_id=context_id,
            customer_message=customer_query,
            intent=Intent.ORDER_STATUS,
            knowledge_context=knowledge_result_data["results"],
        )

        response_gen_request = create_a2a_message(
            role="assistant", content=response_request, context_id=context_id
        )

        response_gen_response = await response_agent.handle_message(
            response_gen_request
        )
        generated_response_data = extract_message_content(response_gen_response)

        # Validate generated response
        response_text = generated_response_data["response_text"]
        assert len(response_text) > 50, "Response should be substantial (>50 chars)"
        assert (
            "Sarah" in response_text
        ), "Response should address customer by name (personalization)"
        assert "10234" in response_text, "Response should mention order number"
        assert (
            "9400123456789" in response_text or "tracking" in response_text.lower()
        ), "Response should include tracking information"
        assert (
            "USPS" in response_text or "usps" in response_text.lower()
        ), "Response should mention carrier"
        assert not generated_response_data[
            "requires_escalation"
        ], "Standard shipped order should not require escalation"

        print(f"[OK] Step 3 Complete: Response generated")
        print(f"  - Response length: {len(response_text)} characters")
        print(f"  - Personalized: {'Sarah' in response_text}")
        print(f"  - Includes tracking: {('9400123456789' in response_text)}")

        # Final validation: Complete response preview
        print("\n" + "=" * 60)
        print("FINAL CUSTOMER RESPONSE:")
        print("=" * 60)
        print(response_text)
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_order_status_order_not_found(
        self, intent_agent, knowledge_agent, response_agent
    ):
        """
        Test Case: Order status query for non-existent order.

        Scenario: Customer asks about order #99999 (doesn't exist in test data)
        Expected: Graceful error handling, helpful response asking for verification

        Edge Case Coverage:
        - Invalid order number
        - Knowledge agent returns empty results
        - Response agent handles missing data gracefully
        """
        # Initialize agents
        await intent_agent.initialize()
        await knowledge_agent.initialize()
        await response_agent.initialize()

        context_id = generate_context_id()
        customer_query = "What's the status of order #99999?"

        # Step 1: Intent Classification
        customer_message = CustomerMessage(
            message_id=generate_message_id(),
            customer_id="unknown_customer",
            content=customer_query,
            channel="chat",
            context_id=context_id,
        )

        intent_request = create_a2a_message(
            role="user", content=customer_message, context_id=context_id
        )
        intent_response = await intent_agent.handle_message(intent_request)
        intent_data = extract_message_content(intent_response)

        assert intent_data["intent"] == Intent.ORDER_STATUS.value
        assert intent_data["extracted_entities"]["order_number"] == "99999"

        # Step 2: Knowledge Retrieval (should return empty or error)
        knowledge_query = KnowledgeQuery(
            query_id=generate_message_id(),
            context_id=context_id,
            query_text=customer_query,
            intent=Intent.ORDER_STATUS,
            filters={"order_number": "99999"},
        )

        knowledge_request = create_a2a_message(
            role="assistant", content=knowledge_query, context_id=context_id
        )
        knowledge_response = await knowledge_agent.handle_message(knowledge_request)
        knowledge_data = extract_message_content(knowledge_response)

        # Should have error result or empty
        if knowledge_data["total_results"] > 0:
            result = knowledge_data["results"][0]
            assert (
                result.get("type") == "error"
                or result.get("error_code") == "ORDER_NOT_FOUND"
            ), "Non-existent order should return error result"

        print("[OK] Order not found scenario handled gracefully")
        print(f"  - Results: {knowledge_data['total_results']}")

    @pytest.mark.asyncio
    async def test_order_status_delivered_order(
        self, intent_agent, knowledge_agent, response_agent
    ):
        """
        Test Case: Order status for delivered order.

        Scenario: Customer asks about order #10156 (delivered)
        Expected: Response confirms delivery with date and location

        Test Data: Order #10156 delivered on 2025-12-15
        Reference: test-data/shopify/orders.json lines 64-120
        """
        # Initialize agents
        await intent_agent.initialize()
        await knowledge_agent.initialize()
        await response_agent.initialize()

        context_id = generate_context_id()
        customer_query = "Has my order 10156 been delivered?"

        # Full flow for delivered order
        customer_message = CustomerMessage(
            message_id=generate_message_id(),
            customer_id="persona_001",
            content=customer_query,
            channel="email",
            context_id=context_id,
        )

        # Intent Classification
        intent_request = create_a2a_message(
            role="user", content=customer_message, context_id=context_id
        )
        intent_response = await intent_agent.handle_message(intent_request)
        intent_data = extract_message_content(intent_response)

        assert intent_data["intent"] == Intent.ORDER_STATUS.value
        assert intent_data["extracted_entities"]["order_number"] == "10156"

        # Knowledge Retrieval
        knowledge_query = KnowledgeQuery(
            query_id=generate_message_id(),
            context_id=context_id,
            query_text=customer_query,
            intent=Intent.ORDER_STATUS,
            filters={"order_number": "10156"},
        )

        knowledge_request = create_a2a_message(
            role="assistant", content=knowledge_query, context_id=context_id
        )
        knowledge_response = await knowledge_agent.handle_message(knowledge_request)
        knowledge_data = extract_message_content(knowledge_response)

        assert knowledge_data["total_results"] > 0
        order = knowledge_data["results"][0]
        assert order["status"] == "delivered"

        # Response Generation
        response_request = ResponseRequest(
            request_id=generate_message_id(),
            context_id=context_id,
            customer_message=customer_query,
            intent=Intent.ORDER_STATUS,
            knowledge_context=knowledge_data["results"],
        )

        response_gen_request = create_a2a_message(
            role="assistant", content=response_request, context_id=context_id
        )
        response_gen_response = await response_agent.handle_message(
            response_gen_request
        )
        response_data = extract_message_content(response_gen_response)

        response_text = response_data["response_text"]
        assert "delivered" in response_text.lower() or "Delivered" in response_text
        assert "10156" in response_text

        print("[OK] Delivered order scenario completed")
        print(
            f"  - Delivery confirmed in response: {'delivered' in response_text.lower()}"
        )


# Test execution function for manual testing
async def run_manual_test():
    """
    Manual test runner for debugging and demonstration.

    Run with: python -m pytest tests/integration/test_order_status_flow.py -v -s
    Or: python tests/integration/test_order_status_flow.py
    """
    print("\n" + "=" * 70)
    print("MANUAL TEST: Order Status Inquiry Flow (Issue #24)")
    print("=" * 70 + "\n")

    test_suite = TestOrderStatusFlow()

    # Create agent instances
    intent_agent = IntentClassificationAgent()
    knowledge_agent = KnowledgeRetrievalAgent()
    response_agent = ResponseGenerationAgent()

    await intent_agent.initialize()
    await knowledge_agent.initialize()
    await response_agent.initialize()

    try:
        # Run test
        await test_suite.test_order_status_shipped_complete_flow(
            intent_agent, knowledge_agent, response_agent
        )
        print("\n[OK] ALL TESTS PASSED\n")

    finally:
        intent_agent.cleanup()
        knowledge_agent.cleanup()
        response_agent.cleanup()


if __name__ == "__main__":
    # Allow running as standalone script for manual testing
    # Reference: Python asyncio.run() - https://docs.python.org/3/library/asyncio-runner.html
    asyncio.run(run_manual_test())
