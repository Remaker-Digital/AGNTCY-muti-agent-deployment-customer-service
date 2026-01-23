# Architecture Requirements: Phase 2-5 Enhancements

**Document Purpose:** Comprehensive specification of new architectural requirements for PII tokenization, data abstraction, event-driven architecture, and differentiated AI models.

**Last Updated:** 2026-01-22
**Status:** ✅ Approved - Ready for Implementation
**Budget Impact:** Revised Phase 4-5 budget from $200/month to $265-300/month

---

## Executive Summary

This document defines four major architectural enhancements to the multi-agent customer service platform:

1. **PII Tokenization:** Protect customer data when using third-party AI services
2. **Data Abstraction:** Multi-store strategy optimized for staleness tolerance
3. **Event-Driven Architecture:** Real-time responsiveness to external triggers
4. **Differentiated AI Models:** RAG and task-specific model optimization

**Phase Implementation:** All requirements follow design (Phase 2) → mock (Phase 3) → production (Phase 4-5) pattern.

**Post Phase 5 Enhancements:** Fine-tuned models, self-hosted vector DB, medium e-commerce scale, advanced cost optimization.

---

## 1. PII Tokenization & De-identification

### 1.1 Scope

**Applies to:** Third-party AI services ONLY (public OpenAI API, public Anthropic API, etc.)

**Does NOT apply to (within secure Azure perimeter):**
- Azure OpenAI Service
- Microsoft Foundry models (including Anthropic Claude 4.5 Opus via Azure)
- Any Azure AI model service accessed through secure Azure endpoints

**Rationale:** Azure-hosted AI services do not retain customer data and are within the organization's security perimeter. See: https://azure.microsoft.com/en-us/blog/introducing-claude-opus-4-5-in-microsoft-foundry/

### 1.2 PII Fields Requiring Tokenization

**All PII must be tokenized when sent to third-party AI services:**

**Customer Information:**
- Customer name (first, last)
- Email address
- Phone number
- Physical address (street, city, state, zip)
- Customer ID / account number

**Order/Transaction Data:**
- Order ID / order number
- Tracking numbers
- Payment information (credit card, billing address)
- Purchase amounts / pricing

**Support/Communication Data:**
- Support ticket ID
- Conversation content/messages
- Agent notes
- Attachments/files

**Other:**
- IP addresses
- Device identifiers
- Custom fields

### 1.3 Tokenization Approach

**Method:** Random UUID tokens (Option B)

**Format:**
```
Original: john.doe@example.com
Tokenized: TOKEN_a7f3c9e1-4b2d-8f6a-9c3e-1d5b7a2f8e4c
```

**Rationale:** Maximum security, non-reversible without mapping, no field type leakage

### 1.4 Token Mapping Storage

**Phase 4-5 (Production):**
- **Primary:** Azure Key Vault
- **Cost:** ~$1-5/month (~$0.03 per 10K operations)
- **Latency:** 50-100ms per lookup
- **Security:** Highest level, managed encryption, audit logs

**Fallback (if latency unacceptable):**
- **Secondary:** Cosmos DB encrypted field
- **Cost:** ~$5-10/month incremental
- **Latency:** 10-20ms per lookup
- **Migration:** Triggered if P95 latency >100ms impacts user experience

### 1.5 Tokenization Flow

```
┌─────────────────┐
│  User Message   │
│  (with PII)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  PII Tokenization Service   │
│  - Detect PII fields        │
│  - Generate UUID tokens     │
│  - Store mapping in Key     │
│    Vault                    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Tokenized Message          │
│  (sent to third-party AI)   │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  AI Response                │
│  (with tokens)              │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  De-tokenization Service    │
│  - Lookup tokens in Key     │
│    Vault                    │
│  - Replace with original    │
│    PII                      │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  User Response              │
│  (with real PII)            │
└─────────────────────────────┘
```

### 1.6 Implementation Timeline

- **Phase 2:** Design tokenization service, implement mock with in-memory token storage
- **Phase 3:** Test tokenization with mock third-party AI calls
- **Phase 4:** Integrate Azure Key Vault, deploy to production
- **Phase 5:** Validate latency and security in production load tests

### 1.7 Code Location

