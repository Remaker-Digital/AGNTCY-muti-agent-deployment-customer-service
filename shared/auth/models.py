# ============================================================================
# Customer Session Models - Phase 6
# ============================================================================
# Purpose: Data models for customer authentication and session management
#
# Tiered Access Model:
# - ANONYMOUS: No identification, limited features (product info, general FAQ)
# - IDENTIFIED: Email/phone provided, can retrieve orders by lookup
# - AUTHENTICATED: Shopify login, full account access, saved payments (Phase 8)
#
# Why tiered access?
# - Balances UX (low friction) with security (sensitive operations require auth)
# - 60-70% of support queries can be handled at Anonymous/Identified level
# - Authentication required for: order modifications, returns, payment access
#
# Architecture Decision:
# - Sessions stored in Cosmos DB with customer_id as partition key
# - Cross-device: Same customer_id links sessions across devices
# - Token refresh: Access tokens expire, refresh tokens enable seamless renewal
#
# Related Documentation:
# - Shopify Customer Accounts API: https://shopify.dev/docs/api/customer
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q5.A, Q5.C)
# ============================================================================

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class AuthLevel(str, Enum):
    """
    Customer authentication level for tiered access control.

    Progression: ANONYMOUS → IDENTIFIED → AUTHENTICATED

    Each level unlocks additional capabilities:
    - ANONYMOUS: Product info, FAQs, store policies, general support
    - IDENTIFIED: Order status by email/phone, shipping tracking
    - AUTHENTICATED: Full account access, order history, saved payments, returns
    """

    ANONYMOUS = "anonymous"  # No identification provided
    IDENTIFIED = "identified"  # Email/phone provided, not verified
    AUTHENTICATED = "authenticated"  # Shopify login verified


class SessionState(str, Enum):
    """
    Session lifecycle states.

    Flow: ACTIVE → EXPIRED (or REVOKED for logout)
    """

    ACTIVE = "active"  # Session is valid and usable
    EXPIRED = "expired"  # Session has timed out
    REVOKED = "revoked"  # User logged out or session invalidated


