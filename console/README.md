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
- **NEW: Azure OpenAI Mode** - Real AI responses using GPT-4o-mini with Phase 3.5 optimized prompts

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

### Option 1: Web Console (Streamlit)
```powershell
# Start the console locally
.\start-console.ps1

# Or manually with Streamlit
streamlit run console/app.py --server.port 8080
```

The console will be available at: http://localhost:8080

### Option 2: Command-Line Interface
```powershell
# Interactive console chat with Azure OpenAI
python -m evaluation.console_chat

# With debug mode (shows agent pipeline details)
python -m evaluation.console_chat --debug

# With specific context
python -m evaluation.console_chat --context product
```

### Option 3: Docker
```powershell
# Start with Docker Compose
.\start-console.ps1 -Mode docker

# Or manually
docker-compose up --build console
```

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

### Azure OpenAI Mode (Phase 3.5)

Enable **Azure OpenAI Mode** in the Chat Interface to use real AI responses:

1. Toggle "🔌 Azure OpenAI Mode" in the Chat Interface
2. Select a context type (order, return, product, billing, empty)
3. Send messages to get real GPT-4o-mini responses

**Features:**
- Full agent pipeline: Critic/Supervisor → Intent Classification → Escalation Detection → Response Generation
- Uses Phase 3.5 optimized prompts (98% intent accuracy, 88.4% response quality)
- Real-time cost and latency tracking per message
- Blocked message detection (prompt injection, jailbreaks)

**Requirements:**
```bash
# Set Azure OpenAI environment variables
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT=gpt-4o-mini
```

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
├── agntcy_integration.py  # AGNTCY system integration (mock/local mode)
├── azure_openai_mode.py   # Azure OpenAI integration (Phase 3.5 prompts)
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

### Streamlit Shows Old/Cached Content
This is a common issue where Streamlit serves cached content instead of loading updated code.

**Symptoms:**
- Code changes don't appear in the browser
- New features/toggles don't show up
- Debug statements don't execute

**Solutions:**
1. **Kill all Python processes and use a fresh port:**
   ```powershell
   # Kill any existing Streamlit/Python processes
   Get-Process python* | Stop-Process -Force -ErrorAction SilentlyContinue

   # Start on a fresh port (not the previously used port)
   streamlit run console/app.py --server.port 8085
   ```

2. **Clear browser cache:** Use Ctrl+Shift+R (hard refresh) or open in incognito/private window

3. **Clear Python cache:**
   ```powershell
   Remove-Item -Path console/__pycache__ -Recurse -Force -ErrorAction SilentlyContinue
   ```

4. **Clear Streamlit cache:**
   ```powershell
   python -m streamlit cache clear
   ```

**Root Cause:** Streamlit maintains WebSocket connections. If an old process is still running on a port, the browser may reconnect to it instead of the new process. Always ensure the old process is fully terminated before restarting.

### Azure OpenAI Mode Not Available
If the "🔌 Azure OpenAI Mode" toggle doesn't appear in Chat Interface:

1. **Check sidebar status:** Look for "🔧 Azure OpenAI Status" in the sidebar
   - If "Available: False" - check environment variables
   - If "Import Error" shown - check module installation

2. **Verify environment variables are set:**
   ```powershell
   echo $env:AZURE_OPENAI_ENDPOINT
   echo $env:AZURE_OPENAI_API_KEY
   echo $env:AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT
   ```

3. **Test Azure OpenAI connection directly:**
   ```powershell
   python -c "from console.azure_openai_mode import get_azure_mode; azure = get_azure_mode(); print(azure.initialize())"
   ```

### Azure OpenAI Responses Blocked
If messages are blocked with "Content blocked by Azure safety filter":

- This is Azure's built-in content moderation working correctly
- The filter may trigger on certain word patterns or phrases
- Rephrase the message to avoid triggering the filter
- This is defense-in-depth: Azure filter + Critic/Supervisor agent both validate content

### No Agent Responses
- Ensure AGNTCY infrastructure is running: `docker-compose up -d`
- Check SLIM connectivity: `curl http://localhost:46357/health`
- Verify agent containers are running: `docker-compose ps`

### Missing Traces/Metrics
- Confirm OpenTelemetry collector is running
- Check ClickHouse connectivity: `curl http://localhost:8123/ping`
- Verify tracing is enabled: `AGNTCY_ENABLE_TRACING=true`

### Mock API Errors
- Mock API connection errors are **expected** when Docker containers aren't running
- Azure OpenAI mode works independently without mock services
- Start mock services if needed: `docker-compose up -d mock-shopify mock-zendesk mock-mailchimp mock-google-analytics`
- Check service health: Visit http://localhost:8001/health (Shopify), etc.

## Phase 2 Integration

This console is designed to support Phase 2 implementation with:

- **Real Agent Testing**: Test actual intent classification, knowledge retrieval, response generation
- **Escalation Validation**: Verify escalation rules ($50 auto-refund, frustration detection)
- **Performance Monitoring**: Track 78% automation target and 2.5s response time goals
- **Knowledge Base Testing**: Validate coffee e-commerce knowledge base responses

The console provides the development and validation environment needed for Phase 2 story-driven development.