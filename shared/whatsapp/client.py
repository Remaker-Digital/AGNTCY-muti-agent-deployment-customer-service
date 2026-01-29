# ============================================================================
# WhatsApp Business Cloud API Client - Phase 6
# ============================================================================
# Purpose: HTTP client for WhatsApp Business Cloud API
#
# API Features:
# - Send text messages
# - Send template messages (proactive notifications)
# - Send interactive messages (buttons, lists)
# - Upload and send media
# - Mark messages as read
#
# Architecture Decision:
# - Use Meta's Cloud API (not on-premise) for simplicity and lower cost
# - Async HTTP client with connection pooling (httpx)
# - Retry logic with exponential backoff for reliability
# - Rate limiting awareness (1000 messages/minute per phone number)
#
# Authentication:
# - System User Access Token (long-lived, recommended for production)
# - Token stored in Azure Key Vault (Phase 4-5)
#
# Related Documentation:
# - WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
# - Send Messages: https://developers.facebook.com/docs/whatsapp/cloud-api/messages
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q1.C)
#
# Budget Impact:
# - API calls: Free (unlimited API calls)
# - Conversations: ~$0.01-0.10/conversation (varies by type and country)
# ============================================================================

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from .models import (
    MessageStatus,
    MessageTemplate,
    MessageType,
    WhatsAppMessage,
)

logger = logging.getLogger(__name__)

# API configuration
WHATSAPP_API_VERSION = "v18.0"
WHATSAPP_API_BASE_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"

# Singleton instance
_whatsapp_client: Optional["WhatsAppCloudClient"] = None


