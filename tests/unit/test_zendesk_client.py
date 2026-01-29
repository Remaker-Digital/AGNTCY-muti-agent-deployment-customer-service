# ============================================================================
# Unit Tests for Zendesk API Client
# ============================================================================
# Purpose: Test Zendesk Support API client for ticket management
#
# Test Categories:
# 1. Client Initialization - Verify client setup and config
# 2. Ticket Operations - CRUD operations for tickets
# 3. Comment Management - Adding and retrieving comments
# 4. User Operations - User lookup and search
# 5. Search Functionality - Ticket search with filters
# 6. Health Check - API availability checks
# 7. Singleton Pattern - Client reuse and shutdown
#
# Related Documentation:
# - Zendesk Client: shared/api_clients/zendesk.py
# - Zendesk API Reference: https://developer.zendesk.com/api-reference/
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.api_clients.zendesk import (
    ZendeskClient,
    get_zendesk_client,
    shutdown_zendesk_client,
)
from shared.api_clients.base import APIClientConfig, AuthType, APIResponse


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def zendesk_client():
    """Create a Zendesk client for testing."""
    return ZendeskClient()


@pytest.fixture
def mock_api_response():
    """Create a factory for mock API responses."""

    def _create_response(success=True, data=None, error=None, status_code=200):
        response = MagicMock(spec=APIResponse)
        response.success = success
        response.data = data
        response.error = error
        response.status_code = status_code
        response.is_not_found = status_code == 404
        return response

    return _create_response


@pytest.fixture
def sample_ticket():
    """Sample ticket data."""
    return {
        "id": 12345,
        "subject": "Cannot access my account",
        "description": "I forgot my password and cannot reset it.",
        "status": "open",
        "priority": "high",
        "requester_id": 99001,
        "assignee_id": 88001,
        "created_at": "2026-01-28T10:00:00Z",
        "updated_at": "2026-01-28T11:00:00Z",
        "tags": ["password", "account-access"],
    }


@pytest.fixture
def sample_user():
    """Sample user data."""
    return {
        "id": 99001,
        "email": "customer@example.com",
        "name": "John Doe",
        "role": "end-user",
        "created_at": "2025-06-15T08:00:00Z",
    }


@pytest.fixture
def sample_comment():
    """Sample comment data."""
    return {
        "id": 55001,
        "body": "Thank you for contacting support. Let me help you with that.",
        "author_id": 88001,
        "public": True,
        "created_at": "2026-01-28T10:30:00Z",
    }


# =============================================================================
# Test: Client Initialization
# =============================================================================


class TestClientInitialization:
    """Tests for Zendesk client initialization."""

    def test_service_name(self, zendesk_client):
        """Verify service name is correct."""
        assert zendesk_client.service_name == "zendesk"

    def test_default_config_mock_mode(self, zendesk_client):
        """Verify default config uses mock API."""
        config = zendesk_client._default_config()
        assert "localhost:8002" in config.base_url
        assert config.auth_type == AuthType.NONE

    @patch.dict(
        os.environ,
        {
            "USE_REAL_APIS": "true",
            "ZENDESK_SUBDOMAIN": "mycompany",
            "ZENDESK_EMAIL": "admin@mycompany.com",
            "ZENDESK_API_TOKEN": "secret_token_123",
        },
    )
    def test_real_api_config(self):
        """Verify real API config from environment."""
        client = ZendeskClient()
        config = client._default_config()
        assert "mycompany.zendesk.com" in config.base_url
        assert config.auth_type == AuthType.BASIC_AUTH
        assert "admin@mycompany.com/token" in config.api_key
        assert config.api_secret == "secret_token_123"

    @patch.dict(os.environ, {"USE_REAL_APIS": "true"}, clear=False)
    def test_real_api_without_subdomain_falls_back_to_mock(self):
        """Verify fallback to mock when subdomain not set."""
        # Remove ZENDESK_SUBDOMAIN if present
        env_backup = os.environ.get("ZENDESK_SUBDOMAIN")
        if "ZENDESK_SUBDOMAIN" in os.environ:
            del os.environ["ZENDESK_SUBDOMAIN"]

        try:
            client = ZendeskClient()
            config = client._default_config()
            assert "localhost" in config.base_url
        finally:
            if env_backup:
                os.environ["ZENDESK_SUBDOMAIN"] = env_backup

    @patch.dict(os.environ, {"MOCK_ZENDESK_URL": "http://custom-mock:9000"})
    def test_custom_mock_url(self):
        """Verify custom mock URL from environment."""
        client = ZendeskClient()
        config = client._default_config()
        assert config.base_url == "http://custom-mock:9000"


