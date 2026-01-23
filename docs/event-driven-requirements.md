# Event-Driven Architecture Requirements

**Document Purpose:** Defines event sources, routing, and handling requirements for the multi-agent customer service platform.

**Last Updated:** 2026-01-22
**Phase:** Architecture Design (Phase 2 preparation)

---

## Overview

The multi-agent system requires event-driven capabilities to respond to external triggers, system changes, and scheduled actions. This document categorizes events by phase and implementation priority.

---

## Event Sources by Phase

### Phase 5 Events (Production Deployment)

These events are **REQUIRED** to satisfy Phase 5 user stories and production operational requirements:

#### Customer/Order Events (Shopify Webhooks)
- ✅ **Customer account status changes** (created, updated, deleted)
  - **Related Stories:** Phase 4/5 - Customer profile management, VIP status changes
  - **Trigger:** Shopify webhook `customers/create`, `customers/update`, `customers/delete`
  - **Handler:** Intent Classification Agent (update customer context cache)
  - **Use Case:** Update customer profile cache when VIP status changes, invalidate session cache on account deletion

- ✅ **Order status changes** (created, paid, fulfilled, cancelled)
  - **Related Stories:** Phase 4/5 - Real-time order tracking (Story 1.40)
  - **Trigger:** Shopify webhooks `orders/create`, `orders/paid`, `orders/fulfilled`, `orders/cancelled`
  - **Handler:** Response Generation Agent (invalidate order cache), Analytics Agent (update metrics)
  - **Use Case:** Proactively notify customer of shipment, update analytics dashboards

- ✅ **Inventory level changes** (low stock, out of stock, restocked)
  - **Related Stories:** Phase 2/4 - Product availability inquiries (Stories 1.24, 2.7)
  - **Trigger:** Shopify webhook `inventory_levels/update`
  - **Handler:** Knowledge Retrieval Agent (update product availability cache), Mailchimp (notify waitlist subscribers)
  - **Use Case:** Trigger "back in stock" email campaigns, update product availability in real-time

- ✅ **Customer tag changes** (VIP status, segment changes)
  - **Related Stories:** Phase 4 - VIP customer handling, personalized responses
  - **Trigger:** Shopify webhook `customers/update` (tags field changed)
  - **Handler:** Intent Classification Agent (update customer segmentation)
  - **Use Case:** Adjust response tone/priority for newly tagged VIP customers

#### Support Events (Zendesk Webhooks)
- ✅ **Ticket created, updated, closed**
  - **Related Stories:** Phase 3/4/5 - Support escalation flow (Stories 3.3, 3.11, 3.13)
  - **Trigger:** Zendesk webhooks `ticket.created`, `ticket.updated`, `ticket.closed`
  - **Handler:** Escalation Agent (track escalation lifecycle), Analytics Agent (calculate resolution time)
  - **Use Case:** Update customer when support closes ticket, track SLA compliance

- ✅ **Ticket priority changes**
  - **Related Stories:** Phase 5 - Critical issue escalation (Story 3.15)
  - **Trigger:** Zendesk webhook `ticket.updated` (priority field changed)
  - **Handler:** Escalation Agent (send urgent notifications)
  - **Use Case:** Alert on-call support when ticket escalated to "urgent"

- ✅ **Agent assignment changes**
  - **Related Stories:** Phase 3/4 - Support workflow (Stories 3.3, 3.11)
  - **Trigger:** Zendesk webhook `ticket.updated` (assignee field changed)
  - **Handler:** Escalation Agent (update agent availability cache)
  - **Use Case:** Track agent workload for intelligent routing

- ✅ **Customer satisfaction rating submitted**
  - **Related Stories:** Phase 3/5 - Analytics and KPI tracking (Stories 7.7, 5.14)
  - **Trigger:** Zendesk webhook `satisfaction_rating.created`
  - **Handler:** Analytics Agent (update CSAT metrics)
  - **Use Case:** Track customer satisfaction KPI, trigger follow-up for low ratings

#### Time-Based Events (Scheduled Triggers)
- ✅ **Time-limited promotions** (start, end)
  - **Related Stories:** Phase 2/4 - Promo code handling (Story 1.17)
  - **Trigger:** Cron/scheduled job (Azure Functions Timer Trigger or NATS scheduled message)
  - **Handler:** Knowledge Retrieval Agent (update active promotions), Mailchimp (send campaign)
  - **Use Case:** Automatically activate/deactivate promo codes, trigger promotional email campaigns
  - **NEW STORY NEEDED:** "Operator schedules time-limited promotion with auto-activation"

