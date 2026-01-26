# MCP Testing and Validation Approach for Phase 4-5

**Date:** 2026-01-26
**Purpose:** Define the testing strategy for MCP (Model Context Protocol) integration with UCP capabilities

---

## Executive Summary

This document outlines a comprehensive testing approach for MCP-based UCP integration, covering:
1. Unit testing of MCP client components
2. Integration testing with Shopify development store
3. Contract testing for UCP capability compliance
4. End-to-end testing of commerce flows
5. Performance and reliability testing

---

## 1. Testing Pyramid for MCP/UCP

```
                    ┌─────────────┐
                    │   E2E (5%)  │  Full commerce flows
                    ├─────────────┤
                    │Contract (15%)│  UCP spec compliance
                    ├─────────────┤
                    │Integration   │  Shopify API, real services
                    │   (30%)      │
                    ├─────────────┤
                    │  Unit (50%)  │  MCP client, tool handlers
                    └─────────────┘
```

---

## 2. Unit Testing Strategy

### 2.1 MCP Client Unit Tests

**Scope:** Test MCP client wrapper in isolation with mocked responses

**Location:** `tests/unit/test_ucp_client.py`

```python
# Example unit test structure
import pytest
from unittest.mock import AsyncMock, patch
from shared.ucp_client import UCPMCPClient
from shared.ucp_models import Product, CatalogSearchResponse

class TestUCPMCPClient:
    """Unit tests for UCP MCP client wrapper."""

    @pytest.fixture
    def mock_mcp_transport(self):
        """Mock MCP transport for isolated testing."""
        transport = AsyncMock()
        return transport

    @pytest.fixture
    def ucp_client(self, mock_mcp_transport):
        """Create UCP client with mocked transport."""
        return UCPMCPClient(transport=mock_mcp_transport)

    @pytest.mark.asyncio
    async def test_search_catalog_success(self, ucp_client, mock_mcp_transport):
        """Test successful catalog search."""
        # Arrange
        mock_mcp_transport.call_tool.return_value = {
            "products": [
                {"id": "prod_123", "title": "Ethiopian Yirgacheffe", "price": 18.99}
            ],
            "total_count": 1
        }

        # Act
        result = await ucp_client.search_catalog("Ethiopian coffee", limit=5)

        # Assert
        assert len(result.products) == 1
        assert result.products[0].title == "Ethiopian Yirgacheffe"
        mock_mcp_transport.call_tool.assert_called_once_with(
            "dev.ucp.shopping.catalog.search",
            {"query": "Ethiopian coffee", "limit": 5}
        )

    @pytest.mark.asyncio
    async def test_search_catalog_empty_results(self, ucp_client, mock_mcp_transport):
        """Test catalog search with no results."""
        mock_mcp_transport.call_tool.return_value = {"products": [], "total_count": 0}

        result = await ucp_client.search_catalog("nonexistent product")

        assert len(result.products) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_search_catalog_error_handling(self, ucp_client, mock_mcp_transport):
        """Test error handling for failed catalog search."""
        mock_mcp_transport.call_tool.side_effect = Exception("MCP transport error")

        with pytest.raises(UCPClientError) as exc_info:
            await ucp_client.search_catalog("test query")

        assert "MCP transport error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_order_status_success(self, ucp_client, mock_mcp_transport):
        """Test successful order status retrieval."""
        mock_mcp_transport.call_tool.return_value = {
            "order_id": "ORD-2026-001",
            "status": "shipped",
            "tracking_number": "1Z999AA10123456784"
        }

        result = await ucp_client.get_order_status("ORD-2026-001")

        assert result.status == "shipped"
        assert result.tracking_number == "1Z999AA10123456784"
```

### 2.2 UCP Tool Handler Tests

**Scope:** Test individual UCP capability handlers

