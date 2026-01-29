# ============================================================================
# Unit Tests for Google Analytics API Client
# ============================================================================
# Purpose: Test Google Analytics Data API (GA4) client for analytics integration
#
# Test Categories:
# 1. Client Initialization - Verify client setup and config
# 2. Report Generation - Standard and real-time reports
# 3. Convenience Reports - Traffic, e-commerce, channel, journey
# 4. Response Formatting - GA4 response transformation
# 5. Metadata Operations - Dimensions and metrics discovery
# 6. Health Check - API availability checks
# 7. Singleton Pattern - Client reuse and shutdown
#
# Related Documentation:
# - GA Client: shared/api_clients/google_analytics.py
# - GA4 API Reference: https://developers.google.com/analytics/devguides/reporting/data/v1
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
from datetime import datetime, timedelta

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.api_clients.google_analytics import (
    GoogleAnalyticsClient,
    get_google_analytics_client,
    shutdown_google_analytics_client,
)
from shared.api_clients.base import APIClientConfig, AuthType, APIResponse


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def ga_client():
    """Create a Google Analytics client for testing."""
    return GoogleAnalyticsClient()


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
def sample_report_response():
    """Sample GA4 report response data."""
    return {
        "rows": [
            {
                "dimensionValues": [{"value": "2026-01-25"}, {"value": "/home"}],
                "metricValues": [{"value": "1234"}, {"value": "5678"}],
            },
            {
                "dimensionValues": [{"value": "2026-01-26"}, {"value": "/products"}],
                "metricValues": [{"value": "2345"}, {"value": "6789"}],
            },
        ],
        "rowCount": 2,
        "metadata": {"currencyCode": "USD"},
    }


@pytest.fixture
def sample_realtime_response():
    """Sample GA4 real-time report response."""
    return {
        "rows": [
            {
                "dimensionValues": [{"value": "page_view"}],
                "metricValues": [{"value": "42"}],
            },
            {
                "dimensionValues": [{"value": "click"}],
                "metricValues": [{"value": "15"}],
            },
        ],
        "rowCount": 2,
    }


@pytest.fixture
def sample_metadata_response():
    """Sample GA4 metadata response."""
    return {
        "dimensions": [
            {"apiName": "date"},
            {"apiName": "pagePath"},
            {"apiName": "country"},
            {"apiName": "sessionSource"},
        ],
        "metrics": [
            {"apiName": "activeUsers"},
            {"apiName": "sessions"},
            {"apiName": "totalRevenue"},
            {"apiName": "conversions"},
        ],
    }


# =============================================================================
# Test: Client Initialization
# =============================================================================


class TestClientInitialization:
    """Tests for Google Analytics client initialization."""

    def test_service_name(self, ga_client):
        """Verify service name is correct."""
        assert ga_client.service_name == "google_analytics"

    def test_default_config_mock_mode(self, ga_client):
        """Verify default config uses mock API."""
        config = ga_client._default_config()
        assert "localhost:8004" in config.base_url
        assert config.auth_type == AuthType.NONE

    @patch.dict(
        os.environ,
        {
            "USE_REAL_APIS": "true",
            "GOOGLE_ANALYTICS_CREDENTIALS_JSON": '{"type": "service_account"}',
        },
    )
    def test_real_api_config(self):
        """Verify real API config from environment."""
        client = GoogleAnalyticsClient()
        config = client._default_config()
        assert "analyticsdata.googleapis.com" in config.base_url
        assert config.auth_type == AuthType.OAUTH2
        assert config.rate_limit_per_second == 10.0

    @patch.dict(os.environ, {"USE_REAL_APIS": "true"}, clear=False)
    def test_real_api_without_credentials_falls_back_to_mock(self):
        """Verify fallback to mock when credentials not set."""
        env_backup = os.environ.get("GOOGLE_ANALYTICS_CREDENTIALS_JSON")
        if "GOOGLE_ANALYTICS_CREDENTIALS_JSON" in os.environ:
            del os.environ["GOOGLE_ANALYTICS_CREDENTIALS_JSON"]

        try:
            client = GoogleAnalyticsClient()
            config = client._default_config()
            assert "localhost" in config.base_url
        finally:
            if env_backup:
                os.environ["GOOGLE_ANALYTICS_CREDENTIALS_JSON"] = env_backup

    @patch.dict(os.environ, {"MOCK_GOOGLE_ANALYTICS_URL": "http://custom-mock:9004"})
    def test_custom_mock_url(self):
        """Verify custom mock URL from environment."""
        client = GoogleAnalyticsClient()
        config = client._default_config()
        assert config.base_url == "http://custom-mock:9004"


