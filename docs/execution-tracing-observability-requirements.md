# Execution Tracing & Observability Requirements

**Document Purpose:** Specification for detailed execution traces enabling operators to understand agent decisions and diagnose issues.

**Last Updated:** 2026-01-22
**Status:** ✅ Approved - Ready for Implementation
**Phase:** Phase 2 (Design + Mock), Phase 3-5 (Full Implementation)

---

## Executive Summary

Comprehensive execution tracing captures every agent decision, LLM call, validation step, and data access to enable operators to:
- Understand why an agent made a specific decision
- Diagnose undesirable behaviors
- Debug complex multi-agent interactions
- Audit customer interactions for compliance
- Improve agent logic based on real-world patterns

**Key Capabilities:**
- Full decision tree tracing (every step in conversation)
- Timeline view (chronological flow)
- Decision tree diagram (visual routing)
- Searchable logs with rich filtering
- PII tokenization (privacy-safe traces)
- 7-day retention (cost-optimized)

---

## 1. Tracing Requirements

### 1.1 Trace Depth: Full Decision Tree

**Captures:**
- Every agent interaction (A2A messages sent/received)
- Every LLM call (prompts, responses, tokens, latency)
- Every validation step (Critic/Supervisor checks)
- Every data access (Cosmos, Blob, Key Vault reads/writes)
- Every routing decision (why Intent Agent chose response-generator)
- Every escalation trigger (why Escalation Agent created ticket)
- Every event processed (Shopify webhooks, scheduled triggers)

**For Each Step:**
```json
{
  "trace_id": "trace_abc123",
  "span_id": "span_001",
  "parent_span_id": null,
  "timestamp": "2026-01-22T14:35:00.123Z",
  "agent": "intent-classifier",
  "action": "classify_intent",
  "inputs": {
    "message": "Where is my order?",
    "customer_id": "TOKEN_a7f3c9e1",  // Tokenized
    "context": {...}
  },
  "outputs": {
    "intent": "order_status",
    "confidence": 0.95,
    "routing": "response-generator"
  },
  "reasoning": "High confidence order status query detected. Keywords: 'where', 'order'. No ambiguity.",
  "latency_ms": 245,
  "cost": {
    "tokens": 150,
    "dollars": 0.000023
  },
  "metadata": {
    "model": "gpt-4o-mini",
    "temperature": 0.3
  }
}
```

**Rationale:**
- ✅ Complete visibility into multi-agent decision flow
- ✅ Enables root cause analysis of any issue
- ✅ Supports regulatory compliance (audit trail)
- ❌ Higher storage cost (~$10-20/month for 7 days)
- ✅ But: Worth it for debuggability and compliance

---

### 1.2 Trace Scope: All Agent Types

**Traced Agents:**
1. **Intent Classification Agent**
   - Input message received
   - LLM classification call
   - Intent + confidence + routing decision
   - Reasoning for routing choice

2. **Knowledge Retrieval Agent**
   - Query received
   - Embedding generation (if RAG)
   - Vector search results (top 3)
   - Context formatted for response generation
   - Cache hits/misses

3. **Response Generation Agent**
   - Context received (intent + knowledge)
   - Data fetched (Cosmos, Shopify API)
   - LLM response generation call
   - Response sent to Critic/Supervisor
   - Regeneration attempts (if rejected)

4. **Critic/Supervisor Agent**
   - Validation request (input or output)
   - Each validation check (profanity, PII, harmful content)
   - Rejection reasons (if any)
   - Feedback sent to Response Generation
   - Retry count

5. **Escalation Agent**
   - Escalation trigger evaluation
   - Business rules applied
   - Zendesk ticket creation
   - Priority and queue assignment

6. **Analytics Agent**
   - Event received (conversation completed)
   - Metrics calculated (latency, satisfaction, cost)
   - Aggregation to Cosmos analytical store