```python
class TestUCPToolHandlers:
    """Unit tests for UCP tool response handlers."""

    def test_format_product_data(self):
        """Test product data formatting."""
        raw_product = {
            "id": "prod_123",
            "title": "Ethiopian Yirgacheffe",
            "price_range": {"min": 18.99, "max": 24.99},
            "images": [{"src": "https://example.com/coffee.jpg"}],
            "description": "Light roast with floral notes"
        }

        formatted = format_product_data(raw_product)

        assert formatted.id == "prod_123"
        assert formatted.price == "$18.99 - $24.99"
        assert formatted.image_url == "https://example.com/coffee.jpg"

    def test_format_product_data_missing_fields(self):
        """Test handling of missing optional fields."""
        raw_product = {"id": "prod_456", "title": "Mystery Coffee"}

        formatted = format_product_data(raw_product)

        assert formatted.price == "Price not available"
        assert formatted.image_url is None
```

### 2.3 Unit Test Coverage Targets

| Component | Target Coverage | Priority |
|-----------|-----------------|----------|
| `UCPMCPClient` | 90% | P0 |
| `ucp_models.py` | 95% | P0 |
| Tool handlers | 85% | P1 |
| Error handling | 90% | P0 |

---

## 3. Integration Testing Strategy

### 3.1 Shopify Development Store Setup

**Prerequisites:**
1. Shopify Partner account (free)
2. Development store created
3. Test products populated
4. OAuth app registered

**Test Data Requirements:**

| Data Type | Quantity | Purpose |
|-----------|----------|---------|
| Products | 50+ | Catalog search testing |
| Orders | 20+ | Order status testing |
| Customers | 10+ | Identity linking testing |
| Discounts | 5+ | Discount extension testing |

### 3.2 Integration Test Structure

**Location:** `tests/integration/test_ucp_integration.py`

```python
import pytest
from shared.ucp_client import UCPMCPClient
from shared.config import Config

@pytest.fixture(scope="module")
def ucp_client():
    """Create real UCP client connected to Shopify dev store."""
    config = Config.load_from_env()
    client = UCPMCPClient(
        shopify_store=config.SHOPIFY_DEV_STORE,
        access_token=config.SHOPIFY_ACCESS_TOKEN
    )
    yield client
    client.close()

class TestUCPCatalogIntegration:
    """Integration tests for UCP Catalog capability."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_real_products(self, ucp_client):
        """Search for actual products in development store."""
        result = await ucp_client.search_catalog("coffee", limit=10)

        assert len(result.products) > 0
        assert all(hasattr(p, 'id') for p in result.products)
        assert all(hasattr(p, 'title') for p in result.products)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_with_filters(self, ucp_client):
        """Test catalog search with price filters."""
        result = await ucp_client.search_catalog(
            "coffee",
            filters={"price_min": 10, "price_max": 25}
        )

        for product in result.products:
            assert 10 <= product.price_min <= 25

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_pagination(self, ucp_client):
        """Test catalog search pagination."""
        page1 = await ucp_client.search_catalog("coffee", limit=5, offset=0)
        page2 = await ucp_client.search_catalog("coffee", limit=5, offset=5)

        # Pages should have different products
        page1_ids = {p.id for p in page1.products}
        page2_ids = {p.id for p in page2.products}
        assert page1_ids.isdisjoint(page2_ids)

class TestUCPOrderIntegration:
    """Integration tests for UCP Order capability."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_order_status_existing(self, ucp_client):
        """Get status of existing test order."""
        # Use known test order from development store
        result = await ucp_client.get_order_status("TEST-ORD-001")

        assert result.order_id == "TEST-ORD-001"
        assert result.status in ["pending", "processing", "shipped", "delivered"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_order_status_not_found(self, ucp_client):
        """Handle non-existent order gracefully."""
        with pytest.raises(OrderNotFoundError):
            await ucp_client.get_order_status("NONEXISTENT-ORDER")
```

### 3.3 Integration Test Categories

| Category | Test Count | CI Integration |
|----------|------------|----------------|
| Catalog Search | 10-15 | Nightly |
| Order Status | 5-10 | Nightly |
| Checkout Flow | 5-8 | Weekly (manual) |
| Webhooks | 5-8 | Nightly |
| Error Scenarios | 10-15 | Nightly |

---

## 4. Contract Testing Strategy

### 4.1 UCP Specification Compliance

**Purpose:** Ensure our implementation matches UCP specification

**Approach:** Use schema validation against official UCP schemas

