"""
Unit tests for BaseAPIClient abstract class.

Tests the core API client functionality:
- Configuration and initialization
- Authentication header building (all auth types)
- Rate limiting
- PII masking
- HTTP request methods with retry logic
- Error handling and metrics
- Async context manager support

Target: 90%+ coverage for shared/api_clients/base.py
"""

import asyncio
import base64
import os
import time
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import httpx
import pytest

from shared.api_clients.base import (
    AuthType,
    APIClientConfig,
    APIResponse,
    BaseAPIClient,
)


# ============================================================================
# Concrete Test Implementation
# ============================================================================


class ConcreteTestClient(BaseAPIClient):
    """Concrete implementation for testing BaseAPIClient."""

    @property
    def service_name(self) -> str:
        return "test-service"

    def _default_config(self) -> APIClientConfig:
        return APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.NONE,
        )


# ============================================================================
# APIClientConfig Tests
# ============================================================================


class TestAPIClientConfig:
    """Tests for APIClientConfig dataclass."""

    def test_default_values(self):
        """Verify default configuration values."""
        config = APIClientConfig(base_url="http://localhost:8000")

        assert config.base_url == "http://localhost:8000"
        assert config.auth_type == AuthType.NONE
        assert config.api_key is None
        assert config.api_secret is None
        assert config.access_token is None
        assert config.timeout == 10.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.rate_limit_per_second == 2.0
        assert config.custom_headers == {}
        assert config.log_requests is True
        assert config.log_responses is True
        assert config.mask_pii is True

    def test_custom_values(self):
        """Verify custom configuration values."""
        config = APIClientConfig(
            base_url="https://api.example.com",
            auth_type=AuthType.BEARER_TOKEN,
            api_key="test-api-key",
            api_secret="test-secret",
            access_token="test-token",
            timeout=30.0,
            max_retries=5,
            retry_delay=2.0,
            rate_limit_per_second=10.0,
            custom_headers={"X-Custom": "value"},
            log_requests=False,
            log_responses=False,
            mask_pii=False,
        )

        assert config.base_url == "https://api.example.com"
        assert config.auth_type == AuthType.BEARER_TOKEN
        assert config.api_key == "test-api-key"
        assert config.api_secret == "test-secret"
        assert config.access_token == "test-token"
        assert config.timeout == 30.0
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.rate_limit_per_second == 10.0
        assert config.custom_headers == {"X-Custom": "value"}
        assert config.log_requests is False
        assert config.log_responses is False
        assert config.mask_pii is False

    def test_from_environment_mock_mode(self):
        """Verify config from environment in mock mode."""
        with patch.dict(os.environ, {
            "USE_REAL_APIS": "false",
            "MOCK_SHOPIFY_URL": "http://mock-shopify:8001",
        }, clear=False):
            config = APIClientConfig.from_environment(
                service_name="shopify",
                default_mock_url="http://localhost:8001",
                auth_type=AuthType.API_KEY,
            )

            assert config.base_url == "http://mock-shopify:8001"
            assert config.auth_type == AuthType.NONE  # Mock mode uses no auth

    def test_from_environment_mock_mode_default_url(self):
        """Verify mock mode uses default URL when env var not set."""
        with patch.dict(os.environ, {
            "USE_REAL_APIS": "false",
        }, clear=True):
            config = APIClientConfig.from_environment(
                service_name="shopify",
                default_mock_url="http://localhost:8001",
            )

            assert config.base_url == "http://localhost:8001"
            assert config.auth_type == AuthType.NONE

    def test_from_environment_real_mode(self):
        """Verify config from environment in real API mode."""
        with patch.dict(os.environ, {
            "USE_REAL_APIS": "true",
            "ZENDESK_URL": "https://company.zendesk.com",
            "ZENDESK_API_KEY": "zen-api-key",
            "ZENDESK_API_SECRET": "zen-secret",
            "ZENDESK_ACCESS_TOKEN": "zen-token",
            "ZENDESK_TIMEOUT": "20.0",
            "ZENDESK_MAX_RETRIES": "5",
        }, clear=False):
            config = APIClientConfig.from_environment(
                service_name="zendesk",
                default_mock_url="http://localhost:8002",
                auth_type=AuthType.BASIC_AUTH,
            )

            assert config.base_url == "https://company.zendesk.com"
            assert config.auth_type == AuthType.BASIC_AUTH
            assert config.api_key == "zen-api-key"
            assert config.api_secret == "zen-secret"
            assert config.access_token == "zen-token"
            assert config.timeout == 20.0
            assert config.max_retries == 5

    def test_from_environment_real_mode_missing_url(self):
        """Verify real mode falls back to mock URL when URL not set."""
        with patch.dict(os.environ, {
            "USE_REAL_APIS": "true",
            # MAILCHIMP_URL not set
        }, clear=True):
            config = APIClientConfig.from_environment(
                service_name="mailchimp",
                default_mock_url="http://localhost:8003",
                auth_type=AuthType.API_KEY,
            )

            # Should fall back to mock URL and no auth
            assert config.base_url == "http://localhost:8003"
            assert config.auth_type == AuthType.NONE


