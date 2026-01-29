# ============================================================================
# WhatsApp Business API Models - Phase 6
# ============================================================================
# Purpose: Data models for WhatsApp Business Cloud API integration
#
# WhatsApp Message Types:
# - TEXT: Plain text messages
# - TEMPLATE: Pre-approved message templates for proactive notifications
# - INTERACTIVE: Buttons, lists, and reply options
# - MEDIA: Images, documents, audio, video
#
# Architecture Decision:
# - Use Meta's Cloud API (hosted solution) rather than on-premise
# - Message templates must be pre-approved by Meta (24-hour response window)
# - Interactive messages provide better UX than plain text
#
# Related Documentation:
# - WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
# - Message Templates: https://developers.facebook.com/docs/whatsapp/message-templates
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q1.C)
#
# Budget Impact:
# - WhatsApp Business API: ~$15-25/month (conversation-based pricing)
# - Business-initiated: ~$0.02-0.10/conversation (varies by country)
# - User-initiated: ~$0.01-0.06/conversation (varies by country)
# ============================================================================

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(str, Enum):
    """
    WhatsApp message types supported by the Cloud API.

    TEXT and TEMPLATE are most commonly used for customer service.
    INTERACTIVE enables rich interactions like quick replies and lists.
    """

    TEXT = "text"  # Plain text message
    TEMPLATE = "template"  # Pre-approved template message
    INTERACTIVE = "interactive"  # Buttons, lists, reply options
    IMAGE = "image"  # Image attachment
    DOCUMENT = "document"  # File attachment (PDF, etc.)
    AUDIO = "audio"  # Voice message
    VIDEO = "video"  # Video attachment
    STICKER = "sticker"  # Sticker message
    LOCATION = "location"  # Location sharing
    CONTACTS = "contacts"  # Contact card


class MessageStatus(str, Enum):
    """
    WhatsApp message delivery status.

    Progression: PENDING → SENT → DELIVERED → READ (or FAILED)

    Status updates received via webhook from WhatsApp.
    """

    PENDING = "pending"  # Message queued for sending
    SENT = "sent"  # Message sent to WhatsApp servers
    DELIVERED = "delivered"  # Message delivered to recipient device
    READ = "read"  # Message read by recipient
    FAILED = "failed"  # Delivery failed


class ConversationType(str, Enum):
    """
    WhatsApp conversation types for billing purposes.

    Pricing varies by conversation type:
    - USER_INITIATED: Customer starts conversation (cheaper)
    - BUSINESS_INITIATED: Business sends proactive message (more expensive)
    - REFERRAL: Conversation from ad click (specific pricing)

    See: https://developers.facebook.com/docs/whatsapp/pricing
    """

    USER_INITIATED = "user_initiated"  # Customer messaged first
    BUSINESS_INITIATED = "business_initiated"  # Business sent template
    REFERRAL = "referral"  # From ads or entry points


@dataclass
class WhatsAppContact:
    """
    WhatsApp contact information.

    Represents a WhatsApp user profile from incoming messages.
    Profile information is available only if user has shared it.

    Privacy Note:
    - WhatsApp phone numbers are the primary identifier
    - Profile name may not match real name
    - Profile photo URL expires after webhook receipt
    """

    wa_id: str  # WhatsApp ID (phone number without + prefix)
    phone_number: str  # Full phone number with country code
    name: Optional[str] = None  # Display name (if available)
    profile_picture_url: Optional[str] = None  # Profile photo (expires quickly)

    @property
    def formatted_phone(self) -> str:
        """Get phone number with + prefix for display."""
        if self.phone_number.startswith("+"):
            return self.phone_number
        return f"+{self.phone_number}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WhatsAppContact":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_webhook(cls, contact_data: Dict[str, Any]) -> "WhatsAppContact":
        """
        Create from WhatsApp webhook contact data.

        Webhook format:
        {
            "wa_id": "1234567890",
            "profile": {"name": "John Doe"}
        }
        """
        profile = contact_data.get("profile", {})
        return cls(
            wa_id=contact_data.get("wa_id", ""),
            phone_number=contact_data.get("wa_id", ""),
            name=profile.get("name"),
        )


