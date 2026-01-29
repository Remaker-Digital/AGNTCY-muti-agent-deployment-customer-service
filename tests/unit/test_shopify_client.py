# ============================================================================
# Unit Tests for Shopify API Client
# ============================================================================
# Purpose: Test Shopify REST Admin API client for e-commerce integration
#
# Test Categories:
# 1. Client Initialization - Verify client setup and config
# 2. Order Operations - Order retrieval and filtering
# 3. Product Operations - Product search and catalog
# 4. Inventory Operations - Stock level checking
# 5. Customer Operations - Customer lookup and search
# 6. Checkout Operations - Abandoned cart handling
# 7. Health Check - API availability checks
# 8. Singleton Pattern - Client reuse and shutdown
#
# Related Documentation:
# - Shopify Client: shared/api_clients/shopify.py
# - Shopify API Reference: https://shopify.dev/docs/api/admin-rest
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.api_clients.shopify import (
    ShopifyClient,
    get_shopify_client,
    shutdown_shopify_client,
)
from shared.api_clients.base import APIClientConfig, AuthType, APIResponse


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def shopify_client():
    """Create a Shopify client for testing."""
    return ShopifyClient()


@pytest.fixture
def mock_api_response():
    """Create a factory for mock API responses."""

    def _create_response(success=True, data=None, error=None, status_code=200):
        response = MagicMock(spec=APIResponse)
        response.success = success
        response.data = data
        response.error = error
        response.status_code = status_code
        response.is_not_found = status_code == 404
        return response

    return _create_response


@pytest.fixture
def sample_order():
    """Sample order data."""
    return {
        "id": 12345,
        "order_number": "ORD-12345",
        "email": "customer@example.com",
        "created_at": "2026-01-25T10:00:00-05:00",
        "total_price": "125.99",
        "currency": "USD",
        "financial_status": "paid",
        "fulfillment_status": "fulfilled",
        "line_items": [
            {
                "id": 1,
                "title": "Premium Coffee Blend",
                "quantity": 2,
                "price": "24.99",
            },
            {
                "id": 2,
                "title": "Coffee Mug",
                "quantity": 1,
                "price": "15.99",
            },
        ],
        "shipping_address": {
            "first_name": "John",
            "last_name": "Doe",
            "city": "Seattle",
            "province": "WA",
            "country": "US",
            "zip": "98101",
        },
    }


@pytest.fixture
def sample_product():
    """Sample product data."""
    return {
        "id": 67890,
        "title": "Premium Coffee Blend",
        "body_html": "<p>Our finest coffee blend</p>",
        "vendor": "BrewVi Coffee",
        "product_type": "Coffee",
        "created_at": "2025-06-01T08:00:00-05:00",
        "variants": [
            {
                "id": 1001,
                "title": "12oz Bag",
                "price": "24.99",
                "sku": "COFFEE-PREM-12",
                "inventory_quantity": 50,
            },
            {
                "id": 1002,
                "title": "24oz Bag",
                "price": "44.99",
                "sku": "COFFEE-PREM-24",
                "inventory_quantity": 30,
            },
        ],
        "images": [
            {"src": "https://cdn.shopify.com/coffee-blend.jpg"},
        ],
    }


@pytest.fixture
def sample_customer():
    """Sample customer data."""
    return {
        "id": 99001,
        "email": "customer@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+15551234567",
        "created_at": "2025-03-15T09:00:00-05:00",
        "orders_count": 5,
        "total_spent": "523.45",
    }


@pytest.fixture
def sample_fulfillment():
    """Sample fulfillment data."""
    return {
        "id": 55001,
        "order_id": 12345,
        "status": "success",
        "tracking_company": "UPS",
        "tracking_number": "1Z999AA10123456784",
        "tracking_url": "https://www.ups.com/track?loc=en_US&tracknum=1Z999AA10123456784",
        "created_at": "2026-01-26T08:00:00-05:00",
    }


# =============================================================================
# Test: Client Initialization
# =============================================================================


