"""
Mock Zendesk API for AGNTCY Multi-Agent Customer Service Platform
Phase 1-3: Local development mock service

This mock API simulates Zendesk's Support API endpoints needed for:
- Ticket management (create, read, update)
- User information retrieval
- Ticket comments/conversations
- Escalation workflows

All responses are static JSON fixtures for predictable testing.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Mock Zendesk API",
    description="Mock Zendesk Support API for development and testing",
    version="1.0.0",
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
class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: Optional[str] = "normal"
    type: Optional[str] = "question"
    requester_id: int
    tags: Optional[List[str]] = []


class TicketUpdate(BaseModel):
    subject: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None


class CommentCreate(BaseModel):
    body: str
    public: Optional[bool] = True
    author_id: int


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/")
async def root():
    """API root - basic info."""
    return {
        "service": "Mock Zendesk API",
        "version": "1.0.0",
        "endpoints": [
            "/api/v2/tickets.json",
            "/api/v2/tickets/{ticket_id}.json",
            "/api/v2/users/{user_id}.json",
            "/api/v2/tickets/{ticket_id}/comments.json",
        ],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-zendesk"}


@app.get("/api/v2/tickets.json")
async def get_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=100),
    authorization: str = Header(None),
):
    """
    Get tickets list.
    Mock response with sample support tickets.
    """
    tickets_data = load_fixture("tickets.json")
    tickets = tickets_data.get("tickets", [])

    # Filter by status if provided
    if status:
        tickets = [t for t in tickets if t.get("status") == status]

    # Filter by priority if provided
    if priority:
        tickets = [t for t in tickets if t.get("priority") == priority]

    return {"tickets": tickets, "count": len(tickets)}


@app.get("/api/v2/tickets/{ticket_id}.json")
async def get_ticket(ticket_id: int, authorization: str = Header(None)):
    """Get single ticket by ID."""
    tickets_data = load_fixture("tickets.json")
    tickets = tickets_data.get("tickets", [])

    for ticket in tickets:
        if ticket.get("id") == ticket_id:
            return {"ticket": ticket}

    raise HTTPException(status_code=404, detail="Ticket not found")


@app.post("/api/v2/tickets.json")
async def create_ticket(ticket: TicketCreate, authorization: str = Header(None)):
    """
    Create new ticket.
    Mock response for ticket creation.
    """
    # Generate mock ticket ID
    new_ticket = {
        "id": 9999,  # Mock ID
        "subject": ticket.subject,
        "description": ticket.description,
        "status": "new",
        "priority": ticket.priority,
        "type": ticket.type,
        "requester_id": ticket.requester_id,
        "assignee_id": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "tags": ticket.tags,
    }

    return {"ticket": new_ticket}


@app.put("/api/v2/tickets/{ticket_id}.json")
async def update_ticket(
    ticket_id: int, ticket_update: TicketUpdate, authorization: str = Header(None)
):
    """
    Update existing ticket.
    Mock response for ticket updates (status changes, assignments, etc.)
    """
    # Load existing ticket
    tickets_data = load_fixture("tickets.json")
    tickets = tickets_data.get("tickets", [])

    for ticket in tickets:
        if ticket.get("id") == ticket_id:
            # Update fields that were provided
            if ticket_update.subject:
                ticket["subject"] = ticket_update.subject
            if ticket_update.status:
                ticket["status"] = ticket_update.status
            if ticket_update.priority:
                ticket["priority"] = ticket_update.priority
            if ticket_update.assignee_id is not None:
                ticket["assignee_id"] = ticket_update.assignee_id

            ticket["updated_at"] = datetime.utcnow().isoformat() + "Z"

            return {"ticket": ticket}

    raise HTTPException(status_code=404, detail="Ticket not found")


@app.get("/api/v2/users/{user_id}.json")
async def get_user(user_id: int, authorization: str = Header(None)):
    """
    Get user information by ID.
    Used for customer profile lookup during escalation.
    """
    users_data = load_fixture("users.json")
    users = users_data.get("users", [])

    for user in users:
        if user.get("id") == user_id:
            return {"user": user}

    raise HTTPException(status_code=404, detail="User not found")


@app.post("/api/v2/tickets/{ticket_id}/comments.json")
async def create_comment(
    ticket_id: int, comment: CommentCreate, authorization: str = Header(None)
):
    """
    Add comment to ticket.
    Mock response for adding agent/customer responses.
    """
    # Verify ticket exists
    tickets_data = load_fixture("tickets.json")
    tickets = tickets_data.get("tickets", [])

    ticket_exists = any(t.get("id") == ticket_id for t in tickets)
    if not ticket_exists:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Create mock comment
    new_comment = {
        "id": 8888,  # Mock ID
        "ticket_id": ticket_id,
        "author_id": comment.author_id,
        "body": comment.body,
        "public": comment.public,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    return {"comment": new_comment}


@app.get("/api/v2/tickets/{ticket_id}/comments.json")
async def get_comments(ticket_id: int, authorization: str = Header(None)):
    """
    Get all comments for a ticket.
    Used for conversation history retrieval.
    """
    comments_data = load_fixture("comments.json")
    all_comments = comments_data.get("comments", [])

    # Filter comments for this ticket
    ticket_comments = [c for c in all_comments if c.get("ticket_id") == ticket_id]

    return {"comments": ticket_comments, "count": len(ticket_comments)}


# Webhook simulation endpoint (for future Phase 2/3 testing)
@app.post("/webhooks/tickets/status_change")
async def webhook_ticket_status_changed():
    """Simulate Zendesk webhook for ticket status changes."""
    return {"received": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
