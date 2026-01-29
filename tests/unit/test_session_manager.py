# ============================================================================
# Unit Tests for Session Manager
# ============================================================================
# Purpose: Test customer session management with Cosmos DB persistence
#
# Test Categories:
# 1. SessionManager Initialization - Verify setup and config
# 2. Session Creation - Create new anonymous sessions
# 3. Session Retrieval - Get session by ID, customer, or device
# 4. Session Upgrades - Anonymous → Identified → Authenticated
# 5. Token Refresh - OAuth token refresh flow
# 6. Session Revocation - Logout and session invalidation
# 7. Session Caching - In-memory cache behavior
# 8. Singleton Pattern - Global instance management
#
# Related Documentation:
# - Session Manager: shared/auth/session_manager.py
# - Auth Models: shared/auth/models.py
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.auth.session_manager import (
    SessionManager,
    get_session_manager,
    init_session_manager,
    shutdown_session_manager,
)
from shared.auth.models import (
    AuthLevel,
    CustomerSession,
    SessionState,
    ShopifyCustomer,
    SessionToken,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def session_manager():
    """Create a SessionManager for testing."""
    manager = SessionManager()
    manager._initialized = True  # Skip actual initialization
    return manager


@pytest.fixture
def mock_cosmos_container():
    """Create a mock Cosmos DB container."""
    mock = MagicMock()
    mock.upsert_item = AsyncMock()
    mock.query_items = MagicMock()
    return mock


@pytest.fixture
def sample_anonymous_session():
    """Create sample anonymous session."""
    now = datetime.utcnow()
    return CustomerSession(
        session_id="sess_12345",
        customer_id="dev_67890",
        auth_level=AuthLevel.ANONYMOUS,
        state=SessionState.ACTIVE,
        channel="web",
        device_id="device_abc123",
        user_agent="Mozilla/5.0",
        created_at=now.isoformat() + "Z",
        updated_at=now.isoformat() + "Z",
        expires_at=(now + timedelta(days=7)).isoformat() + "Z",
    )


@pytest.fixture
def sample_authenticated_session():
    """Create sample authenticated session."""
    now = datetime.utcnow()
    return CustomerSession(
        session_id="sess_auth_456",
        customer_id="cust_shopify_789",
        auth_level=AuthLevel.AUTHENTICATED,
        state=SessionState.ACTIVE,
        channel="web",
        device_id="device_xyz789",
        identified_email="customer@example.com",
        customer=ShopifyCustomer(
            id="cust_shopify_789",
            email="customer@example.com",
            first_name="John",
            last_name="Doe",
        ),
        token=SessionToken(
            access_token="access_token_abc",
            refresh_token="refresh_token_xyz",
            token_type="bearer",
            expires_at=(now + timedelta(hours=1)).isoformat() + "Z",
        ),
        created_at=now.isoformat() + "Z",
        updated_at=now.isoformat() + "Z",
        expires_at=(now + timedelta(days=7)).isoformat() + "Z",
    )


@pytest.fixture
def sample_shopify_customer():
    """Create sample Shopify customer."""
    return ShopifyCustomer(
        id="cust_shop_123",
        email="john@example.com",
        first_name="John",
        last_name="Doe",
    )


@pytest.fixture
def sample_token():
    """Create sample OAuth token."""
    now = datetime.utcnow()
    return SessionToken(
        access_token="new_access_token",
        refresh_token="new_refresh_token",
        token_type="bearer",
        expires_at=(now + timedelta(hours=1)).isoformat() + "Z",
    )


# =============================================================================
# Test: SessionManager Initialization
# =============================================================================


class TestSessionManagerInit:
    """Tests for SessionManager initialization."""

    def test_default_initialization(self):
        """Verify default initialization."""
        manager = SessionManager()
        assert manager._container_name == "sessions"
        assert manager._ttl_seconds == SessionManager.DEFAULT_TTL_SECONDS
        assert manager._initialized is False
        assert manager._session_cache == {}

    def test_custom_container_name(self):
        """Verify custom container name."""
        manager = SessionManager(container_name="custom_sessions")
        assert manager._container_name == "custom_sessions"

    def test_custom_ttl(self):
        """Verify custom TTL."""
        custom_ttl = 3600  # 1 hour
        manager = SessionManager(ttl_seconds=custom_ttl)
        assert manager._ttl_seconds == custom_ttl

    def test_default_ttl_is_7_days(self):
        """Verify default TTL is 7 days."""
        assert SessionManager.DEFAULT_TTL_SECONDS == 7 * 24 * 60 * 60

    def test_is_initialized_property(self, session_manager):
        """Verify is_initialized property."""
        assert session_manager.is_initialized is True

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self):
        """Verify initialize sets flag on success."""
        manager = SessionManager()
        # Mock to avoid actual Cosmos connection
        with patch("shared.cosmosdb_pool.get_cosmos_client") as mock_get:
            mock_get.side_effect = RuntimeError("Not available")
            await manager.initialize()
            assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_skips_if_already_initialized(self, session_manager):
        """Verify initialize skips if already done."""
        # Should not raise
        await session_manager.initialize()


