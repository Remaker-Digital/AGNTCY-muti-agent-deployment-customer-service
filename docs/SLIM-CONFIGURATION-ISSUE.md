# SLIM Configuration Issue - January 24, 2026

## Issue Summary

**Status**: SLIM service cannot start due to configuration incompatibility
**Impact**: Console operates in simulation mode (acceptable for Phase 1-3)
**Severity**: Low (does not block development)

---

## Problem Description

The SLIM Docker container (ghcr.io/agntcy/slim:0.6.1) fails to start with configuration errors.

### Error Messages

```
thread 'main' panicked at core/slim/src/bin/main.rs:27:55:
failed to load configuration: InvalidKey("server")
```

### Root Cause

The SLIM server configuration file (`config/slim/server-config.yaml`) uses a configuration structure that is not compatible with SLIM v0.6.1.

**Incompatible Configuration**:
```yaml
server:
  host: 0.0.0.0
  port: 46357
  gateway:
    enabled: true
    password: ${SLIM_GATEWAY_PASSWORD}
```

**Issue**: SLIM v0.6.1 does not recognize the `server` top-level key. The configuration schema may have changed between versions or the example configuration is from a different version.

---

## Investigation Steps Taken

### 1. Docker Image Validation ✅
```bash
docker pull ghcr.io/agntcy/slim:0.6.1
# Status: Image is up to date
```

### 2. Executable Location Fix ✅
**Original Issue**: Command tried to run `slim` but executable is at `/slim`

**Fix Applied** (docker-compose.yml):
```yaml
# BEFORE
command: ["slim", "server", "--config", "/config.yaml"]

# AFTER
command: ["/slim", "--config", "/config.yaml"]
```

### 3. Command Arguments Fix ✅
**Issue**: SLIM doesn't accept `server` subcommand

**Fix Applied**:
```yaml
# BEFORE
command: ["/slim", "server", "--config", "/config.yaml"]

# AFTER
command: ["/slim", "--config", "/config.yaml"]
```

### 4. Configuration Schema Mismatch ❌
**Issue**: Configuration file uses `server:` key which SLIM v0.6.1 doesn't recognize

**Status**: Unable to determine correct schema without SLIM documentation

---

## Attempted Solutions

### Solution 1: Fix Docker Command ✅
- Changed `"slim"` to `"/slim"` (absolute path)
- Removed `"server"` subcommand
- **Result**: Command runs but configuration fails

### Solution 2: Configuration Update ❌
- Cannot update without official SLIM v0.6.1 configuration schema
- No error indicates what the correct schema should be
- AGNTCY SDK documentation not available locally

---

## Impact Assessment

### What Works ✅
1. **Console Web Interface**: Fully functional at http://localhost:8080
2. **All 5 Pages**: Dashboard, Chat, Metrics, Traces, Status accessible
3. **Simulation Mode**: Console provides simulated agent responses
4. **UI Testing**: All features testable with mock data
5. **Documentation**: Can validate all console documentation

### What Doesn't Work ❌
1. **Real Agent Communication**: Cannot send A2A messages without SLIM
2. **Live Trace Collection**: No real OpenTelemetry traces from agents
3. **Actual Performance Metrics**: Metrics are simulated/estimated

### Phase 1-3 Impact: **MINIMAL** ✅

**Rationale**:
- Phase 1-3 is local development with mock services
- Console is designed with graceful fallback to simulation mode
- All agent business logic can be tested via integration tests
- Real A2A communication testing can be deferred to Phase 4

---

## Recommended Approach

### For Phase 1-3 (Current - LOCAL DEVELOPMENT)

**Continue with Simulation Mode** ✅

**Advantages**:
1. Console fully functional for UI/UX testing
2. No blocking issues for Phase 2 story implementation
3. Integration tests validate agent logic independently
4. Simulation mode demonstrates fallback behavior (good for educational project)

