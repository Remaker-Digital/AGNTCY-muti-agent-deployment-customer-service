# AGNTCY SDK Review and Integration Guide

## Executive Summary

The AGNTCY Application SDK is a Python library for building interoperable multi-agent systems with flexible transport layers. It provides a unified factory interface for creating agents that can communicate using different protocols (A2A, MCP, FastMCP) over various transport mechanisms (SLIM, NATS, HTTP).

**Version Information:**
- Current SDK Version: Available via PyPI as `agntcy-app-sdk`
- SLIM Version: 0.6.1
- Observe SDK: 1.0.24
- License: Apache 2.0
- Python Requirement: 3.12+

**Project Implementation Status:**
- **Phase 1**: 95% Complete (Infrastructure, Mock APIs, Agents, Tests)
- **Current State**: All 5 agents implemented with AGNTCY SDK integration
- **Test Coverage**: 46% (63 tests passing)
- **Remaining**: GitHub Actions CI/CD pipeline
- **Next Phase**: Phase 2 - Real NLP/LLM integration

---

## Core Architecture

### 1. **Factory Pattern**
The SDK uses a central factory class (`AgntcyFactory`) for creating all components:
- Clients (protocol implementations)
- Transports (message delivery mechanisms)
- Protocols (communication standards)
- App Sessions (multi-agent lifecycle management)

### 2. **Supported Protocols**

#### **A2A (Agent-to-Agent)**
- Purpose: Direct peer-to-peer agent communication
- Message Format: Structured with messageId, role, parts, contextId, taskId, metadata
- Use Case: Custom agent-to-agent coordination, skill invocation, task delegation
- Transport Support: SLIM ✅, NATS ✅, MQTT 🕐 (coming)

#### **MCP (Model Context Protocol)**
- Purpose: Agent-to-agent communication over abstract transports
- Decoupling: Separates protocol from transport layer
- Use Case: Standardized agent communication, integration with LLM frameworks
- Transport Support: SLIM ✅, NATS ✅

#### **FastMCP**
- Purpose: Enhanced MCP for high-performance concurrent operations
- Features: Streamable HTTP transport, optimized initialization
- Initialization: Two-phase POST request pattern (init + notification)
- Use Case: High-throughput scenarios requiring HTTP streaming

### 3. **Supported Transports**

#### **SLIM (Secure Low-Latency Interactive Messaging)**
- Version: 0.6.1
- Endpoint: `http://localhost:46357` (default dev)
- Features: Point-to-point, pub-sub, group chat messaging
- Authentication: Gateway password protection
- Use Case: Production-grade secure messaging

#### **NATS**
- Endpoint: `localhost:4222` (default)
- Features: High-performance messaging, clustering, monitoring
- Monitoring Port: 8222
- Use Case: Scalable distributed agent networks

#### **STREAMABLE_HTTP**
- Purpose: HTTP-based streaming for FastMCP
- Use Case: Web-based agent communication

#### **MQTT** 🕐
- Status: Coming soon
- Use Case: IoT and edge device agent communication

### 4. **Core Components**

#### **AgntcyFactory**
```python
factory = AgntcyFactory(
    name="AgntcyFactory",
    enable_tracing=False,  # Set True for production observability
    log_level="INFO"       # DEBUG, INFO, WARNING, ERROR, CRITICAL
)
```

**Key Methods:**
- `create_client(protocol, agent_topic, transport, **kwargs)`
- `create_transport(transport, endpoint, name, **kwargs)`
- `create_protocol(protocol)`
- `create_app_session(max_sessions=10)`
- `registered_protocols()` → ['A2A', 'MCP', 'FastMCP']
- `registered_transports()` → ['SLIM', 'NATS', 'STREAMABLE_HTTP']

#### **AppSession**
Manages multiple agent containers with lifecycle control:
```python
session = factory.create_app_session(max_sessions=10)
session.add_app_container(session_id, container)
session.start_session(session_id, keep_alive=False, push_to_directory_on_startup=False)
session.stop_session(session_id)
session.start_all_sessions()
session.stop_all_sessions()
```

