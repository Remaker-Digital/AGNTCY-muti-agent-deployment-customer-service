# ============================================================================
# Unit Tests for Mailchimp API Client
# ============================================================================
# Purpose: Test Mailchimp Marketing API client for email marketing integration
#
# Test Categories:
# 1. Client Initialization - Verify client setup and config
# 2. List/Audience Operations - CRUD operations for lists
# 3. Member Management - Subscription and member updates
# 4. Campaign Operations - Campaign retrieval and reports
# 5. Automation Operations - Workflow access
# 6. Tag Operations - Member tagging
# 7. Health Check - API availability checks
# 8. Singleton Pattern - Client reuse and shutdown
#
# Related Documentation:
# - Mailchimp Client: shared/api_clients/mailchimp.py
# - Mailchimp API Reference: https://mailchimp.com/developer/marketing/api/
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import hashlib

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.api_clients.mailchimp import (
    MailchimpClient,
    get_mailchimp_client,
    shutdown_mailchimp_client,
)
from shared.api_clients.base import APIClientConfig, AuthType, APIResponse


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mailchimp_client():
    """Create a Mailchimp client for testing."""
    return MailchimpClient()


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
def sample_list():
    """Sample audience/list data."""
    return {
        "id": "abc123def4",
        "name": "Newsletter Subscribers",
        "contact": {
            "company": "BrewVi Coffee",
            "address1": "123 Coffee Lane",
            "city": "Seattle",
            "state": "WA",
            "zip": "98101",
            "country": "US",
        },
        "stats": {
            "member_count": 5000,
            "unsubscribe_count": 150,
            "cleaned_count": 50,
            "open_rate": 0.35,
            "click_rate": 0.12,
        },
        "date_created": "2025-01-15T10:00:00+00:00",
    }


@pytest.fixture
def sample_member():
    """Sample member data."""
    return {
        "id": "a1b2c3d4e5",
        "email_address": "customer@example.com",
        "status": "subscribed",
        "merge_fields": {
            "FNAME": "John",
            "LNAME": "Doe",
        },
        "tags": [{"id": 1, "name": "coffee-lover"}],
        "stats": {
            "avg_open_rate": 0.42,
            "avg_click_rate": 0.15,
        },
        "timestamp_signup": "2025-06-15T08:00:00+00:00",
    }


@pytest.fixture
def sample_campaign():
    """Sample campaign data."""
    return {
        "id": "camp12345",
        "type": "regular",
        "status": "sent",
        "settings": {
            "subject_line": "New Coffee Arrivals!",
            "title": "January Newsletter",
            "from_name": "BrewVi Coffee",
            "reply_to": "info@brewvi.com",
        },
        "send_time": "2026-01-20T10:00:00+00:00",
        "emails_sent": 4500,
    }


@pytest.fixture
def sample_automation():
    """Sample automation workflow data."""
    return {
        "id": "auto123",
        "create_time": "2025-06-01T09:00:00+00:00",
        "status": "sending",
        "recipients": {"list_id": "abc123def4"},
        "settings": {
            "title": "Welcome Series",
            "from_name": "BrewVi Coffee",
        },
        "tracking": {
            "opens": True,
            "clicks": True,
        },
    }


# =============================================================================
# Test: Client Initialization
# =============================================================================