@dataclass
class WhatsAppMessage:
    """
    Represents a WhatsApp message (incoming or outgoing).

    For incoming messages, created from webhook payload.
    For outgoing messages, created before sending via API.

    Session Integration:
    - Links to CustomerSession via phone number lookup
    - Cross-channel: Same customer_id for web and WhatsApp
    - Conversation threading via context_id

    Message Structure:
    - message_id: Unique identifier from WhatsApp
    - wa_id: Recipient/sender WhatsApp ID (phone number)
    - type: Message type (text, template, interactive, etc.)
    - content: Type-specific content (text body, template params, etc.)
    """

    message_id: str  # WhatsApp message ID (wamid.xxx)
    wa_id: str  # WhatsApp ID (phone number without +)
    type: MessageType
    content: Dict[str, Any]  # Type-specific content
    direction: str = "inbound"  # inbound (from customer) or outbound (from us)
    status: MessageStatus = MessageStatus.PENDING
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # Session linkage
    session_id: Optional[str] = None
    context_id: Optional[str] = None

    # Metadata
    contact: Optional[WhatsAppContact] = None
    reply_to_message_id: Optional[str] = None  # For reply threading

    @property
    def text_body(self) -> Optional[str]:
        """Get text body if this is a text message."""
        if self.type == MessageType.TEXT:
            return self.content.get("body", "")
        return None

    @property
    def is_inbound(self) -> bool:
        """Check if message is from customer."""
        return self.direction == "inbound"

    @property
    def is_outbound(self) -> bool:
        """Check if message is to customer."""
        return self.direction == "outbound"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = {
            "id": self.message_id,  # Cosmos DB document ID
            "message_id": self.message_id,
            "wa_id": self.wa_id,
            "type": self.type.value,
            "content": self.content,
            "direction": self.direction,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "context_id": self.context_id,
            "reply_to_message_id": self.reply_to_message_id,
        }
        if self.contact:
            data["contact"] = self.contact.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WhatsAppMessage":
        """Create from dictionary."""
        # Extract nested objects
        contact_data = data.pop("contact", None)

        # Convert enum values
        data["type"] = MessageType(data["type"])
        data["status"] = MessageStatus(data["status"])

        # Remove Cosmos DB metadata
        for key in ["id", "_rid", "_self", "_etag", "_attachments", "_ts"]:
            data.pop(key, None)

        message = cls(**data)

        if contact_data:
            message.contact = WhatsAppContact.from_dict(contact_data)

        return message

    @classmethod
    def from_webhook(cls, message_data: Dict[str, Any], contact: WhatsAppContact) -> "WhatsAppMessage":
        """
        Create from WhatsApp webhook message payload.

        Webhook format:
        {
            "from": "1234567890",
            "id": "wamid.xxx",
            "timestamp": "1234567890",
            "type": "text",
            "text": {"body": "Hello"}
        }
        """
        msg_type = MessageType(message_data.get("type", "text"))

        # Extract type-specific content
        content = {}
        if msg_type == MessageType.TEXT:
            content = message_data.get("text", {})
        elif msg_type == MessageType.IMAGE:
            content = message_data.get("image", {})
        elif msg_type == MessageType.DOCUMENT:
            content = message_data.get("document", {})
        elif msg_type == MessageType.INTERACTIVE:
            # Interactive reply (button click or list selection)
            content = message_data.get("interactive", {})
        elif msg_type == MessageType.LOCATION:
            content = message_data.get("location", {})

        # Convert Unix timestamp to ISO format
        unix_ts = int(message_data.get("timestamp", 0))
        timestamp = datetime.utcfromtimestamp(unix_ts).isoformat() + "Z" if unix_ts else datetime.utcnow().isoformat() + "Z"

        return cls(
            message_id=message_data.get("id", f"msg-{uuid.uuid4().hex[:12]}"),
            wa_id=message_data.get("from", ""),
            type=msg_type,
            content=content,
            direction="inbound",
            status=MessageStatus.DELIVERED,  # Inbound messages are already delivered
            timestamp=timestamp,
            contact=contact,
            reply_to_message_id=message_data.get("context", {}).get("id"),
        )


