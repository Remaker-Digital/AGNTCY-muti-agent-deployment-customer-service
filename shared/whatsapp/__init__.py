# ============================================================================
# WhatsApp Business API Module - Phase 6
# ============================================================================
# Purpose: WhatsApp Business Cloud API integration for multi-channel support
#
# This module provides:
# - WhatsApp Cloud API client for sending messages
# - Message templates for proactive notifications
# - Webhook handler for receiving messages
# - Session bridging for cross-channel conversations
#
# Architecture Decision:
# - Use Meta's Cloud API (hosted) for simplicity and lower setup cost
# - Message templates required for business-initiated conversations
# - Webhook-based message reception with signature verification
# - Sessions linked to CustomerSession for unified history
#
# Channel Integration:
# - WhatsApp messages routed to same agent pipeline as web widget
# - Same customer_id links sessions across channels
# - AI has full conversation history regardless of originating channel
#
# Related Documentation:
# - WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
# - Message Templates: https://developers.facebook.com/docs/whatsapp/message-templates
# - Webhooks: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q1.C, Q1.D)
#
# Budget Impact:
# - WhatsApp Business API: ~$15-25/month (conversation-based pricing)
# - User-initiated conversations: ~$0.01-0.06 (varies by country)
# - Business-initiated conversations: ~$0.02-0.10 (varies by country)
# ============================================================================

from .models import (
    # Enums
    MessageType,
    MessageStatus,
    ConversationType,
    # Models
    WhatsAppContact,
    WhatsAppMessage,
    MessageTemplate,
    WebhookEvent,
    # Pre-defined templates
    ORDER_CONFIRMATION_TEMPLATE,
    SHIPPING_UPDATE_TEMPLATE,
    ORDER_STATUS_TEMPLATE,
    WELCOME_TEMPLATE,
)

from .client import (
    WhatsAppCloudClient,
    init_whatsapp_client,
    get_whatsapp_client,
    shutdown_whatsapp_client,
)

from .webhook_handler import (
    WhatsAppWebhookHandler,
    WhatsAppSessionBridge,
    get_webhook_handler,
    get_session_bridge,
)

__all__ = [
    # Enums
    "MessageType",
    "MessageStatus",
    "ConversationType",
    # Models
    "WhatsAppContact",
    "WhatsAppMessage",
    "MessageTemplate",
    "WebhookEvent",
    # Pre-defined templates
    "ORDER_CONFIRMATION_TEMPLATE",
    "SHIPPING_UPDATE_TEMPLATE",
    "ORDER_STATUS_TEMPLATE",
    "WELCOME_TEMPLATE",
    # Client
    "WhatsAppCloudClient",
    "init_whatsapp_client",
    "get_whatsapp_client",
    "shutdown_whatsapp_client",
    # Webhook Handler
    "WhatsAppWebhookHandler",
    "WhatsAppSessionBridge",
    "get_webhook_handler",
    "get_session_bridge",
]