# =============================================================================
# Test: Ticket Operations - Get Ticket
# =============================================================================


class TestGetTicket:
    """Tests for get_ticket method."""

    @pytest.mark.asyncio
    async def test_get_ticket_success(
        self, zendesk_client, mock_api_response, sample_ticket
    ):
        """Verify successful ticket retrieval."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"ticket": sample_ticket})
        )

        result = await zendesk_client.get_ticket("12345")

        assert result is not None
        assert result["id"] == 12345
        assert result["subject"] == "Cannot access my account"
        zendesk_client.get.assert_called_once_with("/tickets/12345.json")

    @pytest.mark.asyncio
    async def test_get_ticket_not_found(self, zendesk_client, mock_api_response):
        """Verify ticket not found handling."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await zendesk_client.get_ticket("99999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_ticket_error(self, zendesk_client, mock_api_response):
        """Verify error handling for ticket retrieval."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(
                success=False, error="Server error", status_code=500
            )
        )

        result = await zendesk_client.get_ticket("12345")

        assert result is None


# =============================================================================
# Test: Ticket Operations - List Tickets
# =============================================================================


class TestListTickets:
    """Tests for list_tickets method."""

    @pytest.mark.asyncio
    async def test_list_tickets_success(
        self, zendesk_client, mock_api_response, sample_ticket
    ):
        """Verify successful ticket listing."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(
                data={
                    "tickets": [sample_ticket],
                    "count": 1,
                    "next_page": None,
                    "previous_page": None,
                }
            )
        )

        result = await zendesk_client.list_tickets()

        assert len(result["tickets"]) == 1
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_list_tickets_with_status_filter(
        self, zendesk_client, mock_api_response
    ):
        """Verify status filter is passed."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"tickets": [], "count": 0})
        )

        await zendesk_client.list_tickets(status="open")

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["status"] == "open"

    @pytest.mark.asyncio
    async def test_list_tickets_with_priority_filter(
        self, zendesk_client, mock_api_response
    ):
        """Verify priority filter is passed."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"tickets": [], "count": 0})
        )

        await zendesk_client.list_tickets(priority="urgent")

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["priority"] == "urgent"

    @pytest.mark.asyncio
    async def test_list_tickets_with_assignee_filter(
        self, zendesk_client, mock_api_response
    ):
        """Verify assignee filter is passed."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"tickets": [], "count": 0})
        )

        await zendesk_client.list_tickets(assignee_id="88001")

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["assignee_id"] == "88001"

    @pytest.mark.asyncio
    async def test_list_tickets_with_requester_filter(
        self, zendesk_client, mock_api_response
    ):
        """Verify requester filter is passed."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"tickets": [], "count": 0})
        )

        await zendesk_client.list_tickets(requester_id="99001")

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["requester_id"] == "99001"

    @pytest.mark.asyncio
    async def test_list_tickets_pagination(self, zendesk_client, mock_api_response):
        """Verify pagination parameters."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"tickets": [], "count": 0})
        )

        await zendesk_client.list_tickets(page=3, per_page=50)

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["page"] == 3
        assert call_args[1]["params"]["per_page"] == 50

    @pytest.mark.asyncio
    async def test_list_tickets_per_page_max_100(
        self, zendesk_client, mock_api_response
    ):
        """Verify per_page is capped at 100."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"tickets": [], "count": 0})
        )

        await zendesk_client.list_tickets(per_page=200)

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["per_page"] == 100

    @pytest.mark.asyncio
    async def test_list_tickets_error_returns_empty(
        self, zendesk_client, mock_api_response
    ):
        """Verify error returns empty result."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await zendesk_client.list_tickets()

        assert result["tickets"] == []
        assert result["count"] == 0


# =============================================================================
# Test: Ticket Operations - Create Ticket
# =============================================================================


class TestCreateTicket:
    """Tests for create_ticket method."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(
        self, zendesk_client, mock_api_response, sample_ticket
    ):
        """Verify successful ticket creation."""
        zendesk_client.post = AsyncMock(
            return_value=mock_api_response(data={"ticket": sample_ticket})
        )

        result = await zendesk_client.create_ticket(
            subject="Cannot access my account",
            description="I forgot my password",
            requester_email="customer@example.com",
        )

        assert result is not None
        assert result["id"] == 12345
        zendesk_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_ticket_payload_structure(
        self, zendesk_client, mock_api_response
    ):
        """Verify correct payload structure."""
        zendesk_client.post = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.create_ticket(
            subject="Test Subject",
            description="Test Description",
            requester_email="test@example.com",
            priority="high",
        )

        call_args = zendesk_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["subject"] == "Test Subject"
        assert payload["ticket"]["comment"]["body"] == "Test Description"
        assert payload["ticket"]["requester"]["email"] == "test@example.com"
        assert payload["ticket"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_create_ticket_with_tags(self, zendesk_client, mock_api_response):
        """Verify tags are included in payload."""
        zendesk_client.post = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.create_ticket(
            subject="Test",
            description="Test",
            requester_email="test@example.com",
            tags=["urgent", "billing"],
        )

        call_args = zendesk_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["tags"] == ["urgent", "billing"]

    @pytest.mark.asyncio
    async def test_create_ticket_with_custom_fields(
        self, zendesk_client, mock_api_response
    ):
        """Verify custom fields are included."""
        zendesk_client.post = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        custom_fields = [{"id": 123, "value": "premium"}]
        await zendesk_client.create_ticket(
            subject="Test",
            description="Test",
            requester_email="test@example.com",
            custom_fields=custom_fields,
        )

        call_args = zendesk_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["custom_fields"] == custom_fields

    @pytest.mark.asyncio
    async def test_create_ticket_failure(self, zendesk_client, mock_api_response):
        """Verify failure handling."""
        zendesk_client.post = AsyncMock(
            return_value=mock_api_response(success=False, error="Validation failed")
        )

        result = await zendesk_client.create_ticket(
            subject="Test",
            description="Test",
            requester_email="invalid",
        )

        assert result is None


# =============================================================================
# Test: Ticket Operations - Update Ticket
# =============================================================================


class TestUpdateTicket:
    """Tests for update_ticket method."""

    @pytest.mark.asyncio
    async def test_update_ticket_success(
        self, zendesk_client, mock_api_response, sample_ticket
    ):
        """Verify successful ticket update."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": sample_ticket})
        )

        result = await zendesk_client.update_ticket("12345", status="pending")

        assert result is not None
        zendesk_client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_ticket_status(self, zendesk_client, mock_api_response):
        """Verify status update payload."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.update_ticket("12345", status="solved")

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["status"] == "solved"

    @pytest.mark.asyncio
    async def test_update_ticket_priority(self, zendesk_client, mock_api_response):
        """Verify priority update payload."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.update_ticket("12345", priority="urgent")

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["priority"] == "urgent"

    @pytest.mark.asyncio
    async def test_update_ticket_assignee(self, zendesk_client, mock_api_response):
        """Verify assignee update payload."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.update_ticket("12345", assignee_id="88002")

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["assignee_id"] == "88002"

    @pytest.mark.asyncio
    async def test_update_ticket_tags(self, zendesk_client, mock_api_response):
        """Verify tags update payload."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.update_ticket("12345", tags=["resolved", "feedback"])

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["tags"] == ["resolved", "feedback"]

    @pytest.mark.asyncio
    async def test_update_ticket_with_public_comment(
        self, zendesk_client, mock_api_response
    ):
        """Verify public comment in update."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.update_ticket(
            "12345", comment="Working on your issue", public=True
        )

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["comment"]["body"] == "Working on your issue"
        assert payload["ticket"]["comment"]["public"] is True

    @pytest.mark.asyncio
    async def test_update_ticket_with_internal_note(
        self, zendesk_client, mock_api_response
    ):
        """Verify internal note (non-public comment)."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.update_ticket(
            "12345", comment="Internal investigation", public=False
        )

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["comment"]["public"] is False

    @pytest.mark.asyncio
    async def test_update_ticket_failure(self, zendesk_client, mock_api_response):
        """Verify failure handling."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(success=False, error="Not found")
        )

        result = await zendesk_client.update_ticket("99999", status="closed")

        assert result is None


