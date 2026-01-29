"""
Knowledge Retrieval Agent
Searches internal knowledge bases, product catalogs, and documentation

Phase 1: Mock API calls to Shopify, Zendesk, internal docs
Phase 2: Coffee/brewing business specific with real Shopify integration
Phase 4+: Azure OpenAI embeddings for semantic search (RAG)

Refactored to use BaseAgent pattern for reduced code duplication.
"""

import asyncio
import httpx
import time
import math
from pathlib import Path
from typing import List, Dict, Any, Optional

from shared.base_agent import BaseAgent, run_agent
from shared.models import (
    KnowledgeQuery,
    KnowledgeResult,
    Intent,
    Language,
    extract_message_content,
    generate_message_id,
)

# Import Phase 2 clients
from agents.knowledge_retrieval.shopify_client import ShopifyClient
from agents.knowledge_retrieval.knowledge_base_client import KnowledgeBaseClient


class KnowledgeRetrievalAgent(BaseAgent):
    """
    Knowledge Retrieval Agent - Searches knowledge bases and external systems.

    Uses AGNTCY SDK MCP protocol for standardized tool interface.
    Integrates with:
    - Shopify API (product catalog, orders, inventory)
    - Zendesk API (previous tickets, customer history)
    - Internal documentation (FAQs, policies)
    - Azure OpenAI embeddings for semantic search (Phase 4+)
    """

    agent_name = "knowledge-retrieval-agent"
    default_topic = "knowledge-retrieval"

    def __init__(self):
        """Initialize the Knowledge Retrieval Agent."""
        super().__init__()

        # HTTP client for legacy Phase 1 mock API calls
        self.http_client = httpx.AsyncClient(timeout=10.0)

        # Phase 2: Initialize Shopify and Knowledge Base clients
        shopify_url = self.config.get("shopify_url", "http://localhost:8001")
        self.shopify_client = ShopifyClient(base_url=shopify_url, logger=self.logger)

        kb_path = Path(__file__).parent.parent.parent / "test-data" / "knowledge-base"
        self.kb_client = KnowledgeBaseClient(
            knowledge_base_path=kb_path, logger=self.logger
        )

        self.logger.info(
            f"Phase 2 clients initialized (Shopify: {shopify_url}, KB: {kb_path})"
        )

        # -------------------------------------------------------------------------
        # Phase 4+: Embedding Cache for Semantic Search
        # -------------------------------------------------------------------------
        # Purpose: Reduces Azure OpenAI API calls by caching embeddings
        #
        # Cache Key Strategy: First 200 characters of text
        # - Pros: Fast lookup, bounded memory, handles long documents
        # - Cons: POTENTIAL COLLISION RISK if two different texts share the
        #   same first 200 characters but differ later
        #
        # Collision Risk Assessment: LOW for production use case
        # - Customer queries are typically <100 characters
        # - Product descriptions rarely share 200-char prefixes
        # - Policy documents have unique headers
        #
        # Mitigation (if collisions occur):
        # 1. Use hash of full text as cache key: hashlib.sha256(text.encode()).hexdigest()
        # 2. Add text length to cache key: f"{text[:200]}|{len(text)}"
        # 3. Use LRU cache with full text comparison
        #
        # Monitoring: Track cache hit/miss ratio in Application Insights
        # If miss ratio suddenly increases, investigate potential collisions.
        #
        # See: _generate_embedding() method for cache implementation
        # -------------------------------------------------------------------------
        self._embedding_cache: Dict[str, List[float]] = {}

        # Additional counters for knowledge retrieval tracking
        self.semantic_searches = 0
        self.keyword_searches = 0

    async def process_message(self, content: dict, message: dict) -> dict:
        """
        Handle incoming knowledge query and search relevant sources.

        Args:
            content: Extracted message content
            message: Full A2A message

        Returns:
            KnowledgeResult as dict
        """
        # Parse as KnowledgeQuery
        query = KnowledgeQuery(
            query_id=content.get("query_id", generate_message_id()),
            context_id=message.get("contextId", "unknown"),
            query_text=content.get("query_text", ""),
            intent=Intent(content.get("intent", "general_inquiry")),
            filters=content.get("filters", {}),
            max_results=content.get("max_results", 5),
            language=Language(content.get("language", "en")),
        )

        self.logger.info(
            f"Processing knowledge query {query.query_id}: '{query.query_text}' "
            f"(intent: {query.intent.value})"
        )

        # Search knowledge sources based on intent
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
            confidence=self._calculate_confidence(results),
        )

        self.logger.info(
            f"Knowledge search complete: {len(results)} results in {search_time_ms:.2f}ms "
            f"(confidence: {result.confidence:.2f})"
        )

        return result

    def get_demo_messages(self) -> List[dict]:
        """Return sample messages for demo mode - Phase 2 coffee/brewing examples."""
        return [
            {
                "contextId": "demo-ctx-001",
                "taskId": "demo-task-001",
                "parts": [
                    {
                        "type": "text",
                        "content": {
                            "query_id": "q-001",
                            "query_text": "Where is my order?",
                            "intent": "order_status",
                            "filters": {"order_number": "10234"},
                            "max_results": 3,
                        },
                    }
                ],
            },
            {
                "contextId": "demo-ctx-002",
                "taskId": "demo-task-002",
                "parts": [
                    {
                        "type": "text",
                        "content": {
                            "query_id": "q-002",
                            "query_text": "espresso pods",
                            "intent": "product_info",
                            "max_results": 3,
                        },
                    }
                ],
            },
            {
                "contextId": "demo-ctx-003",
                "taskId": "demo-task-003",
                "parts": [
                    {
                        "type": "text",
                        "content": {
                            "query_id": "q-003",
                            "query_text": "brewer won't turn on",
                            "intent": "brewer_support",
                            "max_results": 2,
                        },
                    }
                ],
            },
        ]

    def cleanup(self) -> None:
        """Cleanup with additional search stats."""
        self.logger.info(
            f"Search stats - Semantic: {self.semantic_searches}, "
            f"Keyword: {self.keyword_searches}"
        )
        # Close HTTP clients
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._cleanup_async())
            except RuntimeError:
                self.logger.debug("No event loop running, skipping async cleanup")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        super().cleanup()

    async def _cleanup_async(self):
        """Async cleanup of HTTP clients."""
        try:
            await self.http_client.aclose()
            await self.shopify_client.close()
        except Exception as e:
            self.logger.error(f"Error closing HTTP clients: {e}")

    # ========================================================================
    # Knowledge Search Routing
    # ========================================================================

    async def _search_knowledge(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search knowledge sources based on intent and query.
        Phase 2: Coffee/brewing business specific routing.
        """
        results = []

        # Route to appropriate coffee-specific knowledge source based on intent
        intent_handlers = {
            Intent.ORDER_STATUS: self._search_order_status,
            Intent.ORDER_MODIFICATION: self._search_order_status,
            Intent.REFUND_STATUS: self._search_refund_status,
            Intent.PRODUCT_INFO: self._search_products,
            Intent.PRODUCT_RECOMMENDATION: self._search_product_recommendations,
            Intent.PRODUCT_COMPARISON: self._search_product_comparison,
            Intent.BREWER_SUPPORT: self._search_brewer_support,
            Intent.AUTO_DELIVERY_MANAGEMENT: self._search_subscription_info,
            Intent.RETURN_REQUEST: self._search_return_info,
            Intent.SHIPPING_QUESTION: self._search_shipping_info,
            Intent.GIFT_CARD: self._search_gift_card_info,
            Intent.LOYALTY_PROGRAM: self._search_loyalty_info,
        }

        handler = intent_handlers.get(query.intent)
        if handler:
            results.extend(await handler(query))
        else:
            # General inquiry - search all policies
            results.extend(await self._search_products(query))
            results.extend(self.kb_client.search_all_policies(query.query_text))

        return results[: query.max_results]

    # ========================================================================
    # Phase 2: Coffee-Specific Search Methods
    # ========================================================================

    async def _search_order_status(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Search order status - coffee/brewing specific."""
        results = []

        try:
            order_number = query.filters.get("order_number")
            customer_email = query.filters.get("customer_email")

            if order_number:
                order = await self.shopify_client.get_order_by_number(order_number)
                if order:
                    results.append(
                        {
                            "source": "shopify_order",
                            "type": "order",
                            "order_id": order.get("order_id"),
                            "order_number": order.get("order_number"),
                            "status": order.get("status"),
                            "fulfillment_status": order.get("fulfillment_status"),
                            "financial_status": order.get("financial_status"),
                            "items": order.get("items", []),
                            "tracking": order.get("tracking"),
                            "shipping_address": order.get("shipping_address"),
                            "total": order.get("total"),
                            "order_date": order.get("order_date"),
                            "relevance": 0.95,
                        }
                    )
                    self.logger.info(f"Found order {order_number}")

            elif customer_email:
                orders = await self.shopify_client.get_orders_by_customer_email(
                    customer_email
                )
                for order in orders[:3]:
                    results.append(
                        {
                            "source": "shopify_order_history",
                            "type": "order",
                            "order_id": order.get("order_id"),
                            "order_number": order.get("order_number"),
                            "status": order.get("status"),
                            "total": order.get("total"),
                            "order_date": order.get("order_date"),
                            "relevance": 0.80,
                        }
                    )
                self.logger.info(f"Found {len(orders)} orders for {customer_email}")

        except Exception as e:
            self.logger.error(f"Order status search failed: {e}", exc_info=True)

        return results

    async def _search_products(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Search coffee products (brewers, pods, accessories, gift cards)."""
        results = []

        try:
            # Extract product keywords from customer query
            search_query = query.query_text

            # Strip common question words/phrases
            question_words = [
                "how much is the",
                "how much is",
                "how much",
                "what is the price of the",
                "what is the price of",
                "price of the",
                "price of",
                "tell me about the",
                "tell me about",
                "is the",
                "is",
                "are the",
                "are",
                "do you have the",
                "do you have",
                "in stock",
                "available",
                "what's the",
                "whats the",
            ]

            search_query_lower = search_query.lower()
            for phrase in sorted(question_words, key=len, reverse=True):
                if search_query_lower.startswith(phrase):
                    search_query = search_query[len(phrase) :].strip()
                    search_query_lower = search_query.lower()
                    break

            search_query = search_query.rstrip("?!.,")

            # Remove filler words
            filler_words = ["your", "my", "the", "our", "about", "tell me"]
            search_words = search_query.split()
            search_words = [
                word for word in search_words if word.lower() not in filler_words
            ]
            search_query = " ".join(search_words)

            self.logger.debug(
                f"Product search: '{query.query_text}' → '{search_query}'"
            )

            products = await self.shopify_client.search_products(search_query, limit=5)

            for product in products:
                in_stock = product.get("in_stock", True)
                inventory_count = product.get("inventory_count")
                price = product.get("price")
                price_range = product.get("price_range")

                if price is None and price_range:
                    price = price_range.get("min")

                results.append(
                    {
                        "source": "shopify_product",
                        "type": "product",
                        "product_id": product.get("id"),
                        "sku": product.get("sku"),
                        "name": product.get("name"),
                        "description": product.get("description"),
                        "price": price,
                        "price_range": price_range,
                        "category": product.get("category"),
                        "features": product.get("features", []),
                        "tags": product.get("tags", []),
                        "in_stock": in_stock,
                        "inventory_count": inventory_count,
                        "variant_id": product.get("variant_id"),
                        "variant_name": product.get("variant_name"),
                        "relevance": 0.85,
                    }
                )

            self.logger.info(f"Product search: Found {len(results)} products")

        except Exception as e:
            self.logger.error(f"Product search failed: {e}", exc_info=True)

        return results

    async def _search_product_recommendations(
        self, query: KnowledgeQuery
    ) -> List[Dict[str, Any]]:
        """Recommend coffee products based on customer preferences."""
        results = []

        try:
            query_lower = query.query_text.lower()

            if any(
                word in query_lower for word in ["strong", "bold", "dark", "espresso"]
            ):
                search_term = "dark roast espresso"
            elif any(word in query_lower for word in ["light", "bright", "fruity"]):
                search_term = "light roast"
            elif any(word in query_lower for word in ["balanced", "smooth", "medium"]):
                search_term = "medium roast"
            elif any(word in query_lower for word in ["brewer", "machine"]):
                search_term = "brewer"
            elif any(word in query_lower for word in ["gift", "present"]):
                search_term = "variety pack"
            else:
                search_term = "signature blend"

            products = await self.shopify_client.search_products(search_term, limit=3)

            for product in products:
                results.append(
                    {
                        "source": "product_recommendation",
                        "type": "recommendation",
                        "product_id": product.get("id"),
                        "name": product.get("name"),
                        "price": product.get("price"),
                        "description": product.get("description"),
                        "why_recommended": f"Matches your preference for {search_term}",
                        "relevance": 0.85,
                    }
                )

            self.logger.info(f"Generated {len(results)} recommendations")

        except Exception as e:
            self.logger.error(f"Product recommendation failed: {e}", exc_info=True)

        return results

    async def _search_product_comparison(
        self, query: KnowledgeQuery
    ) -> List[Dict[str, Any]]:
        """Compare coffee products."""
        results = []

        try:
            query_lower = query.query_text.lower()

            if "brewer" in query_lower or "machine" in query_lower:
                products = await self.shopify_client.search_products("brewer", limit=3)
            elif "variety" in query_lower or "sampler" in query_lower:
                products = await self.shopify_client.search_products("variety", limit=3)
            else:
                products = await self.shopify_client.search_products(
                    "coffee pods", limit=3
                )

            for product in products:
                results.append(
                    {
                        "source": "product_comparison",
                        "type": "product",
                        "product_id": product.get("id"),
                        "name": product.get("name"),
                        "price": product.get("price"),
                        "features": product.get("features", []),
                        "category": product.get("category"),
                        "relevance": 0.80,
                    }
                )

            self.logger.info(f"Generated comparison for {len(results)} products")

        except Exception as e:
            self.logger.error(f"Product comparison failed: {e}", exc_info=True)

        return results

    async def _search_refund_status(
        self, query: KnowledgeQuery
    ) -> List[Dict[str, Any]]:
        """Search refund status and auto-approval rules."""
        results = []

        try:
            auto_approval_rules = self.kb_client.get_auto_approval_rules(
                "refund_status"
            )

            for rule in auto_approval_rules:
                results.append(
                    {
                        "source": "refund_policy",
                        "type": "business_rule",
                        "scenario": rule.get("scenario"),
                        "condition": rule.get("condition"),
                        "auto_approval": rule.get("auto_approval"),
                        "action": rule.get("action"),
                        "relevance": 0.90,
                    }
                )

            policy_results = self.kb_client.search_return_policy(query.query_text)
            results.extend(policy_results)

            self.logger.info(f"Found {len(results)} refund-related results")

        except Exception as e:
            self.logger.error(f"Refund status search failed: {e}", exc_info=True)

        return results

    async def _search_return_info(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Search return policy information and order data for return requests."""
        results = []

        try:
            order_number = query.filters.get("order_number")
            if order_number:
                self.logger.info(
                    f"Fetching order #{order_number} for return request validation"
                )
                order = await self.shopify_client.get_order_by_number(order_number)

                if order:
                    results.append(
                        {
                            "source": "shopify_order",
                            "type": "order",
                            "order_number": order.get("order_number"),
                            "order_id": order.get("order_id"),
                            "customer_email": order.get("customer_email"),
                            "customer_name": order.get("customer_name"),
                            "shipping_address": order.get("shipping_address"),
                            "total": order.get("total"),
                            "status": order.get("status"),
                            "items": order.get("items", []),
                            "order_date": order.get("created_at"),
                            "delivery_date": order.get("delivered_at"),
                            "return_eligible": order.get("status") == "delivered",
                            "relevance": 1.0,
                        }
                    )
                    self.logger.info(
                        f"Order #{order_number} found: ${order.get('total'):.2f}"
                    )
                else:
                    self.logger.warning(f"Order #{order_number} not found")
                    results.append(
                        {
                            "source": "shopify_order",
                            "type": "error",
                            "error_code": "ORDER_NOT_FOUND",
                            "error_message": f"Order #{order_number} not found.",
                            "order_number": order_number,
                            "relevance": 1.0,
                        }
                    )

            policy_results = self.kb_client.search_return_policy(query.query_text)
            results.extend(policy_results)

            self.logger.info(f"Found {len(results)} return-related results")

        except Exception as e:
            self.logger.error(f"Return info search failed: {e}", exc_info=True)

        return results

    async def _search_shipping_info(
        self, query: KnowledgeQuery
    ) -> List[Dict[str, Any]]:
        """Search shipping policy and carrier information."""
        try:
            results = self.kb_client.search_shipping_policy(query.query_text)
            self.logger.info(f"Found {len(results)} shipping policy results")
            return results
        except Exception as e:
            self.logger.error(f"Shipping info search failed: {e}", exc_info=True)
            return []

    async def _search_subscription_info(
        self, query: KnowledgeQuery
    ) -> List[Dict[str, Any]]:
        """Search auto-delivery subscription information."""
        results = []

        try:
            results.append(
                {
                    "source": "subscription_policy",
                    "type": "policy",
                    "title": "Auto-Delivery Subscription",
                    "content": "Free shipping on all auto-delivery orders. Manage frequency, skip deliveries, or cancel anytime.",
                    "benefits": [
                        "Never run out of your favorite coffee",
                        "Free shipping on every order",
                        "Flexible scheduling - change frequency anytime",
                        "Skip or pause deliveries as needed",
                        "Cancel anytime, no commitment",
                    ],
                    "relevance": 0.90,
                }
            )

            self.logger.info(f"Returned subscription policy info")

        except Exception as e:
            self.logger.error(f"Subscription info search failed: {e}", exc_info=True)

        return results

    async def _search_brewer_support(
        self, query: KnowledgeQuery
    ) -> List[Dict[str, Any]]:
        """Search brewer troubleshooting and support information."""
        results = []

        try:
            query_lower = query.query_text.lower()

            # Check if this is a product information query
            product_info_keywords = [
                "how much",
                "price",
                "cost",
                "buy",
                "purchase",
                "tell me about",
                "what is",
                "describe",
                "in stock",
                "available",
                "features",
            ]

            if any(keyword in query_lower for keyword in product_info_keywords):
                product_results = await self._search_products(query)
                if product_results:
                    self.logger.info(f"Brewer query identified as product info request")
                    return product_results

            # Troubleshooting queries
            if any(
                word in query_lower
                for word in ["won't turn on", "not working", "broken"]
            ):
                results.append(
                    {
                        "source": "brewer_support",
                        "type": "troubleshooting",
                        "issue": "Brewer won't turn on",
                        "solutions": [
                            "Check that power cord is firmly connected",
                            "Verify outlet is working (test with another device)",
                            "Try a different outlet",
                            "Check for tripped circuit breaker",
                        ],
                        "escalation_needed": True,
                        "relevance": 0.90,
                    }
                )

            elif any(
                word in query_lower for word in ["clean", "descale", "maintenance"]
            ):
                results.append(
                    {
                        "source": "brewer_support",
                        "type": "maintenance",
                        "title": "Brewer Cleaning & Maintenance",
                        "instructions": "Descale monthly using our 3-pack descaling solution.",
                        "product_recommendation": "ACC-DESC-3PK - Descaling Solution 3-pack ($14.99)",
                        "relevance": 0.85,
                    }
                )

            elif any(word in query_lower for word in ["weak", "taste", "flavor"]):
                results.append(
                    {
                        "source": "brewer_support",
                        "type": "troubleshooting",
                        "issue": "Coffee tastes weak or off",
                        "solutions": [
                            "Check brew strength settings (Medium or Bold)",
                            "Ensure you're using fresh pods",
                            "Run a descaling cycle if needed",
                            "Try a different coffee blend",
                        ],
                        "relevance": 0.85,
                    }
                )

            else:
                results.append(
                    {
                        "source": "brewer_support",
                        "type": "general",
                        "title": "Brewer Support Resources",
                        "content": "For brewer technical issues, please contact support. Warranty covers 2 years.",
                        "contact": "support@example.com or call 1-800-COFFEE",
                        "relevance": 0.70,
                    }
                )

            self.logger.info(f"Found {len(results)} brewer support results")

        except Exception as e:
            self.logger.error(f"Brewer support search failed: {e}", exc_info=True)

        return results

    async def _search_gift_card_info(
        self, query: KnowledgeQuery
    ) -> List[Dict[str, Any]]:
        """Search gift card information."""
        results = []

        try:
            query_lower = query.query_text.lower()

            product_info_keywords = [
                "how much",
                "price",
                "cost",
                "buy",
                "purchase",
                "available",
                "denominations",
                "amounts",
                "in stock",
            ]

            if any(keyword in query_lower for keyword in product_info_keywords):
                product_results = await self._search_products(query)
                if product_results:
                    self.logger.info(
                        f"Gift card query identified as product info request"
                    )
                    return product_results

            results.append(
                {
                    "source": "gift_card_policy",
                    "type": "policy",
                    "title": "Gift Cards",
                    "content": "Virtual and physical gift cards available in amounts from $25-$200. Never expire.",
                    "options": [
                        "Virtual Gift Card - Delivered via email instantly",
                        "Physical Gift Card - Mailed in gift packaging (2-5 business days)",
                    ],
                    "product_ids": ["PROD-060", "PROD-061"],
                    "relevance": 0.90,
                }
            )

            self.logger.info(f"Returned gift card policy info")

        except Exception as e:
            self.logger.error(f"Gift card info search failed: {e}", exc_info=True)

        return results

    async def _search_loyalty_info(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """Search loyalty program information and customer balance."""
        results = []

        try:
            customer_id = query.filters.get("customer_id")
            results = self.kb_client.search_loyalty_program(
                query.query_text, customer_id=customer_id
            )

            self.logger.info(f"Loyalty program search: {len(results)} results")

        except Exception as e:
            self.logger.error(f"Loyalty info search failed: {e}", exc_info=True)

        return results

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _calculate_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence score based on results."""
        if not results:
            return 0.0

        avg_relevance = sum(r.get("relevance", 0.5) for r in results) / len(results)
        unique_sources = len(set(r.get("source") for r in results))
        diversity_boost = min(unique_sources * 0.1, 0.3)

        return min(avg_relevance + diversity_boost, 1.0)

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using Azure OpenAI text-embedding-3-large.

        Caching Strategy:
        - Uses first 200 characters as cache key for performance
        - This is a tradeoff: O(1) lookup vs. potential collision risk
        - See __init__ for detailed collision risk assessment

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats (1536 dimensions for text-embedding-3-large)
            or None if embedding generation fails
        """
        if not self.openai_client:
            return None

        # Cache key: first 200 chars (see __init__ for collision risk discussion)
        # If collisions become an issue, change to: hashlib.sha256(text.encode()).hexdigest()
        cache_key = text[:200]
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        try:
            embeddings = await self.openai_client.generate_embeddings([text])
            if embeddings:
                self._embedding_cache[cache_key] = embeddings[0]
                return embeddings[0]
        except Exception as e:
            self.logger.warning(f"Embedding generation failed: {e}")

        return None

    def _calculate_cosine_similarity(
        self, vec1: List[float], vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def _semantic_search_knowledge_base(
        self, query_text: str, documents: List[Dict[str, Any]], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform semantic search over documents using embeddings."""
        if not self.openai_client:
            self.keyword_searches += 1
            return documents[:top_k]

        try:
            self.semantic_searches += 1

            query_embedding = await self._generate_embedding(query_text)
            if not query_embedding:
                return documents[:top_k]

            scored_docs = []
            for doc in documents:
                doc_text = (
                    doc.get("content", "") or doc.get("description", "") or str(doc)
                )
                doc_embedding = await self._generate_embedding(doc_text[:1000])

                if doc_embedding:
                    similarity = self._calculate_cosine_similarity(
                        query_embedding, doc_embedding
                    )
                    doc["relevance"] = similarity
                    scored_docs.append((similarity, doc))
                else:
                    scored_docs.append((0.5, doc))

            scored_docs.sort(key=lambda x: x[0], reverse=True)
            return [doc for _, doc in scored_docs[:top_k]]

        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return documents[:top_k]


if __name__ == "__main__":
    run_agent(KnowledgeRetrievalAgent)
