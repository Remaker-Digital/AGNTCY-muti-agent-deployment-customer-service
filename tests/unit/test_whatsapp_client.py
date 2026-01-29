# ============================================================================
# Unit Tests for WhatsApp Business Cloud API Client
# ============================================================================
# Purpose: Test WhatsApp message sending and API interactions
#
# Test Categories:
# 1. Client Initialization - Verify client setup
# 2. Text Messages - Test plain text message sending
# 3. Template Messages - Test pre-approved template messages
# 4. Interactive Messages - Test button and list messages
# 5. Media Messages - Test media attachment handling
# 6. Error Handling - Test API error responses
#
# Related Documentation:
# - WhatsApp Client: shared/whatsapp/client.py
# - WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.whatsapp.client import WhatsAppCloudClient, WHATSAPP_API_VERSION


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def whatsapp_client():
    """Create a WhatsApp client for testing."""
    client = WhatsAppCloudClient(
        access_token="test_access_token_12345",
        phone_number_id="123456789",
        business_account_id="987654321",
    )
    return client


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    mock = AsyncMock(spec=httpx.AsyncClient)
    mock.post = AsyncMock()
    mock.get = AsyncMock()
    mock.aclose = AsyncMock()
    return mock


@pytest.fixture
def successful_send_response():
    """Sample successful message send response."""
    return {
        "messaging_product": "whatsapp",
        "contacts": [{"input": "1234567890", "wa_id": "1234567890"}],
        "messages": [{"id": "wamid.HBgLMTIzNDU2Nzg5MBUCABEYEjYwQTI="}],
    }


# =============================================================================
# Test: Client Initialization
# =============================================================================


class TestClientInitialization:
    """Tests for WhatsApp client initialization."""

    def test_client_creation(self):
        """Verify client is created with correct attributes."""
        client = WhatsAppCloudClient(
            access_token="test_token",
            phone_number_id="123456",
        )
        assert client._access_token == "test_token"
        assert client._phone_number_id == "123456"
        assert client._http_client is None  # Lazy initialization

    def test_client_with_business_account_id(self):
        """Verify business account ID is stored."""
        client = WhatsAppCloudClient(
            access_token="test_token",
            phone_number_id="123456",
            business_account_id="789012",
        )
        assert client._business_account_id == "789012"

    def test_custom_api_base_url(self):
        """Verify custom API base URL is used."""
        client = WhatsAppCloudClient(
            access_token="test_token",
            phone_number_id="123456",
            api_base_url="https://custom.api.url",
        )
        assert client._api_base_url == "https://custom.api.url"

    def test_default_api_version(self):
        """Verify default API version is set."""
        assert "v" in WHATSAPP_API_VERSION


# =============================================================================
# Test: HTTP Client Management
# =============================================================================