@dataclass
class MessageTemplate:
    """
    WhatsApp message template for proactive messaging.

    Templates must be pre-approved by Meta before use.
    Used for: order confirmations, shipping updates, appointment reminders.

    Template Structure:
    - name: Template name registered with Meta
    - language: Language code (e.g., "en_US")
    - components: Header, body, footer, buttons with parameters

    Approval Process:
    1. Create template in Meta Business Manager
    2. Submit for review (1-24 hours)
    3. Once approved, use via API with parameters

    See: https://developers.facebook.com/docs/whatsapp/message-templates
    """

    name: str  # Template name (registered with Meta)
    language: str  # Language code (e.g., "en_US", "es", "fr_CA")
    components: List[Dict[str, Any]] = field(default_factory=list)

    # Template metadata
    category: str = "UTILITY"  # UTILITY, MARKETING, AUTHENTICATION
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED

    def to_api_format(self, parameters: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Convert to WhatsApp API format for sending.

        Args:
            parameters: Dict mapping component type to list of parameter values
                       e.g., {"body": ["John", "Order #123"]}

        Returns:
            API-ready template object
        """
        template = {
            "name": self.name,
            "language": {"code": self.language},
        }

        if parameters or self.components:
            components = []

            for comp in self.components:
                comp_type = comp.get("type", "body")
                comp_params = parameters.get(comp_type, []) if parameters else []

                if comp_params:
                    component = {
                        "type": comp_type,
                        "parameters": [
                            {"type": "text", "text": param}
                            for param in comp_params
                        ],
                    }
                    components.append(component)

            if components:
                template["components"] = components

        return template

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageTemplate":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class WebhookEvent:
    """
    Represents a WhatsApp webhook event.

    Event Types:
    - messages: New message received
    - statuses: Message delivery status update
    - errors: Error notification

    Webhook Verification:
    - Meta sends hub.challenge for verification
    - Verify hub.verify_token matches configured token
    - Return hub.challenge to complete verification

    See: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
    """

    event_type: str  # messages, statuses, errors
    business_account_id: str  # WhatsApp Business Account ID
    phone_number_id: str  # Phone number ID receiving the event
    timestamp: str

    # Event-specific data
    message: Optional[WhatsAppMessage] = None  # For message events
    status_update: Optional[Dict[str, Any]] = None  # For status events
    error: Optional[Dict[str, Any]] = None  # For error events

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "event_type": self.event_type,
            "business_account_id": self.business_account_id,
            "phone_number_id": self.phone_number_id,
            "timestamp": self.timestamp,
        }
        if self.message:
            data["message"] = self.message.to_dict()
        if self.status_update:
            data["status_update"] = self.status_update
        if self.error:
            data["error"] = self.error
        return data

    @classmethod
    def from_webhook_payload(cls, payload: Dict[str, Any]) -> List["WebhookEvent"]:
        """
        Parse WhatsApp webhook payload into events.

        Webhook payload structure:
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "...", "display_phone_number": "..."},
                                "contacts": [...],
                                "messages": [...],
                                "statuses": [...]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }

        Returns:
            List of WebhookEvent objects
        """
        events = []

        if payload.get("object") != "whatsapp_business_account":
            return events

        for entry in payload.get("entry", []):
            business_account_id = entry.get("id", "")

            for change in entry.get("changes", []):
                value = change.get("value", {})
                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id", "")

                # Parse contacts for message events
                contacts = {}
                for contact_data in value.get("contacts", []):
                    contact = WhatsAppContact.from_webhook(contact_data)
                    contacts[contact.wa_id] = contact

                # Parse message events
                for msg_data in value.get("messages", []):
                    contact = contacts.get(msg_data.get("from"), WhatsAppContact(
                        wa_id=msg_data.get("from", ""),
                        phone_number=msg_data.get("from", ""),
                    ))

                    message = WhatsAppMessage.from_webhook(msg_data, contact)

                    events.append(cls(
                        event_type="messages",
                        business_account_id=business_account_id,
                        phone_number_id=phone_number_id,
                        timestamp=message.timestamp,
                        message=message,
                    ))

                # Parse status events
                for status_data in value.get("statuses", []):
                    events.append(cls(
                        event_type="statuses",
                        business_account_id=business_account_id,
                        phone_number_id=phone_number_id,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                        status_update=status_data,
                    ))

                # Parse error events
                for error_data in value.get("errors", []):
                    events.append(cls(
                        event_type="errors",
                        business_account_id=business_account_id,
                        phone_number_id=phone_number_id,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                        error=error_data,
                    ))

        return events


# ============================================================================
# Pre-defined Templates for Common Use Cases
# ============================================================================
# These are example templates - actual templates must be registered with Meta.
# Template registration: https://business.facebook.com/wa/manage/message-templates
# ============================================================================

# Order confirmation template
ORDER_CONFIRMATION_TEMPLATE = MessageTemplate(
    name="order_confirmation",
    language="en_US",
    category="UTILITY",
    status="APPROVED",  # Would be approved by Meta
    components=[
        {"type": "body", "parameters": ["customer_name", "order_number", "total_amount"]},
    ],
)

# Shipping update template
SHIPPING_UPDATE_TEMPLATE = MessageTemplate(
    name="shipping_update",
    language="en_US",
    category="UTILITY",
    status="APPROVED",
    components=[
        {"type": "body", "parameters": ["order_number", "carrier", "tracking_number"]},
    ],
)

# Order status template
ORDER_STATUS_TEMPLATE = MessageTemplate(
    name="order_status",
    language="en_US",
    category="UTILITY",
    status="APPROVED",
    components=[
        {"type": "body", "parameters": ["order_number", "status", "estimated_delivery"]},
    ],
)

# Welcome message template (for business-initiated conversations)
WELCOME_TEMPLATE = MessageTemplate(
    name="welcome_message",
    language="en_US",
    category="MARKETING",
    status="APPROVED",
    components=[
        {"type": "body", "parameters": ["customer_name", "store_name"]},
    ],
)
