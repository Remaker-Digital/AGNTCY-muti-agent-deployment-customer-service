# AGNTCY Development Console

A comprehensive development and testing interface for the AGNTCY multi-agent customer service platform.

## Features

### 🏠 Dashboard
- System overview with key metrics
- Real-time activity monitoring
- Response time trends and intent distribution

### 💬 Chat Interface
- Interactive chatbot client for end-user simulation
- Test personas (Sarah, Mike, Jennifer, David) with quick message templates
- Real-time conversation with AGNTCY agents
- Escalation indicators and agent involvement tracking

### 📊 Agent Metrics
- Performance metrics for all agents (latency, success rate, cost)
- Visual charts and detailed breakdowns
- Real-time agent status monitoring

### 🔍 Trace Viewer
- Conversation trace timeline visualization
- Detailed step-by-step agent execution
- Input/output inspection and performance analysis

### ⚙️ System Status
- Service health monitoring (Mock APIs, Infrastructure)
- Docker container status
- System configuration overview

## Quick Start

### Option 1: Local Development
```powershell
# Start the console locally
.\start-console.ps1

# Or manually with Streamlit
streamlit run console/app.py --server.port 8080
```

### Option 2: Docker
```powershell
# Start with Docker Compose
.\start-console.ps1 -Mode docker

# Or manually
docker-compose up --build console
```

The console will be available at: http://localhost:8080

## Prerequisites

### For Local Development
- Python 3.8+
- Required packages: `streamlit plotly pandas requests websockets`
- AGNTCY infrastructure services running (SLIM, ClickHouse, etc.)

### For Docker
- Docker Desktop
- Docker Compose

## Integration with AGNTCY System

The console integrates with the real AGNTCY multi-agent system through:

1. **Real Agent Communication**: Uses A2A protocol to communicate with live agents
2. **OpenTelemetry Traces**: Collects real performance data from agent executions  
3. **ClickHouse Storage**: Retrieves conversation history and metrics
4. **Mock API Monitoring**: Tracks health and performance of mock services

### Fallback Behavior

If real agents are not available, the console gracefully falls back to:
- Simulated agent responses with realistic processing times
- Mock trace data for demonstration
- Estimated performance metrics

## Test Personas

The console includes 4 customer personas based on Phase 2 decisions:

### Sarah (Coffee Enthusiast)
- Knowledgeable about coffee
- Asks detailed questions about origins, processing, brewing
- Example: "What's the difference between your Ethiopian Yirgacheffe and Sidamo?"

### Mike (Convenience Seeker)  
- Wants quick, simple answers
- Focuses on practical concerns
- Example: "Where's my order?"

### Jennifer (Gift Buyer)
- Buying coffee as gifts
- Needs guidance on selections
- Example: "What's a good coffee for someone who drinks Starbucks?"

### David (Business Customer)
- Bulk orders and business needs
- Price and logistics focused
- Example: "Can we get a discount for monthly orders?"

## Architecture

```
Console App (Streamlit)
├── Chat Interface → AGNTCY Integration → Real Agents
├── Metrics Dashboard → ClickHouse/OpenTelemetry
├── Trace Viewer → OpenTelemetry Collector
└── System Status → Docker APIs + Health Checks
```

## Configuration

Environment variables for console configuration:

```bash
# AGNTCY Connection
SLIM_ENDPOINT=http://localhost:46357
SLIM_GATEWAY_PASSWORD=changeme_local_dev_password

# Observability  
OTLP_HTTP_ENDPOINT=http://localhost:4318
AGNTCY_ENABLE_TRACING=true

# Logging
LOG_LEVEL=INFO
```

## Development

### File Structure
```
console/
├── app.py                 # Main Streamlit application
├── agntcy_integration.py  # AGNTCY system integration
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── README.md             # This file
```

### Adding New Features

1. **New Dashboard Widgets**: Add to `show_dashboard()` function
2. **Additional Metrics**: Extend `get_agent_metrics()` in integration module
3. **Custom Test Scenarios**: Add to persona message templates
4. **New Trace Visualizations**: Enhance `show_trace_viewer()` function

## Troubleshooting

### Console Won't Start
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r console/requirements.txt`
- Verify port availability: `netstat -an | findstr :8080`

### No Agent Responses
- Ensure AGNTCY infrastructure is running: `docker-compose up -d`
- Check SLIM connectivity: `curl http://localhost:46357/health`
- Verify agent containers are running: `docker-compose ps`

### Missing Traces/Metrics
- Confirm OpenTelemetry collector is running
- Check ClickHouse connectivity: `curl http://localhost:8123/ping`
- Verify tracing is enabled: `AGNTCY_ENABLE_TRACING=true`

### Mock API Errors
- Start mock services: `docker-compose up -d mock-shopify mock-zendesk mock-mailchimp mock-google-analytics`
- Check service health: Visit http://localhost:8001/health (Shopify), etc.

## Phase 2 Integration

This console is designed to support Phase 2 implementation with:

- **Real Agent Testing**: Test actual intent classification, knowledge retrieval, response generation
- **Escalation Validation**: Verify escalation rules ($50 auto-refund, frustration detection)
- **Performance Monitoring**: Track 78% automation target and 2.5s response time goals
- **Knowledge Base Testing**: Validate coffee e-commerce knowledge base responses

The console provides the development and validation environment needed for Phase 2 story-driven development.