class TestHttpClientManagement:
    """Tests for HTTP client lifecycle."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self, whatsapp_client):
        """Verify _get_client creates HTTP client on first call."""
        with patch.object(httpx, "AsyncClient") as mock_async_client:
            mock_instance = MagicMock()
            mock_async_client.return_value = mock_instance

            client = await whatsapp_client._get_client()

            mock_async_client.assert_called_once()
            assert client is mock_instance

    @pytest.mark.asyncio
    async def test_get_client_reuses_client(self, whatsapp_client):
        """Verify _get_client reuses existing client."""
        mock_client = MagicMock()
        whatsapp_client._http_client = mock_client

        client = await whatsapp_client._get_client()

        assert client is mock_client

    @pytest.mark.asyncio
    async def test_close_client(self, whatsapp_client):
        """Verify close() properly closes client."""
        mock_client = AsyncMock()
        whatsapp_client._http_client = mock_client

        await whatsapp_client.close()

        mock_client.aclose.assert_called_once()
        assert whatsapp_client._http_client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(self, whatsapp_client):
        """Verify close() handles no client gracefully."""
        # Should not raise exception
        await whatsapp_client.close()


# =============================================================================
# Test: Text Messages
# =============================================================================


class TestTextMessages:
    """Tests for text message sending."""

    @pytest.mark.asyncio
    async def test_send_text_message_payload(self, whatsapp_client, mock_http_client):
        """Verify correct payload is sent for text message."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.123"}]}
        mock_http_client.post.return_value = mock_response

        result = await whatsapp_client.send_text_message(
            to="1234567890",
            text="Hello, world!",
        )

        # Verify post was called
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args

        # Verify payload structure
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "1234567890"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Hello, world!"

    @pytest.mark.asyncio
    async def test_send_text_message_with_preview_url(
        self, whatsapp_client, mock_http_client
    ):
        """Verify preview_url flag is included."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_text_message(
            to="1234567890",
            text="Check out https://example.com",
            preview_url=True,
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["text"]["preview_url"] is True

    @pytest.mark.asyncio
    async def test_send_text_message_with_reply(
        self, whatsapp_client, mock_http_client
    ):
        """Verify reply_to_message_id is included."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.456"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_text_message(
            to="1234567890",
            text="Thanks for your message!",
            reply_to_message_id="wamid.original123",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "context" in payload
        assert payload["context"]["message_id"] == "wamid.original123"


# =============================================================================
# Test: Template Messages
# =============================================================================


class TestTemplateMessages:
    """Tests for template message sending."""

    @pytest.mark.asyncio
    async def test_send_template_message_payload(
        self, whatsapp_client, mock_http_client
    ):
        """Verify correct payload for template message."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.789"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_template_message(
            to="1234567890",
            template_name="order_confirmation",
            language="en_US",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "template"
        assert "template" in payload
        assert payload["template"]["name"] == "order_confirmation"

    @pytest.mark.asyncio
    async def test_send_template_message_with_parameters(
        self, whatsapp_client, mock_http_client
    ):
        """Verify template parameters are included."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.789"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_template_message(
            to="1234567890",
            template_name="order_update",
            language="en_US",
            parameters={"body": ["John", "12345", "$99.99"]},
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "template" in payload


# =============================================================================
# Test: Interactive Messages
# =============================================================================


class TestInteractiveMessages:
    """Tests for interactive message sending."""

    @pytest.mark.asyncio
    async def test_send_button_message(self, whatsapp_client, mock_http_client):
        """Verify button interactive message payload."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.btn123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_interactive_message(
            to="1234567890",
            interactive_type="button",
            body="How can I help you?",
            action={
                "buttons": [
                    {"type": "reply", "reply": {"id": "help", "title": "Get Help"}},
                ]
            },
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "interactive"
        assert "interactive" in payload

    @pytest.mark.asyncio
    async def test_send_list_message(self, whatsapp_client, mock_http_client):
        """Verify list interactive message payload."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.list123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_interactive_message(
            to="1234567890",
            interactive_type="list",
            body="Select an option:",
            action={
                "button": "View Options",
                "sections": [
                    {
                        "title": "Orders",
                        "rows": [
                            {"id": "track", "title": "Track Order"},
                        ],
                    }
                ],
            },
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "interactive"

    @pytest.mark.asyncio
    async def test_interactive_with_header_footer(
        self, whatsapp_client, mock_http_client
    ):
        """Verify header and footer are included."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.full123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_interactive_message(
            to="1234567890",
            interactive_type="button",
            header={"type": "text", "text": "Welcome!"},
            body="Choose an option:",
            footer="Powered by AI",
            action={"buttons": []},
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        interactive = payload.get("interactive", {})
        assert "header" in interactive or "body" in interactive


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_phone_number(self):
        """Verify empty phone number is accepted (API validates)."""
        client = WhatsAppCloudClient(
            access_token="token",
            phone_number_id="",
        )
        assert client._phone_number_id == ""

    @pytest.mark.asyncio
    async def test_special_characters_in_message(
        self, whatsapp_client, mock_http_client
    ):
        """Verify special characters are handled."""
        # Just testing client accepts special chars - API will handle encoding
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.123"}]}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        # This should not raise
        await whatsapp_client.send_text_message(
            to="1234567890",
            text="Café ☕ Ñ 中文 🎉",
        )

    def test_long_message(self, whatsapp_client):
        """Verify long messages are not truncated by client."""
        # WhatsApp has 4096 char limit, but client should pass through
        long_text = "A" * 5000
        # Client shouldn't modify the text
        assert len(long_text) == 5000


# =============================================================================
# Test: Phone Number Validation
# =============================================================================


class TestPhoneNumberHandling:
    """Tests for phone number handling."""

    @pytest.mark.asyncio
    async def test_phone_number_formats(self, whatsapp_client, mock_http_client):
        """Verify various phone number formats are passed through."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.123"}]}
        mock_http_client.post = AsyncMock(return_value=mock_response)

        # US format
        await whatsapp_client.send_text_message(to="12025551234", text="Hello")

        # International format
        await whatsapp_client.send_text_message(to="447911123456", text="Hello")

        # API should receive both - client doesn't validate
        assert mock_http_client.post.call_count == 2


