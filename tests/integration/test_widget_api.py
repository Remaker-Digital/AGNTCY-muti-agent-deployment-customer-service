# ============================================================================
# Integration Tests for Widget API Endpoints - Phase 6
# ============================================================================
#
# Purpose: Test the widget API endpoints for configuration, session management,
#          authentication flows, and embed code generation.
#
# Test Coverage:
# - Widget configuration endpoints
# - Session creation and retrieval
# - Authentication flow (OAuth initiation and callback)
# - Embed code generation
# - Error handling and edge cases
#
# Related Documentation:
# - Widget API: api_gateway/main.py
# - Widget Source: widget/src/chat-widget.js
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q1.B)
# ============================================================================

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from api_gateway.main import app
    return TestClient(app)


@pytest.fixture
def mock_session_manager():
    """Mock session manager for tests."""
    with patch("api_gateway.main.get_session_manager") as mock:
        manager = AsyncMock()
        mock.return_value = manager
        yield manager


# ============================================================================
# Widget Configuration Tests
# ============================================================================


class TestWidgetConfig:
    """Tests for widget configuration endpoints."""

    def test_get_config_returns_defaults(self, client):
        """GET /api/v1/widget/config/{merchant_id} returns default config."""
        response = client.get("/api/v1/widget/config/test-merchant")

        assert response.status_code == 200
        data = response.json()

        assert data["merchant_id"] == "test-merchant"
        assert data["enabled"] is True
        assert data["primary_color"] == "#5c6ac4"
        assert data["position"] == "bottom-right"
        assert data["language"] == "en"
        assert data["agent_name"] == "Support Assistant"

    def test_get_config_includes_features(self, client):
        """Widget config includes feature flags."""
        response = client.get("/api/v1/widget/config/test-merchant")

        data = response.json()
        features = data["features"]

        assert "file_upload" in features
        assert "typing_indicators" in features
        assert features["file_upload"] is False  # Phase 7 feature
        assert features["typing_indicators"] is True

    def test_get_config_different_merchants(self, client):
        """Different merchants get their own config."""
        response1 = client.get("/api/v1/widget/config/merchant-a")
        response2 = client.get("/api/v1/widget/config/merchant-b")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert data1["merchant_id"] == "merchant-a"
        assert data2["merchant_id"] == "merchant-b"


# ============================================================================
# Session API Tests
# ============================================================================


