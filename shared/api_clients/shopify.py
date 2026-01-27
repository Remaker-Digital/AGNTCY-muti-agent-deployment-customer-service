"""
Shopify API Client for AGNTCY Multi-Agent Customer Service Platform

Provides async HTTP client for Shopify REST Admin API integration.

Phase 1-3: Mock API (http://localhost:8001)
Phase 4-5: Real Shopify API (https://{shop}.myshopify.com/admin/api/2024-01)

Features:
- Order retrieval by order number or customer email
- Product search and catalog browsing
- Inventory status checking
- Full authentication support for production

API Reference: https://shopify.dev/docs/api/admin-rest
Rate Limits: 2 req/sec standard, 4 req/sec Plus
"""

import os
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAPIClient, APIClientConfig, AuthType, APIResponse

logger = logging.getLogger(__name__)

# Singleton instance
_client_instance: Optional["ShopifyClient"] = None


class ShopifyClient(BaseAPIClient):
    """
    Async HTTP client for Shopify REST Admin API.

    Supports both mock (Phase 1-3) and real API (Phase 4-5) modes.

    Usage:
        # Using singleton (recommended)
        client = await get_shopify_client()
        order = await client.get_order("ORD-12345")

        # Using context manager
        async with ShopifyClient() as client:
            products = await client.search_products("coffee")
    """

    API_VERSION = "2024-01"  # Shopify API version

    @property
    def service_name(self) -> str:
        return "shopify"

    def _default_config(self) -> APIClientConfig:
        """Create default config from environment."""
        use_real = os.getenv("USE_REAL_APIS", "false").lower() == "true"

        if use_real and os.getenv("SHOPIFY_STORE_URL"):
            # Real Shopify API
            store_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
            base_url = f"https://{store_url}/admin/api/{self.API_VERSION}"

            return APIClientConfig(
                base_url=base_url,
                auth_type=AuthType.API_KEY,
                access_token=os.getenv("SHOPIFY_ACCESS_TOKEN"),
                api_key=os.getenv("SHOPIFY_API_KEY"),
                api_secret=os.getenv("SHOPIFY_API_SECRET"),
                rate_limit_per_second=2.0,  # Shopify standard limit
            )
        else:
            # Mock API
            return APIClientConfig(
                base_url=os.getenv("MOCK_SHOPIFY_URL", "http://localhost:8001"),
                auth_type=AuthType.NONE,
                rate_limit_per_second=0,  # No rate limit for mock
            )

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build Shopify-specific authentication headers."""
        headers = {}

        if self.config.auth_type == AuthType.API_KEY and self.config.access_token:
            # Shopify uses X-Shopify-Access-Token header
            headers["X-Shopify-Access-Token"] = self.config.access_token

        return headers

    # =========================================================================
    # ORDER METHODS
    # =========================================================================

    async def get_order(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        Get order by order number.

        Args:
            order_number: Order number (e.g., "ORD-12345", "12345", "#12345")

        Returns:
            Order data dict or None if not found

        API: GET /admin/api/2024-01/orders/{order_number}.json
        """
        # Normalize order number (remove prefix if present)
        clean_number = order_number.lstrip("#").replace("ORD-", "")

        response = await self.get(
            f"/admin/api/{self.API_VERSION}/orders/{order_number}.json"
        )

        if response.success and response.data:
            return response.data.get("order")
        elif response.is_not_found:
            self.logger.debug(f"Order {order_number} not found")
            return None
        else:
            self.logger.warning(f"Error fetching order {order_number}: {response.error}")
            return None

    async def get_orders_by_email(
        self,
        email: str,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get orders for a customer by email.

        Args:
            email: Customer email address
            limit: Maximum orders to return (default 10)
            status: Filter by status (open, closed, cancelled, any)

        Returns:
            List of order dicts

        API: GET /admin/api/2024-01/orders.json?customer_email={email}
        """
        params = {
            "customer_email": email,
            "limit": limit,
        }
        if status:
            params["status"] = status

        response = await self.get(
            f"/admin/api/{self.API_VERSION}/orders.json",
            params=params
        )

        if response.success and response.data:
            return response.data.get("orders", [])
        return []

    async def get_order_fulfillments(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Get fulfillments (shipments) for an order.

        Args:
            order_id: Order ID

        Returns:
            List of fulfillment dicts with tracking info

        API: GET /admin/api/2024-01/orders/{order_id}/fulfillments.json
        """
        response = await self.get(
            f"/admin/api/{self.API_VERSION}/orders/{order_id}/fulfillments.json"
        )

        if response.success and response.data:
            return response.data.get("fulfillments", [])
        return []

    # =========================================================================
    # PRODUCT METHODS
    # =========================================================================

    async def search_products(
        self,
        query: str,
        limit: int = 10,
        collection_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search products by title/keyword.

        Args:
            query: Search query (matches product title)
            limit: Maximum products to return (default 10, max 250)
            collection_id: Optional collection ID to filter

        Returns:
            List of matching product dicts

        API: GET /admin/api/2024-01/products.json?title={query}
        """
        params = {
            "title": query,
            "limit": min(limit, 250),
        }
        if collection_id:
            params["collection_id"] = collection_id

        response = await self.get(
            f"/admin/api/{self.API_VERSION}/products.json",
            params=params
        )

        if response.success and response.data:
            products = response.data.get("products", [])
            self.logger.debug(f"Found {len(products)} products for query '{query}'")
            return products
        return []

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get product by ID.

        Args:
            product_id: Product ID

        Returns:
            Product data dict or None

        API: GET /admin/api/2024-01/products/{product_id}.json
        """
        response = await self.get(
            f"/admin/api/{self.API_VERSION}/products/{product_id}.json"
        )

        if response.success and response.data:
            return response.data.get("product")
        elif response.is_not_found:
            return None
        else:
            self.logger.warning(f"Error fetching product {product_id}: {response.error}")
            return None

    async def get_products(
        self,
        limit: int = 50,
        since_id: Optional[str] = None,
        product_type: Optional[str] = None,
        vendor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List products with optional filters.

        Args:
            limit: Maximum products to return (default 50, max 250)
            since_id: Pagination cursor (products after this ID)
            product_type: Filter by product type
            vendor: Filter by vendor

        Returns:
            List of product dicts

        API: GET /admin/api/2024-01/products.json
        """
        params = {"limit": min(limit, 250)}
        if since_id:
            params["since_id"] = since_id
        if product_type:
            params["product_type"] = product_type
        if vendor:
            params["vendor"] = vendor

        response = await self.get(
            f"/admin/api/{self.API_VERSION}/products.json",
            params=params
        )

        if response.success and response.data:
            return response.data.get("products", [])
        return []

    # =========================================================================
    # INVENTORY METHODS
    # =========================================================================

    async def get_inventory_levels(
        self,
        inventory_item_ids: Optional[List[str]] = None,
        location_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get inventory levels for items/locations.

        Args:
            inventory_item_ids: List of inventory item IDs
            location_ids: List of location IDs

        Returns:
            List of inventory level dicts

        API: GET /admin/api/2024-01/inventory_levels.json
        """
        params = {}
        if inventory_item_ids:
            params["inventory_item_ids"] = ",".join(inventory_item_ids)
        if location_ids:
            params["location_ids"] = ",".join(location_ids)

        response = await self.get(
            f"/admin/api/{self.API_VERSION}/inventory_levels.json",
            params=params
        )

        if response.success and response.data:
            return response.data.get("inventory_levels", [])
        return []

    # =========================================================================
    # CUSTOMER METHODS
    # =========================================================================

    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get customer by ID.

        Args:
            customer_id: Customer ID

        Returns:
            Customer data dict or None

        API: GET /admin/api/2024-01/customers/{customer_id}.json
        """
        response = await self.get(
            f"/admin/api/{self.API_VERSION}/customers/{customer_id}.json"
        )

        if response.success and response.data:
            return response.data.get("customer")
        return None

    async def search_customers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search customers by email, name, etc.

        Args:
            query: Search query (email, name, phone)
            limit: Maximum customers to return

        Returns:
            List of customer dicts

        API: GET /admin/api/2024-01/customers/search.json?query={query}
        """
        response = await self.get(
            f"/admin/api/{self.API_VERSION}/customers/search.json",
            params={"query": query, "limit": limit}
        )

        if response.success and response.data:
            return response.data.get("customers", [])
        return []

    # =========================================================================
    # CHECKOUT/CART METHODS
    # =========================================================================

    async def get_abandoned_checkouts(
        self,
        limit: int = 50,
        since_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get abandoned checkouts.

        Args:
            limit: Maximum checkouts to return
            since_id: Pagination cursor

        Returns:
            List of abandoned checkout dicts

        API: GET /admin/api/2024-01/checkouts.json
        """
        params = {"limit": limit}
        if since_id:
            params["since_id"] = since_id

        response = await self.get(
            f"/admin/api/{self.API_VERSION}/checkouts.json",
            params=params
        )

        if response.success and response.data:
            return response.data.get("checkouts", [])
        return []

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    async def health_check(self) -> bool:
        """Check if Shopify API is reachable."""
        # Try to get shop info as health check
        response = await self.get(f"/admin/api/{self.API_VERSION}/shop.json")
        if response.success:
            return True

        # Fall back to /health for mock API
        response = await self.get("/health")
        return response.success


async def get_shopify_client() -> ShopifyClient:
    """
    Get singleton Shopify client instance.

    Returns:
        ShopifyClient instance (reused across calls)
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = ShopifyClient()
    return _client_instance


async def shutdown_shopify_client():
    """Shutdown the singleton client."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
