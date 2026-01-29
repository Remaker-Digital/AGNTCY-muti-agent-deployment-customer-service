# Model Context Protocol (MCP)

This page documents how the AGNTCY Multi-Agent Customer Service platform uses the **Model Context Protocol (MCP)** for external service integrations and standardized tool interfaces.

---

## Overview

The Model Context Protocol (MCP) is an open standard for connecting AI assistants to external data sources and tools. In this project, MCP serves as the **external integration protocol**, complementing the Agent-to-Agent (A2A) protocol used for internal agent communication.

### Protocol Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AGNTCY Multi-Agent Platform                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────┐    A2A Protocol     ┌─────────────┐               │
│   │   Intent    │◄──────────────────►│  Response   │               │
│   │   Agent     │                     │   Agent     │               │
│   └──────┬──────┘                     └──────┬──────┘               │
│          │                                    │                       │
│          │ A2A                                │ A2A                   │
│          ▼                                    ▼                       │
│   ┌─────────────┐                     ┌─────────────┐               │
│   │  Knowledge  │                     │ Escalation  │               │
│   │  Retrieval  │                     │   Agent     │               │
│   └──────┬──────┘                     └─────────────┘               │
│          │                                                           │
│          │ MCP Protocol                                              │
│          ▼                                                           │
├─────────────────────────────────────────────────────────────────────┤
│                        External Services                             │
│   ┌─────────┐   ┌─────────┐   ┌───────────┐   ┌─────────┐          │
│   │ Shopify │   │ Zendesk │   │ Mailchimp │   │   UCP   │          │
│   │   API   │   │   API   │   │    API    │   │ Catalog │          │
│   └─────────┘   └─────────┘   └───────────┘   └─────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Protocol Strategy

This project uses a **hybrid protocol approach**:

| Protocol | Purpose | Use Cases |
|----------|---------|-----------|
| **A2A (Agent-to-Agent)** | Internal agent coordination | Intent classification, response generation, escalation decisions, analytics, content validation |
| **MCP (Model Context Protocol)** | External tool integrations | Shopify API, Zendesk API, Mailchimp API, Universal Commerce Protocol (UCP) |

### Why Two Protocols?

1. **A2A Protocol** provides custom agent logic with full control over message routing, context management, and conversation state
2. **MCP Protocol** provides standardized tool interfaces that integrate seamlessly with external services and LLM frameworks

This separation allows internal agents to communicate efficiently while exposing external capabilities through a well-defined, standardized interface.

---

## AGNTCY SDK Integration

The AGNTCY SDK provides first-class support for MCP as one of its core protocols.

### Supported Protocols

```python
from agntcy_app_sdk import AgntcyFactory

factory = AgntcyFactory()
factory.registered_protocols()  # Returns: ['A2A', 'MCP', 'FastMCP']
```

### Creating MCP Clients

The `AgntcyFactory` class provides a dedicated method for creating MCP clients:

```python
# shared/factory.py - MCP Client Creation
from agntcy_app_sdk.protocols import A2AProtocol, MCPProtocol

def create_mcp_client(self, agent_topic: str, transport, **kwargs):
    """
    Create MCP (Model Context Protocol) client.

    Use MCP for standardized tool interfaces and external service integrations.
    Ideal for knowledge retrieval agents accessing search APIs.

    Args:
        agent_topic: Topic name for the MCP client (e.g., "shopify-integration")
        transport: SLIM or NATS transport instance
        **kwargs: Additional MCP-specific configuration

    Returns:
        MCPClient instance for tool-based interactions
    """
    return self._sdk_factory.create_client(
        protocol="MCP",
        agent_topic=agent_topic,
        transport=transport,
        **kwargs
    )
```

### Usage Example

```python
from shared.factory import AgntcyFactory

# Initialize factory
factory = AgntcyFactory()

# Create SLIM transport for secure communication
transport = factory.create_slim_transport()

# Create MCP client for Shopify integration
shopify_client = factory.create_mcp_client(
    agent_topic="shopify-integration",
    transport=transport
)

# Call a tool via MCP
products = await shopify_client.call_tool(
    "shopify.products.search",
    {"query": "coffee", "limit": 10}
)
```

---

## Transport Layer: SLIM Protocol

MCP clients in this project run over the **SLIM (Secure Lightweight Inter-agent Messaging)** transport protocol.

### Why SLIM for MCP?

| Feature | SLIM Benefit |
|---------|--------------|
| **Security** | TLS 1.3 encryption, mTLS authentication |
| **Low Latency** | P95 < 50ms for tool calls |
| **Reliability** | Automatic reconnection, message delivery guarantees |
| **Observability** | OpenTelemetry tracing integration |

### SLIM + MCP Configuration

```python
# Create SLIM transport with TLS
slim_transport = factory.create_slim_transport(
    endpoint="slim.agntcy.local:8443",
    tls_enabled=True,
    client_cert_path="/secrets/client.crt",
    client_key_path="/secrets/client.key"
)

# MCP client uses SLIM for external service calls
mcp_client = factory.create_mcp_client(
    agent_topic="external-service",
    transport=slim_transport
)
```

