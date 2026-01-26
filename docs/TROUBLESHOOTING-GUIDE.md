# Troubleshooting Guide - Multi-Agent Customer Service Platform

**Version**: 1.0
**Last Updated**: January 25, 2026
**Phase**: Phase 3 - Testing & Validation
**Status**: Active

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Environment Issues](#environment-issues)
3. [Docker Service Issues](#docker-service-issues)
4. [Test Execution Issues](#test-execution-issues)
5. [Agent Communication Issues](#agent-communication-issues)
6. [Performance Issues](#performance-issues)
7. [Integration Test Issues](#integration-test-issues)
8. [Load & Stress Test Issues](#load--stress-test-issues)
9. [CI/CD Issues](#cicd-issues)
10. [Phase-Specific Issues](#phase-specific-issues)

---

## Quick Diagnostics

### System Health Check

Run this diagnostic script to quickly identify common issues:

```bash
#!/bin/bash
# health-check.sh

echo "=== MULTI-AGENT CUSTOMER SERVICE - HEALTH CHECK ==="
echo ""

# Python version
echo "Python version:"
python --version
echo ""

# Docker status
echo "Docker services:"
docker compose ps
echo ""

# SLIM service health
echo "SLIM service health:"
curl -s http://localhost:8080/health || echo "SLIM service not reachable"
echo ""

# Mock API health
echo "Mock Shopify health:"
curl -s http://localhost:5001/health || echo "Mock Shopify not reachable"
echo ""

echo "Mock Zendesk health:"
curl -s http://localhost:5002/health || echo "Mock Zendesk not reachable"
echo ""

echo "Mock Mailchimp health:"
curl -s http://localhost:5003/health || echo "Mock Mailchimp not reachable"
echo ""

echo "Mock Analytics health:"
curl -s http://localhost:5004/health || echo "Mock Analytics not reachable"
echo ""

# Test execution
echo "Quick test:"
pytest tests/unit/test_models.py::test_customer_message_creation -v
echo ""

echo "=== HEALTH CHECK COMPLETE ==="
```

### Quick Fixes

**Most common issues** (in order of frequency):

1. **Docker services not running**
   ```bash
   docker compose up -d
   sleep 10
   ```

2. **Missing dependencies**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov pytest-asyncio psutil locust
   ```

3. **Environment variables not set**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

4. **Port conflicts**
   ```bash
   # Check what's using port 8080
   netstat -an | findstr :8080  # Windows
   lsof -i :8080  # macOS/Linux

   # Kill process or change port in .env
   ```

5. **Stale Docker containers**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

---

## Environment Issues

### Issue: Python Version Mismatch

**Error**:
```
ERROR: This package requires Python 3.12 or higher
```

**Cause**: AGNTCY SDK requires Python 3.12+

**Solution**:
```bash
# Check Python version
python --version

# Install Python 3.14 (recommended)
# Windows: https://www.python.org/downloads/
# macOS: brew install python@3.14
# Linux: sudo apt install python3.14

# Verify installation
python3.14 --version

# Create virtual environment
python3.14 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows
```

### Issue: Missing Dependencies

**Error**:
```
ModuleNotFoundError: No module named 'agntcy_app_sdk'
ModuleNotFoundError: No module named 'pytest'
```

**Cause**: Dependencies not installed

**Solution**:
```bash
# Install all dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio psutil locust pyyaml

# Verify installation
pip list | grep agntcy
pip list | grep pytest
```

### Issue: Environment Variables Not Loaded

**Error**:
```
KeyError: 'SLIM_ENDPOINT'
ValueError: SLIM_ENDPOINT not set
```

**Cause**: `.env` file missing or not loaded

**Solution**:
```bash
# Create .env from example
cp .env.example .env

# Edit .env with correct values
# Verify .env exists
ls -la .env  # macOS/Linux
dir .env  # Windows

# Load .env manually (if needed)
export $(cat .env | xargs)  # macOS/Linux
# Windows: Set each variable manually in PowerShell
```

**Example `.env`**:
```bash
SLIM_ENDPOINT=http://localhost:8080
SHOPIFY_API_URL=http://localhost:5001
ZENDESK_API_URL=http://localhost:5002
MAILCHIMP_API_URL=http://localhost:5003
ANALYTICS_API_URL=http://localhost:5004
AGENT_LOG_LEVEL=INFO
AGENT_TIMEOUT=30
```

---

## Docker Service Issues

### Issue: Docker Services Not Starting

**Error**:
```
ERROR: Cannot connect to the Docker daemon
ERROR: docker-compose command not found
```

**Cause**: Docker Desktop not running or not installed

**Solution**:
```bash
# Start Docker Desktop (GUI application)
# Windows: Start Menu → Docker Desktop
# macOS: Applications → Docker

# Verify Docker running
docker --version
docker compose version

# If not installed, download from:
# https://www.docker.com/products/docker-desktop
```

### Issue: SLIM Service Not Reachable

**Error**:
```
requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
curl: (7) Failed to connect to localhost port 8080
```

**Cause**: SLIM service container not running or not healthy

**Diagnosis**:
```bash
# Check if container running
docker compose ps

# Expected output:
# NAME           STATUS    PORTS
# slim-service   Up        0.0.0.0:8080->8080/tcp

# If not running, check logs
docker logs slim-service

# Common log errors:
# - "Address already in use" → Port 8080 conflict
# - "No such file or directory" → Volume mount issue
# - "Permission denied" → File permissions issue
```

**Solution**:
```bash
# Restart SLIM service
docker compose restart slim-service

# If still failing, rebuild
docker compose down
docker compose up -d --build slim-service

# Wait for service to be ready
sleep 10
curl http://localhost:8080/health
```

### Issue: SLIM Configuration Schema Error

**Error**:
```
thread 'main' panicked at core/slim/src/bin/main.rs:27:55:
failed to load configuration: InvalidKey("server")
```

**Cause**: SLIM v0.6.1 uses a specific configuration schema. Common mistakes:
- Using `server:` as top-level key (invalid)
- Including `http://` scheme in endpoint (invalid)

**Solution**: Use the correct SLIM configuration schema:

```yaml
# config/slim/server-config.yaml - CORRECT FORMAT

tracing:
  log_level: info
  display_thread_names: true
  display_thread_ids: true

runtime:
  n_cores: 0  # 0 = auto-detect
  thread_name: "slim-data-plane"
  drain_timeout: 10s

services:
  slim/1:
    dataplane:
      servers:
        - endpoint: "0.0.0.0:46357"  # NO http:// prefix!
          tls:
            insecure: true
      clients: []
```

**Common Mistakes**:
```yaml
# WRONG - "server:" is not a valid key
server:
  host: 0.0.0.0
  port: 46357

# WRONG - don't include http:// in endpoint
endpoint: "http://0.0.0.0:46357"

# CORRECT - just host:port
endpoint: "0.0.0.0:46357"
```

**Reference**: See [SLIM-CONFIGURATION-ISSUE.md](./SLIM-CONFIGURATION-ISSUE.md) for full details.

---

### Issue: Mock API Services Not Responding

**Error**:
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=5001)
```

**Cause**: Mock API container not running

**Diagnosis**:
```bash
# Check which mock services are running
docker compose ps | grep mock

# Expected:
# mock-shopify     Up   0.0.0.0:5001->5001/tcp
# mock-zendesk     Up   0.0.0.0:5002->5002/tcp
# mock-mailchimp   Up   0.0.0.0:5003->5003/tcp
# mock-analytics   Up   0.0.0.0:5004->5004/tcp

# Check individual service logs
docker logs mock-shopify
docker logs mock-zendesk
```

**Solution**:
```bash
# Restart all mock services
docker compose restart mock-shopify mock-zendesk mock-mailchimp mock-analytics

# Or rebuild specific service
docker compose up -d --build mock-shopify

# Verify health endpoints
curl http://localhost:5001/health  # Shopify
curl http://localhost:5002/health  # Zendesk
curl http://localhost:5003/health  # Mailchimp
curl http://localhost:5004/health  # Analytics
```

### Issue: Port Already in Use

**Error**:
```
ERROR: for slim-service  Cannot start service slim-service: driver failed programming external connectivity on endpoint slim-service: Bind for 0.0.0.0:8080 failed: port is already allocated
```

**Cause**: Another process using the port

**Diagnosis**:
```bash
# Windows
netstat -an | findstr :8080
netstat -an | findstr :5001

# macOS/Linux
lsof -i :8080
lsof -i :5001
```

**Solution**:
```bash
# Option 1: Kill process using the port
# Windows: Find PID from netstat, then:
taskkill /PID <PID> /F

# macOS/Linux:
kill -9 <PID>

# Option 2: Change port in docker-compose.yml
# Edit docker-compose.yml:
# ports:
#   - "8081:8080"  # Changed external port to 8081

# Then update .env:
# SLIM_ENDPOINT=http://localhost:8081
```

### Issue: Docker Compose File Not Found

**Error**:
```
ERROR: Can't find a suitable configuration file in this directory or any parent
```

**Cause**: Running `docker compose` command from wrong directory

**Solution**:
```bash
# Navigate to project root
cd /path/to/AGNTCY-muti-agent-deployment-customer-service

# Verify docker-compose.yml exists
ls docker-compose.yml

# Run command from project root
docker compose up -d
```

---

## Test Execution Issues

### Issue: Pytest Not Found

**Error**:
```
'pytest' is not recognized as an internal or external command
pytest: command not found
```

**Cause**: Pytest not installed or not in PATH

**Solution**:
```bash
# Install pytest
pip install pytest pytest-cov pytest-asyncio

# Verify installation
pytest --version

# If still not found, use module syntax
python -m pytest tests/unit/ -v
```

### Issue: Import Errors in Tests

**Error**:
```
ImportError: cannot import name 'CustomerMessage' from 'shared.models'
ModuleNotFoundError: No module named 'shared'
```

**Cause**: Python path not configured or project not installed

**Solution**:
```bash
# Option 1: Install project in editable mode
pip install -e .

# Option 2: Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # macOS/Linux
set PYTHONPATH=%PYTHONPATH%;%CD%  # Windows CMD
$env:PYTHONPATH += ";$(Get-Location)"  # Windows PowerShell

# Option 3: Run from project root
cd /path/to/AGNTCY-muti-agent-deployment-customer-service
pytest tests/unit/ -v
```

### Issue: Async Test Warnings

**Error**:
```
PytestUnraisableExceptionWarning: Exception ignored in: <coroutine object test_intent_classification at 0x...>
RuntimeWarning: coroutine 'test_intent_classification' was never awaited
```

**Cause**: Missing `pytest-asyncio` or missing `@pytest.mark.asyncio` decorator

**Solution**:
```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Add decorator to async tests
@pytest.mark.asyncio
async def test_intent_classification():
    result = await agent.handle_message(msg)
    assert result is not None
```

### Issue: Test Discovery Issues

**Error**:
```
ERROR: not found: /path/to/test_file.py::test_function
collected 0 items
```

**Cause**: Test file or function doesn't match pytest naming conventions

**Solution**:
```bash
# Pytest discovers tests matching these patterns:
# - Files: test_*.py or *_test.py
# - Functions: test_*
# - Classes: Test*

# Correct naming:
# tests/unit/test_models.py  ✓
# tests/unit/models_test.py  ✓
# tests/unit/test.py         ✗ (too generic)

# Run pytest with verbose discovery
pytest tests/ -v --collect-only
```

---

## Agent Communication Issues

### Issue: Agent Timeout

**Error**:
```
asyncio.TimeoutError: Agent did not respond within 30 seconds
TimeoutError: Waiting for response from agent 'intent-classifier' timed out
```

**Cause**: Agent not registered, SLIM service down, or agent hung

**Diagnosis**:
```bash
# Check SLIM service
curl http://localhost:8080/health

# Check agent logs (if running in containers)
docker logs intent-classification-agent
docker logs knowledge-retrieval-agent

# Check if agents registered with SLIM
# (SLIM should maintain agent registry)
```

**Solution**:
```bash
# Increase timeout in .env
AGENT_TIMEOUT=60  # Increase from 30 to 60 seconds

# Restart SLIM service
docker compose restart slim-service

# Or debug agent registration
# Add logging to agent code:
logger.info(f"Agent {self.name} registered with SLIM")
```

### Issue: Message Routing Failures

**Error**:
```
ValueError: No route found for topic 'intent-classifier'
KeyError: 'intent-classifier' not in agent registry
```

**Cause**: Agent topic mismatch or agent not started

**Diagnosis**:
```python
# Check agent topic registration
# In agent code:
factory.create_a2a_agent(
    name="intent-classifier",  # Must match topic
    handler=self.handle_message
)

# Sending message:
msg.topic = "intent-classifier"  # Must match agent name
```

**Solution**:
```python
# Ensure topic consistency
AGENT_TOPICS = {
    'intent': 'intent-classifier',
    'knowledge': 'knowledge-retrieval',
    'response': 'response-generator-en',
    'escalation': 'escalation-handler',
    'analytics': 'analytics-processor'
}

# Use constants instead of hardcoded strings
msg.topic = AGENT_TOPICS['intent']
```

### Issue: A2A Message Format Errors

**Error**:
```
ValueError: Invalid message format: missing 'role' field
KeyError: 'content'
```

**Cause**: Message doesn't conform to A2A protocol

**Solution**:
```python
# Use helper function to create A2A messages
from shared.utils import create_a2a_message

# Correct format
msg = create_a2a_message(
    role="user",  # or "assistant", "system"
    content={"message": "Hello"},  # Dictionary
    context_id="ctx-001"  # Required for threading
)

# Incorrect format (missing fields)
msg = {
    "content": "Hello"  # Missing 'role', 'context_id'
}
```

---

## Performance Issues

### Issue: Slow Test Execution

**Symptom**: Tests take >5 minutes to run

**Diagnosis**:
```bash
# Profile test execution
pytest tests/ -v --durations=10

# Shows 10 slowest tests
# Example output:
# 3.45s call    tests/e2e/test_scenarios.py::test_S001
# 2.31s call    tests/integration/test_intent_agent.py::test_intent_classification
```

**Solution**:
```bash
# Run only fast tests
pytest tests/unit/ -v  # Fast (~1s total)

# Skip slow tests
pytest tests/ -v -m "not slow"

# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest tests/ -v -n auto  # Auto-detect CPU count
```

### Issue: High Memory Usage During Tests

**Symptom**: Tests consume >2GB RAM, system becomes slow

**Diagnosis**:
```python
# Add memory profiling
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

**Solution**:
```python
# Close resources after tests
@pytest.fixture
async def agents():
    # Create agents
    agents = create_all_agents()
    yield agents

    # Cleanup
    for agent in agents.values():
        await agent.shutdown()

# Run garbage collection between tests
import gc
gc.collect()
```

### Issue: Performance Regression

**Symptom**: Tests that used to pass P95 < 2000ms now fail

**Diagnosis**:
```bash
# Compare current results with baseline
pytest tests/performance/ -v > current_results.txt
diff current_results.txt docs/PHASE-3-DAY-6-7-SUMMARY.md

# Check for changes in code
git diff main -- agents/
```

**Solution**:
```bash
# Profile agent code
import cProfile
cProfile.run('agent.handle_message(msg)')

# Identify bottlenecks
# - Database queries
# - External API calls
# - Complex computations

# Optimize identified bottlenecks
# - Add caching
# - Reduce query complexity
# - Parallelize operations
```

---

## Integration Test Issues

### Issue: Integration Tests Fail with "Connection Refused"

**Error**:
```
requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=5001): Max retries exceeded
ConnectionRefusedError: [Errno 61] Connection refused
```

**Cause**: Mock API services not running

**Solution**:
```bash
# Start Docker services before running integration tests
docker compose up -d
sleep 10  # Wait for services to initialize

# Run integration tests
pytest tests/integration/ -v

# Stop services after tests
docker compose down
```

### Issue: Mock API Returns Unexpected Data

**Error**:
```
AssertionError: assert 'shipped' in 'mock response'
KeyError: 'order_id'
```

**Cause**: Mock API fixture data incorrect or missing

**Diagnosis**:
```bash
# Check mock API directly
curl http://localhost:5001/api/orders/ORD-2024-001

# Expected response:
# {
#   "order_id": "ORD-2024-001",
#   "status": "shipped",
#   "customer": {...}
# }
```

**Solution**:
```bash
# Update mock API fixtures
# File: test-data/shopify/orders.json
# Add or fix order data

# Restart mock service to load new data
docker compose restart mock-shopify

# Verify fixture loaded
curl http://localhost:5001/api/orders/ORD-2024-001
```

### Issue: Docker Network Hostname Resolution Failures

**Error**:
```
socket.gaierror: [Errno -2] Name or service not known: 'mock-shopify'
requests.exceptions.ConnectionError: HTTPConnectionPool(host='mock-shopify', port=5001)
```

**Cause**: Docker DNS resolution failing (known Phase 3 issue)

**Workaround**:
```python
# In agent code, use localhost instead of container name
# Phase 3 (localhost):
SHOPIFY_API_URL = "http://localhost:5001"

# Phase 4 (container name):
SHOPIFY_API_URL = "http://mock-shopify:5001"

# Or use environment variable
import os
SHOPIFY_API_URL = os.getenv("SHOPIFY_API_URL", "http://localhost:5001")
```

**Note**: This is a known limitation in Phase 3. Phase 4 will use Azure Container Instances with proper service discovery.

---

## Load & Stress Test Issues

### Issue: Locust Requires HTTP Endpoint

**Error**:
```
locust.exception.StopTest: You must specify the base host. Either in the host attribute in the User class, or on the command line using the --host option.
```

**Cause**: Locust is HTTP-based, Phase 3 has no HTTP endpoints

**Solution**:
```bash
# Use custom Python load tester instead
python tests/load/load_test.py

# Locust will be used in Phase 4 when HTTP endpoints available
# locustfile.py is prepared for future use
```

### Issue: Load Tests Show 0 Requests

**Symptom**: Load test completes but shows 0 total requests

**Diagnosis**:
```bash
# Check if agents are running
docker compose ps

# Check load test logs
python tests/load/load_test.py > load_test.log 2>&1
cat load_test.log
```

**Solution**:
```python
# Ensure agents properly initialized
# In load_test.py:
load_tester = LoadTester()
await load_tester.setup()  # Must call setup()

# Run tests
results = await load_tester.run_concurrent_users(num_users=10)
```

### Issue: Stress Tests Cause System Freeze

**Symptom**: System becomes unresponsive during 1000-user stress test

**Cause**: Insufficient system resources

**Solution**:
```bash
# Reduce concurrent user count
# Edit tests/stress/stress_test.py:
# MAX_USERS = 500  # Reduce from 1000

# Or run stress tests on dedicated hardware
# Close other applications
# Monitor system resources:
# - Task Manager (Windows)
# - Activity Monitor (macOS)
# - htop (Linux)
```

### Issue: Unicode Encoding Errors in Test Output

**Error**:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position X
```

**Cause**: Windows console doesn't support Unicode arrows/emojis

**Solution**:
```python
# Replace Unicode characters with ASCII
# Change: "10 → 100 → 500"
# To: "10 -> 100 -> 500"

# Remove emojis
# Change: "🚀 Starting test"
# To: "Starting test"

# This fix is already applied in stress_test.py and locustfile.py
```

---

## CI/CD Issues

### Issue: GitHub Actions Workflow Fails

**Error**:
```
Error: Process completed with exit code 1
Error: Unable to locate executable file: pytest
```

**Cause**: Workflow YAML syntax error or missing dependencies

**Diagnosis**:
```bash
# Validate YAML locally
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"

# Check workflow on GitHub
# Go to Actions tab → Select failed workflow → View logs
```

**Solution**:
```yaml
# Ensure dependencies installed in workflow
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install pytest pytest-cov pytest-asyncio
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
```

### Issue: Docker Services Not Starting in CI

**Error**:
```
Error: Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Cause**: Docker not available in GitHub Actions runner

**Solution**:
```yaml
# GitHub Actions runners have Docker pre-installed
# Use docker compose (not docker-compose):
- name: Start Docker services
  run: |
    docker compose up -d slim-service mock-shopify mock-zendesk
    sleep 10
```

### Issue: Codecov Upload Fails

**Error**:
```
Error: Codecov token not found
Warning: Coverage upload failed
```

**Cause**: Missing CODECOV_TOKEN secret (optional for public repos)

**Solution**:
```yaml
# For public repos, Codecov token is optional
- name: Upload coverage
  uses: codecov/codecov-action@v4
  if: github.event_name == 'pull_request'
  with:
    file: ./coverage.xml
    flags: unittests
  continue-on-error: true  # Don't fail build if upload fails
```

### Issue: Nightly Cron Not Triggering

**Symptom**: Scheduled workflow doesn't run at 2 AM UTC

**Diagnosis**:
```yaml
# Check cron syntax in .github/workflows/ci.yml
schedule:
  - cron: '0 2 * * *'  # Correct: 2 AM UTC daily

# Incorrect examples:
# - cron: '0 2 * * 1-5'  # Only weekdays
# - cron: '2 0 * * *'   # Swapped hour/minute
```

**Solution**:
```bash
# Verify cron expression at: https://crontab.guru/
# GitHub Actions cron uses UTC timezone
# 2 AM UTC = 9 PM ET (previous day) / 6 PM PT (previous day)

# Manually trigger workflow to test
# Go to Actions tab → Select workflow → Run workflow
```

---

## Phase-Specific Issues

### Phase 3: Expected Test Failures

**These failures are EXPECTED in Phase 3** (template-based responses, no LLM):

1. **E2E Scenarios (1/20 passing, 5%)**
   - S002, S004, S005, S006, S007, S008, S009, S010, S011, S012, S013, S014, S015, S016, S017, S018, S019, S020
   - Reason: Templates lack context-aware data (customer names, order IDs, product details)
   - Resolution: Phase 4 Azure OpenAI integration

2. **Multi-Turn Conversations (3/10 passing, 30%)**
   - MT002, MT003, MT004, MT005, MT006, MT007, MT008, MT009, MT010
   - Reason: No pronoun resolution, no clarification AI, no sentiment analysis
   - Resolution: Phase 4 GPT-4o for context-aware responses

3. **Agent Communication (8/10 passing, 80%)**
   - AC006, AC007 (Shopify hostname resolution)
   - Reason: Docker networking issue (mock-shopify host not resolving)
   - Resolution: Not a bug, use localhost in Phase 3

**Action**: Do NOT attempt to fix these in Phase 3. They are architectural limitations.

### Phase 4: Azure OpenAI Integration

**Anticipated issues** (not in Phase 3 yet):

1. **Rate Limiting**
   - Error: `429 Too Many Requests`
   - Solution: Implement exponential backoff, request queuing

2. **High Latency**
   - Symptom: P95 > 2000ms
   - Solution: Caching, parallel requests, GPT-4o-mini for non-critical tasks

3. **Cost Overruns**
   - Symptom: Monthly bill > $310-360
   - Solution: Reduce agent count, optimize prompts, implement caching

**See DEPLOYMENT-GUIDE.md for Phase 4 troubleshooting**

---

## Getting Help

### Self-Service Resources

1. **Check Documentation**:
   - TESTING-GUIDE.md (comprehensive test instructions)
   - DEPLOYMENT-GUIDE.md (Phase 4 prep)
   - README.md (project overview)
   - .github/workflows/README.md (CI/CD guide)

2. **Search GitHub Issues**:
   - https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues
   - Check closed issues (may already be resolved)

3. **Review Phase 3 Summaries**:
   - docs/PHASE-3-DAY-1-SUMMARY.md through PHASE-3-DAY-12-SUMMARY.md
   - docs/PHASE-3-PROGRESS.md (current status)

### Creating a Bug Report

If issue not covered in this guide:

1. **Gather Information**:
   - Error message (full traceback)
   - Steps to reproduce
   - Environment (OS, Python version, Docker version)
   - Expected vs actual behavior

2. **Minimal Reproduction**:
   - Simplify to smallest code that reproduces issue
   - Remove unrelated code

3. **Create GitHub Issue**:
   ```markdown
   **Title**: Brief description (e.g., "Docker services fail to start on Windows 11")

   **Environment**:
   - OS: Windows 11
   - Python: 3.14.0
   - Docker: 24.0.5

   **Steps to Reproduce**:
   1. Run `docker compose up -d`
   2. Wait 10 seconds
   3. Run `pytest tests/integration/ -v`

   **Expected**: Tests pass
   **Actual**: ConnectionError: Cannot connect to localhost:5001

   **Error Message**:
   ```
   [paste full error here]
   ```

   **Logs**:
   ```
   [paste docker logs mock-shopify]
   ```
   ```

### Contact

- **GitHub Issues**: https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues
- **Email**: support@remaker.digital
- **Documentation Feedback**: documentation@remaker.digital

---

## Appendix: Common Error Codes

| Error Code | Meaning | Common Cause |
|------------|---------|--------------|
| `ModuleNotFoundError` | Python can't find module | Missing dependency, PYTHONPATH not set |
| `ConnectionError` | Can't connect to service | Docker service down, wrong port |
| `TimeoutError` | Operation took too long | Agent hung, network issue, timeout too short |
| `AssertionError` | Test assertion failed | Expected vs actual mismatch, Phase 3 limitation |
| `KeyError` | Dictionary key not found | Missing field in message, API response |
| `ValueError` | Invalid value | Wrong data type, out of range |
| `FileNotFoundError` | File doesn't exist | Wrong path, file not created yet |
| `PermissionError` | Insufficient permissions | Docker volume mount, file ownership |

---

**Document Status**: Active
**Maintained By**: Development Team
**Next Review**: After Phase 4 Deployment
**Feedback**: GitHub Issues or support@remaker.digital

---

## Streamlit Console Issues

### Issue: Streamlit Shows Old/Cached Content

**Symptoms**:
- Code changes don't appear in the browser
- New features/toggles don't show up (e.g., Azure OpenAI mode toggle missing)
- Debug statements in code don't execute
- Browser shows stale UI even after code modifications

**Root Cause**: Streamlit maintains persistent WebSocket connections. If an old Streamlit process is still running on a port, the browser reconnects to it instead of the new process. Additionally, Python's `__pycache__` may contain outdated compiled bytecode.

**Diagnosis**:
```powershell
# Check if multiple Python/Streamlit processes are running
Get-Process python* | Select-Object Id, ProcessName, StartTime

# Check what's using specific ports
netstat -an | findstr :8080
netstat -an | findstr :8085
```

**Solution**:
```powershell
# Step 1: Kill ALL Python processes (careful if other Python apps running)
Get-Process python* | Stop-Process -Force -ErrorAction SilentlyContinue

# Step 2: Clear Python cache
Remove-Item -Path console/__pycache__ -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path evaluation/__pycache__ -Recurse -Force -ErrorAction SilentlyContinue

# Step 3: Clear Streamlit cache
python -m streamlit cache clear

# Step 4: Start on a FRESH PORT (not previously used)
streamlit run console/app.py --server.port 8085

# Step 5: Open browser to the NEW port
# http://localhost:8085
```

**Prevention**:
- Always stop Streamlit with Ctrl+C before restarting
- Use a fresh port number when troubleshooting
- Hard refresh browser with Ctrl+Shift+R
- Use incognito/private browsing window

**OneDrive Consideration**: If project is in OneDrive folder, sync delays can cause the running process to see older file versions. The filesystem reports the new content but the process may have cached the old version. Restarting the process resolves this.

### Issue: Azure OpenAI Mode Toggle Not Appearing

**Symptoms**:
- Chat Interface shows no "🔌 Azure OpenAI Mode" toggle
- Sidebar doesn't show "🔧 Azure OpenAI Status" debug info

**Diagnosis**:
1. Check sidebar for "🔧 Azure OpenAI Status" section
2. If "Available: False" - environment variables not set
3. If "Import Error" shown - module installation issue

**Solution**:
```powershell
# 1. Verify environment variables
echo $env:AZURE_OPENAI_ENDPOINT
echo $env:AZURE_OPENAI_API_KEY
echo $env:AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT

# 2. Test import directly
python -c "from console.azure_openai_mode import is_azure_mode_available; print('Available:', is_azure_mode_available())"

# 3. Test full initialization
python -c "from console.azure_openai_mode import get_azure_mode; azure = get_azure_mode(); print(azure.initialize())"

# 4. If working in Python but not Streamlit, follow "Streamlit Shows Old/Cached Content" above
```

### Issue: Azure OpenAI Responses Blocked

**Symptoms**:
- Messages return "Content blocked by Azure safety filter 🚫 BLOCKED"
- 0% confidence, only Critic/Supervisor agent shown

**Cause**: Azure's built-in content moderation filter detected potentially problematic content. This is defense-in-depth working correctly.

**Solution**:
- Rephrase the message to avoid triggering the filter
- This is expected behavior for certain word patterns
- The Critic/Supervisor agent provides additional validation layer

**Note**: Blocked messages still cost a small amount (~$0.0001) for the API call.

---

**Version History**:
- v1.1 (2026-01-25): Added Streamlit Console troubleshooting section
- v1.0 (2026-01-25): Initial release for Phase 3
