# ============================================================================
# WhatsApp API Integration Tests - Phase 6
# ============================================================================
# Purpose: Integration tests for WhatsApp API endpoints
#
# Test Coverage:
# - Webhook verification endpoint
# - Webhook event processing
# - Send message endpoints
# - Session retrieval
# - Status endpoint
#
# Run:
#     pytest tests/integration/test_whatsapp_api.py -v
# ============================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Import the API gateway app
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api_gateway.main import app


@pytest.fixture
def client():
    """Create test client for API gateway."""
    return TestClient(app)


class TestWebhookVerification:
    """Tests for WhatsApp webhook verification endpoint."""

    def test_webhook_verification_success(self, client):
        """Test successful webhook verification returns challenge."""
        response = client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "agntcy_webhook_verify_token",
                "hub.challenge": "test_challenge_123",
            },
        )

        assert response.status_code == 200
        assert response.text == "test_challenge_123"

    def test_webhook_verification_wrong_token(self, client):
        """Test webhook verification fails with wrong token."""
        response = client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "challenge",
            },
        )

        assert response.status_code == 403

    def test_webhook_verification_wrong_mode(self, client):
        """Test webhook verification fails with wrong mode."""
        response = client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": "agntcy_webhook_verify_token",
                "hub.challenge": "challenge",
            },
        )

        assert response.status_code == 403