#### **AppContainer**
Encapsulates complete agent service:
```python
container = AppContainer(
    server=my_server,
    transport=transport,
    directory=None,  # Coming soon
    topic="agent_topic",
    host="localhost",
    port=8000
)
container.run(keep_alive=False, push_to_directory_on_startup=False)
container.stop()
container.loop_forever()  # Handles SIGTERM/SIGINT
```

---

## Development Infrastructure

### Local Development Stack (Docker Compose)

The SDK requires the following services for local development:

#### **NATS Messaging**
```yaml
Service: nats:latest
Ports: 4222 (client), 4223, 6222 (cluster), 8222 (monitoring)
Resource: Minimal footprint
```

#### **SLIM Dataplane**
```yaml
Image: ghcr.io/agntcy/slim:0.6.1
Port: 46357
Config: /config.yaml (mounted)
Authentication: Gateway password
```

#### **ClickHouse Database**
```yaml
Image: clickhouse/clickhouse-server
Ports: 9000 (native), 8123 (HTTP)
Credentials: admin/admin
Purpose: Observability data storage
File Descriptors: 262,144
```

#### **OpenTelemetry Collector**
```yaml
Image: otel/opentelemetry-collector-contrib:latest
Ports: 4317 (gRPC), 4318 (HTTP)
Purpose: Telemetry aggregation
Depends: ClickHouse health
```

#### **Grafana Monitoring**
```yaml
Image: grafana/grafana
Port: 3001 (external) → 3000 (internal)
Plugin: ClickHouse datasource
Credentials: admin/admin
Purpose: Observability dashboards
```

**Network Requirements:**
- Bridge network named "gateway"
- Inter-service DNS resolution
- Health check mechanisms

**Storage Requirements:**
- Configuration file mounts
- Volume persistence for ClickHouse data

---

## Installation & Setup

### SDK Installation
```bash
# Production
pip install agntcy-app-sdk

# Development with uv
uv add agntcy-app-sdk

# From source
git clone https://github.com/agntcy/app-sdk
cd app-sdk
pip install -e .
```

### Start Development Services
```bash
cd services/docker
docker-compose up -d
```

### Verify Services
```bash
# NATS
curl http://localhost:8222/varz

# SLIM
curl http://localhost:46357/health  # (if endpoint exists)

# ClickHouse
curl http://localhost:8123/ping
```

---

## Message Patterns

### A2A Message Structure
```python
from agntcy_app_sdk.semantic.a2a.models import Message, Part, TextPart

message = Message(
    messageId="unique-id",
    role="user",  # or "agent"
    parts=[Part(TextPart(text="Your message content"))],
    contextId="conversation-context-id",
    taskId="task-tracking-id",
    metadata={"custom": "data"}
)
```

### Topic-Based Routing
- Agents subscribe to topics: `agent_topic="my_service"`
- Clients publish to topics: Match agent's topic
- Group communication: Multiple agents on same topic
- Broadcast: Publish to wildcard topics

### Task Management
- `InMemoryTaskStore`: Track agent operations
- Task IDs: Link related messages across agents
- Context IDs: Maintain conversation threads

---

## Integration with Customer Service Project

### Recommended Agent Architecture

Based on the AGNTCY SDK capabilities, here's how to map your agents:

#### **Intent Classification Agent**
```python
Protocol: A2A (fast routing decisions)
Transport: SLIM (security + low latency)
Topic: "intent-classifier"
Input: Customer message
Output: Route to appropriate handler agent
```

#### **Knowledge Retrieval Agent**
```python
Protocol: MCP (standardized tool interface)
Transport: SLIM
Topic: "knowledge-retrieval"
Tools: Azure Cognitive Search integration
Resources: Internal documentation, FAQs
```

#### **Response Generation Agent**
```python
Protocol: A2A (custom generation logic)
Transport: SLIM
Topic: "response-generator"
Input: Context + intent + knowledge
Output: Customer-facing response
```

#### **Escalation Agent**
```python
Protocol: A2A (decision-making logic)
Transport: SLIM
Topic: "escalation-handler"
Logic: Sentiment analysis, complexity scoring
Output: Human handoff trigger + context
```

#### **Analytics Agent**
```python
Protocol: A2A (data collection)
Transport: NATS (high-throughput pub-sub)
Topic: "analytics-collector"
Function: Passive monitoring, metrics aggregation
```

