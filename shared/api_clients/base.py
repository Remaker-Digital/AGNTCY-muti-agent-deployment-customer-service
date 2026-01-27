"""
Base API Client for AGNTCY Multi-Agent Customer Service Platform

Provides common functionality for all external API integrations:
- Authentication handling (API keys, tokens, OAuth)
- Retry logic with exponential backoff
- Rate limiting compliance
- Request/response logging (with PII protection)
- Error handling and graceful degradation

Phase 1-3: Mock API endpoints (http://localhost:800X)
Phase 4-5: Real API endpoints with Azure Key Vault credentials
"""

import os
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class AuthType(Enum):
    """Authentication types supported by API clients."""
    NONE = "none"  # Mock APIs (Phase 1-3)
    API_KEY = "api_key"  # Header-based API key
    BEARER_TOKEN = "bearer_token"  # Authorization: Bearer
    BASIC_AUTH = "basic_auth"  # Authorization: Basic
    OAUTH2 = "oauth2"  # OAuth 2.0 service account


@dataclass
class APIClientConfig:
    """Configuration for API clients."""
    base_url: str
    auth_type: AuthType = AuthType.NONE
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_per_second: float = 2.0

    # Headers
    custom_headers: Dict[str, str] = field(default_factory=dict)

    # Logging
    log_requests: bool = True
    log_responses: bool = True
    mask_pii: bool = True  # Mask PII in logs

    @classmethod
    def from_environment(
        cls,
        service_name: str,
        default_mock_url: str,
        auth_type: AuthType = AuthType.NONE
    ) -> "APIClientConfig":
        """
        Create config from environment variables.

        Supports both mock (Phase 1-3) and real API (Phase 4-5) modes.

        Args:
            service_name: Service name (e.g., "SHOPIFY", "ZENDESK")
            default_mock_url: Default mock API URL (e.g., "http://localhost:8001")
            auth_type: Authentication type for real API

        Environment Variables:
            {SERVICE}_URL: API endpoint URL
            {SERVICE}_API_KEY: API key
            {SERVICE}_API_SECRET: API secret
            {SERVICE}_ACCESS_TOKEN: Access token
            USE_REAL_APIS: Set to "true" to use real APIs
        """
        service_upper = service_name.upper()
        use_real_apis = os.getenv("USE_REAL_APIS", "false").lower() == "true"

        # Get URL (mock or real)
        if use_real_apis:
            base_url = os.getenv(f"{service_upper}_URL", "")
            if not base_url:
                logger.warning(
                    f"{service_upper}_URL not set, falling back to mock: {default_mock_url}"
                )
                base_url = default_mock_url
                auth_type = AuthType.NONE
        else:
            base_url = os.getenv(f"MOCK_{service_upper}_URL", default_mock_url)
            auth_type = AuthType.NONE  # Mock APIs don't need auth

        return cls(
            base_url=base_url,
            auth_type=auth_type if use_real_apis else AuthType.NONE,
            api_key=os.getenv(f"{service_upper}_API_KEY"),
            api_secret=os.getenv(f"{service_upper}_API_SECRET"),
            access_token=os.getenv(f"{service_upper}_ACCESS_TOKEN"),
            timeout=float(os.getenv(f"{service_upper}_TIMEOUT", "10.0")),
            max_retries=int(os.getenv(f"{service_upper}_MAX_RETRIES", "3")),
        )


@dataclass
class APIResponse:
    """Standardized API response wrapper."""
    success: bool
    status_code: int
    data: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    retries: int = 0

    @property
    def is_rate_limited(self) -> bool:
        return self.status_code == 429

    @property
    def is_not_found(self) -> bool:
        return self.status_code == 404

    @property
    def is_auth_error(self) -> bool:
        return self.status_code in (401, 403)


