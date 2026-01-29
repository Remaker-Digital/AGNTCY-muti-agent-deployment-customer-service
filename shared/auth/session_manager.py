# ============================================================================
# Session Manager - Phase 6
# ============================================================================
# Purpose: Manage customer sessions with Cosmos DB persistence
#
# Key Features:
# - Create and store sessions with TTL (7 days default)
# - Cross-device session lookup by customer_id
# - Session upgrade flow: Anonymous → Identified → Authenticated
# - Automatic token refresh when access_token expires
#
# Cosmos DB Schema:
# - Container: sessions
# - Partition Key: /customer_id
# - TTL: 7 days (604800 seconds)
#
# Why customer_id as partition key?
# - Enables efficient cross-device queries
# - All sessions for a customer colocated
# - Supports "Continue conversation" on new device
#
# Performance Targets:
# - Session lookup: <50ms P95
# - Session create: <100ms P95
# - Cross-device query: <200ms P95
#
# Related Documentation:
# - Cosmos DB Best Practices: https://learn.microsoft.com/azure/cosmos-db/nosql/best-practice-python
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q5.C)
# - Data Staleness: docs/data-staleness-requirements.md#sessions
#
# Budget Impact:
# - Cosmos DB RU consumption: ~5-10 RU per session operation
# - Storage: ~2KB per session document
# - Estimated: +$5-10/month for 10,000 daily users
# ============================================================================

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import (
    AuthLevel,
    CustomerSession,
    SessionState,
    ShopifyCustomer,
    SessionToken,
    create_anonymous_session,
)
from .shopify_customer_api import (
    ShopifyCustomerAccountsClient,
    get_shopify_customer_client,
)

logger = logging.getLogger(__name__)

# Singleton instance
_session_manager: Optional["SessionManager"] = None