**External Interactions:**
- Shopify API calls (order lookup, inventory check)
- Zendesk API calls (ticket creation, status update)
- Mailchimp API calls (subscriber add, campaign trigger)
- Azure OpenAI calls (every prompt + response)
- Cosmos DB queries (every read/write)
- Key Vault access (PII token lookups)

---

### 1.3 Trace Format: OpenTelemetry Standard

**Protocol:** OpenTelemetry (OTLP)

**Why OpenTelemetry:**
- ✅ Industry standard (portable to any observability platform)
- ✅ Native support in AGNTCY SDK
- ✅ Rich ecosystem (Grafana, Jaeger, DataDog, etc.)
- ✅ Automatic instrumentation for HTTP, gRPC, database calls
- ✅ Distributed tracing across agents

**Instrumentation:**
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Initialize tracer
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="localhost:4317"))
)
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)

# Trace agent action
with tracer.start_as_current_span("classify_intent") as span:
    span.set_attribute("agent", "intent-classifier")
    span.set_attribute("customer_id", customer_id_token)
    span.set_attribute("message_length", len(message))

    # Perform classification
    intent = classify_with_llm(message)

    span.set_attribute("intent", intent.name)
    span.set_attribute("confidence", intent.confidence)
    span.add_event("Intent classified", {
        "reasoning": intent.reasoning,
        "routing": intent.routing_target
    })
```

---

## 2. Trace Storage & Retention

### 2.1 Storage Architecture

**Phase 1-3 (Local Development):**
- **Backend:** ClickHouse (Docker container)
- **Collector:** OpenTelemetry Collector (Docker container)
- **Retention:** 7 days (local disk, ~1GB)
- **Cost:** $0 (local hardware)

**Phase 4-5 (Azure Production):**
- **Backend:** Azure Monitor + Application Insights
- **Collector:** OpenTelemetry Collector (Container Instance)
- **Retention:** 7 days
- **Cost:** ~$10-20/month (based on volume)

**Alternative (Post Phase 5):**
- **Backend:** Self-hosted Jaeger or Grafana Tempo
- **Storage:** Azure Blob (hot tier, 7-day lifecycle)
- **Cost:** ~$5-10/month (cheaper than App Insights)

---

### 2.2 Retention Policy

**Hot Storage (Fast Queries):** 7 days
- Application Insights or ClickHouse
- Sub-second query performance
- Full trace detail

**Archive Storage:** None (cost optimization)
- Rationale: 7 days sufficient for debugging recent issues
- If needed for compliance, can extend to 30 days in Phase 5

**Anonymized Aggregates:** Indefinite
- Conversation success rate by intent
- Average latency by agent
- Escalation patterns
- Cost per conversation
- Stored in Cosmos DB analytical store

**Purge Policy:**
- Auto-delete traces older than 7 days
- Operator can export specific traces before deletion (JSON download)

---

### 2.3 Data Volume Estimates

**Per Conversation:**
- 10-20 spans (agent hops)
- 50-100 KB trace data
- With 1000 conversations/day:
  - **Daily:** 50-100 MB
  - **7 days:** 350-700 MB

**Storage Cost:**
- Application Insights: ~$2.30/GB ingested
- 0.7 GB * 30 days = 21 GB/month
- **Estimated:** $48/month (but with 7-day retention, ~$10-15/month)

**Optimization:**
- Sample high-volume traces (e.g., 10% for successful conversations, 100% for errors)
- Result: ~$5-10/month

---

## 3. Trace Visualization

### 3.1 Timeline View (Conversation Flow)

**Purpose:** See chronological sequence of agent interactions

**Implementation:** Grafana + Jaeger Query UI

**Example Timeline:**
```
14:35:00.000  [Customer]          Message: "Where is my order?"
14:35:00.050  [Intent Agent]      Classifying intent...
14:35:00.245  [Intent Agent]      ✓ Intent: order_status (conf: 0.95)
14:35:00.250  [Response Agent]    Fetching order data from Cosmos...
14:35:00.310  [Response Agent]    ✓ Order found: #10234 (fulfilled)
14:35:00.320  [Response Agent]    Calling Shopify API for tracking...
14:35:00.580  [Response Agent]    ✓ Tracking: 9400123456789
14:35:00.590  [Response Agent]    Generating response with GPT-4o...
14:35:01.820  [Response Agent]    ✓ Response generated (125 tokens)
14:35:01.830  [Critic Agent]      Validating response...
14:35:01.950  [Critic Agent]      ✓ Validation passed (no issues)
14:35:01.960  [Customer]          Response: "Your order is in transit..."
```

**Features:**
- Expand/collapse each step for details
- Color-coded by agent
- Highlight errors in red
- Show latency for each step (visual bars)

**Access:**
- Grafana dashboard: "Conversation Timeline"
- Filter by conversation_id, customer_id, date range

---

### 3.2 Decision Tree Diagram (Visual Routing)

**Purpose:** Understand how agents routed the conversation

**Implementation:** Grafana Node Graph or custom D3.js visualization

**Example Diagram:**
```
                  ┌─────────────┐
                  │  Customer   │
                  │   Message   │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   Intent    │
                  │   Agent     │
                  └──────┬──────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼ (order_status)      ▼ (product_inquiry)
       ┌─────────────┐       ┌─────────────┐
       │  Response   │       │  Knowledge  │
       │   Agent     │       │  Retrieval  │
       └──────┬──────┘       └──────┬──────┘
              │                     │
              ▼                     ▼
       ┌─────────────┐       ┌─────────────┐
       │   Critic    │       │  Response   │
       │   Agent     │       │   Agent     │
       └──────┬──────┘       └─────────────┘
              │
        (pass)│    (reject)
              ▼       ↓ (regenerate)
       ┌─────────────┐
       │  Customer   │
       │  Response   │
       └─────────────┘