@dataclass
class SessionToken:
    """
    OAuth token for Shopify Customer Accounts API.

    Shopify uses OAuth 2.0 with refresh tokens for session persistence.
    Access tokens expire after 1 hour; refresh tokens last 14 days.

    Token Storage:
    - Tokens stored in Cosmos DB with encryption-at-rest
    - Never logged or exposed in error messages
    - Refresh before expiry to maintain seamless experience

    API Reference:
    - https://shopify.dev/docs/api/customer#authentication
    """

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: str = ""  # ISO 8601 timestamp
    scope: str = ""  # OAuth scopes granted
    id_token: Optional[str] = None  # OpenID Connect ID token (if enabled)

    def is_expired(self) -> bool:
        """Check if access token has expired."""
        if not self.expires_at:
            return True
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        # Consider expired 5 minutes before actual expiry for safety margin
        return datetime.now(expiry.tzinfo) >= expiry - timedelta(minutes=5)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionToken":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ShopifyCustomer:
    """
    Shopify customer profile data.

    Retrieved from Shopify Customer Accounts API after authentication.
    Used for personalization and order lookups.

    PII Handling:
    - All PII fields are tokenized before sending to external AI services
    - See: shared/tokenization/tokenizer.py
    - Original values stored in Cosmos DB for display only

    API Reference:
    - https://shopify.dev/docs/api/customer#retrieve-customer-profile
    """

    id: str  # Shopify customer ID (e.g., "gid://shopify/Customer/12345")
    email: str
    first_name: str = ""
    last_name: str = ""
    phone: Optional[str] = None
    accepts_marketing: bool = False
    created_at: str = ""  # Account creation date
    orders_count: int = 0  # Total orders placed
    total_spent: str = "0.00"  # Lifetime value
    default_address: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)  # VIP, Wholesale, etc.

    @property
    def full_name(self) -> str:
        """Get full name for display."""
        return f"{self.first_name} {self.last_name}".strip() or "Customer"

    @property
    def is_vip(self) -> bool:
        """Check if customer has VIP tag (merchant-defined)."""
        return "VIP" in self.tags or "vip" in self.tags

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShopifyCustomer":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class CustomerSession:
    """
    Customer session for authenticated interactions.

    Sessions are created at conversation start and persist across:
    - Multiple messages in a conversation (context_id)
    - Multiple devices for same customer (customer_id)
    - Multiple channels (web, WhatsApp) after Phase 6

    Cosmos DB Schema:
    - Container: sessions
    - Partition Key: /customer_id (enables cross-device lookup)
    - TTL: 7 days (configurable, auto-cleanup of stale sessions)

    Session Linking:
    - Anonymous sessions use device_id as partition key
    - When customer authenticates, session is linked to customer_id
    - Historical sessions visible for same customer_id (cross-device)

    Related: docs/data-staleness-requirements.md#session-staleness
    """

    session_id: str  # Unique session identifier
    customer_id: str  # Shopify customer ID (or device_id for anonymous)
    auth_level: AuthLevel
    state: SessionState = SessionState.ACTIVE

    # Customer profile (populated after authentication)
    customer: Optional[ShopifyCustomer] = None

    # OAuth tokens (populated after authentication)
    token: Optional[SessionToken] = None

    # Session metadata
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    updated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    expires_at: str = ""  # Session expiry (7 days default)

    # Channel and device tracking
    channel: str = "web"  # web, whatsapp, api
    device_id: Optional[str] = None  # For anonymous session linking
    user_agent: Optional[str] = None  # Browser/device info

    # Conversation context
    current_context_id: Optional[str] = None  # Active conversation thread
    conversation_count: int = 0  # Conversations in this session

    # Identification data (IDENTIFIED level)
    identified_email: Optional[str] = None  # Email provided but not verified
    identified_phone: Optional[str] = None  # Phone provided but not verified

    def __post_init__(self):
        """Set default expiry if not provided."""
        if not self.expires_at:
            expiry = datetime.utcnow() + timedelta(days=7)
            self.expires_at = expiry.isoformat() + "Z"

    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.state != SessionState.ACTIVE:
            return True
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(expiry.tzinfo) >= expiry

    def is_authenticated(self) -> bool:
        """Check if session is fully authenticated."""
        return self.auth_level == AuthLevel.AUTHENTICATED and self.state == SessionState.ACTIVE

    def can_access_orders(self) -> bool:
        """Check if session has permission to access order details."""
        return self.auth_level in (AuthLevel.IDENTIFIED, AuthLevel.AUTHENTICATED)

    def can_modify_orders(self) -> bool:
        """Check if session has permission to modify orders."""
        return self.is_authenticated()

    def can_access_payments(self) -> bool:
        """Check if session has permission to access saved payments (Phase 8)."""
        return self.is_authenticated()

    def upgrade_to_identified(self, email: Optional[str] = None, phone: Optional[str] = None):
        """
        Upgrade anonymous session to identified level.

        Called when customer provides email/phone for order lookup.
        """
        if self.auth_level == AuthLevel.ANONYMOUS:
            self.auth_level = AuthLevel.IDENTIFIED
            self.identified_email = email
            self.identified_phone = phone
            self.updated_at = datetime.utcnow().isoformat() + "Z"

    def upgrade_to_authenticated(self, customer: ShopifyCustomer, token: SessionToken):
        """
        Upgrade session to authenticated level.

        Called after successful Shopify Customer Accounts API login.
        """
        self.auth_level = AuthLevel.AUTHENTICATED
        self.customer = customer
        self.customer_id = customer.id  # Link to Shopify customer ID
        self.token = token
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def refresh_token(self, new_token: SessionToken):
        """Update session with refreshed OAuth tokens."""
        self.token = new_token
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def revoke(self):
        """Revoke session (logout)."""
        self.state = SessionState.REVOKED
        self.token = None
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def touch(self):
        """Update last activity timestamp."""
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Cosmos DB storage."""
        data = {
            "id": self.session_id,  # Cosmos DB document ID
            "session_id": self.session_id,
            "customer_id": self.customer_id,
            "auth_level": self.auth_level.value,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "channel": self.channel,
            "device_id": self.device_id,
            "user_agent": self.user_agent,
            "current_context_id": self.current_context_id,
            "conversation_count": self.conversation_count,
            "identified_email": self.identified_email,
            "identified_phone": self.identified_phone,
        }

        # Include nested objects if present
        if self.customer:
            data["customer"] = self.customer.to_dict()
        if self.token:
            data["token"] = self.token.to_dict()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomerSession":
        """Create from Cosmos DB document."""
        # Extract nested objects
        customer_data = data.pop("customer", None)
        token_data = data.pop("token", None)

        # Convert enum values
        data["auth_level"] = AuthLevel(data["auth_level"])
        data["state"] = SessionState(data["state"])

        # Remove Cosmos DB metadata
        data.pop("id", None)
        data.pop("_rid", None)
        data.pop("_self", None)
        data.pop("_etag", None)
        data.pop("_attachments", None)
        data.pop("_ts", None)

        # Create session
        session = cls(**data)

        # Attach nested objects
        if customer_data:
            session.customer = ShopifyCustomer.from_dict(customer_data)
        if token_data:
            session.token = SessionToken.from_dict(token_data)

        return session


# ============================================================================
# Factory Functions
# ============================================================================
# These create properly initialized sessions for common scenarios.
# ============================================================================


def create_anonymous_session(
    device_id: Optional[str] = None,
    channel: str = "web",
    user_agent: Optional[str] = None,
) -> CustomerSession:
    """
    Create a new anonymous session.

    Called when a new conversation starts without authentication.
    Uses device_id for session linking until customer authenticates.

    Args:
        device_id: Device/browser fingerprint (optional)
        channel: Channel type (web, whatsapp, api)
        user_agent: Browser/client user agent string

    Returns:
        New CustomerSession at ANONYMOUS auth level
    """
    session_id = f"sess-{uuid.uuid4().hex[:16]}"

    # Use device_id as customer_id for anonymous sessions
    # This enables session linking when same device returns
    customer_id = device_id or f"anon-{uuid.uuid4().hex[:12]}"

    return CustomerSession(
        session_id=session_id,
        customer_id=customer_id,
        auth_level=AuthLevel.ANONYMOUS,
        channel=channel,
        device_id=device_id,
        user_agent=user_agent,
    )


def create_identified_session(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    device_id: Optional[str] = None,
    channel: str = "web",
) -> CustomerSession:
    """
    Create a session at IDENTIFIED level.

    Called when customer provides email/phone for order lookup
    without full authentication.

    Args:
        email: Customer email (for order lookup)
        phone: Customer phone (alternative lookup)
        device_id: Device/browser fingerprint
        channel: Channel type

    Returns:
        New CustomerSession at IDENTIFIED auth level
    """
    session = create_anonymous_session(
        device_id=device_id,
        channel=channel,
    )
    session.upgrade_to_identified(email=email, phone=phone)
    return session
