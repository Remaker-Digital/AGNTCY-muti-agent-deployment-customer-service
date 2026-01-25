# Development Console - Complete Documentation

## Overview

The AGNTCY Development Console is a Streamlit-based web application that provides interactive testing, monitoring, and debugging capabilities for the multi-agent customer service platform.

**Purpose**: Enable developers to test agents, monitor performance, and debug conversation flows during Phase 2-3 development.

**Access**: http://localhost:8080 (default)

---

## Features

### 1. Dashboard (🏠)
**Purpose**: System overview with real-time metrics and trends

**Components**:
- **Key Metrics Cards**: Total conversations, success rate, avg response time, automation rate
- **Activity Timeline**: 24-hour activity bar chart showing message volume trends
- **Intent Distribution**: Pie chart showing breakdown of customer intent types
- **Response Time Trends**: Line chart tracking average response times over time

**Data Sources**:
- Real-time: Agent responses from A2A protocol
- Historical: OpenTelemetry traces from ClickHouse

### 2. Chat Interface (💬)
**Purpose**: Interactive conversation testing with real/simulated agents

**Features**:
- **Test Personas**: 4 pre-configured customer personas with message templates
  - Sarah (Coffee Enthusiast): Technical brewing questions
  - Mike (Convenience Seeker): Quick order status queries
  - Jennifer (Gift Buyer): Product recommendations
  - David (Business Customer): Bulk orders and pricing
- **Real Agent Communication**: Sends messages via A2A protocol to live agents
- **Fallback Simulation**: Graceful degradation when agents unavailable
- **Response Tracking**: Shows processing time, confidence, escalation indicators

**Message Flow**:
```
User Input → CustomerMessage → Intent Agent → Knowledge Agent → Response Agent → Display
```

### 3. Agent Metrics (📊)
**Purpose**: Performance monitoring for all agents

**Metrics Per Agent**:
- **Latency**: Average, P95, P99 response times
- **Success Rate**: Percentage of successful message handling
- **Cost Per Request**: Estimated cost (for AI model calls)
- **Request Volume**: Total messages processed

**Visualizations**:
- Bar charts: Latency comparison across agents
- Pie charts: Cost distribution by agent
- Tables: Detailed metrics breakdown

**Data Source**: OpenTelemetry metrics from ClickHouse

### 4. Trace Viewer (🔍)
**Purpose**: Debug conversation flows step-by-step

**Features**:
- **Session Selection**: Choose conversation by session ID
- **Timeline Visualization**: Plotly timeline showing agent execution sequence
- **Step Details**: Expand each step to see inputs, outputs, metadata
- **Performance Analysis**: View latency and cost per step

**Trace Format**:
```
Session: conv-abc123
├── Step 1: Intent Classification (25ms)
│   ├── Input: "Where is my order?"
│   ├── Output: {intent: ORDER_STATUS, confidence: 0.95}
│   └── Metadata: {agent: intent-classifier, model: rule-based}
├── Step 2: Knowledge Retrieval (150ms)
│   ├── Input: {query: "order lookup", order_number: "10234"}
│   ├── Output: {order: {...}, tracking: {...}}
│   └── Metadata: {agent: knowledge-retrieval, source: shopify}
└── Step 3: Response Generation (75ms)
    ├── Input: {intent: ORDER_STATUS, knowledge: [...]}
    ├── Output: "Hi Sarah, your order #10234 is in transit..."
    └── Metadata: {agent: response-generator, template: order_status}
```

### 5. System Status (⚙️)
**Purpose**: Monitor infrastructure health

**Components**:
- **Mock API Status**: Health checks for Shopify, Zendesk, Mailchimp, Google Analytics
- **Infrastructure Services**: SLIM, NATS, ClickHouse, OTel Collector, Grafana status
- **Agent Containers**: Docker container status for all 5 agents
- **Configuration Display**: Environment variables and endpoints

**Health Check Endpoints**:
- Shopify: http://localhost:8001/health
- Zendesk: http://localhost:8002/health
- Mailchimp: http://localhost:8003/health
- Google Analytics: http://localhost:8004/health
- SLIM: http://localhost:46357/health
- ClickHouse: http://localhost:8123/ping

---

## Installation & Usage

### Quick Start (PowerShell)

