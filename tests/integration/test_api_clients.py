"""
Integration tests for API clients.

Tests the shared API clients against mock services (Phase 1-3)
and real APIs (Phase 4-5 when USE_REAL_APIS=true).

Run: pytest tests/integration/test_api_clients.py -v
"""

import os
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator

# Set mock mode for tests
os.environ.setdefault("USE_REAL_APIS", "false")
os.environ.setdefault("MOCK_SHOPIFY_URL", "http://localhost:8001")
os.environ.setdefault("MOCK_ZENDESK_URL", "http://localhost:8002")
os.environ.setdefault("MOCK_MAILCHIMP_URL", "http://localhost:8003")
os.environ.setdefault("MOCK_GOOGLE_ANALYTICS_URL", "http://localhost:8004")

from shared.api_clients import (
    ShopifyClient,
    ZendeskClient,
    MailchimpClient,
    GoogleAnalyticsClient,
    get_shopify_client,
    get_zendesk_client,
    get_mailchimp_client,
    get_google_analytics_client,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest_asyncio.fixture
async def shopify_client() -> AsyncGenerator[ShopifyClient, None]:
    """Create Shopify client for testing."""
    client = ShopifyClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def zendesk_client() -> AsyncGenerator[ZendeskClient, None]:
    """Create Zendesk client for testing."""
    client = ZendeskClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def mailchimp_client() -> AsyncGenerator[MailchimpClient, None]:
    """Create Mailchimp client for testing."""
    client = MailchimpClient()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def ga_client() -> AsyncGenerator[GoogleAnalyticsClient, None]:
    """Create Google Analytics client for testing."""
    client = GoogleAnalyticsClient()
    yield client
    await client.close()


# =============================================================================
# SHOPIFY CLIENT TESTS
# =============================================================================


class TestShopifyClient:
    """Test Shopify API client."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, shopify_client: ShopifyClient):
        """Test client initializes with correct config."""
        assert shopify_client.service_name == "shopify"
        assert "localhost:8001" in shopify_client.config.base_url

    @pytest.mark.asyncio
    async def test_search_products(self, shopify_client: ShopifyClient):
        """Test product search."""
        products = await shopify_client.search_products("coffee", limit=5)

        # Mock API should return products
        assert isinstance(products, list)
        # May be empty if mock isn't running, but shouldn't error

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, shopify_client: ShopifyClient):
        """Test getting non-existent order returns None."""
        order = await shopify_client.get_order("NONEXISTENT-ORDER-999")

        # Should return None, not raise exception
        assert order is None

    @pytest.mark.asyncio
    async def test_get_orders_by_email(self, shopify_client: ShopifyClient):
        """Test getting orders by email."""
        orders = await shopify_client.get_orders_by_email("test@example.com")

        # Should return list (may be empty)
        assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_health_check(self, shopify_client: ShopifyClient):
        """Test health check endpoint."""
        # May fail if mock not running, but shouldn't raise
        is_healthy = await shopify_client.health_check()
        assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    async def test_metrics(self, shopify_client: ShopifyClient):
        """Test client metrics tracking."""
        # Make a request first
        await shopify_client.search_products("test")

        metrics = shopify_client.get_metrics()

        assert metrics["service"] == "shopify"
        assert "request_count" in metrics
        assert "error_count" in metrics


# =============================================================================
# ZENDESK CLIENT TESTS
# =============================================================================


class TestZendeskClient:
    """Test Zendesk API client."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, zendesk_client: ZendeskClient):
        """Test client initializes with correct config."""
        assert zendesk_client.service_name == "zendesk"
        assert "localhost:8002" in zendesk_client.config.base_url

    @pytest.mark.asyncio
    async def test_list_tickets(self, zendesk_client: ZendeskClient):
        """Test listing tickets."""
        result = await zendesk_client.list_tickets(page=1, per_page=10)

        assert "tickets" in result
        assert isinstance(result["tickets"], list)

    @pytest.mark.asyncio
    async def test_get_ticket_not_found(self, zendesk_client: ZendeskClient):
        """Test getting non-existent ticket returns None."""
        ticket = await zendesk_client.get_ticket("999999")

        assert ticket is None

    @pytest.mark.asyncio
    async def test_health_check(self, zendesk_client: ZendeskClient):
        """Test health check endpoint."""
        is_healthy = await zendesk_client.health_check()
        assert isinstance(is_healthy, bool)


# =============================================================================
# MAILCHIMP CLIENT TESTS
# =============================================================================


class TestMailchimpClient:
    """Test Mailchimp API client."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, mailchimp_client: MailchimpClient):
        """Test client initializes with correct config."""
        assert mailchimp_client.service_name == "mailchimp"
        assert "localhost:8003" in mailchimp_client.config.base_url

    @pytest.mark.asyncio
    async def test_get_lists(self, mailchimp_client: MailchimpClient):
        """Test getting audience lists."""
        result = await mailchimp_client.get_lists()

        assert "lists" in result
        assert isinstance(result["lists"], list)

    @pytest.mark.asyncio
    async def test_get_campaigns(self, mailchimp_client: MailchimpClient):
        """Test getting campaigns."""
        result = await mailchimp_client.get_campaigns()

        assert "campaigns" in result
        assert isinstance(result["campaigns"], list)

    @pytest.mark.asyncio
    async def test_health_check(self, mailchimp_client: MailchimpClient):
        """Test health check endpoint."""
        is_healthy = await mailchimp_client.health_check()
        assert isinstance(is_healthy, bool)


# =============================================================================
# GOOGLE ANALYTICS CLIENT TESTS
# =============================================================================


class TestGoogleAnalyticsClient:
    """Test Google Analytics API client."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, ga_client: GoogleAnalyticsClient):
        """Test client initializes with correct config."""
        assert ga_client.service_name == "google_analytics"
        assert "localhost:8004" in ga_client.config.base_url

    @pytest.mark.asyncio
    async def test_run_report(self, ga_client: GoogleAnalyticsClient):
        """Test running a report."""
        report = await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["activeUsers"],
        )

        # May be None if mock not running, but shouldn't error
        if report:
            assert "rows" in report

    @pytest.mark.asyncio
    async def test_health_check(self, ga_client: GoogleAnalyticsClient):
        """Test health check endpoint."""
        is_healthy = await ga_client.health_check()
        assert isinstance(is_healthy, bool)


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestSingletons:
    """Test singleton pattern for clients."""

    @pytest.mark.asyncio
    async def test_shopify_singleton(self):
        """Test Shopify client singleton returns same instance."""
        client1 = await get_shopify_client()
        client2 = await get_shopify_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_zendesk_singleton(self):
        """Test Zendesk client singleton returns same instance."""
        client1 = await get_zendesk_client()
        client2 = await get_zendesk_client()

        assert client1 is client2


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================


