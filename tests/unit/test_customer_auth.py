# ============================================================================
# Unit Tests for Customer Authentication Module - Phase 6
# ============================================================================
# Purpose: Test customer session models, tiered access, and session management
#
# Test Coverage:
# - AuthLevel enum and transitions
# - CustomerSession model creation and serialization
# - SessionToken expiry detection
# - Session upgrade flows (Anonymous → Identified → Authenticated)
# - Permission checks based on auth level
#
# Related Documentation:
# - Session Models: shared/auth/models.py
# - Session Manager: shared/auth/session_manager.py
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q5)
# ============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.auth.models import (
    AuthLevel,
    SessionState,
    SessionToken,
    ShopifyCustomer,
    CustomerSession,
    create_anonymous_session,
    create_identified_session,
)


# ============================================================================
# AuthLevel Tests
# ============================================================================


class TestAuthLevel:
    """Tests for AuthLevel enum."""

    def test_auth_levels_exist(self):
        """Verify all expected auth levels are defined."""
        assert AuthLevel.ANONYMOUS.value == "anonymous"
        assert AuthLevel.IDENTIFIED.value == "identified"
        assert AuthLevel.AUTHENTICATED.value == "authenticated"

    def test_auth_level_comparison(self):
        """Auth levels should be comparable as strings."""
        assert AuthLevel.ANONYMOUS != AuthLevel.AUTHENTICATED
        assert AuthLevel("anonymous") == AuthLevel.ANONYMOUS


# ============================================================================
# SessionToken Tests
# ============================================================================


class TestSessionToken:
    """Tests for SessionToken model."""

    def test_create_token(self):
        """Create a basic session token."""
        token = SessionToken(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at="2030-01-01T00:00:00Z",
            scope="openid customer-account-api:full",
        )

        assert token.access_token == "test_access_token"
        assert token.refresh_token == "test_refresh_token"
        assert token.token_type == "Bearer"
        assert not token.is_expired()

    def test_token_expired(self):
        """Token with past expiry should be detected as expired."""
        token = SessionToken(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at="2020-01-01T00:00:00Z",  # Past date
        )

        assert token.is_expired()

    def test_token_expires_soon(self):
        """Token expiring within 5 minutes should be treated as expired."""
        # Create token expiring in 3 minutes
        expires_soon = (datetime.utcnow() + timedelta(minutes=3)).isoformat() + "Z"
        token = SessionToken(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=expires_soon,
        )

        # Should be considered expired (within 5 minute safety margin)
        assert token.is_expired()

    def test_token_serialization(self):
        """Token should serialize to dict and back."""
        token = SessionToken(
            access_token="test_access",
            refresh_token="test_refresh",
            expires_at="2030-01-01T00:00:00Z",
            scope="openid",
        )

        data = token.to_dict()
        assert data["access_token"] == "test_access"
        assert data["refresh_token"] == "test_refresh"

        restored = SessionToken.from_dict(data)
        assert restored.access_token == token.access_token
        assert restored.refresh_token == token.refresh_token


# ============================================================================
# ShopifyCustomer Tests
# ============================================================================


class TestShopifyCustomer:
    """Tests for ShopifyCustomer model."""

    def test_create_customer(self):
        """Create a basic customer profile."""
        customer = ShopifyCustomer(
            id="gid://shopify/Customer/12345",
            email="test@example.com",
            first_name="Test",
            last_name="Customer",
            orders_count=5,
            total_spent="249.95",
        )

        assert customer.id == "gid://shopify/Customer/12345"
        assert customer.email == "test@example.com"
        assert customer.full_name == "Test Customer"
        assert customer.orders_count == 5

    def test_customer_full_name_empty(self):
        """Full name should handle missing names."""
        customer = ShopifyCustomer(
            id="gid://shopify/Customer/12345",
            email="test@example.com",
        )

        assert customer.full_name == "Customer"

    def test_customer_vip_tag(self):
        """VIP customers should be identified by tag."""
        regular = ShopifyCustomer(
            id="gid://shopify/Customer/12345",
            email="regular@example.com",
            tags=[],
        )
        vip = ShopifyCustomer(
            id="gid://shopify/Customer/67890",
            email="vip@example.com",
            tags=["VIP", "Wholesale"],
        )

        assert not regular.is_vip
        assert vip.is_vip

    def test_customer_serialization(self):
        """Customer should serialize to dict and back."""
        customer = ShopifyCustomer(
            id="gid://shopify/Customer/12345",
            email="test@example.com",
            first_name="Test",
            last_name="Customer",
            tags=["VIP"],
        )

        data = customer.to_dict()
        restored = ShopifyCustomer.from_dict(data)

        assert restored.id == customer.id
        assert restored.email == customer.email
        assert restored.is_vip


