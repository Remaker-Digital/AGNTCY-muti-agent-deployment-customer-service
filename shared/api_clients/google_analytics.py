"""
Google Analytics API Client for AGNTCY Multi-Agent Customer Service Platform

Provides async HTTP client for Google Analytics Data API (GA4) integration.

Phase 1-3: Mock API (http://localhost:8004)
Phase 4-5: Real GA4 API (https://analyticsdata.googleapis.com/v1beta)

Features:
- Standard and real-time report generation
- Dimension and metric queries
- E-commerce analytics
- Customer journey analysis

API Reference: https://developers.google.com/analytics/devguides/reporting/data/v1
Rate Limits: 10,000 requests per day, 10 QPS per user
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from .base import BaseAPIClient, APIClientConfig, AuthType

logger = logging.getLogger(__name__)

# Singleton instance
_client_instance: Optional["GoogleAnalyticsClient"] = None


class GoogleAnalyticsClient(BaseAPIClient):
    """
    Async HTTP client for Google Analytics Data API (GA4).

    Supports both mock (Phase 1-3) and real API (Phase 4-5) modes.

    Usage:
        client = await get_google_analytics_client()
        report = await client.run_report(
            property_id="123456789",
            dimensions=["date", "pagePath"],
            metrics=["activeUsers", "sessions"]
        )
    """

    @property
    def service_name(self) -> str:
        return "google_analytics"

    def _default_config(self) -> APIClientConfig:
        """Create default config from environment."""
        use_real = os.getenv("USE_REAL_APIS", "false").lower() == "true"

        if use_real and os.getenv("GOOGLE_ANALYTICS_CREDENTIALS_JSON"):
            # Real Google Analytics API
            return APIClientConfig(
                base_url="https://analyticsdata.googleapis.com/v1beta",
                auth_type=AuthType.OAUTH2,
                rate_limit_per_second=10.0,
            )
        else:
            # Mock API
            return APIClientConfig(
                base_url=os.getenv(
                    "MOCK_GOOGLE_ANALYTICS_URL", "http://localhost:8004"
                ),
                auth_type=AuthType.NONE,
                rate_limit_per_second=0,
            )

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build Google OAuth2 authentication headers."""
        headers = {}

        if self.config.auth_type == AuthType.OAUTH2:
            # For real API, we need to get OAuth2 token
            token = self._get_oauth_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"

        return headers

    def _get_oauth_token(self) -> Optional[str]:
        """
        Get OAuth2 access token from service account credentials.

        Uses google-auth library for token generation.
        Tokens are cached and refreshed automatically.
        """
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            # Load credentials from JSON file or environment variable
            creds_json = os.getenv("GOOGLE_ANALYTICS_CREDENTIALS_JSON")
            if creds_json:
                if os.path.isfile(creds_json):
                    credentials = service_account.Credentials.from_service_account_file(
                        creds_json,
                        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
                    )
                else:
                    # JSON string in environment variable
                    creds_data = json.loads(creds_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_data,
                        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
                    )

                # Refresh token if needed
                if not credentials.valid:
                    credentials.refresh(Request())

                return credentials.token

        except ImportError:
            self.logger.warning(
                "google-auth package not installed. "
                "Install with: pip install google-auth google-auth-oauthlib"
            )
        except Exception as e:
            self.logger.error(f"Failed to get OAuth token: {e}")

        return None

    # =========================================================================
    # REPORT METHODS
    # =========================================================================

    async def run_report(
        self,
        property_id: str,
        dimensions: List[str],
        metrics: List[str],
        date_range_start: Optional[str] = None,
        date_range_end: Optional[str] = None,
        dimension_filter: Optional[Dict[str, Any]] = None,
        metric_filter: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """
        Run a standard GA4 report.

        Args:
            property_id: GA4 property ID (e.g., "123456789")
            dimensions: List of dimension names (e.g., ["date", "pagePath"])
            metrics: List of metric names (e.g., ["activeUsers", "sessions"])
            date_range_start: Start date (YYYY-MM-DD, default: 30 days ago)
            date_range_end: End date (YYYY-MM-DD, default: today)
            dimension_filter: Optional dimension filter
            metric_filter: Optional metric filter
            limit: Max rows to return (default 100)

        Returns:
            Report data with rows, dimension/metric headers

        API: POST /v1beta/properties/{property}/runReport

        Common Dimensions:
        - date, dateHour, dateHourMinute
        - pagePath, pageTitle, landingPage
        - country, city, region
        - deviceCategory, browser, operatingSystem
        - sessionSource, sessionMedium, sessionCampaignName
        - firstUserSource, firstUserMedium

        Common Metrics:
        - activeUsers, newUsers, totalUsers
        - sessions, engagedSessions, bounceRate
        - screenPageViews, eventCount
        - averageSessionDuration, engagementRate
        - conversions, totalRevenue, purchaseRevenue
        """
        # Set default date range (last 30 days)
        if not date_range_start:
            date_range_start = (datetime.now() - timedelta(days=30)).strftime(
                "%Y-%m-%d"
            )
        if not date_range_end:
            date_range_end = datetime.now().strftime("%Y-%m-%d")

        report_request = {
            "dateRanges": [
                {
                    "startDate": date_range_start,
                    "endDate": date_range_end,
                }
            ],
            "dimensions": [{"name": d} for d in dimensions],
            "metrics": [{"name": m} for m in metrics],
            "limit": limit,
        }

        if dimension_filter:
            report_request["dimensionFilter"] = dimension_filter
        if metric_filter:
            report_request["metricFilter"] = metric_filter

        response = await self.post(
            f"/properties/{property_id}:runReport", json_data=report_request
        )

        if response.success and response.data:
            return self._format_report_response(response.data, dimensions, metrics)
        else:
            self.logger.error(f"Report failed: {response.error}")
            return None

    async def run_realtime_report(
        self,
        property_id: str,
        dimensions: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        limit: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """
        Run a real-time GA4 report.

        Args:
            property_id: GA4 property ID
            dimensions: Dimension names (default: eventName)
            metrics: Metric names (default: activeUsers)
            limit: Max rows to return

        Returns:
            Real-time report data

        API: POST /v1beta/properties/{property}:runRealtimeReport

        Real-time Dimensions:
        - eventName, unifiedScreenName
        - country, city
        - platform, deviceCategory

        Real-time Metrics:
        - activeUsers
        - screenPageViews
        - eventCount
        """
        if not dimensions:
            dimensions = ["eventName"]
        if not metrics:
            metrics = ["activeUsers"]

        report_request = {
            "dimensions": [{"name": d} for d in dimensions],
            "metrics": [{"name": m} for m in metrics],
            "limit": limit,
        }

        response = await self.post(
            f"/properties/{property_id}:runRealtimeReport", json_data=report_request
        )

        if response.success and response.data:
            return self._format_report_response(response.data, dimensions, metrics)
        else:
            self.logger.error(f"Realtime report failed: {response.error}")
            return None

    def _format_report_response(
        self, data: Dict[str, Any], dimensions: List[str], metrics: List[str]
    ) -> Dict[str, Any]:
        """Format GA4 report response into a more usable structure."""
        rows = []

        for row in data.get("rows", []):
            formatted_row = {}

            # Add dimensions
            for i, dim_value in enumerate(row.get("dimensionValues", [])):
                if i < len(dimensions):
                    formatted_row[dimensions[i]] = dim_value.get("value")

            # Add metrics
            for i, metric_value in enumerate(row.get("metricValues", [])):
                if i < len(metrics):
                    formatted_row[metrics[i]] = metric_value.get("value")

            rows.append(formatted_row)

        return {
            "rows": rows,
            "row_count": data.get("rowCount", len(rows)),
            "dimensions": dimensions,
            "metrics": metrics,
            "metadata": data.get("metadata", {}),
        }

    # =========================================================================
    # CONVENIENCE REPORT METHODS
    # =========================================================================

    async def get_traffic_report(
        self,
        property_id: str,
        days: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a traffic overview report.

        Args:
            property_id: GA4 property ID
            days: Number of days to include

        Returns:
            Traffic report with users, sessions, pageviews
        """
        date_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        return await self.run_report(
            property_id=property_id,
            dimensions=["date"],
            metrics=["activeUsers", "sessions", "screenPageViews", "bounceRate"],
            date_range_start=date_start,
            limit=days,
        )

    async def get_ecommerce_report(
        self,
        property_id: str,
        days: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Get an e-commerce performance report.

        Args:
            property_id: GA4 property ID
            days: Number of days to include

        Returns:
            E-commerce report with revenue, transactions, conversion rate
        """
        date_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        return await self.run_report(
            property_id=property_id,
            dimensions=["date"],
            metrics=[
                "totalRevenue",
                "purchaseRevenue",
                "ecommercePurchases",
                "addToCarts",
                "purchaserConversionRate",
            ],
            date_range_start=date_start,
            limit=days,
        )

    async def get_channel_report(
        self,
        property_id: str,
        days: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a channel/source breakdown report.

        Args:
            property_id: GA4 property ID
            days: Number of days to include

        Returns:
            Channel report with traffic by source/medium
        """
        date_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        return await self.run_report(
            property_id=property_id,
            dimensions=["sessionSource", "sessionMedium"],
            metrics=["activeUsers", "sessions", "conversions", "totalRevenue"],
            date_range_start=date_start,
            limit=50,
        )

    async def get_customer_journey_report(
        self,
        property_id: str,
        days: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a customer journey report.

        Args:
            property_id: GA4 property ID
            days: Number of days to include

        Returns:
            Report with landing pages, user flow, conversion paths
        """
        date_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        return await self.run_report(
            property_id=property_id,
            dimensions=["landingPage", "sessionDefaultChannelGroup"],
            metrics=["sessions", "engagedSessions", "conversions", "engagementRate"],
            date_range_start=date_start,
            limit=50,
        )

    async def get_active_users(self, property_id: str) -> int:
        """
        Get current active users (real-time).

        Args:
            property_id: GA4 property ID

        Returns:
            Number of active users
        """
        report = await self.run_realtime_report(
            property_id=property_id,
            dimensions=[],
            metrics=["activeUsers"],
        )

        if report and report.get("rows"):
            return int(report["rows"][0].get("activeUsers", 0))
        return 0

    # =========================================================================
    # METADATA METHODS
    # =========================================================================

    async def get_metadata(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Get available dimensions and metrics for a property.

        Args:
            property_id: GA4 property ID

        Returns:
            Metadata with available dimensions and metrics

        API: GET /v1beta/properties/{property}/metadata
        """
        response = await self.get(f"/properties/{property_id}/metadata")

        if response.success and response.data:
            return {
                "dimensions": [
                    d.get("apiName") for d in response.data.get("dimensions", [])
                ],
                "metrics": [m.get("apiName") for m in response.data.get("metrics", [])],
            }
        return None

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    async def health_check(self) -> bool:
        """Check if Google Analytics API is reachable."""
        # Try to list properties as health check
        response = await self.get("/properties")
        if response.success:
            return True

        # Fall back to /health for mock API
        response = await self.get("/health")
        return response.success


async def get_google_analytics_client() -> GoogleAnalyticsClient:
    """
    Get singleton Google Analytics client instance.

    Returns:
        GoogleAnalyticsClient instance (reused across calls)
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = GoogleAnalyticsClient()
    return _client_instance


async def shutdown_google_analytics_client():
    """Shutdown the singleton client."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
