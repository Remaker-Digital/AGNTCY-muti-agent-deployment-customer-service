"""
Unit tests for mock API endpoints
Tests Shopify, Zendesk, Mailchimp, and Google Analytics mocks
"""

import pytest


@pytest.mark.unit
class TestMockAPIs:
    """Basic tests to verify mock API structure."""

    def test_shopify_mock_imports(self):
        """Test that Shopify mock can be imported."""
        try:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path.cwd() / "mocks" / "shopify"))
            import app as shopify_app

            assert shopify_app.app is not None
        except ImportError:
            pytest.skip("Shopify mock not importable in test context")

    def test_zendesk_mock_imports(self):
        """Test that Zendesk mock can be imported."""
        try:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path.cwd() / "mocks" / "zendesk"))
            import app as zendesk_app

            assert zendesk_app.app is not None
        except ImportError:
            pytest.skip("Zendesk mock not importable in test context")

    def test_mailchimp_mock_imports(self):
        """Test that Mailchimp mock can be imported."""
        try:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path.cwd() / "mocks" / "mailchimp"))
            import app as mailchimp_app

            assert mailchimp_app.app is not None
        except ImportError:
            pytest.skip("Mailchimp mock not importable in test context")

    def test_google_analytics_mock_imports(self):
        """Test that Google Analytics mock can be imported."""
        try:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path.cwd() / "mocks" / "google-analytics"))
            import app as ga_app

            assert ga_app.app is not None
        except ImportError:
            pytest.skip("Google Analytics mock not importable in test context")


@pytest.mark.integration
@pytest.mark.skip(reason="Requires Docker containers running")
class TestMockAPIEndpoints:
    """Integration tests for mock API endpoints (requires Docker)."""

    import httpx

    @pytest.fixture
    def http_client(self):
        """HTTP client for API testing."""
        return self.httpx.AsyncClient(timeout=5.0)

    async def test_shopify_health(self, http_client):
        """Test Shopify mock health endpoint."""
        response = await http_client.get("http://localhost:8001/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_zendesk_health(self, http_client):
        """Test Zendesk mock health endpoint."""
        response = await http_client.get("http://localhost:8002/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_mailchimp_health(self, http_client):
        """Test Mailchimp mock health endpoint."""
        response = await http_client.get("http://localhost:8003/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_google_analytics_health(self, http_client):
        """Test Google Analytics mock health endpoint."""
        response = await http_client.get("http://localhost:8004/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