# =============================================================================
# Test: Ticket Operations - Close Ticket
# =============================================================================


class TestCloseTicket:
    """Tests for close_ticket method."""

    @pytest.mark.asyncio
    async def test_close_ticket_success(self, zendesk_client, mock_api_response):
        """Verify successful ticket close."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1, "status": "solved"}})
        )

        result = await zendesk_client.close_ticket("12345")

        assert result is True

    @pytest.mark.asyncio
    async def test_close_ticket_with_comment(self, zendesk_client, mock_api_response):
        """Verify close with custom comment."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.close_ticket("12345", comment="Issue has been resolved.")

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["comment"]["body"] == "Issue has been resolved."
        assert payload["ticket"]["status"] == "solved"

    @pytest.mark.asyncio
    async def test_close_ticket_default_comment(self, zendesk_client, mock_api_response):
        """Verify default closing comment."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.close_ticket("12345")

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["comment"]["body"] == "Ticket resolved."

    @pytest.mark.asyncio
    async def test_close_ticket_failure(self, zendesk_client, mock_api_response):
        """Verify failure returns False."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(success=False, error="Cannot close")
        )

        result = await zendesk_client.close_ticket("12345")

        assert result is False


# =============================================================================
# Test: Comment Operations
# =============================================================================


class TestCommentOperations:
    """Tests for comment operations."""

    @pytest.mark.asyncio
    async def test_get_comments_success(
        self, zendesk_client, mock_api_response, sample_comment
    ):
        """Verify successful comment retrieval."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"comments": [sample_comment]})
        )

        result = await zendesk_client.get_comments("12345")

        assert len(result) == 1
        assert result[0]["body"] == sample_comment["body"]
        zendesk_client.get.assert_called_with("/tickets/12345/comments.json")

    @pytest.mark.asyncio
    async def test_get_comments_empty(self, zendesk_client, mock_api_response):
        """Verify empty comments list."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"comments": []})
        )

        result = await zendesk_client.get_comments("12345")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_comments_error(self, zendesk_client, mock_api_response):
        """Verify error returns empty list."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="Not found")
        )

        result = await zendesk_client.get_comments("99999")

        assert result == []

    @pytest.mark.asyncio
    async def test_add_comment_success(self, zendesk_client, mock_api_response):
        """Verify successful comment addition."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 12345}})
        )

        result = await zendesk_client.add_comment("12345", "Thank you for waiting!")

        assert result is not None

    @pytest.mark.asyncio
    async def test_add_comment_public(self, zendesk_client, mock_api_response):
        """Verify public comment payload."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {}})
        )

        await zendesk_client.add_comment("12345", "Public reply", public=True)

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["comment"]["public"] is True

    @pytest.mark.asyncio
    async def test_add_comment_internal(self, zendesk_client, mock_api_response):
        """Verify internal note payload."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {}})
        )

        await zendesk_client.add_comment("12345", "Internal note", public=False)

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["comment"]["public"] is False

    @pytest.mark.asyncio
    async def test_add_comment_with_author(self, zendesk_client, mock_api_response):
        """Verify author_id in payload."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {}})
        )

        await zendesk_client.add_comment("12345", "Comment", author_id="88001")

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["comment"]["author_id"] == "88001"

    @pytest.mark.asyncio
    async def test_add_comment_failure(self, zendesk_client, mock_api_response):
        """Verify failure handling."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(success=False, error="Cannot add comment")
        )

        result = await zendesk_client.add_comment("12345", "Comment")

        assert result is None


