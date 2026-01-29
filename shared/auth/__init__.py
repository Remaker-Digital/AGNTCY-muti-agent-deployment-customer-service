# ============================================================================
# Customer Authentication Module - Phase 6
# ============================================================================
# Purpose: Shopify Customer Accounts API integration for authenticated sessions
#
# This module provides:
# - Tiered access model (Anonymous → Identified → Authenticated)
# - Shopify Customer Accounts API OAuth flow
# - Cross-device session persistence via Cosmos DB
# - Secure token storage and refresh
#
# Architecture Decision:
# - Shopify-first approach (Phase 6), WordPress/WooCommerce in Phase 7
# - Tokens stored in Cosmos DB with encryption-at-rest (Azure managed keys)
# - Session state includes customer profile for personalized service
#
# Related Documentation:
# - Shopify Customer Accounts API: https://shopify.dev/docs/api/customer
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q5.A, Q5.C)
# - Session Data Model: docs/data-staleness-requirements.md
#
# Budget Impact:
# - Cosmos DB storage: +$5-10/month for session data
# - No additional API costs (Shopify Customer Accounts is free)
# ============================================================================

from .models import (
    AuthLevel,
    CustomerSession,
    ShopifyCustomer,
    SessionToken,
    SessionState,
    create_anonymous_session,
    create_identified_session,
)
from .session_manager import SessionManager, get_session_manager, init_session_manager
from .shopify_customer_api import (
    ShopifyCustomerAccountsClient,
    get_shopify_customer_client,
)

__all__ = [
    # Enums
    "AuthLevel",
    "SessionState",
    # Models
    "CustomerSession",
    "ShopifyCustomer",
    "SessionToken",
    # Factories
    "create_anonymous_session",
    "create_identified_session",
    # Session Manager
    "SessionManager",
    "get_session_manager",
    "init_session_manager",
    # Shopify Client
    "ShopifyCustomerAccountsClient",
    "get_shopify_customer_client",
]
