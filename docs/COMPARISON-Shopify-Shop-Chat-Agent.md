# Comparison: AGNTCY Multi-Agent Platform vs Shopify Shop-Chat-Agent

**Date:** 2026-01-25
**Purpose:** Compare architectural approaches, features, and design decisions between these two AI-powered customer service implementations.

---

## Executive Summary

| Aspect | AGNTCY Multi-Agent Platform | Shopify Shop-Chat-Agent |
|--------|----------------------------|------------------------|
| **Architecture** | Multi-agent (6 specialized agents) | Single-agent (monolithic Claude) |
| **AI Provider** | Azure OpenAI (GPT-4o-mini, GPT-4o) | Anthropic Claude |
| **Protocol** | AGNTCY SDK (A2A, MCP) | Model Context Protocol (MCP) |
| **Deployment** | Azure Container Instances | Shopify App Platform |
| **Cost Tracking** | Built-in per-message tracking | None |
| **Content Moderation** | Defense-in-depth (Azure + Critic Agent) | None documented |
| **Target Audience** | Educational/Enterprise reference | Shopify merchants |

---

## 1. Architecture Comparison

### AGNTCY Multi-Agent Platform
```
Customer Message
       ↓
┌──────────────────────┐
│  Critic/Supervisor   │ ← Input validation, prompt injection detection
└──────────────────────┘
       ↓
┌──────────────────────┐
│ Intent Classification │ ← Categorize: ORDER_STATUS, PRODUCT_INQUIRY, etc.
└──────────────────────┘
       ↓
┌──────────────────────┐
│ Escalation Detection │ ← Detect frustration, sensitive situations
└──────────────────────┘
       ↓
┌──────────────────────┐
│ Response Generation  │ ← Generate contextual response
└──────────────────────┘
       ↓
┌──────────────────────┐
│  Critic/Supervisor   │ ← Output validation, PII check
└──────────────────────┘
       ↓
    Response
```

**Characteristics:**
- 6 specialized agents with single responsibilities
- Agent-to-Agent (A2A) protocol for inter-agent communication
- Each agent can be independently scaled, monitored, and updated
- Full execution trace with decision tree visibility
- Designed for enterprise observability requirements

### Shopify Shop-Chat-Agent
```
Customer Message
       ↓
┌──────────────────────┐
│    Claude (Single)   │ ← All logic in one LLM call
│  + MCP Tool Calling  │
└──────────────────────┘
       ↓
    Response
```

**Characteristics:**
- Single Claude instance handles all logic
- MCP (Model Context Protocol) for tool integration
- Tools: search_shop_catalog, update_cart, get_cart, search_shop_policies_and_faqs, get_order_status
- Simpler architecture, fewer moving parts
- Designed for Shopify merchant adoption

---

## 2. Feature Comparison

| Feature | AGNTCY | Shopify |
|---------|--------|---------|
| **Intent Classification** | Dedicated agent (98% accuracy) | Implicit in Claude |
| **Escalation Detection** | Dedicated agent with rules | Not implemented |
| **Content Moderation** | Critic/Supervisor + Azure filter | Not implemented |
| **Product Search** | Via Knowledge Retrieval agent | MCP tool (search_shop_catalog) |
| **Cart Operations** | Mock API integration | MCP tools (update_cart, get_cart) |
| **Order Status** | Mock API integration | MCP tool (get_order_status) |
| **Cost Tracking** | Per-message ($0.0005 typical) | None |
| **Latency Tracking** | Per-agent + total | None |
| **Execution Tracing** | Full decision tree | None |
| **Multi-language** | Planned (en, fr-CA, es) | Not mentioned |
| **Streaming Responses** | Not implemented | Yes (native SDK) |
| **Personas** | 4 test personas | 2 (Standard, "Zara") |

---

## 3. Technology Stack Comparison