class TestClientInitialization:
    """Tests for Mailchimp client initialization."""

    def test_service_name(self, mailchimp_client):
        """Verify service name is correct."""
        assert mailchimp_client.service_name == "mailchimp"

    def test_default_config_mock_mode(self, mailchimp_client):
        """Verify default config uses mock API."""
        config = mailchimp_client._default_config()
        assert "localhost:8003" in config.base_url
        assert config.auth_type == AuthType.NONE

    @patch.dict(
        os.environ,
        {
            "USE_REAL_APIS": "true",
            "MAILCHIMP_API_KEY": "abc123xyz-us21",
        },
    )
    def test_real_api_config(self):
        """Verify real API config from environment."""
        client = MailchimpClient()
        config = client._default_config()
        assert "us21.api.mailchimp.com" in config.base_url
        assert config.auth_type == AuthType.BASIC_AUTH
        assert config.api_key == "anystring"
        assert config.api_secret == "abc123xyz-us21"

    @patch.dict(
        os.environ,
        {
            "USE_REAL_APIS": "true",
            "MAILCHIMP_API_KEY": "keywithnodatacenter",
        },
    )
    def test_api_key_without_dc_defaults_to_us1(self):
        """Verify datacenter defaults to us1 if not in key."""
        client = MailchimpClient()
        config = client._default_config()
        assert "us1.api.mailchimp.com" in config.base_url

    @patch.dict(os.environ, {"USE_REAL_APIS": "true"}, clear=False)
    def test_real_api_without_key_falls_back_to_mock(self):
        """Verify fallback to mock when API key not set."""
        env_backup = os.environ.get("MAILCHIMP_API_KEY")
        if "MAILCHIMP_API_KEY" in os.environ:
            del os.environ["MAILCHIMP_API_KEY"]

        try:
            client = MailchimpClient()
            config = client._default_config()
            assert "localhost" in config.base_url
        finally:
            if env_backup:
                os.environ["MAILCHIMP_API_KEY"] = env_backup

    @patch.dict(os.environ, {"MOCK_MAILCHIMP_URL": "http://custom-mock:9003"})
    def test_custom_mock_url(self):
        """Verify custom mock URL from environment."""
        client = MailchimpClient()
        config = client._default_config()
        assert config.base_url == "http://custom-mock:9003"


# =============================================================================
# Test: List/Audience Operations
# =============================================================================


