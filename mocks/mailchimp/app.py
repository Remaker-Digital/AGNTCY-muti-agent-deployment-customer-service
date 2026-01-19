"""
Mock Mailchimp API for AGNTCY Multi-Agent Customer Service Platform
Phase 1-3: Local development mock service

This mock API simulates Mailchimp's Marketing API endpoints needed for:
- Campaign performance tracking
- List/audience management
- Automation workflow monitoring
- Email marketing analytics

All responses are static JSON fixtures for predictable testing.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

# Initialize FastAPI app
app = FastAPI(
    title="Mock Mailchimp API",
    description="Mock Mailchimp Marketing API for development and testing",
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
class ListMember(BaseModel):
    email_address: EmailStr
    status: str  # subscribed, unsubscribed, cleaned, pending
    merge_fields: Optional[Dict] = {}
    tags: Optional[List[str]] = []


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root - basic info."""
    return {
        "service": "Mock Mailchimp API",
        "version": "1.0.0",
        "endpoints": [
            "/3.0/campaigns",
            "/3.0/campaigns/{campaign_id}",
            "/3.0/lists",
            "/3.0/lists/{list_id}",
            "/3.0/lists/{list_id}/members",
            "/3.0/automations"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-mailchimp"}


@app.get("/3.0/campaigns")
async def get_campaigns(
    status: Optional[str] = Query(None),
    count: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    authorization: str = Header(None)
):
    """
    Get campaigns list.
    Mock response with email marketing campaigns.
    """
    campaigns_data = load_fixture("campaigns.json")
    campaigns = campaigns_data.get("campaigns", [])

    # Filter by status if provided
    if status:
        campaigns = [c for c in campaigns if c.get("status") == status]

    # Apply pagination
    paginated = campaigns[offset:offset + count]

    return {
        "campaigns": paginated,
        "total_items": len(campaigns)
    }


@app.get("/3.0/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    authorization: str = Header(None)
):
    """
    Get single campaign by ID.
    Used for tracking specific campaign performance.
    """
    campaigns_data = load_fixture("campaigns.json")
    campaigns = campaigns_data.get("campaigns", [])

    for campaign in campaigns:
        if campaign.get("id") == campaign_id:
            return campaign

    raise HTTPException(status_code=404, detail="Campaign not found")


@app.get("/3.0/lists")
async def get_lists(
    count: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    authorization: str = Header(None)
):
    """
    Get audience lists.
    Mock response with subscriber lists/audiences.
    """
    lists_data = load_fixture("lists.json")
    lists = lists_data.get("lists", [])

    # Apply pagination
    paginated = lists[offset:offset + count]

    return {
        "lists": paginated,
        "total_items": len(lists)
    }


@app.get("/3.0/lists/{list_id}")
async def get_list(
    list_id: str,
    authorization: str = Header(None)
):
    """
    Get single list/audience by ID.
    Used for audience analytics and segmentation.
    """
    lists_data = load_fixture("lists.json")
    lists = lists_data.get("lists", [])

    for list_item in lists:
        if list_item.get("id") == list_id:
            return list_item

    raise HTTPException(status_code=404, detail="List not found")


@app.post("/3.0/lists/{list_id}/members")
async def add_list_member(
    list_id: str,
    member: ListMember,
    authorization: str = Header(None)
):
    """
    Add member to list.
    Mock response for subscribing users to email lists.
    Important for cart abandonment campaigns.
    """
    # Verify list exists
    lists_data = load_fixture("lists.json")
    lists = lists_data.get("lists", [])

    list_exists = any(l.get("id") == list_id for l in lists)
    if not list_exists:
        raise HTTPException(status_code=404, detail="List not found")

    # Create mock member response
    new_member = {
        "id": "mock-member-id-12345",
        "email_address": member.email_address,
        "unique_email_id": "mock-unique-email-id",
        "email_type": "html",
        "status": member.status,
        "merge_fields": member.merge_fields,
        "stats": {
            "avg_open_rate": 0.35,
            "avg_click_rate": 0.08
        },
        "ip_signup": "",
        "timestamp_signup": datetime.utcnow().isoformat() + "Z",
        "ip_opt": "",
        "timestamp_opt": datetime.utcnow().isoformat() + "Z",
        "member_rating": 3,
        "last_changed": datetime.utcnow().isoformat() + "Z",
        "language": "en",
        "vip": False,
        "email_client": "",
        "location": {
            "latitude": 0,
            "longitude": 0,
            "gmtoff": 0,
            "dstoff": 0,
            "country_code": "",
            "timezone": ""
        },
        "list_id": list_id,
        "tags": member.tags
    }

    return new_member


@app.get("/3.0/automations")
async def get_automations(
    count: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    authorization: str = Header(None)
):
    """
    Get automation workflows.
    Mock response with email automation sequences.
    Important for tracking automated campaigns like cart abandonment.
    """
    automations_data = load_fixture("automations.json")
    automations = automations_data.get("automations", [])

    # Apply pagination
    paginated = automations[offset:offset + count]

    return {
        "automations": paginated,
        "total_items": len(automations)
    }


@app.get("/3.0/automations/{workflow_id}")
async def get_automation(
    workflow_id: str,
    authorization: str = Header(None)
):
    """
    Get single automation workflow by ID.
    Used for tracking specific automation performance.
    """
    automations_data = load_fixture("automations.json")
    automations = automations_data.get("automations", [])

    for automation in automations:
        if automation.get("id") == workflow_id:
            return automation

    raise HTTPException(status_code=404, detail="Automation not found")


# Webhook simulation endpoint (for future Phase 2/3 testing)
@app.post("/webhooks/subscribe")
async def webhook_subscriber_added():
    """Simulate Mailchimp webhook for new subscriber."""
    return {"received": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