| Component | AGNTCY | Shopify |
|-----------|--------|---------|
| **AI Provider** | Azure OpenAI | Anthropic Claude |
| **Models** | GPT-4o-mini (classification), GPT-4o (generation) | Claude (unspecified version) |
| **Framework** | AGNTCY SDK (Python) | React Router (JavaScript) |
| **Protocol** | A2A + MCP | MCP only |
| **Database** | Cosmos DB (planned) | SQLite via Prisma |
| **Infrastructure** | Azure Container Instances | Shopify App Platform |
| **Frontend** | Streamlit console (dev), Theme extension (prod) | Shopify Theme Extension |
| **IaC** | Terraform | Not mentioned |
| **CI/CD** | GitHub Actions → Azure DevOps | Standard Shopify deployment |

---

## 4. Prompt Engineering Comparison

### AGNTCY Prompts (Phase 3.5 Optimized)

**Intent Classification Prompt:**
- 8 intent categories with detailed descriptions
- Few-shot examples for edge cases
- Structured JSON output format
- 98% accuracy achieved

**Critic/Supervisor Prompt:**
- Prompt injection detection patterns
- Jailbreak attempt recognition
- Logic manipulation detection
- 100% true positive rate on adversarial inputs

**Response Generation Prompt:**
- Register matching (formal/casual based on input)
- Context-aware response guidelines
- Escalation awareness
- 88.4% quality score

### Shopify Prompts

**System Prompt (v1.1):**
- Professional e-commerce support persona
- Markdown formatting requirements
- Basic scope definition (products, shipping, returns)
- No safety guardrails documented

**Alternative Persona ("Zara"):**
- Enthusiastic, character-driven
- Energetic communication style
- Same capabilities, different tone

**Key Differences:**
- AGNTCY has explicit safety guardrails; Shopify has none documented
- AGNTCY has structured output formats; Shopify relies on natural language
- AGNTCY has iteratively optimized prompts (12 iterations); Shopify appears static

---

## 5. Safety & Content Moderation

### AGNTCY Approach (Defense in Depth)

1. **Layer 1: Azure Content Filter**
   - Built-in Azure OpenAI moderation
   - Blocks harmful content before processing
   - Example: Blocked "Jew git caffee" due to pattern matching

2. **Layer 2: Critic/Supervisor Agent (Input)**
   - Prompt injection detection
   - Jailbreak attempt recognition
   - Logic manipulation detection
   - Returns BLOCK with reason

3. **Layer 3: Critic/Supervisor Agent (Output)**
   - PII leakage prevention
   - Harmful content blocking
   - Profanity filtering
   - Max 3 regeneration attempts before escalation

**Test Results:**
- 100% block rate on 100+ adversarial inputs
- 0% false positive rate on legitimate queries

### Shopify Approach

- **No documented content moderation**
- No prompt injection protection
- No output validation
- Relies entirely on Claude's built-in safety (which is substantial but not customizable)

**Risk Assessment:**
- Shopify's approach is simpler but less controllable
- AGNTCY's approach provides enterprise-grade auditability

---

## 6. Cost Management

### AGNTCY

| Metric | Value |
|--------|-------|
| Cost per message | ~$0.0005-0.0006 |
| Model selection | GPT-4o-mini for classification, GPT-4o for generation |
| Monthly budget (Phase 3.5) | $20-50 |
| Monthly budget (Phase 4-5) | $310-360 |
| Cost tracking | Real-time per-message display |
| Cost alerts | 83% ($257) and 93% ($299) thresholds |

**Cost Optimization Strategies:**
- Use GPT-4o-mini for all classification/validation tasks
- Reserve GPT-4o for response generation only
- Aggressive auto-scaling (down to 1 instance)
- 7-day log retention
- Intelligent trace sampling (50%)

### Shopify

| Metric | Value |
|--------|-------|
| Cost per message | Not tracked |
| Model selection | Claude (version unspecified) |
| Monthly budget | Not documented |
| Cost tracking | None |
| Cost alerts | None |

**Observation:** Shopify's approach is "set and forget" - suitable for merchants who don't want to manage infrastructure, but provides no visibility into AI costs.

---

## 7. Observability & Debugging

### AGNTCY

**Execution Tracing:**
- Full decision tree for every conversation
- Per-agent latency breakdown
- Input/output capture (PII tokenized)
- OpenTelemetry instrumentation
- Grafana dashboards (Phase 1-3), Azure Monitor (Phase 4-5)