```powershell
# Start console locally (recommended for development)
.\start-console.ps1

# Start console with Docker
.\start-console.ps1 -Mode docker
```

### Manual Start (Local)

```powershell
# Install dependencies
pip install -r console/requirements.txt

# Start Streamlit
streamlit run console/app.py --server.port 8080
```

### Manual Start (Docker)

```bash
# Build and start console service
docker-compose up --build console

# Or start all services including console
docker-compose up -d
```

---

## Configuration

### Environment Variables

**AGNTCY Connection**:
- `SLIM_ENDPOINT` - SLIM server URL (default: http://slim:46357 in Docker, http://localhost:46357 local)
- `SLIM_GATEWAY_PASSWORD` - SLIM authentication password (default: changeme_local_dev_password)

**Observability**:
- `OTLP_HTTP_ENDPOINT` - OpenTelemetry collector endpoint (default: http://otel-collector:4318 in Docker)
- `AGNTCY_ENABLE_TRACING` - Enable trace collection (default: true)

**Logging**:
- `LOG_LEVEL` - Logging verbosity (default: INFO, options: DEBUG, INFO, WARNING, ERROR)

### Docker Compose Service

```yaml
console:
  build:
    context: .
    dockerfile: console/Dockerfile
  container_name: agntcy-console
  ports:
    - "8080:8080"
  networks:
    - agntcy-network
  environment:
    - SLIM_ENDPOINT=http://slim:46357
    - SLIM_GATEWAY_PASSWORD=${SLIM_GATEWAY_PASSWORD:-changeme_local_dev_password}
    - OTLP_HTTP_ENDPOINT=http://otel-collector:4318
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
    - AGNTCY_ENABLE_TRACING=${AGNTCY_ENABLE_TRACING:-true}
  volumes:
    - ./shared:/app/shared:ro
    - ./docs:/app/docs:ro
    - ./test-data:/app/test-data:ro
  depends_on:
    - slim
    - otel-collector
    - mock-shopify
    - mock-zendesk
    - mock-mailchimp
    - mock-google-analytics
  restart: unless-stopped
```

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  Development Console (Streamlit)            │
│                     http://localhost:8080                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Dashboard  │  Chat  │  Metrics  │  Traces  │  Status      │
│  ─────────────────────────────────────────────────────────  │
│                           │                                  │
│                           ▼                                  │
│               ┌─────────────────────┐                        │
│               │ AGNTCY Integration  │                        │
│               │   (agntcy_integration.py)                    │
│               └─────────────────────┘                        │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│    SLIM     │   │ ClickHouse  │   │   Docker    │
│  (A2A Msgs) │   │  (Metrics)  │   │    APIs     │
│             │   │             │   │             │
│ :46357      │   │ :9000/:8123 │   │ Container   │
└──────┬──────┘   └─────────────┘   │   Status    │
       │                              └─────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Multi-Agent System              │
├─────────────────────────────────────────┤
│ Intent → Knowledge → Response           │
│ Escalation → Analytics                  │
└─────────────────────────────────────────┘
```

### Data Flow

**Chat Message Flow**:
1. User types message in Chat Interface
2. Console creates `CustomerMessage` object
3. A2A protocol wrapper sends to `intent-classifier` topic
4. Intent Agent processes → routes to Knowledge Agent
5. Knowledge Agent fetches data → sends to Response Agent
6. Response Agent generates reply → returns to console
7. Console displays response with metadata (time, confidence, escalation)

**Metrics Collection Flow**:
1. Agents emit OpenTelemetry traces during execution
2. OTel Collector aggregates and sends to ClickHouse
3. Console queries ClickHouse for metrics
4. Metrics displayed in Dashboard and Agent Metrics pages

**Fallback Flow** (when agents unavailable):
1. A2A message send times out (or SLIM unreachable)
2. Console catches exception
3. Simulated response generated with realistic delay
4. Mock trace data created for debugging
5. Warning displayed to user about simulation mode

---

## Integration Points

### 1. SLIM / A2A Protocol
**Purpose**: Real-time agent communication

**Integration**:
- Uses `shared/factory.py` to create SLIM transport
- Creates A2A messages via `shared/utils.py`
- Sends to agent topics: `intent-classifier`, `knowledge-retrieval`, `response-generator-en`

**Fallback**: Simulated responses when SLIM unavailable

### 2. OpenTelemetry / ClickHouse
**Purpose**: Trace collection and metrics storage

**Integration**:
- Queries ClickHouse `otel_traces` table for conversation traces
- Queries `otel_metrics` table for agent performance metrics
- Parses OpenTelemetry span data to reconstruct conversation flows

**Fallback**: Mock trace data for demonstration

### 3. Docker API
**Purpose**: Container status monitoring

**Integration**:
- Uses Docker Python SDK to query container status
- Checks running/stopped state of all services
- Displays container health in System Status page

**Fallback**: Displays "Docker unavailable" if API unreachable

### 4. Mock API Health Checks
**Purpose**: Validate mock services are responding

**Integration**:
- HTTP GET requests to `/health` endpoint of each mock API
- Checks response time and status code
- Displays in System Status page

**Fallback**: Shows "Unhealthy" status with error details

---

## Testing Scenarios

### Phase 2 Test Scenarios

**Scenario 1: Order Status Inquiry (Issue #24)**
1. Select persona: Mike (Convenience Seeker)
2. Send: "Where is my order #10234?"
3. Expected: Intent=ORDER_STATUS, Shopify lookup, tracking details in response
4. Verify: Response < 500ms, includes tracking number and ETA

**Scenario 2: Return Request - Auto-Approval (Issue #29)**
1. Select persona: Sarah (Coffee Enthusiast)
2. Send: "I want to return order #10125"
3. Expected: Intent=RETURN_REQUEST, Order total $30.22, auto-approved
4. Verify: Response includes RMA number, escalation=False

**Scenario 3: Return Request - Escalation (Issue #29)**
1. Select persona: David (Business Customer)
2. Send: "I need to return order #10234"
3. Expected: Intent=RETURN_REQUEST, Order total $86.37, escalated
4. Verify: Response mentions support team, escalation=True

**Scenario 4: Product Information (Issue #25)**
1. Select persona: Jennifer (Gift Buyer)
2. Send: "Tell me about your coffee pods"
3. Expected: Intent=PRODUCT_INFO or GENERAL_INQUIRY, products found
4. Verify: Response lists multiple coffee pod products with prices

---

## Troubleshooting

### Console Won't Start

**Symptom**: Error when running `.\start-console.ps1`

**Solutions**:
1. Check Python version: `python --version` (need 3.8+)
2. Install dependencies: `pip install -r console/requirements.txt`
3. Check port 8080: `netstat -an | findstr :8080` (Windows) or `lsof -i :8080` (Linux/Mac)
4. Try different port: `streamlit run console/app.py --server.port 8081`

### No Agent Responses / Timeout Errors

**Symptom**: "Timeout waiting for agent response" or "SLIM connection failed"

**Solutions**:
1. Start AGNTCY infrastructure: `docker-compose up -d`
2. Check SLIM running: `docker ps --filter name=slim`
3. Test SLIM connectivity: `curl http://localhost:46357/health`
4. Check agent containers: `docker-compose ps | grep agent`
5. View agent logs: `docker-compose logs agent-intent-classification`

### Missing Traces / Empty Metrics

**Symptom**: Trace Viewer shows "No traces found" or Agent Metrics are all zero

**Solutions**:
1. Verify OpenTelemetry Collector: `docker ps --filter name=otel-collector`
2. Check OTel Collector logs: `docker logs agntcy-otel-collector`
3. Test ClickHouse: `curl http://localhost:8123/ping`
4. Query traces manually:
   ```sql
   -- Connect to ClickHouse
   docker exec -it agntcy-clickhouse clickhouse-client

   -- Check if otel database exists
   SHOW DATABASES;

   -- Query traces
   SELECT * FROM otel.otel_traces LIMIT 10;
   ```
5. Enable tracing: Set `AGNTCY_ENABLE_TRACING=true` in environment

### Mock API Health Checks Fail

**Symptom**: System Status shows mock APIs as "Unhealthy"

**Solutions**:
1. Start mock services: `docker-compose up -d mock-shopify mock-zendesk mock-mailchimp mock-google-analytics`
2. Check container status: `docker ps --filter name=mock`
3. Test endpoints manually:
   - Shopify: `curl http://localhost:8001/health`
   - Zendesk: `curl http://localhost:8002/health`
   - Mailchimp: `curl http://localhost:8003/health`
   - Google Analytics: `curl http://localhost:8004/health`
4. View logs: `docker logs agntcy-mock-shopify`
5. Rebuild containers: `docker-compose build mock-shopify && docker-compose up -d mock-shopify`

### Simulation Mode (Not Using Real Agents)

**Symptom**: Warning message "Running in simulation mode" displayed

**Explanation**: This is intentional fallback behavior when real agents unavailable

**To Enable Real Agents**:
1. Ensure AGNTCY SDK installed: `pip install agntcy-app-sdk`
2. Start SLIM and agents: `docker-compose up -d slim agent-intent-classification agent-knowledge-retrieval agent-response-generation`
3. Verify SLIM connection in console logs
4. Restart console: `.\start-console.ps1`

---

## Development Guide

### File Structure

```
console/
├── app.py                  # Main Streamlit application (500+ lines)
│                          # Contains: UI layout, page routing, widget rendering
│
├── agntcy_integration.py  # AGNTCY system integration (600+ lines)
│                          # Contains: A2A client, trace queries, metrics collection
│
├── requirements.txt       # Python dependencies
│                          # streamlit, plotly, pandas, requests, docker
│
├── Dockerfile            # Container configuration
│                          # Multi-stage build, production-ready
│
├── README.md             # User-facing documentation
│
└── .streamlit/           # Streamlit configuration
    └── config.toml       # Theme, server settings
```

### Adding New Features

**Add Dashboard Widget**:
1. Edit `console/app.py` → `show_dashboard()` function
2. Use Streamlit columns: `col1, col2 = st.columns(2)`
3. Add metric: `col1.metric("Label", value, delta)`
4. Add chart: `col2.plotly_chart(fig, use_container_width=True)`

**Add Agent Metric**:
1. Edit `console/agntcy_integration.py` → `get_agent_metrics()` method
2. Query ClickHouse for new metric
3. Parse and return in metrics dictionary
4. Display in `console/app.py` → `show_agent_metrics()` function

**Add Test Persona**:
1. Edit `console/app.py` → `get_persona_details()` function
2. Add new persona with: name, description, quick messages, background
3. Persona automatically appears in Chat Interface dropdown

**Add Trace Visualization**:
1. Edit `console/app.py` → `show_trace_viewer()` function
2. Create Plotly figure with timeline/chart
3. Parse trace data from `agntcy_integration.get_conversation_traces()`
4. Render with `st.plotly_chart()` or custom HTML/CSS

### Code Style Guidelines

- **Streamlit UI**: Use descriptive widget labels, help text for clarity
- **Error Handling**: Always use try/except, show user-friendly error messages
- **Logging**: Use `console.logger.info()` for audit trail
- **Type Hints**: Add type annotations for public functions
- **Comments**: Explain "why" not "what", reference docs/issues

---

## Phase 2-5 Roadmap

### Phase 2: Business Logic Implementation ✅ (Current)
- ✅ Console operational with 5 pages
- ✅ Test personas defined and implemented
- ✅ Real agent integration via A2A protocol
- ✅ Graceful fallback to simulation mode
- ⏳ Additional test scenarios (ongoing)

### Phase 3: Testing & Validation
- Add automated test scenario execution
- Performance benchmarking dashboard
- Load testing integration (Locust metrics)
- Regression test tracking

### Phase 4: Production Deployment
- Azure deployment readiness
- Multi-language support (EN, FR-CA, ES)
- Production metrics integration (Azure Monitor)
- Real API health checks (Shopify, Zendesk)

### Phase 5: Go-Live
- Production monitoring dashboard
- Alert configuration UI
- Cost tracking and optimization metrics
- Disaster recovery test execution UI

---

## References

### Internal Documentation
- Implementation Summary: `CONSOLE-IMPLEMENTATION-SUMMARY.md`
- Phase 2 Readiness: `PHASE-2-READINESS.md`
- Project Guidance: `CLAUDE.md`
- User Stories: `user-stories-phased.md`

### External References
- Streamlit Documentation: https://docs.streamlit.io
- Plotly Documentation: https://plotly.com/python/
- AGNTCY SDK: (internal)
- OpenTelemetry: https://opentelemetry.io/docs/

---

**Document Owner**: Development Team
**Last Updated**: 2026-01-24
**Status**: Phase 2 - Operational
**Access**: http://localhost:8080