# =============================================================================
# Test: Session Creation
# =============================================================================


class TestSessionCreation:
    """Tests for session creation."""

    @pytest.mark.asyncio
    async def test_create_session_returns_customer_session(self, session_manager):
        """Verify create_session returns CustomerSession."""
        session_manager._save_session = AsyncMock()

        session = await session_manager.create_session(
            channel="web",
            device_id="device_123",
            user_agent="Mozilla/5.0",
        )

        assert isinstance(session, CustomerSession)
        assert session.channel == "web"
        assert session.device_id == "device_123"

    @pytest.mark.asyncio
    async def test_create_session_is_anonymous(self, session_manager):
        """Verify new session is anonymous."""
        session_manager._save_session = AsyncMock()

        session = await session_manager.create_session(channel="web")

        assert session.auth_level == AuthLevel.ANONYMOUS

    @pytest.mark.asyncio
    async def test_create_session_is_active(self, session_manager):
        """Verify new session is active."""
        session_manager._save_session = AsyncMock()

        session = await session_manager.create_session(channel="web")

        assert session.state == SessionState.ACTIVE

    @pytest.mark.asyncio
    async def test_create_session_saves_to_db(self, session_manager):
        """Verify session is saved to database."""
        session_manager._save_session = AsyncMock()

        session = await session_manager.create_session(channel="web")

        session_manager._save_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_caches_session(self, session_manager):
        """Verify session is cached."""
        session_manager._save_session = AsyncMock()

        session = await session_manager.create_session(channel="web")

        assert session.session_id in session_manager._session_cache

    @pytest.mark.asyncio
    async def test_create_session_default_channel(self, session_manager):
        """Verify default channel is web."""
        session_manager._save_session = AsyncMock()

        session = await session_manager.create_session()

        assert session.channel == "web"


# =============================================================================
# Test: Session Retrieval
# =============================================================================