# ============================================================================
# CustomerSession Tests
# ============================================================================


class TestCustomerSession:
    """Tests for CustomerSession model."""

    def test_create_anonymous_session(self):
        """Create an anonymous session."""
        session = create_anonymous_session(
            device_id="device-abc123",
            channel="web",
        )

        assert session.auth_level == AuthLevel.ANONYMOUS
        assert session.state == SessionState.ACTIVE
        assert session.channel == "web"
        assert session.device_id == "device-abc123"
        assert session.customer_id == "device-abc123"  # Uses device_id
        assert session.session_id.startswith("sess-")

    def test_create_identified_session(self):
        """Create an identified session with email."""
        session = create_identified_session(
            email="test@example.com",
            channel="web",
        )

        assert session.auth_level == AuthLevel.IDENTIFIED
        assert session.identified_email == "test@example.com"

    def test_session_upgrade_to_identified(self):
        """Anonymous session can upgrade to identified."""
        session = create_anonymous_session()
        assert session.auth_level == AuthLevel.ANONYMOUS

        session.upgrade_to_identified(email="test@example.com")

        assert session.auth_level == AuthLevel.IDENTIFIED
        assert session.identified_email == "test@example.com"

    def test_session_upgrade_to_authenticated(self):
        """Session can upgrade to authenticated with customer profile."""
        session = create_anonymous_session()

        customer = ShopifyCustomer(
            id="gid://shopify/Customer/12345",
            email="test@example.com",
        )
        token = SessionToken(
            access_token="test_access",
            refresh_token="test_refresh",
            expires_at="2030-01-01T00:00:00Z",
        )

        session.upgrade_to_authenticated(customer, token)

        assert session.auth_level == AuthLevel.AUTHENTICATED
        assert session.customer_id == customer.id  # Changed to Shopify ID
        assert session.customer == customer
        assert session.token == token

    def test_session_expiry(self):
        """Session with past expiry should be detected as expired."""
        session = create_anonymous_session()
        session.expires_at = "2020-01-01T00:00:00Z"  # Past date

        assert session.is_expired()

    def test_session_revocation(self):
        """Revoking session should change state and clear token."""
        session = create_anonymous_session()
        token = SessionToken(
            access_token="test",
            refresh_token="test",
            expires_at="2030-01-01T00:00:00Z",
        )
        session.token = token

        session.revoke()

        assert session.state == SessionState.REVOKED
        assert session.token is None
        assert session.is_expired()

    def test_permission_checks_anonymous(self):
        """Anonymous sessions have limited permissions."""
        session = create_anonymous_session()

        assert not session.is_authenticated()
        assert not session.can_access_orders()
        assert not session.can_modify_orders()
        assert not session.can_access_payments()

    def test_permission_checks_identified(self):
        """Identified sessions can access orders but not modify."""
        session = create_identified_session(email="test@example.com")

        assert not session.is_authenticated()
        assert session.can_access_orders()  # Can lookup by email
        assert not session.can_modify_orders()
        assert not session.can_access_payments()

    def test_permission_checks_authenticated(self):
        """Authenticated sessions have full permissions."""
        session = create_anonymous_session()
        customer = ShopifyCustomer(
            id="gid://shopify/Customer/12345",
            email="test@example.com",
        )
        token = SessionToken(
            access_token="test",
            refresh_token="test",
            expires_at="2030-01-01T00:00:00Z",
        )
        session.upgrade_to_authenticated(customer, token)

        assert session.is_authenticated()
        assert session.can_access_orders()
        assert session.can_modify_orders()
        assert session.can_access_payments()

    def test_session_serialization(self):
        """Session should serialize to dict for Cosmos DB."""
        session = create_anonymous_session(
            device_id="device-123",
            channel="web",
        )

        data = session.to_dict()

        assert data["id"] == session.session_id  # Cosmos DB document ID
        assert data["session_id"] == session.session_id
        assert data["customer_id"] == session.customer_id
        assert data["auth_level"] == "anonymous"
        assert data["state"] == "active"
        assert data["channel"] == "web"

    def test_session_deserialization(self):
        """Session should deserialize from Cosmos DB document."""
        data = {
            "session_id": "sess-abc123",
            "customer_id": "device-xyz",
            "auth_level": "identified",
            "state": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "expires_at": "2024-01-08T00:00:00Z",
            "channel": "web",
            "device_id": "device-xyz",
            "user_agent": "Mozilla/5.0",
            "current_context_id": None,
            "conversation_count": 0,
            "identified_email": "test@example.com",
            "identified_phone": None,
            "_rid": "cosmos_rid",  # Cosmos metadata
            "_self": "cosmos_self",
            "_etag": "cosmos_etag",
        }

        session = CustomerSession.from_dict(data)

        assert session.session_id == "sess-abc123"
        assert session.auth_level == AuthLevel.IDENTIFIED
        assert session.identified_email == "test@example.com"

    def test_session_with_customer_serialization(self):
        """Session with nested customer should serialize correctly."""
        session = create_anonymous_session()
        customer = ShopifyCustomer(
            id="gid://shopify/Customer/12345",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )
        token = SessionToken(
            access_token="test_access",
            refresh_token="test_refresh",
            expires_at="2030-01-01T00:00:00Z",
        )
        session.upgrade_to_authenticated(customer, token)

        data = session.to_dict()

        assert "customer" in data
        assert data["customer"]["email"] == "test@example.com"
        assert "token" in data
        assert data["token"]["access_token"] == "test_access"

    def test_session_touch_updates_timestamp(self):
        """Touch should update the updated_at timestamp."""
        session = create_anonymous_session()
        original_updated = session.updated_at

        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)

        session.touch()

        assert session.updated_at != original_updated


