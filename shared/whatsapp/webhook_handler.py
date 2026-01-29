# ============================================================================
# WhatsApp Webhook Handler - Phase 6
# ============================================================================
# Purpose: Process incoming WhatsApp webhooks and route to agents
#
# Webhook Types:
# - messages: New message received from customer
# - statuses: Message delivery status update (sent, delivered, read)
# - errors: Error notifications
#
# Security:
# - Verify webhook signature using X-Hub-Signature-256 header
# - Verify token matches configured WEBHOOK_VERIFY_TOKEN
# - Respond to verification challenge with hub.challenge
#
# Integration:
# - Creates/resumes CustomerSession for WhatsApp conversations
# - Routes messages to Intent Classification Agent
# - Links sessions across channels (web ↔ WhatsApp)
#
# Related Documentation:
# - WhatsApp Webhooks: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
# - Webhook Security: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/signature-verification
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q1.C, Q1.D)
#
# Performance Targets:
# - Webhook processing: <200ms P95 (acknowledgment)
# - Message routing: <500ms to agent (async)
# ============================================================================

import hashlib
import hmac
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Awaitable

from .models import (
    MessageStatus,
    MessageType,
    WebhookEvent,
    WhatsAppContact,
    WhatsAppMessage,
)
from .client import get_whatsapp_client

logger = logging.getLogger(__name__)

