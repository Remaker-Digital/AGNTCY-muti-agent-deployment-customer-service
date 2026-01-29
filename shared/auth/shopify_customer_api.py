# ============================================================================
# Shopify Customer Accounts API Client - Phase 6
# ============================================================================
# Purpose: OAuth 2.0 integration with Shopify Customer Accounts API
#
# Shopify Customer Accounts API provides:
# - Customer authentication via Shopify's hosted login
# - Access to customer profile, addresses, and order history
# - Token-based session management with refresh support
#
# OAuth Flow (Authorization Code + PKCE):
# 1. Generate authorization URL with state and code_verifier
# 2. Customer logs in via Shopify's hosted login page
# 3. Shopify redirects back with authorization code
# 4. Exchange code for access_token and refresh_token
# 5. Use access_token to call Customer API endpoints
#
# API Reference:
# - https://shopify.dev/docs/api/customer
# - https://shopify.dev/docs/api/customer#authentication
#
# Phase Assignment:
# - Phase 1-5: Mock API (http://localhost:8010)
# - Phase 6+: Real Shopify Customer Accounts API
#
# Budget Impact: $0 (Customer Accounts API is free with Shopify plan)
# ============================================================================

import os
import base64
import hashlib
import secrets
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

from shared.api_clients.base import BaseAPIClient, APIClientConfig, AuthType, APIResponse
from .models import ShopifyCustomer, SessionToken

logger = logging.getLogger(__name__)

# Singleton instance
_client_instance: Optional["ShopifyCustomerAccountsClient"] = None


@dataclass
class PKCEChallenge:
    """
    PKCE (Proof Key for Code Exchange) challenge for OAuth security.

    PKCE prevents authorization code interception attacks by requiring
    the client to prove it initiated the authorization request.

    Flow:
    1. Generate code_verifier (random 43-128 character string)
    2. Create code_challenge = BASE64URL(SHA256(code_verifier))
    3. Send code_challenge with authorization request
    4. Send code_verifier with token exchange request
    5. Server verifies SHA256(code_verifier) == code_challenge

    Security: code_verifier is never transmitted until token exchange,
    preventing attackers who intercept the callback from getting tokens.
    """

    code_verifier: str
    code_challenge: str
    code_challenge_method: str = "S256"

    @classmethod
    def generate(cls) -> "PKCEChallenge":
        """Generate a new PKCE challenge pair."""
        # Generate cryptographically secure random verifier (43-128 chars)
        code_verifier = secrets.token_urlsafe(32)

        # Create S256 challenge: BASE64URL(SHA256(verifier))
        verifier_bytes = code_verifier.encode("ascii")
        challenge_hash = hashlib.sha256(verifier_bytes).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_hash).decode("ascii").rstrip("=")

        return cls(
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )


class ShopifyCustomerAccountsClient(BaseAPIClient):
    """
    Async HTTP client for Shopify Customer Accounts API.

    Provides OAuth 2.0 authentication and customer profile access.

    Supports both mock (Phase 1-5) and real API (Phase 6+) modes.

    OAuth Scopes Requested:
    - openid: OpenID Connect ID token
    - customer-account-api:full: Full customer account access

    Usage:
        client = await get_shopify_customer_client()

        # Generate login URL
        auth_url, state, pkce = await client.get_authorization_url(redirect_uri)

        # After customer logs in and is redirected back
        tokens = await client.exchange_code(code, redirect_uri, pkce.code_verifier)

        # Get customer profile
        customer = await client.get_customer_profile(tokens.access_token)

    API Reference: https://shopify.dev/docs/api/customer
    """

    # Shopify Customer Accounts API version
    API_VERSION = "2024-01"

    @property
    def service_name(self) -> str:
        return "shopify-customer"

    def _default_config(self) -> APIClientConfig:
        """Create default config from environment."""
        use_real = os.getenv("USE_REAL_APIS", "false").lower() == "true"

        if use_real and os.getenv("SHOPIFY_STORE_DOMAIN"):
            # Real Shopify Customer Accounts API
            store_domain = os.getenv("SHOPIFY_STORE_DOMAIN", "")

            # Customer Accounts API uses a different endpoint than Admin API
            # Format: https://{shop}.myshopify.com/account
            base_url = f"https://{store_domain}/account"

            return APIClientConfig(
                base_url=base_url,
                auth_type=AuthType.BEARER_TOKEN,
                api_key=os.getenv("SHOPIFY_CUSTOMER_CLIENT_ID"),
                api_secret=os.getenv("SHOPIFY_CUSTOMER_CLIENT_SECRET"),
                rate_limit_per_second=4.0,  # Customer API has higher limits
            )
        else:
            # Mock API for development/testing
            return APIClientConfig(
                base_url=os.getenv("MOCK_SHOPIFY_CUSTOMER_URL", "http://localhost:8010"),
                auth_type=AuthType.NONE,
                rate_limit_per_second=0,  # No rate limit for mock
            )

    # =========================================================================
    # OAUTH FLOW
    # =========================================================================

    def get_authorization_url(
        self,
        redirect_uri: str,
        scope: str = "openid customer-account-api:full",
        state: Optional[str] = None,
    ) -> Tuple[str, str, PKCEChallenge]:
        """
        Generate OAuth authorization URL for Shopify login.

        Customers are redirected to this URL to authenticate with Shopify.
        After login, Shopify redirects back to redirect_uri with auth code.

        Args:
            redirect_uri: URL to redirect after login (must be registered)
            scope: OAuth scopes to request
            state: CSRF protection token (generated if not provided)

        Returns:
            Tuple of (authorization_url, state, pkce_challenge)

        Usage:
            auth_url, state, pkce = client.get_authorization_url(
                redirect_uri="https://myapp.com/auth/callback"
            )
            # Store state and pkce.code_verifier in session
            # Redirect customer to auth_url
        """
        # Generate PKCE challenge
        pkce = PKCEChallenge.generate()

        # Generate state for CSRF protection
        if state is None:
            state = secrets.token_urlsafe(32)

        # Build authorization URL
        client_id = self.config.api_key or os.getenv("SHOPIFY_CUSTOMER_CLIENT_ID", "")

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
            "code_challenge": pkce.code_challenge,
            "code_challenge_method": pkce.code_challenge_method,
        }

        # For mock API, use different endpoint
        if "localhost" in self.config.base_url:
            auth_endpoint = f"{self.config.base_url}/authorize"
        else:
            # Real Shopify uses account.shopify.com for OAuth
            store_domain = os.getenv("SHOPIFY_STORE_DOMAIN", "")
            auth_endpoint = f"https://shopify.com/{store_domain}/auth/oauth/authorize"

        auth_url = f"{auth_endpoint}?{urlencode(params)}"

        logger.info(f"Generated authorization URL for state={state[:8]}...")
        return auth_url, state, pkce

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> Optional[SessionToken]:
        """
        Exchange authorization code for access tokens.

        Called after customer completes Shopify login and is redirected back.

        Args:
            code: Authorization code from Shopify callback
            redirect_uri: Same redirect_uri used in authorization request
            code_verifier: PKCE code_verifier from get_authorization_url()

        Returns:
            SessionToken with access_token and refresh_token, or None on error

        Security:
        - code_verifier proves we initiated the auth request (PKCE)
        - client_secret provides additional app-level auth
        """
        client_id = self.config.api_key or os.getenv("SHOPIFY_CUSTOMER_CLIENT_ID", "")
        client_secret = self.config.api_secret or os.getenv("SHOPIFY_CUSTOMER_CLIENT_SECRET", "")

        # Token exchange endpoint
        if "localhost" in self.config.base_url:
            token_endpoint = "/token"
        else:
            token_endpoint = "/auth/oauth/token"

        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }

        response = await self.post(token_endpoint, json_data=payload)

        if not response.success:
            logger.error(f"Token exchange failed: {response.error}")
            return None

        data = response.data
        if not data:
            logger.error("Token exchange returned empty response")
            return None

        # Calculate expiry timestamp
        expires_in = data.get("expires_in", 3600)
        from datetime import datetime, timedelta
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + "Z"

        token = SessionToken(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope", ""),
            id_token=data.get("id_token"),
        )

        logger.info("Token exchange successful")
        return token

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> Optional[SessionToken]:
        """
        Refresh expired access token using refresh token.

        Called when access_token expires but refresh_token is still valid.
        Shopify refresh tokens are valid for 14 days.

        Args:
            refresh_token: Refresh token from previous token exchange

        Returns:
            New SessionToken with fresh access_token, or None on error
        """
        client_id = self.config.api_key or os.getenv("SHOPIFY_CUSTOMER_CLIENT_ID", "")
        client_secret = self.config.api_secret or os.getenv("SHOPIFY_CUSTOMER_CLIENT_SECRET", "")

        # Token refresh endpoint
        if "localhost" in self.config.base_url:
            token_endpoint = "/token"
        else:
            token_endpoint = "/auth/oauth/token"

        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }

        response = await self.post(token_endpoint, json_data=payload)

        if not response.success:
            logger.error(f"Token refresh failed: {response.error}")
            return None

        data = response.data
        if not data:
            logger.error("Token refresh returned empty response")
            return None

        # Calculate expiry timestamp
        expires_in = data.get("expires_in", 3600)
        from datetime import datetime, timedelta
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + "Z"

        token = SessionToken(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", refresh_token),  # May be same
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope", ""),
            id_token=data.get("id_token"),
        )

        logger.info("Token refresh successful")
        return token

    # =========================================================================
    # CUSTOMER PROFILE
    # =========================================================================

    async def get_customer_profile(
        self,
        access_token: str,
    ) -> Optional[ShopifyCustomer]:
        """
        Get authenticated customer's profile.

        Retrieves customer data from Shopify Customer Accounts API.

        Args:
            access_token: Valid OAuth access token

        Returns:
            ShopifyCustomer with profile data, or None on error

        API: GET /customer with Bearer token
        """
        # Customer API endpoint
        if "localhost" in self.config.base_url:
            endpoint = "/customer"
        else:
            endpoint = f"/account/customer/api/{self.API_VERSION}/graphql"

        # For real API, use GraphQL query
        if "localhost" not in self.config.base_url:
            return await self._get_customer_profile_graphql(access_token)

        # Mock API uses REST
        response = await self.get(
            endpoint,
            extra_headers={"Authorization": f"Bearer {access_token}"},
        )

        if not response.success:
            logger.error(f"Failed to get customer profile: {response.error}")
            return None

        data = response.data
        if not data:
            return None

        customer = ShopifyCustomer(
            id=data.get("id", ""),
            email=data.get("email", ""),
            first_name=data.get("firstName", data.get("first_name", "")),
            last_name=data.get("lastName", data.get("last_name", "")),
            phone=data.get("phone"),
            accepts_marketing=data.get("acceptsMarketing", data.get("accepts_marketing", False)),
            created_at=data.get("createdAt", data.get("created_at", "")),
            orders_count=data.get("ordersCount", data.get("orders_count", 0)),
            total_spent=data.get("totalSpent", data.get("total_spent", "0.00")),
            default_address=data.get("defaultAddress", data.get("default_address")),
            tags=data.get("tags", []),
        )

        logger.info(f"Retrieved profile for customer {customer.id}")
        return customer

    async def _get_customer_profile_graphql(
        self,
        access_token: str,
    ) -> Optional[ShopifyCustomer]:
        """
        Get customer profile using GraphQL API (real Shopify).

        Shopify Customer Accounts API uses GraphQL for data access.
        """
        query = """
        query {
            customer {
                id
                email
                firstName
                lastName
                phone
                acceptsMarketing
                createdAt
                orders(first: 1) {
                    totalCount
                }
                defaultAddress {
                    address1
                    address2
                    city
                    province
                    country
                    zip
                }
            }
        }
        """

        endpoint = f"/account/customer/api/{self.API_VERSION}/graphql"

        response = await self.post(
            endpoint,
            json_data={"query": query},
            extra_headers={"Authorization": f"Bearer {access_token}"},
        )

        if not response.success:
            logger.error(f"GraphQL customer query failed: {response.error}")
            return None

        data = response.data
        if not data or "data" not in data:
            return None

        customer_data = data["data"].get("customer", {})

        customer = ShopifyCustomer(
            id=customer_data.get("id", ""),
            email=customer_data.get("email", ""),
            first_name=customer_data.get("firstName", ""),
            last_name=customer_data.get("lastName", ""),
            phone=customer_data.get("phone"),
            accepts_marketing=customer_data.get("acceptsMarketing", False),
            created_at=customer_data.get("createdAt", ""),
            orders_count=customer_data.get("orders", {}).get("totalCount", 0),
            default_address=customer_data.get("defaultAddress"),
        )

        logger.info(f"Retrieved profile for customer {customer.id}")
        return customer

    # =========================================================================
    # CUSTOMER ORDERS
    # =========================================================================

    async def get_customer_orders(
        self,
        access_token: str,
        limit: int = 10,
    ) -> list:
        """
        Get authenticated customer's orders.

        Args:
            access_token: Valid OAuth access token
            limit: Maximum orders to return

        Returns:
            List of order dicts

        API: Customer Accounts API - orders query
        """
        if "localhost" in self.config.base_url:
            # Mock API
            response = await self.get(
                "/customer/orders",
                params={"limit": limit},
                extra_headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.success and response.data:
                return response.data.get("orders", [])
            return []

        # Real API uses GraphQL
        query = f"""
        query {{
            customer {{
                orders(first: {limit}) {{
                    edges {{
                        node {{
                            id
                            name
                            processedAt
                            fulfillmentStatus
                            financialStatus
                            totalPrice {{
                                amount
                                currencyCode
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """

        endpoint = f"/account/customer/api/{self.API_VERSION}/graphql"

        response = await self.post(
            endpoint,
            json_data={"query": query},
            extra_headers={"Authorization": f"Bearer {access_token}"},
        )

        if not response.success:
            logger.error(f"Orders query failed: {response.error}")
            return []

        data = response.data
        if not data or "data" not in data:
            return []

        orders_data = data["data"].get("customer", {}).get("orders", {}).get("edges", [])
        return [edge["node"] for edge in orders_data]

    # =========================================================================
    # LOGOUT / REVOKE
    # =========================================================================

    async def revoke_token(
        self,
        access_token: str,
    ) -> bool:
        """
        Revoke OAuth token (logout).

        Invalidates the access token so it cannot be used again.

        Args:
            access_token: Token to revoke

        Returns:
            True if revocation successful
        """
        if "localhost" in self.config.base_url:
            # Mock API
            response = await self.post(
                "/revoke",
                json_data={"token": access_token},
            )
            return response.success

        # Real Shopify token revocation
        client_id = self.config.api_key or os.getenv("SHOPIFY_CUSTOMER_CLIENT_ID", "")

        response = await self.post(
            "/auth/oauth/revoke",
            json_data={
                "client_id": client_id,
                "token": access_token,
            },
        )

        return response.success

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    async def health_check(self) -> bool:
        """Check if Shopify Customer Accounts API is reachable."""
        if "localhost" in self.config.base_url:
            response = await self.get("/health")
            return response.success

        # Real API - try to reach the authorize endpoint
        # (doesn't require auth, just checks connectivity)
        try:
            response = await self.get("/auth/oauth/authorize")
            # 400 is expected without params, but proves connectivity
            return response.status_code in (200, 302, 400)
        except Exception:
            return False


async def get_shopify_customer_client() -> ShopifyCustomerAccountsClient:
    """
    Get singleton Shopify Customer Accounts client instance.

    Returns:
        ShopifyCustomerAccountsClient instance (reused across calls)
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = ShopifyCustomerAccountsClient()
    return _client_instance


async def shutdown_shopify_customer_client():
    """Shutdown the singleton client."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