class TestListOperations:
    """Tests for list/audience operations."""

    @pytest.mark.asyncio
    async def test_get_lists_success(
        self, mailchimp_client, mock_api_response, sample_list
    ):
        """Verify successful lists retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(
                data={"lists": [sample_list], "total_items": 1}
            )
        )

        result = await mailchimp_client.get_lists()

        assert len(result["lists"]) == 1
        assert result["total_items"] == 1
        assert result["lists"][0]["name"] == "Newsletter Subscribers"

    @pytest.mark.asyncio
    async def test_get_lists_pagination(self, mailchimp_client, mock_api_response):
        """Verify pagination parameters."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"lists": [], "total_items": 0})
        )

        await mailchimp_client.get_lists(offset=20, count=50)

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["offset"] == 20
        assert call_args[1]["params"]["count"] == 50

    @pytest.mark.asyncio
    async def test_get_lists_count_max_1000(self, mailchimp_client, mock_api_response):
        """Verify count is capped at 1000."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"lists": [], "total_items": 0})
        )

        await mailchimp_client.get_lists(count=2000)

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["count"] == 1000

    @pytest.mark.asyncio
    async def test_get_lists_error_returns_empty(
        self, mailchimp_client, mock_api_response
    ):
        """Verify error returns empty result."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await mailchimp_client.get_lists()

        assert result["lists"] == []
        assert result["total_items"] == 0

    @pytest.mark.asyncio
    async def test_get_list_success(
        self, mailchimp_client, mock_api_response, sample_list
    ):
        """Verify successful list retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data=sample_list)
        )

        result = await mailchimp_client.get_list("abc123def4")

        assert result is not None
        assert result["name"] == "Newsletter Subscribers"
        mailchimp_client.get.assert_called_with("/lists/abc123def4")

    @pytest.mark.asyncio
    async def test_get_list_not_found(self, mailchimp_client, mock_api_response):
        """Verify list not found handling."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await mailchimp_client.get_list("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_list_stats_success(
        self, mailchimp_client, mock_api_response, sample_list
    ):
        """Verify list stats retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"stats": sample_list["stats"]})
        )

        result = await mailchimp_client.get_list_stats("abc123def4")

        assert result is not None
        assert result["member_count"] == 5000
        assert result["open_rate"] == 0.35

    @pytest.mark.asyncio
    async def test_get_list_stats_fields_param(
        self, mailchimp_client, mock_api_response
    ):
        """Verify fields parameter is passed."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"stats": {}})
        )

        await mailchimp_client.get_list_stats("abc123def4")

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["fields"] == "stats"

    @pytest.mark.asyncio
    async def test_get_list_stats_error(self, mailchimp_client, mock_api_response):
        """Verify stats error handling."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="Not found")
        )

        result = await mailchimp_client.get_list_stats("invalid")

        assert result is None


# =============================================================================
# Test: Member Operations
# =============================================================================


class TestMemberOperations:
    """Tests for member operations."""

    @pytest.mark.asyncio
    async def test_get_members_success(
        self, mailchimp_client, mock_api_response, sample_member
    ):
        """Verify successful members retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(
                data={"members": [sample_member], "total_items": 1}
            )
        )

        result = await mailchimp_client.get_members("abc123def4")

        assert len(result["members"]) == 1
        assert result["members"][0]["email_address"] == "customer@example.com"

    @pytest.mark.asyncio
    async def test_get_members_with_status_filter(
        self, mailchimp_client, mock_api_response
    ):
        """Verify status filter is passed."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"members": [], "total_items": 0})
        )

        await mailchimp_client.get_members("abc123def4", status="subscribed")

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["status"] == "subscribed"

    @pytest.mark.asyncio
    async def test_get_members_pagination(self, mailchimp_client, mock_api_response):
        """Verify pagination parameters."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"members": [], "total_items": 0})
        )

        await mailchimp_client.get_members("abc123def4", offset=100, count=50)

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["offset"] == 100
        assert call_args[1]["params"]["count"] == 50

    @pytest.mark.asyncio
    async def test_get_members_count_max_1000(
        self, mailchimp_client, mock_api_response
    ):
        """Verify count is capped at 1000."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"members": [], "total_items": 0})
        )

        await mailchimp_client.get_members("abc123def4", count=5000)

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["count"] == 1000

    @pytest.mark.asyncio
    async def test_get_members_error(self, mailchimp_client, mock_api_response):
        """Verify error returns empty result."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await mailchimp_client.get_members("abc123def4")

        assert result["members"] == []
        assert result["total_items"] == 0

    @pytest.mark.asyncio
    async def test_get_member_success(
        self, mailchimp_client, mock_api_response, sample_member
    ):
        """Verify successful member retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data=sample_member)
        )

        result = await mailchimp_client.get_member("abc123def4", "customer@example.com")

        assert result is not None
        assert result["email_address"] == "customer@example.com"

    @pytest.mark.asyncio
    async def test_get_member_uses_md5_hash(
        self, mailchimp_client, mock_api_response
    ):
        """Verify email is hashed with MD5."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={})
        )

        email = "Customer@Example.com"
        expected_hash = hashlib.md5(email.lower().encode()).hexdigest()

        await mailchimp_client.get_member("abc123def4", email)

        call_args = mailchimp_client.get.call_args
        assert expected_hash in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_member_not_found(self, mailchimp_client, mock_api_response):
        """Verify member not found handling."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await mailchimp_client.get_member("abc123def4", "nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_subscribe_member_success(
        self, mailchimp_client, mock_api_response, sample_member
    ):
        """Verify successful member subscription."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(data=sample_member)
        )

        result = await mailchimp_client.subscribe_member(
            "abc123def4", "new@example.com"
        )

        assert result is not None
        mailchimp_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_member_payload(
        self, mailchimp_client, mock_api_response
    ):
        """Verify subscription payload structure."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(data={})
        )

        await mailchimp_client.subscribe_member(
            "abc123def4",
            "new@example.com",
            merge_fields={"FNAME": "Jane", "LNAME": "Smith"},
            tags=["vip", "newsletter"],
            status="pending",
        )

        call_args = mailchimp_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["email_address"] == "new@example.com"
        assert payload["status"] == "pending"
        assert payload["merge_fields"]["FNAME"] == "Jane"
        assert "vip" in payload["tags"]

    @pytest.mark.asyncio
    async def test_subscribe_member_default_status(
        self, mailchimp_client, mock_api_response
    ):
        """Verify default status is subscribed."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(data={})
        )

        await mailchimp_client.subscribe_member("abc123def4", "new@example.com")

        call_args = mailchimp_client.post.call_args
        payload = call_args[1]["json_data"]
        assert payload["status"] == "subscribed"

    @pytest.mark.asyncio
    async def test_subscribe_member_failure(
        self, mailchimp_client, mock_api_response
    ):
        """Verify subscription failure handling."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(success=False, error="Already subscribed")
        )

        result = await mailchimp_client.subscribe_member(
            "abc123def4", "existing@example.com"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_member_success(
        self, mailchimp_client, mock_api_response, sample_member
    ):
        """Verify successful member update."""
        mailchimp_client._request = AsyncMock(
            return_value=mock_api_response(data=sample_member)
        )

        result = await mailchimp_client.update_member(
            "abc123def4",
            "customer@example.com",
            merge_fields={"FNAME": "Jonathan"},
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_update_member_uses_patch(
        self, mailchimp_client, mock_api_response
    ):
        """Verify PATCH method is used."""
        mailchimp_client._request = AsyncMock(
            return_value=mock_api_response(data={})
        )

        await mailchimp_client.update_member(
            "abc123def4", "customer@example.com", status="unsubscribed"
        )

        call_args = mailchimp_client._request.call_args
        assert call_args[0][0] == "PATCH"

    @pytest.mark.asyncio
    async def test_update_member_payload(
        self, mailchimp_client, mock_api_response
    ):
        """Verify update payload."""
        mailchimp_client._request = AsyncMock(
            return_value=mock_api_response(data={})
        )

        await mailchimp_client.update_member(
            "abc123def4",
            "customer@example.com",
            merge_fields={"FNAME": "Updated"},
            status="pending",
        )

        call_args = mailchimp_client._request.call_args
        payload = call_args[1]["json_data"]
        assert payload["merge_fields"]["FNAME"] == "Updated"
        assert payload["status"] == "pending"

    @pytest.mark.asyncio
    async def test_update_member_failure(
        self, mailchimp_client, mock_api_response
    ):
        """Verify update failure handling."""
        mailchimp_client._request = AsyncMock(
            return_value=mock_api_response(success=False, error="Not found")
        )

        result = await mailchimp_client.update_member(
            "abc123def4", "nonexistent@example.com", status="subscribed"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_unsubscribe_member_success(
        self, mailchimp_client, mock_api_response
    ):
        """Verify successful unsubscribe."""
        mailchimp_client._request = AsyncMock(
            return_value=mock_api_response(data={"status": "unsubscribed"})
        )

        result = await mailchimp_client.unsubscribe_member(
            "abc123def4", "customer@example.com"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_unsubscribe_member_sets_status(
        self, mailchimp_client, mock_api_response
    ):
        """Verify unsubscribe sets correct status."""
        mailchimp_client._request = AsyncMock(
            return_value=mock_api_response(data={})
        )

        await mailchimp_client.unsubscribe_member("abc123def4", "customer@example.com")

        call_args = mailchimp_client._request.call_args
        payload = call_args[1]["json_data"]
        assert payload["status"] == "unsubscribed"

    @pytest.mark.asyncio
    async def test_unsubscribe_member_failure(
        self, mailchimp_client, mock_api_response
    ):
        """Verify unsubscribe failure returns False."""
        mailchimp_client._request = AsyncMock(
            return_value=mock_api_response(success=False, error="Not found")
        )

        result = await mailchimp_client.unsubscribe_member(
            "abc123def4", "nonexistent@example.com"
        )

        assert result is False


# =============================================================================
# Test: Campaign Operations
# =============================================================================


class TestCampaignOperations:
    """Tests for campaign operations."""

    @pytest.mark.asyncio
    async def test_get_campaigns_success(
        self, mailchimp_client, mock_api_response, sample_campaign
    ):
        """Verify successful campaigns retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(
                data={"campaigns": [sample_campaign], "total_items": 1}
            )
        )

        result = await mailchimp_client.get_campaigns()

        assert len(result["campaigns"]) == 1
        assert result["campaigns"][0]["status"] == "sent"

    @pytest.mark.asyncio
    async def test_get_campaigns_with_status_filter(
        self, mailchimp_client, mock_api_response
    ):
        """Verify status filter is passed."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"campaigns": [], "total_items": 0})
        )

        await mailchimp_client.get_campaigns(status="sent")

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["status"] == "sent"

    @pytest.mark.asyncio
    async def test_get_campaigns_with_list_filter(
        self, mailchimp_client, mock_api_response
    ):
        """Verify list_id filter is passed."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"campaigns": [], "total_items": 0})
        )

        await mailchimp_client.get_campaigns(list_id="abc123def4")

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["list_id"] == "abc123def4"

    @pytest.mark.asyncio
    async def test_get_campaigns_pagination(
        self, mailchimp_client, mock_api_response
    ):
        """Verify pagination parameters."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"campaigns": [], "total_items": 0})
        )

        await mailchimp_client.get_campaigns(offset=50, count=25)

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["offset"] == 50
        assert call_args[1]["params"]["count"] == 25

    @pytest.mark.asyncio
    async def test_get_campaigns_error(self, mailchimp_client, mock_api_response):
        """Verify error returns empty result."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await mailchimp_client.get_campaigns()

        assert result["campaigns"] == []
        assert result["total_items"] == 0

    @pytest.mark.asyncio
    async def test_get_campaign_success(
        self, mailchimp_client, mock_api_response, sample_campaign
    ):
        """Verify successful campaign retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data=sample_campaign)
        )

        result = await mailchimp_client.get_campaign("camp12345")

        assert result is not None
        assert result["settings"]["subject_line"] == "New Coffee Arrivals!"
        mailchimp_client.get.assert_called_with("/campaigns/camp12345")

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(
        self, mailchimp_client, mock_api_response
    ):
        """Verify campaign not found handling."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await mailchimp_client.get_campaign("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_campaign_report_success(
        self, mailchimp_client, mock_api_response
    ):
        """Verify successful report retrieval."""
        report_data = {
            "id": "camp12345",
            "opens": {"opens_total": 2500, "unique_opens": 2000},
            "clicks": {"clicks_total": 500, "unique_clicks": 400},
            "bounces": {"hard_bounces": 10, "soft_bounces": 25},
        }
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data=report_data)
        )

        result = await mailchimp_client.get_campaign_report("camp12345")

        assert result is not None
        assert result["opens"]["opens_total"] == 2500
        mailchimp_client.get.assert_called_with("/reports/camp12345")

    @pytest.mark.asyncio
    async def test_get_campaign_report_not_found(
        self, mailchimp_client, mock_api_response
    ):
        """Verify report not found handling."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await mailchimp_client.get_campaign_report("nonexistent")

        assert result is None


# =============================================================================
# Test: Automation Operations
# =============================================================================


class TestAutomationOperations:
    """Tests for automation workflow operations."""

    @pytest.mark.asyncio
    async def test_get_automations_success(
        self, mailchimp_client, mock_api_response, sample_automation
    ):
        """Verify successful automations retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(
                data={"automations": [sample_automation], "total_items": 1}
            )
        )

        result = await mailchimp_client.get_automations()

        assert len(result["automations"]) == 1
        assert result["automations"][0]["settings"]["title"] == "Welcome Series"

    @pytest.mark.asyncio
    async def test_get_automations_pagination(
        self, mailchimp_client, mock_api_response
    ):
        """Verify pagination parameters."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"automations": [], "total_items": 0})
        )

        await mailchimp_client.get_automations(offset=10, count=25)

        call_args = mailchimp_client.get.call_args
        assert call_args[1]["params"]["offset"] == 10
        assert call_args[1]["params"]["count"] == 25

    @pytest.mark.asyncio
    async def test_get_automations_error(
        self, mailchimp_client, mock_api_response
    ):
        """Verify error returns empty result."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, error="API Error")
        )

        result = await mailchimp_client.get_automations()

        assert result["automations"] == []
        assert result["total_items"] == 0

    @pytest.mark.asyncio
    async def test_get_automation_success(
        self, mailchimp_client, mock_api_response, sample_automation
    ):
        """Verify successful automation retrieval."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data=sample_automation)
        )

        result = await mailchimp_client.get_automation("auto123")

        assert result is not None
        assert result["status"] == "sending"
        mailchimp_client.get.assert_called_with("/automations/auto123")

    @pytest.mark.asyncio
    async def test_get_automation_not_found(
        self, mailchimp_client, mock_api_response
    ):
        """Verify automation not found handling."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await mailchimp_client.get_automation("nonexistent")

        assert result is None