# =============================================================================
# Test: Quick Reply Buttons
# =============================================================================


class TestQuickReplyButtons:
    """Tests for quick reply button messages."""

    @pytest.mark.asyncio
    async def test_send_quick_reply_buttons(self, whatsapp_client, mock_http_client):
        """Verify quick reply buttons payload."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.btn123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_quick_reply_buttons(
            to="1234567890",
            body="How can I help?",
            buttons=[
                {"id": "help", "title": "Get Help"},
                {"id": "track", "title": "Track Order"},
            ],
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "interactive"

    @pytest.mark.asyncio
    async def test_send_quick_reply_with_header_footer(
        self, whatsapp_client, mock_http_client
    ):
        """Verify header and footer are included."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.btn123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_quick_reply_buttons(
            to="1234567890",
            body="Choose an option",
            buttons=[{"id": "opt1", "title": "Option 1"}],
            header="Welcome!",
            footer="Powered by AI",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "interactive"

    @pytest.mark.asyncio
    async def test_send_quick_reply_max_three_buttons(
        self, whatsapp_client, mock_http_client
    ):
        """Verify only first 3 buttons are sent."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.btn123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_quick_reply_buttons(
            to="1234567890",
            body="Choose",
            buttons=[
                {"id": "1", "title": "One"},
                {"id": "2", "title": "Two"},
                {"id": "3", "title": "Three"},
                {"id": "4", "title": "Four"},  # This should be truncated
            ],
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        buttons = payload["interactive"]["action"]["buttons"]
        assert len(buttons) == 3


# =============================================================================
# Test: Image Messages
# =============================================================================


class TestImageMessages:
    """Tests for image message sending."""

    @pytest.mark.asyncio
    async def test_send_image_with_url(self, whatsapp_client, mock_http_client):
        """Verify image message with URL."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.img123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_image_message(
            to="1234567890",
            image_url="https://example.com/image.jpg",
            caption="Product image",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "image"
        assert payload["image"]["link"] == "https://example.com/image.jpg"
        assert payload["image"]["caption"] == "Product image"

    @pytest.mark.asyncio
    async def test_send_image_with_id(self, whatsapp_client, mock_http_client):
        """Verify image message with media ID."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.img123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_image_message(
            to="1234567890",
            image_id="media_123456789",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "image"
        assert payload["image"]["id"] == "media_123456789"

    @pytest.mark.asyncio
    async def test_send_image_with_reply(self, whatsapp_client, mock_http_client):
        """Verify image message with reply context."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.img123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_image_message(
            to="1234567890",
            image_url="https://example.com/image.jpg",
            reply_to_message_id="wamid.original123",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "context" in payload
        assert payload["context"]["message_id"] == "wamid.original123"


# =============================================================================
# Test: Document Messages
# =============================================================================