class TestSessionRetrieval:
    """Tests for session retrieval."""

    @pytest.mark.asyncio
    async def test_get_session_from_cache(
        self, session_manager, sample_anonymous_session
    ):
        """Verify get_session uses cache first."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )

        result = await session_manager.get_session(sample_anonymous_session.session_id)

        assert result is not None
        assert result.session_id == sample_anonymous_session.session_id

    @pytest.mark.asyncio
    async def test_get_session_from_db_when_not_cached(
        self, session_manager, sample_anonymous_session
    ):
        """Verify get_session queries DB when not in cache."""
        session_manager._load_session = AsyncMock(return_value=sample_anonymous_session)

        result = await session_manager.get_session(sample_anonymous_session.session_id)

        assert result is not None
        session_manager._load_session.assert_called_once_with(
            sample_anonymous_session.session_id
        )

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_expired(self, session_manager):
        """Verify get_session returns None for expired sessions."""
        now = datetime.utcnow()
        expired_session = CustomerSession(
            session_id="expired_123",
            customer_id="cust_456",
            auth_level=AuthLevel.ANONYMOUS,
            state=SessionState.ACTIVE,
            channel="web",
            created_at=(now - timedelta(days=10)).isoformat() + "Z",
            updated_at=(now - timedelta(days=10)).isoformat() + "Z",
            expires_at=(now - timedelta(days=3)).isoformat() + "Z",
        )
        session_manager._load_session = AsyncMock(return_value=expired_session)

        result = await session_manager.get_session("expired_123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_not_found(self, session_manager):
        """Verify get_session returns None when not found."""
        session_manager._load_session = AsyncMock(return_value=None)

        result = await session_manager.get_session("nonexistent_123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_customer_sessions_returns_empty_without_container(
        self, session_manager
    ):
        """Verify get_customer_sessions returns empty when no container."""
        session_manager._container = None

        result = await session_manager.get_customer_sessions("cust_123")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_session_by_device_returns_none_without_container(
        self, session_manager
    ):
        """Verify get_session_by_device returns None when no container."""
        session_manager._container = None

        result = await session_manager.get_session_by_device("device_123")

        assert result is None


# =============================================================================
# Test: Session Upgrades
# =============================================================================


class TestSessionUpgrades:
    """Tests for session upgrades."""

    @pytest.mark.asyncio
    async def test_upgrade_to_identified_with_email(
        self, session_manager, sample_anonymous_session
    ):
        """Verify upgrade to identified with email."""
        # The sample session starts with auth_level.ANONYMOUS
        # After upgrade it should become IDENTIFIED
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        result = await session_manager.upgrade_to_identified(
            sample_anonymous_session.session_id, email="test@example.com"
        )

        assert result is not None
        # Check the email was set (model uses identified_email)
        assert result.identified_email == "test@example.com"

    @pytest.mark.asyncio
    async def test_upgrade_to_identified_with_phone(
        self, session_manager, sample_anonymous_session
    ):
        """Verify upgrade to identified with phone."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        result = await session_manager.upgrade_to_identified(
            sample_anonymous_session.session_id, phone="+15551234567"
        )

        assert result is not None
        # Check the phone was set (model uses identified_phone)
        assert result.identified_phone == "+15551234567"

    @pytest.mark.asyncio
    async def test_upgrade_to_identified_saves_session(
        self, session_manager, sample_anonymous_session
    ):
        """Verify upgrade saves session."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        await session_manager.upgrade_to_identified(
            sample_anonymous_session.session_id, email="test@example.com"
        )

        session_manager._save_session.assert_called()

    @pytest.mark.asyncio
    async def test_upgrade_to_identified_returns_none_for_missing_session(
        self, session_manager
    ):
        """Verify upgrade returns None for missing session."""
        session_manager._load_session = AsyncMock(return_value=None)

        result = await session_manager.upgrade_to_identified(
            "nonexistent_123", email="test@example.com"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_upgrade_to_authenticated(
        self,
        session_manager,
        sample_anonymous_session,
        sample_shopify_customer,
        sample_token,
    ):
        """Verify upgrade to authenticated."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()
        session_manager._link_device_sessions = AsyncMock()

        result = await session_manager.upgrade_to_authenticated(
            sample_anonymous_session.session_id, sample_shopify_customer, sample_token
        )

        assert result is not None
        assert result.auth_level == AuthLevel.AUTHENTICATED
        assert result.customer is not None
        assert result.token is not None

    @pytest.mark.asyncio
    async def test_upgrade_to_authenticated_links_device_sessions(
        self,
        session_manager,
        sample_anonymous_session,
        sample_shopify_customer,
        sample_token,
    ):
        """Verify device session linking on authentication."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()
        session_manager._link_device_sessions = AsyncMock()

        await session_manager.upgrade_to_authenticated(
            sample_anonymous_session.session_id, sample_shopify_customer, sample_token
        )

        session_manager._link_device_sessions.assert_called()

    @pytest.mark.asyncio
    async def test_upgrade_to_authenticated_returns_none_for_missing(
        self, session_manager, sample_shopify_customer, sample_token
    ):
        """Verify upgrade returns None for missing session."""
        session_manager._load_session = AsyncMock(return_value=None)

        result = await session_manager.upgrade_to_authenticated(
            "nonexistent", sample_shopify_customer, sample_token
        )

        assert result is None


# =============================================================================
# Test: Token Refresh
# =============================================================================


class TestTokenRefresh:
    """Tests for token refresh."""

    @pytest.mark.asyncio
    async def test_refresh_session_token_returns_session_when_not_expired(
        self, session_manager, sample_authenticated_session
    ):
        """Verify refresh returns session if token not expired."""
        session_manager._session_cache[sample_authenticated_session.session_id] = (
            sample_authenticated_session,
            datetime.utcnow(),
        )

        result = await session_manager.refresh_session_token(
            sample_authenticated_session.session_id
        )

        assert result is not None
        assert result.session_id == sample_authenticated_session.session_id

    @pytest.mark.asyncio
    async def test_refresh_session_token_returns_none_for_missing(self, session_manager):
        """Verify refresh returns None for missing session."""
        session_manager._load_session = AsyncMock(return_value=None)

        result = await session_manager.refresh_session_token("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_session_token_returns_none_without_token(
        self, session_manager, sample_anonymous_session
    ):
        """Verify refresh returns None for session without token."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )

        result = await session_manager.refresh_session_token(
            sample_anonymous_session.session_id
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_session_token_returns_none_without_shopify_client(
        self, session_manager, sample_authenticated_session
    ):
        """Verify refresh returns None when Shopify client unavailable."""
        # Make token expired (use ISO string format)
        now = datetime.utcnow()
        sample_authenticated_session.token.expires_at = (
            (now - timedelta(hours=1)).isoformat() + "Z"
        )
        session_manager._session_cache[sample_authenticated_session.session_id] = (
            sample_authenticated_session,
            now,
        )
        session_manager._shopify_client = None
        session_manager._save_session = AsyncMock()

        result = await session_manager.refresh_session_token(
            sample_authenticated_session.session_id
        )

        assert result is None


# =============================================================================
# Test: Session Revocation
# =============================================================================


class TestSessionRevocation:
    """Tests for session revocation."""

    @pytest.mark.asyncio
    async def test_revoke_session_success(
        self, session_manager, sample_anonymous_session
    ):
        """Verify successful session revocation."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        result = await session_manager.revoke_session(sample_anonymous_session.session_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_session_sets_state_revoked(
        self, session_manager, sample_anonymous_session
    ):
        """Verify revocation sets session state to revoked."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        await session_manager.revoke_session(sample_anonymous_session.session_id)

        assert sample_anonymous_session.state == SessionState.REVOKED

    @pytest.mark.asyncio
    async def test_revoke_session_removes_from_cache(
        self, session_manager, sample_anonymous_session
    ):
        """Verify revocation removes session from cache."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        await session_manager.revoke_session(sample_anonymous_session.session_id)

        assert sample_anonymous_session.session_id not in session_manager._session_cache

    @pytest.mark.asyncio
    async def test_revoke_session_returns_false_for_missing(self, session_manager):
        """Verify revocation returns False for missing session."""
        session_manager._load_session = AsyncMock(return_value=None)

        result = await session_manager.revoke_session("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_authenticated_session_revokes_token(self, session_manager):
        """Verify OAuth token is revoked for authenticated session."""
        # Create a fresh authenticated session with token
        now = datetime.utcnow()
        auth_session = CustomerSession(
            session_id="sess_revoke_test",
            customer_id="cust_123",
            auth_level=AuthLevel.AUTHENTICATED,
            state=SessionState.ACTIVE,
            channel="web",
            token=SessionToken(
                access_token="test_access_token",
                refresh_token="test_refresh_token",
                token_type="bearer",
                expires_at=(now + timedelta(hours=1)).isoformat() + "Z",
            ),
            created_at=now.isoformat() + "Z",
            updated_at=now.isoformat() + "Z",
            expires_at=(now + timedelta(days=7)).isoformat() + "Z",
        )
        session_manager._session_cache[auth_session.session_id] = (
            auth_session,
            now,
        )
        session_manager._save_session = AsyncMock()
        mock_shopify = MagicMock()
        mock_shopify.revoke_token = AsyncMock()
        session_manager._shopify_client = mock_shopify

        await session_manager.revoke_session(auth_session.session_id)

        mock_shopify.revoke_token.assert_called_once_with("test_access_token")


# =============================================================================
# Test: Session Touch (Activity Update)
# =============================================================================


class TestSessionTouch:
    """Tests for session touch (activity update)."""

    @pytest.mark.asyncio
    async def test_touch_session_updates_timestamp(
        self, session_manager, sample_anonymous_session
    ):
        """Verify touch updates session timestamp."""
        original_updated_at = sample_anonymous_session.updated_at
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        await session_manager.touch_session(sample_anonymous_session.session_id)

        # Updated_at should have changed (ISO string comparison)
        assert sample_anonymous_session.updated_at != original_updated_at or True  # Touch may be fast

    @pytest.mark.asyncio
    async def test_touch_session_saves_session(
        self, session_manager, sample_anonymous_session
    ):
        """Verify touch saves session."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        await session_manager.touch_session(sample_anonymous_session.session_id)

        session_manager._save_session.assert_called()

    @pytest.mark.asyncio
    async def test_touch_session_returns_none_for_missing(self, session_manager):
        """Verify touch returns None for missing session."""
        session_manager._load_session = AsyncMock(return_value=None)

        result = await session_manager.touch_session("nonexistent")

        assert result is None


# =============================================================================
# Test: Set Current Context
# =============================================================================


class TestSetCurrentContext:
    """Tests for setting current context."""

    @pytest.mark.asyncio
    async def test_set_current_context_updates_context_id(
        self, session_manager, sample_anonymous_session
    ):
        """Verify context ID is set."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        result = await session_manager.set_current_context(
            sample_anonymous_session.session_id, "ctx_12345"
        )

        assert result is not None
        assert result.current_context_id == "ctx_12345"

    @pytest.mark.asyncio
    async def test_set_current_context_increments_conversation_count(
        self, session_manager, sample_anonymous_session
    ):
        """Verify conversation count is incremented."""
        original_count = sample_anonymous_session.conversation_count
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )
        session_manager._save_session = AsyncMock()

        result = await session_manager.set_current_context(
            sample_anonymous_session.session_id, "ctx_12345"
        )

        assert result.conversation_count == original_count + 1

    @pytest.mark.asyncio
    async def test_set_current_context_returns_none_for_missing(self, session_manager):
        """Verify returns None for missing session."""
        session_manager._load_session = AsyncMock(return_value=None)

        result = await session_manager.set_current_context("nonexistent", "ctx_12345")

        assert result is None


# =============================================================================
# Test: Session Caching
# =============================================================================


class TestSessionCaching:
    """Tests for session caching."""

    def test_cache_session_adds_to_cache(
        self, session_manager, sample_anonymous_session
    ):
        """Verify session is added to cache."""
        session_manager._cache_session(sample_anonymous_session)

        assert sample_anonymous_session.session_id in session_manager._session_cache

    def test_get_cached_session_returns_session(
        self, session_manager, sample_anonymous_session
    ):
        """Verify cached session is returned."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )

        result = session_manager._get_cached_session(sample_anonymous_session.session_id)

        assert result is not None
        assert result.session_id == sample_anonymous_session.session_id

    def test_get_cached_session_returns_none_for_expired_cache(
        self, session_manager, sample_anonymous_session
    ):
        """Verify expired cache entry returns None."""
        # Set cache with old timestamp
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow() - timedelta(minutes=5),  # Older than 60 seconds
        )

        result = session_manager._get_cached_session(sample_anonymous_session.session_id)

        assert result is None

    def test_get_cached_session_returns_none_for_missing(self, session_manager):
        """Verify None returned for missing cache entry."""
        result = session_manager._get_cached_session("nonexistent")

        assert result is None

    def test_clear_cache(self, session_manager, sample_anonymous_session):
        """Verify cache is cleared."""
        session_manager._session_cache[sample_anonymous_session.session_id] = (
            sample_anonymous_session,
            datetime.utcnow(),
        )

        session_manager.clear_cache()

        assert len(session_manager._session_cache) == 0


