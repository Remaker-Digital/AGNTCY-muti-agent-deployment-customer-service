# ============================================================================
# Mock WhatsApp Business Cloud API - Phase 6 Development
# ============================================================================
# Purpose: Mock WhatsApp Cloud API for local development and testing
#
# This mock simulates the WhatsApp Business Cloud API behavior:
# - Send messages (text, template, interactive)
# - Upload media
# - Webhook simulation for testing incoming messages
#
# Usage:
#     uvicorn mocks.whatsapp.app:app --host 0.0.0.0 --port 8011
#
# Or via Docker Compose:
#     docker-compose up mock-whatsapp
#
# Test Accounts:
# - 15551234567: Regular customer (Sarah Johnson)
# - 15559876543: VIP customer (Michael Chen)
# - 15551112222: New customer (no prior conversations)
#
# Related Documentation:
# - WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q1.C)
# ============================================================================

import os
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# Request/Response Models
# =============================================================================


class TextContent(BaseModel):
    body: str
    preview_url: bool = False


class TemplateLanguage(BaseModel):
    code: str = "en_US"


class TemplateParameter(BaseModel):
    type: str = "text"
    text: str


class TemplateComponent(BaseModel):
    type: str
    parameters: List[TemplateParameter] = []


class TemplateContent(BaseModel):
    name: str
    language: TemplateLanguage
    components: List[TemplateComponent] = []


class InteractiveButton(BaseModel):
    type: str = "reply"
    reply: Dict[str, str]


class InteractiveAction(BaseModel):
    buttons: List[InteractiveButton] = []


class InteractiveBody(BaseModel):
    text: str


class InteractiveContent(BaseModel):
    type: str
    body: InteractiveBody
    action: Optional[InteractiveAction] = None


class ImageContent(BaseModel):
    link: Optional[str] = None
    id: Optional[str] = None
    caption: Optional[str] = None


class DocumentContent(BaseModel):
    link: Optional[str] = None
    id: Optional[str] = None
    filename: Optional[str] = None
    caption: Optional[str] = None


class MessageContext(BaseModel):
    message_id: Optional[str] = None


