# ============================================================================
# WhatsApp Business API Unit Tests - Phase 6
# ============================================================================
# Purpose: Unit tests for WhatsApp Cloud API client and webhook handler
#
# Test Coverage:
# - Message models and serialization
# - Webhook event parsing
# - Template message formatting
# - Session bridge logic
#
# Run:
#     pytest tests/unit/test_whatsapp.py -v
# ============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Import WhatsApp models
from shared.whatsapp.models import (
    MessageType,
    MessageStatus,
    ConversationType,
    WhatsAppContact,
    WhatsAppMessage,
    MessageTemplate,
    WebhookEvent,
    ORDER_CONFIRMATION_TEMPLATE,
    SHIPPING_UPDATE_TEMPLATE,
)


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_types_exist(self):
        """Verify all expected message types are defined."""
        assert MessageType.TEXT == "text"
        assert MessageType.TEMPLATE == "template"
        assert MessageType.INTERACTIVE == "interactive"
        assert MessageType.IMAGE == "image"
        assert MessageType.DOCUMENT == "document"

    def test_message_type_values(self):
        """Verify message type string values."""
        assert MessageType.TEXT.value == "text"
        assert MessageType.TEMPLATE.value == "template"


class TestMessageStatus:
    """Tests for MessageStatus enum."""

    def test_status_progression(self):
        """Verify status values for delivery tracking."""
        assert MessageStatus.PENDING == "pending"
        assert MessageStatus.SENT == "sent"
        assert MessageStatus.DELIVERED == "delivered"
        assert MessageStatus.READ == "read"
        assert MessageStatus.FAILED == "failed"


class TestWhatsAppContact:
    """Tests for WhatsAppContact model."""

    def test_create_contact(self):
        """Test creating a contact with required fields."""
        contact = WhatsAppContact(
            wa_id="1234567890",
            phone_number="1234567890",
            name="John Doe",
        )

        assert contact.wa_id == "1234567890"
        assert contact.phone_number == "1234567890"
        assert contact.name == "John Doe"

    def test_formatted_phone_without_plus(self):
        """Test phone number formatting adds + prefix."""
        contact = WhatsAppContact(wa_id="1234567890", phone_number="1234567890")
        assert contact.formatted_phone == "+1234567890"

    def test_formatted_phone_with_plus(self):
        """Test phone number formatting preserves + prefix."""
        contact = WhatsAppContact(wa_id="1234567890", phone_number="+1234567890")
        assert contact.formatted_phone == "+1234567890"

    def test_contact_serialization(self):
        """Test contact to_dict serialization."""
        contact = WhatsAppContact(
            wa_id="1234567890",
            phone_number="1234567890",
            name="John Doe",
        )
        data = contact.to_dict()

        assert data["wa_id"] == "1234567890"
        assert data["name"] == "John Doe"

    def test_contact_from_webhook(self):
        """Test creating contact from webhook data."""
        webhook_data = {
            "wa_id": "1234567890",
            "profile": {"name": "Jane Smith"},
        }

        contact = WhatsAppContact.from_webhook(webhook_data)

        assert contact.wa_id == "1234567890"
        assert contact.name == "Jane Smith"


class TestWhatsAppMessage:
    """Tests for WhatsAppMessage model."""

    def test_create_text_message(self):
        """Test creating a text message."""
        message = WhatsAppMessage(
            message_id="wamid.abc123",
            wa_id="1234567890",
            type=MessageType.TEXT,
            content={"body": "Hello, world!"},
            direction="inbound",
        )

        assert message.message_id == "wamid.abc123"
        assert message.type == MessageType.TEXT
        assert message.text_body == "Hello, world!"
        assert message.is_inbound

    def test_text_body_returns_none_for_non_text(self):
        """Test text_body returns None for non-text messages."""
        message = WhatsAppMessage(
            message_id="wamid.abc123",
            wa_id="1234567890",
            type=MessageType.IMAGE,
            content={"id": "media_123"},
        )

        assert message.text_body is None

    def test_message_direction(self):
        """Test inbound/outbound direction checks."""
        inbound = WhatsAppMessage(
            message_id="wamid.1",
            wa_id="1234567890",
            type=MessageType.TEXT,
            content={},
            direction="inbound",
        )
        outbound = WhatsAppMessage(
            message_id="wamid.2",
            wa_id="1234567890",
            type=MessageType.TEXT,
            content={},
            direction="outbound",
        )

        assert inbound.is_inbound
        assert not inbound.is_outbound
        assert outbound.is_outbound
        assert not outbound.is_inbound

    def test_message_serialization(self):
        """Test message to_dict serialization."""
        contact = WhatsAppContact(wa_id="1234567890", phone_number="1234567890")
        message = WhatsAppMessage(
            message_id="wamid.abc123",
            wa_id="1234567890",
            type=MessageType.TEXT,
            content={"body": "Hello"},
            contact=contact,
            session_id="sess-123",
        )

        data = message.to_dict()

        assert data["message_id"] == "wamid.abc123"
        assert data["type"] == "text"
        assert data["session_id"] == "sess-123"
        assert "contact" in data

    def test_message_from_dict(self):
        """Test message deserialization."""
        data = {
            "message_id": "wamid.abc123",
            "wa_id": "1234567890",
            "type": "text",
            "content": {"body": "Hello"},
            "direction": "inbound",
            "status": "delivered",
            "timestamp": "2026-01-28T10:00:00Z",
        }

        message = WhatsAppMessage.from_dict(data)

        assert message.message_id == "wamid.abc123"
        assert message.type == MessageType.TEXT
        assert message.status == MessageStatus.DELIVERED

    def test_message_from_webhook(self):
        """Test creating message from webhook payload."""
        contact = WhatsAppContact(wa_id="1234567890", phone_number="1234567890")
        webhook_data = {
            "from": "1234567890",
            "id": "wamid.webhook123",
            "timestamp": "1706436000",  # Unix timestamp
            "type": "text",
            "text": {"body": "Hi, I need help with my order"},
        }

        message = WhatsAppMessage.from_webhook(webhook_data, contact)

        assert message.message_id == "wamid.webhook123"
        assert message.wa_id == "1234567890"
        assert message.type == MessageType.TEXT
        assert message.text_body == "Hi, I need help with my order"
        assert message.is_inbound
        assert message.status == MessageStatus.DELIVERED


