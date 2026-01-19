"""
Pytest configuration and shared fixtures for AGNTCY multi-agent tests
Phase 1: Unit and integration tests for local development
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# Windows Compatibility Fix
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def configure_windows_event_loop():
    """
    Configure Windows event loop policy for async tests.

    Windows has different default event loop behavior than Unix systems.
    This fixture ensures async tests run correctly on Windows by using
    the ProactorEventLoopPolicy instead of the default SelectorEventLoopPolicy.

    This is automatically applied to all test sessions on Windows.
    """
    if sys.platform == "win32":
        import asyncio
        # Set Windows-specific event loop policy for better async compatibility
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


# =============================================================================
# Shared Fixtures
# =============================================================================

@pytest.fixture
def sample_logger():
    """Sample logger for testing."""
    import logging
    logger = logging.getLogger("test-logger")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.fixture
def sample_customer_message():
    """Sample customer message for testing."""
    return {
        "message_id": "msg-test-001",
        "customer_id": "cust-test-123",
        "content": "Where is my order #12345?",
        "channel": "chat",
        "language": "en",
        "metadata": {}
    }


@pytest.fixture
def sample_a2a_message():
    """Sample AGNTCY A2A message structure."""
    return {
        "messageId": "uuid-test-001",
        "role": "user",
        "parts": [{
            "type": "text",
            "content": {
                "message_id": "msg-001",
                "customer_id": "cust-123",
                "content": "I want to return my order",
                "channel": "email"
            }
        }],
        "contextId": "ctx-test-001",
        "taskId": "task-test-001",
        "metadata": {}
    }


@pytest.fixture
def sample_intent_result():
    """Sample intent classification result."""
    return {
        "message_id": "msg-test-001",
        "context_id": "ctx-test-001",
        "intent": "order_status",
        "confidence": 0.85,
        "extracted_entities": {"order_number": "12345"},
        "language": "en",
        "routing_suggestion": "knowledge-retrieval"
    }


@pytest.fixture
def sample_knowledge_query():
    """Sample knowledge query."""
    return {
        "query_id": "q-test-001",
        "context_id": "ctx-test-001",
        "query_text": "wireless headphones",
        "intent": "product_inquiry",
        "filters": {},
        "max_results": 5,
        "language": "en"
    }


@pytest.fixture
def mock_shopify_product():
    """Sample Shopify product data."""
    return {
        "id": 1001,
        "title": "Premium Wireless Headphones",
        "body_html": "<p>High-quality wireless headphones</p>",
        "vendor": "AudioTech",
        "product_type": "Electronics",
        "variants": [
            {
                "id": 10011,
                "product_id": 1001,
                "title": "Black",
                "price": "299.99",
                "sku": "WH-BLK-001"
            }
        ]
    }


@pytest.fixture
def mock_zendesk_ticket():
    """Sample Zendesk ticket data."""
    return {
        "id": 1001,
        "subject": "Order #12345 not received",
        "description": "I haven't received my order",
        "status": "open",
        "priority": "high",
        "type": "problem",
        "requester_id": 5001,
        "created_at": "2024-01-15T10:30:00Z",
        "tags": ["shipping", "order_issue"]
    }


# =============================================================================
# Mock Configuration
# =============================================================================

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "slim_endpoint": "http://localhost:46357",
        "slim_password": "test-password",
        "nats_endpoint": "nats://localhost:4222",
        "otlp_endpoint": "http://localhost:4318",
        "enable_tracing": False,
        "agent_topic": "test-agent",
        "log_level": "DEBUG",
        "shopify_url": "http://localhost:8001",
        "zendesk_url": "http://localhost:8002",
        "mailchimp_url": "http://localhost:8003",
        "google_analytics_url": "http://localhost:8004"
    }


# =============================================================================
# Test Markers
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring services"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take significant time"
    )
    config.addinivalue_line(
        "markers", "asyncio: Async tests using pytest-asyncio"
    )