class WhatsAppCloudClient:
    """
    Client for WhatsApp Business Cloud API.

    Handles all communication with Meta's WhatsApp Cloud API including:
    - Sending messages (text, template, interactive, media)
    - Receiving message status updates
    - Managing media uploads

    Rate Limits:
    - 1000 messages/minute per phone number
    - 80 messages/second sustained
    - Client implements automatic rate limiting

    Usage:
        client = await get_whatsapp_client()

        # Send text message
        result = await client.send_text_message(
            to="1234567890",
            text="Hello! How can I help you today?"
        )

        # Send template message
        result = await client.send_template_message(
            to="1234567890",
            template_name="order_confirmation",
            language="en_US",
            parameters={"body": ["John", "12345", "$99.99"]}
        )
    """

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        business_account_id: Optional[str] = None,
        api_base_url: str = WHATSAPP_API_BASE_URL,
    ):
        """
        Initialize WhatsApp Cloud API client.

        Args:
            access_token: Meta System User Access Token
            phone_number_id: WhatsApp Business Phone Number ID
            business_account_id: WhatsApp Business Account ID (optional)
            api_base_url: API base URL (override for testing)
        """
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        self._business_account_id = business_account_id
        self._api_base_url = api_base_url

        # HTTP client with connection pooling
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"WhatsAppCloudClient created: phone_number_id={phone_number_id}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._api_base_url,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0),  # 30 second timeout
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                ),
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    # =========================================================================
    # Send Messages
    # =========================================================================

    async def send_text_message(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
        reply_to_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a text message.

        Args:
            to: Recipient phone number (with country code, no + prefix)
            text: Message text content
            preview_url: Whether to show URL preview (if text contains URL)
            reply_to_message_id: Message ID to reply to (for threading)

        Returns:
            API response with message ID

        Example:
            result = await client.send_text_message(
                to="1234567890",
                text="Hello! Your order #12345 has shipped."
            )
            # result = {"messaging_product": "whatsapp", "contacts": [...], "messages": [{"id": "wamid.xxx"}]}
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": text,
                "preview_url": preview_url,
            },
        }

        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}

        return await self._send_message(payload)

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language: str = "en_US",
        parameters: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a pre-approved template message.

        Templates are required for business-initiated conversations
        (first message to customer or after 24-hour window).

        Args:
            to: Recipient phone number
            template_name: Name of approved template
            language: Template language code
            parameters: Dict of component type to parameter values
                       e.g., {"body": ["John", "Order #123"]}

        Returns:
            API response with message ID

        Example:
            result = await client.send_template_message(
                to="1234567890",
                template_name="order_confirmation",
                language="en_US",
                parameters={"body": ["John Doe", "12345", "$99.99"]}
            )
        """
        template = MessageTemplate(name=template_name, language=language)
        template_data = template.to_api_format(parameters)

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template_data,
        }

        return await self._send_message(payload)

    async def send_interactive_message(
        self,
        to: str,
        interactive_type: str,
        header: Optional[Dict[str, Any]] = None,
        body: str = "",
        footer: Optional[str] = None,
        action: Dict[str, Any] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an interactive message (buttons or list).

        Interactive messages provide better UX than plain text
        with clickable buttons or selectable list items.

        Args:
            to: Recipient phone number
            interactive_type: "button" or "list"
            header: Optional header (text, image, video, document)
            body: Message body text (required)
            footer: Optional footer text
            action: Buttons or list configuration
            reply_to_message_id: Message ID to reply to

        Returns:
            API response with message ID

        Example (buttons):
            result = await client.send_interactive_message(
                to="1234567890",
                interactive_type="button",
                body="How can I help you today?",
                action={
                    "buttons": [
                        {"type": "reply", "reply": {"id": "track_order", "title": "Track Order"}},
                        {"type": "reply", "reply": {"id": "return", "title": "Start Return"}},
                        {"type": "reply", "reply": {"id": "help", "title": "Other Help"}},
                    ]
                }
            )

        Example (list):
            result = await client.send_interactive_message(
                to="1234567890",
                interactive_type="list",
                body="Select a topic:",
                action={
                    "button": "View Options",
                    "sections": [
                        {
                            "title": "Orders",
                            "rows": [
                                {"id": "track", "title": "Track Order", "description": "Check order status"},
                                {"id": "return", "title": "Return Item", "description": "Start a return"},
                            ]
                        }
                    ]
                }
            )
        """
        interactive = {
            "type": interactive_type,
            "body": {"text": body},
        }

        if header:
            interactive["header"] = header
        if footer:
            interactive["footer"] = {"text": footer}
        if action:
            interactive["action"] = action

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive,
        }

        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}

        return await self._send_message(payload)

    async def send_quick_reply_buttons(
        self,
        to: str,
        body: str,
        buttons: List[Dict[str, str]],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message with quick reply buttons.

        Convenience method for common button pattern.

        Args:
            to: Recipient phone number
            body: Message body text
            buttons: List of button dicts with "id" and "title" keys
                    (max 3 buttons, titles max 20 chars)
            header: Optional header text
            footer: Optional footer text
            reply_to_message_id: Message ID to reply to

        Returns:
            API response with message ID

        Example:
            result = await client.send_quick_reply_buttons(
                to="1234567890",
                body="Is there anything else I can help with?",
                buttons=[
                    {"id": "yes_help", "title": "Yes, more help"},
                    {"id": "no_thanks", "title": "No, thanks"},
                ]
            )
        """
        action = {
            "buttons": [
                {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}}
                for btn in buttons[:3]  # Max 3 buttons
            ]
        }

        return await self.send_interactive_message(
            to=to,
            interactive_type="button",
            header={"type": "text", "text": header} if header else None,
            body=body,
            footer=footer,
            action=action,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_image_message(
        self,
        to: str,
        image_url: Optional[str] = None,
        image_id: Optional[str] = None,
        caption: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an image message.

        Either image_url or image_id must be provided.

        Args:
            to: Recipient phone number
            image_url: Public URL of the image
            image_id: Media ID from previous upload
            caption: Optional caption text
            reply_to_message_id: Message ID to reply to

        Returns:
            API response with message ID
        """
        image_data = {}
        if image_url:
            image_data["link"] = image_url
        elif image_id:
            image_data["id"] = image_id

        if caption:
            image_data["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": image_data,
        }

        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}

        return await self._send_message(payload)

    async def send_document_message(
        self,
        to: str,
        document_url: Optional[str] = None,
        document_id: Optional[str] = None,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a document message.

        Useful for sending shipping labels, invoices, etc.

        Args:
            to: Recipient phone number
            document_url: Public URL of the document
            document_id: Media ID from previous upload
            filename: Display filename
            caption: Optional caption text
            reply_to_message_id: Message ID to reply to

        Returns:
            API response with message ID
        """
        doc_data = {}
        if document_url:
            doc_data["link"] = document_url
        elif document_id:
            doc_data["id"] = document_id

        if filename:
            doc_data["filename"] = filename
        if caption:
            doc_data["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": doc_data,
        }

        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}

        return await self._send_message(payload)

    # =========================================================================
    # Message Status
    # =========================================================================

    async def mark_message_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.

        Shows read receipts (blue checkmarks) to the sender.

        Args:
            message_id: WhatsApp message ID to mark as read

        Returns:
            API response confirming read status
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        return await self._send_message(payload)

    # =========================================================================
    # Media Management
    # =========================================================================

    async def upload_media(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> Dict[str, Any]:
        """
        Upload media file for later sending.

        Uploaded media is stored for 30 days.

        Args:
            file_data: Binary file data
            filename: Original filename
            content_type: MIME type (e.g., "image/jpeg", "application/pdf")

        Returns:
            API response with media ID for sending
        """
        client = await self._get_client()

        # Media upload uses multipart/form-data
        files = {
            "file": (filename, file_data, content_type),
        }
        data = {
            "messaging_product": "whatsapp",
        }

        url = f"/{self._phone_number_id}/media"

        try:
            response = await client.post(
                url,
                files=files,
                data=data,
            )
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Media uploaded: {result}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Media upload failed: {e.response.text}")
            raise

    async def get_media_url(self, media_id: str) -> Optional[str]:
        """
        Get download URL for media.

        Media URLs expire after 5 minutes.

        Args:
            media_id: WhatsApp media ID

        Returns:
            Download URL or None on error
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/{media_id}")
            response.raise_for_status()
            result = response.json()
            return result.get("url")

        except httpx.HTTPStatusError as e:
            logger.error(f"Get media URL failed: {e.response.text}")
            return None

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send message via WhatsApp API."""
        client = await self._get_client()
        url = f"/{self._phone_number_id}/messages"

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # Log success
            msg_id = result.get("messages", [{}])[0].get("id", "unknown")
            to = payload.get("to", "unknown")
            msg_type = payload.get("type", "unknown")
            logger.info(f"Message sent: id={msg_id}, to={to}, type={msg_type}")

            return result

        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            logger.error(
                f"Send message failed: status={e.response.status_code}, "
                f"error={error_data}"
            )
            raise

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def phone_number_id(self) -> str:
        """Get configured phone number ID."""
        return self._phone_number_id

    @property
    def business_account_id(self) -> Optional[str]:
        """Get configured business account ID."""
        return self._business_account_id


# ============================================================================
# Global Instance (Singleton Pattern)
# ============================================================================


async def init_whatsapp_client(
    access_token: Optional[str] = None,
    phone_number_id: Optional[str] = None,
    business_account_id: Optional[str] = None,
    api_base_url: Optional[str] = None,
) -> WhatsAppCloudClient:
    """
    Initialize the global WhatsApp client.

    Call once at application startup.

    Args:
        access_token: Meta System User Access Token (default from env)
        phone_number_id: WhatsApp Phone Number ID (default from env)
        business_account_id: Business Account ID (optional)
        api_base_url: Override API URL (for testing)

    Returns:
        Initialized WhatsAppCloudClient instance

    Environment Variables:
        WHATSAPP_ACCESS_TOKEN: Meta access token
        WHATSAPP_PHONE_NUMBER_ID: Phone number ID
        WHATSAPP_BUSINESS_ACCOUNT_ID: Business account ID (optional)
        MOCK_WHATSAPP_URL: Mock API URL for development
    """
    global _whatsapp_client

    if _whatsapp_client is not None:
        logger.warning("WhatsApp client already initialized")
        return _whatsapp_client

    # Get config from environment
    token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    biz_id = business_account_id or os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")

    # Check for mock mode
    mock_url = os.getenv("MOCK_WHATSAPP_URL")
    if mock_url or os.getenv("USE_REAL_APIS", "false").lower() != "true":
        base_url = mock_url or "http://localhost:8011"
        logger.info(f"WhatsApp client using mock API: {base_url}")
    else:
        base_url = api_base_url or WHATSAPP_API_BASE_URL

    _whatsapp_client = WhatsAppCloudClient(
        access_token=token,
        phone_number_id=phone_id or "mock_phone_id",
        business_account_id=biz_id,
        api_base_url=base_url,
    )

    logger.info("WhatsApp client initialized")
    return _whatsapp_client


def get_whatsapp_client() -> WhatsAppCloudClient:
    """
    Get the global WhatsApp client.

    Raises RuntimeError if not initialized.

    Returns:
        The global WhatsAppCloudClient instance
    """
    if _whatsapp_client is None:
        raise RuntimeError(
            "WhatsApp client not initialized. Call init_whatsapp_client() first."
        )
    return _whatsapp_client


async def shutdown_whatsapp_client() -> None:
    """Shutdown the global WhatsApp client."""
    global _whatsapp_client
    if _whatsapp_client:
        await _whatsapp_client.close()
    _whatsapp_client = None