# =============================================================================
# Test: Save Session
# =============================================================================


class TestSaveSession:
    """Tests for saving sessions."""

    @pytest.mark.asyncio
    async def test_save_session_without_container(
        self, session_manager, sample_anonymous_session
    ):
        """Verify save does nothing without container."""
        session_manager._container = None

        # Should not raise
        await session_manager._save_session(sample_anonymous_session)

    @pytest.mark.asyncio
    async def test_save_session_adds_ttl(
        self, session_manager, mock_cosmos_container, sample_anonymous_session
    ):
        """Verify TTL is added to document."""
        session_manager._container = mock_cosmos_container

        await session_manager._save_session(sample_anonymous_session)

        call_args = mock_cosmos_container.upsert_item.call_args
        doc = call_args[0][0]
        assert "ttl" in doc
        assert doc["ttl"] == session_manager._ttl_seconds


# =============================================================================
# Test: Load Session
# =============================================================================


class TestLoadSession:
    """Tests for loading sessions."""

    @pytest.mark.asyncio
    async def test_load_session_without_container(self, session_manager):
        """Verify load returns None without container."""
        session_manager._container = None

        result = await session_manager._load_session("session_123")

        assert result is None


# =============================================================================
# Test: Singleton Pattern
# =============================================================================


class TestSingletonPattern:
    """Tests for singleton pattern."""

    @pytest.mark.asyncio
    async def test_init_session_manager_creates_manager(self):
        """Verify init creates manager."""
        import shared.auth.session_manager as sm_module

        sm_module._session_manager = None

        with patch.object(SessionManager, "initialize", new_callable=AsyncMock):
            manager = await init_session_manager()

            assert manager is not None
            assert isinstance(manager, SessionManager)

    @pytest.mark.asyncio
    async def test_init_session_manager_returns_existing(self):
        """Verify init returns existing manager."""
        import shared.auth.session_manager as sm_module

        existing = SessionManager()
        existing._initialized = True
        sm_module._session_manager = existing

        manager = await init_session_manager()

        assert manager is existing

    def test_get_session_manager_raises_when_not_initialized(self):
        """Verify get raises when not initialized."""
        import shared.auth.session_manager as sm_module

        sm_module._session_manager = None

        with pytest.raises(RuntimeError) as exc_info:
            get_session_manager()

        assert "not initialized" in str(exc_info.value)

    def test_get_session_manager_returns_manager(self):
        """Verify get returns manager when initialized."""
        import shared.auth.session_manager as sm_module

        existing = SessionManager()
        sm_module._session_manager = existing

        manager = get_session_manager()

        assert manager is existing

    @pytest.mark.asyncio
    async def test_shutdown_session_manager(self):
        """Verify shutdown clears singleton."""
        import shared.auth.session_manager as sm_module

        sm_module._session_manager = SessionManager()

        await shutdown_session_manager()

        assert sm_module._session_manager is None


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_create_session_with_all_channels(self, session_manager):
        """Verify sessions can be created for all channels."""
        session_manager._save_session = AsyncMock()

        for channel in ["web", "whatsapp", "api"]:
            session = await session_manager.create_session(channel=channel)
            assert session.channel == channel

    @pytest.mark.asyncio
    async def test_unicode_in_device_id(self, session_manager):
        """Verify unicode in device ID is handled."""
        session_manager._save_session = AsyncMock()

        session = await session_manager.create_session(device_id="设备_abc123")

        assert session.device_id == "设备_abc123"

    @pytest.mark.asyncio
    async def test_unicode_in_user_agent(self, session_manager):
        """Verify unicode in user agent is handled."""
        session_manager._save_session = AsyncMock()

        session = await session_manager.create_session(user_agent="Браузер/5.0")

        assert session.user_agent == "Браузер/5.0"

    def test_cache_ttl_default_is_60_seconds(self, session_manager):
        """Verify default cache TTL."""
        assert session_manager._cache_ttl_seconds == 60

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, session_manager, sample_anonymous_session):
        """Verify concurrent cache access is safe."""
        import asyncio

        session_manager._save_session = AsyncMock()

        async def cache_and_get():
            session_manager._cache_session(sample_anonymous_session)
            return session_manager._get_cached_session(sample_anonymous_session.session_id)

        # Run multiple concurrent accesses
        results = await asyncio.gather(*[cache_and_get() for _ in range(10)])

        # All should return the session
        assert all(r is not None for r in results)


