"""
Knowledge Retrieval Agent
Searches internal knowledge bases, product catalogs, and documentation

Phase 1: Mock API calls to Shopify, Zendesk, internal docs
Phase 2: Coffee/brewing business specific with real Shopify integration
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

# Import Phase 2 clients
from agents.knowledge_retrieval.shopify_client import ShopifyClient
from agents.knowledge_retrieval.knowledge_base_client import KnowledgeBaseClient


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

        # HTTP client for mock API calls (legacy, Phase 1)
        self.http_client = httpx.AsyncClient(timeout=10.0)

        # Phase 2: Initialize Shopify and Knowledge Base clients
        shopify_url = self.config.get("shopify_url", "http://localhost:8001")
        self.shopify_client = ShopifyClient(base_url=shopify_url, logger=self.logger)

        kb_path = Path(__file__).parent.parent.parent / "test-data" / "knowledge-base"
        self.kb_client = KnowledgeBaseClient(knowledge_base_path=kb_path, logger=self.logger)

        self.logger.info(f"Phase 2 clients initialized (Shopify: {shopify_url}, KB: {kb_path})")

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
        Phase 2: Coffee/brewing business specific routing.

        Args:
            query: Knowledge query with intent and filters

        Returns:
            List of search results
        """
        results = []

        # Route to appropriate coffee-specific knowledge source based on intent
        if query.intent == Intent.ORDER_STATUS:
            results.extend(await self._search_order_status(query))

        elif query.intent == Intent.ORDER_MODIFICATION:
            results.extend(await self._search_order_status(query))

        elif query.intent == Intent.REFUND_STATUS:
            results.extend(await self._search_refund_status(query))

        elif query.intent == Intent.PRODUCT_INFO:
            results.extend(await self._search_products(query))

        elif query.intent == Intent.PRODUCT_RECOMMENDATION:
            results.extend(await self._search_product_recommendations(query))

        elif query.intent == Intent.PRODUCT_COMPARISON:
            results.extend(await self._search_product_comparison(query))

        elif query.intent == Intent.BREWER_SUPPORT:
            results.extend(await self._search_brewer_support(query))

        elif query.intent == Intent.AUTO_DELIVERY_MANAGEMENT:
            results.extend(await self._search_subscription_info(query))

        elif query.intent == Intent.RETURN_REQUEST:
            results.extend(await self._search_return_info(query))

        elif query.intent == Intent.SHIPPING_QUESTION:
            results.extend(await self._search_shipping_info(query))

        elif query.intent == Intent.GIFT_CARD:
            results.extend(await self._search_gift_card_info(query))

        elif query.intent == Intent.LOYALTY_PROGRAM:
            results.extend(await self._search_loyalty_info(query))

        else:
            # General inquiry - search all policies
            results.extend(await self._search_products(query))
            results.extend(self.kb_client.search_all_policies(query.query_text))

        # Limit results
        return results[:query.max_results]

    # ========================================================================
    # Phase 2: Coffee-Specific Search Methods
    # ========================================================================

    async def _search_order_status(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search order status - coffee/brewing specific.
        Supports order number lookup and customer email history.
        """
        results = []

        try:
            # Check if order number is provided in filters or entities
            order_number = query.filters.get("order_number")
            customer_email = query.filters.get("customer_email")

            if order_number:
                # Lookup specific order
                order = await self.shopify_client.get_order_by_number(order_number)
                if order:
                    results.append({
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
                        "relevance": 0.95
                    })
                    self.logger.info(f"Found order {order_number}")

            elif customer_email:
                # Get customer order history
                orders = await self.shopify_client.get_orders_by_customer_email(customer_email)
                for order in orders[:3]:  # Limit to 3 recent orders
                    results.append({
                        "source": "shopify_order_history",
                        "type": "order",
                        "order_id": order.get("order_id"),
                        "order_number": order.get("order_number"),
                        "status": order.get("status"),
                        "total": order.get("total"),
                        "order_date": order.get("order_date"),
                        "relevance": 0.80
                    })
                self.logger.info(f"Found {len(orders)} orders for {customer_email}")

        except Exception as e:
            self.logger.error(f"Order status search failed: {e}", exc_info=True)

        return results

    async def _search_products(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search coffee products (brewers, pods, accessories, gift cards).

        Issue #25: Customer Product Information Inquiries
        ---------------------------------------------------
        This method enables customers to:
        - Find products by name/keyword ("coffee brewer", "organic soap", "gift card")
        - Check product availability and stock status
        - Learn about product features, prices, and specifications
        - Discover products in specific categories (brewers, coffee pods, accessories)

        Workflow:
        1. Extract product keywords from customer query (strip question words)
        2. Call Shopify API to search products by title/keyword
        3. Transform raw Shopify data into Knowledge Result format
        4. Include stock availability for each product
        5. Return results to Response Generation Agent for customer-facing message

        Args:
            query: KnowledgeQuery with customer's product search text
                Examples: "Is organic mango soap in stock?", "coffee maker price",
                         "espresso pods", "gift card"

        Returns:
            List of product result dictionaries with structure:
            {
                "source": "shopify_product",
                "type": "product",
                "product_id": "PROD-001",
                "sku": "BRWR-PREM-BLK",
                "name": "Premium Single-Serve Coffee Brewer",
                "description": "Our flagship single-serve coffee brewer...",
                "price": 398.00,
                "category": "brewers",
                "features": ["7 customizable brew parameters", ...],
                "tags": ["brewer", "premium", "coffee-maker"],
                "in_stock": true,
                "inventory_count": 47,
                "variant_id": "VAR-001-BLK",
                "variant_name": "Black",
                "relevance": 0.85
            }

        Integration with Other Agents:
        - Intent Classification Agent: Extracts product name/keyword from customer query
        - Response Generation Agent: Creates customer-friendly product information message
        - No escalation needed: Product info is fully automated (no approval threshold)

        Performance Target:
        - <200ms P95 latency (Issue #25 acceptance criteria)
        - Typically <50ms in Phase 1-3 (local mock API)

        Reference: ISSUE-25-IMPLEMENTATION-PLAN.md lines 82-101
        """
        results = []

        try:
            # Issue #25: Extract product keywords from customer query
            # Phase 2: Simple keyword extraction (strip common question words)
            # Phase 4-5: Will use NLP/embeddings for better keyword extraction
            #
            # Example transformations:
            # "How much is the Premium Coffee Brewer?" → "Premium Coffee Brewer"
            # "Tell me about espresso pods" → "espresso pods"
            # "Is organic mango soap in stock?" → "organic mango soap"
            search_query = query.query_text

            # Strip common question words/phrases (Phase 2 simple approach)
            question_words = [
                "how much is the", "how much is", "how much",
                "what is the price of the", "what is the price of", "price of the", "price of",
                "tell me about the", "tell me about",
                "is the", "is", "are the", "are",
                "do you have the", "do you have",
                "in stock", "available",
                "what's the", "whats the"
            ]

            search_query_lower = search_query.lower()
            for phrase in sorted(question_words, key=len, reverse=True):  # Longest first
                if search_query_lower.startswith(phrase):
                    # Remove question phrase from start
                    search_query = search_query[len(phrase):].strip()
                    search_query_lower = search_query.lower()
                    break

            # Remove trailing question marks and punctuation
            search_query = search_query.rstrip('?!.,')

            # Issue #25 Fix: Remove filler words that don't help search
            # Example: "Tell me about your coffee pods" → "coffee pods"
            # These words add noise and reduce search accuracy
            filler_words = ['your', 'my', 'the', 'our', 'about', 'tell me']
            search_words = search_query.split()
            search_words = [word for word in search_words if word.lower() not in filler_words]
            search_query = ' '.join(search_words)

            self.logger.debug(
                f"Product search keyword extraction: "
                f"'{query.query_text}' → '{search_query}'"
            )

            # Call Shopify API to search products by keyword/title
            # Issue #25: Server-side filtering via title parameter (more efficient)
            # Limit to 5 results to keep response concise for customers
            # Reference: shopify_client.py lines 234-320 (search_products method)
            products = await self.shopify_client.search_products(search_query, limit=5)

            # Transform each Shopify product into Knowledge Result format
            # This format is consumed by Response Generation Agent for customer messages
            for product in products:
                # Stock availability check
                # in_stock: Boolean flag (true/false)
                # inventory_count: Actual quantity available (may be None for unlimited/digital)
                in_stock = product.get("in_stock", True)
                inventory_count = product.get("inventory_count")

                # Issue #25 Fix: Handle gift cards with price_range instead of fixed price
                # Gift cards have {"price": null, "price_range": {"min": 25, "max": 200}}
                # For customer response, show price range or use minimum price
                price = product.get("price")
                price_range = product.get("price_range")

                # If price is null but price_range exists (gift cards), use min price for sorting
                # Response Generation Agent will format appropriately
                if price is None and price_range:
                    price = price_range.get("min")  # Use minimum for consistency

                # Build product result dictionary
                # Include all relevant fields for Response Generation Agent
                results.append({
                    "source": "shopify_product",
                    "type": "product",
                    "product_id": product.get("id"),
                    "sku": product.get("sku"),
                    "name": product.get("name"),
                    "description": product.get("description"),
                    "price": price,  # Fixed price or minimum from range
                    "price_range": price_range,  # Include original range if exists
                    "category": product.get("category"),
                    "features": product.get("features", []),
                    "tags": product.get("tags", []),
                    "in_stock": in_stock,
                    "inventory_count": inventory_count,
                    "variant_id": product.get("variant_id"),
                    "variant_name": product.get("variant_name"),
                    "relevance": 0.85  # High relevance (server-side filtered by title)
                })

            self.logger.info(
                f"Product search complete: Found {len(results)} products matching "
                f"'{query.query_text}' (in_stock: {sum(1 for r in results if r['in_stock'])})"
            )

        except Exception as e:
            # Graceful error handling: Log error but don't crash
            # Return empty results to allow Response Generator to inform customer
            # Example response: "I'm having trouble accessing product info, please try again"
            self.logger.error(
                f"Product search failed for query '{query.query_text}': {e}",
                exc_info=True
            )

        return results

    async def _search_product_recommendations(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Recommend coffee products based on customer preferences.
        """
        results = []

        try:
            query_lower = query.query_text.lower()

            # Detect preference keywords
            if any(word in query_lower for word in ["strong", "bold", "dark", "espresso"]):
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
                results.append({
                    "source": "product_recommendation",
                    "type": "recommendation",
                    "product_id": product.get("id"),
                    "name": product.get("name"),
                    "price": product.get("price"),
                    "description": product.get("description"),
                    "why_recommended": f"Matches your preference for {search_term}",
                    "relevance": 0.85
                })

            self.logger.info(f"Generated {len(results)} recommendations")

        except Exception as e:
            self.logger.error(f"Product recommendation failed: {e}", exc_info=True)

        return results

    async def _search_product_comparison(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Compare coffee products (e.g., different brewers or coffee blends).
        """
        results = []

        try:
            # Extract comparison keywords
            query_lower = query.query_text.lower()

            if "brewer" in query_lower or "machine" in query_lower:
                products = await self.shopify_client.search_products("brewer", limit=3)
            elif "variety" in query_lower or "sampler" in query_lower:
                products = await self.shopify_client.search_products("variety", limit=3)
            else:
                # Generic coffee pods comparison
                products = await self.shopify_client.search_products("coffee pods", limit=3)

            for product in products:
                results.append({
                    "source": "product_comparison",
                    "type": "product",
                    "product_id": product.get("id"),
                    "name": product.get("name"),
                    "price": product.get("price"),
                    "features": product.get("features", []),
                    "category": product.get("category"),
                    "relevance": 0.80
                })

            self.logger.info(f"Generated comparison for {len(results)} products")

        except Exception as e:
            self.logger.error(f"Product comparison failed: {e}", exc_info=True)

        return results

    async def _search_refund_status(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search refund status and auto-approval rules.
        """
        results = []

        try:
            # Get auto-approval rules from knowledge base
            auto_approval_rules = self.kb_client.get_auto_approval_rules("refund_status")

            for rule in auto_approval_rules:
                results.append({
                    "source": "refund_policy",
                    "type": "business_rule",
                    "scenario": rule.get("scenario"),
                    "condition": rule.get("condition"),
                    "auto_approval": rule.get("auto_approval"),
                    "action": rule.get("action"),
                    "relevance": 0.90
                })

            # Also search return policy for refund info
            policy_results = self.kb_client.search_return_policy(query.query_text)
            results.extend(policy_results)

            self.logger.info(f"Found {len(results)} refund-related results")

        except Exception as e:
            self.logger.error(f"Refund status search failed: {e}", exc_info=True)

        return results

    async def _search_return_info(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search return policy information and order data for return requests.

        Issue #29: Return/Refund Request Handling
        ------------------------------------------
        For return requests, we need BOTH order data and return policy:
        1. Order data: Validates return eligibility, applies $50 auto-approval threshold
        2. Return policy: Provides return window, conditions, process instructions

        Auto-Approval Business Logic:
        - Orders ≤$50.00: Auto-approved with RMA number (instant customer satisfaction)
        - Orders >$50.00: Escalated to support team (risk mitigation for high-value returns)

        Reference: ISSUE-29-IMPLEMENTATION-PLAN.md lines 36-48
        Reference: test-data/knowledge-base/return-policy.md (30-day return window)

        Args:
            query: Knowledge query with intent=RETURN_REQUEST and optional filters

        Returns:
            List of results containing:
            - Order data (if order_number provided) with type="order"
            - Return policy sections with type="policy"
        """
        results = []

        try:
            # STEP 1: Fetch order data if order number provided (Issue #29 requirement)
            # Rationale: Need order total for $50 auto-approval threshold logic
            order_number = query.filters.get("order_number")
            if order_number:
                self.logger.info(f"Fetching order #{order_number} for return request validation")
                order = await self.shopify_client.get_order_by_number(order_number)

                if order:
                    # Return eligibility validation (Phase 2 enhancement)
                    # Reference: return-policy.md - 30-day window, delivered status required
                    results.append({
                        "source": "shopify_order",
                        "type": "order",  # CRITICAL: Test expects type="order"
                        "order_number": order.get("order_number"),
                        "order_id": order.get("order_id"),
                        "customer_email": order.get("customer_email"),
                        "customer_name": order.get("customer_name"),  # For personalized responses
                        "shipping_address": order.get("shipping_address"),  # For address validation
                        "total": order.get("total"),
                        "status": order.get("status"),
                        "items": order.get("items", []),
                        "order_date": order.get("created_at"),
                        "delivery_date": order.get("delivered_at"),
                        "return_eligible": order.get("status") == "delivered",  # Simplified check
                        "relevance": 1.0
                    })
                    self.logger.info(f"Order #{order_number} found: ${order.get('total'):.2f}, status={order.get('status')}")
                else:
                    # Order not found - return error result for graceful handling
                    self.logger.warning(f"Order #{order_number} not found in Shopify")
                    results.append({
                        "source": "shopify_order",
                        "type": "error",
                        "error_code": "ORDER_NOT_FOUND",
                        "error_message": f"Order #{order_number} not found. Please verify your order number.",
                        "order_number": order_number,
                        "relevance": 1.0
                    })

            # STEP 2: Fetch return policy from knowledge base (always include for context)
            # Reference: Knowledge Base Client search_return_policy() method
            policy_results = self.kb_client.search_return_policy(query.query_text)
            results.extend(policy_results)

            self.logger.info(f"Found {len(results)} return-related results (order + policy)")

        except Exception as e:
            self.logger.error(f"Return info search failed: {e}", exc_info=True)

        return results

    async def _search_shipping_info(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search shipping policy and carrier information.
        """
        try:
            results = self.kb_client.search_shipping_policy(query.query_text)
            self.logger.info(f"Found {len(results)} shipping policy results")
            return results
        except Exception as e:
            self.logger.error(f"Shipping info search failed: {e}", exc_info=True)
            return []

    async def _search_subscription_info(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search auto-delivery subscription information.
        """
        results = []

        try:
            # Return subscription policy info
            results.append({
                "source": "subscription_policy",
                "type": "policy",
                "title": "Auto-Delivery Subscription",
                "content": "Free shipping on all auto-delivery orders. Manage frequency, skip deliveries, or cancel anytime.",
                "benefits": [
                    "Never run out of your favorite coffee",
                    "Free shipping on every order",
                    "Flexible scheduling - change frequency anytime",
                    "Skip or pause deliveries as needed",
                    "Cancel anytime, no commitment"
                ],
                "relevance": 0.90
            })

            self.logger.info(f"Returned subscription policy info")

        except Exception as e:
            self.logger.error(f"Subscription info search failed: {e}", exc_info=True)

        return results

    async def _search_brewer_support(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search brewer troubleshooting and support information.

        Issue #25: Enhanced to support product information queries
        ------------------------------------------------------------
        Queries like "How much is the coffee brewer?" or "Tell me about the brewer"
        should return product information (price, features, stock) FIRST,
        then optionally include support resources.
        """
        results = []

        try:
            query_lower = query.query_text.lower()

            # Issue #25: Check if this is a PRODUCT INFORMATION query
            # Keywords indicating customer wants product details, not troubleshooting
            product_info_keywords = [
                "how much", "price", "cost", "buy", "purchase", "tell me about",
                "what is", "describe", "in stock", "available", "features"
            ]

            is_product_info_query = any(keyword in query_lower for keyword in product_info_keywords)

            if is_product_info_query:
                # Issue #25: Search products FIRST for product information queries
                # Example: "How much is the Premium Coffee Brewer?" → return product with price
                product_results = await self._search_products(query)
                results.extend(product_results)

                # If products found, return them (no need for support articles)
                if product_results:
                    self.logger.info(
                        f"Brewer support query identified as product info request, "
                        f"returned {len(product_results)} products"
                    )
                    return results

            # TROUBLESHOOTING QUERIES (not product information)
            # Common brewer issues
            if any(word in query_lower for word in ["won't turn on", "not working", "broken"]):
                results.append({
                    "source": "brewer_support",
                    "type": "troubleshooting",
                    "issue": "Brewer won't turn on",
                    "solutions": [
                        "Check that power cord is firmly connected",
                        "Verify outlet is working (test with another device)",
                        "Try a different outlet",
                        "Check for tripped circuit breaker"
                    ],
                    "escalation_needed": True,
                    "relevance": 0.90
                })

            elif any(word in query_lower for word in ["clean", "descale", "maintenance"]):
                results.append({
                    "source": "brewer_support",
                    "type": "maintenance",
                    "title": "Brewer Cleaning & Maintenance",
                    "instructions": "Descale monthly using our 3-pack descaling solution. Run 2 descaling cycles followed by 3 rinse cycles.",
                    "product_recommendation": "ACC-DESC-3PK - Descaling Solution 3-pack ($14.99)",
                    "relevance": 0.85
                })

            elif any(word in query_lower for word in ["weak", "taste", "flavor"]):
                results.append({
                    "source": "brewer_support",
                    "type": "troubleshooting",
                    "issue": "Coffee tastes weak or off",
                    "solutions": [
                        "Check brew strength settings (Medium or Bold)",
                        "Ensure you're using fresh Bruvi pods",
                        "Run a descaling cycle if hasn't been done in 30+ days",
                        "Try a different coffee blend"
                    ],
                    "relevance": 0.85
                })

            else:
                # General brewer support
                results.append({
                    "source": "brewer_support",
                    "type": "general",
                    "title": "Brewer Support Resources",
                    "content": "For brewer technical issues, please contact support. Warranty covers 2 years from purchase.",
                    "contact": "support@example.com or call 1-800-COFFEE",
                    "relevance": 0.70
                })

            self.logger.info(f"Found {len(results)} brewer support results")

        except Exception as e:
            self.logger.error(f"Brewer support search failed: {e}", exc_info=True)

        return results

    async def _search_gift_card_info(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search gift card information.

        Issue #25: Enhanced to support product information queries
        ------------------------------------------------------------
        Queries like "How much is the gift card?" should return actual gift card
        products from catalog (price, denominations), not just policy info.
        """
        results = []

        try:
            query_lower = query.query_text.lower()

            # Issue #25: Check if this is a PRODUCT INFORMATION query
            product_info_keywords = [
                "how much", "price", "cost", "buy", "purchase", "available",
                "denominations", "amounts", "in stock"
            ]

            is_product_info_query = any(keyword in query_lower for keyword in product_info_keywords)

            if is_product_info_query:
                # Issue #25: Search gift card products FIRST
                # Example: "How much is the gift card?" → return gift card products with prices
                product_results = await self._search_products(query)
                results.extend(product_results)

                # If products found, return them (customer wants to know prices/options)
                if product_results:
                    self.logger.info(
                        f"Gift card query identified as product info request, "
                        f"returned {len(product_results)} products"
                    )
                    return results

            # POLICY INFORMATION (not product purchasing)
            # Example: "Do gift cards expire?" "Can I use a gift card online?"
            results.append({
                "source": "gift_card_policy",
                "type": "policy",
                "title": "Gift Cards",
                "content": "Virtual and physical gift cards available in amounts from $25-$200. Never expire.",
                "options": [
                    "Virtual Gift Card - Delivered via email instantly",
                    "Physical Gift Card - Mailed in gift packaging (2-5 business days)"
                ],
                "product_ids": ["PROD-060", "PROD-061"],
                "relevance": 0.90
            })

            self.logger.info(f"Returned gift card policy info")

        except Exception as e:
            self.logger.error(f"Gift card info search failed: {e}", exc_info=True)

        return results

    async def _search_loyalty_info(self, query: KnowledgeQuery) -> List[Dict[str, Any]]:
        """
        Search loyalty program information and customer balance.

        Issue #34: Customer Loyalty Program Inquiry
        --------------------------------------------
        Handles customer queries about:
        - Points balance: "How many points do I have?"
        - Redemption options: "How do I use my rewards?"
        - Earning rates: "How do I earn points?"
        - Tier status: "What tier am I in?"
        - Point expiration: "Do my points expire?"

        Provides personalized balance info when customer_id is available.

        Args:
            query: Knowledge query with intent=LOYALTY_PROGRAM and optional filters

        Returns:
            List of results containing:
            - Customer balance (if customer_id provided) with type="customer_balance"
            - Loyalty program sections with type="policy"
            - Redemption tiers with type="redemption_tiers"
            - Membership tiers with type="membership_tiers"
        """
        results = []

        try:
            # Extract customer_id from filters for personalized balance
            customer_id = query.filters.get("customer_id")

            # Search loyalty program knowledge base
            # This includes customer balance (if customer_id provided) and program sections
            results = self.kb_client.search_loyalty_program(
                query.query_text,
                customer_id=customer_id
            )

            self.logger.info(
                f"Loyalty program search complete: {len(results)} results "
                f"(customer_id: {customer_id})"
            )

        except Exception as e:
            self.logger.error(f"Loyalty info search failed: {e}", exc_info=True)

        return results


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

    async def cleanup_async(self):
        """Async cleanup of HTTP clients."""
        try:
            await self.http_client.aclose()
            await self.shopify_client.close()
        except Exception as e:
            self.logger.error(f"Error closing HTTP clients: {e}")

    def cleanup(self):
        """Cleanup resources on shutdown."""
        self.logger.info("Cleaning up Knowledge Retrieval Agent...")

        # Close HTTP clients synchronously
        try:
            # Try to get running event loop and close clients
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.cleanup_async())
            except RuntimeError:
                # No event loop running - close synchronously (best effort)
                self.logger.debug("No event loop running, skipping async cleanup")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

        if self.container:
            try:
                self.container.stop()
            except Exception as e:
                self.logger.error(f"Error stopping container: {e}")

        shutdown_factory()
        self.logger.info("Cleanup complete")

    async def run_demo_mode(self):
        """Run in demo mode without SDK - Phase 2 coffee/brewing examples."""
        self.logger.info("Running in DEMO MODE (no SDK connection)")
        self.logger.info("Simulating coffee/brewing knowledge retrieval...")

        # Demo: Process coffee-specific sample queries
        sample_queries = [
            {
                "contextId": "demo-ctx-001",
                "taskId": "demo-task-001",
                "parts": [{
                    "type": "text",
                    "content": {
                        "query_id": "q-001",
                        "query_text": "Where is my order?",
                        "intent": "order_status",
                        "filters": {"order_number": "10234"},
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
                        "query_text": "espresso pods",
                        "intent": "product_info",
                        "max_results": 3
                    }
                }]
            },
            {
                "contextId": "demo-ctx-003",
                "taskId": "demo-task-003",
                "parts": [{
                    "type": "text",
                    "content": {
                        "query_id": "q-003",
                        "query_text": "brewer won't turn on",
                        "intent": "brewer_support",
                        "max_results": 2
                    }
                }]
            }
        ]

        for msg in sample_queries:
            self.logger.info("=" * 60)
            result = await self.handle_message(msg)
            content = extract_message_content(result)
            self.logger.info(f"Demo Result: Found {content.get('total_results', 0)} results in {content.get('search_time_ms', 0):.2f}ms")
            if content.get("results"):
                for idx, r in enumerate(content["results"][:2], 1):
                    result_name = r.get('name', r.get('title', r.get('order_id', 'N/A')))
                    self.logger.info(f"  {idx}. [{r.get('source')}] {result_name}")
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
