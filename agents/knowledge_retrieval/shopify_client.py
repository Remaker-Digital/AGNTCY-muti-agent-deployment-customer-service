"""
Shopify API client for Knowledge Retrieval Agent
Phase 2: Enhanced with coffee/brewing business logic
"""

import httpx
import json
from typing import List, Dict, Any, Optional
from pathlib import Path


class ShopifyClient:
    """Client for interacting with mock Shopify API."""

    def __init__(self, base_url: str, logger):
        """
        Initialize Shopify client.

        Args:
            base_url: Base URL for Shopify API (e.g., http://localhost:8001)
            logger: Logger instance
        """
        self.base_url = base_url.rstrip('/')
        self.logger = logger
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def get_order_by_number(self, order_number: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve order by order number.

        Args:
            order_number: Order number (e.g., "10234" or "ORD-10234")

        Returns:
            Order dict or None if not found
        """
        try:
            url = f"{self.base_url}/admin/api/2024-01/orders/{order_number}.json"
            self.logger.debug(f"Fetching order: {url}")

            response = await self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()
                return data.get("order")
            elif response.status_code == 404:
                self.logger.warning(f"Order {order_number} not found")
                return None
            else:
                self.logger.error(f"Shopify API error: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error fetching order: {e}", exc_info=True)
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
        Search products by keyword.

        Args:
            query: Search query (keywords)
            limit: Maximum results

        Returns:
            List of matching product dicts
        """
        try:
            url = f"{self.base_url}/admin/api/2024-01/products.json"
            params = {"limit": 50}  # Get all products then filter

            response = await self.http_client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                all_products = data.get("products", [])

                # Simple keyword matching (Phase 2)
                query_lower = query.lower()
                matching = []

                for product in all_products:
                    # Check name, description, tags, category
                    matches = (
                        query_lower in product.get("name", "").lower() or
                        query_lower in product.get("description", "").lower() or
                        query_lower in product.get("category", "").lower() or
                        any(query_lower in tag.lower() for tag in product.get("tags", []))
                    )

                    if matches:
                        matching.append(product)

                return matching[:limit]
            else:
                self.logger.error(f"Shopify API error: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error searching products: {e}", exc_info=True)
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
