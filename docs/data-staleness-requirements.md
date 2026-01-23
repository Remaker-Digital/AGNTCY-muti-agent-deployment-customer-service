# Data Staleness Requirements by Agent

**Document Purpose:** Defines acceptable data staleness tolerances for each agent in the multi-agent customer service platform, guiding data store selection and caching strategies.

**Last Updated:** 2026-01-22
**Phase:** Architecture Design (Phase 2 preparation)

---

## Overview

Each agent has different data freshness requirements based on its function. This document specifies the maximum acceptable staleness (age) of data for each agent, which determines the appropriate data store and caching strategy.

---

## Agent Staleness Tolerances

### 1. Intent Classification Agent

**Function:** Analyzes incoming customer messages to determine intent and route to appropriate agent

**Staleness Tolerance:** **5-10 seconds**

**Data Accessed:**
- Customer profile (name, account tier, preferences)
- Recent conversation history (last 5-10 messages)
- Account status (active, suspended, VIP)
- Customer segment/tags

**Rationale:** Intent classification benefits from recent context but doesn't require real-time data. A customer's profile or recent history changing within 5-10 seconds is unlikely and wouldn't significantly impact intent detection.

**Recommended Storage:**
- **Primary:** Redis cache (5-10 sec TTL)
- **Fallback:** Cosmos DB (if cache miss)

---

### 2. Knowledge Retrieval Agent

**Function:** Searches knowledge base for relevant product information, policies, FAQs, and support articles

**Staleness Tolerance:** **1 hour**

**Data Accessed:**
- Product catalog (descriptions, specifications, features)
- Support articles and FAQs
- Company policies (return, shipping, privacy)
- Shipping rates and delivery estimates
- Promotional content

**Rationale:** Knowledge base content is relatively static. Product details, policies, and support articles rarely change within an hour. Even if updates occur, serving slightly stale content for up to 1 hour is acceptable for this use case.

**Recommended Storage:**
- **Primary:** Blob Storage + CDN (1 hour cache)
- **Secondary:** Cosmos DB analytical store (for search/query)
- **Vector Search:** Cosmos DB vector index (for RAG)

---

### 3. Response Generation Agent

**Function:** Generates customer-facing responses using current order status, inventory, and account information

**Staleness Tolerance:** **Real-time (< 1 second)**

**Data Accessed:**
- Current order status (processing, shipped, delivered)
- Real-time inventory levels
- Active promotions and pricing
- Payment status
- Shipment tracking information

**Rationale:** Customers expect accurate, up-to-date information about their orders and current product availability. Stale data could lead to incorrect responses (e.g., saying an item is in stock when it's sold out, or providing outdated tracking information).

**Recommended Storage:**
- **Primary:** Cosmos DB Core (SQL API) with strong consistency
- **Cache:** None (data must be fresh)
- **Source:** Direct API calls to Shopify/Zendesk when needed

---

### 4. Escalation Agent

**Function:** Determines when to escalate conversations to human agents and routes to available support staff

**Staleness Tolerance:** **30 seconds**

**Data Accessed:**
- Support ticket queue status
- Available human agents (online, busy, away)
- Escalation rules and thresholds
- Agent workload and skill matching
- Customer priority/VIP status

**Rationale:** Escalation decisions don't require instantaneous data. If an agent's status changed from "available" to "busy" 20 seconds ago, the system can still attempt routing and handle any conflicts. Queue status can tolerate brief staleness without impacting customer experience.

**Recommended Storage:**
- **Primary:** Redis cache (30 sec TTL)
- **Fallback:** Cosmos DB
- **Live Updates:** Event-driven notifications for critical changes

---

### 5. Analytics Agent

**Function:** Aggregates metrics, generates reports, and tracks KPIs for system performance and customer satisfaction

**Staleness Tolerance:** **5-15 minutes**

**Data Accessed:**
- Conversation metrics (volume, duration, resolution time)
- Customer satisfaction scores (CSAT, NPS)
- Automation rate and escalation rate
- Agent performance metrics
- System health metrics

**Rationale:** Analytics and reporting are inherently backward-looking. Metrics aggregated over hours, days, or weeks don't need real-time precision. A 5-15 minute delay in reflecting the latest data points is acceptable for dashboards and reports.

**Recommended Storage:**
- **Primary:** Cosmos DB analytical store (batch updates every 5-15 min)
- **Aggregation:** Pre-computed materialized views
- **Long-term:** Azure Blob Storage (archived metrics)

---

## Data Store Mapping Summary

| Agent | Staleness | Primary Store | Cache/Secondary | Update Frequency |
|-------|-----------|---------------|-----------------|------------------|
| **Intent Classification** | 5-10 sec | Cosmos DB | Redis (5-10s TTL) | On profile change |
| **Knowledge Retrieval** | 1 hour | Blob Storage + CDN | Cosmos vector index | Hourly sync |
| **Response Generation** | Real-time | Cosmos DB (strong consistency) | None | On-demand |
| **Escalation** | 30 sec | Cosmos DB | Redis (30s TTL) | Event-driven + polling |
| **Analytics** | 5-15 min | Cosmos analytical store | Materialized views | Batch (every 5-15 min) |

---

## ACID Transaction Requirements

Based on staleness tolerances, ACID transactions are required for:

1. **Response Generation Agent:**
   - Order status updates (must be consistent)
   - Inventory reservations (prevent overselling)
   - Payment status changes

2. **Escalation Agent:**
   - Ticket creation/assignment (no duplicate assignments)
   - Agent status transitions (avoid race conditions)

All other agents can tolerate eventual consistency.

---

## Phase Implementation

### Phase 1-3 (Local Development - $0 budget)
- **Mock all data stores** with JSON fixtures
- **Simulate staleness** with configurable delays in mock services
- **Test caching behavior** with in-memory cache (Python dict/Redis Docker container)

### Phase 4-5 (Azure Production - $200/month budget)
- **Cosmos DB Serverless:** Real-time + near-real-time data (~$30-50/month)
- **Redis Cache (optional):** If latency optimization needed (~$15-30/month)
- **Blob Storage + CDN:** Static knowledge base content (~$5-10/month)

---

## Monitoring & Optimization

**Key Metrics to Track:**
- Cache hit rate by agent (target: >80%)
- Data age at query time (should stay within tolerance)
- Cosmos DB request units consumed (cost optimization)
- Query latency by data store (identify bottlenecks)

**Optimization Triggers:**
- If cache hit rate < 70% → increase TTL or cache size
- If staleness exceeds tolerance → reduce TTL or update frequency
- If Cosmos RU consumption > budget → review query patterns, add indexes

---

## References

- **PROJECT-README.txt:** System architecture and KPI requirements
- **CLAUDE.md:** Technology stack and cost constraints
- **PHASE-2-READINESS.md:** Business logic implementation plan

---

**Document Status:** ✅ Approved
**Next Steps:** Design data abstraction layer and store selection strategy