class TestClientInitialization:
    """Tests for Shopify client initialization."""

    def test_service_name(self, shopify_client):
        """Verify service name is correct."""
        assert shopify_client.service_name == "shopify"

    def test_api_version(self, shopify_client):
        """Verify API version is set."""
        assert shopify_client.API_VERSION == "2024-01"

    def test_default_config_mock_mode(self, shopify_client):
        """Verify default config uses mock API."""
        config = shopify_client._default_config()
        assert "localhost:8001" in config.base_url
        assert config.auth_type == AuthType.NONE

    @patch.dict(
        os.environ,
        {
            "USE_REAL_APIS": "true",
            "SHOPIFY_STORE_URL": "my-store.myshopify.com",
            "SHOPIFY_ACCESS_TOKEN": "shpat_abc123",
            "SHOPIFY_API_KEY": "api_key_123",
            "SHOPIFY_API_SECRET": "api_secret_456",
        },
    )
    def test_real_api_config(self):
        """Verify real API config from environment."""
        client = ShopifyClient()
        config = client._default_config()
        assert "my-store.myshopify.com" in config.base_url
        assert "/admin/api/2024-01" in config.base_url
        assert config.auth_type == AuthType.API_KEY
        assert config.access_token == "shpat_abc123"

    @patch.dict(os.environ, {"USE_REAL_APIS": "true"}, clear=False)
    def test_real_api_without_store_url_falls_back_to_mock(self):
        """Verify fallback to mock when store URL not set."""
        env_backup = os.environ.get("SHOPIFY_STORE_URL")
        if "SHOPIFY_STORE_URL" in os.environ:
            del os.environ["SHOPIFY_STORE_URL"]

        try:
            client = ShopifyClient()
            config = client._default_config()
            assert "localhost" in config.base_url
        finally:
            if env_backup:
                os.environ["SHOPIFY_STORE_URL"] = env_backup

    @patch.dict(os.environ, {"MOCK_SHOPIFY_URL": "http://custom-mock:9001"})
    def test_custom_mock_url(self):
        """Verify custom mock URL from environment."""
        client = ShopifyClient()
        config = client._default_config()
        assert config.base_url == "http://custom-mock:9001"


# =============================================================================
# Test: Auth Headers
# =============================================================================


class TestAuthHeaders:
    """Tests for authentication header building."""

    def test_build_auth_headers_no_auth(self, shopify_client):
        """Verify no headers when no auth configured."""
        # BaseAPIClient sets self.config directly in __init__
        shopify_client.config = APIClientConfig(
            base_url="http://localhost",
            auth_type=AuthType.NONE,
        )
        headers = shopify_client._build_auth_headers()
        assert headers == {}

    def test_build_auth_headers_with_access_token(self, shopify_client):
        """Verify X-Shopify-Access-Token header."""
        # BaseAPIClient sets self.config directly in __init__
        shopify_client.config = APIClientConfig(
            base_url="http://localhost",
            auth_type=AuthType.API_KEY,
            access_token="shpat_test123",
        )
        headers = shopify_client._build_auth_headers()
        assert "X-Shopify-Access-Token" in headers
        assert headers["X-Shopify-Access-Token"] == "shpat_test123"


# =============================================================================
# Test: Order Operations
# =============================================================================