**What to Do**:
1. ✅ Use console at http://localhost:8080
2. ✅ Test all features with simulated data
3. ✅ Continue Phase 2 story implementation
4. ✅ Run integration tests via pytest (these don't need SLIM)
5. ✅ Document simulation mode behavior

### For Phase 4-5 (AZURE DEPLOYMENT)

**Options to Resolve**:

**Option A: Update SLIM Version** (Recommended)
- Check for SLIM v0.7+ or latest version
- Update `docker-compose.yml` image version
- Test with updated configuration schema

**Option B: Obtain Correct Configuration**
- Contact AGNTCY SDK support/documentation
- Get official SLIM v0.6.1 configuration example
- Update `config/slim/server-config.yaml`

**Option C: Use Alternative Transport**
- AGNTCY SDK supports multiple transports
- Consider NATS direct integration (bypassing SLIM)
- Evaluate Azure Service Bus as alternative

**Option D: Deploy SLIM from Source**
- Clone SLIM repository if available
- Build custom Docker image with debugging
- Include configuration examples/documentation

---

## Workaround: Run Agents in Demo Mode

Agents can run independently in demo mode without SLIM, allowing local testing.

### Start Agents in Demo Mode

**Intent Classification Agent**:
```bash
cd agents/intent_classification
python agent.py
# Runs in demo mode, processes sample messages
```

**Knowledge Retrieval Agent**:
```bash
cd agents/knowledge_retrieval
python agent.py
# Runs in demo mode with mock Shopify/KB access
```

**Response Generation Agent**:
```bash
cd agents/response_generation
python agent.py
# Runs in demo mode, generates sample responses
```

**Benefits**:
- Tests agent logic independently
- Validates mock API integrations
- No SLIM dependency required
- Logs show agent processing flows

---

## Configuration Details

### Docker Compose Changes Made

**File**: `docker-compose.yml`

**Line 50** (BEFORE):
```yaml
command: ["slim", "server", "--config", "/config.yaml"]
```

**Line 50** (AFTER):
```yaml
command: ["/slim", "--config", "/config.yaml"]
```

### SLIM Configuration File

**Location**: `config/slim/server-config.yaml`

**Current Structure** (INCOMPATIBLE):
```yaml
server:           # ❌ Invalid key for SLIM v0.6.1
  host: 0.0.0.0
  port: 46357
  gateway:
    enabled: true
    password: ${SLIM_GATEWAY_PASSWORD}
  log_level: INFO

transport:
  type: nats
  nats:
    url: nats://nats:4222

observability:
  metrics:
    enabled: true
    endpoint: http://otel-collector:4318
  tracing:
    enabled: true
    endpoint: http://otel-collector:4318
```

**Expected Structure**: UNKNOWN (documentation not available)

---

## Console Behavior in Simulation Mode

### How It Works

When SLIM is unavailable, the console automatically enters simulation mode:

1. **Message Sending**: Creates CustomerMessage but fails to send via SLIM
2. **Timeout Handling**: Catches connection timeout exception
3. **Fallback Response**: Generates simulated agent response with realistic delay
4. **Mock Traces**: Creates sample trace data for Trace Viewer
5. **Warning Display**: Shows "Running in simulation mode" banner

### Example Simulation Flow

**User Action**: Send "Where is my order?" in Chat Interface

**Console Behavior**:
```python
try:
    # Attempt real A2A message send
    response = await a2a_client.send(message, timeout=5000)
except (TimeoutError, ConnectionError):
    # Fallback to simulation
    simulated_response = {
        "intent": "order_status",
        "confidence": 0.90,
        "response_text": "I can help you track your order...",
        "processing_time_ms": 125
    }
    return simulated_response
```

**User Experience**:
- Message appears to process normally
- Response generated after realistic delay (100-500ms)
- Warning banner indicates simulation mode
- All UI features functional

### What's Simulated

**Dashboard**:
- Total conversations: Increments with each test
- Success rate: Fixed at 85%
- Avg response time: Random 100-300ms
- Activity timeline: Mock 24h data

**Chat Interface**:
- Intent classification: Rule-based (keywords)
- Knowledge results: Static samples
- Responses: Template-based with persona

**Agent Metrics**:
- Latency: Random P50/P95/P99
- Success rate: 80-95% per agent
- Cost: Estimated based on token count
- Volume: Mock request counts

**Trace Viewer**:
- Sample traces: Pre-generated conversation flows
- Timeline: Realistic step sequence
- Metadata: Plausible agent names, latencies

**System Status**:
- Mock APIs: Real health checks (these work!)
- Infrastructure: Shows SLIM as "Unhealthy" (expected)
- Agents: Marked as "Not Running" (accurate)

---

## Testing Without SLIM

### Integration Tests (Recommended)

**Run existing integration tests** - these don't require SLIM:

```bash
# Issue #24 - Order Status
python -m pytest tests/integration/test_order_status_flow.py -v

# Issue #25 - Product Info
python -m pytest tests/integration/test_product_info_flow.py -v

# Issue #29 - Return/Refund
python -m pytest tests/integration/test_return_refund_flow.py -v

# All Phase 2 tests
python run_phase2_tests.py
```

**Why This Works**:
- Tests instantiate agents directly (no SLIM)
- Use mock API containers (Shopify, Zendesk, etc.)
- Validate agent logic independently
- Measure actual performance (not simulated)

### Agent Demo Mode

Each agent has a `run_demo_mode()` method that runs standalone:

```bash
# Navigate to agent directory
cd agents/intent_classification

# Run agent in demo mode
python agent.py

# Output:
# INFO: Running in DEMO MODE
# INFO: Processing sample message: "Where is my order?"
# INFO: Classified intent: ORDER_STATUS (confidence: 0.95)
```

This validates:
- Agent initialization
- Message processing logic
- Mock API integration
- Logging and error handling

---

## Next Steps

### Immediate (For Current Development)

1. ✅ **Use Console in Simulation Mode**
   - Access: http://localhost:8080
   - Test all 5 pages
   - Validate UI/UX flows

2. ✅ **Run Integration Tests**
   - Execute: `python run_phase2_tests.py`
   - Verify: All tests passing
   - Coverage: Monitor test coverage progress

3. ✅ **Continue Phase 2 Implementation**
   - Implement next user story (Issue #30)
   - Use integration tests for validation
   - Console for UI testing

4. ✅ **Document Simulation Mode**
   - Update console README
   - Note SLIM limitation
   - Explain fallback behavior

### Future (Phase 4 Preparation)

1. **Research SLIM Configuration**
   - Check AGNTCY SDK updates
   - Look for SLIM v0.7+ release
   - Review official documentation

2. **Test Alternative Approaches**
   - Direct NATS integration
   - Azure Service Bus transport
   - Custom SLIM build

3. **Plan Phase 4 Migration**
   - Evaluate transport options
   - Design Azure deployment
   - Test real A2A communication

---

## Conclusion

**Current Status**: SLIM cannot start due to configuration incompatibility with v0.6.1

**Impact**: Minimal for Phase 1-3 local development

**Recommendation**: Continue with simulation mode for Phase 2 implementation

**Next Actions**:
1. Use console at http://localhost:8080 (simulation mode)
2. Continue Phase 2 story implementation
3. Run integration tests for agent validation
4. Defer SLIM resolution to Phase 4 preparation

**Educational Value**: Demonstrates graceful degradation and fallback patterns (beneficial for blog post audience)

---

**Document Created**: 2026-01-24
**Author**: Development Team
**Status**: Known Issue - Non-Blocking
**Phase Impact**: Phase 1-3 (Minimal), Phase 4-5 (Requires Resolution)