```

**Features:**
- Nodes color-coded by agent type
- Edges labeled with decision rationale
- Click node to see full trace details
- Highlight critical path (longest latency)

**Access:**
- Grafana dashboard: "Agent Decision Flow"
- Filterable by conversation outcome (success, escalation, error)

---

### 3.3 Searchable Logs with Filtering

**Purpose:** Text-based search and filtering for forensic analysis

**Implementation:** Azure Log Analytics (Kusto Query Language) or ClickHouse SQL

**Query Examples:**

**Find all escalations for a customer:**
```kusto
traces
| where customer_id == "TOKEN_a7f3c9e1"
| where action == "escalate_to_human"
| project timestamp, reason, priority, ticket_id
| order by timestamp desc
```

**Find conversations where Critic rejected response 3+ times:**
```kusto
traces
| where agent == "critic-supervisor"
| where action == "validate_output"
| where status == "reject"
| summarize reject_count = count() by conversation_id
| where reject_count >= 3
| join (traces | where action == "escalate_to_human") on conversation_id
```

**Find all PII leakage detections:**
```kusto
traces
| where agent == "critic-supervisor"
| where issues has "pii_leakage"
| project timestamp, conversation_id, customer_id, data_type, severity
```

**Find slowest agent operations:**
```kusto
traces
| where latency_ms > 2000
| summarize count(), avg(latency_ms), max(latency_ms) by agent, action
| order by avg_latency_ms desc
```

**Features:**
- Saved queries for common investigations
- Alert on specific patterns (e.g., PII leakage detected)
- Export results to CSV or JSON

**Access:**
- Azure Portal → Log Analytics Workspace → Logs
- Or: Grafana "Explore" tab with Azure Monitor data source

---

## 4. Trace Enrichment

### 4.1 Standard Trace Attributes

**Every Span Includes:**
```json
{
  // OpenTelemetry standard
  "trace_id": "unique_trace_id",
  "span_id": "unique_span_id",
  "parent_span_id": "parent_span_id",
  "name": "classify_intent",
  "kind": "INTERNAL",  // or CLIENT, SERVER
  "start_time": "2026-01-22T14:35:00.000Z",
  "end_time": "2026-01-22T14:35:00.245Z",
  "status": "OK",  // or ERROR

  // Custom attributes
  "attributes": {
    // Agent context
    "agent.name": "intent-classifier",
    "agent.version": "v1.2.3",
    "agent.instance_id": "pod-abc-123",

    // Conversation context
    "conversation.id": "conv_1234567890",
    "conversation.turn": 3,
    "customer.id": "TOKEN_a7f3c9e1",  // Tokenized
    "customer.tier": "vip",

    // Action context
    "action.type": "classify_intent",
    "action.input_length": 18,  // "Where is my order?"
    "action.output": "order_status",

    // Model context (if LLM used)
    "model.provider": "azure_openai",
    "model.name": "gpt-4o-mini",
    "model.temperature": 0.3,
    "model.tokens.prompt": 50,
    "model.tokens.completion": 100,
    "model.cost_usd": 0.000023,

    // Performance
    "latency.llm_ms": 200,
    "latency.data_fetch_ms": 30,
    "latency.total_ms": 245,

    // Routing
    "routing.next_agent": "response-generator",
    "routing.confidence": 0.95,
    "routing.reasoning": "High confidence order status query"
  },

  // Events within span
  "events": [
    {
      "name": "LLM call started",
      "timestamp": "2026-01-22T14:35:00.050Z",
      "attributes": {"prompt_length": 50}
    },
    {
      "name": "LLM call completed",
      "timestamp": "2026-01-22T14:35:00.245Z",
      "attributes": {"completion_length": 100}
    }
  ]
}
```

---

### 4.2 PII Tokenization in Traces

**Requirement:** All PII must be tokenized before writing to trace storage

**Implementation:**
```python
def sanitize_trace_data(data: Dict) -> Dict:
    """
    Replace all PII with tokens before sending to trace storage.

    Applies to:
    - Customer messages (inputs)
    - AI responses (outputs)
    - API call parameters
    - Database query results
    """

    # Tokenize customer ID
    if "customer_id" in data:
        data["customer_id"] = tokenize_pii(data["customer_id"])

    # Tokenize customer message
    if "message" in data:
        data["message"] = tokenize_pii_in_text(data["message"])

    # Tokenize AI response
    if "response" in data:
        data["response"] = tokenize_pii_in_text(data["response"])

    # Tokenize email in any field
    data = regex_replace_emails(data, replacement="EMAIL_TOKEN")

    # Tokenize phone in any field
    data = regex_replace_phones(data, replacement="PHONE_TOKEN")

    return data