### Multi-Language Support Strategy
- Create language-specific topic subscriptions: `intent-classifier-en`, `intent-classifier-es`, `intent-classifier-fr`
- Use metadata field for language tagging: `metadata={"language": "es"}`
- Route to appropriate language-specific response generators

### Session Management
- Use `contextId` for conversation continuity
- Store conversation state in Azure Cosmos DB
- Map session IDs to AppSession containers
- Handle concurrent customer sessions via `max_sessions` configuration

---

## Observability & Monitoring

### Built-in Tracing
```python
factory = AgntcyFactory(enable_tracing=True)
# Set environment variable
os.environ['OTLP_HTTP_ENDPOINT'] = 'http://localhost:4318'
```

### Azure Integration Points
- **Application Insights**: Replace OTLP endpoint with Azure Monitor
- **Custom Metrics**: Agent performance, response times, routing accuracy
- **Log Analytics**: Centralized logging from all agents
- **Alerts**: Latency thresholds, error rates, cost anomalies

### Key Metrics to Track
- Message throughput per agent
- Inter-agent latency
- Protocol overhead (A2A vs MCP)
- Transport performance (SLIM vs NATS)
- Task completion rates
- Escalation frequency

---

## Security Considerations

### Current SDK Security
- SLIM gateway authentication (password-based)
- TLS support (configure in SLIM config)
- Environment variable protection for credentials

### Identity Service (Coming Soon)
- Token-Based Access Control (TBAC)
- Role-based permissions
- Agent authentication

### Azure Integration Security
- **Managed Identities**: Replace SLIM passwords with Azure AD
- **Key Vault**: Store SLIM gateway passwords, API keys
- **Network Isolation**: Private endpoints for agent communication
- **Encryption**: TLS 1.3 for all transport connections

### Recommended Approach for Phase 1
- Use SLIM gateway password authentication
- Store passwords in environment variables (`.env` file)
- Plan migration to Azure Managed Identities in Phase 4

---

## Scalability Patterns

### Horizontal Scaling
- Multiple AppContainer instances per agent type
- NATS clustering for transport layer
- Load balancing via topic-based routing
- Stateless agent design (state in Cosmos DB)

### Resource Management
```python
# Start with conservative limits
session = factory.create_app_session(max_sessions=10)

# Scale based on metrics
# - CPU/memory per container
# - Message queue depth
# - Response time SLAs
```

### Azure Container Instances Mapping
- Each agent type → Separate container group
- AppContainer → Container instance
- Auto-scaling: 2-10 instances per agent (from requirements)
- Health checks: Container liveness probes

---

## Development Workflow

### Phase 1: Local Development
1. Start Docker Compose services
2. Implement agents using AgntcyFactory
3. Use SLIM transport for consistency
4. Test with `pytest` (examples in SDK)
5. Validate with Grafana dashboards

### Testing Strategy
```bash
# A2A client tests
uv run pytest tests/e2e/test_a2a.py::test_client -s -k "SLIM"

# Group chat (multi-agent coordination)
uv run pytest tests/e2e/test_a2a.py::test_groupchat -s -k "SLIM"

# FastMCP (if using for specific agents)
uv run pytest tests/e2e/test_fast_mcp.py::test_client -s -k "SLIM"
```

### Phase 2-3: Business Logic Implementation
- Implement agent skills (A2A pattern)
- Create MCP tools for external integrations
- Build task workflows with contextId/taskId
- Test multi-agent conversations

### Phase 4: Azure Migration
- Replace Docker Compose with Azure Container Instances
- Replace SLIM with managed NATS or Azure Service Bus
- Integrate Azure Monitor OTLP endpoint
- Deploy containerized agents

---

## Critical Limitations & Workarounds

### Current Limitations

1. **Directory Service: Coming Soon**
   - No built-in service discovery
   - Workaround: Hardcode agent topics, use config management

2. **Identity Service: Coming Soon**
   - No built-in authentication beyond SLIM gateway
   - Workaround: Use SLIM passwords + Azure Key Vault

3. **Python 3.12+ Required**
   - Must use latest Python version
   - Docker base image: `python:3.12-slim`