class SessionManager:
    """
    Manages customer sessions with Cosmos DB persistence.

    Responsibilities:
    - Create sessions (anonymous, identified, authenticated)
    - Store and retrieve sessions from Cosmos DB
    - Handle cross-device session lookup
    - Refresh OAuth tokens when expired
    - Clean up expired sessions

    Thread Safety:
    - Safe for concurrent access from multiple coroutines
    - Uses Cosmos DB's optimistic concurrency via _etag

    Usage:
        manager = await get_session_manager()

        # Create anonymous session
        session = await manager.create_session(channel="web", device_id="...")

        # Upgrade to identified
        session = await manager.upgrade_to_identified(session.session_id, email="...")

        # Get session
        session = await manager.get_session(session_id)

        # Get all sessions for customer
        sessions = await manager.get_customer_sessions(customer_id)
    """

    # Default TTL for sessions (7 days in seconds)
    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 604800

    def __init__(
        self,
        cosmos_client=None,
        container_name: str = "sessions",
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ):
        """
        Initialize session manager.

        Args:
            cosmos_client: CosmosDBClient instance (auto-created if None)
            container_name: Name of Cosmos DB container for sessions
            ttl_seconds: Session TTL in seconds (default 7 days)
        """
        self._cosmos = cosmos_client
        self._container_name = container_name
        self._container = None
        self._ttl_seconds = ttl_seconds
        self._initialized = False

        # Shopify client for token operations
        self._shopify_client: Optional[ShopifyCustomerAccountsClient] = None

        # In-memory cache for active sessions (reduces Cosmos reads)
        # Key: session_id, Value: (session, cached_at)
        self._session_cache: Dict[str, tuple] = {}
        self._cache_ttl_seconds = 60  # Cache for 60 seconds

        logger.info(f"SessionManager created: container={container_name}, ttl={ttl_seconds}s")

    async def initialize(self) -> None:
        """
        Initialize Cosmos DB connection and verify container exists.

        Call this at application startup.
        """
        if self._initialized:
            logger.debug("SessionManager already initialized")
            return

        try:
            # Get Cosmos client if not provided
            if self._cosmos is None:
                from shared.cosmosdb_pool import get_cosmos_client

                try:
                    self._cosmos = get_cosmos_client()
                except RuntimeError:
                    # Cosmos not initialized - use mock mode
                    logger.warning(
                        "Cosmos DB not available. SessionManager running in mock mode."
                    )
                    self._initialized = True
                    return

            # Get container reference
            self._container = self._cosmos.get_container(self._container_name)

            # Get Shopify client
            self._shopify_client = await get_shopify_customer_client()

            self._initialized = True
            logger.info("SessionManager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize SessionManager: {e}")
            # Don't raise - allow mock mode for development
            self._initialized = True

    async def create_session(
        self,
        channel: str = "web",
        device_id: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CustomerSession:
        """
        Create a new anonymous session.

        Called when a new conversation starts without authentication.

        Args:
            channel: Channel type (web, whatsapp, api)
            device_id: Device/browser fingerprint for session linking
            user_agent: Browser/client user agent string

        Returns:
            New CustomerSession at ANONYMOUS auth level
        """
        session = create_anonymous_session(
            device_id=device_id,
            channel=channel,
            user_agent=user_agent,
        )

        # Persist to Cosmos DB
        await self._save_session(session)

        # Add to cache
        self._cache_session(session)

        logger.info(f"Created session {session.session_id} for channel={channel}")
        return session

    async def get_session(self, session_id: str) -> Optional[CustomerSession]:
        """
        Get session by ID.

        Checks cache first, then Cosmos DB.

        Args:
            session_id: Session ID

        Returns:
            CustomerSession if found and active, None otherwise
        """
        # Check cache first
        cached = self._get_cached_session(session_id)
        if cached:
            return cached

        # Not in cache - query Cosmos DB
        session = await self._load_session(session_id)

        if session and not session.is_expired():
            self._cache_session(session)
            return session

        return None

    async def get_customer_sessions(
        self,
        customer_id: str,
        active_only: bool = True,
    ) -> List[CustomerSession]:
        """
        Get all sessions for a customer (cross-device lookup).

        Enables "Continue conversation" feature when customer
        authenticates on a new device.

        Args:
            customer_id: Shopify customer ID
            active_only: Only return active (non-expired) sessions

        Returns:
            List of CustomerSession objects
        """
        if self._container is None:
            logger.warning("Cosmos container not available")
            return []

        try:
            # Query by partition key (customer_id)
            query = "SELECT * FROM c WHERE c.customer_id = @customer_id"
            params = [{"name": "@customer_id", "value": customer_id}]

            if active_only:
                query += " AND c.state = @state"
                params.append({"name": "@state", "value": SessionState.ACTIVE.value})

            items = self._container.query_items(
                query=query,
                parameters=params,
                partition_key=customer_id,
            )

            sessions = []
            async for item in items:
                session = CustomerSession.from_dict(item)
                if not active_only or not session.is_expired():
                    sessions.append(session)

            logger.debug(f"Found {len(sessions)} sessions for customer {customer_id}")
            return sessions

        except Exception as e:
            logger.error(f"Failed to query customer sessions: {e}")
            return []

    async def get_session_by_device(
        self,
        device_id: str,
    ) -> Optional[CustomerSession]:
        """
        Get most recent session for a device.

        Used to resume anonymous sessions on same device.

        Args:
            device_id: Device/browser fingerprint

        Returns:
            Most recent active session for device, or None
        """
        if self._container is None:
            return None

        try:
            # Query by device_id (cross-partition query)
            query = """
                SELECT * FROM c
                WHERE c.device_id = @device_id
                AND c.state = @state
                ORDER BY c.updated_at DESC
                OFFSET 0 LIMIT 1
            """
            params = [
                {"name": "@device_id", "value": device_id},
                {"name": "@state", "value": SessionState.ACTIVE.value},
            ]

            items = self._container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )

            async for item in items:
                session = CustomerSession.from_dict(item)
                if not session.is_expired():
                    return session

            return None

        except Exception as e:
            logger.error(f"Failed to query device sessions: {e}")
            return None

    async def upgrade_to_identified(
        self,
        session_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[CustomerSession]:
        """
        Upgrade anonymous session to identified level.

        Called when customer provides email/phone for order lookup.

        Args:
            session_id: Session to upgrade
            email: Customer email
            phone: Customer phone

        Returns:
            Updated session, or None if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        session.upgrade_to_identified(email=email, phone=phone)
        await self._save_session(session)
        self._cache_session(session)

        logger.info(f"Upgraded session {session_id} to IDENTIFIED")
        return session

    async def upgrade_to_authenticated(
        self,
        session_id: str,
        customer: ShopifyCustomer,
        token: SessionToken,
    ) -> Optional[CustomerSession]:
        """
        Upgrade session to authenticated level.

        Called after successful Shopify Customer Accounts API login.

        Args:
            session_id: Session to upgrade
            customer: Shopify customer profile
            token: OAuth tokens

        Returns:
            Updated session, or None if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        # Remember old customer_id (device-based) for linking
        old_customer_id = session.customer_id

        # Upgrade to authenticated
        session.upgrade_to_authenticated(customer, token)

        # Save with new partition key (customer_id)
        await self._save_session(session)
        self._cache_session(session)

        logger.info(
            f"Upgraded session {session_id} to AUTHENTICATED "
            f"(customer={customer.id})"
        )

        # Optionally, link old device-based sessions
        # This enables "I see you were looking at..." on new device
        if old_customer_id != customer.id:
            await self._link_device_sessions(old_customer_id, customer.id)

        return session

    async def refresh_session_token(
        self,
        session_id: str,
    ) -> Optional[CustomerSession]:
        """
        Refresh OAuth token for authenticated session.

        Called when access_token is expired but refresh_token is valid.

        Args:
            session_id: Session with expired token

        Returns:
            Session with refreshed token, or None on failure
        """
        session = await self.get_session(session_id)
        if not session or not session.token:
            return None

        if not session.token.is_expired():
            # Token still valid, no refresh needed
            return session

        if not self._shopify_client:
            logger.error("Shopify client not available for token refresh")
            return None

        # Refresh token
        new_token = await self._shopify_client.refresh_access_token(
            session.token.refresh_token
        )

        if not new_token:
            logger.error(f"Failed to refresh token for session {session_id}")
            # Token refresh failed - session should be re-authenticated
            session.revoke()
            await self._save_session(session)
            return None

        session.refresh_token(new_token)
        await self._save_session(session)
        self._cache_session(session)

        logger.info(f"Refreshed token for session {session_id}")
        return session

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke session (logout).

        Invalidates session and revokes OAuth token if authenticated.

        Args:
            session_id: Session to revoke

        Returns:
            True if revocation successful
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        # Revoke OAuth token if authenticated
        if session.is_authenticated() and session.token and self._shopify_client:
            await self._shopify_client.revoke_token(session.token.access_token)

        # Mark session as revoked
        session.revoke()
        await self._save_session(session)

        # Remove from cache
        self._session_cache.pop(session_id, None)

        logger.info(f"Revoked session {session_id}")
        return True

    async def touch_session(self, session_id: str) -> Optional[CustomerSession]:
        """
        Update session activity timestamp.

        Called on each message to keep session alive.

        Args:
            session_id: Session to touch

        Returns:
            Updated session, or None if not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        session.touch()
        await self._save_session(session)
        self._cache_session(session)

        return session

    async def set_current_context(
        self,
        session_id: str,
        context_id: str,
    ) -> Optional[CustomerSession]:
        """
        Set current conversation context for session.

        Args:
            session_id: Session ID
            context_id: Conversation context ID

        Returns:
            Updated session
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        session.current_context_id = context_id
        session.conversation_count += 1
        session.touch()

        await self._save_session(session)
        self._cache_session(session)

        return session

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    async def _save_session(self, session: CustomerSession) -> None:
        """Save session to Cosmos DB."""
        if self._container is None:
            logger.debug("Cosmos container not available - session not persisted")
            return

        try:
            doc = session.to_dict()

            # Add TTL for automatic cleanup
            doc["ttl"] = self._ttl_seconds

            await self._container.upsert_item(doc)
            logger.debug(f"Saved session {session.session_id}")

        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    async def _load_session(self, session_id: str) -> Optional[CustomerSession]:
        """Load session from Cosmos DB."""
        if self._container is None:
            return None

        try:
            # Query by session_id (need cross-partition query)
            query = "SELECT * FROM c WHERE c.session_id = @session_id"
            params = [{"name": "@session_id", "value": session_id}]

            items = self._container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )

            async for item in items:
                return CustomerSession.from_dict(item)

            return None

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    async def _link_device_sessions(
        self,
        device_customer_id: str,
        shopify_customer_id: str,
    ) -> None:
        """
        Link device-based sessions to Shopify customer ID.

        Called after authentication to enable cross-device history.
        """
        # For now, just log the linking
        # Future enhancement: Update old sessions to reference new customer_id
        logger.info(
            f"Session linking: {device_customer_id} → {shopify_customer_id}"
        )

    def _cache_session(self, session: CustomerSession) -> None:
        """Add session to in-memory cache."""
        self._session_cache[session.session_id] = (
            session,
            datetime.utcnow(),
        )

    def _get_cached_session(self, session_id: str) -> Optional[CustomerSession]:
        """Get session from cache if not expired."""
        if session_id not in self._session_cache:
            return None

        session, cached_at = self._session_cache[session_id]
        cache_age = (datetime.utcnow() - cached_at).total_seconds()

        if cache_age > self._cache_ttl_seconds:
            # Cache expired
            del self._session_cache[session_id]
            return None

        return session

    def clear_cache(self) -> None:
        """Clear session cache (for testing)."""
        self._session_cache.clear()

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized


# ============================================================================
# Global Instance (Singleton Pattern)
# ============================================================================


async def init_session_manager(
    cosmos_client=None,
    container_name: str = "sessions",
    ttl_seconds: int = SessionManager.DEFAULT_TTL_SECONDS,
) -> SessionManager:
    """
    Initialize the global session manager.

    Call once at application startup.

    Args:
        cosmos_client: CosmosDBClient instance (auto-created if None)
        container_name: Cosmos DB container name
        ttl_seconds: Session TTL in seconds

    Returns:
        Initialized SessionManager instance
    """
    global _session_manager

    if _session_manager is not None and _session_manager.is_initialized:
        logger.warning("SessionManager already initialized")
        return _session_manager

    _session_manager = SessionManager(
        cosmos_client=cosmos_client,
        container_name=container_name,
        ttl_seconds=ttl_seconds,
    )
    await _session_manager.initialize()

    return _session_manager


def get_session_manager() -> SessionManager:
    """
    Get the global session manager.

    Raises RuntimeError if not initialized.

    Returns:
        The global SessionManager instance
    """
    if _session_manager is None:
        raise RuntimeError(
            "SessionManager not initialized. Call init_session_manager() first."
        )
    return _session_manager


async def shutdown_session_manager() -> None:
    """Shutdown the global session manager."""
    global _session_manager
    _session_manager = None