class TestMessageTemplate:
    """Tests for MessageTemplate model."""

    def test_create_template(self):
        """Test creating a message template."""
        template = MessageTemplate(
            name="order_confirmation",
            language="en_US",
            category="UTILITY",
            status="APPROVED",
        )

        assert template.name == "order_confirmation"
        assert template.language == "en_US"
        assert template.status == "APPROVED"

    def test_template_to_api_format_simple(self):
        """Test template API format without parameters."""
        template = MessageTemplate(name="hello_world", language="en")

        api_format = template.to_api_format()

        assert api_format["name"] == "hello_world"
        assert api_format["language"]["code"] == "en"

    def test_template_to_api_format_with_parameters(self):
        """Test template API format with parameters."""
        template = MessageTemplate(
            name="order_confirmation",
            language="en_US",
            components=[{"type": "body"}],
        )

        params = {"body": ["John", "12345", "$99.99"]}
        api_format = template.to_api_format(params)

        assert api_format["name"] == "order_confirmation"
        assert "components" in api_format

        body_comp = api_format["components"][0]
        assert body_comp["type"] == "body"
        assert len(body_comp["parameters"]) == 3
        assert body_comp["parameters"][0]["text"] == "John"

    def test_predefined_templates(self):
        """Test pre-defined templates are properly configured."""
        assert ORDER_CONFIRMATION_TEMPLATE.name == "order_confirmation"
        assert ORDER_CONFIRMATION_TEMPLATE.status == "APPROVED"

        assert SHIPPING_UPDATE_TEMPLATE.name == "shipping_update"
        assert SHIPPING_UPDATE_TEMPLATE.category == "UTILITY"