```
shared/
├── tokenization/
│   ├── tokenizer.py           # PII detection and token generation
│   ├── detokenizer.py         # Token-to-PII mapping retrieval
│   ├── key_vault_client.py    # Azure Key Vault integration
│   └── mock_token_store.py    # Phase 1-3 in-memory mock
```

---

## 2. Data Abstraction & Multi-Store Strategy

### 2.1 Staleness Tolerance by Agent

| Agent | Staleness | Primary Store | Cache/Secondary | Update Frequency |
|-------|-----------|---------------|-----------------|------------------|
| **Intent Classification** | 5-10 sec | Cosmos DB | Redis (5-10s TTL) | On profile change |
| **Knowledge Retrieval** | 1 hour | Blob Storage + CDN | Cosmos vector index | Hourly sync |
| **Response Generation** | Real-time | Cosmos DB (strong consistency) | None | On-demand |
| **Escalation** | 30 sec | Cosmos DB | Redis (30s TTL) | Event-driven + polling |
| **Analytics** | 5-15 min | Cosmos analytical store | Materialized views | Batch (every 5-15 min) |

### 2.2 Data Store Mapping

**Real-time (ACID) - Cosmos DB Core (SQL API):**
- Response Generation Agent data
- Order status, inventory, payment status
- Current conversation state
- **Consistency:** Strong
- **Cost:** ~$30-50/month (serverless mode)

**Near-real-time Cache - Redis (optional):**
- Intent Classification Agent (customer profiles, session data)
- Escalation Agent (queue status, agent availability)
- **TTL:** 5-30 seconds
- **Cost:** ~$15-30/month if implemented (Phase 5 optimization)
- **Status:** Deferred to Post Phase 5 cost optimization

**Eventually Consistent - Cosmos DB Analytical Store:**
- Analytics Agent (aggregated metrics, reports)
- Historical data
- **Sync frequency:** 5-15 minutes
- **Cost:** Included in Cosmos serverless

**Static/Slow-Changing - Blob Storage + CDN:**
- Knowledge Retrieval Agent (knowledge base articles, product catalogs, policies)
- **Cache TTL:** 1 hour
- **Cost:** ~$5-10/month

### 2.3 ACID Transaction Requirements

**ACID transactions required for:**
1. Response Generation Agent:
   - Order status updates (prevent inconsistent states)
   - Inventory reservations (prevent overselling)
   - Payment status changes (financial accuracy)

2. Escalation Agent:
   - Ticket creation/assignment (no duplicate assignments)
   - Agent status transitions (avoid race conditions)

**All other agents:** Eventual consistency acceptable

### 2.4 Data Engineering Integration Guidance

This system is designed to integrate with enterprise data platforms:

**Delta Lake / Databricks:**
- Analytics Agent writes metrics to Cosmos analytical store
- Nightly export to Delta Lake via Azure Data Factory
- Schema: Parquet format, partitioned by date

**Delta Sharing:**
- Share anonymized conversation metrics with partner teams
- Use PII tokenization before sharing
- Share schema: `conversations`, `customer_satisfaction`, `agent_performance`

**Azure Data Lake (ADLS Gen2):**
- Long-term archival (>90 days) of conversation logs
- Blob Storage lifecycle policy: Cold tier after 30 days, Archive after 90 days
- Format: JSON Lines compressed with gzip

**Data Catalog:**
- All data stores registered in Azure Purview (if available)
- Lineage tracking: Shopify → Cosmos → Analytics → Data Lake
- Sensitivity labels: PII fields marked as "Highly Confidential"

### 2.5 Implementation Timeline

- **Phase 2:** Design data abstraction layer, implement mocks with JSON fixtures
- **Phase 3:** Test multi-store access patterns with Docker containers
- **Phase 4:** Deploy Cosmos DB, Blob Storage, optional Redis to Azure
- **Phase 5:** Validate staleness tolerances and performance SLAs

### 2.6 Code Location

```
shared/
├── data_abstraction/
│   ├── abstract_store.py      # Base interface for all data stores
│   ├── cosmos_store.py        # Cosmos DB implementation
│   ├── blob_store.py          # Azure Blob Storage implementation
│   ├── redis_store.py         # Redis cache implementation
│   ├── mock_store.py          # Phase 1-3 in-memory mock
│   └── store_factory.py       # Factory for store selection by staleness
```