# =============================================================================
# Test: Auth Headers
# =============================================================================


class TestAuthHeaders:
    """Tests for authentication header building."""

    def test_build_auth_headers_no_auth(self, ga_client):
        """Verify no headers when no auth configured."""
        ga_client.config = APIClientConfig(
            base_url="http://localhost",
            auth_type=AuthType.NONE,
        )
        headers = ga_client._build_auth_headers()
        assert headers == {}

    def test_build_auth_headers_oauth2_without_token(self, ga_client):
        """Verify empty headers when OAuth2 but no token available."""
        ga_client.config = APIClientConfig(
            base_url="http://localhost",
            auth_type=AuthType.OAUTH2,
        )
        # _get_oauth_token will return None since google-auth might not be available
        headers = ga_client._build_auth_headers()
        assert "Authorization" not in headers or headers == {}


# =============================================================================
# Test: Run Report
# =============================================================================


class TestRunReport:
    """Tests for standard report generation."""

    @pytest.mark.asyncio
    async def test_run_report_success(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify successful report generation."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        result = await ga_client.run_report(
            property_id="123456789",
            dimensions=["date", "pagePath"],
            metrics=["activeUsers", "sessions"],
        )

        assert result is not None
        assert "rows" in result
        assert len(result["rows"]) == 2
        assert result["row_count"] == 2
        assert result["dimensions"] == ["date", "pagePath"]
        assert result["metrics"] == ["activeUsers", "sessions"]

    @pytest.mark.asyncio
    async def test_run_report_with_date_range(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify date range parameters are passed."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["sessions"],
            date_range_start="2026-01-01",
            date_range_end="2026-01-31",
        )

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        assert json_data["dateRanges"][0]["startDate"] == "2026-01-01"
        assert json_data["dateRanges"][0]["endDate"] == "2026-01-31"

    @pytest.mark.asyncio
    async def test_run_report_default_date_range(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify default date range is last 30 days."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["sessions"],
        )

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]

        # Should have date ranges
        assert "dateRanges" in json_data
        date_range = json_data["dateRanges"][0]

        # End date should be today
        expected_end = datetime.now().strftime("%Y-%m-%d")
        assert date_range["endDate"] == expected_end

        # Start date should be 30 days ago
        expected_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert date_range["startDate"] == expected_start

    @pytest.mark.asyncio
    async def test_run_report_with_dimension_filter(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify dimension filter is included."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        dimension_filter = {
            "filter": {"fieldName": "country", "stringFilter": {"value": "US"}}
        }

        await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["sessions"],
            dimension_filter=dimension_filter,
        )

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        assert "dimensionFilter" in json_data
        assert json_data["dimensionFilter"] == dimension_filter

    @pytest.mark.asyncio
    async def test_run_report_with_metric_filter(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify metric filter is included."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        metric_filter = {
            "filter": {
                "fieldName": "sessions",
                "numericFilter": {"operation": "GREATER_THAN", "value": {"int64Value": 100}},
            }
        }

        await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["sessions"],
            metric_filter=metric_filter,
        )

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        assert "metricFilter" in json_data
        assert json_data["metricFilter"] == metric_filter

    @pytest.mark.asyncio
    async def test_run_report_with_limit(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify limit parameter is passed."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["sessions"],
            limit=50,
        )

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        assert json_data["limit"] == 50

    @pytest.mark.asyncio
    async def test_run_report_error(self, ga_client, mock_api_response):
        """Verify error handling."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["sessions"],
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_run_report_endpoint_format(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify correct endpoint is called."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["sessions"],
        )

        call_args = ga_client.post.call_args
        endpoint = call_args[0][0]
        assert "/properties/123456789:runReport" == endpoint


# =============================================================================
# Test: Run Real-time Report
# =============================================================================


class TestRunRealtimeReport:
    """Tests for real-time report generation."""

    @pytest.mark.asyncio
    async def test_run_realtime_report_success(
        self, ga_client, mock_api_response, sample_realtime_response
    ):
        """Verify successful real-time report generation."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_realtime_response)
        )

        result = await ga_client.run_realtime_report(
            property_id="123456789",
            dimensions=["eventName"],
            metrics=["activeUsers"],
        )

        assert result is not None
        assert "rows" in result
        assert len(result["rows"]) == 2

    @pytest.mark.asyncio
    async def test_run_realtime_report_default_dimensions_metrics(
        self, ga_client, mock_api_response, sample_realtime_response
    ):
        """Verify default dimensions and metrics."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_realtime_response)
        )

        await ga_client.run_realtime_report(property_id="123456789")

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]

        # Default should be eventName dimension and activeUsers metric
        assert json_data["dimensions"][0]["name"] == "eventName"
        assert json_data["metrics"][0]["name"] == "activeUsers"

    @pytest.mark.asyncio
    async def test_run_realtime_report_with_limit(
        self, ga_client, mock_api_response, sample_realtime_response
    ):
        """Verify limit parameter is passed."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_realtime_response)
        )

        await ga_client.run_realtime_report(property_id="123456789", limit=25)

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        assert json_data["limit"] == 25

    @pytest.mark.asyncio
    async def test_run_realtime_report_error(self, ga_client, mock_api_response):
        """Verify error handling."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await ga_client.run_realtime_report(property_id="123456789")

        assert result is None

    @pytest.mark.asyncio
    async def test_run_realtime_report_endpoint_format(
        self, ga_client, mock_api_response, sample_realtime_response
    ):
        """Verify correct endpoint is called."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_realtime_response)
        )

        await ga_client.run_realtime_report(property_id="123456789")

        call_args = ga_client.post.call_args
        endpoint = call_args[0][0]
        assert "/properties/123456789:runRealtimeReport" == endpoint


