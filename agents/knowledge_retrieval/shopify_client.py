"""
Shopify API Client for Knowledge Retrieval Agent

This module provides an async HTTP client for interacting with the Shopify REST Admin API
(Phase 1-3: mock implementation, Phase 4-5: real Shopify integration).

Educational Project: Multi-Agent AI Customer Service Platform
Phase: 2 - Business Logic Implementation
Purpose: Order management and product catalog integration

API Reference: Shopify REST Admin API
- Documentation: https://shopify.dev/docs/api/admin-rest
- Order Resource: https://shopify.dev/docs/api/admin-rest/resources/order
- Product Resource: https://shopify.dev/docs/api/admin-rest/resources/product
- API Versioning: https://shopify.dev/docs/api/admin-rest/api-versioning

Mock API Implementation: Phase 1-3 (Local Development)
- Endpoint: http://localhost:8001 (Docker Compose)
- Reference: mocks/shopify/api.py
- Test Data: test-data/shopify/orders.json, products.json

Production API: Phase 4-5 (Azure Deployment)
- Endpoint: https://{shop}.myshopify.com/admin/api/{version}
- Authentication: Admin API access token (stored in Azure Key Vault)
- Rate Limits: 2 req/sec standard, 4 req/sec Plus (Shopify API limits)
- Reference: https://shopify.dev/docs/api/admin-rest/rate-limits

HTTP Client Library: httpx
- Documentation: https://www.python-httpx.org/
- Advantages: Async/await support, HTTP/2, connection pooling, timeout handling
- Alternative: aiohttp (similar capabilities)

Design Patterns:
- Client Pattern: Encapsulates API communication logic
- Dependency Injection: Logger injected for testability
- Async/Await: Non-blocking I/O for concurrent requests

Author: Claude Sonnet 4.5 (AI Assistant)
License: MIT (Educational Use)
"""

import httpx
import json
from typing import List, Dict, Any, Optional
from pathlib import Path


