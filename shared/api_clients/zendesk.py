"""
Zendesk API Client for AGNTCY Multi-Agent Customer Service Platform

Provides async HTTP client for Zendesk Support API integration.

Phase 1-3: Mock API (http://localhost:8002)
Phase 4-5: Real Zendesk API (https://{subdomain}.zendesk.com/api/v2)

Features:
- Ticket creation, retrieval, and updates
- Comment/conversation management
- User profile access
- Full authentication support for production

API Reference: https://developer.zendesk.com/api-reference/ticketing/
Rate Limits: 700 req/min (Team), 2,500 req/min (Enterprise)
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseAPIClient, APIClientConfig, AuthType

logger = logging.getLogger(__name__)

# Singleton instance
_client_instance: Optional["ZendeskClient"] = None


class ZendeskClient(BaseAPIClient):
    """
    Async HTTP client for Zendesk Support API.

    Supports both mock (Phase 1-3) and real API (Phase 4-5) modes.

    Usage:
        client = await get_zendesk_client()
        ticket = await client.get_ticket("12345")
        await client.add_comment("12345", "Thank you for your patience!")
    """

    @property
    def service_name(self) -> str:
        return "zendesk"

    def _default_config(self) -> APIClientConfig:
        """Create default config from environment."""
        use_real = os.getenv("USE_REAL_APIS", "false").lower() == "true"

        if use_real and os.getenv("ZENDESK_SUBDOMAIN"):
            # Real Zendesk API
            subdomain = os.getenv("ZENDESK_SUBDOMAIN", "")
            base_url = f"https://{subdomain}.zendesk.com/api/v2"

            return APIClientConfig(
                base_url=base_url,
                auth_type=AuthType.BASIC_AUTH,
                api_key=f"{os.getenv('ZENDESK_EMAIL', '')}/token",
                api_secret=os.getenv("ZENDESK_API_TOKEN"),
                rate_limit_per_second=10.0,  # ~600/min conservative
            )
        else:
            # Mock API
            return APIClientConfig(
                base_url=os.getenv("MOCK_ZENDESK_URL", "http://localhost:8002"),
                auth_type=AuthType.NONE,
                rate_limit_per_second=0,
            )

    # =========================================================================
    # TICKET METHODS
    # =========================================================================

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Get ticket by ID.

        Args:
            ticket_id: Ticket ID

        Returns:
            Ticket data dict or None

        API: GET /api/v2/tickets/{ticket_id}.json
        """
        response = await self.get(f"/tickets/{ticket_id}.json")

        if response.success and response.data:
            return response.data.get("ticket")
        elif response.is_not_found:
            self.logger.debug(f"Ticket {ticket_id} not found")
            return None
        else:
            self.logger.warning(f"Error fetching ticket {ticket_id}: {response.error}")
            return None

    async def list_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        requester_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> Dict[str, Any]:
        """
        List tickets with optional filters.

        Args:
            status: Filter by status (new, open, pending, hold, solved, closed)
            priority: Filter by priority (low, normal, high, urgent)
            assignee_id: Filter by assignee
            requester_id: Filter by requester
            page: Page number
            per_page: Results per page (max 100)

        Returns:
            Dict with 'tickets' list and pagination info

        API: GET /api/v2/tickets.json
        """
        params = {
            "page": page,
            "per_page": min(per_page, 100),
        }
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        if assignee_id:
            params["assignee_id"] = assignee_id
        if requester_id:
            params["requester_id"] = requester_id

        response = await self.get("/tickets.json", params=params)

        if response.success and response.data:
            return {
                "tickets": response.data.get("tickets", []),
                "count": response.data.get("count", 0),
                "next_page": response.data.get("next_page"),
                "previous_page": response.data.get("previous_page"),
            }
        return {"tickets": [], "count": 0}

    async def create_ticket(
        self,
        subject: str,
        description: str,
        requester_email: str,
        priority: str = "normal",
        tags: Optional[List[str]] = None,
        custom_fields: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new support ticket.

        Args:
            subject: Ticket subject
            description: Ticket body/description
            requester_email: Requester's email address
            priority: Priority level (low, normal, high, urgent)
            tags: Optional list of tags
            custom_fields: Optional custom field values

        Returns:
            Created ticket data or None on failure

        API: POST /api/v2/tickets.json
        """
        ticket_data = {
            "ticket": {
                "subject": subject,
                "comment": {"body": description},
                "requester": {"email": requester_email},
                "priority": priority,
            }
        }

        if tags:
            ticket_data["ticket"]["tags"] = tags
        if custom_fields:
            ticket_data["ticket"]["custom_fields"] = custom_fields

        response = await self.post("/tickets.json", json_data=ticket_data)

        if response.success and response.data:
            ticket = response.data.get("ticket")
            self.logger.info(f"Created ticket {ticket.get('id')}: {subject}")
            return ticket
        else:
            self.logger.error(f"Failed to create ticket: {response.error}")
            return None

    async def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        comment: Optional[str] = None,
        public: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing ticket.

        Args:
            ticket_id: Ticket ID to update
            status: New status (open, pending, hold, solved, closed)
            priority: New priority
            assignee_id: Assign to user ID
            tags: Replace tags
            comment: Add a comment
            public: Whether comment is public (default True)

        Returns:
            Updated ticket data or None

        API: PUT /api/v2/tickets/{ticket_id}.json
        """
        ticket_data: Dict[str, Any] = {"ticket": {}}

        if status:
            ticket_data["ticket"]["status"] = status
        if priority:
            ticket_data["ticket"]["priority"] = priority
        if assignee_id:
            ticket_data["ticket"]["assignee_id"] = assignee_id
        if tags is not None:
            ticket_data["ticket"]["tags"] = tags
        if comment:
            ticket_data["ticket"]["comment"] = {
                "body": comment,
                "public": public,
            }

        response = await self.put(f"/tickets/{ticket_id}.json", json_data=ticket_data)

        if response.success and response.data:
            return response.data.get("ticket")
        else:
            self.logger.error(f"Failed to update ticket {ticket_id}: {response.error}")
            return None

    async def close_ticket(self, ticket_id: str, comment: Optional[str] = None) -> bool:
        """
        Close a ticket with optional closing comment.

        Args:
            ticket_id: Ticket ID
            comment: Optional closing comment

        Returns:
            True if successful

        API: PUT /api/v2/tickets/{ticket_id}.json
        """
        result = await self.update_ticket(
            ticket_id,
            status="solved",
            comment=comment or "Ticket resolved.",
        )
        return result is not None

    # =========================================================================
    # COMMENT METHODS
    # =========================================================================

    async def get_comments(self, ticket_id: str) -> List[Dict[str, Any]]:
        """
        Get all comments on a ticket.

        Args:
            ticket_id: Ticket ID

        Returns:
            List of comment dicts

        API: GET /api/v2/tickets/{ticket_id}/comments.json
        """
        response = await self.get(f"/tickets/{ticket_id}/comments.json")

        if response.success and response.data:
            return response.data.get("comments", [])
        return []

    async def add_comment(
        self,
        ticket_id: str,
        body: str,
        public: bool = True,
        author_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Add a comment to a ticket.

        Args:
            ticket_id: Ticket ID
            body: Comment text
            public: Public (customer visible) or internal note
            author_id: Author user ID (optional)

        Returns:
            Created comment data or None

        API: POST /api/v2/tickets/{ticket_id}/comments.json
        """
        comment_data = {
            "comment": {
                "body": body,
                "public": public,
            }
        }
        if author_id:
            comment_data["comment"]["author_id"] = author_id

        # Zendesk uses ticket update to add comments
        response = await self.put(
            f"/tickets/{ticket_id}.json",
            json_data={"ticket": {"comment": comment_data["comment"]}},
        )

        if response.success:
            self.logger.info(f"Added comment to ticket {ticket_id}")
            return response.data
        else:
            self.logger.error(f"Failed to add comment: {response.error}")
            return None

    # =========================================================================
    # USER METHODS
    # =========================================================================

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User data dict or None

        API: GET /api/v2/users/{user_id}.json
        """
        response = await self.get(f"/users/{user_id}.json")

        if response.success and response.data:
            return response.data.get("user")
        return None

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """
        Search users by email or name.

        Args:
            query: Search query (email, name)

        Returns:
            List of matching user dicts

        API: GET /api/v2/users/search.json?query={query}
        """
        response = await self.get("/users/search.json", params={"query": query})

        if response.success and response.data:
            return response.data.get("users", [])
        return []

    async def get_user_tickets(
        self, user_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tickets for a specific user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            List of ticket dicts

        API: GET /api/v2/users/{user_id}/tickets/requested.json
        """
        params = {}
        if status:
            params["status"] = status

        response = await self.get(
            f"/users/{user_id}/tickets/requested.json", params=params
        )

        if response.success and response.data:
            return response.data.get("tickets", [])
        return []

    # =========================================================================
    # SEARCH METHODS
    # =========================================================================

    async def search_tickets(
        self,
        query: str,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """
        Search tickets using Zendesk query language.

        Args:
            query: Zendesk search query (e.g., "status:open type:ticket")
            sort_by: Sort field (created_at, updated_at, priority, status)
            sort_order: Sort direction (asc, desc)

        Returns:
            List of matching ticket dicts

        API: GET /api/v2/search.json?query={query}
        Reference: https://support.zendesk.com/hc/en-us/articles/203663226
        """
        params = {
            "query": f"type:ticket {query}",
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

        response = await self.get("/search.json", params=params)

        if response.success and response.data:
            return response.data.get("results", [])
        return []

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    async def health_check(self) -> bool:
        """Check if Zendesk API is reachable."""
        # Try to get current user as health check
        response = await self.get("/users/me.json")
        if response.success:
            return True

        # Fall back to /health for mock API
        response = await self.get("/health")
        return response.success


async def get_zendesk_client() -> ZendeskClient:
    """
    Get singleton Zendesk client instance.

    Returns:
        ZendeskClient instance (reused across calls)
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = ZendeskClient()
    return _client_instance


async def shutdown_zendesk_client():
    """Shutdown the singleton client."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