```

**Example Tokenized Trace:**
```json
{
  "customer_id": "TOKEN_a7f3c9e1",  // Not "cust_5678"
  "message": "Where is my order? EMAIL_TOKEN",  // Not "john@example.com"
  "response": "Your order will ship to EMAIL_TOKEN",  // Not actual email
  "api_call": {
    "endpoint": "/orders/10234",
    "customer_email": "EMAIL_TOKEN"  // Not actual email
  }
}
```

**Rationale:**
- ✅ Traces are privacy-safe (can be viewed by all operators)
- ✅ Meets GDPR compliance (no PII in logs)
- ✅ Reduces risk of data leaks
- ❌ Operator can't see actual customer data (must look up token in Key Vault)
- ✅ But: Token can be de-tokenized if needed for debugging (with proper authorization)

---

### 4.3 Error and Exception Tracking

**Standard Error Attributes:**
```json
{
  "status": "ERROR",
  "error.type": "ValidationError",
  "error.message": "Profanity detected in response",
  "error.stack": "[full stack trace]",
  "error.recoverable": true,  // or false
  "error.retry_count": 2,
  "error.escalated": false
}
```

**Error Categories:**
- `ValidationError`: Critic/Supervisor rejected response
- `TimeoutError`: External API call exceeded timeout
- `DataNotFoundError`: Order/customer not found in Cosmos
- `RateLimitError`: External API rate limit exceeded
- `SystemError`: Unexpected exception (agent crash)

**Automatic Alerting:**
- ERROR status → Immediate alert (Slack, email)
- `error.escalated = true` → Page on-call engineer
- Error rate >5% sustained for 5 min → Alert

---

## 5. Debugging Workflows

### 5.1 Investigate Customer Complaint

**Scenario:** Customer complains "I got a weird response from the chatbot"

**Workflow:**
1. **Find conversation trace:**
   - Query: `customer_id == "TOKEN_from_support_ticket"`
   - Or: `conversation_id == "conv_from_chat_logs"`

2. **View timeline:**
   - Open Grafana "Conversation Timeline" dashboard
   - Filter by conversation_id
   - Identify unusual latency or errors

3. **Drill into specific agent:**
   - Click on Response Generation Agent span
   - View full LLM prompt and response
   - Check if Critic rejected response (and why)

4. **Check routing decision:**
   - Review Intent Agent classification
   - Verify confidence score
   - Check if intent was misclassified

5. **Root cause identified:**
   - Example: "Response Generation hallucinated order status because Shopify API returned 500"
   - Fix: Add retry logic + better error handling

**Time to Resolution:** 5-10 minutes (with traces) vs. 1-2 hours (without)

---

### 5.2 Diagnose Escalation Pattern

**Scenario:** Escalation rate suddenly increased from 10% to 25%

**Workflow:**
1. **Query escalations:**
   ```kusto
   traces
   | where action == "escalate_to_human"
   | where timestamp > ago(24h)
   | summarize count() by reason
   | order by count_ desc
   ```

2. **Identify pattern:**
   - Example: 80% of escalations have reason "intent_confidence_low"
   - Intent Agent is struggling to classify recent queries

3. **Analyze failing cases:**
   ```kusto
   traces
   | where action == "classify_intent"
   | where confidence < 0.7
   | project message, intent, confidence, reasoning
   | take 100
   ```

4. **Root cause identified:**
   - Example: "New product launch introduced terms not in training data"
   - Fix: Add new product terms to intent classifier prompt

**Time to Resolution:** 15-30 minutes

---

### 5.3 Performance Optimization

**Scenario:** Average response time increased from 1.5s to 3.0s

**Workflow:**
1. **Query slowest operations:**
   ```kusto
   traces
   | where latency_ms > 2000
   | summarize avg(latency_ms), count() by agent, action
   | order by avg_latency_ms desc
   ```

2. **Identify bottleneck:**
   - Example: Knowledge Retrieval Agent avg 2.5s (was 500ms)

3. **Drill into slow spans:**
   ```kusto
   traces
   | where agent == "knowledge-retrieval"
   | where latency_ms > 2000
   | project timestamp, action, latency_ms, attributes
   ```

4. **Root cause identified:**
   - Example: "Cosmos vector search slow due to missing index"
   - Fix: Add vector index on frequently queried fields

**Time to Resolution:** 30 minutes - 1 hour

---

## 6. Implementation Details

### 6.1 AGNTCY SDK Integration

**Enable Tracing in Factory:**
```python
from agntcy_app_sdk.factory import AgntcyFactory
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Initialize OpenTelemetry
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(endpoint=os.getenv("OTLP_ENDPOINT", "localhost:4317"))
    )
)
trace.set_tracer_provider(tracer_provider)