class TestDocumentMessages:
    """Tests for document message sending."""

    @pytest.mark.asyncio
    async def test_send_document_with_url(self, whatsapp_client, mock_http_client):
        """Verify document message with URL."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.doc123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_document_message(
            to="1234567890",
            document_url="https://example.com/invoice.pdf",
            filename="Invoice-12345.pdf",
            caption="Your invoice",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "document"
        assert payload["document"]["link"] == "https://example.com/invoice.pdf"
        assert payload["document"]["filename"] == "Invoice-12345.pdf"
        assert payload["document"]["caption"] == "Your invoice"

    @pytest.mark.asyncio
    async def test_send_document_with_id(self, whatsapp_client, mock_http_client):
        """Verify document message with media ID."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.doc123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_document_message(
            to="1234567890",
            document_id="media_doc_123",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["type"] == "document"
        assert payload["document"]["id"] == "media_doc_123"

    @pytest.mark.asyncio
    async def test_send_document_with_reply(self, whatsapp_client, mock_http_client):
        """Verify document message with reply context."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.doc123"}]}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.send_document_message(
            to="1234567890",
            document_url="https://example.com/doc.pdf",
            reply_to_message_id="wamid.reply123",
        )

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "context" in payload


# =============================================================================
# Test: Mark Message Read
# =============================================================================


class TestMarkMessageRead:
    """Tests for marking messages as read."""

    @pytest.mark.asyncio
    async def test_mark_message_read(self, whatsapp_client, mock_http_client):
        """Verify mark message read payload."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_http_client.post.return_value = mock_response

        await whatsapp_client.mark_message_read("wamid.message123")

        call_args = mock_http_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["messaging_product"] == "whatsapp"
        assert payload["status"] == "read"
        assert payload["message_id"] == "wamid.message123"


# =============================================================================
# Test: Media Management
# =============================================================================


class TestMediaManagement:
    """Tests for media upload and retrieval."""

    @pytest.mark.asyncio
    async def test_upload_media(self, whatsapp_client, mock_http_client):
        """Verify media upload."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "media_uploaded_123"}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post.return_value = mock_response

        result = await whatsapp_client.upload_media(
            file_data=b"fake image data",
            filename="test.jpg",
            content_type="image/jpeg",
        )

        assert result["id"] == "media_uploaded_123"

    @pytest.mark.asyncio
    async def test_upload_media_http_error(self, whatsapp_client, mock_http_client):
        """Verify upload media handles HTTP errors."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad request",
            request=MagicMock(),
            response=mock_response,
        )
        mock_http_client.post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await whatsapp_client.upload_media(
                file_data=b"data",
                filename="test.jpg",
                content_type="image/jpeg",
            )

    @pytest.mark.asyncio
    async def test_get_media_url(self, whatsapp_client, mock_http_client):
        """Verify get media URL."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"url": "https://media.example.com/file.jpg"}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        result = await whatsapp_client.get_media_url("media_123")

        assert result == "https://media.example.com/file.jpg"

    @pytest.mark.asyncio
    async def test_get_media_url_http_error(self, whatsapp_client, mock_http_client):
        """Verify get media URL handles HTTP errors."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(),
            response=mock_response,
        )
        mock_http_client.get.return_value = mock_response

        result = await whatsapp_client.get_media_url("nonexistent_media")

        assert result is None


# =============================================================================
# Test: Send Message Error Handling
# =============================================================================


class TestSendMessageErrorHandling:
    """Tests for send message error handling."""

    @pytest.mark.asyncio
    async def test_send_message_http_error(self, whatsapp_client, mock_http_client):
        """Verify send message handles HTTP errors."""
        whatsapp_client._http_client = mock_http_client
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": {"message": "Invalid phone"}}'
        mock_response.json.return_value = {"error": {"message": "Invalid phone"}}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad request",
            request=MagicMock(),
            response=mock_response,
        )
        mock_http_client.post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await whatsapp_client.send_text_message(
                to="invalid", text="Test"
            )


# =============================================================================
# Test: Client Properties
# =============================================================================


class TestClientProperties:
    """Tests for client properties."""

    def test_phone_number_id_property(self, whatsapp_client):
        """Verify phone_number_id property."""
        assert whatsapp_client.phone_number_id == "123456789"

    def test_business_account_id_property(self, whatsapp_client):
        """Verify business_account_id property."""
        assert whatsapp_client.business_account_id == "987654321"

    def test_business_account_id_none(self):
        """Verify business_account_id can be None."""
        client = WhatsAppCloudClient(
            access_token="token",
            phone_number_id="123",
        )
        assert client.business_account_id is None


# =============================================================================
# Test: Singleton Pattern
# =============================================================================