4. **MQTT Transport: Coming Soon**
   - Cannot use MQTT for edge scenarios
   - Workaround: Use NATS or SLIM

### Azure Budget Constraints & Cost Optimization

**Project Budget**: $200/month for Phase 4-5 (Azure production deployment)

**Phase 1-3 Budget**: $0/month (local Docker development only)

**Phase 4-5 Estimated Costs** (Target: $180-200/month):
- Azure Container Instances (5 agents, pay-per-second): ~$60-80/month
- Cosmos DB Serverless (pay-per-request): ~$30-50/month
- Redis Cache (Basic C0, 250MB): ~$15/month
- Container Registry (Basic): ~$5/month
- Log Analytics (7-day retention): ~$10-20/month
- Application Insights: ~$10-20/month
- Bandwidth & misc: ~$10-20/month
- **Total: ~$180-200/month**

**Cost Optimization Strategies:**
- Use pay-per-use pricing (Container Instances, Cosmos Serverless)
- Auto-scale down to 1 instance per agent during idle
- 7-day log retention (not 30-day default)
- Single region deployment (East US)
- No Premium tiers (use Basic/Standard)
- Auto-shutdown during low-traffic hours (2am-6am ET)

**Phase 1-3 Approach:**
- All development local with Docker Compose (no cloud costs)
- Mock APIs eliminate external service costs
- Full stack runs on developer workstation

---

## Integration with Third-Party Services

### Shopify Integration
- Create dedicated Shopify agent
- Protocol: MCP (tools for Shopify API)
- Transport: SLIM (secure API key handling)
- Operations: Inventory queries, order status, cart management

### Zendesk Integration
- Create ticket management agent
- Protocol: A2A (custom escalation logic)
- Transport: SLIM
- Operations: Create tickets, update status, fetch history

### Mailchimp Integration
- Create email campaign agent
- Protocol: MCP (tools for Mailchimp API)
- Transport: SLIM
- Operations: Campaign triggers, list management

### Pattern
```python
# Shopify Agent
shopify_transport = factory.create_transport("SLIM", "http://localhost:46357")
shopify_agent = factory.create_client(
    "MCP",
    agent_topic="shopify-integration",
    transport=shopify_transport
)

# Register tools: get_product, check_inventory, get_order_status
```

---

## Recommended Project Structure

```
project-root/
├── agents/
│   ├── intent_classification/
│   │   ├── agent.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── knowledge_retrieval/
│   ├── response_generation/
│   ├── escalation/
│   └── analytics/
├── shared/
│   ├── factory.py          # Shared AgntcyFactory configuration
│   ├── models.py           # Common message models
│   └── utils.py
├── integrations/
│   ├── shopify_agent.py
│   ├── zendesk_agent.py
│   └── mailchimp_agent.py
├── config/
│   ├── slim/
│   │   └── server-config.yaml
│   ├── otel/
│   │   └── collector-config.yaml
│   └── agents/
│       └── agent-config.yaml
├── tests/
│   ├── unit/
│   └── e2e/
├── terraform/
│   ├── phase1_dev/         # Docker Compose equivalents
│   └── phase4_prod/        # Full Azure infrastructure
├── docker-compose.yml      # Local development stack
├── .env.example
└── requirements.txt
```

---

## Best Practices for This Project

### 1. Factory Singleton Pattern
```python
# shared/factory.py
_factory_instance = None

def get_factory(enable_tracing=False):
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = AgntcyFactory(
            name="CustomerServiceFactory",
            enable_tracing=enable_tracing,
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    return _factory_instance
```

### 2. Transport Reuse
```python
# Create transport once, share across agents
slim_transport = factory.create_transport(
    "SLIM",
    endpoint=os.getenv("SLIM_ENDPOINT", "http://localhost:46357"),
    name="customer-service-platform"
)

# Reuse for multiple agents
intent_agent = factory.create_client("A2A", "intent-classifier", slim_transport)
knowledge_agent = factory.create_client("MCP", "knowledge-retrieval", slim_transport)
```

### 3. Graceful Shutdown
```python
import signal
import sys

def signal_handler(sig, frame):
    print("Shutting down gracefully...")
    container.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

container.loop_forever()
```