# Enable tracing in AGNTCY factory
factory = AgntcyFactory(
    transport="slim",
    enable_tracing=True,  # ← Enable
    trace_sampling_rate=1.0  # 100% sampling (or 0.1 for 10%)
)
```

**Automatic Instrumentation:**
- All A2A messages automatically traced
- All MCP tool calls automatically traced
- HTTP calls automatically traced (Azure OpenAI, Shopify, Zendesk)
- Database calls automatically traced (Cosmos, Blob)

**Manual Instrumentation (for custom logic):**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def classify_intent(message: str) -> Intent:
    with tracer.start_as_current_span("classify_intent") as span:
        # Add custom attributes
        span.set_attribute("message_length", len(message))
        span.set_attribute("customer_tier", get_customer_tier())

        # Perform classification
        intent = await call_llm_classifier(message)

        # Add result attributes
        span.set_attribute("intent", intent.name)
        span.set_attribute("confidence", intent.confidence)

        # Add reasoning event
        span.add_event("Intent classified", {
            "reasoning": intent.reasoning,
            "routing": intent.routing_target
        })

        return intent
```

---

### 6.2 Cost Optimization

**Sampling Strategies:**

**Phase 1-3 (Local):**
- 100% sampling (no cost, unlimited storage)

**Phase 4 (Initial Production):**
- 100% sampling (learn patterns, tune thresholds)
- Budget: ~$15-20/month for 7 days