class SendMessageRequest(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str
    text: Optional[TextContent] = None
    template: Optional[TemplateContent] = None
    interactive: Optional[InteractiveContent] = None
    image: Optional[ImageContent] = None
    document: Optional[DocumentContent] = None
    context: Optional[MessageContext] = None
    status: Optional[str] = None  # For mark-as-read requests
    message_id: Optional[str] = None  # For mark-as-read requests


class MessageResponse(BaseModel):
    messaging_product: str = "whatsapp"
    contacts: List[Dict[str, str]]
    messages: List[Dict[str, str]]


class MediaUploadResponse(BaseModel):
    id: str


class MediaUrlResponse(BaseModel):
    url: str
    mime_type: str
    sha256: str
    file_size: int


class SimulateWebhookRequest(BaseModel):
    """Request to simulate an incoming webhook for testing."""

    from_number: str = Field(..., description="Sender phone number")
    message_type: str = Field(default="text", description="Message type")
    text: Optional[str] = Field(default=None, description="Text message body")
    button_reply_id: Optional[str] = Field(default=None, description="Button reply ID")
    button_reply_title: Optional[str] = Field(
        default=None, description="Button reply title"
    )


# =============================================================================
# Mock Data
# =============================================================================

# Simulated customer profiles
MOCK_CUSTOMERS = {
    "15551234567": {
        "name": "Sarah Johnson",
        "wa_id": "15551234567",
        "is_vip": False,
        "email": "sarah.johnson@example.com",
    },
    "15559876543": {
        "name": "Michael Chen",
        "wa_id": "15559876543",
        "is_vip": True,
        "email": "michael.chen@example.com",
    },
    "15551112222": {
        "name": "New Customer",
        "wa_id": "15551112222",
        "is_vip": False,
        "email": None,
    },
}

# Message history for testing
message_history: List[Dict[str, Any]] = []

# Uploaded media storage
uploaded_media: Dict[str, Dict[str, Any]] = {}

# Approved templates (simulate Meta's template approval)
APPROVED_TEMPLATES = {
    "order_confirmation": {
        "name": "order_confirmation",
        "language": "en_US",
        "status": "APPROVED",
        "body": "Hi {{1}}, your order {{2}} for {{3}} has been confirmed!",
    },
    "shipping_update": {
        "name": "shipping_update",
        "language": "en_US",
        "status": "APPROVED",
        "body": "Your order {{1}} shipped via {{2}}. Track: {{3}}",
    },
    "order_status": {
        "name": "order_status",
        "language": "en_US",
        "status": "APPROVED",
        "body": "Order {{1}} status: {{2}}. Estimated delivery: {{3}}",
    },
    "welcome_message": {
        "name": "welcome_message",
        "language": "en_US",
        "status": "APPROVED",
        "body": "Hi {{1}}, welcome to {{2}}! How can we help you today?",
    },
}


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Mock WhatsApp Business Cloud API",
    description="Mock WhatsApp API for local development and testing",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Mock WhatsApp Business Cloud API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/{phone_number_id}/messages", response_model=MessageResponse)
async def send_message(phone_number_id: str, request: SendMessageRequest):
    """
    Send a message via WhatsApp.

    Simulates the /v18.0/{phone_number_id}/messages endpoint.
    """
    logger.info(
        f"Sending {request.type} message to {request.to} "
        f"from phone_number_id={phone_number_id}"
    )

    # Handle mark-as-read requests
    if request.status == "read" and request.message_id:
        logger.info(f"Marking message {request.message_id} as read")
        # Update message in history
        for msg in message_history:
            if msg.get("message_id") == request.message_id:
                msg["status"] = "read"
        return MessageResponse(
            contacts=[{"wa_id": request.to}],
            messages=[{"id": request.message_id}],
        )

    # Validate recipient
    if not request.to:
        raise HTTPException(status_code=400, detail="Missing recipient")

    # Validate message type and content
    if request.type == "text" and not request.text:
        raise HTTPException(status_code=400, detail="Missing text content")

    if request.type == "template" and not request.template:
        raise HTTPException(status_code=400, detail="Missing template content")

    # Check template approval status
    if request.type == "template" and request.template:
        template_name = request.template.name
        if template_name not in APPROVED_TEMPLATES:
            raise HTTPException(
                status_code=400,
                detail=f"Template '{template_name}' not found or not approved",
            )

    # Generate message ID
    message_id = f"wamid.{uuid.uuid4().hex[:24]}"

    # Store message in history
    message_record = {
        "message_id": message_id,
        "to": request.to,
        "type": request.type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "sent",
        "direction": "outbound",
    }

    # Add type-specific content
    if request.text:
        message_record["text"] = request.text.body
    if request.template:
        message_record["template"] = request.template.name
    if request.interactive:
        message_record["interactive_type"] = request.interactive.type
    if request.context:
        message_record["reply_to"] = request.context.message_id

    message_history.append(message_record)

    # Simulate delivery status (would be delivered via webhook in real API)
    logger.info(f"Message sent: {message_id}")

    return MessageResponse(
        contacts=[{"wa_id": request.to}],
        messages=[{"id": message_id}],
    )


@app.post("/{phone_number_id}/media", response_model=MediaUploadResponse)
async def upload_media(phone_number_id: str, request: Request):
    """
    Upload media for sending.

    Simulates the /v18.0/{phone_number_id}/media endpoint.
    """
    # Generate media ID
    media_id = f"media.{uuid.uuid4().hex[:16]}"

    # Store media metadata (not actual file in mock)
    content_type = request.headers.get("content-type", "application/octet-stream")
    uploaded_media[media_id] = {
        "id": media_id,
        "mime_type": content_type,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
    }

    logger.info(f"Media uploaded: {media_id}")
    return MediaUploadResponse(id=media_id)


@app.get("/{media_id}")
async def get_media_url(media_id: str):
    """
    Get download URL for media.

    Simulates the /v18.0/{media_id} endpoint.
    """
    if media_id not in uploaded_media:
        raise HTTPException(status_code=404, detail="Media not found")

    media = uploaded_media[media_id]

    return MediaUrlResponse(
        url=f"https://mock-cdn.whatsapp.net/media/{media_id}",
        mime_type=media.get("mime_type", "application/octet-stream"),
        sha256="mock_sha256_hash",
        file_size=1024,
    )


# =============================================================================
# Test Helper Endpoints (not in real WhatsApp API)
# =============================================================================


@app.get("/test/messages")
async def get_message_history():
    """Get all sent messages (for testing)."""
    return {"messages": message_history, "count": len(message_history)}


@app.delete("/test/messages")
async def clear_message_history():
    """Clear message history (for testing)."""
    message_history.clear()
    return {"status": "cleared"}


@app.get("/test/customers")
async def get_mock_customers():
    """Get mock customer profiles (for testing)."""
    return {"customers": MOCK_CUSTOMERS}


@app.get("/test/templates")
async def get_approved_templates():
    """Get approved message templates (for testing)."""
    return {"templates": APPROVED_TEMPLATES}


@app.post("/test/simulate-webhook")
async def simulate_incoming_webhook(request: SimulateWebhookRequest):
    """
    Simulate an incoming webhook for testing.

    This helps test the webhook handler without setting up actual WhatsApp.
    """
    customer = MOCK_CUSTOMERS.get(request.from_number, {
        "name": "Unknown",
        "wa_id": request.from_number,
    })

    message_id = f"wamid.{uuid.uuid4().hex[:24]}"
    timestamp = int(datetime.utcnow().timestamp())

    # Build message content based on type
    if request.message_type == "text":
        message_content = {
            "from": request.from_number,
            "id": message_id,
            "timestamp": str(timestamp),
            "type": "text",
            "text": {"body": request.text or "Hello!"},
        }
    elif request.message_type == "interactive":
        message_content = {
            "from": request.from_number,
            "id": message_id,
            "timestamp": str(timestamp),
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {
                    "id": request.button_reply_id or "btn_1",
                    "title": request.button_reply_title or "Option 1",
                },
            },
        }
    else:
        message_content = {
            "from": request.from_number,
            "id": message_id,
            "timestamp": str(timestamp),
            "type": request.message_type,
        }

    # Build webhook payload
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "MOCK_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "MOCK_PHONE_NUMBER_ID",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": customer.get("name", "Unknown")},
                                    "wa_id": request.from_number,
                                }
                            ],
                            "messages": [message_content],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    # Store in history as inbound
    message_history.append({
        "message_id": message_id,
        "from": request.from_number,
        "type": request.message_type,
        "content": request.text or request.button_reply_title,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "received",
        "direction": "inbound",
    })

    logger.info(f"Simulated inbound message from {request.from_number}: {message_id}")

    return {
        "status": "simulated",
        "message_id": message_id,
        "webhook_payload": webhook_payload,
    }


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MOCK_WHATSAPP_PORT", "8011"))
    host = os.getenv("MOCK_WHATSAPP_HOST", "0.0.0.0")

    uvicorn.run(app, host=host, port=port)