**Full documentation:** `docs/data-staleness-requirements.md`

---

## 3. Event-Driven Architecture

### 3.1 Event Sources (Phase 5 Scope)

**Customer/Order Events (Shopify Webhooks):**
- ✅ Customer account status changes (created, updated, deleted)
- ✅ Order status changes (created, paid, fulfilled, cancelled)
- ✅ Inventory level changes (low stock, out of stock, restocked)
- ✅ Customer tag changes (VIP status, segment changes)

**Support Events (Zendesk Webhooks):**
- ✅ Ticket created, updated, closed
- ✅ Ticket priority changes
- ✅ Agent assignment changes
- ✅ Customer satisfaction rating submitted

**Time-Based Events (Scheduled Triggers):**
- ✅ Time-limited promotions (start, end)
- ✅ Daily/weekly report generation
- ✅ Batch data sync operations
- ✅ Company news/announcements

**Total:** 12 event types for Phase 5

### 3.2 Post Phase 5 Enhancements

**Social Media Events:**
- ⏳ Twitter mentions of brand
- ⏳ Facebook comments/messages
- ⏳ Instagram mentions

**RSS/Feed Events:**
- ⏳ Industry news feeds
- ⏳ Competitor pricing changes

### 3.3 Event Routing Architecture

**Selected Approach:** NATS JetStream (Option B)

**Rationale:**
- Zero incremental cost (reuses AGNTCY transport layer)
- High performance (1M+ msgs/sec)
- Persistent streams with replay capability
- Built-in dead-letter queues