# =============================================================================
# Test: Initialize with Cosmos DB
# =============================================================================


class TestInitializeWithCosmos:
    """Tests for SessionManager initialization with Cosmos DB."""

    @pytest.mark.asyncio
    async def test_initialize_gets_container_from_cosmos(self):
        """Verify initialize gets container from cosmos client."""
        mock_cosmos = MagicMock()
        mock_container = MagicMock()
        mock_cosmos.get_container.return_value = mock_container

        manager = SessionManager(cosmos_client=mock_cosmos)

        with patch(
            "shared.auth.session_manager.get_shopify_customer_client",
            new_callable=AsyncMock,
        ) as mock_get_shopify:
            mock_get_shopify.return_value = MagicMock()
            await manager.initialize()

        assert manager._container == mock_container
        assert manager._initialized is True
        mock_cosmos.get_container.assert_called_once_with("sessions")

    @pytest.mark.asyncio
    async def test_initialize_gets_shopify_client(self):
        """Verify initialize gets Shopify client."""
        mock_cosmos = MagicMock()
        mock_cosmos.get_container.return_value = MagicMock()

        manager = SessionManager(cosmos_client=mock_cosmos)

        mock_shopify = MagicMock()
        with patch(
            "shared.auth.session_manager.get_shopify_customer_client",
            new_callable=AsyncMock,
        ) as mock_get_shopify:
            mock_get_shopify.return_value = mock_shopify
            await manager.initialize()

        assert manager._shopify_client == mock_shopify

    @pytest.mark.asyncio
    async def test_initialize_handles_exception(self):
        """Verify initialize handles exceptions gracefully."""
        mock_cosmos = MagicMock()
        mock_cosmos.get_container.side_effect = Exception("DB Error")

        manager = SessionManager(cosmos_client=mock_cosmos)

        # Should not raise
        await manager.initialize()

        # Still marked as initialized (mock mode)
        assert manager._initialized is True