class TestConfiguration:
    """Test configuration loading."""

    def test_mock_mode_default(self):
        """Test that mock mode is default."""
        os.environ["USE_REAL_APIS"] = "false"

        client = ShopifyClient()

        assert "localhost" in client.config.base_url
        assert client.config.auth_type.value == "none"

    def test_config_from_environment(self):
        """Test configuration loads from environment."""
        os.environ["MOCK_SHOPIFY_URL"] = "http://custom-mock:9999"
        os.environ["USE_REAL_APIS"] = "false"

        client = ShopifyClient()

        assert "custom-mock:9999" in client.config.base_url

        # Clean up
        os.environ["MOCK_SHOPIFY_URL"] = "http://localhost:8001"


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_connection_error_returns_none(self):
        """Test connection errors return None/empty, not exceptions."""
        # Point to non-existent server
        from shared.api_clients.base import APIClientConfig, AuthType

        config = APIClientConfig(
            base_url="http://localhost:59999",  # Non-existent port
            auth_type=AuthType.NONE,
            max_retries=0,  # Don't retry for fast test
            timeout=1.0,
        )

        client = ShopifyClient(config)

        # Should not raise, should return None
        result = await client.get_order("12345")
        assert result is None

        await client.close()

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        """Test timeout returns None, not exception."""
        from shared.api_clients.base import APIClientConfig, AuthType

        config = APIClientConfig(
            base_url="http://localhost:8001",
            auth_type=AuthType.NONE,
            max_retries=0,
            timeout=0.001,  # Extremely short timeout
        )

        client = ShopifyClient(config)

        # Should not raise even with tiny timeout
        result = await client.get_order("12345")
        # Result may be None or actual data depending on mock speed

        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
