# System Architecture

**Multi-Agent Customer Service Platform on Azure using AGNTCY SDK**

**Last Updated:** 2026-01-26

**Version:** 3.0 (Phase 3 Complete, Phase 3.5 Complete, Phase 4 Infrastructure Deployed)

**Status:** Phase 1-3 Complete ✅, Phase 3.5 Complete ✅, Phase 4 Infrastructure Deployed ✅

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture Diagram](#system-architecture-diagram)
3. [Key Architecture Decisions](#key-architecture-decisions)
4. [Multi-Agent Design](#multi-agent-design)
5. [Data Architecture](#data-architecture)
6. [Event-Driven Architecture](#event-driven-architecture)
7. [Security & Privacy](#security--privacy)
8. [Technology Stack](#technology-stack)
9. [Design Patterns & Standards](#design-patterns--standards)
10. [Deployment Architecture](#deployment-architecture)
11. [Performance & Scalability](#performance--scalability)
12. [Cost Optimization](#cost-optimization)
13. [References](#references)

---

## Overview

### Purpose

This is an **educational example project** demonstrating how to build a cost-effective, production-ready multi-agent AI customer service platform on Microsoft Azure using the AGNTCY SDK. The project serves as a comprehensive guide for developers learning multi-agent architectures, Azure deployment, and cost optimization techniques.

### Business Context

**Target Use Case:** E-commerce customer service automation
**Scale:** Small e-commerce (50 products, 20 support articles, 5 policies)
**Budget Constraint:** $310-360/month (Azure Phase 4-5) - **REVISED 2026-01-22**
**Key Objective:** Demonstrate enterprise patterns within tight budget constraints

### Success Criteria

- **Response Time:** <2 minutes for customer queries
- **Automation Rate:** >70% of queries handled without human intervention
- **Availability:** 99.9% uptime during business hours
- **Cost Efficiency:** Operate within $310-360/month budget (Phase 4-5), optimize to $200-250/month post-Phase 5
- **Reproducibility:** All code and documentation enable readers to build it themselves
- **Security:** <5% false positive rate on content validation, 100% block rate for adversarial inputs
- **Observability:** Full execution traces for all conversations with <50ms overhead

---

## Current Project Status

### Phase 3: Testing & Validation - COMPLETE ✅

**Completion Date:** January 25, 2026
**Status:** 100% Complete

**Key Achievements:**
- ✅ 96% integration test pass rate (25/26 passing)
- ✅ 80% agent communication test pass rate (8/10 passing)
- ✅ 0.11ms P95 response time (well under 2000ms target)
- ✅ 3,071 req/s throughput at 100 concurrent users
- ✅ GitHub Actions CI/CD (7 jobs, PR validation, nightly regression)
- ✅ 3,508 lines of documentation (3 comprehensive guides)

**Documentation:** [Phase 3 Completion Summary](./PHASE-3-COMPLETION-SUMMARY.md)

---

### Phase 3.5: AI Model Optimization - COMPLETE ✅

**Completion Date:** January 25, 2026
**Total Cost:** ~$0.10 (well under $20-50 budget)

**Evaluation Results (All Exit Criteria Exceeded):**
- ✅ Intent Classification: 98% accuracy (target >85%)
- ✅ Critic/Supervisor: 0% FP, 100% TP (target <5% FP, 100% TP)
- ✅ Escalation Detection: 100% precision/recall (target >90%/>95%)
- ✅ RAG Retrieval: 100% retrieval@1 (target >90% retrieval@3)
- ✅ Response Quality: 88.4% (target >80%)
- ✅ Robustness: 82% appropriateness (target >80%)

**Deliverables:**
- 5 production-ready prompts in `evaluation/prompts/`
- 7 evaluation datasets (375 samples total)
- Model selection: GPT-4o-mini for all agents

**Documentation:** [Phase 3.5 Completion Summary](../evaluation/results/PHASE-3.5-COMPLETION-SUMMARY.md)

---

### Phase 4: Azure Production Setup - CONTAINERS RUNNING ✅

**Status as of 2026-01-27:** All infrastructure deployed, all containers running (0 restarts)

**Deployed Azure Resources:**
- Resource Group: `agntcy-prod-rg` (East US 2)
- VNet: `agntcy-cs-prod-vnet` (10.0.0.0/16)
- Container Registry: `acragntcycsprodrc6vcp.azurecr.io`
- Cosmos DB: `cosmos-agntcy-cs-prod-rc6vcp` (Serverless)
- Key Vault: `kv-agntcy-cs-prod-rc6vcp`
- Application Insights: `agntcy-cs-prod-appinsights-rc6vcp`
- Azure OpenAI: GPT-4o, GPT-4o-mini, text-embedding-3-large deployed

**Container Groups Running (All Healthy - 0 Restarts):**
| Container | Private IP | Port | Status | Image |
|-----------|------------|------|--------|-------|
| SLIM Gateway | 10.0.1.4 | 8443 | ✅ Running | slim-gateway:latest (custom) |
| NATS JetStream | 10.0.1.5 | 4222 | ✅ Running | nats:2.10-alpine |
| Knowledge Retrieval | 10.0.1.6 | 8080 | ✅ Running | knowledge-retrieval:v1.1.1-fix |
| Critic/Supervisor | 10.0.1.8 | 8080 | ✅ Running | critic-supervisor:v1.1.0-openai |
| Analytics | 10.0.1.9 | 8080 | ✅ Running | analytics:v1.1.0-openai |
| Intent Classifier | 10.0.1.9 | 8080 | ✅ Running | intent-classifier:v1.1.0-openai |
| Response Generator | 10.0.1.10 | 8080 | ✅ Running | response-generator:v1.1.0-openai |
| Escalation | 10.0.1.11 | 8080 | ✅ Running | escalation:v1.1.0-openai |

**Container Issues Fixed (2026-01-27):**
1. **SLIM Gateway (ExitCode 2):** Created custom Docker image with config baked in. SLIM requires `--config /config.yaml`, not `--port`. See `infrastructure/slim/Dockerfile`.
2. **Knowledge Retrieval (ExitCode 1):** Fixed Dockerfile to copy all Python files, added `__init__.py` for package imports, updated `.dockerignore` to include `test-data/knowledge-base/`.

**Completed Work:**
- ✅ All Terraform infrastructure provisioned
- ✅ All 8 container images built and pushed to ACR
- ✅ Private VNet networking configured
- ✅ Azure OpenAI integration complete
- ✅ PII Tokenization module created and tested (24 unit tests)
- ✅ Security validation (bandit scan, prompt injection tests)
- ✅ Real API integrations (Shopify, Zendesk, Mailchimp, Google Analytics)
- ✅ Container crash issues resolved (SLIM, Knowledge)

**Remaining Phase 4 Work:**
- ⏳ Multi-language support (fr-CA, es)
- ⏳ Azure DevOps pipelines
- ⏳ Application Gateway for public HTTPS endpoint

**Current Monthly Cost:** ~$214-285/month (estimated)
**Budget:** $310-360/month

**Documentation:** [Phase 4 Deployment Knowledge Base](./PHASE-4-DEPLOYMENT-KNOWLEDGE-BASE.md)

---

## System Architecture Diagram

### High-Level Architecture (Phase 4-5 Production)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Customer Channels                          │
│                    (Web Chat, Email, Mailchimp)                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Azure Application Gateway                      │
│                     (TLS 1.3, WAF, Load Balancing)                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Multi-Agent System Layer (6 Agents)             │
│                                                                     │
│  ┌────────────────┐                                                 │
│  │ Critic/        │ ◄── Input Validation (customer messages)        │
│  │ Supervisor     │ ──► Output Validation (AI responses)            │
│  │ Agent (NEW)    │                                                 │
│  └────────┬───────┘                                                 │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐   │
│  │   Intent    │  │  Knowledge  │  │  Response   │  │Escalation │   │
│  │Classificat. │  │  Retrieval  │  │ Generation  │  │   Agent   │   │
│  │    Agent    │  │    Agent    │  │    Agent    │  │           │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘   │
│         │                │                │               │         │
│         └────────────────┴────────────────┴───────────────┘         │
│                              │                                      │
│                    ┌─────────▼──────────┐                           │
│                    │   Analytics Agent  │                           │
│                    └────────────────────┘                           │
│                                                                     │
│  [OpenTelemetry Tracing: All agents instrumented for full           │
│   decision tree capture, PII tokenized, 7-day retention]            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────┴─────────┐
                    │                  │
                    ▼                  ▼
┌─────────────────────────────┐  ┌──────────────────────────────┐
│   AGNTCY Transport Layer    │  │   Event-Driven Layer         │
│   (NATS SLIM/JetStream)     │  │   (NATS JetStream)           │
│   - A2A Protocol            │  │   - Shopify Webhooks         │
│   - MCP Protocol            │  │   - Zendesk Webhooks         │
│   - Topic-based Routing     │  │   - Scheduled Triggers       │
└─────────────┬───────────────┘  └──────────────┬───────────────┘
              │                                 │
              ▼                                 ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Data Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Cosmos DB   │  │ Blob Storage │  │  Azure Key   │             │
│  │  Serverless  │  │   + CDN      │  │    Vault     │             │
│  │              │  │              │  │              │             │
│  │ - Real-time  │  │ - Knowledge  │  │ - PII Tokens │             │
│  │ - Vector DB  │  │   Base (KB)  │  │ - Secrets    │             │
│  │ - Analytics  │  │ - Static     │  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└───────────────────────────────────────────────────────────────────┘
              │                                  │
              ▼                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                    External Integrations                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Shopify    │  │   Zendesk    │  │  Mailchimp   │             │
│  │   (Orders,   │  │  (Tickets,   │  │ (Campaigns,  │             │
│  │   Products,  │  │   Support)   │  │ Subscribers) │             │
│  │   Inventory) │  │              │  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐                               │
│  │   Google     │  │  Azure       │                               │
│  │  Analytics   │  │  OpenAI      │                               │
│  │  (Tracking)  │  │  (GPT-4o,    │                               │
│  │              │  │  Embeddings) │                               │
│  └──────────────┘  └──────────────┘                               │
└───────────────────────────────────────────────────────────────────┘
```

---

## Key Architecture Decisions

### 1. Multi-Agent Framework: AGNTCY SDK

**Decision:** Use AGNTCY SDK as the foundation for all agent implementations

**Rationale:**
- **Purpose-built for multi-agent systems:** Designed specifically for agent orchestration and communication
- **Protocol support:** Native A2A (Agent-to-Agent) and MCP (Model Context Protocol) support
- **Transport flexibility:** Supports SLIM (secure), NATS (high-throughput), and HTTP transports
- **Educational value:** Demonstrates modern multi-agent patterns for blog readers
- **Python-native:** Aligns with AI/ML ecosystem (requires Python 3.12+)

**Trade-offs:**
- ❌ Newer framework (less mature than traditional message queues)
- ❌ Requires learning AGNTCY-specific patterns
- ✅ Cleaner abstractions than raw RabbitMQ/Kafka
- ✅ Built-in support for agent lifecycle and session management

**Alternative Considered:** Custom implementation with RabbitMQ + FastAPI
**Why Rejected:** Higher complexity, reinventing agent orchestration patterns

---

### 2. Cloud Platform: Microsoft Azure

**Decision:** Deploy to Azure (East US region) for production (Phase 4-5)

**Rationale:**
- **Cost-effective serverless options:** Container Instances, Cosmos Serverless, Azure Functions
- **AI/ML integration:** Native Azure OpenAI Service, Microsoft Foundry (Anthropic Claude)
- **Enterprise readiness:** Managed Identity, Key Vault, TLS 1.3, compliance certifications
- **Educational alignment:** Popular enterprise cloud platform for blog audience

**Trade-offs:**
- ❌ Not cheapest option (AWS Lambda cold starts might be faster)
- ❌ Some services expensive at small scale (avoided in design)
- ✅ Excellent serverless/pay-per-use options
- ✅ Strong security and compliance features

**Alternatives Considered:** AWS (cheaper Lambda), GCP (better AI APIs)
**Why Azure:** Balance of cost, enterprise patterns, and AI integration

---

### 3. Transport Layer: NATS (SLIM for agents, JetStream for events)

**Decision:**
- **NATS SLIM** for agent-to-agent communication (AGNTCY A2A protocol)
- **NATS JetStream** for event-driven architecture

**Rationale:**
- **Consolidation:** Single NATS deployment serves both use cases (~$0 incremental cost for events)
- **Performance:** 1M+ messages/sec throughput, <1ms latency
- **Reliability:** JetStream provides persistent streams, replay capability, dead-letter queues
- **Simplicity:** Simpler than Kafka, more features than Redis Pub/Sub

**Trade-offs:**
- ❌ Self-managed (not a managed Azure service)
- ❌ Requires Container Instance overhead
- ✅ Cost savings vs. Azure Event Grid ($0 vs. $5-15/month)
- ✅ Unified platform reduces operational complexity

**Alternative Considered:** Azure Event Grid + Azure Functions for events
**Why NATS:** Cost optimization ($22-45/month total vs. $30-60/month split)

---

### 4. Data Strategy: Multi-Store with Staleness Optimization

**Decision:** Use different data stores optimized for each agent's staleness tolerance

**Rationale:**
- **Cost efficiency:** Avoid over-provisioning for all agents
- **Performance:** Match latency requirements to store capabilities
- **Scalability:** Each store scales independently
- **Flexibility:** Can swap stores per agent without full rewrite

**Store Mapping:**

| Agent | Staleness | Store | Rationale |
|-------|-----------|-------|-----------|
| **Intent Classification** | 5-10 sec | Cosmos DB + (optional Redis cache) | Customer profiles change infrequently |
| **Knowledge Retrieval** | 1 hour | Blob Storage + CDN | Static content, hourly sync acceptable |
| **Response Generation** | Real-time | Cosmos DB (strong consistency) | Order status must be accurate |
| **Escalation** | 30 sec | Cosmos DB + (optional Redis cache) | Queue state can tolerate brief delay |
| **Analytics** | 5-15 min | Cosmos DB analytical store | Metrics are backward-looking |

**Trade-offs:**
- ❌ More complex than single database
- ❌ Requires data abstraction layer
- ✅ Optimizes cost (~$35-60/month vs. $100+ for single Redis/Cosmos)
- ✅ Better performance (CDN for static, strong consistency only where needed)

**Alternative Considered:** Single Cosmos DB for all agents
**Why Multi-Store:** 40-60% cost savings with better performance

**See:** [Data Staleness Requirements](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/data-staleness-requirements.md)

---

### 5. Vector Database: Cosmos DB for MongoDB (Vector Search)

**Decision:** Use Cosmos DB MongoDB API with vector search for RAG (Retrieval-Augmented Generation)

**Rationale:**
- **Cost:** ~$5-10/month incremental (vs. $75-100/month for Azure AI Search)
- **Consolidation:** Reuses existing Cosmos DB infrastructure
- **Sufficient for scale:** 75 documents (50 products, 20 articles, 5 policies)
- **Future-proof:** Can migrate to self-hosted Qdrant if needed (Post Phase 5)

**Trade-offs:**
- ❌ Preview feature (potential limitations)
- ❌ Less mature than Azure AI Search
- ✅ 90% cost savings ($5-10 vs. $75-100/month)
- ✅ Meets Phase 5 requirements (<500ms query latency, >90% accuracy)

**Alternatives Considered:**
- Azure AI Search (too expensive, 37-50% of budget)
- Self-hosted Qdrant ($20-30/month, more ops work)

**Why Cosmos:** Budget optimization, sufficient for Phase 5 scale

**Fallback Plan:** Migrate to Qdrant in Post Phase 5 if Cosmos preview has issues

---

### 6. PII Tokenization: Azure Key Vault

**Decision:** Tokenize all PII with random UUIDs, store mapping in Azure Key Vault (only for third-party AI services)

**Rationale:**
- **Security:** PII never leaves secure perimeter when using external AI APIs
- **Compliance:** Prevents third-party AI model providers from retaining customer data
- **Auditability:** Key Vault provides full audit logs of token access
- **Flexibility:** Can migrate to Cosmos DB if latency >100ms impacts UX

**Scope:**
- ✅ **Required:** Public OpenAI API, public Anthropic API, any third-party AI service
- ❌ **NOT required:** Azure OpenAI, Microsoft Foundry (Anthropic via Azure) - within secure perimeter

**Method:** Random UUID tokens (e.g., `TOKEN_a7f3c9e1-4b2d-8f6a-9c3e`)

**Trade-offs:**
- ❌ Adds 50-100ms latency per token lookup
- ❌ Additional complexity in request/response pipeline
- ✅ Strong security and compliance posture
- ✅ Minimal cost (~$1-5/month)

**Alternative Considered:** No tokenization (rely on AI provider data retention policies)
**Why Tokenize:** Security best practice, compliance requirement for PII handling

**See:** [Architecture Requirements - Section 1](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/architecture-requirements-phase2-5.md#1-pii-tokenization--de-identification)

---

### 7. AI Models: Differentiated by Task Complexity

**Decision:** Use different Azure OpenAI models for different agent tasks (Phase 5)

**Model Selection:**

| Agent | Model | Cost per 1M Tokens | Rationale |
|-------|-------|-------------------|-----------|
| **Intent Classification** | GPT-4o-mini | $0.15 | Fast, simple classification task |
| **Response Generation** | GPT-4o | $2.50 | High-quality customer-facing responses |
| **Knowledge Retrieval** | text-embedding-3-large | $0.13 | Vector embeddings for RAG |
| **Critic/Supervisor** (NEW) | GPT-4o-mini | $0.15 | Cost-effective content validation |

**Estimated Monthly Cost:** ~$48-62/month (8M intent + 15M response + 3M embedding + 12M validation tokens) - **REVISED 2026-01-22**

**Trade-offs:**
- ❌ More complex than single model
- ❌ Requires model routing logic
- ✅ 80% cost savings vs. using GPT-4o for all tasks
- ✅ Better performance (GPT-4o-mini is faster for simple tasks)

**Post Phase 5 Enhancement:** Fine-tuned models for brand voice, improved intent accuracy

**Alternative Considered:** Single GPT-4o model for all agents
**Why Differentiated:** Cost optimization without sacrificing quality where it matters

---

### 8. Content Validation: Critic/Supervisor Agent (Added 2026-01-22)

**Decision:** Implement a 6th dedicated agent for input and output content validation

**Rationale:**
- **Security:** Block prompt injection, jailbreak attempts, malicious instructions
- **Safety:** Filter profanity, hate speech, harmful content from responses
- **Compliance:** Prevent PII leakage in responses, enforce brand guidelines
- **Quality:** Ensure all responses meet content policy standards

**Architecture:**
- **Agent Type:** A2A protocol via AGNTCY SDK
- **Position:** Sits between customer input and Intent Agent (input validation), between Response Agent and customer (output validation)
- **Model:** GPT-4o-mini for cost-effective validation (~$0.15/1M tokens)
- **Strategy:** Block and regenerate (max 3 attempts), escalate to human if all attempts fail

**Content Policies Enforced:**
- ✅ Profanity and obscenity (adult content, slurs, hate speech)
- ✅ PII leakage (credit cards, SSNs, passwords in responses)
- ✅ Harmful content (self-harm, violence, illegal activities)
- ✅ Prompt injection (jailbreak attempts, instruction override)

**Performance Targets:**
- **Latency:** <200ms P95 for validation
- **False Positive Rate:** <5% (legitimate queries incorrectly blocked)
- **True Positive Rate:** 100% for adversarial test cases

**Cost:** ~$22-31/month (Container Instance + GPT-4o-mini API calls + tracing)

**See:** [Critic/Supervisor Requirements](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/critic-supervisor-agent-requirements.md)

---

### 9. Execution Tracing: OpenTelemetry Instrumentation (Added 2026-01-22)

**Decision:** Instrument all agents with OpenTelemetry for full execution tracing

**Rationale:**
- **Debugging:** Enable operators to trace through failed conversations and identify root causes
- **Understanding:** See why agents made specific decisions (intent classification, routing, escalation)
- **Compliance:** Audit trail for content validation and PII tokenization
- **Optimization:** Identify latency bottlenecks and cost optimization opportunities

**Architecture:**
- **Instrumentation:** OpenTelemetry SDK integrated into AGNTCY factory
- **Trace Backend:** ClickHouse + Grafana (Phase 1-3), Azure Application Insights + Monitor Logs (Phase 4-5)
- **Trace Format:** Spans with agent name, action, inputs (PII tokenized), outputs, reasoning, latency, cost
- **Retention:** 7 days (cost optimized), exportable for long-term analysis

**Visualization Modes:**
1. **Timeline View:** Conversation flow with agent handoffs, timestamps, latencies
2. **Decision Tree Diagram:** Hierarchical visualization of agent decisions and reasoning
3. **Searchable Logs:** Filter by conversation ID, agent, action type, error conditions

**Data Captured Per Span:**
- Agent name and action type (classify_intent, generate_response, validate_output)
- Inputs (PII tokenized: customer names → TOKEN_xyz)
- Outputs (intent classification, responses, validation results)
- Reasoning (why the agent made this decision)
- Latency (milliseconds per action)
- Cost (tokens used, dollar cost per LLM call)

**Performance Target:** <50ms overhead for trace instrumentation (P95)

**Cost:** ~$10-15/month (Application Insights ingestion with 50% sampling, 7-day retention)

**See:** [Execution Tracing Requirements](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/execution-tracing-observability-requirements.md)

---

## Multi-Agent Design

### Agent Responsibilities

#### 1. Intent Classification Agent
**Role:** Analyze incoming messages to determine customer intent and route to appropriate agent

**Inputs:**
- Customer message (text)
- Conversation context (previous messages)
- Customer profile (account tier, purchase history)

**Outputs:**
- Intent classification (order_status, product_inquiry, return_request, etc.)
- Confidence score (0.0-1.0)
- Routing decision (which agent should handle this)

**Technology:**
- Model: Azure OpenAI GPT-4o-mini
- Protocol: AGNTCY A2A
- Data: Cosmos DB (customer profiles cached 5-10 sec)

**Key Logic:**
```python
# Pseudo-code
intent = classify_with_gpt4o_mini(message, context)
if intent.confidence < 0.7:
    route_to(EscalationAgent)
elif intent == "order_status":
    route_to(ResponseGenerationAgent, context={"order_id": extract_order_id()})
elif intent == "product_inquiry":
    route_to(KnowledgeRetrievalAgent, context={"query": message})
```

**Performance Targets:**
- Latency: <500ms
- Accuracy: >90% intent classification
- Escalation rate: <30%

---

#### 2. Knowledge Retrieval Agent
**Role:** Search knowledge base using RAG (Retrieval-Augmented Generation) to answer product/policy questions

**Inputs:**
- Customer query (text)
- Search filters (product category, policy type)

**Outputs:**
- Retrieved documents (top 3 most relevant)
- Relevance scores
- Suggested response context for Response Generation Agent

**Technology:**
- Vector DB: Cosmos DB for MongoDB (vector search)
- Embeddings: Azure OpenAI text-embedding-3-large (1536 dimensions)
- Protocol: AGNTCY A2A
- Data: Blob Storage + CDN (knowledge base articles, 1hr cache)

**RAG Pipeline:**
```python
# Pseudo-code
query_embedding = azure_openai.embed(customer_query)
results = cosmos_vector_search(query_embedding, top_k=3)
context = format_context(results)
route_to(ResponseGenerationAgent, context=context)
```

**Knowledge Base:**
- 50 products (descriptions, ingredients, pricing, availability)
- 20 support articles (FAQs, troubleshooting guides)
- 5 policies (shipping, returns, privacy, terms, guarantees)
- **Total:** 75 documents, ~15K words, ~20K tokens

**Performance Targets:**
- Query latency: <500ms
- Retrieval accuracy: >90% (relevant docs in top 3)
- Cache hit rate: >80% (reduce embedding API calls)

---

#### 3. Response Generation Agent
**Role:** Generate customer-facing responses using retrieved context and real-time data

**Inputs:**
- Customer query
- Retrieved knowledge (from Knowledge Retrieval Agent)
- Real-time data (order status from Shopify, inventory from Cosmos DB)
- Customer profile (name, purchase history, VIP status)

**Outputs:**
- Natural language response
- Suggested follow-up actions (e.g., "Track your order here: [link]")
- Escalation flag (if unable to answer confidently)

**Technology:**
- Model: Azure OpenAI GPT-4o
- Protocol: AGNTCY A2A
- Data: Cosmos DB (real-time, strong consistency)

**Response Generation:**
```python
# Pseudo-code
prompt = f"""
You are a helpful customer service assistant.
Customer question: {query}
Relevant information: {knowledge_context}
Order status: {order_data}
Customer: {customer_profile}

Generate a helpful, concise response.
"""
response = azure_openai.chat(prompt, model="gpt-4o")
```

**Performance Targets:**
- Latency: <2 seconds (includes external API calls)
- Quality: >4.0/5.0 customer satisfaction (CSAT)
- Accuracy: 100% for factual data (order status, pricing)

---

#### 4. Critic/Supervisor Agent (Added 2026-01-22)
**Role:** Validate all customer inputs and AI-generated responses for safety, compliance, and quality

**Inputs (Input Validation):**
- Customer message (raw text)
- Conversation context (previous exchanges)
- Content policy rules (prompt injection patterns, jailbreak attempts)

**Inputs (Output Validation):**
- AI-generated response (from Response Generation Agent)
- PII detection patterns (credit cards, SSNs, passwords)
- Brand guidelines (tone, language, prohibited phrases)

**Outputs:**
- Validation result (approved/rejected)
- Violations detected (prompt_injection, profanity, pii_leak, harmful_content)
- Confidence score (0.0-1.0)
- Reasoning (why the content was blocked)
- Regeneration feedback (if rejected, how to fix)

**Technology:**
- Model: Azure OpenAI GPT-4o-mini (cost-effective)
- Protocol: AGNTCY A2A
- Strategy: Block and regenerate (max 3 attempts), escalate if all fail

**Validation Flow:**
```python
# Pseudo-code (Input Validation)
def validate_input(customer_message):
    validation = gpt4o_mini_validate(customer_message, policy="input")

    if validation.contains_prompt_injection:
        return {"approved": False, "violation": "prompt_injection",
                "reason": "Detected jailbreak attempt"}

    return {"approved": True}

# Pseudo-code (Output Validation)
def validate_output(ai_response, attempt=1):
    validation = gpt4o_mini_validate(ai_response, policy="output")

    if validation.contains_profanity:
        if attempt < 3:
            return regenerate_response(feedback="Remove profanity")
        else:
            escalate_to_human(reason="Failed validation after 3 attempts")

    if validation.contains_pii_leak:
        return {"approved": False, "violation": "pii_leak",
                "reason": "Response contains credit card number"}

    return {"approved": True}
```

**Performance Targets:**
- Latency: <200ms P95
- False Positive Rate: <5%
- True Positive Rate: 100% for adversarial tests

**Cost:** ~$5-8/month (API calls only, validation is short-prompt task)

---

#### 5. Escalation Agent
**Role:** Determine when to escalate to human agents and create Zendesk tickets

**Inputs:**
- Conversation transcript
- Intent confidence scores
- Customer frustration indicators (repeated questions, negative sentiment)
- Business rules (VIP customers always escalate, refund requests >$100 escalate)

**Outputs:**
- Escalation decision (yes/no)
- Zendesk ticket (if escalated)
- Priority level (urgent, high, normal, low)
- Assigned queue (support, service, sales)

**Technology:**
- Logic: Rule-based + ML sentiment analysis
- Protocol: AGNTCY MCP (Zendesk integration)
- Data: Cosmos DB (queue status cached 30 sec)

**Escalation Rules:**
```python
# Pseudo-code
escalate = (
    intent_confidence < 0.7 or
    contains_keywords(["refund", "complaint", "manager"]) or
    customer.is_vip or
    order.value > 100 and issue_type == "refund"
)

if escalate:
    ticket = create_zendesk_ticket(
        subject=summarize_issue(),
        description=conversation_transcript,
        priority=calculate_priority(),
        tags=["ai-escalated", customer.segment]
    )
```

**Performance Targets:**
- Escalation accuracy: >90% (minimize false escalations)
- Ticket creation time: <5 seconds
- SLA compliance: 99.9% tickets created within target

---

#### 6. Analytics Agent
**Role:** Track KPIs, generate reports, and provide system health metrics

**Inputs:**
- Conversation logs (all agent interactions)
- Customer satisfaction ratings (CSAT from Zendesk)
- System performance metrics (response times, error rates)
- Business metrics (automation rate, escalation rate)

**Outputs:**
- Real-time dashboards (Grafana)
- Daily/weekly reports (email to operators)
- Alerts (SLA breaches, cost anomalies)

**Technology:**
- Data: Cosmos DB analytical store (5-15 min staleness acceptable)
- Visualization: Grafana
- Protocol: AGNTCY A2A (receives events from all agents)

**Key Metrics:**
```python
# Tracked KPIs
automation_rate = resolved_by_ai / total_conversations
avg_response_time = sum(response_times) / count
escalation_rate = escalated_conversations / total_conversations
csat_score = sum(satisfaction_ratings) / count
cost_per_conversation = total_monthly_cost / conversation_count
```

**Performance Targets:**
- Data freshness: <15 minutes for reports
- Dashboard load time: <2 seconds
- Report generation: Daily at 8am ET, Weekly Monday 9am ET

---

### Agent Communication Patterns

#### A2A (Agent-to-Agent) Protocol
Used for **custom agent logic** and **inter-agent coordination**

**Message Format:**
```json
{
  "messageId": "msg_a7f3c9e1-4b2d-8f6a",
  "contextId": "conv_1234567890",  // Conversation thread ID
  "taskId": "task_abc123",         // Specific task within conversation
  "from": "intent-classifier",
  "to": "response-generator",
  "action": "generate_response",
  "payload": {
    "query": "Where is my order?",
    "intent": "order_status",
    "confidence": 0.95,
    "context": {
      "customer_id": "cust_5678",
      "order_id": "10234"
    }
  },
  "timestamp": "2026-01-22T14:35:00Z"
}
```

**Routing:**
- **Topic-based:** `critic-supervisor`, `intent-classifier`, `knowledge-retrieval-en`, `response-generator-en`, `escalation`, `analytics`
- **Language-specific:** Separate response agents for English, French (fr-CA), Spanish (es) in Phase 4

**Example Flow with Critic/Supervisor (Added 2026-01-22):**
```
1. Customer Message → Critic/Supervisor (input validation)
2. Critic/Supervisor → Intent Classifier (if approved)
3. Intent Classifier → Knowledge Retrieval OR Response Generation
4. Response Generation → Critic/Supervisor (output validation)
5. Critic/Supervisor → Customer (if approved) OR Regenerate (if rejected, max 3x)
```

---

#### MCP (Model Context Protocol)
Used for **external tool integrations** (Shopify, Zendesk, Mailchimp, Google Analytics)

**Example: Shopify Order Lookup**
```json
{
  "tool": "shopify",
  "action": "get_order",
  "parameters": {
    "order_id": "10234"
  },
  "context": {
    "conversation_id": "conv_1234567890"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "order_id": "10234",
    "status": "fulfilled",
    "tracking_number": "9400123456789",
    "carrier": "USPS",
    "estimated_delivery": "2026-01-25"
  }
}
```

---

## Data Architecture

### Data Stores Overview

| Store | Purpose | Consistency | Cost (est.) |
|-------|---------|-------------|-------------|
| **Cosmos DB Core (SQL API)** | Real-time order status, conversation state | Strong | $30-50/mo |
| **Cosmos DB Analytical Store** | Aggregated metrics, historical data | Eventual | Included |
| **Cosmos DB Vector Search** | RAG embeddings (MongoDB API) | Eventual | $5-10/mo |
| **Blob Storage + CDN** | Knowledge base articles, static content | Eventual | $5-10/mo |
| **Azure Key Vault** | PII token mappings, secrets | Strong | $1-5/mo |
| **Redis (optional)** | Intent/Escalation cache (Post Phase 5) | Eventual | Deferred |

---

### Data Flow Example: "Where is my order?"

```
1. Customer sends: "Where is my order #10234?"
   │
   ▼
2. Intent Classification Agent
   - Reads: Cosmos DB (customer profile, cached 5-10 sec)
   - Classifies: "order_status" intent (GPT-4o-mini)
   │
   ▼
3. Response Generation Agent
   - Reads: Cosmos DB (order status, real-time strong consistency)
   - Calls: Shopify API via MCP (get tracking number)
   - Generates: Response with GPT-4o
   │
   ▼
4. Analytics Agent
   - Writes: Cosmos DB analytical store (conversation log, 5-15 min batch)
   │
   ▼
5. Customer receives: "Your order is in transit with USPS. Tracking: 9400123456789. Expected delivery: Jan 25."
```

---

### Data Retention & Archival

| Data Type | Retention | Storage | Archive Policy |
|-----------|-----------|---------|----------------|
| **Conversation logs** | 90 days hot | Cosmos DB | → Blob (Cold) after 30 days |
| **Analytics metrics** | 1 year | Cosmos analytical | → Blob (Archive) after 90 days |
| **Knowledge base** | Indefinite | Blob Storage | CDN cached 1 hour |
| **PII token mappings** | Until customer deletion | Key Vault | Soft-delete 90 days |
| **Event logs** | 7 days | NATS JetStream | Purged after 7 days |

**Cost Optimization:**
- Blob lifecycle policy: Hot → Cool (30 days) → Archive (90 days)
- Cosmos TTL: Auto-delete conversation logs after 90 days
- Log Analytics: 7-day retention (not 30-day default)

---

## Event-Driven Architecture

### Event Sources (Phase 5)

**12 event types** trigger proactive agent actions:

#### Shopify Webhooks (4 types)
- `customers/created`, `customers/updated`, `customers/deleted` → Update customer cache
- `orders/created`, `orders/paid`, `orders/fulfilled`, `orders/cancelled` → Notify customer, update analytics
- `inventory_levels/update` → Trigger back-in-stock emails
- `customers/update` (tags changed) → Update VIP status, adjust response priority

#### Zendesk Webhooks (5 types)
- `tickets/created`, `tickets/updated`, `tickets/closed` → Track escalation lifecycle
- `tickets/priority_changed` → Alert on-call support
- `tickets/assigned` → Update agent availability cache
- `satisfaction_ratings/created` → Update CSAT metrics

#### Scheduled Triggers (3 types)
- **Promotions:** Start/end time-limited promo codes
- **Reports:** Daily (8am ET), Weekly (Mon 9am ET) analytics reports
- **Batch Sync:** Hourly product catalog sync, nightly analytics export

#### RSS Feeds (1 type)
- **Company News:** Auto-update knowledge base when new policies published

---

### Event Routing Architecture

```
┌─────────────────┐
│  Event Sources  │
│  (Webhooks,     │
│   Cron, RSS)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Event Ingestion│   ← Azure Function HTTP endpoint
│  Service        │   ← Timer triggers for cron
│                 │   ← RSS polling every 15 min
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  NATS JetStream │   ← Durable event storage
│  Event Bus      │   ← 7-day retention
│                 │   ← Replay capability
└────────┬────────┘
         │
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Intent Agent │   │Knowledge Ag. │   │Analytics Ag. │
│ (Subscriber) │   │ (Subscriber) │   │ (Subscriber) │
└──────────────┘   └──────────────┘   └──────────────┘
```

**NATS Subject Hierarchy:**
```
events.shopify.customers.{created|updated|deleted}
events.shopify.orders.{created|paid|fulfilled|cancelled}
events.shopify.inventory.updated
events.zendesk.tickets.{created|updated|closed|priority_changed|assigned}
events.zendesk.satisfaction_ratings.created
events.scheduled.promotions.{start|end}
events.scheduled.reports.{daily|weekly}
events.scheduled.sync.{products|analytics}
events.rss.company_news.updated
```

---

### Throttling & Reliability

**Throttling Limits:**
- Global: 100 events/sec
- Per agent: 20 events/sec
- Concurrent handlers: 5 per agent
- Queue depth: 1000 events per topic

**Overflow Behavior:**
- Drop oldest events when queue full
- Log warning + operator alert if >50 events dropped in 5 min

**Retry Policy:**
- Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 5 retries)
- Dead-letter queue (DLQ) for failed events
- Operator notification at >10 DLQ events

**Event Retention:**
- 7 days in NATS JetStream
- Replay capability for debugging
- Auto-purge after 7 days

**See:** [Event-Driven Requirements](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/event-driven-requirements.md)

---

## Security & Privacy

### Threat Model

**Assets to Protect:**
1. Customer PII (names, emails, addresses, payment info)
2. Business data (order history, conversation logs)
3. System credentials (API keys, connection strings)
4. AI model access (prevent abuse, cost overruns)

**Threat Actors:**
1. External attackers (internet-facing endpoints)
2. Malicious insiders (privileged access abuse)
3. Third-party AI providers (data retention concerns)
4. Accidental exposure (misconfigured storage, logs)

---

### Security Controls

#### 1. Authentication & Authorization
- **Azure Managed Identity:** All agents use managed identity (no secrets in code)
- **RBAC:** Least-privilege access per agent (Intent Agent can't delete orders)
- **API Key Rotation:** Quarterly rotation for Shopify, Zendesk, Mailchimp keys
- **No Passwords:** Passwordless auth only (managed identity, OAuth, API keys in Key Vault)

#### 2. Data Protection
- **PII Tokenization:** All PII tokenized before third-party AI calls (Azure Key Vault)
- **Encryption at Rest:** All data stores (Cosmos DB, Blob, Key Vault) encrypted (AES-256)
- **Encryption in Transit:** TLS 1.3 for all connections (no TLS 1.0/1.1)
- **Field-Level Encryption:** Sensitive fields double-encrypted in Cosmos DB

#### 3. Network Security
- **Private Endpoints:** Backend services not internet-accessible (Cosmos, Blob, Key Vault)
- **NSG Rules:** Container Instances only accept traffic from App Gateway
- **WAF (Web Application Firewall):** Azure App Gateway blocks OWASP Top 10
- **DDoS Protection:** Azure DDoS Standard (if budget allows in Phase 5)

#### 4. Logging & Monitoring
- **Audit Logs:** All Key Vault access logged to Azure Monitor
- **Conversation Logs:** PII tokenized before logging (safe for analytics)
- **Anomaly Detection:** Alert on unusual API usage, cost spikes, error rates
- **SIEM Integration:** Logs exportable to Sentinel (if customer has it)

#### 5. Secrets Management
- **Azure Key Vault:** All secrets (API keys, connection strings, PII tokens)
- **No Hardcoded Secrets:** Pre-commit hooks (git-secrets, detect-secrets)
- **Secret Rotation:** Quarterly rotation + audit trail
- **Access Control:** Only specific managed identities per secret

#### 6. Compliance & Governance
- **GDPR:** Customer data deletion within 30 days of request
- **Data Residency:** All data in East US region (no geo-replication)
- **Right to Access:** Customers can request conversation transcripts (PII de-tokenized)
- **Audit Readiness:** 90-day audit log retention

---

### Security Testing

**Phase 3 (Local):**
- Dependency scanning: Dependabot, Snyk
- Secret scanning: git-secrets, detect-secrets (pre-commit hooks)

**Phase 5 (Production):**
- OWASP ZAP: Web vulnerability scanning
- Azure Defender: Runtime threat detection
- Penetration testing: Annual third-party audit (if budget allows Post Phase 5)

---

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| **Multi-Agent Framework** | AGNTCY SDK | Latest | Purpose-built for multi-agent systems |
| **Programming Language** | Python | 3.12+ | AGNTCY requirement, AI/ML ecosystem |
| **Cloud Platform** | Microsoft Azure | - | Cost-effective serverless, enterprise features |
| **IaC (Infrastructure-as-Code)** | Terraform | Latest | Declarative, version-controlled infrastructure |
| **Containerization** | Docker + Docker Compose | Latest | Local dev, consistent environments |
| **CI/CD (Phase 1-3)** | GitHub Actions | - | Free for public repos |
| **CI/CD (Phase 4-5)** | Azure DevOps Pipelines | - | Better Azure integration |

---

### Azure Services

| Service | Purpose | Tier | Monthly Cost (est.) |
|---------|---------|------|---------------------|
| **Container Instances** | Agent compute (5 agents) | Pay-per-second | $50-80 |
| **Cosmos DB** | Real-time + vector + analytics | Serverless | $30-50 |
| **Blob Storage + CDN** | Knowledge base (static) | Standard + Standard | $5-10 |
| **Azure Key Vault** | Secrets + PII tokens | Standard | $1-5 |
| **Azure Functions** | Event ingestion, cron | Consumption Plan | $5-10 |
| **Application Gateway** | Load balancer, WAF | Standard_v2 | $20-40 |
| **Azure Monitor + Log Analytics** | Observability | Pay-per-GB (7-day retention) | $10-20 |
| **Azure OpenAI** | GPT-4o, GPT-4o-mini, embeddings | Pay-per-token | $20-50 |
| **NATS (self-hosted)** | Transport + events (Container Instance) | N/A | Included in Container $ |
| **TOTAL** | | | **$141-265/mo** |

**Budget Target:** $265-300/month (allows headroom for spikes)

---

### External APIs

| Service | Purpose | Cost | Notes |
|---------|---------|------|-------|
| **Shopify** | Product catalog, orders, inventory | Free (Dev Store) | Partner account |
| **Zendesk** | Support tickets, escalations | $0-49/mo | Trial/Sandbox account |
| **Mailchimp** | Email campaigns, subscribers | Free (up to 500 contacts) | - |
| **Google Analytics** | Customer behavior tracking | Free | GA4 property |

---

### Development Tools

| Tool | Purpose | License |
|------|---------|---------|
| **VS Code** | IDE | Free |
| **Docker Desktop** | Local containers | Free for personal/small biz |
| **GitHub Desktop** | Git GUI | Free |
| **Postman** | API testing | Free |
| **Grafana** | Observability (local + Azure) | Free (OSS) |
| **ClickHouse** | Telemetry storage (local) | Free (OSS) |

---

### Python Libraries

**Core Dependencies:**
```
agntcy-app-sdk>=1.0.0     # Multi-agent framework
fastapi>=0.100.0          # API framework
uvicorn>=0.23.0           # ASGI server
pydantic>=2.0.0           # Data validation
azure-identity>=1.13.0    # Managed Identity
azure-keyvault>=4.0.0     # Key Vault SDK
azure-cosmos>=4.5.0       # Cosmos DB SDK
azure-storage-blob>=12.0  # Blob Storage SDK
openai>=1.0.0             # Azure OpenAI SDK
httpx>=0.24.0             # Async HTTP client
```

**Testing:**
```
pytest>=7.4.0             # Test framework
pytest-asyncio>=0.21.0    # Async test support
pytest-cov>=4.1.0         # Coverage reporting
locust>=2.15.0            # Load testing
```

**See:** `requirements.txt` for full dependency list

---

## Design Patterns & Standards

### Architectural Patterns

#### 1. Factory Pattern (AGNTCY SDK)
**Usage:** Single `AgntcyFactory` instance per application

```python
# Singleton factory
from agntcy_app_sdk.factory import AgntcyFactory

factory = AgntcyFactory(
    transport="slim",  # or "nats" for high-throughput
    enable_tracing=True,
    max_sessions=100
)

# Each agent gets factory instance
intent_agent = factory.create_agent("intent-classifier", protocol="a2a")
```

**Rationale:** Centralized agent lifecycle management, consistent configuration

---

#### 2. Data Abstraction Layer Pattern
**Usage:** Hide store implementation details from agents

```python
# Abstract interface
class DataStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Dict]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Dict, ttl: int = None):
        pass

# Implementations
class CosmosStore(DataStore):
    # Real-time, strong consistency
    pass

class BlobStore(DataStore):
    # Static content, 1hr cache
    pass

class MockStore(DataStore):
    # Phase 1-3 in-memory
    pass

# Agent uses abstraction
class ResponseGenerationAgent:
    def __init__(self, store: DataStore):
        self.store = store  # Injected, doesn't know implementation
```

**Rationale:** Swap stores per environment (mock → Cosmos), optimize per agent

---

#### 3. Event-Driven Architecture Pattern
**Usage:** Decouple agents from external system changes

```python
# Publisher (Shopify webhook handler)
async def handle_order_fulfilled(webhook_data):
    event = Event(
        type="shopify.orders.fulfilled",
        payload=webhook_data,
        timestamp=datetime.utcnow()
    )
    await nats.publish("events.shopify.orders.fulfilled", event)

# Subscriber (Analytics Agent)
async def on_order_fulfilled(event: Event):
    order = event.payload
    await update_metrics(order_id=order["id"], status="fulfilled")
```

**Rationale:** Agents react to changes without polling, scalable event processing

---

#### 4. Retry with Exponential Backoff
**Usage:** Resilient external API calls

```python
async def call_shopify_api(order_id: str, max_retries=5):
    for attempt in range(max_retries):
        try:
            return await shopify.get_order(order_id)
        except (Timeout, ConnectionError) as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
            await asyncio.sleep(wait)
```

**Rationale:** Handle transient failures (network issues, rate limits)

---

### Coding Standards

#### Python Style
- **Formatter:** black (line length 100)
- **Linter:** flake8 + pylint
- **Type Hints:** Use for public APIs, optional for internal
- **Docstrings:** Google style, focus on "why" not "what"
- **Async:** Use `async`/`await` for all AGNTCY SDK calls

**Example:**
```python
async def classify_intent(message: str, context: Dict) -> IntentResult:
    """
    Classify customer message intent using GPT-4o-mini.

    Args:
        message: Customer's natural language query
        context: Conversation history and customer profile

    Returns:
        IntentResult with classification, confidence, and routing

    Raises:
        ClassificationError: If model API call fails after retries

    Note:
        Uses cached customer profile (5-10 sec staleness acceptable).
        Falls back to escalation if confidence < 0.7.
    """
    # Implementation
```

#### Naming Conventions
- **Agents:** `{purpose}_agent.py` (e.g., `intent_classification_agent.py`)
- **Topics:** `{agent-name}` (e.g., `intent-classifier`, `response-generator-en`)
- **Containers:** `{agent-name}:v{version}-{commit-sha}` (e.g., `intent-classifier:v1.0.0-abc123`)
- **Environment Vars:** `UPPER_SNAKE_CASE` (e.g., `SLIM_ENDPOINT`, `COSMOS_CONNECTION_STRING`)
- **Functions:** `snake_case` (e.g., `classify_intent`, `retrieve_knowledge`)
- **Classes:** `PascalCase` (e.g., `IntentAgent`, `CosmosStore`)

#### Error Handling
```python
# Good: Specific exceptions, clear messages
try:
    order = await cosmos.get_order(order_id)
except CosmosResourceNotFound:
    logger.warning(f"Order {order_id} not found in Cosmos DB")
    raise OrderNotFoundError(f"Order {order_id} does not exist")
except CosmosException as e:
    logger.error(f"Cosmos DB error: {e}", exc_info=True)
    raise DatabaseError("Failed to retrieve order") from e

# Bad: Bare except, silent failures
try:
    order = await cosmos.get_order(order_id)
except:
    pass  # ❌ Silent failure
```

#### Tracing with OpenTelemetry (Added 2026-01-22)
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# Wrap agent actions in spans
async def classify_intent(message: str, context: Dict) -> IntentResult:
    with tracer.start_as_current_span("classify_intent") as span:
        # PII tokenization before adding to span
        span.set_attribute("message", tokenize_pii(message))
        span.set_attribute("customer_id", context.get("customer_id"))

        # Perform classification
        result = await gpt4o_mini_classify(message, context)

        # Capture decision details
        span.set_attribute("intent", result.intent)
        span.set_attribute("confidence", result.confidence)
        span.set_attribute("reasoning", result.reasoning)
        span.set_attribute("latency_ms", result.latency)
        span.set_attribute("cost_tokens", result.tokens)

        return result
```

**Key Principles:**
- All agent actions wrapped in spans for full traceability
- PII tokenized before adding to span attributes (names → TOKEN_xyz)
- Capture inputs, outputs, reasoning, latency, cost for every decision
- Enable with `AgntcyFactory(enable_tracing=True)`

---

#### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Structured logging with context
logger.info(
    "Intent classified",
    extra={
        "conversation_id": conv_id,
        "intent": intent.name,
        "confidence": intent.confidence,
        "latency_ms": elapsed_time
    }
)
```

**Log Levels:**
- DEBUG: Detailed troubleshooting info (disabled in prod)
- INFO: Normal operation events (conversation started, intent classified)
- WARNING: Unexpected but recoverable (cache miss, retry attempt)
- ERROR: Operation failed but system continues (API timeout, invalid data)
- CRITICAL: System-level failure (database unreachable, out of memory)

---

## Deployment Architecture

### Phase 1-3: Local Development

```
┌────────────────────────────────────────────────────────────────┐
│                    Docker Compose (13 services)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Intent Agent │  │Knowledge Ag. │  │ Response Ag. │          │
│  │  Container   │  │  Container   │  │  Container   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                           │                                    │
│                ┌──────────▼──────────┐                         │
│                │   RabbitMQ (mock)   │                         │
│                └─────────────────────┘                         │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Mock Shopify │  │ Mock Zendesk │  │Mock Mailchimp│          │
│  │     API      │  │     API      │  │     API      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Grafana    │  │  ClickHouse  │  │ OTLP         │          │
│  │ (localhost:  │  │  (Telemetry) │  │ Collector    │          │
│  │   3001)      │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────────────────────────────────────────┘
```

**Commands:**
```bash
# Start all services
docker-compose up

# Run tests
pytest tests/

# View logs
docker-compose logs -f intent-classifier

# Stop all services
docker-compose down
```

**Cost:** $0/month (local hardware only)

---

### Phase 4-5: Azure Production

```
┌───────────────────────────────────────────────────────────────────┐
│                      Azure Resource Group (East US)               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Application Gateway (WAF, TLS, LB)             │  │
│  └────────────────────────────┬────────────────────────────────┘  │
│                               │                                   │
│  ┌────────────────────────────┼───────────────────────────────┐   │
│  │       Container Instances (5 agents, 1-3 instances each)   │   │
│  │                            │                               │   │
│  │  ┌──────────────┐  ┌──────▼───────┐  ┌──────────────┐      │   │
│  │  │ Intent Agent │  │ Knowledge Ag.│  │ Response Ag. │      │   │
│  │  │ (1-3 inst.)  │  │ (1-3 inst.)  │  │ (1-3 inst.)  │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  │                                                            │   │
│  │  ┌──────────────┐  ┌──────────────┐                        │   │
│  │  │Escalation Ag.│  │ Analytics Ag.│                        │   │
│  │  │ (1-3 inst.)  │  │ (1-3 inst.)  │                        │   │
│  │  └──────────────┘  └──────────────┘                        │   │
│  │                                                            │   │
│  │  ┌──────────────────────────────────────────────────┐      │   │
│  │  │   NATS JetStream (Container Instance)            │      │   │
│  │  │   - AGNTCY transport (SLIM)                      │      │   │
│  │  │   - Event bus (JetStream)                        │      │   │
│  │  └──────────────────────────────────────────────────┘      │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                      Data Layer                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │  │
│  │  │  Cosmos DB   │  │ Blob Storage │  │ Azure Key    │       │  │
│  │  │  Serverless  │  │   + CDN      │  │    Vault     │       │  │
│  │  │              │  │              │  │              │       │  │
│  │  │ - Real-time  │  │ - Knowledge  │  │ - Secrets    │       │  │
│  │  │ - Vector DB  │  │   Base       │  │ - PII Tokens │       │  │
│  │  │ - Analytics  │  │              │  │              │       │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              Azure Functions (Event Ingestion)               │ │
│  │  - HTTP triggers (Shopify/Zendesk webhooks)                  │ │
│  │  - Timer triggers (cron jobs, RSS polling)                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │         Azure Monitor + Log Analytics + App Insights         │ │
│  │         (7-day retention, cost alerts, dashboards)           │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
         │                       │                 │
         ▼                       ▼                 ▼
┌──────────────┐         ┌──────────────┐    ┌──────────────────┐
│  Shopify API │         │ Zendesk API  │    │ Azure OpenAI     │
│  (Real)      │         │  (Real)      │    │ (GPT-4o, mini,   │
│              │         │              │    │  embeddings)     │
└──────────────┘         └──────────────┘    └──────────────────┘
```

**Deployment Process:**
```bash
# Terraform: Provision infrastructure
cd terraform/phase4_prod
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Azure DevOps: Build + deploy agents
az pipelines run --name "Multi-Agent-CI-CD"

# Verify deployment
az container list --resource-group agntcy-prod-rg
az cosmosdb list --resource-group agntcy-prod-rg
```

**Cost:** $310-360/month (Phase 4-5 target) - **REVISED 2026-01-22**

---

## Performance & Scalability

### Performance Targets

| Metric | Target | Phase |
|--------|--------|-------|
| **Response Time** | <2 minutes | Phase 1-5 |
| **Automation Rate** | >70% | Phase 3-5 |
| **Availability** | 99.9% (business hours) | Phase 5 |
| **Intent Classification Latency** | <500ms | Phase 5 |
| **RAG Query Latency** | <500ms | Phase 5 |
| **Content Validation Latency** | <200ms P95 | Phase 5 |
| **Trace Instrumentation Overhead** | <50ms P95 | Phase 5 |
| **Event Processing Latency** | <5 seconds | Phase 5 |
| **Concurrent Conversations** | 100+ | Phase 5 |
| **Throughput** | 1000 requests/min | Phase 5 |

---

### Scalability Strategy

#### Horizontal Scaling
- **Container Instances:** Auto-scale 1-3 instances per agent (6 agents total - REVISED 2026-01-22)
- **Cosmos DB:** Serverless auto-scales RU/s (no manual provisioning)
- **NATS:** Single instance sufficient for Phase 5 (1M+ msgs/sec capacity)

**Auto-Scale Rules:**
```
IF avg_cpu > 70% for 5 minutes:
    scale_out(+1 instance, max=3)

IF avg_cpu < 30% for 10 minutes:
    scale_in(-1 instance, min=1)
```

#### Vertical Scaling
- **Container CPU/Memory:** Start small (1 vCPU, 2GB RAM), profile, adjust
- **Cosmos DB:** Serverless handles spikes automatically

#### Caching Strategy
- **Knowledge Base:** CDN 1-hour cache (Blob Storage)
- **Customer Profiles:** Optional Redis cache (5-10 sec TTL, Post Phase 5)
- **Vector Embeddings:** Pre-computed, stored in Cosmos (not re-generated on query)

---

### Bottleneck Analysis

**Potential Bottlenecks:**
1. **Azure OpenAI Rate Limits:** 10K tokens/min (gpt-4o), 60K tokens/min (gpt-4o-mini)
   - **Mitigation:** Use GPT-4o-mini for simple tasks, cache common responses
2. **Cosmos DB Throttling:** 400 RU/s free tier, serverless scales but costs increase
   - **Mitigation:** Optimize queries, use analytical store for reports
3. **NATS Single Instance:** Single point of failure
   - **Mitigation:** Phase 5 HA setup (3-node cluster, ~$30-60/month extra)
4. **External API Latency:** Shopify/Zendesk APIs can be slow (500ms-2s)
   - **Mitigation:** Async calls, cache results, use webhooks for updates

---

## Cost Optimization

### Budget Breakdown (Phase 4-5) - **REVISED 2026-01-22**

| Category | Services | Monthly Cost | % of Budget |
|----------|----------|--------------|-------------|
| **Compute** | Container Instances (6 agents), Azure Functions | $75-110 | 27% |
| **Data** | Cosmos DB, Blob, Key Vault | $36-65 | 17% |
| **AI/ML** | Azure OpenAI (tokens, incl. Critic/Supervisor) | $48-62 | 17% |
| **Events** | NATS (Container), Event storage | $12-25 | 6% |
| **Networking** | App Gateway, egress | $20-40 | 10% |
| **Monitoring** | Azure Monitor, Log Analytics, Tracing | $32-43 | 12% |
| **Security** | Critic/Supervisor validation overhead | Included | - |
| **Headroom** | Buffer for spikes | $35-45 | 11% |
| **TOTAL** | | **$310-360** | 100% |

**Target:** $310-360/month Phase 4-5, optimize to $200-250/month post-Phase 5

---

### Cost Optimization Techniques

#### 1. Serverless & Pay-Per-Use
- ✅ Container Instances (vs. App Service Always On)
- ✅ Cosmos DB Serverless (vs. provisioned RU/s)
- ✅ Azure Functions Consumption Plan (vs. Premium)
- ✅ Blob Storage + CDN (vs. premium storage)

**Savings:** ~40% vs. provisioned/premium alternatives

---

#### 2. Aggressive Auto-Scaling DOWN
```
# Azure Container Instances auto-scale policy
min_instances: 1  # Not 3
max_instances: 3
scale_down_cooldown: 10 minutes  # Aggressively scale down

# Night-time shutdown (2am-6am ET)
IF current_hour in [2, 3, 4, 5]:
    scale_to(min_instances=0)  # Full shutdown during idle
```

**Savings:** ~20% (off-peak shutdown)

---

#### 3. Data Retention & Archival
- Logs: 7 days (not 30-day default) = $10-15/month savings
- Conversation logs: Hot (30 days) → Cool (90 days) → Archive
- Cosmos DB TTL: Auto-delete stale data

**Savings:** ~15% storage costs

---

#### 4. Model Selection
- Use GPT-4o-mini ($0.15/1M) instead of GPT-4o ($2.50/1M) for 75% of tasks (intent, validation)
- Use GPT-4o only for customer-facing responses (quality matters)
- Cache common responses (reduce API calls by 30-50%)

**Savings:** ~70% AI costs vs. using GPT-4o for all tasks

---

#### 5. Single Region, No Geo-Replication
- Deploy only to East US (not multi-region)
- No Azure Front Door, no Traffic Manager
- Accept 99.9% SLA (not 99.99%)

**Savings:** ~$50-100/month

---

### Cost Monitoring

**Azure Cost Management:**
- **Budget:** $360/month hard limit (REVISED 2026-01-22)
- **Alerts:** 83% ($299), 93% ($335), 100% ($360)
- **Weekly Review:** Every Monday 9am ET
- **Daily Monitoring:** Grafana dashboard with cost metrics, trace sampling costs

**Cost Allocation Tags:**
```
Environment: Production
Project: AGNTCY-Multi-Agent
Phase: Phase-4
CostCenter: Engineering
Owner: <your-email>
```

**Post Phase 5 Optimization Target:** $200-250/month (REVISED 2026-01-22)

---

## Development Console

### Overview

**Purpose:** Interactive development and testing interface for Phase 2-3 implementation

The Development Console is a Streamlit-based web application that provides developers with real-time monitoring, interactive testing, and debugging capabilities during the development phase. It serves as the primary interface for validating agent implementations, testing conversation flows, and monitoring system health.

**Status:** ✅ Operational (Phase 2-3)
**Access:** http://localhost:8080 (local development)

**Current Implementation Status (as of 2026-01-24):**
- ✅ All 5 pages fully implemented and tested
- ✅ Real A2A protocol integration with live agents
- ✅ 4 test personas operational (Sarah, Mike, Jennifer, David)
- ✅ OpenTelemetry trace visualization working
- ✅ Mock API health checks functional
- ✅ Agent performance metrics dashboard operational

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│          Development Console (Streamlit Web App)                        │
│                    http://localhost:8080                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📊 Dashboard  │  💬 Chat  │  📈 Metrics  │  🔍 Traces  │ ⚙️ Status   │
│  ─────────────────────────────────────────────────────────────────────  │
│                           │                                             │
│                           ▼                                             │
│               ┌─────────────────────┐                                   │
│               │ AGNTCY Integration  │                                   │
│               │   (A2A Protocol)    │                                   │
│               └─────────────────────┘                                   │
│                         │                                               │
└─────────────────────────┼───────────────────────────────────────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│    SLIM     │   │ ClickHouse  │   │   Docker    │
│  (A2A Msgs) │   │  (OTel)     │   │    APIs     │
│             │   │             │   │             │
│ :46357      │   │ :9000/:8123 │   │  Health     │
└──────┬──────┘   └─────────────┘   └─────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Multi-Agent System              │
│  Intent → Knowledge → Response          │
│  Escalation → Analytics                 │
└─────────────────────────────────────────┘
```

### Features

#### 1. Dashboard (🏠)
**Real-time system overview and metrics visualization**

- **Key Metrics**: Total conversations, success rate, average response time, automation rate
- **Activity Timeline**: 24-hour message volume trends (bar chart)
- **Intent Distribution**: Breakdown of customer intent types (pie chart)
- **Response Time Trends**: Historical latency tracking (line chart)

**Data Sources:**
- Real-time: A2A protocol messages from agents
- Historical: OpenTelemetry traces from ClickHouse

#### 2. Chat Interface (💬)
**Interactive conversation testing with real/simulated agents**

- **Test Personas**: 4 pre-configured customer personas
  - Sarah (Coffee Enthusiast): Technical brewing questions
  - Mike (Convenience Seeker): Quick order status queries
  - Jennifer (Gift Buyer): Product recommendations
  - David (Business Customer): Bulk orders and pricing
- **Real Agent Communication**: Sends via A2A protocol to live agents
- **Fallback Simulation**: Graceful degradation when agents unavailable
- **Response Tracking**: Processing time, confidence scores, escalation indicators

**Message Flow:**
```
User Input → CustomerMessage → Intent Agent → Knowledge Agent → Response Agent → Display
```

#### 3. Agent Metrics (📊)
**Performance monitoring for all 5 agents**

**Metrics Per Agent:**
- **Latency**: Average, P95, P99 response times
- **Success Rate**: Percentage of successful message handling
- **Cost Per Request**: Estimated cost (AI model calls in Phase 4-5)
- **Request Volume**: Total messages processed

**Visualizations:**
- Bar charts: Latency comparison across agents
- Pie charts: Cost distribution by agent
- Tables: Detailed metrics breakdown

#### 4. Trace Viewer (🔍)
**Debug conversation flows step-by-step**

- **Session Selection**: Choose conversation by session ID
- **Timeline Visualization**: Plotly timeline showing agent execution sequence
- **Step Details**: Expand each step for inputs, outputs, metadata
- **Performance Analysis**: Latency and cost per step

**Example Trace:**
```
Session: conv-abc123
├── Step 1: Intent Classification (25ms)
│   Input: "Where is my order?"
│   Output: {intent: ORDER_STATUS, confidence: 0.95}
├── Step 2: Knowledge Retrieval (150ms)
│   Input: {query: "order lookup", order_number: "10234"}
│   Output: {order: {...}, tracking: {...}}
└── Step 3: Response Generation (75ms)
    Input: {intent: ORDER_STATUS, knowledge: [...]}
    Output: "Hi Sarah, your order #10234 is in transit..."
```

#### 5. System Status (⚙️)
**Infrastructure and service health monitoring**

- **Mock API Status**: Health checks for Shopify, Zendesk, Mailchimp, Google Analytics
- **Infrastructure Services**: SLIM, NATS, ClickHouse, OTel Collector, Grafana
- **Agent Containers**: Docker container status for all agents
- **Configuration Display**: Environment variables and endpoints

### Integration Points

#### SLIM / A2A Protocol
- Creates A2A messages using `shared/utils.py`
- Sends to agent topics: `intent-classifier`, `knowledge-retrieval`, `response-generator-en`
- Fallback: Simulated responses when SLIM unavailable

#### OpenTelemetry / ClickHouse
- Queries `otel_traces` table for conversation traces
- Queries `otel_metrics` table for agent performance
- Parses OpenTelemetry span data to reconstruct flows

#### Docker API
- Uses Docker Python SDK to query container status
- Displays container health in System Status page

#### Mock API Health Checks
- HTTP GET requests to `/health` endpoints
- Validates mock services are responding

### Usage

**Quick Start (PowerShell):**
```powershell
# Start console locally (recommended)
.\start-console.ps1

# Start console with Docker
.\start-console.ps1 -Mode docker
```

**Manual Start:**
```powershell
# Install dependencies
pip install -r console/requirements.txt

# Run Streamlit
streamlit run console/app.py --server.port 8080
```

**Docker Compose:**
```bash
# Start console service
docker-compose up --build console
```

### Configuration

**Environment Variables:**
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

### Phase 2 Test Scenarios

**Scenario 1: Order Status Inquiry (Issue #24)**
1. Select persona: Mike
2. Send: "Where is my order #10234?"
3. Verify: Response < 500ms, includes tracking and ETA

**Scenario 2: Return Auto-Approval (Issue #29)**
1. Select persona: Sarah
2. Send: "I want to return order #10125"
3. Verify: Auto-approved (≤$50), RMA number generated

**Scenario 3: Return Escalation (Issue #29)**
1. Select persona: David
2. Send: "I need to return order #10234"
3. Verify: Escalated (>$50), mentions support team

**Scenario 4: Product Information (Issue #25)**
1. Select persona: Jennifer
2. Send: "Tell me about your coffee pods"
3. Verify: Lists multiple products with prices

### File Structure

```
console/
├── app.py                 # Main Streamlit application (500+ lines)
├── agntcy_integration.py  # AGNTCY system integration (600+ lines)
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── README.md             # User-facing documentation
```

### Technology Stack

- **Framework**: Streamlit 1.29+ (Python web framework)
- **Visualization**: Plotly (interactive charts)
- **Data Processing**: Pandas (metrics aggregation)
- **AGNTCY SDK**: A2A protocol client (via `shared/factory.py`)
- **Observability**: OpenTelemetry, ClickHouse
- **Container**: Docker (multi-stage build)

### Phase Roadmap

**Phase 2** ✅ (95% Complete - 2026-01-24):
- ✅ Console operational with 5 pages
- ✅ Test personas implemented (4 personas)
- ✅ Real agent integration via A2A protocol
- ✅ Issue #34 (Loyalty Program) validated
- ✅ Integration tests: 25/26 passing (96% pass rate)
- ✅ E2E baseline established: 20 scenarios (5% pass rate expected for templates)

**Phase 3** ⏳ (Day 3-4/15 Complete - 2026-01-25):
- ✅ Environment validated (8/9 Docker services healthy)
- ✅ Phase 3 kickoff documents created
- ✅ E2E test analysis and validation (Day 2) - GO/NO-GO decision complete
- ✅ Multi-turn conversation testing (Day 3-4) - 10 scenarios, 3/10 passing
- ⏳ Agent communication testing (Day 5)
- ⏳ Performance benchmarking dashboard (Day 6-7)
- ⏳ Load testing integration with Locust (Day 8-9)
- ⏳ GitHub Actions CI/CD setup (Day 11-12)

**Phase 4-5** (Not Started):
- Azure deployment readiness
- Production metrics integration
- Real API health checks (Shopify, Zendesk)
- Critic/Supervisor Agent deployment
- Execution tracing in Azure Monitor

### Documentation

- **User Guide**: [console/README.md](../console/README.md)
- **Complete Documentation**: [docs/CONSOLE-DOCUMENTATION.md](./CONSOLE-DOCUMENTATION.md)
- **Implementation Summary**: [CONSOLE-IMPLEMENTATION-SUMMARY.md](../CONSOLE-IMPLEMENTATION-SUMMARY.md)

---

## References

### Project Documentation

- **[PROJECT-README.txt](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/PROJECT-README.txt)** - Original project specification and requirements
- **[CLAUDE.md](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/CLAUDE.md)** - AI assistant guidance, technology stack, phase overview
- **[Architecture Requirements (Phase 2-5)](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/architecture-requirements-phase2-5.md)** - Comprehensive architectural enhancements specification
- **[Data Staleness Requirements](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/data-staleness-requirements.md)** - Agent-specific data store mapping
- **[Event-Driven Requirements](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/event-driven-requirements.md)** - Event catalog, NATS architecture, new user stories
- **[Critic/Supervisor Agent Requirements](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/critic-supervisor-agent-requirements.md)** - Content validation specification (NEW 2026-01-22)
- **[Execution Tracing Requirements](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/docs/execution-tracing-observability-requirements.md)** - OpenTelemetry observability (NEW 2026-01-22)
- **[User Stories (Phased)](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/user-stories-phased.md)** - 145 user stories across 5 phases (REVISED 2026-01-22)

### External References

- **[AGNTCY SDK Documentation](https://docs.agntcy.com)** - Multi-agent framework
- **[Azure Architecture Center](https://learn.microsoft.com/azure/architecture/)** - Cloud patterns and best practices
- **[Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)** - GPT-4o, embeddings
- **[Cosmos DB Vector Search](https://learn.microsoft.com/azure/cosmos-db/mongodb/vector-search)** - RAG implementation
- **[NATS JetStream](https://docs.nats.io/nats-concepts/jetstream)** - Event streaming
- **[OpenTelemetry](https://opentelemetry.io/)** - Distributed tracing and observability standard
- **[Microsoft Foundry](https://azure.microsoft.com/en-us/blog/introducing-claude-opus-4-5-in-microsoft-foundry/)** - Anthropic Claude via Azure
- **[Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)** - Infrastructure-as-Code

### GitHub Project Management

- **[Project Board](https://github.com/orgs/Remaker-Digital/projects/1)** - Kanban board, 145 issues (REVISED 2026-01-22)
- **[Epics](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues?q=label%3A%22type%3A+epic%22)** - 7 actor-based epics
- **[Phase 1 Milestone](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/milestone/1)** - ✅ Complete
- **[Phase 2 Milestone](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/milestone/2)** - ⏳ In progress
- **[Issue #144](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues/144)** - Critic/Supervisor Agent (NEW 2026-01-22)
- **[Issue #145](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues/145)** - Execution Tracing (NEW 2026-01-22)

---

**Document Maintained By:** Claude Sonnet 4.5 (AI Assistant)
**Last Updated:** 2026-01-25
**Version:** 2.4 (Phase 2 Complete 95%, Phase 3 Day 3-4 Complete)
**License:** Public (educational use)

---

## Feedback & Contributions

This is an educational project! Feedback and contributions welcome:

- **Issues:** [GitHub Issues](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/discussions)
- **Contributing:** See [CONTRIBUTING.md](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/blob/main/CONTRIBUTING.md)

**Questions about architecture decisions?** Open a discussion or issue!
