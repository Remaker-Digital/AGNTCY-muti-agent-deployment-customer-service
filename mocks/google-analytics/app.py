"""
Mock Google Analytics API for AGNTCY Multi-Agent Customer Service Platform
Phase 1-3: Local development mock service

This mock API simulates Google Analytics Data API (GA4) endpoints needed for:
- Standard analytics reports (traffic, conversions, behavior)
- Real-time user activity monitoring
- E-commerce tracking and performance
- Customer journey analytics

All responses are static JSON fixtures for predictable testing.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Mock Google Analytics API",
    description="Mock Google Analytics Data API (GA4) for development and testing",
    version="1.0.0"
)

# Data directory for JSON fixtures
DATA_DIR = Path("/app/data") if os.path.exists("/app/data") else Path("./data")


def load_fixture(filename: str) -> Dict:
    """Load JSON fixture from data directory."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return {"error": f"Fixture {filename} not found"}

    with open(filepath, "r") as f:
        return json.load(f)


# Pydantic models for request bodies
class DateRange(BaseModel):
    startDate: str  # YYYY-MM-DD format
    endDate: str


class Dimension(BaseModel):
    name: str


class Metric(BaseModel):
    name: str


class RunReportRequest(BaseModel):
    dateRanges: List[DateRange]
    dimensions: Optional[List[Dimension]] = []
    metrics: Optional[List[Metric]] = []
    limit: Optional[int] = 10000


class RunRealtimeReportRequest(BaseModel):
    dimensions: Optional[List[Dimension]] = []
    metrics: Optional[List[Metric]] = []
    limit: Optional[int] = 10000


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root - basic info."""
    return {
        "service": "Mock Google Analytics API",
        "version": "1.0.0",
        "endpoints": [
            "/v1beta/properties/{property}/runReport",
            "/v1beta/properties/{property}/runRealtimeReport"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-google-analytics"}


@app.post("/v1beta/properties/{property}/runReport")
async def run_report(
    property: str,
    request: RunReportRequest,
    authorization: str = Header(None)
):
    """
    Run a standard GA4 report.
    Mock response with analytics data for specified dimensions and metrics.

    Supports multiple report types based on requested dimensions:
    - Standard traffic report (date, pagePath)
    - E-commerce report (date, sessionSource with revenue metrics)
    - Customer journey report (channel, landing page with conversions)
    """
    reports_data = load_fixture("reports.json")

    # Determine which report to return based on dimensions
    dimension_names = [d.name for d in request.dimensions]

    if "sessionSource" in dimension_names or "ecommercePurchases" in [m.name for m in request.metrics]:
        # E-commerce report
        return reports_data.get("ecommerce_report", {})
    elif "sessionDefaultChannelGroup" in dimension_names or "landingPage" in dimension_names:
        # Customer journey report
        return reports_data.get("customer_journey_report", {})
    else:
        # Standard traffic report (default)
        return reports_data.get("standard_report", {})


@app.post("/v1beta/properties/{property}/runRealtimeReport")
async def run_realtime_report(
    property: str,
    request: RunRealtimeReportRequest,
    authorization: str = Header(None)
):
    """
    Run a real-time GA4 report.
    Mock response with current active users and real-time events.

    Important for monitoring:
    - Current site traffic
    - Active user locations
    - Real-time conversion events
    - Cart abandonment in progress
    """
    realtime_data = load_fixture("realtime.json")

    # Determine which real-time report to return
    dimension_names = [d.name for d in request.dimensions]

    if "eventName" in dimension_names:
        # Real-time events report
        return realtime_data.get("realtime_events", {})
    else:
        # Real-time users report (default)
        return realtime_data.get("realtime_report", {})


@app.get("/v1beta/properties/{property}/metadata")
async def get_metadata(
    property: str,
    authorization: str = Header(None)
):
    """
    Get property metadata.
    Mock response with available dimensions and metrics for the property.
    """
    return {
        "name": f"properties/{property}/metadata",
        "dimensions": [
            {"apiName": "date", "uiName": "Date", "description": "The date of the event"},
            {"apiName": "pagePath", "uiName": "Page path", "description": "The path of the page"},
            {"apiName": "country", "uiName": "Country", "description": "User's country"},
            {"apiName": "city", "uiName": "City", "description": "User's city"},
            {"apiName": "sessionSource", "uiName": "Session source", "description": "Traffic source"},
            {"apiName": "sessionDefaultChannelGroup", "uiName": "Channel group", "description": "Default channel"},
            {"apiName": "landingPage", "uiName": "Landing page", "description": "First page viewed"},
            {"apiName": "eventName", "uiName": "Event name", "description": "Name of the event"}
        ],
        "metrics": [
            {"apiName": "activeUsers", "uiName": "Active users", "description": "Number of active users"},
            {"apiName": "sessions", "uiName": "Sessions", "description": "Number of sessions"},
            {"apiName": "totalUsers", "uiName": "Total users", "description": "Total unique users"},
            {"apiName": "screenPageViews", "uiName": "Views", "description": "Number of page views"},
            {"apiName": "averageSessionDuration", "uiName": "Avg session", "description": "Average session duration"},
            {"apiName": "bounceRate", "uiName": "Bounce rate", "description": "Percentage of bounced sessions"},
            {"apiName": "ecommercePurchases", "uiName": "Purchases", "description": "Number of purchases"},
            {"apiName": "purchaseRevenue", "uiName": "Revenue", "description": "Total purchase revenue"},
            {"apiName": "itemsViewed", "uiName": "Items viewed", "description": "Number of items viewed"},
            {"apiName": "itemsAddedToCart", "uiName": "Cart adds", "description": "Items added to cart"},
            {"apiName": "conversions", "uiName": "Conversions", "description": "Number of conversions"},
            {"apiName": "conversionRate", "uiName": "Conversion rate", "description": "Conversion percentage"},
            {"apiName": "eventCount", "uiName": "Event count", "description": "Number of events"}
        ]
    }


# Additional helper endpoints for testing
@app.get("/v1beta/properties")
async def list_properties(
    authorization: str = Header(None)
):
    """
    List GA4 properties (mock).
    Returns a single mock property for testing.
    """
    return {
        "properties": [
            {
                "name": "properties/123456789",
                "property": "123456789",
                "displayName": "Company Store - Production",
                "industryCategory": "SHOPPING",
                "timeZone": "America/New_York",
                "currencyCode": "USD"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