**Phase 5 (Optimized Production):**
- **Successful conversations:** 10% sampling
- **Escalations:** 100% sampling
- **Errors:** 100% sampling
- **Slow responses (>2s):** 100% sampling
- Result: ~$5-10/month

**Dynamic Sampling:**
```python
def should_sample_trace(conversation: Conversation) -> bool:
    """
    Decide whether to sample this conversation trace.

    Always sample:
    - Errors or exceptions
    - Escalations
    - Slow responses (>2s)
    - VIP customers

    Sample 10% of successful standard conversations
    """

    if conversation.has_error:
        return True
    if conversation.escalated:
        return True
    if conversation.latency_ms > 2000:
        return True
    if conversation.customer_tier == "vip":
        return True

    # 10% sampling for normal conversations
    return random.random() < 0.1
```

---

### 6.3 Grafana Dashboards

**Dashboard 1: Conversation Timeline**
- **Purpose:** View single conversation flow
- **Inputs:** conversation_id or customer_id
- **Visualizations:**
  - Timeline chart (Jaeger trace view)
  - Latency breakdown (pie chart by agent)
  - Error/success indicators

**Dashboard 2: Agent Decision Flow**
- **Purpose:** Visual routing diagram
- **Inputs:** conversation_id
- **Visualizations:**
  - Node graph (agents as nodes, messages as edges)
  - Critical path highlighting
  - Click node → drill into trace details

**Dashboard 3: Trace Search & Filter**
- **Purpose:** Text-based forensic analysis
- **Inputs:** Kusto queries or filters
- **Visualizations:**
  - Table view (filterable, sortable)
  - Export to CSV/JSON

**Dashboard 4: System Health (Traces)**
- **Purpose:** Aggregate metrics from traces
- **Visualizations:**
  - Avg latency by agent (time series)
  - Error rate by agent (time series)
  - Escalation rate trend
  - Top 10 slowest operations

---

## 7. Testing & Validation

### 7.1 Phase 2-3 (Local Development)

**Unit Tests:**
- Verify tracing instrumentation doesn't break agent logic
- Test trace sanitization (PII tokenization)
- Test sampling logic (10% vs 100%)

**Integration Tests:**
- Generate traces for end-to-end conversation
- Verify traces appear in ClickHouse
- Query traces via Grafana
- Validate span hierarchy (parent/child relationships)

**Load Tests:**
- Run 1000 conversations with tracing enabled
- Measure overhead: <50ms per conversation
- Verify no memory leaks (trace buffers flush correctly)

---

### 7.2 Phase 5 (Production)

**Validation:**
- [ ] All agents emit traces (6/6 agents)
- [ ] Traces appear in Azure Monitor within 5 minutes
- [ ] Grafana dashboards load correctly
- [ ] Kusto queries return expected results
- [ ] No PII in traces (audit sample of 100 traces)
- [ ] Trace sampling reduces cost by 80-90%

**Acceptance Criteria:**
- [ ] Operator can investigate customer complaint in <10 minutes
- [ ] Operator can diagnose escalation pattern in <30 minutes
- [ ] Operator can identify performance bottleneck in <1 hour
- [ ] Trace storage cost <$10/month

---

## 8. Cost Analysis

### 8.1 Phase-by-Phase Costs