# =============================================================================
# Test: User Operations
# =============================================================================


class TestUserOperations:
    """Tests for user operations."""

    @pytest.mark.asyncio
    async def test_get_user_success(
        self, zendesk_client, mock_api_response, sample_user
    ):
        """Verify successful user retrieval."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"user": sample_user})
        )

        result = await zendesk_client.get_user("99001")

        assert result is not None
        assert result["email"] == "customer@example.com"
        zendesk_client.get.assert_called_with("/users/99001.json")

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, zendesk_client, mock_api_response):
        """Verify user not found."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await zendesk_client.get_user("99999")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_users_success(
        self, zendesk_client, mock_api_response, sample_user
    ):
        """Verify successful user search."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"users": [sample_user]})
        )

        result = await zendesk_client.search_users("customer@example.com")

        assert len(result) == 1
        assert result[0]["email"] == "customer@example.com"

    @pytest.mark.asyncio
    async def test_search_users_query_param(self, zendesk_client, mock_api_response):
        """Verify query parameter is passed."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"users": []})
        )

        await zendesk_client.search_users("john@example.com")

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["query"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_search_users_empty(self, zendesk_client, mock_api_response):
        """Verify empty search results."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"users": []})
        )

        result = await zendesk_client.search_users("nonexistent@example.com")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_users_error(self, zendesk_client, mock_api_response):
        """Verify error returns empty list."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="Search failed")
        )

        result = await zendesk_client.search_users("query")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_tickets_success(
        self, zendesk_client, mock_api_response, sample_ticket
    ):
        """Verify getting user's tickets."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"tickets": [sample_ticket]})
        )

        result = await zendesk_client.get_user_tickets("99001")

        assert len(result) == 1
        zendesk_client.get.assert_called()

    @pytest.mark.asyncio
    async def test_get_user_tickets_with_status(
        self, zendesk_client, mock_api_response
    ):
        """Verify status filter for user tickets."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"tickets": []})
        )

        await zendesk_client.get_user_tickets("99001", status="open")

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["status"] == "open"

    @pytest.mark.asyncio
    async def test_get_user_tickets_error(self, zendesk_client, mock_api_response):
        """Verify error returns empty list."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="Not found")
        )

        result = await zendesk_client.get_user_tickets("99999")

        assert result == []


# =============================================================================
# Test: Search Operations
# =============================================================================


class TestSearchOperations:
    """Tests for search operations."""

    @pytest.mark.asyncio
    async def test_search_tickets_success(
        self, zendesk_client, mock_api_response, sample_ticket
    ):
        """Verify successful ticket search."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"results": [sample_ticket]})
        )

        result = await zendesk_client.search_tickets("status:open")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_tickets_query_format(self, zendesk_client, mock_api_response):
        """Verify query includes type:ticket prefix."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"results": []})
        )

        await zendesk_client.search_tickets("priority:urgent")

        call_args = zendesk_client.get.call_args
        assert "type:ticket" in call_args[1]["params"]["query"]
        assert "priority:urgent" in call_args[1]["params"]["query"]

    @pytest.mark.asyncio
    async def test_search_tickets_sort_params(self, zendesk_client, mock_api_response):
        """Verify sort parameters."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"results": []})
        )

        await zendesk_client.search_tickets(
            "status:pending", sort_by="updated_at", sort_order="asc"
        )

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["sort_by"] == "updated_at"
        assert call_args[1]["params"]["sort_order"] == "asc"

    @pytest.mark.asyncio
    async def test_search_tickets_default_sort(self, zendesk_client, mock_api_response):
        """Verify default sort parameters."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"results": []})
        )

        await zendesk_client.search_tickets("assignee:me")

        call_args = zendesk_client.get.call_args
        assert call_args[1]["params"]["sort_by"] == "created_at"
        assert call_args[1]["params"]["sort_order"] == "desc"

    @pytest.mark.asyncio
    async def test_search_tickets_error(self, zendesk_client, mock_api_response):
        """Verify error returns empty list."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="Search error")
        )

        result = await zendesk_client.search_tickets("invalid:query")

        assert result == []