### 4. Environment-Based Configuration
```python
# .env file
SLIM_ENDPOINT=http://localhost:46357
SLIM_PASSWORD=your_secure_password
NATS_ENDPOINT=localhost:4222
OTLP_ENDPOINT=http://localhost:4318
LOG_LEVEL=INFO
ENABLE_TRACING=false

# In code
from dotenv import load_dotenv
load_dotenv()
```

### 5. Error Handling
```python
try:
    client = factory.create_client("A2A", "my-agent", transport)
except Exception as e:
    logger.error(f"Failed to create client: {e}")
    # Fallback or retry logic
```

---

## KPI Tracking with AGNTCY SDK

Map project KPIs to SDK observability:

| KPI | Measurement Method | AGNTCY Feature |
|-----|-------------------|----------------|
| Response time < 2 min | Message timestamp diff | OpenTelemetry tracing |
| CSAT > 80% | User feedback metadata | Message metadata field |
| Cart abandonment < 30% | Conversion tracking | Analytics agent + taskId |
| 70%+ automation | Escalation rate | Escalation agent metrics |
| Conversion +50% | Sales funnel tracking | Analytics agent + contextId |
| Cost -40% | Infrastructure metrics | Azure Monitor integration |

---

## PyPI Release Process (SDK Updates)

If you need to fork and customize the SDK:

1. Update version in `pyproject.toml`
2. Commit to main branch
3. Create annotated tag: `git tag -a v0.x.x -m "Release v0.x.x"`
4. Push tag: `git push origin v0.x.x`
5. GitHub Actions auto-publishes to PyPI

**Note**: Only use official SDK unless you have specific customization needs.

---

## Next Steps for Integration

### Immediate Actions (Phase 1)
1. ✅ Review this document
2. Install AGNTCY SDK: `pip install agntcy-app-sdk`
3. Start Docker Compose services: `docker-compose -f services/docker/docker-compose.yaml up`
4. Create factory singleton in `shared/factory.py`
5. Implement basic Intent Classification Agent as proof of concept
6. Test with SDK's test suite patterns

### Phase 2 Preparation
1. Design agent message schemas (A2A Message format)
2. Define agent topics and routing logic
3. Create integration agent stubs (Shopify, Zendesk, Mailchimp)
4. Implement conversation state management (contextId pattern)

### Phase 4 Considerations
1. Research Azure Service Bus as SLIM alternative
2. Plan Azure Container Instance deployment
3. Configure Azure Monitor OTLP integration
4. Design managed identity authentication flow

---

## Questions to Resolve Before Implementation

1. **Budget Clarification**: Confirm actual Azure budget (free tier vs $10/month vs higher)
2. **Transport Choice**: SLIM (secure, lower throughput) vs NATS (high throughput, clustering)?
3. **Protocol Mix**: Pure A2A, pure MCP, or hybrid approach?
4. **Directory Service**: Hardcode topics or wait for directory service release?
5. **Observability**: Use built-in OTLP or integrate Azure Application Insights from start?
6. **Multi-language**: Separate agents per language or single multilingual agent?
7. **Session Management**: AppSession max_sessions value based on expected load?
8. **Testing Strategy**: Use SDK test patterns or custom test framework?

---

## Conclusion

The AGNTCY SDK provides a solid foundation for building your multi-agent customer service platform. Its protocol-transport decoupling allows flexibility in development (Docker + SLIM) vs production (Azure + NATS/Service Bus). The factory pattern simplifies agent creation, while built-in observability integration supports your KPI tracking requirements.

**Key Strengths:**
- Flexible transport options (can start with SLIM, scale with NATS)
- Protocol standardization (A2A for custom logic, MCP for tools)
- Built-in observability (OpenTelemetry compatible)
- Session management for multi-agent coordination
- Python 3.12+ modern codebase

**Key Gaps:**
- Directory and Identity services not yet available (manual configuration needed)
- Limited documentation on production deployment patterns
- No official Azure integration examples (custom implementation required)
- Budget constraints may require significant architecture modifications

**Overall Assessment:** The SDK is suitable for this project, but requires careful planning around the budget constraints and manual implementation of service discovery and authentication patterns until those features are released.