class TestOrderOperations:
    """Tests for order operations."""

    @pytest.mark.asyncio
    async def test_get_order_success(
        self, shopify_client, mock_api_response, sample_order
    ):
        """Verify successful order retrieval."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"order": sample_order})
        )

        result = await shopify_client.get_order("ORD-12345")

        assert result is not None
        assert result["order_number"] == "ORD-12345"
        assert result["total_price"] == "125.99"

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, shopify_client, mock_api_response):
        """Verify order not found handling."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await shopify_client.get_order("ORD-99999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_order_error(self, shopify_client, mock_api_response):
        """Verify error handling."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(
                success=False, error="Server error", status_code=500
            )
        )

        result = await shopify_client.get_order("ORD-12345")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_orders_by_email_success(
        self, shopify_client, mock_api_response, sample_order
    ):
        """Verify orders by email retrieval."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"orders": [sample_order]})
        )

        result = await shopify_client.get_orders_by_email("customer@example.com")

        assert len(result) == 1
        assert result[0]["email"] == "customer@example.com"

    @pytest.mark.asyncio
    async def test_get_orders_by_email_with_status_filter(
        self, shopify_client, mock_api_response
    ):
        """Verify status filter is passed."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"orders": []})
        )

        await shopify_client.get_orders_by_email(
            "test@example.com", status="open"
        )

        call_args = shopify_client.get.call_args
        assert call_args[1]["params"]["status"] == "open"

    @pytest.mark.asyncio
    async def test_get_orders_by_email_with_limit(
        self, shopify_client, mock_api_response
    ):
        """Verify limit parameter is passed."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"orders": []})
        )

        await shopify_client.get_orders_by_email("test@example.com", limit=5)

        call_args = shopify_client.get.call_args
        assert call_args[1]["params"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_orders_by_email_error(self, shopify_client, mock_api_response):
        """Verify error returns empty list."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await shopify_client.get_orders_by_email("test@example.com")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_order_fulfillments_success(
        self, shopify_client, mock_api_response, sample_fulfillment
    ):
        """Verify fulfillments retrieval."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"fulfillments": [sample_fulfillment]})
        )

        result = await shopify_client.get_order_fulfillments("12345")

        assert len(result) == 1
        assert result[0]["tracking_company"] == "UPS"

    @pytest.mark.asyncio
    async def test_get_order_fulfillments_error(
        self, shopify_client, mock_api_response
    ):
        """Verify error returns empty list."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="Not found")
        )

        result = await shopify_client.get_order_fulfillments("99999")

        assert result == []


# =============================================================================
# Test: Product Operations
# =============================================================================


class TestProductOperations:
    """Tests for product operations."""

    @pytest.mark.asyncio
    async def test_search_products_success(
        self, shopify_client, mock_api_response, sample_product
    ):
        """Verify product search."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"products": [sample_product]})
        )

        result = await shopify_client.search_products("coffee")

        assert len(result) == 1
        assert result[0]["title"] == "Premium Coffee Blend"

    @pytest.mark.asyncio
    async def test_search_products_with_collection_filter(
        self, shopify_client, mock_api_response
    ):
        """Verify collection_id filter is passed."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"products": []})
        )

        await shopify_client.search_products("coffee", collection_id="coll_123")

        call_args = shopify_client.get.call_args
        assert call_args[1]["params"]["collection_id"] == "coll_123"

    @pytest.mark.asyncio
    async def test_search_products_limit_capped_at_250(
        self, shopify_client, mock_api_response
    ):
        """Verify limit is capped at 250."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"products": []})
        )

        await shopify_client.search_products("coffee", limit=500)

        call_args = shopify_client.get.call_args
        assert call_args[1]["params"]["limit"] == 250

    @pytest.mark.asyncio
    async def test_search_products_error(self, shopify_client, mock_api_response):
        """Verify error returns empty list."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await shopify_client.search_products("nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_product_success(
        self, shopify_client, mock_api_response, sample_product
    ):
        """Verify product retrieval."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"product": sample_product})
        )

        result = await shopify_client.get_product("67890")

        assert result is not None
        assert result["title"] == "Premium Coffee Blend"

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, shopify_client, mock_api_response):
        """Verify product not found."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await shopify_client.get_product("99999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_product_error(self, shopify_client, mock_api_response):
        """Verify error handling."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(
                success=False, error="Server error", status_code=500
            )
        )

        result = await shopify_client.get_product("67890")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_products_success(
        self, shopify_client, mock_api_response, sample_product
    ):
        """Verify products list retrieval."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"products": [sample_product]})
        )

        result = await shopify_client.get_products()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_products_with_filters(
        self, shopify_client, mock_api_response
    ):
        """Verify filter parameters are passed."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"products": []})
        )

        await shopify_client.get_products(
            since_id="123",
            product_type="Coffee",
            vendor="BrewVi",
        )

        call_args = shopify_client.get.call_args
        params = call_args[1]["params"]
        assert params["since_id"] == "123"
        assert params["product_type"] == "Coffee"
        assert params["vendor"] == "BrewVi"

    @pytest.mark.asyncio
    async def test_get_products_limit_capped(self, shopify_client, mock_api_response):
        """Verify limit is capped at 250."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"products": []})
        )

        await shopify_client.get_products(limit=500)

        call_args = shopify_client.get.call_args
        assert call_args[1]["params"]["limit"] == 250

    @pytest.mark.asyncio
    async def test_get_products_error(self, shopify_client, mock_api_response):
        """Verify error returns empty list."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await shopify_client.get_products()

        assert result == []