**Event Flow:**
```
┌─────────────────┐
│  Event Sources  │
│  (Webhooks,     │
│   Cron, RSS)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Event Ingestion│
│  Service        │ ← Azure Function or Container
│  (HTTP endpoint)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  NATS JetStream │
│  Event Bus      │ ← Durable storage, replay
└────────┬────────┘
         │
         ├──────────────────┬──────────────────┬──────────────────┐
         ▼                  ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Intent Agent │   │Knowledge Ag. │   │Escalation Ag.│   │Analytics Ag. │
│ (Subscriber) │   │ (Subscriber) │   │ (Subscriber) │   │ (Subscriber) │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### 3.4 Event Topics (NATS Subject Hierarchy)

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

### 3.5 Throttling & Reliability

**Throttling Limits:**
- **Global:** 100 events/sec
- **Per agent:** 20 events/sec
- **Concurrent handlers:** 5 per agent
- **Queue depth:** 1000 events per topic

**Overflow Behavior:**
- Drop oldest events when queue full
- Log warning with dropped event count
- Operator alert if >50 events dropped in 5 minutes

**Retry Policy:**
- Exponential backoff: 1s, 2s, 4s, 8s, 16s
- Max retries: 5 attempts
- Dead-letter queue for failed events
- Operator notification at >10 DLQ events

**Event Retention:**
- 7 days in NATS JetStream
- Replay capability for debugging
- Auto-purge after 7 days

### 3.6 New User Stories Required

**5 new GitHub issues needed:**

1. **Story 7.20:** Operator Schedules Time-Limited Promotion (Phase 4)
2. **Story 7.21:** Operator Configures Batch Data Sync Schedule (Phase 4)
3. **Story 7.22:** Operator Publishes Company Announcement (Phase 4)
4. **Story 1.41:** Customer Receives Proactive Shipment Notification (Phase 5)
5. **Story 2.23:** Prospect Receives Back-in-Stock Notification (Phase 5)

**See `docs/event-driven-requirements.md` for full story details.**

### 3.7 Implementation Timeline

- **Phase 2:** Design event ingestion service, define event schemas
- **Phase 3:** Mock RabbitMQ for local event testing
- **Phase 4:** Deploy NATS JetStream, configure Shopify/Zendesk webhooks, implement Azure Functions
- **Phase 5:** Load test event throughput (1000 events/min), validate reliability

### 3.8 Code Location

```
events/
├── ingestion/
│   ├── webhook_handler.py     # HTTP endpoint for Shopify/Zendesk webhooks
│   ├── scheduler.py           # Cron/timer trigger for scheduled events
│   └── rss_poller.py          # RSS feed polling service
├── handlers/
│   ├── shopify_handlers.py    # Event handlers for Shopify events
│   ├── zendesk_handlers.py    # Event handlers for Zendesk events
│   └── scheduled_handlers.py  # Event handlers for time-based events
└── nats_client.py             # NATS JetStream pub/sub client
```

**Full documentation:** `docs/event-driven-requirements.md`

---

## 4. Retrieval-Augmented Generation (RAG) & Differentiated Models

### 4.1 Model Differentiation Strategy (Phase 5)

**Scenario A: Different Model Sizes by Agent Complexity**

| Agent | Model | Cost per 1M Tokens | Use Case |
|-------|-------|-------------------|----------|
| **Intent Classification** | GPT-4o-mini | ~$0.15 | Fast classification, simple task |
| **Response Generation** | GPT-4o | ~$2.50 | High-quality customer responses |
| **Knowledge Retrieval** | text-embedding-3-large | ~$0.13 | Vector embeddings for RAG |

**Estimated monthly token usage:**
- Intent: 5M tokens/month = $0.75
- Response: 10M tokens/month = $25.00
- Embeddings: 2M tokens/month = $0.26
- **Total:** ~$26/month

**Phase 5 Scope:** Scenario A only

### 4.2 Post Phase 5 Enhancement

**Scenario B: Fine-Tuned Models for Specialized Tasks**
- Custom intent classifier (fine-tuned on e-commerce queries)
- Custom response generator (fine-tuned on brand voice/tone)
- **One-time cost:** $100-500 for training
- **Monthly cost:** $30-70 for inference
- **Status:** Deferred to Post Phase 5

### 4.3 RAG Vector Store

**Selected Approach:** Cosmos DB for MongoDB (Vector Search - Preview)

**Configuration:**
- **API:** MongoDB API with vector search capability
- **Embedding model:** text-embedding-3-large (1536 dimensions)
- **Index type:** IVF (Inverted File Index)
- **Distance metric:** Cosine similarity
- **Cost:** ~$5-10/month incremental (serverless mode)

**Backup Plan (Post Phase 5):**
- Self-hosted Qdrant in Container Instance (~$20-30/month)
- Triggered if Cosmos preview has limitations or performance issues

### 4.4 Knowledge Base Size (Phase 5 Scope)

**Small E-commerce Scale:**
- **Products:** 50 products
- **Support Articles:** 20 articles
- **Company Policies:** 5 documents (shipping, returns, privacy, terms, FAQ)
- **Total:** 75 documents, ~15K words, ~20K tokens
- **Embeddings:** 75 x 1536 dimensions = ~115K vector dimensions

**Post Phase 5 Enhancement:**
- Medium e-commerce scale: 500 products, 100 articles, 10 policies
- ~150K words, ~200K tokens

### 4.5 RAG Query Flow

```
┌─────────────────┐
│  User Question  │
│  "Is mango soap │
│   in stock?"    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Knowledge Retrieval Agent  │
│  1. Generate query embedding│
│  2. Vector search in Cosmos │
│  3. Retrieve top 3 results  │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Retrieved Context          │
│  - Product: Organic Mango   │
│    Soap, $12, In Stock (25) │
│  - Ingredients: ...         │
│  - Customer Reviews: ...    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Response Generation Agent  │
│  - Prompt: Question +       │
│    Retrieved Context        │
│  - Model: GPT-4o            │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  User Response              │
│  "Yes, the organic mango    │
│   soap is in stock! We have │
│   25 units available for    │
│   $12 each. It's made with  │
│   ..."                      │
└─────────────────────────────┘
```

### 4.6 Implementation Timeline

- **Phase 2:** Design RAG pipeline, implement mock embeddings with local FAISS
- **Phase 3:** Test vector search with mock knowledge base
- **Phase 4:** Deploy Cosmos DB vector search, integrate Azure OpenAI embeddings
- **Phase 5:** Load test RAG performance (query latency <500ms), validate accuracy

### 4.7 Code Location

```
agents/knowledge_retrieval/
├── embedder.py                # Azure OpenAI embedding generation
├── vector_store.py            # Cosmos DB vector search client
├── rag_pipeline.py            # End-to-end RAG query flow
└── mock_embeddings.py         # Phase 1-3 FAISS-based mock