class TestWebhookEvent:
    """Tests for WebhookEvent model."""

    def test_parse_message_webhook(self):
        """Test parsing incoming message webhook."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "BIZ_ACCOUNT_123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15550000000",
                                    "phone_number_id": "PHONE_ID_123",
                                },
                                "contacts": [
                                    {
                                        "wa_id": "1234567890",
                                        "profile": {"name": "Test Customer"},
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "1234567890",
                                        "id": "wamid.event123",
                                        "timestamp": "1706436000",
                                        "type": "text",
                                        "text": {"body": "Hello!"},
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        events = WebhookEvent.from_webhook_payload(payload)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == "messages"
        assert event.business_account_id == "BIZ_ACCOUNT_123"
        assert event.phone_number_id == "PHONE_ID_123"
        assert event.message is not None
        assert event.message.message_id == "wamid.event123"
        assert event.message.text_body == "Hello!"

    def test_parse_status_webhook(self):
        """Test parsing message status webhook."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "BIZ_ACCOUNT_123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15550000000",
                                    "phone_number_id": "PHONE_ID_123",
                                },
                                "statuses": [
                                    {
                                        "id": "wamid.msg123",
                                        "status": "delivered",
                                        "timestamp": "1706436100",
                                        "recipient_id": "1234567890",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        events = WebhookEvent.from_webhook_payload(payload)

        assert len(events) == 1
        event = events[0]
        assert event.event_type == "statuses"
        assert event.status_update is not None
        assert event.status_update["id"] == "wamid.msg123"
        assert event.status_update["status"] == "delivered"

    def test_parse_invalid_payload(self):
        """Test parsing non-WhatsApp payload returns empty."""
        payload = {"object": "not_whatsapp", "entry": []}

        events = WebhookEvent.from_webhook_payload(payload)

        assert len(events) == 0

    def test_parse_multiple_messages(self):
        """Test parsing webhook with multiple messages."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "BIZ_123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"phone_number_id": "PHONE_123"},
                                "contacts": [{"wa_id": "111", "profile": {"name": "A"}}],
                                "messages": [
                                    {
                                        "from": "111",
                                        "id": "msg1",
                                        "timestamp": "1706436000",
                                        "type": "text",
                                        "text": {"body": "First"},
                                    },
                                    {
                                        "from": "111",
                                        "id": "msg2",
                                        "timestamp": "1706436001",
                                        "type": "text",
                                        "text": {"body": "Second"},
                                    },
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        events = WebhookEvent.from_webhook_payload(payload)

        assert len(events) == 2
        assert events[0].message.message_id == "msg1"
        assert events[1].message.message_id == "msg2"


class TestWebhookHandler:
    """Tests for WhatsAppWebhookHandler."""

    def test_verify_webhook_success(self):
        """Test successful webhook verification."""
        from shared.whatsapp.webhook_handler import WhatsAppWebhookHandler

        handler = WhatsAppWebhookHandler(verify_token="test_token_123")

        result = handler.verify_webhook(
            mode="subscribe",
            token="test_token_123",
            challenge="challenge_string_abc",
        )

        assert result == "challenge_string_abc"

    def test_verify_webhook_wrong_token(self):
        """Test webhook verification fails with wrong token."""
        from shared.whatsapp.webhook_handler import WhatsAppWebhookHandler

        handler = WhatsAppWebhookHandler(verify_token="correct_token")

        result = handler.verify_webhook(
            mode="subscribe",
            token="wrong_token",
            challenge="challenge_string",
        )

        assert result is None

    def test_verify_webhook_wrong_mode(self):
        """Test webhook verification fails with wrong mode."""
        from shared.whatsapp.webhook_handler import WhatsAppWebhookHandler

        handler = WhatsAppWebhookHandler(verify_token="test_token")

        result = handler.verify_webhook(
            mode="unsubscribe",
            token="test_token",
            challenge="challenge_string",
        )

        assert result is None

    def test_register_message_handler(self):
        """Test registering a message handler."""
        from shared.whatsapp.webhook_handler import WhatsAppWebhookHandler

        handler = WhatsAppWebhookHandler()

        @handler.on_message
        async def my_handler(message):
            pass

        assert len(handler._message_handlers) == 1

    def test_register_status_handler(self):
        """Test registering a status handler."""
        from shared.whatsapp.webhook_handler import WhatsAppWebhookHandler

        handler = WhatsAppWebhookHandler()

        @handler.on_status
        async def my_handler(status):
            pass

        assert len(handler._status_handlers) == 1

    def test_verify_signature_skipped_without_secret(self):
        """Test signature verification is skipped if no secret configured."""
        from shared.whatsapp.webhook_handler import WhatsAppWebhookHandler

        handler = WhatsAppWebhookHandler(app_secret="")

        # Should return True (skip verification)
        result = handler.verify_signature(b"payload", "sha256=signature")

        assert result is True

    def test_verify_signature_missing_header(self):
        """Test signature verification fails with missing header."""
        from shared.whatsapp.webhook_handler import WhatsAppWebhookHandler

        handler = WhatsAppWebhookHandler(app_secret="my_secret")

        result = handler.verify_signature(b"payload", "")

        assert result is False


class TestWhatsAppClient:
    """Tests for WhatsAppCloudClient initialization."""

    def test_client_creation(self):
        """Test client is created with required parameters."""
        from shared.whatsapp.client import WhatsAppCloudClient

        client = WhatsAppCloudClient(
            access_token="test_token",
            phone_number_id="123456789",
            business_account_id="987654321",
        )

        assert client.phone_number_id == "123456789"
        assert client.business_account_id == "987654321"

    def test_client_properties(self):
        """Test client property accessors."""
        from shared.whatsapp.client import WhatsAppCloudClient

        client = WhatsAppCloudClient(
            access_token="token",
            phone_number_id="phone_123",
        )

        assert client.phone_number_id == "phone_123"
        assert client.business_account_id is None


class TestSessionBridge:
    """Tests for WhatsAppSessionBridge."""

    @pytest.mark.asyncio
    async def test_get_session_manager_not_available(self):
        """Test session bridge handles missing session manager gracefully."""
        from shared.whatsapp.webhook_handler import WhatsAppSessionBridge

        # Create bridge with mock session manager that's None
        bridge = WhatsAppSessionBridge(session_manager=None)

        # Mock the _get_session_manager method to return None
        with patch.object(bridge, "_get_session_manager", new=AsyncMock(return_value=None)):
            result = await bridge.get_or_create_session("1234567890")

        # Result should be None when manager is unavailable
        assert result is None