# ============================================================================
# Integration Tests (Mock Cosmos DB)
# ============================================================================


class TestSessionManagerMock:
    """Tests for SessionManager with mocked Cosmos DB."""

    @pytest.fixture
    def mock_cosmos(self):
        """Create mock Cosmos DB client."""
        cosmos = MagicMock()
        container = MagicMock()
        cosmos.get_container.return_value = container
        return cosmos, container

    @pytest.mark.asyncio
    async def test_create_session_stores_in_cosmos(self, mock_cosmos):
        """Creating session should store in Cosmos DB."""
        cosmos_client, container = mock_cosmos
        container.upsert_item = AsyncMock()

        from shared.auth.session_manager import SessionManager

        manager = SessionManager(cosmos_client=cosmos_client)
        manager._initialized = True
        manager._container = container

        session = await manager.create_session(channel="web", device_id="test-device")

        assert session is not None
        assert session.auth_level == AuthLevel.ANONYMOUS
        container.upsert_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_cache_hit(self, mock_cosmos):
        """Cached sessions should be returned without Cosmos query."""
        cosmos_client, container = mock_cosmos

        from shared.auth.session_manager import SessionManager

        manager = SessionManager(cosmos_client=cosmos_client)
        manager._initialized = True
        manager._container = container

        # Create and cache a session
        session = create_anonymous_session()
        manager._cache_session(session)

        # Query should hit cache
        container.query_items = AsyncMock()
        result = await manager.get_session(session.session_id)

        assert result == session
        container.query_items.assert_not_called()

    @pytest.mark.asyncio
    async def test_upgrade_to_identified_persists(self, mock_cosmos):
        """Upgrading session should persist changes."""
        cosmos_client, container = mock_cosmos
        container.upsert_item = AsyncMock()

        from shared.auth.session_manager import SessionManager

        manager = SessionManager(cosmos_client=cosmos_client)
        manager._initialized = True
        manager._container = container

        # Create session in cache
        session = create_anonymous_session()
        manager._cache_session(session)

        # Upgrade
        upgraded = await manager.upgrade_to_identified(
            session.session_id,
            email="test@example.com"
        )

        assert upgraded.auth_level == AuthLevel.IDENTIFIED
        assert upgraded.identified_email == "test@example.com"
        container.upsert_item.assert_called()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