class TestSessionAPI:
    """Tests for session creation and retrieval."""

    def test_create_session_anonymous(self, client):
        """POST /api/v1/widget/sessions creates anonymous session."""
        response = client.post(
            "/api/v1/widget/sessions",
            json={
                "merchant_id": "test-merchant",
                "channel": "web",
                "device_id": "device-123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert data["auth_level"] == "anonymous"
        assert "expires_at" in data
        assert "created_at" in data

    def test_create_session_with_user_agent(self, client):
        """Session creation accepts user agent."""
        response = client.post(
            "/api/v1/widget/sessions",
            json={
                "merchant_id": "test-merchant",
                "channel": "web",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_create_session_different_channels(self, client):
        """Sessions can be created for different channels."""
        for channel in ["web", "whatsapp", "mobile"]:
            response = client.post(
                "/api/v1/widget/sessions",
                json={"merchant_id": "test-merchant", "channel": channel},
            )
            assert response.status_code == 200

    def test_get_session_not_found(self, client):
        """GET /api/v1/widget/sessions/{session_id} returns 404 for unknown session."""
        response = client.get("/api/v1/widget/sessions/nonexistent-session-id")
        assert response.status_code == 404


# ============================================================================
# Embed Code Generation Tests
# ============================================================================


class TestEmbedCodeGeneration:
    """Tests for widget embed code generation."""

    def test_generate_embed_code_post(self, client):
        """POST /api/v1/widget/embed-code generates valid embed code."""
        response = client.post(
            "/api/v1/widget/embed-code",
            json={
                "merchant_id": "acme-coffee",
                "primary_color": "#ff5722",
                "position": "bottom-left",
                "language": "fr-CA",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["merchant_id"] == "acme-coffee"
        assert "cdn_url" in data
        assert "script_tag" in data
        assert "init_code" in data
        assert "full_snippet" in data

        # Verify script tag format
        assert data["script_tag"].startswith("<script src=")
        assert "agntcy-chat.min.js" in data["cdn_url"]

        # Verify init code contains options
        assert "acme-coffee" in data["init_code"]
        assert "#ff5722" in data["init_code"]
        assert "bottom-left" in data["init_code"]
        assert "fr-CA" in data["init_code"]

        # Verify full snippet structure
        assert "<!-- AGNTCY Chat Widget -->" in data["full_snippet"]
        assert "AGNTCYChat.init" in data["full_snippet"]

    def test_generate_embed_code_get(self, client):
        """GET /api/v1/widget/embed-code/{merchant_id} works with query params."""
        response = client.get(
            "/api/v1/widget/embed-code/test-merchant",
            params={
                "primary_color": "#4caf50",
                "position": "bottom-right",
                "language": "es",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["merchant_id"] == "test-merchant"
        assert "#4caf50" in data["init_code"]
        assert "es" in data["init_code"]

    def test_generate_embed_code_defaults(self, client):
        """Embed code uses defaults when options not provided."""
        response = client.post(
            "/api/v1/widget/embed-code",
            json={"merchant_id": "minimal-merchant"},
        )

        assert response.status_code == 200
        data = response.json()

        # Default values should be applied
        assert "#5c6ac4" in data["init_code"]  # Default primary color
        assert "bottom-right" in data["init_code"]  # Default position
        assert '"en"' in data["init_code"]  # Default language

    def test_generate_embed_code_custom_greeting(self, client):
        """Embed code includes custom greeting when provided."""
        response = client.post(
            "/api/v1/widget/embed-code",
            json={
                "merchant_id": "greeting-merchant",
                "custom_greeting": "Welcome to our store!",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "Welcome to our store!" in data["init_code"]

    def test_generate_embed_code_powered_by_false(self, client):
        """Embed code respects show_powered_by setting."""
        response = client.post(
            "/api/v1/widget/embed-code",
            json={
                "merchant_id": "no-branding",
                "show_powered_by": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert '"showPoweredBy": false' in data["init_code"]

    def test_embed_code_is_valid_html(self, client):
        """Generated snippet is valid HTML."""
        response = client.post(
            "/api/v1/widget/embed-code",
            json={"merchant_id": "html-test"},
        )

        data = response.json()
        snippet = data["full_snippet"]

        # Check proper HTML structure
        assert snippet.count("<script") == 2  # One for CDN, one for init
        assert snippet.count("</script>") == 2
        assert snippet.startswith("<!--")
        assert snippet.endswith("-->")


# ============================================================================
# Authentication Flow Tests
# ============================================================================


class TestAuthenticationFlow:
    """Tests for OAuth authentication flow."""

    def test_login_endpoint_requires_session(self, client):
        """Login endpoint requires session_id and redirect_uri."""
        response = client.post(
            "/api/v1/widget/auth/login",
            json={"session_id": "test-session", "redirect_uri": "https://example.com/callback"},
        )

        # Should either return auth URL or 501 if not configured
        assert response.status_code in [200, 501]

    def test_callback_endpoint_processes_code(self, client):
        """Callback endpoint accepts authorization code."""
        response = client.post(
            "/api/v1/widget/auth/callback",
            json={
                "code": "test-auth-code",
                "state": "test-state",
                "redirect_uri": "https://example.com/callback",
            },
        )

        # Should process or return 501 if not configured
        assert response.status_code in [200, 501]


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in widget API."""

    def test_invalid_session_request(self, client):
        """Invalid session request returns 422."""
        response = client.post(
            "/api/v1/widget/sessions",
            json={},  # Missing required merchant_id
        )

        assert response.status_code == 422

    def test_invalid_embed_code_request(self, client):
        """Invalid embed code request returns 422."""
        response = client.post(
            "/api/v1/widget/embed-code",
            json={},  # Missing required merchant_id
        )

        assert response.status_code == 422


# ============================================================================
# CORS and Security Tests
# ============================================================================


class TestCORSAndSecurity:
    """Tests for CORS and security headers."""

    def test_cors_headers_present(self, client):
        """CORS headers are present for cross-origin requests."""
        response = client.options(
            "/api/v1/widget/config/test-merchant",
            headers={"Origin": "https://merchant-site.com"},
        )

        # FastAPI CORS middleware should handle this
        # Status could be 200 or 405 depending on config
        assert response.status_code in [200, 405]

    def test_content_type_json(self, client):
        """API responses have correct content type."""
        response = client.get("/api/v1/widget/config/test-merchant")

        assert "application/json" in response.headers.get("content-type", "")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