# Type alias for message handler callback
MessageHandler = Callable[[WhatsAppMessage], Awaitable[None]]
StatusHandler = Callable[[Dict[str, Any]], Awaitable[None]]
ErrorHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class WhatsAppWebhookHandler:
    """
    Handles incoming WhatsApp webhooks.

    Responsibilities:
    - Verify webhook signatures for security
    - Parse webhook payloads into typed events
    - Route messages to registered handlers
    - Update message delivery status
    - Handle errors and retries

    Webhook Flow:
    1. Verify signature (X-Hub-Signature-256)
    2. Parse payload into WebhookEvent objects
    3. For messages: Create/resume session, route to handler
    4. For statuses: Update message status in storage
    5. For errors: Log and notify

    Usage:
        handler = WhatsAppWebhookHandler(verify_token="my_secret_token")

        @handler.on_message
        async def handle_message(message: WhatsAppMessage):
            # Process incoming message
            response = await process_with_agents(message)
            await send_reply(message.wa_id, response)

        # In FastAPI endpoint:
        @app.post("/webhooks/whatsapp")
        async def whatsapp_webhook(request: Request):
            return await handler.handle_webhook(request)
    """

    def __init__(
        self,
        verify_token: Optional[str] = None,
        app_secret: Optional[str] = None,
    ):
        """
        Initialize webhook handler.

        Args:
            verify_token: Token for webhook verification challenge
            app_secret: App secret for signature verification
        """
        self._verify_token = verify_token or os.getenv(
            "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "agntcy_webhook_verify_token"
        )
        self._app_secret = app_secret or os.getenv("WHATSAPP_APP_SECRET", "")

        # Registered handlers
        self._message_handlers: List[MessageHandler] = []
        self._status_handlers: List[StatusHandler] = []
        self._error_handlers: List[ErrorHandler] = []

        logger.info("WhatsAppWebhookHandler initialized")

    # =========================================================================
    # Handler Registration
    # =========================================================================

    def on_message(self, handler: MessageHandler) -> MessageHandler:
        """
        Decorator to register a message handler.

        Usage:
            @webhook_handler.on_message
            async def handle_message(message: WhatsAppMessage):
                print(f"Received: {message.text_body}")
        """
        self._message_handlers.append(handler)
        return handler

    def on_status(self, handler: StatusHandler) -> StatusHandler:
        """
        Decorator to register a status handler.

        Usage:
            @webhook_handler.on_status
            async def handle_status(status: Dict[str, Any]):
                print(f"Message {status['id']} is now {status['status']}")
        """
        self._status_handlers.append(handler)
        return handler

    def on_error(self, handler: ErrorHandler) -> ErrorHandler:
        """
        Decorator to register an error handler.

        Usage:
            @webhook_handler.on_error
            async def handle_error(error: Dict[str, Any]):
                logger.error(f"WhatsApp error: {error}")
        """
        self._error_handlers.append(handler)
        return handler

    def register_message_handler(self, handler: MessageHandler) -> None:
        """Register a message handler programmatically."""
        self._message_handlers.append(handler)

    def register_status_handler(self, handler: StatusHandler) -> None:
        """Register a status handler programmatically."""
        self._status_handlers.append(handler)

    def register_error_handler(self, handler: ErrorHandler) -> None:
        """Register an error handler programmatically."""
        self._error_handlers.append(handler)

    # =========================================================================
    # Webhook Verification
    # =========================================================================

    def verify_webhook(
        self,
        mode: str,
        token: str,
        challenge: str,
    ) -> Optional[str]:
        """
        Verify webhook subscription request.

        Called when Meta sends GET request to verify webhook endpoint.

        Args:
            mode: hub.mode parameter (should be "subscribe")
            token: hub.verify_token parameter (should match our token)
            challenge: hub.challenge parameter (return to verify)

        Returns:
            Challenge string if verification succeeds, None otherwise
        """
        if mode == "subscribe" and token == self._verify_token:
            logger.info("Webhook verified successfully")
            return challenge

        logger.warning(
            f"Webhook verification failed: mode={mode}, "
            f"token_match={token == self._verify_token}"
        )
        return None

    def verify_signature(
        self,
        payload: bytes,
        signature_header: str,
    ) -> bool:
        """
        Verify webhook payload signature.

        Meta signs payloads with HMAC SHA-256 using the app secret.

        Args:
            payload: Raw request body bytes
            signature_header: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self._app_secret:
            # Skip verification if no secret configured (development mode)
            logger.warning(
                "Skipping signature verification - no WHATSAPP_APP_SECRET configured"
            )
            return True

        if not signature_header:
            logger.warning("Missing X-Hub-Signature-256 header")
            return False

        # Parse signature (format: "sha256=...")
        parts = signature_header.split("=", 1)
        if len(parts) != 2 or parts[0] != "sha256":
            logger.warning(f"Invalid signature format: {signature_header}")
            return False

        expected_signature = parts[1]

        # Calculate HMAC SHA-256
        mac = hmac.new(
            self._app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        )
        calculated_signature = mac.hexdigest()

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(calculated_signature, expected_signature)

        if not is_valid:
            logger.warning("Webhook signature verification failed")

        return is_valid

    # =========================================================================
    # Webhook Processing
    # =========================================================================

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature_header: Optional[str] = None,
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, str]:
        """
        Process incoming webhook payload.

        Args:
            payload: Parsed JSON payload
            signature_header: X-Hub-Signature-256 header (optional for dev)
            raw_body: Raw request body for signature verification

        Returns:
            Response dict to return to Meta
        """
        # Verify signature if raw body provided
        if raw_body and signature_header:
            if not self.verify_signature(raw_body, signature_header):
                return {"status": "error", "message": "Invalid signature"}

        # Parse webhook events
        events = WebhookEvent.from_webhook_payload(payload)

        if not events:
            logger.debug("No events in webhook payload")
            return {"status": "ok"}

        logger.info(f"Processing {len(events)} webhook events")

        # Process each event
        for event in events:
            try:
                await self._process_event(event)
            except Exception as e:
                logger.error(f"Error processing webhook event: {e}", exc_info=True)
                # Continue processing other events

        return {"status": "ok"}

    async def _process_event(self, event: WebhookEvent) -> None:
        """Process a single webhook event."""
        if event.event_type == "messages" and event.message:
            await self._handle_message_event(event.message)

        elif event.event_type == "statuses" and event.status_update:
            await self._handle_status_event(event.status_update)

        elif event.event_type == "errors" and event.error:
            await self._handle_error_event(event.error)

    async def _handle_message_event(self, message: WhatsAppMessage) -> None:
        """Handle incoming message event."""
        logger.info(
            f"Received message: id={message.message_id}, "
            f"from={message.wa_id}, type={message.type.value}"
        )

        # Mark message as read (shows blue checkmarks to sender)
        try:
            client = get_whatsapp_client()
            await client.mark_message_read(message.message_id)
        except Exception as e:
            logger.warning(f"Failed to mark message as read: {e}")

        # Call registered handlers
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}", exc_info=True)

    async def _handle_status_event(self, status_update: Dict[str, Any]) -> None:
        """Handle message status update event."""
        message_id = status_update.get("id", "unknown")
        status = status_update.get("status", "unknown")

        logger.debug(f"Status update: message={message_id}, status={status}")

        # Call registered handlers
        for handler in self._status_handlers:
            try:
                await handler(status_update)
            except Exception as e:
                logger.error(f"Status handler error: {e}", exc_info=True)

    async def _handle_error_event(self, error: Dict[str, Any]) -> None:
        """Handle error event."""
        error_code = error.get("code", "unknown")
        error_message = error.get("message", "Unknown error")

        logger.error(f"WhatsApp error: code={error_code}, message={error_message}")

        # Call registered handlers
        for handler in self._error_handlers:
            try:
                await handler(error)
            except Exception as e:
                logger.error(f"Error handler error: {e}", exc_info=True)


# ============================================================================
# Session Bridge - Cross-Channel Session Linking
# ============================================================================


class WhatsAppSessionBridge:
    """
    Bridges WhatsApp sessions with CustomerSession.

    Enables unified conversation history across channels:
    - Customer starts on web widget → continues on WhatsApp
    - Customer starts on WhatsApp → continues on web
    - Same customer_id links all sessions

    Session Linking Strategy:
    1. WhatsApp message arrives with phone number
    2. Look up existing session by phone in Cosmos DB
    3. If found and authenticated: Link to customer_id
    4. If found but anonymous: Upgrade to identified using phone
    5. If not found: Create new session with channel="whatsapp"

    Cross-Channel Context:
    - Same context_id continues conversation
    - AI has full history regardless of channel
    - Messages tagged with originating channel
    """

    def __init__(self, session_manager=None):
        """
        Initialize session bridge.

        Args:
            session_manager: SessionManager instance (auto-resolved if None)
        """
        self._session_manager = session_manager

    async def _get_session_manager(self):
        """Lazily get session manager."""
        if self._session_manager is None:
            from shared.auth import get_session_manager
            try:
                self._session_manager = get_session_manager()
            except RuntimeError:
                logger.warning("SessionManager not available")
                return None
        return self._session_manager

    async def get_or_create_session(
        self,
        phone_number: str,
        contact_name: Optional[str] = None,
    ) -> Optional[Any]:  # Returns CustomerSession
        """
        Get existing session or create new one for WhatsApp user.

        Args:
            phone_number: Customer phone number (wa_id)
            contact_name: Customer display name from WhatsApp

        Returns:
            CustomerSession (existing or new)
        """
        manager = await self._get_session_manager()
        if not manager:
            logger.warning("Cannot get/create session - manager not available")
            return None

        # Try to find existing session by phone
        # First check if phone matches identified_phone in any session
        session = await self._find_session_by_phone(phone_number)

        if session:
            logger.info(f"Found existing session for phone {phone_number[-4:]}")
            return session

        # Create new session for WhatsApp channel
        session = await manager.create_session(
            channel="whatsapp",
            device_id=f"wa_{phone_number}",  # Use phone as device ID
            user_agent=f"WhatsApp/{contact_name or 'User'}",
        )

        # Upgrade to identified with phone number
        session = await manager.upgrade_to_identified(
            session.session_id,
            phone=phone_number,
        )

        logger.info(f"Created new WhatsApp session for phone {phone_number[-4:]}")
        return session

    async def _find_session_by_phone(self, phone_number: str) -> Optional[Any]:
        """Find session by phone number."""
        manager = await self._get_session_manager()
        if not manager:
            return None

        # Try device_id lookup first (WhatsApp-originated sessions)
        session = await manager.get_session_by_device(f"wa_{phone_number}")
        if session:
            return session

        # Could also search by identified_phone across all sessions
        # This would require a cross-partition query in Cosmos DB
        # For now, we rely on device_id matching
        return None

    async def link_session_to_customer(
        self,
        session_id: str,
        customer_id: str,
    ) -> Optional[Any]:
        """
        Link WhatsApp session to authenticated customer.

        Called when customer authenticates on web while having
        an active WhatsApp session.

        Args:
            session_id: WhatsApp session ID
            customer_id: Shopify customer ID

        Returns:
            Updated session or None
        """
        manager = await self._get_session_manager()
        if not manager:
            return None

        # This would update the session's customer_id
        # For full implementation, see shared/auth/session_manager.py
        logger.info(f"Linking session {session_id} to customer {customer_id}")
        return None  # Placeholder - full implementation requires session update


# ============================================================================
# Global Instances
# ============================================================================

_webhook_handler: Optional[WhatsAppWebhookHandler] = None
_session_bridge: Optional[WhatsAppSessionBridge] = None


def get_webhook_handler() -> WhatsAppWebhookHandler:
    """Get or create the global webhook handler."""
    global _webhook_handler
    if _webhook_handler is None:
        _webhook_handler = WhatsAppWebhookHandler()
    return _webhook_handler


def get_session_bridge() -> WhatsAppSessionBridge:
    """Get or create the global session bridge."""
    global _session_bridge
    if _session_bridge is None:
        _session_bridge = WhatsAppSessionBridge()
    return _session_bridge