# =============================================================================
# Test: Health Check
# =============================================================================


class TestHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success_users_me(
        self, zendesk_client, mock_api_response
    ):
        """Verify health check with /users/me endpoint."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"user": {"id": 1}})
        )

        result = await zendesk_client.health_check()

        assert result is True
        zendesk_client.get.assert_called_with("/users/me.json")

    @pytest.mark.asyncio
    async def test_health_check_fallback_to_health(
        self, zendesk_client, mock_api_response
    ):
        """Verify fallback to /health endpoint for mock API."""
        # First call fails, second succeeds
        zendesk_client.get = AsyncMock(
            side_effect=[
                mock_api_response(success=False),  # /users/me fails
                mock_api_response(success=True),  # /health succeeds
            ]
        )

        result = await zendesk_client.health_check()

        assert result is True
        assert zendesk_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_both_fail(self, zendesk_client, mock_api_response):
        """Verify health check failure when both endpoints fail."""
        zendesk_client.get = AsyncMock(
            side_effect=[
                mock_api_response(success=False),
                mock_api_response(success=False),
            ]
        )

        result = await zendesk_client.health_check()

        assert result is False


# =============================================================================
# Test: Singleton Pattern
# =============================================================================


class TestSingletonPattern:
    """Tests for singleton client pattern."""

    @pytest.mark.asyncio
    async def test_get_zendesk_client_returns_client(self):
        """Verify get_zendesk_client returns a client."""
        # Reset singleton
        import shared.api_clients.zendesk as zendesk_module

        zendesk_module._client_instance = None

        client = await get_zendesk_client()

        assert client is not None
        assert isinstance(client, ZendeskClient)

    @pytest.mark.asyncio
    async def test_get_zendesk_client_singleton(self):
        """Verify same instance is returned."""
        import shared.api_clients.zendesk as zendesk_module

        zendesk_module._client_instance = None

        client1 = await get_zendesk_client()
        client2 = await get_zendesk_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_shutdown_zendesk_client(self):
        """Verify shutdown clears singleton."""
        import shared.api_clients.zendesk as zendesk_module

        # Create a client
        zendesk_module._client_instance = None
        client = await get_zendesk_client()
        client.close = AsyncMock()

        # Shutdown
        await shutdown_zendesk_client()

        assert zendesk_module._client_instance is None
        client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_when_no_client(self):
        """Verify shutdown handles no client gracefully."""
        import shared.api_clients.zendesk as zendesk_module

        zendesk_module._client_instance = None

        # Should not raise
        await shutdown_zendesk_client()


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_ticket_id(self, zendesk_client, mock_api_response):
        """Verify handling of empty ticket ID."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await zendesk_client.get_ticket("")

        assert result is None

    @pytest.mark.asyncio
    async def test_special_characters_in_search(
        self, zendesk_client, mock_api_response
    ):
        """Verify special characters in search query."""
        zendesk_client.get = AsyncMock(
            return_value=mock_api_response(data={"results": []})
        )

        # Should not raise
        await zendesk_client.search_tickets("subject:\"Hello World\" AND status:open")

    @pytest.mark.asyncio
    async def test_unicode_in_ticket_content(self, zendesk_client, mock_api_response):
        """Verify unicode characters in ticket."""
        zendesk_client.post = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        # Should not raise
        await zendesk_client.create_ticket(
            subject="Café Order Issue ☕",
            description="Issue with my order: 日本語テスト",
            requester_email="test@example.com",
        )

    @pytest.mark.asyncio
    async def test_very_long_description(self, zendesk_client, mock_api_response):
        """Verify very long ticket description."""
        zendesk_client.post = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        long_description = "A" * 10000

        # Should not raise
        await zendesk_client.create_ticket(
            subject="Long Description Test",
            description=long_description,
            requester_email="test@example.com",
        )

    @pytest.mark.asyncio
    async def test_empty_tags_list(self, zendesk_client, mock_api_response):
        """Verify empty tags list is handled."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        await zendesk_client.update_ticket("12345", tags=[])

        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert payload["ticket"]["tags"] == []

    @pytest.mark.asyncio
    async def test_none_vs_missing_tags(self, zendesk_client, mock_api_response):
        """Verify None tags vs not passing tags."""
        zendesk_client.put = AsyncMock(
            return_value=mock_api_response(data={"ticket": {"id": 1}})
        )

        # Not passing tags
        await zendesk_client.update_ticket("12345", status="open")
        call_args = zendesk_client.put.call_args
        payload = call_args[1]["json_data"]
        assert "tags" not in payload["ticket"]