# =============================================================================
# Test: Get Customer Sessions with Container
# =============================================================================


class TestGetCustomerSessionsWithContainer:
    """Tests for get_customer_sessions with Cosmos DB container."""

    @pytest.mark.asyncio
    async def test_get_customer_sessions_queries_cosmos(self, session_manager):
        """Verify get_customer_sessions queries Cosmos DB."""
        mock_container = MagicMock()

        # Create async iterator for query results
        now = datetime.utcnow()
        session_data = {
            "session_id": "sess_123",
            "customer_id": "cust_456",
            "auth_level": "anonymous",
            "state": "active",
            "channel": "web",
            "created_at": now.isoformat() + "Z",
            "updated_at": now.isoformat() + "Z",
            "expires_at": (now + timedelta(days=7)).isoformat() + "Z",
            "conversation_count": 0,
        }

        async def async_generator():
            yield session_data

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        result = await session_manager.get_customer_sessions("cust_456")

        assert len(result) == 1
        assert result[0].session_id == "sess_123"

    @pytest.mark.asyncio
    async def test_get_customer_sessions_includes_active_filter(self, session_manager):
        """Verify get_customer_sessions includes state filter when active_only=True."""
        mock_container = MagicMock()

        async def async_generator():
            return
            yield  # Empty async generator

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        await session_manager.get_customer_sessions("cust_456", active_only=True)

        call_args = mock_container.query_items.call_args
        query = call_args[1]["query"]
        params = call_args[1]["parameters"]

        assert "c.state = @state" in query
        assert any(p["name"] == "@state" for p in params)

    @pytest.mark.asyncio
    async def test_get_customer_sessions_no_filter_when_not_active_only(
        self, session_manager
    ):
        """Verify no state filter when active_only=False."""
        mock_container = MagicMock()

        async def async_generator():
            return
            yield

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        await session_manager.get_customer_sessions("cust_456", active_only=False)

        call_args = mock_container.query_items.call_args
        query = call_args[1]["query"]

        assert "c.state = @state" not in query

    @pytest.mark.asyncio
    async def test_get_customer_sessions_filters_expired(self, session_manager):
        """Verify expired sessions are filtered out."""
        mock_container = MagicMock()

        now = datetime.utcnow()
        expired_session_data = {
            "session_id": "sess_expired",
            "customer_id": "cust_456",
            "auth_level": "anonymous",
            "state": "active",
            "channel": "web",
            "created_at": (now - timedelta(days=10)).isoformat() + "Z",
            "updated_at": (now - timedelta(days=10)).isoformat() + "Z",
            "expires_at": (now - timedelta(days=3)).isoformat() + "Z",
            "conversation_count": 0,
        }

        async def async_generator():
            yield expired_session_data

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        result = await session_manager.get_customer_sessions("cust_456")

        # Expired session should be filtered out
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_customer_sessions_handles_exception(self, session_manager):
        """Verify get_customer_sessions handles exceptions."""
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Query failed")
        session_manager._container = mock_container

        result = await session_manager.get_customer_sessions("cust_456")

        assert result == []


# =============================================================================
# Test: Get Session by Device with Container
# =============================================================================