# =============================================================================
# Test: Response Formatting
# =============================================================================


class TestResponseFormatting:
    """Tests for GA4 response formatting."""

    def test_format_report_response_basic(self, ga_client, sample_report_response):
        """Verify basic response formatting."""
        result = ga_client._format_report_response(
            sample_report_response, ["date", "pagePath"], ["activeUsers", "sessions"]
        )

        assert len(result["rows"]) == 2
        assert result["rows"][0]["date"] == "2026-01-25"
        assert result["rows"][0]["pagePath"] == "/home"
        assert result["rows"][0]["activeUsers"] == "1234"
        assert result["rows"][0]["sessions"] == "5678"

    def test_format_report_response_preserves_metadata(
        self, ga_client, sample_report_response
    ):
        """Verify metadata is preserved."""
        result = ga_client._format_report_response(
            sample_report_response, ["date", "pagePath"], ["activeUsers", "sessions"]
        )

        assert result["metadata"] == {"currencyCode": "USD"}

    def test_format_report_response_row_count(self, ga_client, sample_report_response):
        """Verify row count is included."""
        result = ga_client._format_report_response(
            sample_report_response, ["date", "pagePath"], ["activeUsers", "sessions"]
        )

        assert result["row_count"] == 2

    def test_format_report_response_dimensions_metrics_list(
        self, ga_client, sample_report_response
    ):
        """Verify dimensions and metrics lists are included."""
        result = ga_client._format_report_response(
            sample_report_response, ["date", "pagePath"], ["activeUsers", "sessions"]
        )

        assert result["dimensions"] == ["date", "pagePath"]
        assert result["metrics"] == ["activeUsers", "sessions"]

    def test_format_report_response_empty_rows(self, ga_client):
        """Verify empty response is handled."""
        empty_response = {"rows": [], "rowCount": 0}
        result = ga_client._format_report_response(empty_response, ["date"], ["sessions"])

        assert result["rows"] == []
        assert result["row_count"] == 0

    def test_format_report_response_missing_rows(self, ga_client):
        """Verify missing rows key is handled."""
        response = {"metadata": {}}
        result = ga_client._format_report_response(response, ["date"], ["sessions"])

        assert result["rows"] == []


# =============================================================================
# Test: Convenience Report Methods
# =============================================================================