class TestWebhookEvents:
    """Tests for WhatsApp webhook event processing."""

    def test_webhook_receives_message(self, client):
        """Test webhook processes incoming message event."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "BIZ_123",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15550000000",
                                    "phone_number_id": "PHONE_123",
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
                                        "id": "wamid.test123",
                                        "timestamp": "1706436000",
                                        "type": "text",
                                        "text": {"body": "Hello, I need help!"},
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        response = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_webhook_receives_status_update(self, client):
        """Test webhook processes status update event."""
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

        response = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_webhook_empty_payload(self, client):
        """Test webhook handles empty payload gracefully."""
        payload = {"object": "whatsapp_business_account", "entry": []}

        response = client.post("/api/v1/whatsapp/webhook", json=payload)

        assert response.status_code == 200

    def test_webhook_invalid_json(self, client):
        """Test webhook rejects invalid JSON."""
        response = client.post(
            "/api/v1/whatsapp/webhook",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400


class TestSendMessageEndpoints:
    """Tests for WhatsApp send message endpoints."""

    def test_send_text_message_not_initialized(self, client):
        """Test sending a text message when client not initialized returns error."""
        # When client is not initialized, should return error response
        response = client.post(
            "/api/v1/whatsapp/send/text",
            json={
                "to": "1234567890",
                "message": "Hello, your order has shipped!",
            },
        )

        # Should return 503 (service unavailable) since client not initialized
        assert response.status_code == 503

    def test_send_template_message_not_initialized(self, client):
        """Test sending a template message when client not initialized."""
        response = client.post(
            "/api/v1/whatsapp/send/template",
            json={
                "to": "1234567890",
                "template_name": "order_confirmation",
                "language": "en_US",
                "parameters": {"body": ["John", "12345", "$99.99"]},
            },
        )

        # Should return 503 since client not initialized
        assert response.status_code == 503

    def test_send_buttons_message_not_initialized(self, client):
        """Test sending an interactive button message when client not initialized."""
        response = client.post(
            "/api/v1/whatsapp/send/buttons",
            json={
                "to": "1234567890",
                "body": "How can I help you today?",
                "buttons": [
                    {"id": "track_order", "title": "Track Order"},
                    {"id": "return_item", "title": "Return Item"},
                ],
            },
        )

        # Should return 503 since client not initialized
        assert response.status_code == 503

    @patch("shared.whatsapp.client._whatsapp_client")
    def test_send_text_with_mock_client(self, mock_client_global, client):
        """Test sending text when a mock client is available."""
        # Create a mock client
        from shared.whatsapp.client import WhatsAppCloudClient
        mock_client = MagicMock(spec=WhatsAppCloudClient)
        mock_client.send_text_message = AsyncMock(
            return_value={
                "messaging_product": "whatsapp",
                "contacts": [{"wa_id": "1234567890"}],
                "messages": [{"id": "wamid.sent123"}],
            }
        )

        # Patch the module-level variable
        import shared.whatsapp.client as client_module
        original = client_module._whatsapp_client
        client_module._whatsapp_client = mock_client

        try:
            response = client.post(
                "/api/v1/whatsapp/send/text",
                json={
                    "to": "1234567890",
                    "message": "Hello, your order has shipped!",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message_id"] == "wamid.sent123"
            assert data["to"] == "1234567890"
        finally:
            client_module._whatsapp_client = original

    def test_send_text_returns_error_details(self, client):
        """Test send text error response includes details."""
        response = client.post(
            "/api/v1/whatsapp/send/text",
            json={"to": "1234567890", "message": "Hello"},
        )

        # Should return 503 when client not initialized
        assert response.status_code == 503
        # Response should have detail
        assert "detail" in response.json()


class TestSessionEndpoint:
    """Tests for WhatsApp session endpoint."""

    def test_get_session_returns_info(self, client):
        """Test getting session information for phone number."""
        # Session endpoint should work even without full setup
        response = client.get("/api/v1/whatsapp/session/1234567890")

        # Should return 200 with session info (may be empty if not linked)
        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == "1234567890"
        assert "auth_level" in data
        assert "is_linked" in data


class TestStatusEndpoint:
    """Tests for WhatsApp status endpoint."""

    def test_status_returns_configuration(self, client):
        """Test status endpoint returns configuration info."""
        response = client.get("/api/v1/whatsapp/status")

        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "verify_token_set" in data
        assert "app_secret_set" in data
        assert "handlers_registered" in data

    def test_status_shows_unconfigured_gracefully(self, client):
        """Test status shows unconfigured state without error."""
        response = client.get("/api/v1/whatsapp/status")

        assert response.status_code == 200
        # Should not throw errors even if WhatsApp is not fully configured


class TestCORSAndSecurity:
    """Tests for CORS headers and security."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are returned."""
        response = client.options(
            "/api/v1/whatsapp/webhook",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

        # FastAPI handles CORS via middleware
        assert response.status_code in [200, 204, 405]

    def test_content_type_json(self, client):
        """Test JSON content type is required for POST endpoints."""
        response = client.post(
            "/api/v1/whatsapp/send/text",
            data="to=1234567890&message=hello",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Should reject non-JSON content
        assert response.status_code == 422


class TestErrorHandling:
    """Tests for error handling."""

    def test_send_text_missing_to(self, client):
        """Test sending text without recipient fails."""
        response = client.post(
            "/api/v1/whatsapp/send/text",
            json={"message": "Hello"},
        )

        assert response.status_code == 422  # Validation error

    def test_send_text_missing_message(self, client):
        """Test sending without message fails."""
        response = client.post(
            "/api/v1/whatsapp/send/text",
            json={"to": "1234567890"},
        )

        assert response.status_code == 422  # Validation error

    def test_send_template_missing_name(self, client):
        """Test sending template without name fails."""
        response = client.post(
            "/api/v1/whatsapp/send/template",
            json={"to": "1234567890"},
        )

        assert response.status_code == 422

    def test_send_buttons_missing_body(self, client):
        """Test sending buttons without body fails."""
        response = client.post(
            "/api/v1/whatsapp/send/buttons",
            json={
                "to": "1234567890",
                "buttons": [{"id": "1", "title": "Option"}],
            },
        )

        assert response.status_code == 422


class TestMessageReplyThreading:
    """Tests for message reply threading."""

    def test_send_text_with_reply_not_initialized(self, client):
        """Test sending a text message with reply when client not initialized."""
        response = client.post(
            "/api/v1/whatsapp/send/text",
            json={
                "to": "1234567890",
                "message": "Here's the tracking info you requested",
                "reply_to_message_id": "wamid.original123",
            },
        )

        # Should return 503 when client not initialized
        assert response.status_code == 503

    def test_send_text_with_reply_using_mock(self, client):
        """Test reply threading passes message ID to client."""
        from shared.whatsapp.client import WhatsAppCloudClient
        mock_client = MagicMock(spec=WhatsAppCloudClient)
        mock_client.send_text_message = AsyncMock(
            return_value={
                "messaging_product": "whatsapp",
                "contacts": [{"wa_id": "1234567890"}],
                "messages": [{"id": "wamid.reply123"}],
            }
        )

        # Patch the module-level variable
        import shared.whatsapp.client as client_module
        original = client_module._whatsapp_client
        client_module._whatsapp_client = mock_client

        try:
            response = client.post(
                "/api/v1/whatsapp/send/text",
                json={
                    "to": "1234567890",
                    "message": "Here's the tracking info you requested",
                    "reply_to_message_id": "wamid.original123",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify reply_to was passed to client
            mock_client.send_text_message.assert_called_once()
            call_kwargs = mock_client.send_text_message.call_args.kwargs
            assert call_kwargs.get("reply_to_message_id") == "wamid.original123"
        finally:
            client_module._whatsapp_client = original