# =============================================================================
# Test: Inventory Operations
# =============================================================================


class TestInventoryOperations:
    """Tests for inventory operations."""

    @pytest.mark.asyncio
    async def test_get_inventory_levels_success(
        self, shopify_client, mock_api_response
    ):
        """Verify inventory levels retrieval."""
        inventory_data = [
            {"inventory_item_id": "101", "location_id": "loc1", "available": 50},
            {"inventory_item_id": "102", "location_id": "loc1", "available": 30},
        ]
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"inventory_levels": inventory_data})
        )

        result = await shopify_client.get_inventory_levels(
            inventory_item_ids=["101", "102"]
        )

        assert len(result) == 2
        assert result[0]["available"] == 50

    @pytest.mark.asyncio
    async def test_get_inventory_levels_with_filters(
        self, shopify_client, mock_api_response
    ):
        """Verify filter parameters are passed."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"inventory_levels": []})
        )

        await shopify_client.get_inventory_levels(
            inventory_item_ids=["101", "102"],
            location_ids=["loc1", "loc2"],
        )

        call_args = shopify_client.get.call_args
        params = call_args[1]["params"]
        assert params["inventory_item_ids"] == "101,102"
        assert params["location_ids"] == "loc1,loc2"

    @pytest.mark.asyncio
    async def test_get_inventory_levels_error(
        self, shopify_client, mock_api_response
    ):
        """Verify error returns empty list."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await shopify_client.get_inventory_levels()

        assert result == []


# =============================================================================
# Test: Customer Operations
# =============================================================================


class TestCustomerOperations:
    """Tests for customer operations."""

    @pytest.mark.asyncio
    async def test_get_customer_success(
        self, shopify_client, mock_api_response, sample_customer
    ):
        """Verify customer retrieval."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"customer": sample_customer})
        )

        result = await shopify_client.get_customer("99001")

        assert result is not None
        assert result["email"] == "customer@example.com"

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, shopify_client, mock_api_response):
        """Verify customer not found."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await shopify_client.get_customer("99999")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_customers_success(
        self, shopify_client, mock_api_response, sample_customer
    ):
        """Verify customer search."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"customers": [sample_customer]})
        )

        result = await shopify_client.search_customers("customer@example.com")

        assert len(result) == 1
        assert result[0]["email"] == "customer@example.com"

    @pytest.mark.asyncio
    async def test_search_customers_with_limit(
        self, shopify_client, mock_api_response
    ):
        """Verify limit parameter is passed."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"customers": []})
        )

        await shopify_client.search_customers("john", limit=5)

        call_args = shopify_client.get.call_args
        assert call_args[1]["params"]["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_customers_error(self, shopify_client, mock_api_response):
        """Verify error returns empty list."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await shopify_client.search_customers("nonexistent")

        assert result == []


# =============================================================================
# Test: Checkout Operations
# =============================================================================


class TestCheckoutOperations:
    """Tests for checkout operations."""

    @pytest.mark.asyncio
    async def test_get_abandoned_checkouts_success(
        self, shopify_client, mock_api_response
    ):
        """Verify abandoned checkouts retrieval."""
        checkout_data = [
            {
                "id": "chk_123",
                "email": "abandoned@example.com",
                "total_price": "49.99",
                "abandoned_checkout_url": "https://shop.com/checkouts/123",
            }
        ]
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"checkouts": checkout_data})
        )

        result = await shopify_client.get_abandoned_checkouts()

        assert len(result) == 1
        assert result[0]["email"] == "abandoned@example.com"

    @pytest.mark.asyncio
    async def test_get_abandoned_checkouts_with_pagination(
        self, shopify_client, mock_api_response
    ):
        """Verify pagination parameters are passed."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"checkouts": []})
        )

        await shopify_client.get_abandoned_checkouts(limit=25, since_id="chk_100")

        call_args = shopify_client.get.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 25
        assert params["since_id"] == "chk_100"

    @pytest.mark.asyncio
    async def test_get_abandoned_checkouts_error(
        self, shopify_client, mock_api_response
    ):
        """Verify error returns empty list."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await shopify_client.get_abandoned_checkouts()

        assert result == []


# =============================================================================
# Test: Health Check
# =============================================================================


class TestHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success_shop_endpoint(
        self, shopify_client, mock_api_response
    ):
        """Verify health check with shop endpoint."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"shop": {"id": 123}})
        )

        result = await shopify_client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_fallback_to_health(
        self, shopify_client, mock_api_response
    ):
        """Verify fallback to /health endpoint for mock API."""
        shopify_client.get = AsyncMock(
            side_effect=[
                mock_api_response(success=False),  # /shop.json fails
                mock_api_response(success=True),  # /health succeeds
            ]
        )

        result = await shopify_client.health_check()

        assert result is True
        assert shopify_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_both_fail(self, shopify_client, mock_api_response):
        """Verify health check failure when both endpoints fail."""
        shopify_client.get = AsyncMock(
            side_effect=[
                mock_api_response(success=False),
                mock_api_response(success=False),
            ]
        )

        result = await shopify_client.health_check()

        assert result is False