# =============================================================================
# Test: Tag Operations
# =============================================================================


class TestTagOperations:
    """Tests for member tag operations."""

    @pytest.mark.asyncio
    async def test_add_member_tags_success(
        self, mailchimp_client, mock_api_response
    ):
        """Verify successful tag addition."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(success=True, data={})
        )

        result = await mailchimp_client.add_member_tags(
            "abc123def4", "customer@example.com", ["vip", "loyalty-member"]
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_add_member_tags_payload(
        self, mailchimp_client, mock_api_response
    ):
        """Verify tag payload structure."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(success=True, data={})
        )

        await mailchimp_client.add_member_tags(
            "abc123def4", "customer@example.com", ["vip", "premium"]
        )

        call_args = mailchimp_client.post.call_args
        payload = call_args[1]["json_data"]
        assert len(payload["tags"]) == 2
        assert payload["tags"][0]["name"] == "vip"
        assert payload["tags"][0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_add_member_tags_uses_md5_hash(
        self, mailchimp_client, mock_api_response
    ):
        """Verify email is hashed with MD5."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(success=True, data={})
        )

        email = "Test@Example.com"
        expected_hash = hashlib.md5(email.lower().encode()).hexdigest()

        await mailchimp_client.add_member_tags("abc123def4", email, ["tag"])

        call_args = mailchimp_client.post.call_args
        assert expected_hash in call_args[0][0]

    @pytest.mark.asyncio
    async def test_add_member_tags_failure(
        self, mailchimp_client, mock_api_response
    ):
        """Verify tag addition failure."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(success=False, error="Member not found")
        )

        result = await mailchimp_client.add_member_tags(
            "abc123def4", "nonexistent@example.com", ["tag"]
        )

        assert result is False