- ✅ **Daily/weekly report generation**
  - **Related Stories:** Phase 3/5 - Performance reporting (Stories 7.7, 7.18)
  - **Trigger:** Cron/scheduled job (daily 8am ET, weekly Monday 9am ET)
  - **Handler:** Analytics Agent (generate reports), Operator (receive email/dashboard)
  - **Use Case:** Automated KPI reports, cost monitoring alerts

- ✅ **Batch data sync operations**
  - **Related Stories:** Phase 4 - Real API integration (Shopify, Zendesk, Mailchimp)
  - **Trigger:** Cron/scheduled job (hourly or configurable interval)
  - **Handler:** Knowledge Retrieval Agent (sync product catalog), Analytics Agent (sync metrics)
  - **Use Case:** Hourly sync of product catalog to knowledge base, nightly sync of analytics data to data warehouse
  - **NEW STORY NEEDED:** "Operator configures batch sync schedule for product catalog"

- ✅ **Company news/announcements**
  - **Related Stories:** Phase 2/4 - Knowledge base updates (Story 3.7)
  - **Trigger:** RSS feed polling or manual trigger
  - **Handler:** Knowledge Retrieval Agent (update knowledge base), Mailchimp (send newsletter)
  - **Use Case:** Auto-update knowledge base when company blog posts new policy, trigger customer newsletter
  - **NEW STORY NEEDED:** "Operator publishes company announcement, AI knowledge base auto-updates"

---

### Post Phase 5 Enhancements (Future Scope)

These events are **NOT REQUIRED** for Phase 5 completion but are valuable for future iterations:

#### Social Media Events (Optional - Post Phase 5)
- ⏳ **Twitter mentions of brand**
  - **Use Case:** Monitor brand sentiment, respond to customer service requests via Twitter
  - **Requires:** Twitter API account, social listening integration
  - **Budget Impact:** Twitter API fees (varies)

- ⏳ **Facebook comments/messages**
  - **Use Case:** Respond to customer inquiries on Facebook page
  - **Requires:** Facebook Business account, Graph API integration
  - **Budget Impact:** Minimal (free API)

- ⏳ **Instagram mentions**
  - **Use Case:** Track product mentions, influencer engagement
  - **Requires:** Instagram Business account, Graph API integration
  - **Budget Impact:** Minimal (free API)

#### RSS/Feed Events (Optional - Post Phase 5)
- ⏳ **Product blog updates**
  - **Use Case:** Auto-populate knowledge base with new product announcements
  - **Covered by:** "Company news/announcements" event (RSS polling)

- ⏳ **Industry news feeds**
  - **Use Case:** Proactive customer outreach based on industry trends
  - **Budget Impact:** Minimal (free RSS feeds)

- ⏳ **Competitor pricing changes**
  - **Use Case:** Dynamic pricing adjustments, sales alerts
  - **Requires:** Web scraping or third-party pricing API
  - **Budget Impact:** $50-200/month for pricing intelligence services

---

## New User Stories Required for Phase 5

Based on event requirements, the following user stories should be added to Phase 4/5:

### Story 7.20: Operator Schedules Time-Limited Promotion (Phase 4)
**Epic:** Operator (Epic #8)
**Theme:** Event-driven promotion management
**Example Scenarios:**
- Operator schedules "Summer Sale" promo code for June 1-15
- System creates scheduled events: promotion start (June 1 00:00 ET), promotion end (June 15 23:59 ET)
- On June 1, Knowledge Retrieval Agent activates promo code, Mailchimp campaign sent
- On June 15, promo code automatically deactivated, Knowledge Retrieval Agent updated

**Technical Scope:**
- Time-based event scheduler (Azure Functions Timer Trigger or NATS scheduled messages)
- Event handler for promotion activation/deactivation
- Integration with Knowledge Retrieval Agent and Mailchimp

**Acceptance Criteria:**
- Operator can schedule promotion via configuration file or admin UI
- Promotion activates/deactivates automatically at scheduled time
- Customers receive promotional email campaign on activation
- Knowledge base reflects current active promotions

**Labels:** `phase: phase-4`, `component: agent`, `component: api`, `actor: operator`, `priority: high`

---

### Story 7.21: Operator Configures Batch Data Sync Schedule (Phase 4)
**Epic:** Operator (Epic #8)
**Theme:** Scheduled data synchronization
**Example Scenarios:**
- Operator configures: product catalog sync every 1 hour, analytics sync nightly at 2am ET
- System creates scheduled jobs for each sync operation
- Product catalog changes in Shopify automatically reflected in knowledge base within 1 hour
- Analytics data synced to data warehouse for long-term reporting

**Technical Scope:**
- Configurable cron schedule for data sync jobs
- Event handlers for product catalog sync, analytics sync
- Integration with Shopify API, Cosmos DB, Blob Storage

**Acceptance Criteria:**
- Operator can configure sync frequency via environment variables or config file
- Sync jobs execute on schedule with logging and error handling
- Failed sync retries with exponential backoff
- Operator receives notification on sync failure

**Labels:** `phase: phase-4`, `component: infrastructure`, `component: api`, `actor: operator`, `priority: high`

---

### Story 7.22: Operator Publishes Company Announcement (Phase 4)
**Epic:** Operator (Epic #8)
**Theme:** Event-driven knowledge base updates
**Example Scenarios:**
- Operator publishes new shipping policy on company blog (RSS feed)
- System detects RSS update within 15 minutes
- Knowledge Retrieval Agent automatically updates knowledge base with new policy
- Analytics dashboard shows "knowledge base updated: shipping policy v2.0"

**Technical Scope:**
- RSS feed polling (every 15 minutes)
- Event handler for RSS updates
- Knowledge base update automation
- Integration with Knowledge Retrieval Agent

**Acceptance Criteria:**
- System polls configured RSS feeds on schedule
- New RSS items trigger knowledge base update workflow
- Knowledge Retrieval Agent indexes new content within 30 minutes
- Operator receives notification of knowledge base updates

**Labels:** `phase: phase-4`, `component: agent`, `component: api`, `actor: operator`, `priority: medium`

---

### Story 1.41: Customer Receives Proactive Shipment Notification (Phase 5)
**Epic:** Customer (Epic #2)
**Theme:** Event-driven customer engagement
**Example Scenarios:**
- Customer's order status changes to "fulfilled" in Shopify
- Shopify webhook triggers event handler
- System sends Mailchimp email: "Your order has shipped! Tracking: [link]"
- Customer receives notification within 5 minutes of shipment

**Technical Scope:**
- Shopify webhook handler for `orders/fulfilled` event
- Event routing to Mailchimp integration
- Email template with order details and tracking link

**Acceptance Criteria:**
- Webhook received and processed within 5 seconds
- Customer receives shipment notification email within 5 minutes
- Email includes: order number, tracking link, estimated delivery date
- No duplicate notifications sent for same order

**Labels:** `phase: phase-5`, `component: api`, `component: agent`, `actor: customer`, `priority: high`

---

### Story 2.23: Prospect Receives Back-in-Stock Notification (Phase 5)
**Epic:** Prospect (Epic #3)
**Theme:** Event-driven marketing automation
**Example Scenarios:**
- Prospect signed up for "eucalyptus soap" restock notifications in Phase 2
- Shopify inventory webhook: eucalyptus soap restocked (0 → 25 units)
- System triggers Mailchimp campaign to all waitlist subscribers
- Prospect receives email: "Eucalyptus soap is back in stock!"

**Technical Scope:**
- Shopify webhook handler for `inventory_levels/update` event
- Mailchimp segment/tag-based campaign triggering
- Waitlist subscriber management

**Acceptance Criteria:**
- Inventory increase triggers campaign within 15 minutes
- Only subscribers who requested that specific product receive notification
- Email includes direct product link and current stock level
- Campaign sent only once per restock event (no duplicates)

**Labels:** `phase: phase-5`, `component: api`, `component: agent`, `actor: prospect`, `priority: high`

---

## Event Routing Architecture

### Proposed Approach: NATS JetStream

**Rationale:**
- Already planned for AGNTCY transport layer (no incremental cost)
- Native support for pub/sub, queues, and persistent streams
- Built-in message replay and dead-letter queues
- High performance (1M+ msgs/sec throughput)

**Alternative Considered: Azure Event Grid + Azure Functions**
- **Pros:** Native Azure service, serverless, dead-letter queues
- **Cons:** ~$5-15/month additional cost, another service to manage
- **Decision:** Use NATS to consolidate infrastructure and minimize costs

### Event Flow Architecture

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
│  Service        │ ← Receives webhooks, polls RSS, executes cron
│  (Azure Function│
│   or Container) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  NATS JetStream │
│  Event Bus      │ ← Durable event storage, replay capability
└────────┬────────┘
         │
         ├──────────────────┬──────────────────┬──────────────────┐
         ▼                  ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Intent Agent │   │Knowledge Agent│   │Escalation Ag.│   │Analytics Ag. │
│ (Subscriber) │   │ (Subscriber)  │   │ (Subscriber) │   │ (Subscriber) │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### Event Topics (NATS Subject Hierarchy)

```
events.shopify.customers.created
events.shopify.customers.updated
events.shopify.customers.deleted
events.shopify.orders.created
events.shopify.orders.paid
events.shopify.orders.fulfilled
events.shopify.orders.cancelled
events.shopify.inventory.updated

events.zendesk.tickets.created
events.zendesk.tickets.updated
events.zendesk.tickets.closed
events.zendesk.tickets.priority_changed
events.zendesk.tickets.assigned
events.zendesk.satisfaction_ratings.created

events.scheduled.promotions.start
events.scheduled.promotions.end
events.scheduled.reports.daily
events.scheduled.reports.weekly
events.scheduled.sync.products
events.scheduled.sync.analytics

events.rss.company_news.updated
```

### Event Message Format

All events will use a standardized format:

```json
{
  "eventId": "evt_a7f3c9e1-4b2d-8f6a-9c3e-1d5b7a2f8e4c",
  "eventType": "shopify.orders.fulfilled",
  "timestamp": "2026-01-22T14:35:00Z",
  "source": "shopify",
  "payload": {
    "orderId": "10234",
    "customerId": "cust_5678",
    "status": "fulfilled",
    "trackingNumber": "9400123456789",
    "carrier": "USPS"
  },
  "metadata": {
    "retryCount": 0,
    "processingDeadline": "2026-01-22T14:40:00Z"
  }
}
```

---

## Throttling and Reliability

### Throttling Rules
- **Max events per second (global):** 100 events/sec
- **Max events per agent per second:** 20 events/sec
- **Max concurrent event handlers per agent:** 5 handlers

### Backpressure Strategy
- **Queue depth:** 1000 events per topic
- **Overflow behavior:** Drop oldest events, log warning
- **Rate limit exceeded:** Reject with HTTP 429, log event for manual retry

### Retry Policy
- **Transient failures:** Exponential backoff (1s, 2s, 4s, 8s, 16s)
- **Max retries:** 5 attempts
- **Dead-letter queue:** Events that fail after 5 retries moved to DLQ for manual investigation
- **Operator notification:** Email/Slack alert on DLQ threshold (>10 events)

### Event Persistence
- **Retention:** 7 days (cost optimization)
- **Replay capability:** Operators can replay events from past 7 days for debugging
- **Purge policy:** Auto-purge events older than 7 days

---

## Logging and Observability

### Event Metrics to Track
- **Event volume:** Events/sec by source and type
- **Processing latency:** Time from event ingestion to handler completion
- **Error rate:** Failed events / total events (target: <1%)
- **Queue depth:** Current pending events per topic
- **Handler performance:** Execution time per event handler

### Alerts
- **Critical:** DLQ depth >10 events, event processing latency >10 seconds
- **Warning:** Event error rate >5%, queue depth >500 events
- **Info:** Event processing latency >5 seconds

### Event Audit Log
All events will be logged to Azure Monitor / Application Insights with:
- Event ID, type, source, timestamp
- Handler execution results (success/failure)
- Processing duration
- Error messages (if failed)

---

## Phase Implementation

### Phase 1-3 (Local Development - $0 budget)
- **Mock event sources** with test fixtures (JSON files)
- **Simulate webhooks** with manual HTTP POST to local endpoints
- **Use RabbitMQ in Docker** as NATS substitute for local testing
- **Scheduled events** simulated with Python `schedule` library or cron-like mock

### Phase 4 (Azure Production - $200/month budget)
- **Real Shopify/Zendesk webhooks** configured to Azure Function endpoint
- **NATS JetStream** deployed in Container Instance (~$10-20/month)
- **Azure Functions Timer Triggers** for scheduled events (~$5-10/month)
- **RSS polling** via Azure Function or Container Instance cron job

### Phase 5 (Production Testing & Go-Live)
- **Load test event ingestion** (1000 events/min sustained)
- **Validate webhook reliability** (99.9% delivery rate)
- **DR test:** Event replay from NATS JetStream after simulated failure

---

## Budget Impact

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| NATS JetStream (Container Instance) | $10-20 | Shared with AGNTCY transport layer |
| Azure Functions (event ingestion) | $5-10 | Serverless, pay-per-execution |
| Azure Functions (scheduled triggers) | $5-10 | Timer triggers for cron jobs |
| Event storage (7-day retention) | $2-5 | NATS JetStream disk storage |
| **Total Event Infrastructure** | **$22-45/month** | Within $200 total budget |

---

## References

- **PROJECT-README.txt:** System architecture and KPI requirements
- **CLAUDE.md:** Technology stack and cost constraints
- **user-stories-phased.md:** User story catalog for event-driven features
- **data-staleness-requirements.md:** Event-triggered cache invalidation rules

---

**Document Status:** ✅ Approved with 5 new user stories required
**Next Steps:**
1. Create 5 new GitHub issues for event-driven stories (Stories 7.20-7.22, 1.41, 2.23)
2. Design event ingestion service architecture
3. Implement NATS JetStream event bus integration
4. Create event handler interfaces for each agent