| Component | Phase 1-3 | Phase 4-5 (100%) | Phase 5 (Optimized) |
|-----------|-----------|------------------|---------------------|
| **OTLP Collector** | $0 (Docker) | $5 (Container Instance) | $5 |
| **Trace Storage** | $0 (local disk) | $15-20 (App Insights) | $5-10 (10% sampling) |
| **Grafana** | $0 (Docker) | $0 (OSS, Container) | $0 |
| **TOTAL** | **$0** | **$20-25/month** | **$10-15/month** |

**Budget Impact:**
- Phase 4-5: $287-331 + $10-15 = **$297-346/month**
- Still within acceptable range for comprehensive observability

---

### 8.2 Cost Optimization (Post Phase 5)

**Option 1:** Self-hosted Jaeger
- Replace Azure Monitor with Jaeger
- Store in Azure Blob (hot tier)
- Savings: ~$10/month
- Trade-off: More ops work (managing Jaeger)

**Option 2:** Reduce retention to 3 days
- Sufficient for recent debugging
- Savings: ~$5/month
- Trade-off: Can't investigate older issues

**Option 3:** Increase sampling to 5% (from 10%)
- Even fewer traces stored
- Savings: ~$3/month
- Trade-off: May miss some edge cases

**Recommended:** Start with 10% sampling, monitor for 30 days, adjust based on actual needs

---

## 9. Compliance & Audit

### 9.1 Regulatory Requirements

**GDPR:**
- ✅ All PII tokenized in traces (compliant)
- ✅ Customer can request trace deletion (7-day auto-purge)
- ✅ Traces deletable on demand (operator script)

**SOC 2:**
- ✅ Audit trail of all agent decisions (traces)
- ✅ Immutable logs (Application Insights)
- ✅ Access controls (Azure RBAC)

**HIPAA (if applicable):**
- ✅ Encrypted at rest (Azure storage)
- ✅ Encrypted in transit (TLS 1.3)
- ✅ No PHI in traces (tokenized)

---

### 9.2 Audit Trail

**Use Case:** Regulatory audit asks "How did your AI make decision X for customer Y?"

**Response:**
1. Query trace by customer_id + date
2. Export full trace to JSON
3. Provide to auditor showing:
   - Input message (tokenized)
   - Intent classification reasoning
   - Data accessed (order status, policies)
   - Response generated
   - Validation checks passed
   - Response sent to customer (tokenized)

**Time to Produce Audit Report:** <5 minutes

---

## 10. Success Criteria

**Phase 2-3:**
- [ ] All agents instrumented with OpenTelemetry
- [ ] Traces visible in ClickHouse (local)
- [ ] Grafana dashboards functional
- [ ] PII tokenization tested (no leaks)
- [ ] Performance overhead <50ms per conversation

**Phase 5:**
- [ ] Traces visible in Azure Monitor (<5 min latency)
- [ ] All 3 visualization modes working (timeline, decision tree, searchable logs)
- [ ] Operator can debug customer complaint in <10 minutes
- [ ] Trace sampling reduces cost to <$15/month
- [ ] Zero PII leaks in traces (audit of 1000 samples)
- [ ] 100% of critical incidents have full traces (errors, escalations)

---

## 11. References

**Related Documentation:**
- [Architecture Requirements](./architecture-requirements-phase2-5.md) - Observability section
- [Critic/Supervisor Agent](./critic-supervisor-agent-requirements.md) - Validation tracing
- [CLAUDE.md](../CLAUDE.md) - Monitoring and observability

**External References:**
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
- [Azure Monitor Distributed Tracing](https://learn.microsoft.com/azure/azure-monitor/app/distributed-tracing)
- [Grafana Trace Visualization](https://grafana.com/docs/grafana/latest/explore/trace-integration/)
- [Jaeger Architecture](https://www.jaegertracing.io/docs/latest/architecture/)

---

**Document Status:** ✅ Complete and Approved
**Approver:** User (2026-01-22)
**Next Steps:** Instrument agents with OpenTelemetry (Phase 2)

---

*This document defines comprehensive execution tracing for all 6 agents in the multi-agent system.*