```python
import jsonschema
from ucp_schemas import CATALOG_SEARCH_REQUEST_SCHEMA, CATALOG_SEARCH_RESPONSE_SCHEMA

class TestUCPContractCompliance:
    """Contract tests for UCP specification compliance."""

    def test_catalog_search_request_schema(self):
        """Validate catalog search request matches UCP spec."""
        request = {
            "query": "Ethiopian coffee",
            "limit": 10,
            "offset": 0,
            "filters": {"price_min": 10}
        }

        # Should not raise
        jsonschema.validate(request, CATALOG_SEARCH_REQUEST_SCHEMA)

    def test_catalog_search_response_schema(self):
        """Validate catalog search response matches UCP spec."""
        response = await ucp_client.search_catalog("test")

        jsonschema.validate(response.to_dict(), CATALOG_SEARCH_RESPONSE_SCHEMA)

    def test_checkout_session_schema(self):
        """Validate checkout session matches UCP spec."""
        session = await ucp_client.create_checkout_session(cart_items=[...])

        jsonschema.validate(session.to_dict(), CHECKOUT_SESSION_SCHEMA)
```

### 4.2 MCP Binding Compliance

**Purpose:** Ensure MCP tool calls follow protocol specification

```python
class TestMCPBindingCompliance:
    """Contract tests for MCP binding compliance."""

    def test_tool_call_format(self):
        """Validate MCP tool call format."""
        # Capture actual tool call
        with capture_mcp_calls() as calls:
            await ucp_client.search_catalog("test")

        assert len(calls) == 1
        call = calls[0]

        # Validate MCP tool call structure
        assert "method" in call
        assert call["method"] == "tools/call"
        assert "params" in call
        assert "name" in call["params"]
        assert call["params"]["name"] == "dev.ucp.shopping.catalog.search"

    def test_tool_response_format(self):
        """Validate MCP tool response format."""
        response = await ucp_client.search_catalog("test")

        # Response should be properly deserialized
        assert isinstance(response, CatalogSearchResponse)
        assert hasattr(response, 'products')
        assert hasattr(response, 'total_count')
```

### 4.3 Contract Test Automation

**CI Integration:**
```yaml
# .github/workflows/ci.yml addition
contract-tests:
  runs-on: ubuntu-latest
  steps:
    - name: Download UCP Schemas
      run: |
        curl -o schemas/ucp-catalog.json https://ucp.dev/schemas/2026-01-11/catalog.json
        curl -o schemas/ucp-checkout.json https://ucp.dev/schemas/2026-01-11/checkout.json

    - name: Run Contract Tests
      run: pytest tests/contract/ -v --tb=short
```

---

## 5. End-to-End Testing Strategy

### 5.1 Commerce Flow Scenarios

| Scenario | Description | Priority |
|----------|-------------|----------|
| **E2E-001** | Search → View Product → Add to Cart → Checkout | P0 |
| **E2E-002** | Search → No Results → Suggest Alternatives | P1 |
| **E2E-003** | Order Status → Shipped → Tracking Link | P0 |
| **E2E-004** | Apply Discount → Price Updates → Checkout | P1 |
| **E2E-005** | Checkout → Payment Fails → Retry | P1 |
| **E2E-006** | Checkout → Timeout → Session Recovery | P2 |

### 5.2 E2E Test Implementation

```python
class TestCommerceE2E:
    """End-to-end tests for complete commerce flows."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_search_to_checkout_flow(self, console_client):
        """E2E-001: Complete purchase flow from search to checkout."""
        # Step 1: User searches for product
        response = await console_client.send_message(
            "I'm looking for Ethiopian coffee"
        )
        assert "Ethiopian" in response.text
        assert response.products is not None
        assert len(response.products) > 0

        # Step 2: User asks about specific product
        product_id = response.products[0].id
        response = await console_client.send_message(
            f"Tell me more about the {response.products[0].title}"
        )
        assert response.intent == "PRODUCT_INQUIRY"

        # Step 3: User adds to cart
        response = await console_client.send_message(
            "Add it to my cart"
        )
        assert "cart" in response.text.lower()
        assert response.cart is not None
        assert len(response.cart.items) == 1

        # Step 4: User initiates checkout
        response = await console_client.send_message(
            "I'd like to checkout"
        )
        assert response.checkout_url is not None
        assert "continue" in response.text.lower()

        # Step 5: Verify checkout session created
        session = await ucp_client.get_checkout_session(response.session_id)
        assert session.status == "pending"
        assert len(session.line_items) == 1

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_order_status_flow(self, console_client):
        """E2E-003: Order status inquiry flow."""
        # Pre-condition: Create test order
        order_id = await create_test_order()

        # User asks about order
        response = await console_client.send_message(
            f"What's the status of order {order_id}?"
        )

        assert response.intent == "ORDER_STATUS"
        assert order_id in response.text
        assert any(status in response.text.lower()
                   for status in ["processing", "shipped", "delivered"])
```