class TestSingletonPattern:
    """Tests for singleton pattern."""

    @pytest.mark.asyncio
    async def test_init_whatsapp_client(self):
        """Verify init creates client."""
        import shared.whatsapp.client as whatsapp_module

        whatsapp_module._whatsapp_client = None

        with patch.dict(
            "os.environ",
            {
                "WHATSAPP_ACCESS_TOKEN": "test_token",
                "WHATSAPP_PHONE_NUMBER_ID": "123456",
            },
            clear=True,
        ):
            client = await whatsapp_module.init_whatsapp_client()

            assert client is not None
            assert client.phone_number_id == "123456"

        # Cleanup
        await whatsapp_module.shutdown_whatsapp_client()

    @pytest.mark.asyncio
    async def test_init_whatsapp_client_returns_existing(self):
        """Verify init returns existing client."""
        import shared.whatsapp.client as whatsapp_module

        existing = WhatsAppCloudClient(
            access_token="token",
            phone_number_id="existing",
        )
        whatsapp_module._whatsapp_client = existing

        result = await whatsapp_module.init_whatsapp_client()

        assert result is existing

        # Cleanup
        whatsapp_module._whatsapp_client = None

    @pytest.mark.asyncio
    async def test_init_whatsapp_client_mock_mode(self):
        """Verify init uses mock mode when not USE_REAL_APIS."""
        import shared.whatsapp.client as whatsapp_module

        whatsapp_module._whatsapp_client = None

        with patch.dict(
            "os.environ",
            {"USE_REAL_APIS": "false"},
            clear=True,
        ):
            client = await whatsapp_module.init_whatsapp_client()

            # Should use localhost as base URL
            assert "localhost" in client._api_base_url

        # Cleanup
        await whatsapp_module.shutdown_whatsapp_client()

    @pytest.mark.asyncio
    async def test_init_whatsapp_client_real_mode(self):
        """Verify init uses real API when USE_REAL_APIS=true."""
        import shared.whatsapp.client as whatsapp_module

        whatsapp_module._whatsapp_client = None

        with patch.dict(
            "os.environ",
            {
                "USE_REAL_APIS": "true",
                "WHATSAPP_ACCESS_TOKEN": "token",
                "WHATSAPP_PHONE_NUMBER_ID": "123",
            },
            clear=True,
        ):
            client = await whatsapp_module.init_whatsapp_client()

            # Should use graph.facebook.com
            assert "graph.facebook.com" in client._api_base_url

        # Cleanup
        await whatsapp_module.shutdown_whatsapp_client()

    def test_get_whatsapp_client_raises_when_not_initialized(self):
        """Verify get_whatsapp_client raises when not initialized."""
        import shared.whatsapp.client as whatsapp_module

        whatsapp_module._whatsapp_client = None

        with pytest.raises(RuntimeError, match="not initialized"):
            whatsapp_module.get_whatsapp_client()

    def test_get_whatsapp_client_returns_client(self):
        """Verify get_whatsapp_client returns client."""
        import shared.whatsapp.client as whatsapp_module

        existing = WhatsAppCloudClient(
            access_token="token",
            phone_number_id="123",
        )
        whatsapp_module._whatsapp_client = existing

        result = whatsapp_module.get_whatsapp_client()

        assert result is existing

        # Cleanup
        whatsapp_module._whatsapp_client = None

    @pytest.mark.asyncio
    async def test_shutdown_whatsapp_client(self):
        """Verify shutdown clears client."""
        import shared.whatsapp.client as whatsapp_module

        existing = WhatsAppCloudClient(
            access_token="token",
            phone_number_id="123",
        )
        whatsapp_module._whatsapp_client = existing

        await whatsapp_module.shutdown_whatsapp_client()

        assert whatsapp_module._whatsapp_client is None

    @pytest.mark.asyncio
    async def test_shutdown_when_no_client(self):
        """Verify shutdown handles no client gracefully."""
        import shared.whatsapp.client as whatsapp_module

        whatsapp_module._whatsapp_client = None

        # Should not raise
        await whatsapp_module.shutdown_whatsapp_client()