# =============================================================================
# Test: Singleton Pattern
# =============================================================================


class TestSingletonPattern:
    """Tests for singleton client pattern."""

    @pytest.mark.asyncio
    async def test_get_shopify_client_returns_client(self):
        """Verify get_shopify_client returns a client."""
        import shared.api_clients.shopify as shopify_module

        shopify_module._client_instance = None

        client = await get_shopify_client()

        assert client is not None
        assert isinstance(client, ShopifyClient)

    @pytest.mark.asyncio
    async def test_get_shopify_client_singleton(self):
        """Verify same instance is returned."""
        import shared.api_clients.shopify as shopify_module

        shopify_module._client_instance = None

        client1 = await get_shopify_client()
        client2 = await get_shopify_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_shutdown_shopify_client(self):
        """Verify shutdown clears singleton."""
        import shared.api_clients.shopify as shopify_module

        shopify_module._client_instance = None
        client = await get_shopify_client()
        client.close = AsyncMock()

        await shutdown_shopify_client()

        assert shopify_module._client_instance is None
        client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_when_no_client(self):
        """Verify shutdown handles no client gracefully."""
        import shared.api_clients.shopify as shopify_module

        shopify_module._client_instance = None

        # Should not raise
        await shutdown_shopify_client()


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_order_number_normalization(
        self, shopify_client, mock_api_response, sample_order
    ):
        """Verify various order number formats are accepted."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"order": sample_order})
        )

        # Test with different formats - all should work
        await shopify_client.get_order("ORD-12345")
        await shopify_client.get_order("#12345")
        await shopify_client.get_order("12345")

        assert shopify_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_unicode_in_search_query(
        self, shopify_client, mock_api_response
    ):
        """Verify unicode in search query is handled."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"products": []})
        )

        # Should not raise
        await shopify_client.search_products("Café ☕")

    @pytest.mark.asyncio
    async def test_empty_email_for_orders(self, shopify_client, mock_api_response):
        """Verify empty email returns empty list."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"orders": []})
        )

        result = await shopify_client.get_orders_by_email("")

        assert result == []

    @pytest.mark.asyncio
    async def test_special_characters_in_customer_search(
        self, shopify_client, mock_api_response
    ):
        """Verify special characters in customer search."""
        shopify_client.get = AsyncMock(
            return_value=mock_api_response(data={"customers": []})
        )

        # Should not raise
        await shopify_client.search_customers("user+tag@example.com")