# =============================================================================
# Test: Health Check
# =============================================================================


class TestHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success_root(
        self, mailchimp_client, mock_api_response
    ):
        """Verify health check with root endpoint."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={"account_id": "123"})
        )

        result = await mailchimp_client.health_check()

        assert result is True
        mailchimp_client.get.assert_called_with("/")

    @pytest.mark.asyncio
    async def test_health_check_fallback_to_health(
        self, mailchimp_client, mock_api_response
    ):
        """Verify fallback to /health endpoint for mock API."""
        mailchimp_client.get = AsyncMock(
            side_effect=[
                mock_api_response(success=False),  # / fails
                mock_api_response(success=True),  # /health succeeds
            ]
        )

        result = await mailchimp_client.health_check()

        assert result is True
        assert mailchimp_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_both_fail(
        self, mailchimp_client, mock_api_response
    ):
        """Verify health check failure when both endpoints fail."""
        mailchimp_client.get = AsyncMock(
            side_effect=[
                mock_api_response(success=False),
                mock_api_response(success=False),
            ]
        )

        result = await mailchimp_client.health_check()

        assert result is False


# =============================================================================
# Test: Singleton Pattern
# =============================================================================


class TestSingletonPattern:
    """Tests for singleton client pattern."""

    @pytest.mark.asyncio
    async def test_get_mailchimp_client_returns_client(self):
        """Verify get_mailchimp_client returns a client."""
        import shared.api_clients.mailchimp as mailchimp_module

        mailchimp_module._client_instance = None

        client = await get_mailchimp_client()

        assert client is not None
        assert isinstance(client, MailchimpClient)

    @pytest.mark.asyncio
    async def test_get_mailchimp_client_singleton(self):
        """Verify same instance is returned."""
        import shared.api_clients.mailchimp as mailchimp_module

        mailchimp_module._client_instance = None

        client1 = await get_mailchimp_client()
        client2 = await get_mailchimp_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_shutdown_mailchimp_client(self):
        """Verify shutdown clears singleton."""
        import shared.api_clients.mailchimp as mailchimp_module

        mailchimp_module._client_instance = None
        client = await get_mailchimp_client()
        client.close = AsyncMock()

        await shutdown_mailchimp_client()

        assert mailchimp_module._client_instance is None
        client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_when_no_client(self):
        """Verify shutdown handles no client gracefully."""
        import shared.api_clients.mailchimp as mailchimp_module

        mailchimp_module._client_instance = None

        # Should not raise
        await shutdown_mailchimp_client()


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_list_id(self, mailchimp_client, mock_api_response):
        """Verify handling of empty list ID."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(success=False, status_code=404)
        )

        result = await mailchimp_client.get_list("")

        assert result is None

    @pytest.mark.asyncio
    async def test_unicode_in_merge_fields(
        self, mailchimp_client, mock_api_response
    ):
        """Verify unicode characters in merge fields."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(data={})
        )

        # Should not raise
        await mailchimp_client.subscribe_member(
            "abc123def4",
            "test@example.com",
            merge_fields={"FNAME": "José", "LNAME": "García"},
        )

    @pytest.mark.asyncio
    async def test_email_case_insensitive_hash(
        self, mailchimp_client, mock_api_response
    ):
        """Verify email hash is case-insensitive."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={})
        )

        # Get hashes for both cases
        lower_hash = hashlib.md5("test@example.com".encode()).hexdigest()

        await mailchimp_client.get_member("abc123def4", "TEST@EXAMPLE.COM")

        call_args = mailchimp_client.get.call_args
        assert lower_hash in call_args[0][0]

    @pytest.mark.asyncio
    async def test_empty_tags_list(self, mailchimp_client, mock_api_response):
        """Verify empty tags list is not included in payload."""
        mailchimp_client.post = AsyncMock(
            return_value=mock_api_response(data={})
        )

        await mailchimp_client.subscribe_member(
            "abc123def4", "test@example.com", tags=[]
        )

        call_args = mailchimp_client.post.call_args
        payload = call_args[1]["json_data"]
        # Empty tags list is falsy, so not included in payload
        assert "tags" not in payload

    @pytest.mark.asyncio
    async def test_special_characters_in_email(
        self, mailchimp_client, mock_api_response
    ):
        """Verify special characters in email are handled."""
        mailchimp_client.get = AsyncMock(
            return_value=mock_api_response(data={})
        )

        # Should not raise
        await mailchimp_client.get_member("abc123def4", "user+tag@example.com")
