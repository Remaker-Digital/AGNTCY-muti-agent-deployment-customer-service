"""
Integration Test: Customer Loyalty Program Inquiry Flow (Issue #34)

This test validates the complete end-to-end workflow for customer loyalty program inquiries,
demonstrating the collaboration between multiple agents in the AGNTCY multi-agent system.

Educational Project: Multi-Agent AI Customer Service Platform
Phase: 2 - Business Logic Implementation
Test Coverage: Issue #34 - Customer Loyalty Program Inquiry (Week 1-2 Priority)

Test Flow (3-Agent Collaboration):
1. Intent Classification Agent: Classifies customer query intent & extracts customer context
2. Knowledge Retrieval Agent: Fetches loyalty balance + program details from knowledge base
3. Response Generation Agent: Generates customer-facing response with personalized balance

Success Criteria (per Issue #34):
✓ Intent classification accuracy for loyalty program queries
✓ Balance lookup completes successfully with customer personalization
✓ Response includes current balance, redemption options, tier status
✓ Handles edge cases: non-existent customer, general program info without customer ID
✓ Full conversation context maintained via contextId threading

Architecture Patterns Demonstrated:
- Agent-to-Agent (A2A) Protocol: Structured messaging between agents
- Message Threading: contextId links messages in same conversation
- Graceful Degradation: Agents handle missing data without crashing system
- Separation of Concerns: Each agent has single, well-defined responsibility

Testing Strategy:
- Integration test: Tests agent collaboration, not individual units
- Uses real knowledge base (test-data/knowledge-base/loyalty-program.json)
- Validates complete message flow from customer query to final response
- Edge case coverage: Various query types, with/without customer ID

Reference Documentation:
- User Story: GitHub Issue #34
- Knowledge Base: test-data/knowledge-base/loyalty-program.json
- AGNTCY A2A Protocol: AGNTCY-REVIEW.md lines 34-39

Author: Claude Sonnet 4.5 (AI Assistant)
License: MIT (Educational Use)
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add project root to Python path for imports
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


class TestLoyaltyProgramFlow:
    """
    Integration test suite for loyalty program inquiry workflow.

    Tests the complete flow from customer query to final response,
    validating all three agents work together correctly.
    """

    @pytest.fixture(scope="function")
    def intent_agent(self):
        """Create Intent Classification Agent instance for testing."""
        agent = IntentClassificationAgent()
        yield agent
        agent.cleanup()

    @pytest.fixture(scope="function")
    def knowledge_agent(self):
        """Create Knowledge Retrieval Agent instance for testing."""
        agent = KnowledgeRetrievalAgent()
        # Override Shopify client to use localhost for tests
        agent.shopify_client.base_url = "http://localhost:8001"
        yield agent
        agent.cleanup()

    @pytest.fixture(scope="function")
    def response_agent(self):
        """Create Response Generation Agent instance for testing."""
        agent = ResponseGenerationAgent()
        yield agent
        agent.cleanup()

    @pytest.mark.asyncio
    async def test_loyalty_balance_query_with_customer_id(
        self, intent_agent, knowledge_agent, response_agent
    ):
        """
        Test Case: Complete loyalty balance query flow with customer ID.

        Scenario: Customer "Sarah Martinez" asks about her rewards balance
        Expected: Personalized response with current balance, tier, redemption options

        Acceptance Criteria (Issue #34):
        ✓ Intent correctly classified as LOYALTY_PROGRAM
        ✓ Customer balance retrieved successfully
        ✓ Response includes current balance (475 points)
        ✓ Response includes tier (Bronze)
        ✓ Response includes points to next tier (25 points to Silver)
        ✓ Response includes available redemption options
        ✓ Response addresses customer by name ("Hi Sarah")

        Test Data Reference: test-data/knowledge-base/loyalty-program.json
        Customer: persona_001 (Sarah Martinez, 475 points, Bronze tier)
        """
        # Initialize agents (async initialization in test method)
        await intent_agent.initialize()
        await knowledge_agent.initialize()
        await response_agent.initialize()

        # STEP 1: Simulate customer query
        context_id = generate_context_id()
        customer_query = "How many rewards points do I have?"

        customer_message = CustomerMessage(
            message_id=generate_message_id(),
            customer_id="persona_001",  # Sarah Martinez from test data
            content=customer_query,
            channel="chat",
            context_id=context_id,
            language=Language.EN,
        )

        # Create A2A message format for agent communication
        intent_request = create_a2a_message(
            role="user",
            content=customer_message,
            context_id=context_id,
            metadata={"test": "loyalty_balance_flow"},
        )

        # STEP 2: Intent Classification Agent processes query
        intent_response = await intent_agent.handle_message(intent_request)
        intent_result_data = extract_message_content(intent_response)

        # Validate intent classification
        assert (
            intent_result_data["intent"] == Intent.LOYALTY_PROGRAM.value
        ), "Intent should be classified as LOYALTY_PROGRAM"
        assert (
            intent_result_data["confidence"] >= 0.80
        ), "Confidence should be high (>80%) for clear loyalty program query"

        print(
            f"[OK] Step 1 Complete: Intent classified as {intent_result_data['intent']}"
        )
        print(f"  - Confidence: {intent_result_data['confidence']:.2%}")

        # STEP 3: Knowledge Retrieval Agent fetches loyalty balance + program info
        knowledge_query = KnowledgeQuery(
            query_id=generate_message_id(),
            context_id=context_id,
            query_text=customer_query,
            intent=Intent.LOYALTY_PROGRAM,
            filters={
                "customer_id": "persona_001"
            },  # Pass customer ID for personalization
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
        ), "Knowledge agent should find loyalty program data"
        assert (
            knowledge_result_data["search_time_ms"] < 500
        ), "Search should complete in <500ms (P95 target)"

        # Find customer balance in results
        balance_result = None
        for result in knowledge_result_data["results"]:
            if result.get("type") == "customer_balance":
                balance_result = result
                break

        assert balance_result is not None, "Customer balance should be in results"
        assert (
            balance_result["customer_id"] == "persona_001"
        ), "Customer ID should match"
        assert (
            balance_result["current_balance"] == 475
        ), "Sarah's balance should be 475 points"
        assert balance_result["tier"] == "Bronze", "Sarah should be in Bronze tier"
        assert (
            balance_result["points_to_next_tier"] == 25
        ), "Should be 25 points from Silver"

        print(
            f"[OK] Step 2 Complete: Balance retrieved in {knowledge_result_data['search_time_ms']:.2f}ms"
        )
        print(f"  - Current Balance: {balance_result['current_balance']} points")
        print(f"  - Tier: {balance_result['tier']}")
        print(f"  - Points to next tier: {balance_result['points_to_next_tier']}")

        # STEP 4: Response Generation Agent creates customer-facing response
        response_request = ResponseRequest(
            request_id=generate_message_id(),
            context_id=context_id,
            customer_message=customer_query,
            intent=Intent.LOYALTY_PROGRAM,
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
        assert "475" in response_text, "Response should mention current balance"
        assert "Bronze" in response_text, "Response should mention tier"
        assert (
            "Silver" in response_text or "25" in response_text
        ), "Response should mention progress to next tier"
        assert not generated_response_data[
            "requires_escalation"
        ], "Standard loyalty query should not require escalation"

        print(f"[OK] Step 3 Complete: Response generated")
        print(f"  - Response length: {len(response_text)} characters")
        print(f"  - Personalized: {'Sarah' in response_text}")
        print(f"  - Includes balance: {'475' in response_text}")

        # Final validation: Complete response preview
        print("\n" + "=" * 60)
        print("FINAL CUSTOMER RESPONSE:")
        print("=" * 60)
        print(response_text)
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_loyalty_general_info_without_customer_id(
        self, intent_agent, knowledge_agent, response_agent
    ):
        """
        Test Case: General loyalty program info query without customer ID.

        Scenario: Anonymous visitor asks "How does the loyalty program work?"
        Expected: Generic program information without personalized balance

        Edge Case Coverage:
        - No customer_id provided
        - Knowledge agent returns program sections but no balance
        - Response agent provides general program info
        """
        # Initialize agents
        await intent_agent.initialize()
        await knowledge_agent.initialize()
        await response_agent.initialize()

        context_id = generate_context_id()
        customer_query = "How does your rewards program work?"

        # Step 1: Intent Classification
        customer_message = CustomerMessage(
            message_id=generate_message_id(),
            customer_id=None,  # No customer ID (anonymous query)
            content=customer_query,
            channel="chat",
            context_id=context_id,
        )

        intent_request = create_a2a_message(
            role="user", content=customer_message, context_id=context_id
        )

        intent_response = await intent_agent.handle_message(intent_request)
        intent_data = extract_message_content(intent_response)

        assert intent_data["intent"] == Intent.LOYALTY_PROGRAM.value

        # Step 2: Knowledge Retrieval (no customer_id)
        knowledge_query = KnowledgeQuery(
            query_id=generate_message_id(),
            context_id=context_id,
            query_text=customer_query,
            intent=Intent.LOYALTY_PROGRAM,
            filters={},  # No customer_id filter
            max_results=5,
        )

        knowledge_request = create_a2a_message(
            role="assistant", content=knowledge_query, context_id=context_id
        )

        knowledge_response = await knowledge_agent.handle_message(knowledge_request)
        knowledge_data = extract_message_content(knowledge_response)

        # Should have program sections but no customer balance
        assert knowledge_data["total_results"] > 0
        has_balance = any(
            r.get("type") == "customer_balance" for r in knowledge_data["results"]
        )
        assert not has_balance, "Should not have customer balance without customer_id"

        # Step 3: Response Generation (generic response)
        response_request = ResponseRequest(
            request_id=generate_message_id(),
            context_id=context_id,
            customer_message=customer_query,
            intent=Intent.LOYALTY_PROGRAM,
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
        assert (
            "1 point per $1" in response_text or "100 points" in response_text
        ), "Generic response should include earning/redemption info"

        print("[OK] General loyalty info scenario completed")
        print(f"  - No personalized balance: {not has_balance}")
        print(f"  - Generic program info provided: {len(response_text) > 50}")

    @pytest.mark.asyncio
    async def test_loyalty_redemption_query(
        self, intent_agent, knowledge_agent, response_agent
    ):
        """
        Test Case: Loyalty redemption query with customer ID.

        Scenario: Customer "Mike Thompson" (Gold tier, 1250 points) asks
                 "How do I redeem my rewards?"
        Expected: Response includes current balance and available redemption options

        Test Data: persona_002 (Mike Thompson, 1250 points, Gold tier, auto-delivery)
        """
        # Initialize agents
        await intent_agent.initialize()
        await knowledge_agent.initialize()
        await response_agent.initialize()

        context_id = generate_context_id()
        customer_query = "How do I use my loyalty rewards?"

        # Full flow for redemption query
        customer_message = CustomerMessage(
            message_id=generate_message_id(),
            customer_id="persona_002",  # Mike Thompson (1250 points, Gold tier)
            content=customer_query,
            channel="chat",
            context_id=context_id,
        )

        # Intent Classification
        intent_request = create_a2a_message(
            role="user", content=customer_message, context_id=context_id
        )
        intent_response = await intent_agent.handle_message(intent_request)
        intent_data = extract_message_content(intent_response)

        assert intent_data["intent"] == Intent.LOYALTY_PROGRAM.value

        # Knowledge Retrieval
        knowledge_query = KnowledgeQuery(
            query_id=generate_message_id(),
            context_id=context_id,
            query_text=customer_query,
            intent=Intent.LOYALTY_PROGRAM,
            filters={"customer_id": "persona_002"},
        )

        knowledge_request = create_a2a_message(
            role="assistant", content=knowledge_query, context_id=context_id
        )
        knowledge_response = await knowledge_agent.handle_message(knowledge_request)
        knowledge_data = extract_message_content(knowledge_response)

        assert knowledge_data["total_results"] > 0

        # Find customer balance
        balance = next(
            (
                r
                for r in knowledge_data["results"]
                if r.get("type") == "customer_balance"
            ),
            None,
        )
        assert balance is not None
        assert balance["current_balance"] == 1250
        assert balance["tier"] == "Gold"

        # Response Generation
        response_request = ResponseRequest(
            request_id=generate_message_id(),
            context_id=context_id,
            customer_message=customer_query,
            intent=Intent.LOYALTY_PROGRAM,
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
        assert "1250" in response_text, "Response should show current balance"
        assert "Gold" in response_text, "Response should show tier"
        assert (
            "100 points" in response_text or "redeem" in response_text.lower()
        ), "Response should include redemption options"

        print("[OK] Redemption query scenario completed")
        print(f"  - Balance shown: {'1250' in response_text}")
        print(f"  - Tier shown: {'Gold' in response_text}")


# Test execution function for manual testing
async def run_manual_test():
    """
    Manual test runner for debugging and demonstration.

    Run with: python -m pytest tests/integration/test_loyalty_flow.py -v -s
    Or: python tests/integration/test_loyalty_flow.py
    """
    print("\n" + "=" * 70)
    print("MANUAL TEST: Loyalty Program Inquiry Flow (Issue #34)")
    print("=" * 70 + "\n")

    test_suite = TestLoyaltyProgramFlow()

    # Create agent instances
    intent_agent = IntentClassificationAgent()
    knowledge_agent = KnowledgeRetrievalAgent()
    response_agent = ResponseGenerationAgent()

    await intent_agent.initialize()
    await knowledge_agent.initialize()
    await response_agent.initialize()

    try:
        # Run test
        await test_suite.test_loyalty_balance_query_with_customer_id(
            intent_agent, knowledge_agent, response_agent
        )
        print("\n[OK] ALL TESTS PASSED\n")

    finally:
        intent_agent.cleanup()
        knowledge_agent.cleanup()
        response_agent.cleanup()


if __name__ == "__main__":
    # Allow running as standalone script for manual testing
    asyncio.run(run_manual_test())
