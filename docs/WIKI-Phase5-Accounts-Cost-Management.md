# Phase 5 Accounts, Subscriptions & Cost Management

**Purpose:** Complete guide to accounts required for Phase 5 production deployment, with detailed cost analysis, scaling projections, and optimization strategies.

**Last Updated:** 2026-01-25

**Audience:** Technical operators and managers responsible for predicting and managing cloud costs.

**Budget:** $310-360/month (Phase 4-5), optimization target $200-250/month (Post Phase 5)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Required Accounts & Subscriptions](#required-accounts--subscriptions)
3. [Cost Breakdown by Category](#cost-breakdown-by-category)
4. [Cost Scaling Analysis](#cost-scaling-analysis)
5. [Configuration Options & Trade-offs](#configuration-options--trade-offs)
6. [Cost Optimization Strategies](#cost-optimization-strategies)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Cost Projection Calculator](#cost-projection-calculator)
9. [Risk Factors & Contingencies](#risk-factors--contingencies)
10. [Post Phase 5 Optimization Roadmap](#post-phase-5-optimization-roadmap)

---

## Executive Summary

### Budget Overview

| Phase | Monthly Budget | Status |
|-------|---------------|--------|
| Phase 1-3 (Local Development) | $0 | Complete |
| Phase 4-5 (Production) | $310-360 | Target |
| Post Phase 5 (Optimized) | $200-250 | Future goal |

### Cost Distribution (Phase 5)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Monthly Cost Distribution                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Compute (27%)        ████████████░░░░░░░░░░░░░  $75-110       │
│  AI/ML (17%)          ██████░░░░░░░░░░░░░░░░░░░  $48-62        │
│  Data (17%)           ██████░░░░░░░░░░░░░░░░░░░  $36-65        │
│  Monitoring (12%)     █████░░░░░░░░░░░░░░░░░░░░  $32-43        │
│  Networking (10%)     ████░░░░░░░░░░░░░░░░░░░░░  $20-40        │
│  Events (6%)          ███░░░░░░░░░░░░░░░░░░░░░░  $12-25        │
│  Buffer (11%)         ████░░░░░░░░░░░░░░░░░░░░░  $35-45        │
│                                                                 │
│  TOTAL: $310-360/month                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Cost Drivers

1. **Azure Container Instances** - 6 agents, scales with traffic
2. **Azure OpenAI** - Token usage scales linearly with conversations
3. **Cosmos DB** - Request Units scale with query volume
4. **Azure Monitor** - Log ingestion scales with trace volume

---

## Required Accounts & Subscriptions

### 1. Azure Accounts

#### Azure Subscription (Pay-As-You-Go)

| Attribute | Value |
|-----------|-------|
| **Type** | Pay-As-You-Go |
| **Purpose** | Host all Azure resources |
| **Monthly Cost** | $310-360 (all Azure services) |
| **Region** | East US (primary) |
| **Billing Cycle** | Monthly |

**Setup Requirements:**
- [ ] Create Azure account at [azure.microsoft.com](https://azure.microsoft.com)
- [ ] Enable Pay-As-You-Go billing
- [ ] Create Resource Group: `agntcy-prod-rg`
- [ ] Configure budget alerts (see [Monitoring & Alerts](#monitoring--alerts))
- [ ] Create Service Principal for Terraform automation

**Service Principal Setup:**
```bash
# Create Service Principal for Terraform
az ad sp create-for-rbac \
  --name "terraform-agntcy-prod" \
  --role "Contributor" \
  --scopes "/subscriptions/<subscription-id>/resourceGroups/agntcy-prod-rg"

# Store credentials in Azure Key Vault (not local files)
```

---

#### Azure DevOps Organization

| Attribute | Value |
|-----------|-------|
| **Type** | Free (up to 5 users) |
| **Purpose** | CI/CD pipelines, artifact storage |
| **Monthly Cost** | $0 |
| **URL** | `https://dev.azure.com/{your-org}` |

**Setup Requirements:**
- [ ] Create organization at [dev.azure.com](https://dev.azure.com)
- [ ] Create project: `agntcy-multi-agent`
- [ ] Configure service connection to Azure subscription
- [ ] Import `azure-pipelines.yml` from repository

---

### 2. Azure Services (Within Subscription)

#### Container Registry (Basic Tier)

| Attribute | Value |
|-----------|-------|
| **SKU** | Basic |
| **Storage** | 10 GB included |
| **Monthly Cost** | ~$5 |
| **Purpose** | Store agent container images |

**Cost Scaling:**
- Storage: $0.003/GB/day beyond 10 GB
- Build minutes: $0.0001/second (if using ACR Tasks)

**Optimization:** Delete unused images after 30 days (lifecycle policy)

---

#### Container Instances (6 Agents)

| Agent | vCPU | Memory | Monthly Cost (Est.) |
|-------|------|--------|---------------------|
| Intent Classification | 1 | 2 GB | $8-15 |
| Knowledge Retrieval | 1 | 2 GB | $8-15 |
| Response Generation | 1 | 2 GB | $8-15 |
| Escalation | 0.5 | 1 GB | $4-8 |
| Analytics | 0.5 | 1 GB | $4-8 |
| **Critic/Supervisor** | 1 | 2 GB | $8-15 |
| **NATS JetStream** | 1 | 2 GB | $10-20 |
| **TOTAL** | | | **$50-96** |

**Cost Scaling:**
- vCPU: $0.0000125/second ($0.045/hour, $32.85/month continuous)
- Memory: $0.0000125/GB/second ($0.045/GB/hour)
- Each additional instance: +$8-15/month per agent

**Key Insight:** Container Instances are billed per-second. Aggressive auto-scaling down to 0 instances during idle periods can reduce costs by 30-50%.

---

#### Cosmos DB (Serverless)

| Component | Purpose | Monthly Cost (Est.) |
|-----------|---------|---------------------|
| Core (SQL API) | Real-time data (orders, conversations) | $15-30 |
| Analytical Store | Metrics, historical data | Included |
| Vector Search (MongoDB API) | RAG embeddings | $5-10 |
| **TOTAL** | | **$20-40** |

**Cost Scaling:**
- Request Units: $0.25 per 1 million RUs
- Storage: $0.25/GB/month
- Serverless max: 5,000 RU/s burst

**Estimation Formula:**
```
Monthly RU Cost = (Avg RU/s) × 3600 × 24 × 30 × $0.00000025
Monthly RU Cost = (Avg RU/s) × $0.648

Example: 100 RU/s average = $64.80/month
Example: 20 RU/s average = $12.96/month (typical Phase 5)
```

**Key Insight:** Serverless mode eliminates idle costs but has higher per-RU pricing. Break-even with provisioned throughput is ~400 RU/s sustained.

---

#### Blob Storage + CDN

| Component | Purpose | Monthly Cost (Est.) |
|-----------|---------|---------------------|
| Storage (Hot tier) | Knowledge base, logs | $2-5 |
| CDN (Standard) | Static content delivery | $3-5 |
| **TOTAL** | | **$5-10** |

**Cost Scaling:**
- Storage: $0.0184/GB/month (Hot), $0.01/GB (Cool), $0.00099/GB (Archive)
- CDN egress: $0.087/GB (first 10 TB)
- Operations: $0.0004 per 10,000 operations

**Key Insight:** Knowledge base is ~75 documents (~1 MB). CDN caches for 1 hour, reducing origin requests by 80%+.

---

#### Azure Key Vault (Standard)

| Component | Purpose | Monthly Cost (Est.) |
|-----------|---------|---------------------|
| Secrets storage | API keys, connection strings | $0.50 |
| Secret operations | PII token mapping | $0.50-4.50 |
| **TOTAL** | | **$1-5** |

**Cost Scaling:**
- Secrets: $0.03 per 10,000 operations
- Keys: $0.03 per 10,000 operations
- Certificates: $3/certificate/month

**Estimation Formula:**
```
Monthly Key Vault Cost = (Secrets × $0.03/10K) + (Operations × $0.03/10K)

Example: 100 secrets, 500K operations/month
Cost = $0.30 + $1.50 = $1.80/month
```

---

#### Azure Functions (Consumption Plan)

| Component | Purpose | Monthly Cost (Est.) |
|-----------|---------|---------------------|
| Execution time | Event ingestion, cron jobs | $3-8 |
| Executions | Webhook handlers | $2-5 |
| **TOTAL** | | **$5-13** |

**Cost Scaling:**
- Executions: $0.20 per million executions (first 1M free)
- Execution time: $0.000016/GB-second
- Memory: Configurable 128 MB - 1.5 GB

**Estimation Formula:**
```
Monthly Functions Cost = (Executions - 1M) × $0.0000002 + (GB-seconds × $0.000016)

Example: 2M executions, 100K GB-seconds
Cost = (1M × $0.0000002) + (100K × $0.000016) = $0.20 + $1.60 = $1.80/month
```

**Key Insight:** First 1 million executions free. Event-driven architecture typically uses 500K-2M executions/month.

---

#### Application Gateway (Standard_v2)

| Component | Purpose | Monthly Cost (Est.) |
|-----------|---------|---------------------|
| Fixed cost | Gateway instance | $18-25 |
| Capacity units | Traffic processing | $2-15 |
| **TOTAL** | | **$20-40** |

**Cost Scaling:**
- Fixed: $0.025/hour (~$18.25/month)
- Capacity units: $0.008/CU/hour
- Data processed: $0.008/GB

**Key Insight:** Application Gateway has significant fixed cost. For lower traffic, consider Azure Front Door (consumption-based) or direct Container Instance exposure with TLS.

**Alternative (Lower Cost):**
- Skip Application Gateway, use Container Instance with TLS: Saves $20-40/month
- Trade-off: No WAF, no automatic failover, manual TLS management

---

#### Azure Monitor + Application Insights

| Component | Purpose | Monthly Cost (Est.) |
|-----------|---------|---------------------|
| Log Analytics (7-day retention) | Centralized logging | $5-10 |
| Application Insights | APM, tracing | $10-20 |
| Alerts | Cost and performance alerts | $0.10/alert rule |
| **TOTAL** | | **$15-30** |

**Cost Scaling:**
- Log ingestion: $2.30/GB
- Log retention: First 31 days free, then $0.10/GB/month
- Alert rules: $0.10/rule/month

**Estimation Formula:**
```
Monthly Log Cost = (Daily GB × 30) × $2.30

Example: 500 MB/day logs
Cost = (0.5 × 30) × $2.30 = $34.50/month (unoptimized)

With 50% sampling:
Cost = (0.25 × 30) × $2.30 = $17.25/month
```

**Key Insight:** Trace sampling (50% for successful conversations, 100% for errors) reduces log volume by 40-50%.

---

### 3. AI/ML Services

#### Azure OpenAI Service

| Model | Purpose | Cost per 1M Tokens | Est. Monthly Tokens | Est. Cost |
|-------|---------|-------------------|---------------------|-----------|
| GPT-4o-mini | Intent, Validation | $0.15 input, $0.60 output | 8M | $1.20-4.80 |
| GPT-4o | Response Generation | $2.50 input, $10.00 output | 15M | $37.50-150 |
| text-embedding-3-large | RAG embeddings | $0.13 | 3M | $0.39 |
| **TOTAL** | | | | **$39-155** |

**Realistic Phase 5 Estimate:** $48-62/month (conservative usage)

**Cost Scaling:**
- Linear with conversation volume
- Each conversation: ~500-1500 tokens (intent + validation + response)
- 1000 conversations/day = ~1M tokens/day = ~$3-10/day

**Estimation Formula:**
```
Daily Token Cost = (Conversations × Avg Tokens) × Token Price

Example: 500 conversations/day, 1000 tokens each
GPT-4o-mini (intent + validation): 500 × 300 × $0.00000015 = $0.02/day
GPT-4o (response): 500 × 700 × $0.0000025 = $0.88/day
Total: ~$0.90/day = ~$27/month
```

**Key Insight:** Response generation (GPT-4o) is 85% of AI costs. Caching common responses can reduce this by 30-50%.

---

#### Azure Content Safety API

| Component | Purpose | Monthly Cost (Est.) |
|-----------|---------|---------------------|
| Text moderation | Critic/Supervisor validation | $8-12 |
| **TOTAL** | | **$8-12** |

**Cost Scaling:**
- $1 per 1,000 text records (up to 1,000 characters each)
- Phase 5 estimate: 8,000-12,000 validations/month

**Key Insight:** Content Safety API is optional. GPT-4o-mini can perform similar validation at lower cost for most use cases.

---

### 4. Third-Party API Accounts

#### Shopify Partner Account

| Attribute | Value |
|-----------|-------|
| **Type** | Partner Program (Free) |
| **Purpose** | Order, product, inventory APIs |
| **Monthly Cost** | $0 |
| **Setup URL** | [shopify.com/partners](https://www.shopify.com/partners) |

**Included:**
- Development Store (unlimited products, orders)
- Admin API access (REST and GraphQL)
- Webhook subscriptions (orders, inventory, customers)

**Setup Requirements:**
- [ ] Create Partner account
- [ ] Create Development Store
- [ ] Generate API credentials
- [ ] Store credentials in Azure Key Vault
- [ ] Configure webhooks for event-driven architecture

---

#### Zendesk Account

| Option | Type | Monthly Cost | Recommendation |
|--------|------|--------------|----------------|
| **Sandbox** | Partner/Developer | $0 | Recommended for testing |
| **Trial** | 14-day free | $0 | Short-term only |
| **Team** | Paid (per agent) | $19-49 | If trial expires |

**Setup Requirements:**
- [ ] Request Sandbox account (preferred) or start Trial
- [ ] Generate API token
- [ ] Store token in Azure Key Vault
- [ ] Configure webhooks (ticket events, satisfaction ratings)

**Cost Impact:** If Zendesk paid plan required, reduce Azure budget by $19-49 to stay within $360 ceiling.

---

#### Mailchimp Account

| Attribute | Value |
|-----------|-------|
| **Type** | Free Plan |
| **Limits** | 500 contacts, 1,000 sends/month |
| **Monthly Cost** | $0 |
| **Upgrade** | $13/month (Essentials, 500+ contacts) |

**Setup Requirements:**
- [ ] Create free account
- [ ] Generate API key
- [ ] Store key in Azure Key Vault
- [ ] Create audience for subscribers

---

#### Google Analytics 4

| Attribute | Value |
|-----------|-------|
| **Type** | Free |
| **Purpose** | Customer behavior tracking |
| **Monthly Cost** | $0 |

**Setup Requirements:**
- [ ] Create GA4 property
- [ ] Create Service Account in Google Cloud Console
- [ ] Download JSON credentials
- [ ] Store credentials in Azure Key Vault

---

### 5. Development & CI/CD Tools

| Tool | Type | Purpose | Cost |
|------|------|---------|------|
| **Terraform** | Open Source | Infrastructure-as-Code | $0 |
| **Azure CLI** | Free | Resource management | $0 |
| **GitHub CLI (gh)** | Free | Issue management | $0 |
| **Docker Desktop** | Free (personal) | Local containers | $0 |
| **Python 3.12+** | Open Source | AGNTCY SDK runtime | $0 |
| **VS Code** | Free | IDE | $0 |

---

### 6. Security & Scanning Tools

| Tool | Type | Purpose | Cost |
|------|------|---------|------|
| **Dependabot** | GitHub (free) | Dependency updates | $0 |
| **Snyk** | Free tier | Vulnerability scanning | $0 |
| **OWASP ZAP** | Open Source | Web security scanning | $0 |
| **git-secrets** | Open Source | Pre-commit secret detection | $0 |
| **detect-secrets** | Open Source | Secret scanning | $0 |

---

## Cost Breakdown by Category

### Detailed Monthly Cost Table

| Category | Service | Low Est. | High Est. | Notes |
|----------|---------|----------|-----------|-------|
| **Compute** | | | | |
| | Container Instances (6 agents) | $50 | $80 | 1-3 instances each |
| | Azure Functions | $5 | $10 | Event ingestion |
| | Container Registry | $5 | $5 | Basic tier |
| | **Subtotal** | **$60** | **$95** | |
| **Data** | | | | |
| | Cosmos DB Serverless | $20 | $40 | SQL + Vector |
| | Blob Storage + CDN | $5 | $10 | Knowledge base |
| | Key Vault | $1 | $5 | Secrets + PII tokens |
| | **Subtotal** | **$26** | **$55** | |
| **AI/ML** | | | | |
| | Azure OpenAI | $40 | $55 | GPT-4o, 4o-mini, embeddings |
| | Content Safety API | $8 | $12 | Optional |
| | **Subtotal** | **$48** | **$67** | |
| **Networking** | | | | |
| | Application Gateway | $20 | $40 | Standard_v2 |
| | Egress | $0 | $5 | Data transfer |
| | **Subtotal** | **$20** | **$45** | |
| **Monitoring** | | | | |
| | Log Analytics | $5 | $10 | 7-day retention |
| | Application Insights | $10 | $20 | APM, tracing |
| | Alert rules | $1 | $3 | 10-30 rules |
| | **Subtotal** | **$16** | **$33** | |
| **Events** | | | | |
| | NATS (Container Instance) | $10 | $20 | Included in compute |
| | Event storage | $2 | $5 | JetStream disk |
| | **Subtotal** | **$12** | **$25** | |
| **GRAND TOTAL** | | **$182** | **$320** | |
| **Buffer (15%)** | | **$27** | **$48** | Spike protection |
| **TOTAL WITH BUFFER** | | **$209** | **$368** | |

**Target Range:** $310-360/month (with buffer for cost spikes)

---

## Cost Scaling Analysis

### Scaling Factors

Understanding how costs scale with usage is critical for budget planning.

#### 1. Conversation Volume

| Daily Conversations | AI Cost | Compute Cost | Data Cost | Total Monthly |
|--------------------|---------|--------------|-----------|---------------|
| 100 | $15 | $60 | $25 | ~$210 |
| 500 | $35 | $70 | $30 | ~$270 |
| 1,000 | $55 | $85 | $40 | ~$330 |
| 2,000 | $95 | $110 | $55 | ~$420 |
| 5,000 | $200 | $180 | $85 | ~$650 |

**Key Insight:** AI costs scale linearly. Compute scales step-wise (add instances). Data scales sub-linearly (caching helps).

---

#### 2. Agent Instance Scaling

| Scenario | Instances | Monthly Cost | When to Use |
|----------|-----------|--------------|-------------|
| **Minimum** | 1 per agent (6 total) | $50-60 | <200 conversations/day |
| **Standard** | 2 per agent (12 total) | $100-120 | 200-1000 conversations/day |
| **High** | 3 per agent (18 total) | $150-180 | 1000+ conversations/day |

**Auto-Scale Trigger Points:**
- Scale up: CPU > 70% for 5 minutes
- Scale down: CPU < 30% for 10 minutes

---

#### 3. Token Usage Scaling

| Usage Level | Daily Tokens | Monthly Cost | Use Case |
|-------------|--------------|--------------|----------|
| Low | 100K | $15-20 | Testing, low traffic |
| Medium | 500K | $35-50 | Typical Phase 5 |
| High | 2M | $100-150 | High traffic, verbose responses |
| Very High | 5M+ | $250+ | Requires optimization |

**Cost Drivers:**
- Response length: Longer responses = more tokens
- Retry rate: Critic/Supervisor rejections = regeneration = 2-3x tokens
- Caching: Cache hits = $0 additional cost

---

#### 4. Cosmos DB RU Scaling

| RU/s Average | Monthly Cost | Use Case |
|--------------|--------------|----------|
| 10 | $6.50 | Very low traffic |
| 50 | $32 | Typical Phase 5 |
| 100 | $65 | High traffic |
| 400+ | $260+ | Consider provisioned mode |

**Serverless vs. Provisioned Break-Even:**
- Serverless: Better for <400 RU/s average
- Provisioned: Better for >400 RU/s sustained

---

### Cost Projection Chart

```
Monthly Cost vs. Daily Conversations

$700 ┤                                          ╭─
     │                                       ╭──╯
$600 ┤                                    ╭──╯
     │                                 ╭──╯
$500 ┤                              ╭──╯
     │                           ╭──╯
$400 ┤                        ╭──╯
     │                     ╭──╯           ← Budget ceiling ($360)
$350 ┤─────────────────────╯──────────────────────────
$300 ┤              ╭──────╯
     │           ╭──╯
$250 ┤        ╭──╯
     │     ╭──╯
$200 ┤──╭──╯
     │╭─╯
$150 ┼────┼────┼────┼────┼────┼────┼────┼────┼────┼───
     0   100  200  500  800  1K   1.5K  2K   3K   5K
                    Daily Conversations
```

**Interpretation:**
- 0-800 conversations/day: Comfortably within budget
- 800-1200 conversations/day: Near budget ceiling, optimize recommended
- 1200+ conversations/day: Exceeds budget, requires optimization or budget increase

---

## Configuration Options & Trade-offs

### Decision Matrix

Each configuration option has cost, performance, and complexity trade-offs.

---

### 1. Container Instance Size

| Option | vCPU | Memory | Cost/Month | Performance | Recommendation |
|--------|------|--------|------------|-------------|----------------|
| **Minimal** | 0.5 | 1 GB | $4-8 | Limited, may throttle | Analytics, Escalation only |
| **Standard** | 1 | 2 GB | $8-15 | Good for most agents | Intent, Knowledge, Response, Critic |
| **Enhanced** | 2 | 4 GB | $16-30 | High throughput | Only if needed |

**Trade-off:** Smaller instances save ~$40/month but may cause latency spikes during traffic bursts.

**Recommendation:** Start with Standard, monitor CPU/memory, downsize if <50% utilization sustained.

---

### 2. Cosmos DB Mode

| Option | Cost Model | Monthly Est. | Best For |
|--------|------------|--------------|----------|
| **Serverless** | Per-RU consumed | $20-65 | Variable traffic, <400 RU/s avg |
| **Provisioned (400 RU/s)** | Fixed + burst | $24 fixed | Predictable traffic, >400 RU/s |
| **Provisioned (Autoscale)** | Min + scale | $24-240 | Unpredictable spikes |

**Trade-off:** Serverless has no minimum cost but higher per-RU price. Provisioned requires capacity planning but lower per-RU cost.

**Recommendation:** Use Serverless for Phase 5. Switch to Provisioned (Autoscale) if sustained >400 RU/s.

---

### 3. Application Gateway vs. Alternatives

| Option | Monthly Cost | Features | Trade-off |
|--------|--------------|----------|-----------|
| **Application Gateway (Standard_v2)** | $20-40 | WAF, SSL offload, autoscaling | Higher fixed cost |
| **Azure Front Door (Consumption)** | $5-15 | Global CDN, SSL, rules | Per-request pricing |
| **Direct Container + TLS** | $0 | Basic TLS only | No WAF, manual cert renewal |

**Trade-off:** Application Gateway provides enterprise security (WAF) but costs $20-40/month fixed. Direct exposure saves money but increases security risk.

**Recommendation:** Use Application Gateway for production. Consider Front Door if global distribution needed.

---

### 4. Log Retention Period

| Option | Retention | Monthly Cost | Use Case |
|--------|-----------|--------------|----------|
| **7 days** | 1 week | $5-10 | Cost-optimized, recent debugging only |
| **30 days** | 1 month | $15-25 | Standard, compliance needs |
| **90 days** | 3 months | $30-50 | Audit, compliance, long investigations |

**Trade-off:** Longer retention enables historical analysis but increases storage costs linearly.

**Recommendation:** Use 7-day retention for Phase 5. Export critical traces to Blob Storage (cold tier) for long-term archive.

---

### 5. Trace Sampling Rate

| Option | Sample Rate | Monthly Cost Impact | Coverage |
|--------|-------------|---------------------|----------|
| **Full** | 100% | $15-25 | All conversations traced |
| **Standard** | 50% | $8-15 | Half of successful conversations |
| **Optimized** | 10% success, 100% errors | $5-10 | Errors + sample of success |

**Trade-off:** Lower sampling reduces cost but may miss edge cases. Always sample 100% of errors/escalations.

**Recommendation:** Use "Optimized" sampling (10% success, 100% errors/escalations).

---

### 6. AI Model Selection

| Scenario | Model Mix | Monthly Est. | Quality |
|----------|-----------|--------------|---------|
| **Cost Optimized** | GPT-4o-mini everywhere | $15-25 | Good, may miss nuance |
| **Quality Optimized** | GPT-4o everywhere | $150-250 | Best, expensive |
| **Balanced (Recommended)** | 4o-mini (intent, validation) + 4o (response) | $48-62 | Best value |

**Trade-off:** GPT-4o produces better customer-facing responses but costs 15x more per token than GPT-4o-mini.

**Recommendation:** Use balanced approach. Monitor CSAT; if >4.0/5.0, consider switching more tasks to GPT-4o-mini.

---

### 7. Zendesk Account Type

| Option | Monthly Cost | Duration | Recommendation |
|--------|--------------|----------|----------------|
| **Sandbox** | $0 | Unlimited | Best for testing |
| **Trial** | $0 | 14 days | Short-term only |
| **Team (1 agent)** | $19 | Ongoing | If sandbox unavailable |
| **Professional** | $49 | Ongoing | If advanced features needed |

**Trade-off:** Paid Zendesk reduces Azure budget headroom.

**Recommendation:** Request Sandbox first. If unavailable, reduce Azure Functions or Container sizes to accommodate $19-49/month.

---

## Cost Optimization Strategies

### Quick Wins (Implement Immediately)

| Strategy | Monthly Savings | Effort | Impact |
|----------|-----------------|--------|--------|
| 7-day log retention (not 30) | $10-15 | Low | Medium |
| 50% trace sampling | $5-10 | Low | Low |
| Night shutdown (2am-6am ET) | $15-25 | Medium | Medium |
| GPT-4o-mini for validation | $10-20 | Low | Low |
| **Total Quick Wins** | **$40-70** | | |

---

### Medium-Term Optimizations (Month 1-3)

| Strategy | Monthly Savings | Effort | Impact |
|----------|-----------------|--------|--------|
| Response caching (common queries) | $10-30 | Medium | Medium |
| Right-size Container Instances | $10-20 | Medium | Low |
| Cosmos DB query optimization | $5-15 | High | Low |
| CDN cache tuning | $2-5 | Low | Low |
| **Total Medium-Term** | **$27-70** | | |

---

### Long-Term Optimizations (Post Phase 5)

| Strategy | Monthly Savings | Effort | Impact |
|----------|-----------------|--------|--------|
| Fine-tuned models (fewer tokens) | $15-30 | High | Medium |
| Self-hosted Qdrant (vs Cosmos vector) | $5-10 | High | Low |
| Remove Application Gateway | $20-40 | High | High (security trade-off) |
| Provisioned Cosmos (if high traffic) | $10-30 | Medium | Medium |
| **Total Long-Term** | **$50-110** | | |

---

### Optimization Decision Tree

```
START: Is monthly cost > $360?
  │
  ├── YES → Check AI costs first (usually largest)
  │         │
  │         ├── AI > $60/month? → Implement response caching
  │         │                   → Review retry rate (reduce regenerations)
  │         │                   → Consider GPT-4o-mini for more tasks
  │         │
  │         └── AI < $60/month? → Check Container costs
  │                              → Right-size instances
  │                              → Enable night shutdown
  │
  └── NO → Is cost > $300?
           │
           ├── YES → Apply quick wins (log retention, sampling)
           │
           └── NO → Cost optimized, monitor for changes
```

---

## Monitoring & Alerts

### Budget Alerts (Required)

Configure these alerts in Azure Cost Management:

| Alert | Threshold | Amount | Action |
|-------|-----------|--------|--------|
| **Warning** | 70% | $252 | Email notification |
| **High** | 83% | $299 | Email + Slack/Teams |
| **Critical** | 93% | $335 | Email + Slack + PagerDuty |
| **Exceeded** | 100% | $360 | All channels + consider scale-down |

**Setup (Azure Portal):**
1. Navigate to Cost Management + Billing
2. Select subscription → Budgets
3. Create budget: $360/month
4. Add alert conditions at 70%, 83%, 93%, 100%
5. Configure action groups for notifications

---

### Cost Monitoring Dashboard

**Key Metrics to Track (Grafana/Azure Monitor):**

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Daily cost | <$12 | >$15 |
| AI token usage | <50K/day | >100K/day |
| Container CPU (avg) | 40-60% | >80% or <20% |
| Cosmos RU/s (avg) | <100 | >200 |
| Log ingestion | <500 MB/day | >1 GB/day |

**Grafana Dashboard Panels:**
1. Daily cost trend (7-day rolling)
2. Cost by service (pie chart)
3. AI token usage (line chart)
4. Container utilization (heat map)
5. Projected monthly cost (gauge)

---

### Anomaly Detection

Configure alerts for unusual spending patterns:

| Condition | Alert |
|-----------|-------|
| Daily cost > 150% of 7-day average | Email warning |
| AI tokens > 200% of daily average | Investigate immediately |
| Cosmos RU spike > 500 RU/s sustained | Check for runaway queries |
| Log ingestion spike > 2 GB/day | Check for logging loop |

---

## Cost Projection Calculator

### Simple Calculator

Use this formula to estimate monthly costs:

```
Monthly Cost = Base + (Conversations × Per-Conversation Cost) + Variable

Where:
  Base = $150 (fixed infrastructure)
  Per-Conversation Cost = $0.05-0.10 (AI + compute + data)
  Variable = $20-50 (monitoring, networking, spikes)

Example:
  1000 conversations/day × 30 days = 30,000 conversations/month
  Cost = $150 + (30,000 × $0.07) + $35
  Cost = $150 + $2,100 + $35 = $2,285 ❌ (exceeds budget)

  500 conversations/day × 30 days = 15,000 conversations/month
  Cost = $150 + (15,000 × $0.07) + $35
  Cost = $150 + $1,050 + $35 = $1,235 ❌ (still exceeds)

With optimization (caching, sampling):
  Per-Conversation Cost = $0.03
  Cost = $150 + (15,000 × $0.03) + $35
  Cost = $150 + $450 + $35 = $635 ❌

Realistic Phase 5 (with heavy optimization):
  Per-Conversation Cost = $0.01 (cached, sampled, optimized)
  Cost = $150 + (15,000 × $0.01) + $35
  Cost = $150 + $150 + $35 = $335 ✓
```

**Key Insight:** At $360/month budget, maximum ~20,000 conversations/month with heavy optimization, or ~3,000 conversations/month without optimization.

---

### Detailed Cost Calculator (Spreadsheet)

For detailed planning, use this structure:

| Line Item | Unit | Quantity | Unit Cost | Monthly Total |
|-----------|------|----------|-----------|---------------|
| Container Instances | vCPU-hour | 4,320 | $0.045 | $194 |
| Cosmos DB RUs | Million RUs | 50 | $0.25 | $12.50 |
| Azure OpenAI (GPT-4o) | Million tokens | 10 | $2.50 | $25 |
| Azure OpenAI (GPT-4o-mini) | Million tokens | 5 | $0.15 | $0.75 |
| Blob Storage | GB | 10 | $0.02 | $0.20 |
| Log Analytics | GB ingested | 10 | $2.30 | $23 |
| Application Gateway | Hour | 720 | $0.025 | $18 |
| Key Vault operations | 10K operations | 50 | $0.03 | $1.50 |
| **SUBTOTAL** | | | | **$275** |
| Buffer (15%) | | | | $41 |
| **TOTAL** | | | | **$316** |

---

## Risk Factors & Contingencies

### Cost Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **AI token spike** (retry loops, verbose responses) | Medium | High (+$50-100) | Cache responses, monitor retry rate |
| **Cosmos DB throttling** (query spike) | Low | Medium (+$20-50) | Optimize queries, add caching |
| **Container scaling runaway** | Low | Medium (+$30-60) | Set max instances, review auto-scale rules |
| **Log ingestion explosion** | Medium | Medium (+$20-40) | Sampling, retention limits, alert on spike |
| **Zendesk upgrade required** | Medium | Low (+$19-49) | Budget headroom, use sandbox |
| **Azure OpenAI rate limit** | Low | High (downtime) | Request quota increase, fallback provider |

---

### Contingency Budget Allocation

Reserve 15% of budget for unexpected costs:

| Category | Budget | Contingency (15%) | Total Ceiling |
|----------|--------|-------------------|---------------|
| Target | $310 | $47 | $357 |
| High estimate | $360 | $54 | $414 |

**Contingency Triggers:**
- Use contingency if any category exceeds estimate by >20%
- Review and reallocate monthly
- Document all contingency usage

---

### Fallback Options

If costs exceed budget despite optimization:

| Scenario | Action | Savings |
|----------|--------|---------|
| **Minor overage (+$20-50)** | Reduce log retention to 3 days, increase sampling to 25% | $15-25 |
| **Moderate overage (+$50-100)** | Switch GPT-4o → GPT-4o-mini for responses, reduce container sizes | $30-50 |
| **Significant overage (+$100+)** | Disable Critic/Supervisor, reduce to 4 agents, remove App Gateway | $50-80 |
| **Emergency** | Scale down to minimum configuration, notify stakeholders | Variable |

---

## Post Phase 5 Optimization Roadmap

### Target: $200-250/month

| Phase | Timeline | Actions | Expected Savings |
|-------|----------|---------|------------------|
| **Immediate** | Week 1-2 | Quick wins (retention, sampling, shutdown) | $40-70 |
| **Short-term** | Month 1-2 | Response caching, right-sizing | $30-50 |
| **Medium-term** | Month 3-6 | Fine-tuned models, Cosmos optimization | $30-50 |
| **Long-term** | Month 6-12 | Self-hosted components, architecture review | $20-40 |
| **TOTAL** | | | **$120-210** |

### Optimized Architecture (Post Phase 5)

```
Current Phase 5: $310-360/month
┌──────────────────────────────────────┐
│ 6 Agents (full size)                 │
│ Cosmos DB Serverless                 │
│ Application Gateway                  │
│ Full tracing (50% sample)            │
│ Azure Content Safety API             │
│ 7-day log retention                  │
└──────────────────────────────────────┘

Optimized: $200-250/month
┌──────────────────────────────────────┐
│ 5 Agents (right-sized) - merge       │
│   Critic into Response               │
│ Cosmos DB Provisioned (if high vol)  │
│ Direct TLS (no App Gateway)          │
│ 10% trace sampling                   │
│ GPT-4o-mini validation (no API)      │
│ 3-day log retention + cold archive   │
└──────────────────────────────────────┘
```

---

## Summary Checklist

### Pre-Deployment Checklist

**Accounts & Subscriptions:**
- [ ] Azure subscription created with Pay-As-You-Go billing
- [ ] Budget set to $360 with alerts at 70%, 83%, 93%, 100%
- [ ] Azure DevOps organization created
- [ ] Service Principal created for Terraform
- [ ] Shopify Partner account with Development Store
- [ ] Zendesk Sandbox/Trial account
- [ ] Mailchimp free account
- [ ] Google Analytics 4 property
- [ ] All API credentials stored in Azure Key Vault

**Cost Optimization:**
- [ ] Log retention set to 7 days
- [ ] Trace sampling configured (50% success, 100% errors)
- [ ] Container auto-scale rules configured (min 1, max 3)
- [ ] Night shutdown scheduled (2am-6am ET)
- [ ] Cost allocation tags applied to all resources
- [ ] Grafana cost dashboard configured

**Monitoring:**
- [ ] Budget alerts tested
- [ ] Cost anomaly detection enabled
- [ ] Daily cost report scheduled
- [ ] Slack/Teams notifications configured

---

## References

- [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
- [Azure OpenAI Pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/)
- [Cosmos DB Pricing](https://azure.microsoft.com/pricing/details/cosmos-db/)
- [Container Instances Pricing](https://azure.microsoft.com/pricing/details/container-instances/)
- [Azure Cost Management Documentation](https://learn.microsoft.com/azure/cost-management-billing/)
- [PROJECT-README.txt](../PROJECT-README.txt) - Original budget constraints
- [CLAUDE.md](../CLAUDE.md) - Project cost optimization principles
- [Architecture Requirements](./architecture-requirements-phase2-5.md) - Detailed service specifications

---

**Document Status:** ✅ Complete
**Last Updated:** 2026-01-25
**Maintained By:** Project Team
**Next Review:** After Phase 5 deployment

---

*This document is designed for technical operators responsible for cost management. For architecture details, see [WIKI-Architecture](./WIKI-Architecture.md).*