### 5.3 E2E Test Environment

| Environment | Purpose | Data |
|-------------|---------|------|
| **Local + Mock** | Development | Mocked UCP responses |
| **Local + Dev Store** | Integration | Real Shopify dev store |
| **Staging** | Pre-production | Cloned production data |
| **Production** | Smoke tests | Real data (read-only) |

---

## 6. Performance Testing Strategy

### 6.1 MCP/UCP Latency Requirements

| Operation | Target P95 | Acceptable P99 |
|-----------|------------|----------------|
| Catalog Search | 500ms | 1000ms |
| Order Status | 300ms | 600ms |
| Checkout Session Create | 800ms | 1500ms |
| Full Conversation Turn | 2500ms | 4000ms |

### 6.2 Performance Test Implementation

```python
class TestUCPPerformance:
    """Performance tests for UCP operations."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_catalog_search_latency(self, ucp_client):
        """Measure catalog search latency."""
        latencies = []

        for _ in range(100):
            start = time.perf_counter()
            await ucp_client.search_catalog("coffee")
            latencies.append((time.perf_counter() - start) * 1000)

        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        assert p95 < 500, f"P95 latency {p95}ms exceeds 500ms target"
        assert p99 < 1000, f"P99 latency {p99}ms exceeds 1000ms target"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_searches(self, ucp_client):
        """Test performance under concurrent load."""
        async def single_search():
            start = time.perf_counter()
            await ucp_client.search_catalog("coffee")
            return (time.perf_counter() - start) * 1000

        # 10 concurrent searches
        tasks = [single_search() for _ in range(10)]
        latencies = await asyncio.gather(*tasks)

        assert max(latencies) < 2000, "Max latency under load exceeds 2s"
```

### 6.3 Load Testing with Locust

```python
# locustfile_ucp.py
from locust import User, task, between

class UCPUser(User):
    wait_time = between(1, 3)

    @task(3)
    def search_products(self):
        """Simulate product search."""
        self.client.post("/api/chat", json={
            "message": "Show me coffee options",
            "session_id": self.session_id
        })

    @task(1)
    def check_order(self):
        """Simulate order status check."""
        self.client.post("/api/chat", json={
            "message": "What's the status of my order?",
            "session_id": self.session_id
        })
```

---

## 7. Reliability Testing

### 7.1 Failure Scenarios

| Scenario | Test Approach | Expected Behavior |
|----------|---------------|-------------------|
| Shopify API timeout | Mock slow response | Graceful timeout, retry |
| Invalid OAuth token | Expired token | Re-authenticate, retry |
| Rate limiting | Exceed Shopify limits | Backoff, queue requests |
| Network partition | Kill connection | Reconnect, resume session |
| Malformed response | Return invalid JSON | Error handling, fallback |

### 7.2 Chaos Testing

```python
class TestUCPResilience:
    """Resilience tests for UCP integration."""

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_shopify_timeout_handling(self, ucp_client):
        """Test handling of Shopify API timeout."""
        with mock_slow_response(delay_seconds=10):
            with pytest.raises(TimeoutError):
                await ucp_client.search_catalog("test", timeout=5)

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_rate_limit_backoff(self, ucp_client):
        """Test exponential backoff on rate limiting."""
        with mock_rate_limit(limit=2):
            # First 2 should succeed
            await ucp_client.search_catalog("test1")
            await ucp_client.search_catalog("test2")

            # Third should trigger backoff and eventually succeed
            start = time.time()
            await ucp_client.search_catalog("test3")
            elapsed = time.time() - start

            assert elapsed > 1.0, "Should have backed off"

    @pytest.mark.chaos
    @pytest.mark.asyncio
    async def test_session_recovery(self, ucp_client):
        """Test checkout session recovery after failure."""
        # Create checkout session
        session = await ucp_client.create_checkout_session([...])

        # Simulate crash and recovery
        await ucp_client.close()
        ucp_client = UCPMCPClient(...)

        # Should be able to recover session
        recovered = await ucp_client.get_checkout_session(session.id)
        assert recovered.id == session.id
        assert recovered.line_items == session.line_items
```