class ShopifyClient:
    """
    Async HTTP client for Shopify REST Admin API interactions.

    This client handles all communication with Shopify's order and product APIs,
    providing a clean abstraction layer for the Knowledge Retrieval Agent.

    Responsibilities:
    - Fetch order details by order number
    - Query customer order history by email
    - Search product catalog by keywords
    - Retrieve individual product details
    - Handle API errors gracefully (no crashes)

    Performance Considerations:
    - Connection pooling via httpx.AsyncClient (reuses TCP connections)
    - 10-second timeout to prevent hanging requests
    - Async operations allow concurrent API calls without blocking

    Error Handling Philosophy:
    - Log all errors with exc_info=True for debugging
    - Return None or empty list on failure (graceful degradation)
    - Never raise exceptions to calling code (resilient design)
    """

    def __init__(self, base_url: str, logger):
        """
        Initialize Shopify API client with base URL and logger.

        Args:
            base_url: Shopify API base URL
                Phase 1-3: http://localhost:8001 (mock API)
                Phase 4-5: https://{shop}.myshopify.com/admin/api/2024-01
            logger: Python logging.Logger instance for structured logging

        Design Notes:
        - HTTP client created once and reused (connection pooling)
        - 10-second timeout prevents indefinite hangs
        - Base URL normalized (trailing slash removed for consistency)

        Reference: httpx AsyncClient - https://www.python-httpx.org/async/
        """
        self.base_url = base_url.rstrip('/')
        self.logger = logger

        # Create async HTTP client with connection pooling and timeout
        # Connection pooling: Reuses TCP connections for better performance
        # Timeout: 10 seconds prevents hanging on slow/dead endpoints
        # Reference: https://www.python-httpx.org/advanced/#timeout-configuration
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def get_order_by_number(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete order details by order number from Shopify.

        This is the primary method for Issue #24 (Customer Order Status Inquiries).
        It fetches order status, tracking information, items, and customer details.

        API Endpoint: GET /admin/api/{version}/orders/{order_number}.json
        Reference: https://shopify.dev/docs/api/admin-rest/resources/order#get-orders-order-id

        Args:
            order_number: Order number to retrieve
                Formats supported: "10234", "#10234", "ORD-10234"
                The Intent Classification Agent normalizes these to numeric form

        Returns:
            Dictionary with order details or None if not found
            Order structure (per test-data/shopify/orders.json):
            {
                "order_id": "ORD-10234",
                "order_number": "10234",
                "customer_id": "persona_001",
                "customer_email": "sarah.martinez@email.com",
                "status": "shipped|delivered|pending|cancelled",
                "fulfillment_status": "in_transit|fulfilled|pending",
                "items": [{"name": "...", "quantity": 2, "price": 24.99}],
                "tracking": {
                    "carrier": "USPS",
                    "tracking_number": "9400123456789",
                    "expected_delivery": "2026-01-25T20:00:00Z",
                    "last_location": "Portland Distribution Center"
                },
                "shipping_address": {...},
                "total": 86.37
            }

        Error Handling:
        - 200 OK: Returns order data
        - 404 Not Found: Returns None (order doesn't exist)
        - Other errors: Logs error, returns None (graceful degradation)
        - Network timeouts: Caught by httpx timeout (10s), returns None

        Performance:
        - Target latency: <500ms (P95) per WIKI-Architecture.md
        - Actual latency: Typically <100ms for mock API (local Docker)
        - Production latency: 200-500ms (Shopify API over internet)
        """
        try:
            # Construct Shopify REST Admin API URL
            # API Version: 2024-01 (Shopify recommends using stable versions)
            # Reference: https://shopify.dev/docs/api/admin-rest/api-versioning
            url = f"{self.base_url}/admin/api/2024-01/orders/{order_number}.json"
            self.logger.debug(f"Fetching order from Shopify: {url}")

            # Make async HTTP GET request
            # This is non-blocking - allows other agents to process concurrently
            # Reference: Python asyncio - https://docs.python.org/3/library/asyncio-task.html
            response = await self.http_client.get(url)

            if response.status_code == 200:
                # Success: Parse JSON response body
                # Shopify wraps order in {"order": {...}} structure
                data = response.json()
                order = data.get("order")

                self.logger.info(
                    f"Order {order_number} retrieved successfully "
                    f"(status: {order.get('status')}, total: ${order.get('total')})"
                )
                return order

            elif response.status_code == 404:
                # Order not found - this is expected behavior for invalid order numbers
                # Return None to allow Response Generator to handle gracefully
                self.logger.warning(f"Order {order_number} not found in Shopify")
                return None

            else:
                # Unexpected API error (5xx server errors, 401 auth errors, etc.)
                # Log for debugging but don't crash - return None for graceful degradation
                self.logger.error(
                    f"Shopify API error fetching order {order_number}: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                return None

        except httpx.TimeoutException:
            # Network timeout (>10 seconds)
            # This might indicate Shopify API downtime or network issues
            self.logger.error(
                f"Timeout fetching order {order_number} from Shopify (>10s). "
                "Check API availability and network connectivity."
            )
            return None

        except httpx.HTTPError as e:
            # Other HTTP errors (connection refused, DNS resolution failure, etc.)
            self.logger.error(f"HTTP error fetching order {order_number}: {e}", exc_info=True)
            return None

        except Exception as e:
            # Catch-all for unexpected errors (JSON parsing, etc.)
            # exc_info=True provides full stack trace for debugging
            self.logger.error(f"Unexpected error fetching order {order_number}: {e}", exc_info=True)
            return None

    async def get_orders_by_customer_email(self, email: str) -> List[Dict[str, Any]]:
        """
        Retrieve orders for a customer by email.

        Args:
            email: Customer email address

        Returns:
            List of order dicts
        """
        try:
            url = f"{self.base_url}/admin/api/2024-01/orders.json"
            params = {"customer_email": email, "limit": 10}

            self.logger.debug(f"Fetching orders for customer: {email}")

            response = await self.http_client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get("orders", [])
            else:
                self.logger.error(f"Shopify API error: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error fetching customer orders: {e}", exc_info=True)
            return []

    async def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search products by keyword/title using Shopify API.

        This is the primary method for Issue #25 (Customer Product Information Inquiries).
        It searches the product catalog by name, allowing customers to find products,
        check availability, and learn about features.

        API Endpoint: GET /admin/api/{version}/products.json?title={query}
        Reference: https://shopify.dev/docs/api/admin-rest/resources/product#get-products

        Args:
            query: Search query (keywords/product name)
                Examples: "coffee", "brewer", "espresso", "gift card", "organic mango"
                Search is case-insensitive and matches partial names
            limit: Maximum number of results to return (default 10)

        Returns:
            List of matching product dictionaries
            Product structure (per test-data/shopify/products.json):
            {
                "id": "PROD-001",
                "sku": "BRWR-PREM-BLK",
                "name": "Premium Single-Serve Coffee Brewer",
                "category": "brewers",
                "price": 398.00,
                "in_stock": true,
                "inventory_count": 47,
                "description": "Our flagship single-serve coffee brewer...",
                "features": ["7 customizable brew parameters", "Auto-optimization..."],
                "tags": ["brewer", "premium", "coffee-maker"],
                "variant_id": "VAR-001-BLK",
                "variant_name": "Black"
            }

        Error Handling:
        - 200 OK: Returns product list (may be empty if no matches)
        - Other errors: Logs error, returns empty list (graceful degradation)
        - Network timeouts: Caught by httpx timeout (10s), returns empty list

        Performance:
        - Target latency: <200ms (P95) per ISSUE-25-IMPLEMENTATION-PLAN.md
        - Actual latency: Typically <50ms for mock API (local Docker)
        - Production latency: 100-300ms (Shopify API over internet)

        Issue #25 Implementation Notes:
        - Phase 1-3: Uses mock API with server-side filtering (title parameter)
        - Phase 4-5: Uses real Shopify API with same endpoint
        - Search strategy: Server-side partial match on product name (case-insensitive)
        - Example: query="coffee" matches "Premium Coffee Brewer", "Coffee Pods Variety Pack"
        """
        try:
            # Construct Shopify REST Admin API URL with title search parameter
            # Issue #25: Uses title parameter for server-side product name filtering
            # This is more efficient than client-side filtering (reduces network payload)
            # API Version: 2024-01 (Shopify recommends using stable versions)
            # Reference: https://shopify.dev/docs/api/admin-rest/api-versioning
            url = f"{self.base_url}/admin/api/2024-01/products.json"
            params = {
                "title": query,  # Issue #25: Server-side search by product name
                "limit": limit   # Limit results (1-250, default 50 on API)
            }

            self.logger.debug(f"Searching products with query='{query}', limit={limit}")

            # Make async HTTP GET request
            # This is non-blocking - allows other agents to process concurrently
            # Reference: Python asyncio - https://docs.python.org/3/library/asyncio-task.html
            response = await self.http_client.get(url, params=params)

            if response.status_code == 200:
                # Success: Parse JSON response body
                # Shopify wraps products in {"products": [...]} structure
                data = response.json()
                products = data.get("products", [])

                self.logger.info(
                    f"Found {len(products)} products matching '{query}' "
                    f"(limit: {limit})"
                )
                return products

            else:
                # Unexpected API error (5xx server errors, 401 auth errors, etc.)
                # Log for debugging but don't crash - return empty list for graceful degradation
                self.logger.error(
                    f"Shopify API error searching products (query='{query}'): "
                    f"HTTP {response.status_code} - {response.text}"
                )
                return []

        except httpx.TimeoutException:
            # Network timeout (>10 seconds)
            # This might indicate Shopify API downtime or network issues
            self.logger.error(
                f"Timeout searching products (query='{query}', >10s). "
                "Check API availability and network connectivity."
            )
            return []

        except httpx.HTTPError as e:
            # Other HTTP errors (connection refused, DNS resolution failure, etc.)
            self.logger.error(
                f"HTTP error searching products (query='{query}'): {e}",
                exc_info=True
            )
            return []

        except Exception as e:
            # Catch-all for unexpected errors (JSON parsing, etc.)
            # exc_info=True provides full stack trace for debugging
            self.logger.error(
                f"Unexpected error searching products (query='{query}'): {e}",
                exc_info=True
            )
            return []

    async def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get product by ID.

        Args:
            product_id: Product ID (e.g., "PROD-001")

        Returns:
            Product dict or None
        """
        try:
            url = f"{self.base_url}/admin/api/2024-01/products/{product_id}.json"

            response = await self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()
                return data.get("product")
            elif response.status_code == 404:
                return None
            else:
                self.logger.error(f"Shopify API error: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error fetching product: {e}", exc_info=True)
            return None

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