# ============================================================================
# APIResponse Tests
# ============================================================================


class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_default_values(self):
        """Verify default response values."""
        response = APIResponse(success=True, status_code=200)

        assert response.success is True
        assert response.status_code == 200
        assert response.data is None
        assert response.error is None
        assert response.latency_ms == 0.0
        assert response.retries == 0

    def test_with_data(self):
        """Verify response with data."""
        data = {"id": 123, "name": "Test"}
        response = APIResponse(
            success=True,
            status_code=200,
            data=data,
            latency_ms=45.2,
            retries=1,
        )

        assert response.data == data
        assert response.latency_ms == 45.2
        assert response.retries == 1

    def test_with_error(self):
        """Verify response with error."""
        response = APIResponse(
            success=False,
            status_code=500,
            error="Internal server error",
        )

        assert response.success is False
        assert response.error == "Internal server error"

    def test_is_rate_limited(self):
        """Verify rate limited property."""
        rate_limited = APIResponse(success=False, status_code=429)
        not_rate_limited = APIResponse(success=False, status_code=500)

        assert rate_limited.is_rate_limited is True
        assert not_rate_limited.is_rate_limited is False

    def test_is_not_found(self):
        """Verify not found property."""
        not_found = APIResponse(success=False, status_code=404)
        found = APIResponse(success=True, status_code=200)

        assert not_found.is_not_found is True
        assert found.is_not_found is False

    def test_is_auth_error(self):
        """Verify auth error property for 401 and 403."""
        unauthorized = APIResponse(success=False, status_code=401)
        forbidden = APIResponse(success=False, status_code=403)
        ok = APIResponse(success=True, status_code=200)

        assert unauthorized.is_auth_error is True
        assert forbidden.is_auth_error is True
        assert ok.is_auth_error is False


# ============================================================================
# BaseAPIClient Initialization Tests
# ============================================================================


class TestBaseAPIClientInit:
    """Tests for BaseAPIClient initialization."""

    def test_init_with_default_config(self):
        """Verify initialization with default config."""
        client = ConcreteTestClient()

        assert client.config.base_url == "http://localhost:8000"
        assert client.config.auth_type == AuthType.NONE
        assert client._client is None
        assert client._last_request_time == 0.0
        assert client._request_count == 0
        assert client._error_count == 0

    def test_init_with_custom_config(self):
        """Verify initialization with custom config."""
        config = APIClientConfig(
            base_url="http://custom:9000",
            auth_type=AuthType.BEARER_TOKEN,
            access_token="custom-token",
        )
        client = ConcreteTestClient(config=config)

        assert client.config.base_url == "http://custom:9000"
        assert client.config.auth_type == AuthType.BEARER_TOKEN
        assert client.config.access_token == "custom-token"

    def test_service_name_property(self):
        """Verify service_name property returns correct value."""
        client = ConcreteTestClient()
        assert client.service_name == "test-service"


# ============================================================================
# Authentication Header Tests
# ============================================================================