---

## 8. Test Automation and CI Integration

### 8.1 CI Pipeline Integration

```yaml
# .github/workflows/ucp-tests.yml
name: UCP Tests

on:
  push:
    paths:
      - 'shared/ucp_*.py'
      - 'tests/**/test_ucp_*.py'
  schedule:
    - cron: '0 2 * * *'  # Nightly

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Unit Tests
        run: pytest tests/unit/test_ucp_*.py -v --cov

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - name: Run Integration Tests
        env:
          SHOPIFY_DEV_STORE: ${{ secrets.SHOPIFY_DEV_STORE }}
          SHOPIFY_ACCESS_TOKEN: ${{ secrets.SHOPIFY_ACCESS_TOKEN }}
        run: pytest tests/integration/test_ucp_*.py -v -m integration

  contract-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - name: Run Contract Tests
        run: pytest tests/contract/test_ucp_*.py -v

  performance-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v4
      - name: Run Performance Tests
        run: pytest tests/performance/test_ucp_*.py -v -m performance
```

### 8.2 Test Coverage Requirements

| Test Type | Coverage Target | Blocking |
|-----------|-----------------|----------|
| Unit | 85% | Yes |
| Integration | 70% | No |
| Contract | 100% of schemas | Yes |
| E2E | All P0 scenarios | Yes |
| Performance | All P95 targets | No |

---

## 9. Test Data Management

### 9.1 Test Fixtures

**Location:** `tests/fixtures/ucp/`

```
tests/fixtures/ucp/
├── products.json          # Sample product data
├── orders.json            # Sample order data
├── checkout_sessions.json # Sample checkout sessions
├── schemas/
│   ├── catalog.json       # UCP Catalog schema
│   └── checkout.json      # UCP Checkout schema
└── mocks/
    ├── catalog_search.json
    └── order_status.json
```

### 9.2 Data Generation

```python
# tests/fixtures/ucp/generate_test_data.py
def generate_test_products(count: int = 50) -> List[dict]:
    """Generate realistic test product data."""
    products = []
    for i in range(count):
        products.append({
            "id": f"prod_{uuid.uuid4().hex[:8]}",
            "title": f"Test Coffee {i+1}",
            "price": round(random.uniform(12.99, 29.99), 2),
            "description": f"Test product description {i+1}",
            "images": [{"src": f"https://example.com/coffee_{i}.jpg"}],
            "tags": random.sample(["light", "medium", "dark", "organic", "fair-trade"], 2)
        })
    return products
```

---

## 10. Summary and Recommendations

### 10.1 Testing Priorities by Phase

**Phase 4:**
1. Unit tests for MCP client (P0)
2. Integration tests for Catalog (P0)
3. Contract tests for UCP schemas (P0)
4. E2E tests for search flows (P1)
5. Performance baseline (P1)

**Phase 5:**
1. Integration tests for Checkout (P0)
2. E2E tests for purchase flows (P0)
3. Reliability/chaos tests (P1)
4. Load testing with Locust (P1)
5. Production smoke tests (P0)

### 10.2 Key Success Metrics

| Metric | Target |
|--------|--------|
| Unit test coverage | >85% |
| Integration test pass rate | >95% |
| Contract compliance | 100% |
| E2E scenario pass rate | >90% |
| P95 latency targets met | 100% |

### 10.3 Tools and Technologies

| Purpose | Tool |
|---------|------|
| Unit/Integration testing | pytest, pytest-asyncio |
| Contract testing | jsonschema |
| Performance testing | Locust, pytest-benchmark |
| Chaos testing | toxiproxy, pytest-chaos |
| CI/CD | GitHub Actions |
| Coverage | pytest-cov |

---

**Document Status:** Complete
**Last Updated:** 2026-01-26