test-data/
├── knowledge_base/
│   ├── products.json          # 50 product documents
│   ├── support_articles.json # 20 support articles
│   └── policies.json          # 5 policy documents
```

---

## 5. Budget Summary

### 5.1 Revised Budget (Phase 4-5)

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| **Compute** | | |
| Container Instances (5 agents) | $50-80 | 1-3 instances per agent, auto-scale |
| Azure Functions (event ingestion) | $5-10 | Serverless, pay-per-execution |
| **Data** | | |
| Cosmos DB Serverless (real-time + vector) | $30-50 | Includes vector search |
| Blob Storage + CDN (knowledge base) | $5-10 | Static content, 1hr cache |
| Azure Key Vault (PII tokens) | $1-5 | Secrets + token mapping |
| **Events** | | |
| NATS JetStream (Container Instance) | $10-20 | Shared with AGNTCY transport |
| Event storage (7-day retention) | $2-5 | JetStream disk storage |
| **AI/ML** | | |
| Azure OpenAI (embeddings + inference) | $20-50 | Scenario A models only |
| **Networking** | | |
| Application Gateway / Load Balancer | $20-40 | Traffic routing |
| **Monitoring** | | |
| Azure Monitor + Log Analytics | $10-20 | 7-day retention |
| **TOTAL** | **$153-280/month** | |

**Revised Budget:** $265-300/month (up from $200)

**Rationale for increase:**
- New architectural requirements (PII, events, RAG) add functionality
- Cost optimization deferred to Post Phase 5
- Prioritizes feature completeness over cost minimization for Phase 5

### 5.2 Post Phase 5 Cost Optimization Opportunities

**Potential savings: $40-80/month**

1. **Migrate to Redis cache** for Intent/Escalation agents (latency optimization): -$0 (cost neutral, improves performance)
2. **Reduce Container Instance sizes** after profiling actual resource usage: -$10-20/month
3. **Implement aggressive Azure OpenAI caching** to reduce token usage: -$10-20/month
4. **Optimize Cosmos DB throughput** based on actual query patterns: -$10-20/month
5. **Move to self-hosted Qdrant** if Cosmos vector search costs increase: -$10-20/month

**Target Post-Phase-5 Budget:** $180-220/month

---

## 6. Success Criteria

### 6.1 Phase 2 Success Criteria

- [ ] PII tokenization service designed and mocked (in-memory token store)
- [ ] Data abstraction layer interfaces defined for all stores
- [ ] Event ingestion service designed with mock RabbitMQ
- [ ] RAG pipeline designed with mock FAISS embeddings
- [ ] All agents updated to use abstraction layers (mocks)
- [ ] Unit tests pass with >80% coverage

### 6.2 Phase 3 Success Criteria

- [ ] PII tokenization tested end-to-end with mock AI calls
- [ ] Multi-store access patterns validated with Docker containers
- [ ] Event-driven flows tested with mock webhooks and cron
- [ ] RAG accuracy validated with test knowledge base (75 documents)
- [ ] Integration tests pass with mock services
- [ ] Test coverage >70%

### 6.3 Phase 4 Success Criteria

- [ ] Azure Key Vault integrated for PII token storage
- [ ] Cosmos DB, Blob Storage deployed with real data
- [ ] NATS JetStream deployed, Shopify/Zendesk webhooks configured
- [ ] Azure OpenAI embeddings + Cosmos vector search operational
- [ ] All 5 agents deployed to Azure Container Instances
- [ ] Terraform infrastructure-as-code complete
- [ ] Azure DevOps pipeline operational

### 6.4 Phase 5 Success Criteria

- [ ] PII tokenization latency <100ms (P95), no data leaks
- [ ] Data staleness meets tolerances (Intent: <10s, Knowledge: <1hr, Response: real-time)
- [ ] Event processing: 100 events/sec sustained, <1% error rate
- [ ] RAG query latency <500ms, retrieval accuracy >90%
- [ ] Monthly costs within $265-300 budget
- [ ] Load test: 100 concurrent users, 1000 req/min, <2s response time
- [ ] Security scan (OWASP ZAP): no critical vulnerabilities
- [ ] Disaster recovery: RTO <4hrs, RPO <1hr

---

## 7. Risk Assessment

### 7.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Cosmos DB vector search (preview) has limitations | High | Medium | Backup plan: Self-hosted Qdrant (Post Phase 5) |
| Azure Key Vault latency >100ms impacts UX | Medium | Medium | Fallback: Cosmos DB token storage |
| NATS JetStream event loss during failures | High | Low | Persistent streams, replay capability, DLQ |
| Azure OpenAI token costs exceed estimate | Medium | Medium | Aggressive caching, usage alerts at $40/month |

### 7.2 Budget Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Actual costs exceed $300/month | High | Cost alerts at $250 (83%), $280 (93%), daily monitoring |
| Cosmos DB serverless spikes unexpectedly | Medium | Request unit caps, query optimization, caching |
| Container Instances don't scale down | Medium | Auto-scale policies tested in Phase 3, manual review weekly |

### 7.3 Schedule Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Phase 2 scope creep with new requirements | Medium | TodoWrite task management, focus on design over implementation |
| Phase 4 Azure service delays (approvals, quotas) | Low | Pre-validate Azure subscription quotas, request increases early |
| Phase 5 load testing uncovers performance issues | Medium | Phase 3 local load testing, early performance profiling |

---

## 8. References

**Related Documentation:**
- `docs/data-staleness-requirements.md` - Data store selection by agent
- `docs/event-driven-requirements.md` - Event sources, routing, handlers, new user stories
- `CLAUDE.md` - Project overview, technology stack, cost constraints
- `PROJECT-README.txt` - Original project specification and KPIs
- `PHASE-2-READINESS.md` - Phase 2 implementation plan
- `user-stories-phased.md` - User story catalog (130 stories + 5 new event stories)

**Technology References:**
- AGNTCY SDK Documentation: https://docs.agntcy.com
- Azure Cosmos DB Vector Search: https://learn.microsoft.com/azure/cosmos-db/mongodb/vector-search
- NATS JetStream: https://docs.nats.io/nats-concepts/jetstream
- Azure OpenAI Service: https://learn.microsoft.com/azure/ai-services/openai/

---

## 9. Next Steps

### Immediate Actions (Phase 2 Preparation)

1. **Create 5 new GitHub issues** for event-driven user stories (7.20-7.22, 1.41, 2.23)
2. **Update CLAUDE.md** with revised budget ($265-300) and new architectural requirements
3. **Design PII tokenization service** (interface, mock implementation)
4. **Design data abstraction layer** (interfaces for Cosmos, Blob, Redis, mock)
5. **Design event ingestion service** (webhook handler, schema definitions)
6. **Design RAG pipeline** (embedder, vector store, query flow)
7. **Update Phase 2 user stories** (add tasks for new architectural components)

### Phase 2 Implementation Focus

- Implement mock versions of all 4 architectural enhancements
- Update all 5 agents to use new abstraction layers
- Write comprehensive unit tests (>80% coverage target)
- Document integration points for data engineers (Delta Lake, ADLS)

### Phase 3 Validation Focus

- End-to-end testing with Docker containers
- Performance profiling and bottleneck identification
- Security testing (PII tokenization validation)
- Load testing with Locust (local hardware limits)

### Phase 4 Deployment Focus

- Terraform infrastructure-as-code for all Azure services
- Azure Key Vault secrets management
- NATS JetStream deployment and webhook configuration
- Azure OpenAI integration and Cosmos vector search setup

### Phase 5 Go-Live Focus

- Production load testing (100 concurrent users, 1000 req/min)
- Security scanning (OWASP ZAP, Dependabot, Snyk)
- Disaster recovery drill (full end-to-end validation)
- Cost monitoring and budget compliance validation

---

**Document Status:** ✅ Complete and Approved
**Approver:** User (2026-01-22)
**Next Review:** After Phase 2 implementation (estimated 2026-04-30)

---

*This document consolidates requirements from sequential Q&A session on 2026-01-22. All decisions documented and approved by project owner.*
