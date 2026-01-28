"""
Mailchimp API Client for AGNTCY Multi-Agent Customer Service Platform

Provides async HTTP client for Mailchimp Marketing API integration.

Phase 1-3: Mock API (http://localhost:8003)
Phase 4-5: Real Mailchimp API (https://{dc}.api.mailchimp.com/3.0)

Features:
- Audience/list management
- Campaign retrieval and status
- Member subscription management
- Automation workflow access

API Reference: https://mailchimp.com/developer/marketing/api/
Rate Limits: 10 concurrent connections, 10 req/sec
"""

import os
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAPIClient, APIClientConfig, AuthType

logger = logging.getLogger(__name__)

# Singleton instance
_client_instance: Optional["MailchimpClient"] = None


class MailchimpClient(BaseAPIClient):
    """
    Async HTTP client for Mailchimp Marketing API.

    Supports both mock (Phase 1-3) and real API (Phase 4-5) modes.

    Usage:
        client = await get_mailchimp_client()
        lists = await client.get_lists()
        await client.subscribe_member("list_id", "email@example.com")
    """

    @property
    def service_name(self) -> str:
        return "mailchimp"

    def _default_config(self) -> APIClientConfig:
        """Create default config from environment."""
        use_real = os.getenv("USE_REAL_APIS", "false").lower() == "true"

        if use_real and os.getenv("MAILCHIMP_API_KEY"):
            # Real Mailchimp API
            api_key = os.getenv("MAILCHIMP_API_KEY", "")
            # Extract datacenter from API key (format: key-dc)
            dc = api_key.split("-")[-1] if "-" in api_key else "us1"
            base_url = f"https://{dc}.api.mailchimp.com/3.0"

            return APIClientConfig(
                base_url=base_url,
                auth_type=AuthType.BASIC_AUTH,
                api_key="anystring",  # Mailchimp uses any string as username
                api_secret=api_key,
                rate_limit_per_second=10.0,
            )
        else:
            # Mock API
            return APIClientConfig(
                base_url=os.getenv("MOCK_MAILCHIMP_URL", "http://localhost:8003"),
                auth_type=AuthType.NONE,
                rate_limit_per_second=0,
            )

    # =========================================================================
    # LIST/AUDIENCE METHODS
    # =========================================================================

    async def get_lists(self, offset: int = 0, count: int = 10) -> Dict[str, Any]:
        """
        Get all audiences/lists.

        Args:
            offset: Pagination offset
            count: Number of lists to return (max 1000)

        Returns:
            Dict with 'lists' and pagination info

        API: GET /3.0/lists
        """
        params = {
            "offset": offset,
            "count": min(count, 1000),
        }

        response = await self.get("/lists", params=params)

        if response.success and response.data:
            return {
                "lists": response.data.get("lists", []),
                "total_items": response.data.get("total_items", 0),
            }
        return {"lists": [], "total_items": 0}

    async def get_list(self, list_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific audience/list.

        Args:
            list_id: List ID

        Returns:
            List data dict or None

        API: GET /3.0/lists/{list_id}
        """
        response = await self.get(f"/lists/{list_id}")

        if response.success and response.data:
            return response.data
        elif response.is_not_found:
            self.logger.debug(f"List {list_id} not found")
            return None
        return None

    async def get_list_stats(self, list_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a list.

        Args:
            list_id: List ID

        Returns:
            Stats dict with member counts, open rates, etc.

        API: GET /3.0/lists/{list_id}?fields=stats
        """
        response = await self.get(f"/lists/{list_id}", params={"fields": "stats"})

        if response.success and response.data:
            return response.data.get("stats", {})
        return None

    # =========================================================================
    # MEMBER METHODS
    # =========================================================================

    async def get_members(
        self,
        list_id: str,
        status: Optional[str] = None,
        offset: int = 0,
        count: int = 100,
    ) -> Dict[str, Any]:
        """
        Get members of a list.

        Args:
            list_id: List ID
            status: Filter by status (subscribed, unsubscribed, cleaned, pending)
            offset: Pagination offset
            count: Number to return (max 1000)

        Returns:
            Dict with 'members' list

        API: GET /3.0/lists/{list_id}/members
        """
        params = {
            "offset": offset,
            "count": min(count, 1000),
        }
        if status:
            params["status"] = status

        response = await self.get(f"/lists/{list_id}/members", params=params)

        if response.success and response.data:
            return {
                "members": response.data.get("members", []),
                "total_items": response.data.get("total_items", 0),
            }
        return {"members": [], "total_items": 0}

    async def get_member(self, list_id: str, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific member by email.

        Args:
            list_id: List ID
            email: Member email (will be hashed)

        Returns:
            Member data dict or None

        API: GET /3.0/lists/{list_id}/members/{subscriber_hash}
        """
        import hashlib

        subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()

        response = await self.get(f"/lists/{list_id}/members/{subscriber_hash}")

        if response.success and response.data:
            return response.data
        elif response.is_not_found:
            self.logger.debug(f"Member {email} not found in list {list_id}")
            return None
        return None

    async def subscribe_member(
        self,
        list_id: str,
        email: str,
        merge_fields: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        status: str = "subscribed",
    ) -> Optional[Dict[str, Any]]:
        """
        Subscribe a member to a list.

        Args:
            list_id: List ID
            email: Email address
            merge_fields: Custom fields (FNAME, LNAME, etc.)
            tags: Tags to apply
            status: Status (subscribed, pending, unsubscribed)

        Returns:
            Created/updated member data or None

        API: POST /3.0/lists/{list_id}/members
        """
        member_data = {
            "email_address": email,
            "status": status,
        }
        if merge_fields:
            member_data["merge_fields"] = merge_fields
        if tags:
            member_data["tags"] = tags

        response = await self.post(f"/lists/{list_id}/members", json_data=member_data)

        if response.success and response.data:
            self.logger.info(f"Subscribed {email} to list {list_id}")
            return response.data
        else:
            self.logger.error(f"Failed to subscribe {email}: {response.error}")
            return None

    async def update_member(
        self,
        list_id: str,
        email: str,
        merge_fields: Optional[Dict[str, str]] = None,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a member's information.

        Args:
            list_id: List ID
            email: Member email
            merge_fields: Fields to update
            status: New status

        Returns:
            Updated member data or None

        API: PATCH /3.0/lists/{list_id}/members/{subscriber_hash}
        """
        import hashlib

        subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()

        member_data: Dict[str, Any] = {}
        if merge_fields:
            member_data["merge_fields"] = merge_fields
        if status:
            member_data["status"] = status

        response = await self._request(
            "PATCH",
            f"/lists/{list_id}/members/{subscriber_hash}",
            json_data=member_data,
        )

        if response.success and response.data:
            return response.data
        return None

    async def unsubscribe_member(self, list_id: str, email: str) -> bool:
        """
        Unsubscribe a member from a list.

        Args:
            list_id: List ID
            email: Member email

        Returns:
            True if successful

        API: PATCH /3.0/lists/{list_id}/members/{subscriber_hash}
        """
        result = await self.update_member(list_id, email, status="unsubscribed")
        return result is not None

    # =========================================================================
    # CAMPAIGN METHODS
    # =========================================================================

    async def get_campaigns(
        self,
        status: Optional[str] = None,
        list_id: Optional[str] = None,
        offset: int = 0,
        count: int = 50,
    ) -> Dict[str, Any]:
        """
        Get campaigns with optional filters.

        Args:
            status: Filter by status (save, paused, schedule, sending, sent)
            list_id: Filter by list ID
            offset: Pagination offset
            count: Number to return

        Returns:
            Dict with 'campaigns' list

        API: GET /3.0/campaigns
        """
        params = {
            "offset": offset,
            "count": count,
        }
        if status:
            params["status"] = status
        if list_id:
            params["list_id"] = list_id

        response = await self.get("/campaigns", params=params)

        if response.success and response.data:
            return {
                "campaigns": response.data.get("campaigns", []),
                "total_items": response.data.get("total_items", 0),
            }
        return {"campaigns": [], "total_items": 0}

    async def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            Campaign data dict or None

        API: GET /3.0/campaigns/{campaign_id}
        """
        response = await self.get(f"/campaigns/{campaign_id}")

        if response.success and response.data:
            return response.data
        return None

    async def get_campaign_report(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get campaign performance report.

        Args:
            campaign_id: Campaign ID

        Returns:
            Report with opens, clicks, bounces, etc.

        API: GET /3.0/reports/{campaign_id}
        """
        response = await self.get(f"/reports/{campaign_id}")

        if response.success and response.data:
            return response.data
        return None

    # =========================================================================
    # AUTOMATION METHODS
    # =========================================================================

    async def get_automations(self, offset: int = 0, count: int = 50) -> Dict[str, Any]:
        """
        Get automation workflows.

        Args:
            offset: Pagination offset
            count: Number to return

        Returns:
            Dict with 'automations' list

        API: GET /3.0/automations
        """
        params = {
            "offset": offset,
            "count": count,
        }

        response = await self.get("/automations", params=params)

        if response.success and response.data:
            return {
                "automations": response.data.get("automations", []),
                "total_items": response.data.get("total_items", 0),
            }
        return {"automations": [], "total_items": 0}

    async def get_automation(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific automation workflow.

        Args:
            workflow_id: Automation workflow ID

        Returns:
            Automation data dict or None

        API: GET /3.0/automations/{workflow_id}
        """
        response = await self.get(f"/automations/{workflow_id}")

        if response.success and response.data:
            return response.data
        return None

    # =========================================================================
    # TAG METHODS
    # =========================================================================

    async def add_member_tags(self, list_id: str, email: str, tags: List[str]) -> bool:
        """
        Add tags to a member.

        Args:
            list_id: List ID
            email: Member email
            tags: Tags to add

        Returns:
            True if successful

        API: POST /3.0/lists/{list_id}/members/{subscriber_hash}/tags
        """
        import hashlib

        subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()

        tag_data = {"tags": [{"name": tag, "status": "active"} for tag in tags]}

        response = await self.post(
            f"/lists/{list_id}/members/{subscriber_hash}/tags", json_data=tag_data
        )

        return response.success

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    async def health_check(self) -> bool:
        """Check if Mailchimp API is reachable."""
        # Try to get account info as health check
        response = await self.get("/")
        if response.success:
            return True

        # Fall back to /health for mock API
        response = await self.get("/health")
        return response.success


async def get_mailchimp_client() -> MailchimpClient:
    """
    Get singleton Mailchimp client instance.

    Returns:
        MailchimpClient instance (reused across calls)
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = MailchimpClient()
    return _client_instance


async def shutdown_mailchimp_client():
    """Shutdown the singleton client."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