**Debug Information:**
```
23:52:07 • 2.39s • Intent: PRODUCT_INQUIRY (90%)
• Agents: Critic/Supervisor, Intent Classification, Escalation Detection, Response Generation
• Cost: $0.0006
```

**Benefits:**
- Diagnose why agent made specific decisions
- Identify performance bottlenecks
- Track cost trends over time
- Audit trail for compliance

### Shopify

**Execution Tracing:**
- Console logging only
- No structured tracing
- No decision visibility

**Debug Information:**
- None exposed to users

**Observation:** Shopify's simplicity trades off debuggability. Suitable for low-stakes applications but challenging for enterprise troubleshooting.

---

## 8. Scalability & Deployment

### AGNTCY

**Scaling Strategy:**
- Independent scaling per agent
- Auto-scale 1-10 instances based on load
- Event-driven architecture (NATS JetStream)
- 100 events/sec sustained throughput

**Deployment:**
- Terraform IaC for Azure resources
- Docker containers
- Azure Container Instances
- GitHub Actions → Azure DevOps pipelines

### Shopify

**Scaling Strategy:**
- Shopify App Platform manages scaling
- No user control over instances
- Single-tenant per merchant

**Deployment:**
- Shopify CLI deployment
- Standard Shopify app procedures
- No infrastructure management required

**Trade-off:** AGNTCY provides control; Shopify provides convenience.

---

## 9. When to Use Each Approach

### Use AGNTCY Multi-Agent When:
- Enterprise compliance/audit requirements
- Need for content moderation customization
- Cost visibility and optimization is critical
- Multi-language support required
- Complex escalation rules needed
- Full observability/debugging required
- Educational/reference architecture goals

### Use Shopify Shop-Chat-Agent When:
- Quick time-to-market for Shopify stores
- Simple use cases (product search, cart, orders)
- No custom moderation requirements
- Budget for AI costs is flexible/untracked
- Technical simplicity is preferred
- Already in Shopify ecosystem

---

## 10. Lessons Learned / Ideas to Adopt

### From Shopify → AGNTCY

1. **Streaming Responses**
   - Shopify uses native SDK streaming
   - AGNTCY could add streaming for better UX
   - Consider for Phase 4

2. **Persona Variants**
   - Shopify's "Zara" enthusiastic persona is interesting
   - Could add configurable tone/personality to Response Generation agent

3. **MCP Tool Simplicity**
   - Shopify's MCP tools are well-defined and focused
   - AGNTCY's Knowledge Retrieval could adopt similar patterns

### From AGNTCY → Shopify (What Shopify is missing)

1. **Content Moderation**
   - Shopify has no documented safety guardrails
   - Critic/Supervisor pattern would improve robustness

2. **Cost Tracking**
   - Per-message cost visibility is valuable
   - Merchants would benefit from usage dashboards

3. **Escalation Detection**
   - Detecting frustrated customers is business-critical
   - Human handoff for sensitive situations

4. **Execution Tracing**
   - Decision tree visibility aids debugging
   - Essential for enterprise support

---

## 11. Summary

| Dimension | Winner | Reason |
|-----------|--------|--------|
| **Simplicity** | Shopify | Single agent, minimal config |
| **Safety** | AGNTCY | Defense-in-depth, tested guardrails |
| **Cost Control** | AGNTCY | Real-time tracking, optimization |
| **Observability** | AGNTCY | Full tracing, decision trees |
| **Time-to-Market** | Shopify | Plug-and-play for merchants |
| **Customization** | AGNTCY | Per-agent configuration |
| **Scalability** | Tie | Both scale, different approaches |
| **Educational Value** | AGNTCY | Demonstrates enterprise patterns |

**Bottom Line:** These projects serve different audiences. Shopify's approach is ideal for merchants wanting quick AI capabilities. AGNTCY's approach is ideal for teams building production-grade, auditable AI systems with enterprise requirements.

---

## References

- AGNTCY Multi-Agent Platform: This repository
- Shopify Shop-Chat-Agent: https://github.com/Shopify/shop-chat-agent
- Shopify MCP Documentation: https://shopify.dev/docs/apps/build/storefront-mcp
- AGNTCY SDK: https://pypi.org/project/agntcy-app-sdk/

---

**Document Status:** Complete
**Last Updated:** 2026-01-25