### Alternative: NATS Transport

For high-throughput scenarios, MCP clients can also run over NATS JetStream:

```python
nats_transport = factory.create_nats_transport(
    url="nats://nats.agntcy.local:4222",
    stream_name="MCP_TOOLS"
)

mcp_client = factory.create_mcp_client(
    agent_topic="high-volume-service",
    transport=nats_transport
)
```

---

## Agent Integration Patterns

### Knowledge Retrieval Agent

The Knowledge Retrieval Agent is the primary consumer of MCP capabilities:

```python
# agents/knowledge_retrieval/agent.py
class KnowledgeRetrievalAgent(BaseAgent):
    """
    Knowledge Retrieval Agent - Searches knowledge bases and external systems.

    Uses AGNTCY SDK MCP protocol for standardized tool interface.
    Integrates with:
    - Shopify API (product catalog, orders, inventory)
    - Zendesk API (previous tickets, customer history)
    - Internal documentation (FAQs, policies)
    - Azure OpenAI embeddings for semantic search (Phase 4+)
    """

    async def handle_product_query(self, msg: Message) -> Message:
        # Use MCP to call external Shopify API
        products = await self.shopify_mcp_client.call_tool(
            "shopify.products.search",
            {"query": msg.content.query, "limit": 5}
        )

        # Return via A2A to Response Generation Agent
        return create_a2a_message(
            role="assistant",
            content={"products": products},
            context_id=msg.context_id
        )
```

### Hybrid A2A + MCP Pattern

Agents maintain internal A2A communication while using MCP for external calls:

```python
class KnowledgeRetrievalAgent(BaseAgent):
    def __init__(self, factory: AgntcyFactory):
        super().__init__(factory)

        # Internal communication: A2A protocol
        self.a2a_client = factory.create_a2a_client(
            agent_topic="knowledge-retrieval"
        )

        # External integrations: MCP protocol
        self.shopify_mcp = factory.create_mcp_client(
            agent_topic="shopify-integration",
            transport=factory.create_slim_transport()
        )
        self.zendesk_mcp = factory.create_mcp_client(
            agent_topic="zendesk-integration",
            transport=factory.create_slim_transport()
        )
```

---

## Universal Commerce Protocol (UCP) via MCP

This project plans to integrate the **Universal Commerce Protocol (UCP)** using MCP bindings.

### UCP Overview

UCP is an open-source commerce standard by Google, Shopify, and 30+ partners that provides:
- Standardized commerce operations (catalog, checkout, orders)
- Protocol compatibility with MCP
- Google AI Mode integration (Gemini, Google Search AI)

### MCP Binding for UCP

```python
# shared/ucp_client.py - UCP via MCP binding
class UCPMCPClient:
    """UCP capabilities accessed via MCP tool protocol."""

    def __init__(self, mcp_client):
        self.mcp = mcp_client

    async def search_catalog(self, query: str, limit: int = 10) -> List[Product]:
        """Search product catalog via UCP Catalog capability."""
        return await self.mcp.call_tool(
            "dev.ucp.shopping.catalog.search",
            {"query": query, "limit": limit}
        )

    async def get_product_details(self, product_id: str) -> Product:
        """Get detailed product information."""
        return await self.mcp.call_tool(
            "dev.ucp.shopping.catalog.get",
            {"product_id": product_id}
        )

    async def initiate_checkout(self, cart_id: str, redirect_url: str) -> CheckoutSession:
        """Begin embedded checkout flow."""
        return await self.mcp.call_tool(
            "dev.ucp.shopping.checkout.create",
            {"cart_id": cart_id, "redirect_url": redirect_url}
        )
```

### UCP Tool Namespace

| Tool Name | Description | Phase |
|-----------|-------------|-------|
| `dev.ucp.shopping.catalog.search` | Search product catalog | Phase 4 |
| `dev.ucp.shopping.catalog.get` | Get product details | Phase 4 |
| `dev.ucp.shopping.checkout.create` | Create checkout session | Phase 4 |
| `dev.ucp.shopping.checkout.complete` | Complete transaction | Phase 5 |
| `dev.ucp.shopping.orders.status` | Get order status | Phase 4 |
| `dev.ucp.shopping.fulfillment.track` | Track shipment | Phase 5 |

---

## MCP Testing Strategy

### Testing Pyramid

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

### Unit Test Example

```python
# tests/unit/test_mcp_client.py
import pytest
from unittest.mock import AsyncMock

class TestMCPClient:
    @pytest.fixture
    def mock_transport(self):
        transport = AsyncMock()
        return transport

    @pytest.mark.asyncio
    async def test_tool_call_success(self, mock_transport):
        """Test successful MCP tool call."""
        mock_transport.call_tool.return_value = {
            "products": [{"id": "prod_123", "title": "Test Product"}]
        }

        client = MCPClient(transport=mock_transport)
        result = await client.call_tool("shopify.products.search", {"query": "test"})

        assert len(result["products"]) == 1
        mock_transport.call_tool.assert_called_once()
```