class TestConvenienceReports:
    """Tests for convenience report methods."""

    @pytest.mark.asyncio
    async def test_get_traffic_report_success(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify traffic report generation."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        result = await ga_client.get_traffic_report(property_id="123456789", days=7)

        assert result is not None
        # Verify correct metrics are requested
        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        metric_names = [m["name"] for m in json_data["metrics"]]
        assert "activeUsers" in metric_names
        assert "sessions" in metric_names
        assert "screenPageViews" in metric_names
        assert "bounceRate" in metric_names

    @pytest.mark.asyncio
    async def test_get_ecommerce_report_success(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify e-commerce report generation."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        result = await ga_client.get_ecommerce_report(property_id="123456789", days=30)

        assert result is not None
        # Verify correct metrics are requested
        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        metric_names = [m["name"] for m in json_data["metrics"]]
        assert "totalRevenue" in metric_names
        assert "purchaseRevenue" in metric_names
        assert "ecommercePurchases" in metric_names
        assert "purchaserConversionRate" in metric_names

    @pytest.mark.asyncio
    async def test_get_channel_report_success(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify channel report generation."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        result = await ga_client.get_channel_report(property_id="123456789", days=14)

        assert result is not None
        # Verify correct dimensions are requested
        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        dimension_names = [d["name"] for d in json_data["dimensions"]]
        assert "sessionSource" in dimension_names
        assert "sessionMedium" in dimension_names

    @pytest.mark.asyncio
    async def test_get_customer_journey_report_success(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify customer journey report generation."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        result = await ga_client.get_customer_journey_report(
            property_id="123456789", days=30
        )

        assert result is not None
        # Verify correct dimensions are requested
        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        dimension_names = [d["name"] for d in json_data["dimensions"]]
        assert "landingPage" in dimension_names
        assert "sessionDefaultChannelGroup" in dimension_names

    @pytest.mark.asyncio
    async def test_get_active_users_success(self, ga_client, mock_api_response):
        """Verify active users retrieval."""
        realtime_response = {
            "rows": [
                {
                    "dimensionValues": [],
                    "metricValues": [{"value": "42"}],
                }
            ],
            "rowCount": 1,
        }
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=realtime_response)
        )

        result = await ga_client.get_active_users(property_id="123456789")

        assert result == 42

    @pytest.mark.asyncio
    async def test_get_active_users_empty_response(self, ga_client, mock_api_response):
        """Verify active users returns 0 for empty response."""
        empty_response = {"rows": [], "rowCount": 0}
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=empty_response)
        )

        result = await ga_client.get_active_users(property_id="123456789")

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_active_users_error(self, ga_client, mock_api_response):
        """Verify active users returns 0 on error."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await ga_client.get_active_users(property_id="123456789")

        assert result == 0


# =============================================================================
# Test: Metadata Operations
# =============================================================================


class TestMetadataOperations:
    """Tests for metadata operations."""

    @pytest.mark.asyncio
    async def test_get_metadata_success(
        self, ga_client, mock_api_response, sample_metadata_response
    ):
        """Verify metadata retrieval."""
        ga_client.get = AsyncMock(
            return_value=mock_api_response(data=sample_metadata_response)
        )

        result = await ga_client.get_metadata(property_id="123456789")

        assert result is not None
        assert "dimensions" in result
        assert "metrics" in result
        assert "date" in result["dimensions"]
        assert "activeUsers" in result["metrics"]

    @pytest.mark.asyncio
    async def test_get_metadata_endpoint_format(
        self, ga_client, mock_api_response, sample_metadata_response
    ):
        """Verify correct endpoint is called."""
        ga_client.get = AsyncMock(
            return_value=mock_api_response(data=sample_metadata_response)
        )

        await ga_client.get_metadata(property_id="123456789")

        call_args = ga_client.get.call_args
        endpoint = call_args[0][0]
        assert endpoint == "/properties/123456789/metadata"

    @pytest.mark.asyncio
    async def test_get_metadata_error(self, ga_client, mock_api_response):
        """Verify error handling."""
        ga_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="Not found")
        )

        result = await ga_client.get_metadata(property_id="123456789")

        assert result is None


# =============================================================================
# Test: Health Check
# =============================================================================


class TestHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success_properties_endpoint(
        self, ga_client, mock_api_response
    ):
        """Verify health check with properties endpoint."""
        ga_client.get = AsyncMock(
            return_value=mock_api_response(data={"properties": []})
        )

        result = await ga_client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_fallback_to_health(self, ga_client, mock_api_response):
        """Verify fallback to /health endpoint for mock API."""
        ga_client.get = AsyncMock(
            side_effect=[
                mock_api_response(success=False),  # /properties fails
                mock_api_response(success=True),  # /health succeeds
            ]
        )

        result = await ga_client.health_check()

        assert result is True
        assert ga_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_both_fail(self, ga_client, mock_api_response):
        """Verify health check failure when both endpoints fail."""
        ga_client.get = AsyncMock(
            side_effect=[
                mock_api_response(success=False),
                mock_api_response(success=False),
            ]
        )

        result = await ga_client.health_check()

        assert result is False


# =============================================================================
# Test: Singleton Pattern
# =============================================================================


class TestSingletonPattern:
    """Tests for singleton client pattern."""

    @pytest.mark.asyncio
    async def test_get_google_analytics_client_returns_client(self):
        """Verify get_google_analytics_client returns a client."""
        import shared.api_clients.google_analytics as ga_module

        ga_module._client_instance = None

        client = await get_google_analytics_client()

        assert client is not None
        assert isinstance(client, GoogleAnalyticsClient)

    @pytest.mark.asyncio
    async def test_get_google_analytics_client_singleton(self):
        """Verify same instance is returned."""
        import shared.api_clients.google_analytics as ga_module

        ga_module._client_instance = None

        client1 = await get_google_analytics_client()
        client2 = await get_google_analytics_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_shutdown_google_analytics_client(self):
        """Verify shutdown clears singleton."""
        import shared.api_clients.google_analytics as ga_module

        ga_module._client_instance = None
        client = await get_google_analytics_client()
        client.close = AsyncMock()

        await shutdown_google_analytics_client()

        assert ga_module._client_instance is None
        client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_when_no_client(self):
        """Verify shutdown handles no client gracefully."""
        import shared.api_clients.google_analytics as ga_module

        ga_module._client_instance = None

        # Should not raise
        await shutdown_google_analytics_client()


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_dimensions(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify empty dimensions list is handled."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        # Empty dimensions might be valid for some aggregate queries
        await ga_client.run_report(
            property_id="123456789",
            dimensions=[],
            metrics=["sessions"],
        )

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        assert json_data["dimensions"] == []

    @pytest.mark.asyncio
    async def test_empty_metrics(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify empty metrics list is handled."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        # Empty metrics might be valid for some dimension-only queries
        await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=[],
        )

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        assert json_data["metrics"] == []

    @pytest.mark.asyncio
    async def test_special_property_id_format(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify property ID with various formats."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        # Property IDs can be numeric strings
        await ga_client.run_report(
            property_id="properties/123456789",
            dimensions=["date"],
            metrics=["sessions"],
        )

        call_args = ga_client.post.call_args
        endpoint = call_args[0][0]
        assert "properties/123456789" in endpoint

    @pytest.mark.asyncio
    async def test_many_dimensions_and_metrics(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify handling of multiple dimensions and metrics."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        dimensions = ["date", "pagePath", "country", "city", "deviceCategory"]
        metrics = ["activeUsers", "sessions", "bounceRate", "conversions", "totalRevenue"]

        await ga_client.run_report(
            property_id="123456789",
            dimensions=dimensions,
            metrics=metrics,
        )

        call_args = ga_client.post.call_args
        json_data = call_args[1]["json_data"]
        assert len(json_data["dimensions"]) == 5
        assert len(json_data["metrics"]) == 5

    @pytest.mark.asyncio
    async def test_unicode_in_filter(
        self, ga_client, mock_api_response, sample_report_response
    ):
        """Verify unicode characters in filter values."""
        ga_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_report_response)
        )

        dimension_filter = {
            "filter": {"fieldName": "pagePath", "stringFilter": {"value": "/página"}}
        }

        # Should not raise
        await ga_client.run_report(
            property_id="123456789",
            dimensions=["date"],
            metrics=["sessions"],
            dimension_filter=dimension_filter,
        )

    def test_format_report_mismatched_dimensions(self, ga_client):
        """Verify handling when response has more values than expected dimensions."""
        response = {
            "rows": [
                {
                    "dimensionValues": [
                        {"value": "2026-01-25"},
                        {"value": "/home"},
                        {"value": "extra"},
                    ],
                    "metricValues": [{"value": "1234"}],
                }
            ],
            "rowCount": 1,
        }

        # Only requesting 2 dimensions, but response has 3
        result = ga_client._format_report_response(
            response, ["date", "pagePath"], ["sessions"]
        )

        # Should only include the expected dimensions
        assert result["rows"][0]["date"] == "2026-01-25"
        assert result["rows"][0]["pagePath"] == "/home"
        assert "extra" not in result["rows"][0]