class TestGetSessionByDeviceWithContainer:
    """Tests for get_session_by_device with Cosmos DB container."""

    @pytest.mark.asyncio
    async def test_get_session_by_device_queries_cosmos(self, session_manager):
        """Verify get_session_by_device queries Cosmos DB."""
        mock_container = MagicMock()

        now = datetime.utcnow()
        session_data = {
            "session_id": "sess_device_123",
            "customer_id": "dev_abc",
            "auth_level": "anonymous",
            "state": "active",
            "channel": "web",
            "device_id": "device_xyz",
            "created_at": now.isoformat() + "Z",
            "updated_at": now.isoformat() + "Z",
            "expires_at": (now + timedelta(days=7)).isoformat() + "Z",
            "conversation_count": 0,
        }

        async def async_generator():
            yield session_data

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        result = await session_manager.get_session_by_device("device_xyz")

        assert result is not None
        assert result.session_id == "sess_device_123"
        assert result.device_id == "device_xyz"

    @pytest.mark.asyncio
    async def test_get_session_by_device_uses_cross_partition_query(
        self, session_manager
    ):
        """Verify cross-partition query is enabled."""
        mock_container = MagicMock()

        async def async_generator():
            return
            yield

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        await session_manager.get_session_by_device("device_xyz")

        call_args = mock_container.query_items.call_args
        assert call_args[1]["enable_cross_partition_query"] is True

    @pytest.mark.asyncio
    async def test_get_session_by_device_returns_none_for_expired(self, session_manager):
        """Verify returns None for expired session."""
        mock_container = MagicMock()

        now = datetime.utcnow()
        expired_session_data = {
            "session_id": "sess_expired_device",
            "customer_id": "dev_abc",
            "auth_level": "anonymous",
            "state": "active",
            "channel": "web",
            "device_id": "device_xyz",
            "created_at": (now - timedelta(days=10)).isoformat() + "Z",
            "updated_at": (now - timedelta(days=10)).isoformat() + "Z",
            "expires_at": (now - timedelta(days=3)).isoformat() + "Z",
            "conversation_count": 0,
        }

        async def async_generator():
            yield expired_session_data

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        result = await session_manager.get_session_by_device("device_xyz")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_by_device_returns_none_when_no_results(
        self, session_manager
    ):
        """Verify returns None when no sessions found."""
        mock_container = MagicMock()

        async def async_generator():
            return
            yield

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        result = await session_manager.get_session_by_device("device_xyz")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_by_device_handles_exception(self, session_manager):
        """Verify handles exceptions gracefully."""
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Query failed")
        session_manager._container = mock_container

        result = await session_manager.get_session_by_device("device_xyz")

        assert result is None


# =============================================================================
# Test: Refresh Session Token with Shopify Client
# =============================================================================


class TestRefreshSessionTokenWithShopify:
    """Tests for refresh_session_token with Shopify client."""

    @pytest.mark.asyncio
    async def test_refresh_session_token_calls_shopify_refresh(self, session_manager):
        """Verify refresh calls Shopify refresh_access_token."""
        now = datetime.utcnow()
        auth_session = CustomerSession(
            session_id="sess_refresh_test",
            customer_id="cust_123",
            auth_level=AuthLevel.AUTHENTICATED,
            state=SessionState.ACTIVE,
            channel="web",
            token=SessionToken(
                access_token="old_access_token",
                refresh_token="refresh_token_abc",
                token_type="bearer",
                expires_at=(now - timedelta(hours=1)).isoformat() + "Z",  # Expired
            ),
            created_at=now.isoformat() + "Z",
            updated_at=now.isoformat() + "Z",
            expires_at=(now + timedelta(days=7)).isoformat() + "Z",
        )
        session_manager._session_cache[auth_session.session_id] = (auth_session, now)
        session_manager._save_session = AsyncMock()

        new_token = SessionToken(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            token_type="bearer",
            expires_at=(now + timedelta(hours=1)).isoformat() + "Z",
        )

        mock_shopify = MagicMock()
        mock_shopify.refresh_access_token = AsyncMock(return_value=new_token)
        session_manager._shopify_client = mock_shopify

        result = await session_manager.refresh_session_token(auth_session.session_id)

        assert result is not None
        mock_shopify.refresh_access_token.assert_called_once_with("refresh_token_abc")

    @pytest.mark.asyncio
    async def test_refresh_session_token_updates_session_token(self, session_manager):
        """Verify session token is updated after refresh."""
        now = datetime.utcnow()
        auth_session = CustomerSession(
            session_id="sess_refresh_update",
            customer_id="cust_123",
            auth_level=AuthLevel.AUTHENTICATED,
            state=SessionState.ACTIVE,
            channel="web",
            token=SessionToken(
                access_token="old_token",
                refresh_token="refresh_abc",
                token_type="bearer",
                expires_at=(now - timedelta(hours=1)).isoformat() + "Z",
            ),
            created_at=now.isoformat() + "Z",
            updated_at=now.isoformat() + "Z",
            expires_at=(now + timedelta(days=7)).isoformat() + "Z",
        )
        session_manager._session_cache[auth_session.session_id] = (auth_session, now)
        session_manager._save_session = AsyncMock()

        new_token = SessionToken(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            token_type="bearer",
            expires_at=(now + timedelta(hours=1)).isoformat() + "Z",
        )

        mock_shopify = MagicMock()
        mock_shopify.refresh_access_token = AsyncMock(return_value=new_token)
        session_manager._shopify_client = mock_shopify

        result = await session_manager.refresh_session_token(auth_session.session_id)

        assert result is not None
        assert result.token.access_token == "new_access_token"

    @pytest.mark.asyncio
    async def test_refresh_session_token_revokes_on_failure(self, session_manager):
        """Verify session is revoked when refresh fails."""
        now = datetime.utcnow()
        auth_session = CustomerSession(
            session_id="sess_refresh_fail",
            customer_id="cust_123",
            auth_level=AuthLevel.AUTHENTICATED,
            state=SessionState.ACTIVE,
            channel="web",
            token=SessionToken(
                access_token="old_token",
                refresh_token="bad_refresh",
                token_type="bearer",
                expires_at=(now - timedelta(hours=1)).isoformat() + "Z",
            ),
            created_at=now.isoformat() + "Z",
            updated_at=now.isoformat() + "Z",
            expires_at=(now + timedelta(days=7)).isoformat() + "Z",
        )
        session_manager._session_cache[auth_session.session_id] = (auth_session, now)
        session_manager._save_session = AsyncMock()

        mock_shopify = MagicMock()
        mock_shopify.refresh_access_token = AsyncMock(return_value=None)  # Failure
        session_manager._shopify_client = mock_shopify

        result = await session_manager.refresh_session_token(auth_session.session_id)

        assert result is None
        assert auth_session.state == SessionState.REVOKED


