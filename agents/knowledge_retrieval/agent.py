"""
Knowledge Retrieval Agent
Searches internal knowledge bases, product catalogs, and documentation

Phase 1: Mock API calls to Shopify, Zendesk, internal docs
Phase 2: Real search with Azure Cognitive Search or similar
"""

import sys
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Any

# Add shared utilities to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import (
    get_factory,
    shutdown_factory,
    setup_logging,
    load_config,
    handle_graceful_shutdown
)
from shared.models import (
    KnowledgeQuery,
    KnowledgeResult,
    Intent,
    Language,
    create_a2a_message,
    extract_message_content,
    generate_message_id
)


class KnowledgeRetrievalAgent:
    """
    Knowledge Retrieval Agent - Searches knowledge bases and external systems.

    Uses AGNTCY SDK MCP protocol for standardized tool interface.
    Integrates with:
    - Shopify API (product catalog, orders, inventory)
    - Zendesk API (previous tickets, customer history)
    - Internal documentation (FAQs, policies)
    """

    def __init__(self):
        """Initialize the Knowledge Retrieval Agent."""
        # Load configuration
        self.config = load_config()
        self.agent_topic = self.config["agent_topic"]

        # Setup logging
        self.logger = setup_logging(
            name=self.agent_topic,
            level=self.config["log_level"]
        )

        self.logger.info(f"Initializing Knowledge Retrieval Agent on topic: {self.agent_topic}")

        # Get AGNTCY factory singleton
        self.factory = get_factory()

        # Create transport and client
        self.transport = None
        self.client = None
        self.container = None

        # HTTP client for mock API calls
        self.http_client = httpx.AsyncClient(timeout=10.0)

        # Query counters
        self.queries_processed = 0

    async def initialize(self):
        """Initialize AGNTCY SDK components."""
        self.logger.info("Creating SLIM transport...")

        try:
            # Create SLIM transport
            self.transport = self.factory.create_slim_transport(
                name=f"{self.agent_topic}-transport"
            )

            if self.transport is None:
                self.logger.warning(
                    "SLIM transport not created (SDK may not be available). "
                    "Running in demo mode."
                )
                return

            self.logger.info(f"SLIM transport created: {self.transport}")

            # Create MCP client for tool-based retrieval
            self.logger.info("Creating MCP client...")
            self.client = self.factory.create_mcp_client(
                agent_topic=self.agent_topic,
                transport=self.transport
            )

            if self.client is None:
                self.logger.warning("MCP client not created. Running in demo mode.")
                return

            self.logger.info(f"MCP client created for topic: {self.agent_topic}")
            self.logger.info("Agent initialization complete")

        except Exception as e:
            self.logger.error(f"Failed to initialize AGNTCY components: {e}", exc_info=True)
            raise

    async def handle_message(self, message: dict) -> dict:
        """
        Handle incoming knowledge query and search relevant sources.

        Args:
            message: AGNTCY message with KnowledgeQuery

        Returns:
            KnowledgeResult as A2A message
        """
        self.queries_processed += 1

        try:
            # Extract knowledge query
            content = extract_message_content(message)
            self.logger.debug(f"Received query: {content}")

            # Parse as KnowledgeQuery
            query = KnowledgeQuery(
                query_id=content.get("query_id", generate_message_id()),
                context_id=message.get("contextId", "unknown"),
                query_text=content.get("query_text", ""),
                intent=Intent(content.get("intent", "general_inquiry")),
                filters=content.get("filters", {}),
                max_results=content.get("max_results", 5),
                language=Language(content.get("language", "en"))
            )

            self.logger.info(
                f"Processing knowledge query {query.query_id}: '{query.query_text}' "
                f"(intent: {query.intent.value})"
            )

            # Search knowledge sources based on intent
            import time
            start_time = time.time()
            results = await self._search_knowledge(query)
            search_time_ms = (time.time() - start_time) * 1000

            # Create result
            result = KnowledgeResult(
                query_id=query.query_id,
                context_id=query.context_id,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms,
                confidence=self._calculate_confidence(results)
            )

            self.logger.info(
                f"Knowledge search complete: {len(results)} results in {search_time_ms:.2f}ms "
                f"(confidence: {result.confidence:.2f})"
            )

            # Create response message
            response = create_a2a_message(
                role="assistant",
                content=result,
                context_id=query.context_id,
                task_id=message.get("taskId"),
                metadata={
                    "agent": self.agent_topic,
                    "queries_processed": self.queries_processed
                }
            )

            return response

        except Exception as e:
            self.logger.error(f"Error handling knowledge query: {e}", exc_info=True)
            return create_a2a_message(
                role="assistant",
                content={"error": str(e), "results": []},
                context_id=message.get("contextId", "unknown")
            )

    async def _search_knowledge(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search knowledge sources based on intent and query.

        Args:
            query: Knowledge query with intent and filters

        Returns:
            List of search results
        """
        results = []

        # Route to appropriate knowledge source based on intent
        if query.intent == Intent.ORDER_STATUS:
            results.extend(await self._search_shopify_orders(query))

        elif query.intent == Intent.PRODUCT_INQUIRY:
            results.extend(await self._search_shopify_products(query))

        elif query.intent == Intent.RETURN_REQUEST:
            results.extend(await self._search_return_policy(query))
            results.extend(await self._search_zendesk_tickets(query, topic="return"))

        elif query.intent == Intent.SHIPPING_QUESTION:
            results.extend(await self._search_shipping_policy(query))

        elif query.intent == Intent.PAYMENT_ISSUE:
            results.extend(await self._search_zendesk_tickets(query, topic="payment"))

        else:
            # General inquiry - search FAQs
            results.extend(await self._search_faqs(query))

        # Limit results
        return results[:query.max_results]

    async def _search_shopify_products(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Search Shopify product catalog."""
        try:
            shopify_url = self.config["shopify_url"]
            response = await self.http_client.get(
                f"{shopify_url}/admin/api/2024-01/products.json"
            )

            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])

                # Simple keyword matching in product titles/descriptions
                query_lower = query.query_text.lower()
                matching_products = [
                    {
                        "source": "shopify_products",
                        "type": "product",
                        "title": p["title"],
                        "description": p.get("body_html", ""),
                        "price": p["variants"][0]["price"] if p.get("variants") else "N/A",
                        "url": f"/products/{p['id']}",
                        "relevance": 0.8
                    }
                    for p in products
                    if query_lower in p["title"].lower() or
                       query_lower in p.get("body_html", "").lower()
                ]

                self.logger.debug(f"Found {len(matching_products)} matching products")
                return matching_products[:3]

        except Exception as e:
            self.logger.error(f"Shopify product search failed: {e}")

        return []

    async def _search_shopify_orders(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Search Shopify orders."""
        try:
            # Extract order number from query if present
            order_number = query.filters.get("order_number")

            shopify_url = self.config["shopify_url"]
            response = await self.http_client.get(
                f"{shopify_url}/admin/api/2024-01/orders.json"
            )

            if response.status_code == 200:
                data = response.json()
                orders = data.get("orders", [])

                # Filter by order number if provided
                if order_number:
                    matching_orders = [o for o in orders if str(o.get("id")) == str(order_number)]
                else:
                    matching_orders = orders[:2]  # Return recent orders

                results = [
                    {
                        "source": "shopify_orders",
                        "type": "order",
                        "order_id": o["id"],
                        "status": o.get("financial_status", "unknown"),
                        "total": o.get("total_price", "N/A"),
                        "created_at": o.get("created_at"),
                        "relevance": 0.9 if order_number else 0.6
                    }
                    for o in matching_orders
                ]

                self.logger.debug(f"Found {len(results)} matching orders")
                return results

        except Exception as e:
            self.logger.error(f"Shopify order search failed: {e}")

        return []

    async def _search_zendesk_tickets(
        self,
        query: KnowledgeQuery,
        topic: str = None
    ) -> List[Dict[str, Any]]:
        """Search Zendesk support tickets."""
        try:
            zendesk_url = self.config["zendesk_url"]
            response = await self.http_client.get(
                f"{zendesk_url}/api/v2/tickets.json"
            )

            if response.status_code == 200:
                data = response.json()
                tickets = data.get("tickets", [])

                # Filter by topic/tags if provided
                if topic:
                    tickets = [t for t in tickets if topic in t.get("tags", [])]

                results = [
                    {
                        "source": "zendesk_tickets",
                        "type": "ticket",
                        "ticket_id": t["id"],
                        "subject": t["subject"],
                        "status": t["status"],
                        "created_at": t.get("created_at"),
                        "relevance": 0.7
                    }
                    for t in tickets[:2]
                ]

                self.logger.debug(f"Found {len(results)} relevant tickets")
                return results

        except Exception as e:
            self.logger.error(f"Zendesk ticket search failed: {e}")

        return []

    async def _search_faqs(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Search internal FAQs (mock data for Phase 1)."""
        # Phase 1: Static FAQ responses
        # Phase 2: Replace with real search (Azure Cognitive Search, Elasticsearch, etc.)
        mock_faqs = [
            {
                "source": "internal_faqs",
                "type": "faq",
                "question": "How do I track my order?",
                "answer": "You can track your order using the tracking link sent to your email.",
                "category": "shipping",
                "relevance": 0.6
            },
            {
                "source": "internal_faqs",
                "type": "faq",
                "question": "What is your return policy?",
                "answer": "We accept returns within 30 days of purchase for a full refund.",
                "category": "returns",
                "relevance": 0.5
            }
        ]

        self.logger.debug(f"Returning {len(mock_faqs)} FAQ results")
        return mock_faqs

    async def _search_return_policy(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Get return policy information."""
        return [{
            "source": "company_policies",
            "type": "policy",
            "title": "Return Policy",
            "content": "We accept returns within 30 days of purchase. Items must be unused and in original packaging.",
            "url": "/policies/returns",
            "relevance": 0.9
        }]

    async def _search_shipping_policy(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Get shipping policy information."""
        return [{
            "source": "company_policies",
            "type": "policy",
            "title": "Shipping Information",
            "content": "Standard shipping takes 5-7 business days. Express shipping available for 2-3 day delivery.",
            "url": "/policies/shipping",
            "relevance": 0.9
        }]

    def _calculate_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence score based on results."""
        if not results:
            return 0.0

        # Average relevance scores
        avg_relevance = sum(r.get("relevance", 0.5) for r in results) / len(results)

        # Boost confidence if we have diverse sources
        unique_sources = len(set(r.get("source") for r in results))
        diversity_boost = min(unique_sources * 0.1, 0.3)

        return min(avg_relevance + diversity_boost, 1.0)

    def cleanup(self):
        """Cleanup resources on shutdown."""
        self.logger.info("Cleaning up Knowledge Retrieval Agent...")

        # Close HTTP client
        asyncio.create_task(self.http_client.aclose())

        if self.container:
            try:
                self.container.stop()
            except Exception as e:
                self.logger.error(f"Error stopping container: {e}")

        shutdown_factory()
        self.logger.info("Cleanup complete")

    async def run_demo_mode(self):
        """Run in demo mode without SDK."""
        self.logger.info("Running in DEMO MODE (no SDK connection)")
        self.logger.info("Simulating knowledge retrieval...")

        # Demo: Process sample queries
        sample_queries = [
            {
                "contextId": "demo-ctx-001",
                "taskId": "demo-task-001",
                "parts": [{
                    "type": "text",
                    "content": {
                        "query_id": "q-001",
                        "query_text": "wireless headphones",
                        "intent": "product_inquiry",
                        "max_results": 3
                    }
                }]
            },
            {
                "contextId": "demo-ctx-002",
                "taskId": "demo-task-002",
                "parts": [{
                    "type": "text",
                    "content": {
                        "query_id": "q-002",
                        "query_text": "order status",
                        "intent": "order_status",
                        "filters": {"order_number": "12345"},
                        "max_results": 5
                    }
                }]
            }
        ]

        for msg in sample_queries:
            self.logger.info("=" * 60)
            result = await self.handle_message(msg)
            content = extract_message_content(result)
            self.logger.info(f"Demo Result: Found {content.get('total_results', 0)} results")
            if content.get("results"):
                for idx, r in enumerate(content["results"][:2], 1):
                    self.logger.info(f"  {idx}. [{r.get('source')}] {r.get('title', r.get('question', 'N/A'))}")
            await asyncio.sleep(2)

        # Keep alive
        self.logger.info("Demo complete. Keeping alive for health checks...")
        try:
            while True:
                await asyncio.sleep(30)
                self.logger.debug(f"Heartbeat - {self.queries_processed} queries processed")
        except asyncio.CancelledError:
            self.logger.info("Demo mode cancelled")


async def main():
    """Main entry point for Knowledge Retrieval Agent."""
    agent = KnowledgeRetrievalAgent()

    # Setup graceful shutdown
    handle_graceful_shutdown(agent.logger, cleanup_callback=agent.cleanup)

    try:
        # Initialize AGNTCY components
        await agent.initialize()

        # If SDK not available, run demo mode
        if agent.client is None:
            await agent.run_demo_mode()
        else:
            # Production mode
            agent.logger.info("Agent ready and waiting for queries...")
            while True:
                await asyncio.sleep(10)
                agent.logger.debug("Agent alive - waiting for queries")

    except KeyboardInterrupt:
        agent.logger.info("Received keyboard interrupt")
    except Exception as e:
        agent.logger.error(f"Agent crashed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