class BaseAPIClient(ABC):
    """
    Abstract base class for all API clients.

    Provides:
    - Unified authentication handling
    - Retry logic with exponential backoff
    - Rate limiting compliance
    - Request/response logging
    - Error handling and graceful degradation

    Subclasses must implement:
    - service_name property
    - Any service-specific methods
    """

    def __init__(self, config: Optional[APIClientConfig] = None):
        """
        Initialize API client.

        Args:
            config: Client configuration (auto-created from env if None)
        """
        self.config = config or self._default_config()
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0.0
        self._request_count: int = 0
        self._error_count: int = 0
        self.logger = logging.getLogger(f"{__name__}.{self.service_name}")

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Service name for logging and config."""
        pass

    @abstractmethod
    def _default_config(self) -> APIClientConfig:
        """Create default configuration from environment."""
        pass

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers."""
        if self._client is None:
            headers = self._build_auth_headers()
            headers.update(self.config.custom_headers)
            headers["User-Agent"] = "AGNTCY-CustomerService/1.0"
            headers["Accept"] = "application/json"

            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers=headers,
            )
        return self._client

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build authentication headers based on auth type."""
        headers: Dict[str, str] = {}

        if self.config.auth_type == AuthType.NONE:
            pass  # No auth for mock APIs

        elif self.config.auth_type == AuthType.API_KEY:
            if self.config.api_key:
                # Service-specific header name (override in subclass if needed)
                headers["X-API-Key"] = self.config.api_key

        elif self.config.auth_type == AuthType.BEARER_TOKEN:
            if self.config.access_token:
                headers["Authorization"] = f"Bearer {self.config.access_token}"

        elif self.config.auth_type == AuthType.BASIC_AUTH:
            if self.config.api_key:
                import base64
                credentials = f"{self.config.api_key}:{self.config.api_secret or ''}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"

        return headers

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        if self.config.rate_limit_per_second <= 0:
            return

        min_interval = 1.0 / self.config.rate_limit_per_second
        elapsed = time.monotonic() - self._last_request_time

        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)

        self._last_request_time = time.monotonic()

    def _mask_sensitive_data(self, data: Any) -> Any:
        """Mask PII and sensitive data in logs."""
        if not self.config.mask_pii:
            return data

        if isinstance(data, dict):
            masked = {}
            sensitive_keys = {
                "email", "phone", "address", "name", "customer_email",
                "api_key", "token", "password", "secret", "credit_card"
            }
            for key, value in data.items():
                if any(s in key.lower() for s in sensitive_keys):
                    masked[key] = "***MASKED***"
                elif isinstance(value, (dict, list)):
                    masked[key] = self._mask_sensitive_data(value)
                else:
                    masked[key] = value
            return masked
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        return data

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/orders/123")
            params: URL query parameters
            json_data: JSON request body
            extra_headers: Additional headers for this request

        Returns:
            APIResponse with success status, data or error
        """
        url = f"{self.config.base_url.rstrip('/')}{endpoint}"
        retries = 0
        last_error = None

        while retries <= self.config.max_retries:
            try:
                # Enforce rate limiting
                await self._rate_limit()

                # Get client and make request
                client = await self._get_client()

                # Add extra headers if provided
                headers = dict(extra_headers) if extra_headers else {}

                start_time = time.monotonic()

                if self.config.log_requests:
                    self.logger.debug(
                        f"{method} {url} params={self._mask_sensitive_data(params)} "
                        f"body={self._mask_sensitive_data(json_data)}"
                    )

                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=headers,
                )

                latency_ms = (time.monotonic() - start_time) * 1000
                self._request_count += 1

                # Handle response
                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    self.logger.warning(
                        f"Rate limited by {self.service_name}, waiting {retry_after}s"
                    )
                    await asyncio.sleep(retry_after)
                    retries += 1
                    continue

                # Parse response
                try:
                    data = response.json() if response.content else None
                except Exception:
                    data = response.text

                if self.config.log_responses:
                    self.logger.debug(
                        f"Response {response.status_code} ({latency_ms:.1f}ms): "
                        f"{self._mask_sensitive_data(data)}"
                    )

                if response.status_code >= 400:
                    self._error_count += 1
                    return APIResponse(
                        success=False,
                        status_code=response.status_code,
                        data=data,
                        error=f"HTTP {response.status_code}: {data}",
                        latency_ms=latency_ms,
                        retries=retries,
                    )

                return APIResponse(
                    success=True,
                    status_code=response.status_code,
                    data=data,
                    latency_ms=latency_ms,
                    retries=retries,
                )

            except httpx.TimeoutException as e:
                last_error = f"Request timeout: {e}"
                self.logger.warning(f"{self.service_name} timeout (attempt {retries + 1})")

            except httpx.HTTPError as e:
                last_error = f"HTTP error: {e}"
                self.logger.warning(f"{self.service_name} HTTP error: {e}")

            except Exception as e:
                last_error = f"Unexpected error: {e}"
                self.logger.error(f"{self.service_name} error: {e}", exc_info=True)

            # Exponential backoff
            if retries < self.config.max_retries:
                delay = self.config.retry_delay * (2 ** retries)
                self.logger.debug(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

            retries += 1

        self._error_count += 1
        return APIResponse(
            success=False,
            status_code=0,
            error=last_error or "Max retries exceeded",
            retries=retries - 1,
        )

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """Make GET request."""
        return await self._request("GET", endpoint, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """Make POST request."""
        return await self._request("POST", endpoint, json_data=json_data, **kwargs)

    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> APIResponse:
        """Make PUT request."""
        return await self._request("PUT", endpoint, json_data=json_data, **kwargs)

    async def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> APIResponse:
        """Make DELETE request."""
        return await self._request("DELETE", endpoint, **kwargs)

    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics for monitoring."""
        return {
            "service": self.service_name,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._request_count, 1),
            "base_url": self.config.base_url,
            "auth_type": self.config.auth_type.value,
        }

    async def close(self):
        """Close HTTP client and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """Check if the API is reachable."""
        try:
            response = await self.get("/health")
            return response.success
        except Exception:
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