### Contract Test Example

```python
# tests/contract/test_ucp_compliance.py
class TestUCPCompliance:
    """Verify MCP tool calls comply with UCP specification."""

    def test_catalog_search_format(self):
        """Validate catalog search request format."""
        with capture_mcp_calls() as calls:
            await ucp_client.search_catalog("coffee")

        call = calls[0]
        assert call["method"] == "tools/call"
        assert call["params"]["name"] == "dev.ucp.shopping.catalog.search"
        assert "query" in call["params"]["arguments"]
```

---

## Security Considerations

### PII Tokenization

Before sending data via MCP to external services, PII must be tokenized:

```python
async def call_external_service(self, customer_data: dict) -> dict:
    # Tokenize PII before MCP call
    tokenized_data = await self.pii_tokenizer.tokenize(customer_data)

    # Make MCP tool call with tokenized data
    result = await self.mcp_client.call_tool(
        "external.service.query",
        tokenized_data
    )

    # Detokenize response if needed
    return await self.pii_tokenizer.detokenize(result)
```

### Transport Security

| Layer | Security Measure |
|-------|------------------|
| **Transport** | SLIM with TLS 1.3 encryption |
| **Authentication** | mTLS client certificates |
| **Authorization** | Azure Managed Identity |
| **Secrets** | Azure Key Vault (Phase 4+) |

### Validation

The Critic/Supervisor Agent validates all MCP tool call responses:

```python
# Validate external service response before processing
validated_response = await self.critic_agent.validate_output(
    source="mcp_shopify",
    content=raw_response
)

if not validated_response.is_safe:
    # Block harmful content from external services
    raise ContentValidationError(validated_response.reason)
```

---

## Configuration

### Agent Card Protocol Declaration

Agents declare their protocol support in their agent card:

```python
# shared/models.py
@dataclass
class AgentCard:
    name: str
    description: str
    protocol: str  # "A2A" or "MCP"
    transport: str  # "SLIM" or "NATS"
    capabilities: List[str]

# Example: Knowledge Retrieval Agent card
knowledge_agent_card = AgentCard(
    name="knowledge-retrieval",
    description="Searches knowledge bases and external APIs",
    protocol="MCP",  # Uses MCP for external integrations
    transport="SLIM",
    capabilities=["product_search", "order_lookup", "ticket_history"]
)
```

### Shopify MCP Server Configuration

For local development with Shopify:

```json
// .mcp.json
{
  "mcpServers": {
    "shopify-dev-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@shopify/dev-mcp@latest"]
    }
  }
}
```

---

## Observability

### OpenTelemetry Tracing

MCP tool calls are instrumented with OpenTelemetry spans:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def call_tool(self, tool_name: str, arguments: dict) -> dict:
    with tracer.start_as_current_span(
        f"mcp.tool.{tool_name}",
        attributes={
            "mcp.tool.name": tool_name,
            "mcp.tool.arguments": json.dumps(arguments),
            "mcp.transport": "SLIM"
        }
    ) as span:
        try:
            result = await self._transport.call_tool(tool_name, arguments)
            span.set_attribute("mcp.tool.success", True)
            return result
        except Exception as e:
            span.set_attribute("mcp.tool.success", False)
            span.set_attribute("mcp.tool.error", str(e))
            raise
```

### Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `mcp_tool_calls_total` | Total MCP tool calls | - |
| `mcp_tool_latency_ms` | Tool call latency | P95 > 500ms |
| `mcp_tool_errors_total` | Failed tool calls | Error rate > 5% |

---

## Implementation Timeline

| Phase | MCP Capabilities | Status |
|-------|------------------|--------|
| **Phase 1-5** | MCP factory method, mock clients, A2A protocol | ✅ Complete |
| **Phase 6** | Shopify MCP integration, UCP Catalog, Model Router | ⏳ Planned |
| **Phase 7** | WooCommerce MCP, Headless API, Google Gemini adapter | ⏳ Planned |
| **Phase 8** | Full UCP checkout, voice channel, in-chat transactions | ⏳ Planned |

---

## Related Documentation

- [[AGNTCY SDK Review|AGNTCY-REVIEW]] - Full SDK integration guide
- [[UCP Integration Guide|UCP-Integration-Guide]] - Universal Commerce Protocol details
- [[MCP Testing Validation|MCP-TESTING-VALIDATION-APPROACH]] - Testing strategy
- [[Architecture Requirements|architecture-requirements-phase2-5]] - System architecture

---

## External Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [AGNTCY SDK Documentation](https://github.com/agntcy/agntcy-sdk)
- [Universal Commerce Protocol](https://ucp.dev)
- [Shopify MCP Server](https://shopify.dev/docs/apps/build/storefront-mcp)

---

*Last Updated: 2026-01-28*