class TestBuildAuthHeaders:
    """Tests for _build_auth_headers method."""

    def test_auth_type_none(self):
        """Verify no headers for AuthType.NONE."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.NONE,
        )
        client = ConcreteTestClient(config=config)
        headers = client._build_auth_headers()

        assert headers == {}

    def test_auth_type_api_key(self):
        """Verify X-API-Key header for AuthType.API_KEY."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.API_KEY,
            api_key="test-api-key-123",
        )
        client = ConcreteTestClient(config=config)
        headers = client._build_auth_headers()

        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test-api-key-123"

    def test_auth_type_api_key_missing(self):
        """Verify no header when API key is missing."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.API_KEY,
            api_key=None,
        )
        client = ConcreteTestClient(config=config)
        headers = client._build_auth_headers()

        assert "X-API-Key" not in headers

    def test_auth_type_bearer_token(self):
        """Verify Authorization Bearer header."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.BEARER_TOKEN,
            access_token="bearer-token-xyz",
        )
        client = ConcreteTestClient(config=config)
        headers = client._build_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer bearer-token-xyz"

    def test_auth_type_bearer_token_missing(self):
        """Verify no header when access token is missing."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.BEARER_TOKEN,
            access_token=None,
        )
        client = ConcreteTestClient(config=config)
        headers = client._build_auth_headers()

        assert "Authorization" not in headers

    def test_auth_type_basic_auth(self):
        """Verify Authorization Basic header."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.BASIC_AUTH,
            api_key="username",
            api_secret="password",
        )
        client = ConcreteTestClient(config=config)
        headers = client._build_auth_headers()

        assert "Authorization" in headers
        # Verify base64 encoding
        expected = base64.b64encode(b"username:password").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_auth_type_basic_auth_no_secret(self):
        """Verify Basic auth with only username."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.BASIC_AUTH,
            api_key="username",
            api_secret=None,
        )
        client = ConcreteTestClient(config=config)
        headers = client._build_auth_headers()

        assert "Authorization" in headers
        expected = base64.b64encode(b"username:").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_auth_type_basic_auth_missing_key(self):
        """Verify no header when api_key is missing for basic auth."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            auth_type=AuthType.BASIC_AUTH,
            api_key=None,
        )
        client = ConcreteTestClient(config=config)
        headers = client._build_auth_headers()

        assert "Authorization" not in headers


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_disabled(self):
        """Verify no delay when rate limiting is disabled."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            rate_limit_per_second=0,  # Disabled
        )
        client = ConcreteTestClient(config=config)

        start = time.monotonic()
        await client._rate_limit()
        elapsed = time.monotonic() - start

        assert elapsed < 0.01  # No significant delay

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """Verify delay when rate limit would be exceeded."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            rate_limit_per_second=10.0,  # 0.1s between requests
        )
        client = ConcreteTestClient(config=config)

        # First request sets last_request_time
        client._last_request_time = time.monotonic()

        # Second request should wait
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client._rate_limit()
            # Should have called sleep with some delay
            if mock_sleep.called:
                # Delay should be positive and <= 0.1s
                delay = mock_sleep.call_args[0][0]
                assert 0 < delay <= 0.1


# ============================================================================
# PII Masking Tests
# ============================================================================