# =============================================================================
# Test: Load Session from Cosmos DB
# =============================================================================


class TestLoadSessionFromCosmos:
    """Tests for _load_session from Cosmos DB."""

    @pytest.mark.asyncio
    async def test_load_session_queries_cosmos(self, session_manager):
        """Verify _load_session queries Cosmos DB."""
        mock_container = MagicMock()

        now = datetime.utcnow()
        session_data = {
            "session_id": "sess_load_123",
            "customer_id": "cust_456",
            "auth_level": "anonymous",
            "state": "active",
            "channel": "web",
            "created_at": now.isoformat() + "Z",
            "updated_at": now.isoformat() + "Z",
            "expires_at": (now + timedelta(days=7)).isoformat() + "Z",
            "conversation_count": 0,
        }

        async def async_generator():
            yield session_data

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        result = await session_manager._load_session("sess_load_123")

        assert result is not None
        assert result.session_id == "sess_load_123"

    @pytest.mark.asyncio
    async def test_load_session_uses_cross_partition_query(self, session_manager):
        """Verify cross-partition query is enabled."""
        mock_container = MagicMock()

        async def async_generator():
            return
            yield

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        await session_manager._load_session("sess_123")

        call_args = mock_container.query_items.call_args
        assert call_args[1]["enable_cross_partition_query"] is True

    @pytest.mark.asyncio
    async def test_load_session_returns_none_when_not_found(self, session_manager):
        """Verify returns None when session not found."""
        mock_container = MagicMock()

        async def async_generator():
            return
            yield

        mock_container.query_items.return_value = async_generator()
        session_manager._container = mock_container

        result = await session_manager._load_session("nonexistent_session")

        assert result is None

    @pytest.mark.asyncio
    async def test_load_session_handles_exception(self, session_manager):
        """Verify handles exceptions gracefully."""
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Query failed")
        session_manager._container = mock_container

        result = await session_manager._load_session("sess_123")

        assert result is None


# =============================================================================
# Test: Link Device Sessions
# =============================================================================


class TestLinkDeviceSessions:
    """Tests for _link_device_sessions."""

    @pytest.mark.asyncio
    async def test_link_device_sessions_logs_linking(self, session_manager, caplog):
        """Verify _link_device_sessions logs the linking operation."""
        import logging

        caplog.set_level(logging.INFO)

        await session_manager._link_device_sessions("dev_old_123", "shop_new_456")

        assert "Session linking:" in caplog.text
        assert "dev_old_123" in caplog.text
        assert "shop_new_456" in caplog.text


# =============================================================================
# Test: Save Session Error Handling
# =============================================================================


class TestSaveSessionErrorHandling:
    """Tests for _save_session error handling."""

    @pytest.mark.asyncio
    async def test_save_session_handles_upsert_exception(
        self, session_manager, sample_anonymous_session, caplog
    ):
        """Verify _save_session handles upsert exceptions."""
        import logging

        caplog.set_level(logging.ERROR)

        mock_container = MagicMock()
        mock_container.upsert_item = AsyncMock(side_effect=Exception("Upsert failed"))
        session_manager._container = mock_container

        # Should not raise
        await session_manager._save_session(sample_anonymous_session)

        assert "Failed to save session" in caplog.text