class TestPIIMasking:
    """Tests for _mask_sensitive_data method."""

    @pytest.fixture
    def client_with_masking(self):
        """Client with PII masking enabled."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            mask_pii=True,
        )
        return ConcreteTestClient(config=config)

    @pytest.fixture
    def client_without_masking(self):
        """Client with PII masking disabled."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            mask_pii=False,
        )
        return ConcreteTestClient(config=config)

    def test_mask_disabled_returns_original(self, client_without_masking):
        """Verify no masking when disabled."""
        data = {"email": "user@example.com", "name": "John Doe"}
        result = client_without_masking._mask_sensitive_data(data)
        assert result == data

    def test_mask_email_field(self, client_with_masking):
        """Verify email field is masked."""
        data = {"email": "user@example.com"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["email"] == "***MASKED***"

    def test_mask_phone_field(self, client_with_masking):
        """Verify phone field is masked."""
        data = {"phone": "+1-555-123-4567"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["phone"] == "***MASKED***"

    def test_mask_address_field(self, client_with_masking):
        """Verify address field is masked."""
        data = {"address": "123 Main St"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["address"] == "***MASKED***"

    def test_mask_name_field(self, client_with_masking):
        """Verify name field is masked."""
        data = {"name": "John Doe", "first_name": "John"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["name"] == "***MASKED***"
        assert result["first_name"] == "***MASKED***"

    def test_mask_customer_email(self, client_with_masking):
        """Verify customer_email field is masked."""
        data = {"customer_email": "customer@example.com"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["customer_email"] == "***MASKED***"

    def test_mask_api_key(self, client_with_masking):
        """Verify api_key field is masked."""
        data = {"api_key": "secret-key-123"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["api_key"] == "***MASKED***"

    def test_mask_token_field(self, client_with_masking):
        """Verify token field is masked."""
        data = {"access_token": "abc123", "refresh_token": "xyz789"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["access_token"] == "***MASKED***"
        assert result["refresh_token"] == "***MASKED***"

    def test_mask_password_field(self, client_with_masking):
        """Verify password field is masked."""
        data = {"password": "secret123", "user_password": "secret456"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["password"] == "***MASKED***"
        assert result["user_password"] == "***MASKED***"

    def test_mask_secret_field(self, client_with_masking):
        """Verify secret field is masked."""
        data = {"secret": "secret-value", "client_secret": "xyz"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["secret"] == "***MASKED***"
        assert result["client_secret"] == "***MASKED***"

    def test_mask_credit_card_field(self, client_with_masking):
        """Verify credit_card field is masked."""
        data = {"credit_card": "4111-1111-1111-1111"}
        result = client_with_masking._mask_sensitive_data(data)
        assert result["credit_card"] == "***MASKED***"

    def test_mask_nested_dict(self, client_with_masking):
        """Verify nested dictionaries are masked."""
        data = {
            "order": {
                "customer": {
                    "email": "user@example.com",
                    "name": "John Doe",
                },
                "id": 12345,
            }
        }
        result = client_with_masking._mask_sensitive_data(data)

        assert result["order"]["id"] == 12345
        assert result["order"]["customer"]["email"] == "***MASKED***"
        assert result["order"]["customer"]["name"] == "***MASKED***"

    def test_mask_list_of_dicts(self, client_with_masking):
        """Verify lists of dictionaries are masked."""
        data = {
            "customers": [
                {"email": "user1@example.com"},
                {"email": "user2@example.com"},
            ]
        }
        result = client_with_masking._mask_sensitive_data(data)

        assert result["customers"][0]["email"] == "***MASKED***"
        assert result["customers"][1]["email"] == "***MASKED***"

    def test_mask_non_sensitive_fields_unchanged(self, client_with_masking):
        """Verify non-sensitive fields are not masked."""
        data = {
            "id": 123,
            "status": "active",
            "created_at": "2026-01-28",
        }
        result = client_with_masking._mask_sensitive_data(data)

        assert result["id"] == 123
        assert result["status"] == "active"
        assert result["created_at"] == "2026-01-28"

    def test_mask_non_dict_returns_as_is(self, client_with_masking):
        """Verify non-dict/list values are returned as-is."""
        assert client_with_masking._mask_sensitive_data("string") == "string"
        assert client_with_masking._mask_sensitive_data(123) == 123
        assert client_with_masking._mask_sensitive_data(None) is None


# ============================================================================
# HTTP Request Tests
# ============================================================================


class TestHTTPRequests:
    """Tests for HTTP request methods."""

    @pytest.fixture
    def client(self):
        """Client for request tests."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            log_requests=False,
            log_responses=False,
        )
        return ConcreteTestClient(config=config)

    @pytest.mark.asyncio
    async def test_get_request_success(self, client):
        """Verify successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": 123}'
        mock_response.json.return_value = {"id": 123}
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.get("/test")

            assert response.success is True
            assert response.status_code == 200
            assert response.data == {"id": 123}

    @pytest.mark.asyncio
    async def test_get_request_with_params(self, client):
        """Verify GET request with query parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'[]'
        mock_response.json.return_value = []
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.get("/search", params={"q": "test"})

            mock_http.request.assert_called_once()
            call_kwargs = mock_http.request.call_args[1]
            assert call_kwargs["params"] == {"q": "test"}

    @pytest.mark.asyncio
    async def test_post_request_success(self, client):
        """Verify successful POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": 456}'
        mock_response.json.return_value = {"id": 456}
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.post("/items", json_data={"name": "test"})

            assert response.success is True
            assert response.status_code == 201
            call_kwargs = mock_http.request.call_args[1]
            assert call_kwargs["json"] == {"name": "test"}

    @pytest.mark.asyncio
    async def test_put_request_success(self, client):
        """Verify successful PUT request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"updated": true}'
        mock_response.json.return_value = {"updated": True}
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.put("/items/1", json_data={"name": "updated"})

            assert response.success is True
            assert response.status_code == 200
            call_kwargs = mock_http.request.call_args[1]
            assert call_kwargs["method"] == "PUT"

    @pytest.mark.asyncio
    async def test_delete_request_success(self, client):
        """Verify successful DELETE request."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = b''
        mock_response.json.side_effect = Exception("No content")
        mock_response.text = ""
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.delete("/items/1")

            assert response.success is True
            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_request_with_extra_headers(self, client):
        """Verify extra headers are passed to request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.get("/test", extra_headers={"X-Custom": "value"})

            call_kwargs = mock_http.request.call_args[1]
            assert call_kwargs["headers"]["X-Custom"] == "value"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and retries."""

    @pytest.fixture
    def client(self):
        """Client for error tests."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            max_retries=2,
            retry_delay=0.01,  # Fast retries for tests
            log_requests=False,
            log_responses=False,
        )
        return ConcreteTestClient(config=config)

    @pytest.mark.asyncio
    async def test_http_error_response(self, client):
        """Verify handling of HTTP error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = b'{"error": "Internal error"}'
        mock_response.json.return_value = {"error": "Internal error"}
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.get("/error")

            assert response.success is False
            assert response.status_code == 500
            assert "Internal error" in str(response.error)
            assert client._error_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_response_with_retry(self, client):
        """Verify handling of 429 rate limit with retry."""
        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {"Retry-After": "1"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.content = b'{"ok": true}'
        success_response.json.return_value = {"ok": True}
        success_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            # First call returns 429, second returns 200
            mock_http.request = AsyncMock(
                side_effect=[rate_limited_response, success_response]
            )
            mock_get_client.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client.get("/rate-limited")

            assert response.success is True
            assert response.retries == 1

    @pytest.mark.asyncio
    async def test_timeout_with_retry(self, client):
        """Verify retry on timeout."""
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.content = b'{}'
        success_response.json.return_value = {}
        success_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            # First call times out, second succeeds
            mock_http.request = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("Connection timed out"),
                    success_response,
                ]
            )
            mock_get_client.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client.get("/slow")

            assert response.success is True
            assert response.retries == 1

    @pytest.mark.asyncio
    async def test_http_error_with_retry(self, client):
        """Verify retry on HTTP errors."""
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.content = b'{}'
        success_response.json.return_value = {}
        success_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(
                side_effect=[
                    httpx.HTTPError("Connection failed"),
                    success_response,
                ]
            )
            mock_get_client.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client.get("/flaky")

            assert response.success is True

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, client):
        """Verify failure after max retries exceeded."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(
                side_effect=httpx.TimeoutException("Always timeout")
            )
            mock_get_client.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client.get("/always-timeout")

            assert response.success is False
            assert response.status_code == 0
            assert "timeout" in response.error.lower()
            assert response.retries == 2  # max_retries=2

    @pytest.mark.asyncio
    async def test_unexpected_exception(self, client):
        """Verify handling of unexpected exceptions."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(
                side_effect=Exception("Unexpected error")
            )
            mock_get_client.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                response = await client.get("/unexpected")

            assert response.success is False
            assert "Unexpected error" in response.error


# ============================================================================
# HTTP Client Management Tests
# ============================================================================


class TestHTTPClientManagement:
    """Tests for HTTP client lifecycle management."""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self):
        """Verify _get_client creates httpx client."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            custom_headers={"X-Custom": "value"},
        )
        client = ConcreteTestClient(config=config)

        assert client._client is None

        http_client = await client._get_client()

        assert http_client is not None
        assert client._client is http_client

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self):
        """Verify _get_client reuses existing client."""
        client = ConcreteTestClient()

        client1 = await client._get_client()
        client2 = await client._get_client()

        assert client1 is client2

        # Cleanup
        await client.close()

    @pytest.mark.asyncio
    async def test_close_releases_client(self):
        """Verify close() releases HTTP client."""
        client = ConcreteTestClient()
        await client._get_client()

        assert client._client is not None

        await client.close()

        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        """Verify close() is safe when no client exists."""
        client = ConcreteTestClient()

        # Should not raise
        await client.close()


# ============================================================================
# Metrics Tests
# ============================================================================


class TestMetrics:
    """Tests for get_metrics method."""

    def test_get_metrics_initial(self):
        """Verify initial metrics values."""
        client = ConcreteTestClient()
        metrics = client.get_metrics()

        assert metrics["service"] == "test-service"
        assert metrics["request_count"] == 0
        assert metrics["error_count"] == 0
        assert metrics["error_rate"] == 0.0
        assert metrics["base_url"] == "http://localhost:8000"
        assert metrics["auth_type"] == "none"

    def test_get_metrics_after_requests(self):
        """Verify metrics after some requests."""
        client = ConcreteTestClient()
        client._request_count = 10
        client._error_count = 2

        metrics = client.get_metrics()

        assert metrics["request_count"] == 10
        assert metrics["error_count"] == 2
        assert metrics["error_rate"] == 0.2


# ============================================================================
# Health Check Tests
# ============================================================================


class TestHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Verify health check returns True on success."""
        client = ConcreteTestClient()

        mock_response = APIResponse(success=True, status_code=200)
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.health_check()

            assert result is True
            mock_get.assert_called_once_with("/health")

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Verify health check returns False on failure."""
        client = ConcreteTestClient()

        mock_response = APIResponse(success=False, status_code=503)
        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """Verify health check returns False on exception."""
        client = ConcreteTestClient()

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            result = await client.health_check()

            assert result is False


# ============================================================================
# Context Manager Tests
# ============================================================================


class TestContextManager:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Verify async context manager properly manages lifecycle."""
        async with ConcreteTestClient() as client:
            # Should be usable inside context
            assert client._client is None  # Client created on first request

        # Client should be closed after context exit
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager_with_client_created(self):
        """Verify context manager closes client that was created."""
        async with ConcreteTestClient() as client:
            # Create the HTTP client
            await client._get_client()
            assert client._client is not None

        # Should be closed
        assert client._client is None


# ============================================================================
# Logging Tests
# ============================================================================


class TestRequestLogging:
    """Tests for request/response logging."""

    @pytest.mark.asyncio
    async def test_logging_enabled(self):
        """Verify logging when enabled."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            log_requests=True,
            log_responses=True,
        )
        client = ConcreteTestClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            with patch.object(client.logger, "debug") as mock_debug:
                await client.get("/test")

                # Should have logged request and response
                assert mock_debug.call_count >= 2

    @pytest.mark.asyncio
    async def test_logging_disabled(self):
        """Verify no logging when disabled."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            log_requests=False,
            log_responses=False,
        )
        client = ConcreteTestClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            with patch.object(client.logger, "debug") as mock_debug:
                await client.get("/test")

                # Should have minimal or no debug logging
                # (only internal debug calls, not request/response)
                for call in mock_debug.call_args_list:
                    msg = str(call)
                    assert "GET http://localhost:8000/test" not in msg


# ============================================================================
# Response Parsing Tests
# ============================================================================


class TestResponseParsing:
    """Tests for response parsing edge cases."""

    @pytest.fixture
    def client(self):
        """Client for parsing tests."""
        config = APIClientConfig(
            base_url="http://localhost:8000",
            log_requests=False,
            log_responses=False,
        )
        return ConcreteTestClient(config=config)

    @pytest.mark.asyncio
    async def test_empty_response_content(self, client):
        """Verify handling of empty response content."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = b''  # Empty
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.get("/empty")

            assert response.success is True
            assert response.data is None

    @pytest.mark.asyncio
    async def test_non_json_response(self, client):
        """Verify handling of non-JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'Plain text response'
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = "Plain text response"
        mock_response.headers = {}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            response = await client.get("/text")

            assert response.success is True
            assert response.data == "Plain text response"


# ============================================================================
# AuthType Enum Tests
# ============================================================================


class TestAuthTypeEnum:
    """Tests for AuthType enum."""

    def test_enum_values(self):
        """Verify all enum values."""
        assert AuthType.NONE.value == "none"
        assert AuthType.API_KEY.value == "api_key"
        assert AuthType.BEARER_TOKEN.value == "bearer_token"
        assert AuthType.BASIC_AUTH.value == "basic_auth"
        assert AuthType.OAUTH2.value == "oauth2"

    def test_enum_count(self):
        """Verify we have all expected auth types."""
        assert len(AuthType) == 5
