# Phase 4: Azure Production Setup - Kickoff Document

**Phase**: Phase 4 - Azure Production Setup
**Start Date**: TBD (Phase 3 completed January 25, 2026)
**Target Duration**: 6-8 weeks
**Budget**: $310-360/month
**Status**: ⏳ **READY TO START**

---

## Executive Summary

Phase 4 will deploy the Multi-Agent Customer Service platform to Microsoft Azure with real API integrations, Azure OpenAI LLM capabilities, and production-grade infrastructure. This phase transforms the Phase 3 template-based system into a production-ready AI-powered customer service platform.

### Primary Objectives

1. ✅ Deploy infrastructure to Azure East US region using Terraform
2. ✅ Integrate Azure OpenAI Service (GPT-4o-mini, GPT-4o, text-embedding-3-large)
3. ✅ Integrate real APIs (Shopify, Zendesk, Mailchimp, Google Analytics)
4. ✅ Implement RAG pipeline with Cosmos DB vector search
5. ✅ Deploy PII tokenization service with Azure Key Vault
6. ✅ Implement event-driven architecture with NATS JetStream
7. ✅ Deploy Critic/Supervisor Agent (6th agent) for content validation
8. ✅ Implement execution tracing with Azure Monitor + Application Insights
9. ✅ Establish Azure DevOps CI/CD pipelines
10. ✅ Stay within budget ($310-360/month)

### Expected Outcomes

**Test Pass Rate Improvements**:
- E2E scenarios: 5% → >80% (16x improvement)
- Multi-turn conversations: 30% → >80% (2.7x improvement)
- Integration tests: 96% → >95% (maintain high quality)

**Performance Expectations** (with Azure OpenAI):
- P95 response time: 0.11ms → 800-1500ms (10-20x slower, acceptable)
- Throughput: 3,071 req/s → 30-60 req/s (50-100x decrease, expected)
- Concurrent users: 1,000+ → 10-20 (due to LLM API rate limits)

---

## Table of Contents

1. [Phase 3 Handoff Summary](#phase-3-handoff-summary)
2. [Phase 4 Scope](#phase-4-scope)
3. [Architecture Overview](#architecture-overview)
4. [Prerequisites](#prerequisites)
5. [Week-by-Week Plan](#week-by-week-plan)
6. [Budget Breakdown](#budget-breakdown)
7. [Risk Assessment](#risk-assessment)
8. [Success Criteria](#success-criteria)
9. [Phase 4 → Phase 5 Transition](#phase-4--phase-5-transition)

---

## Phase 3 Handoff Summary

### Completed Deliverables from Phase 3

**Test Suites** (ready to run in Phase 4):
- 152 test scenarios across 8 test types
- 81% overall pass rate (123/152 passing)
- Baselines established for Phase 3 → Phase 4 comparison

**Documentation**:
- Testing Guide (1,245 lines)
- Troubleshooting Guide (1,087 lines)
- Deployment Guide (1,176 lines) - Phase 4 preparation
- CI/CD README (356 lines)
- 10 daily summaries (~15,000 lines total)

**CI/CD Pipeline**:
- GitHub Actions workflow (7 jobs)
- PR validation (3 required checks, ~10 min)
- Nightly regression (6 jobs, ~26 min)

**Performance Baselines**:
- P95 response time: 0.11ms
- Throughput: 3,071 req/s (100 concurrent users)
- Resource usage: CPU 0%, Memory 45 MB (1,000 users)

### Known Issues to Resolve in Phase 4

**Expected Test Failures** (will be resolved with Azure OpenAI):
1. **E2E Scenarios** (19/20 failing): Templates lack context awareness
2. **Multi-Turn Conversations** (7/10 failing): No LLM for context-aware responses
3. **Agent Communication** (2/10 failing): Docker networking issues (will use Azure CNI)

**Code Quality Issues** (cosmetic, non-critical):
1. **Black Formatting**: 15 files need formatting
2. **Bandit Security**: 4 medium-severity mock service issues (will replace with real APIs)

### Phase 3 Success Metrics

- ✅ 100% of Phase 3 objectives completed
- ✅ 0 high-severity security issues
- ✅ 0 critical syntax errors
- ✅ Agent architecture validated (correct AGNTCY SDK usage)
- ✅ CI/CD automation in place

---

## Phase 4 Scope

### In Scope ✅

**Infrastructure**:
- Azure Resource Groups (multi-agent-rg, tfstate-rg)
- Azure Container Instances (6 agents)
- Azure OpenAI Service (3 models)
- Cosmos DB Serverless (MongoDB API with vector search)
- Azure Key Vault (PII tokenization, secrets)
- Blob Storage + CDN (knowledge base)
- Application Gateway (WAF, TLS termination)
- Virtual Network (private endpoints, NSGs)
- Azure Monitor + Application Insights (execution tracing)

**Agents** (6 total):
1. Intent Classification Agent (Azure OpenAI GPT-4o-mini)
2. Knowledge Retrieval Agent (Cosmos DB vector search, RAG pipeline)
3. Response Generation Agent (Azure OpenAI GPT-4o)
4. Escalation Agent (Zendesk API integration)
5. Analytics Agent (Google Analytics API, Cosmos analytical store)
6. Critic/Supervisor Agent (GPT-4o-mini for content validation) - **NEW**

**API Integrations**:
- Shopify Admin API (orders, products, inventory)
- Zendesk Support API (tickets, conversations)
- Mailchimp Marketing API (email campaigns)
- Google Analytics Data API (tracking, reporting)

**New Features** (Phase 4):
- RAG pipeline (75-document knowledge base, 1536-dimension embeddings)
- PII tokenization (Azure Key Vault, UUID tokens for third-party AI)
- Event-driven architecture (NATS JetStream, 12 event types)
- Execution tracing (OpenTelemetry, timeline view, decision tree)
- Multi-language support (English, Canadian French, Spanish)

**CI/CD**:
- Azure DevOps Pipelines (replaces GitHub Actions for production)
- Terraform plan/apply automation
- Container image builds (Azure Container Registry)
- Staging → Production promotion

### Out of Scope ❌

**Deferred to Phase 5**:
- Production load testing (100 concurrent users, 1000 req/min)
- Disaster recovery drills (quarterly full rebuild)
- OWASP ZAP security scanning (full penetration testing)
- Cost optimization iteration (target: reduce to $200-250/month)
- Fine-tuned models (self-hosted alternatives)

**Not Planned**:
- Kubernetes/AKS deployment (too expensive, Container Instances sufficient)
- Geo-replication (single region only, East US)
- Real-time translation APIs (use pre-translated templates)
- Premium tiers (use Basic/Standard only)

---

## Architecture Overview

### Azure Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Azure East US Region                        │
│                        ($310-360/month)                          │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Application Gateway (WAF + TLS)         ~$40-50/month    │  │
│  │  - Public endpoint                                         │  │
│  │  - TLS 1.3 termination                                     │  │
│  │  - Web Application Firewall                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Container Instances (6 agents)          ~$30-40/month    │  │
│  │  - intent-classifier                                       │  │
│  │  - knowledge-retrieval                                     │  │
│  │  - response-generator-en/fr/es                            │  │
│  │  - escalation-handler                                      │  │
│  │  - analytics-processor                                     │  │
│  │  - critic-supervisor (NEW)                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Azure OpenAI Service                    ~$48-62/month    │  │
│  │  - GPT-4o-mini (intent + critic)                          │  │
│  │  - GPT-4o (response generation)                           │  │
│  │  - text-embedding-3-large (RAG)                           │  │
│  │  - Rate limits: 60 req/min (mini), 30 req/min (4o)       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Cosmos DB Serverless (MongoDB API)      ~$50-70/month    │  │
│  │  - Real-time data (orders, inventory, tickets)            │  │
│  │  - Vector search (1536 dimensions)                        │  │
│  │  - Analytical store (analytics agent)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Azure Key Vault                         ~$5-10/month     │  │
│  │  - PII tokenization (UUID tokens)                         │  │
│  │  - API keys (Shopify, Zendesk, etc.)                      │  │
│  │  - Soft-delete + purge protection                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Blob Storage + CDN                      ~$10-15/month    │  │
│  │  - Knowledge base (75 documents)                          │  │
│  │  - 1hr cache TTL                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Azure Monitor + Application Insights    ~$32-43/month    │  │
│  │  - Execution tracing (OpenTelemetry)                      │  │
│  │  - 7-day retention, 50% sampling                          │  │
│  │  - Grafana dashboards                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  NATS JetStream (Event Bus)              ~$0              │  │
│  │  - Reuses AGNTCY transport layer                          │  │
│  │  - 12 event types, 7-day retention                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  **TOTAL ESTIMATED COST**: $310-360/month                        │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Customer Request
    ↓
Application Gateway (TLS termination, WAF)
    ↓
Critic/Supervisor Agent (input validation)
    ↓
Intent Classification Agent
    ├→ Azure OpenAI GPT-4o-mini (intent classification)
    └→ Cosmos DB (conversation history)
    ↓
Knowledge Retrieval Agent
    ├→ Cosmos DB Vector Search (semantic search)
    ├→ Blob Storage (knowledge base documents)
    └→ Shopify API (real-time product data)
    ↓
Response Generation Agent
    ├→ Azure OpenAI GPT-4o (context-aware response)
    ├→ Cosmos DB (order/inventory data)
    └→ PII Tokenization (Azure Key Vault)
    ↓
Critic/Supervisor Agent (output validation)
    ↓
Customer Response
    ↓
Analytics Agent (parallel)
    ├→ Google Analytics API (event tracking)
    └→ Cosmos DB Analytical Store (metrics)
    ↓
Escalation Agent (if needed)
    ├→ Zendesk API (ticket creation)
    └→ Mailchimp API (email notification)
```

---

## Prerequisites

### Azure Subscription

**Required**:
- [ ] Azure account created (https://azure.microsoft.com/free/)
- [ ] Subscription ID obtained
- [ ] Billing alerts configured (83% @ $299, 93% @ $335)
- [ ] Service Principal created (Terraform authentication)
- [ ] Contributor role assigned to Service Principal

**Commands**:
```bash
az login
az account set --subscription "Your Subscription Name"

az ad sp create-for-rbac \
  --name "multi-agent-customer-service-sp" \
  --role="Contributor" \
  --scopes="/subscriptions/{subscription-id}"

# Save output:
# - appId (client_id)
# - password (client_secret)
# - tenant (tenant_id)
```

### Third-Party API Accounts

**Required**:
- [ ] **Shopify Partner Account** (free)
  - Create Development Store
  - Generate Admin API access token
  - URL: https://partners.shopify.com/

- [ ] **Zendesk Trial/Sandbox** ($0-19/month)
  - Create trial account
  - Generate API token
  - URL: https://www.zendesk.com/register/

- [ ] **Mailchimp Free Tier** (free, up to 500 contacts)
  - Create account
  - Generate API key
  - URL: https://mailchimp.com/signup/

- [ ] **Google Analytics GA4** (free)
  - Create GA4 property
  - Create Service Account
  - Download JSON key file
  - URL: https://analytics.google.com/

### Development Tools

**Required**:
- [ ] Terraform v1.6+ installed
- [ ] Azure CLI v2.50+ installed
- [ ] Docker Desktop installed
- [ ] Git installed
- [ ] Python 3.14+ installed

**Optional**:
- [ ] kubectl (for future AKS migration)
- [ ] Azure DevOps CLI extension

---

## Week-by-Week Plan

### Week 1-2: Infrastructure Setup

**Week 1 Objectives**:
- [ ] Create Terraform configuration for all Azure resources
- [ ] Set up Terraform state storage (Azure Blob)
- [ ] Configure Service Principal authentication
- [ ] Deploy Resource Groups
- [ ] Deploy Virtual Network with private endpoints
- [ ] Deploy Network Security Groups

**Week 1 Deliverables**:
- terraform/phase4_prod/ directory with complete configuration
- Terraform state backend configured
- Resource Groups created (multi-agent-rg, tfstate-rg)
- Virtual Network deployed

**Week 2 Objectives**:
- [ ] Deploy Azure Key Vault
- [ ] Store all API credentials in Key Vault
- [ ] Deploy Cosmos DB Serverless (MongoDB API)
- [ ] Deploy Blob Storage + CDN
- [ ] Deploy Azure Monitor + Application Insights
- [ ] Deploy Application Gateway

**Week 2 Deliverables**:
- All infrastructure deployed
- Secrets stored in Key Vault
- Monitoring configured
- Smoke tests passing

### Week 3-4: Service Deployment

**Week 3 Objectives**:
- [ ] Deploy Azure OpenAI Service
- [ ] Deploy 3 models (GPT-4o-mini, GPT-4o, text-embedding-3-large)
- [ ] Configure rate limits (60 req/min mini, 30 req/min 4o)
- [ ] Test LLM endpoints

**Week 3 Deliverables**:
- Azure OpenAI Service operational
- 3 models deployed and tested
- Rate limits configured

**Week 4 Objectives**:
- [ ] Build container images for all 6 agents
- [ ] Push images to Azure Container Registry
- [ ] Deploy 6 Container Instances
- [ ] Configure Managed Identity for agents
- [ ] Configure environment variables (Key Vault references)

**Week 4 Deliverables**:
- 6 agents running in Azure Container Instances
- Managed Identity configured
- Agent-to-agent communication working

### Week 5-6: API Integration

**Week 5 Objectives**:
- [ ] Integrate Shopify Admin API (orders, products, inventory)
- [ ] Integrate Zendesk Support API (tickets, conversations)
- [ ] Test API connectivity and authentication

**Week 5 Deliverables**:
- Shopify API integrated
- Zendesk API integrated
- Integration tests passing with real APIs

**Week 6 Objectives**:
- [ ] Integrate Mailchimp Marketing API (email campaigns)
- [ ] Integrate Google Analytics Data API (tracking)
- [ ] Implement RAG pipeline (vector embeddings, Cosmos DB vector search)
- [ ] Load knowledge base (75 documents) to Blob Storage + Cosmos DB

**Week 6 Deliverables**:
- All 4 APIs integrated
- RAG pipeline operational
- Knowledge base loaded (75 documents)

### Week 7-8: Testing & Validation

**Week 7 Objectives**:
- [ ] Run full integration test suite (expect >95% pass rate)
- [ ] Run E2E scenarios (expect >80% pass rate, up from 5%)
- [ ] Run multi-turn conversation tests (expect >80% pass rate, up from 30%)
- [ ] Run agent communication tests (expect >80% pass rate)

**Week 7 Deliverables**:
- Integration tests: >95% pass rate
- E2E tests: >80% pass rate (16x improvement)
- Multi-turn tests: >80% pass rate (2.7x improvement)
- Test results documented

**Week 8 Objectives**:
- [ ] Performance testing with real APIs (expect P95: 800-1500ms)
- [ ] Load testing (10, 20, 30 concurrent users)
- [ ] Run Bandit security scan
- [ ] Run OWASP ZAP security scan
- [ ] Run Snyk dependency audit
- [ ] Cost optimization iteration

**Week 8 Deliverables**:
- Performance baselines with real APIs
- Load test results (max concurrent users identified)
- Security scan results (0 high-severity issues)
- Cost optimization recommendations

---

## Budget Breakdown

### Azure Service Costs ($310-360/month)

| Service | Monthly Cost | Optimization Strategy |
|---------|--------------|----------------------|
| **Container Instances** (6 agents) | $30-40 | Auto-scale to 1, auto-shutdown 2-6 AM |
| **Azure OpenAI** | $48-62 | Use GPT-4o-mini where possible, cache responses |
| **Cosmos DB Serverless** | $50-70 | Optimize query patterns, staleness tolerances |
| **Key Vault** | $5-10 | Standard tier, minimize operations |
| **Blob Storage + CDN** | $10-15 | 1hr cache TTL, minimize data transfer |
| **Application Insights** | $32-43 | 7-day retention, 50% sampling |
| **Networking** (VNet, App Gateway) | $40-50 | Private endpoints, optimize egress |
| **NATS JetStream** | $0 | Reuses AGNTCY transport layer |
| **TOTAL** | **$310-360** | Target: $200-250 post-Phase 5 |

### Budget Alerts

**Configured in Terraform**:
- **83% threshold** ($299): Email notification to billing@remaker.digital
- **93% threshold** ($335): Email notification to billing + cto@remaker.digital
- **100% threshold** ($360): Hard budget limit (spending freeze)

### Cost Monitoring

**Weekly reviews**:
- Check Azure Cost Management dashboard
- Review resource utilization (right-sizing opportunities)
- Identify unexpected costs
- Document optimization decisions

**Monthly reviews**:
- Compare actual vs budgeted costs
- Review optimization opportunities
- Update Phase 5 cost reduction plan

---

## Risk Assessment

### High-Priority Risks

**Risk 1: Azure OpenAI Rate Limiting**
- **Probability**: High
- **Impact**: High (service degradation)
- **Mitigation**:
  - Implement exponential backoff (retry logic)
  - Request queuing (NATS JetStream)
  - Response caching (Redis optional in Phase 5)
  - Use GPT-4o-mini for non-critical tasks

**Risk 2: Budget Overruns**
- **Probability**: Medium
- **Impact**: High (financial)
- **Mitigation**:
  - Budget alerts at 83% and 93%
  - Weekly cost reviews
  - Aggressive auto-scaling (down to 1 instance)
  - Auto-shutdown during low-traffic hours

**Risk 3: Third-Party API Downtime**
- **Probability**: Medium
- **Impact**: Medium (service interruption)
- **Mitigation**:
  - Graceful degradation (fallback responses)
  - Retry logic with exponential backoff
  - Circuit breaker pattern
  - Status page monitoring

### Medium-Priority Risks

**Risk 4: Performance Degradation**
- **Probability**: Medium
- **Impact**: Medium (user experience)
- **Mitigation**:
  - Performance testing with real APIs
  - Optimize LLM prompts (reduce token usage)
  - Implement caching where possible

**Risk 5: Security Vulnerabilities**
- **Probability**: Low
- **Impact**: High (data breach)
- **Mitigation**:
  - OWASP ZAP scanning
  - Snyk dependency audits
  - PII tokenization for third-party AI
  - TLS 1.3, Managed Identity, private endpoints

---

## Success Criteria

### Test Pass Rates

| Test Suite | Phase 3 Baseline | Phase 4 Target | Improvement |
|------------|------------------|----------------|-------------|
| **Integration Tests** | 96% | >95% | Maintain |
| **E2E Scenarios** | 5% | >80% | 16x |
| **Multi-Turn Conversations** | 30% | >80% | 2.7x |
| **Agent Communication** | 80% | >80% | Maintain |

### Performance Metrics

| Metric | Phase 3 | Phase 4 Target | Status |
|--------|---------|----------------|--------|
| **P95 Response Time** | 0.11ms | <2000ms | Acceptable with LLM |
| **Throughput** | 3,071 req/s | >100 req/min | Within rate limits |
| **Concurrent Users** | 1,000+ | 10-20 | Expected (rate limits) |

### Cost Management

- [ ] Monthly cost: $310-360/month (within budget)
- [ ] Budget alerts firing correctly
- [ ] Weekly cost reviews documented
- [ ] Optimization opportunities identified

### Security

- [ ] 0 high-severity vulnerabilities (OWASP ZAP, Snyk, Bandit)
- [ ] All secrets in Azure Key Vault
- [ ] PII tokenization implemented
- [ ] TLS 1.3 for all connections
- [ ] Managed Identity for all agents

---

## Phase 4 → Phase 5 Transition

### Phase 5 Objectives

**Duration**: 4 weeks
**Focus**: Production deployment, load testing, DR validation, go-live

**Week 1-2**: Pre-Production
- Final security audit
- Disaster recovery drill (full environment rebuild)
- Load testing: 100 concurrent users, 1,000 req/min
- Blue-green deployment preparation

**Week 3**: Go-Live
- Production cutover
- Monitor metrics for 72 hours
- Fix any critical issues

**Week 4**: Post-Launch Optimization
- Cost optimization (reduce to $200-250/month)
- Performance tuning based on production metrics
- Final documentation and blog post

### Phase 5 Success Criteria

- [ ] Production deployment successful
- [ ] Load tests passing (100 users, 1,000 req/min)
- [ ] DR drill successful (RTO <4 hours)
- [ ] Monthly cost: $200-250/month (optimized)
- [ ] Blog post published

---

## Next Steps

**Immediate Actions**:
1. [ ] Create Azure subscription
2. [ ] Set up billing alerts
3. [ ] Create Service Principal
4. [ ] Create third-party API accounts
5. [ ] Begin Terraform configuration (Week 1)

**Phase 4 Kickoff Meeting Agenda**:
1. Review Phase 3 handoff summary
2. Confirm budget allocation ($310-360/month)
3. Review Week 1-2 infrastructure plan
4. Assign responsibilities
5. Set up weekly status meetings

---

**Phase 4 Status**: ⏳ **READY TO START**
**Prerequisites**: 80% complete (Azure subscription, third-party accounts pending)
**Next Milestone**: Week 1 Infrastructure Setup

---

**Document Status**: Draft (Kickoff)
**Created**: January 25, 2026
**Author**: Development Team
**Review Date**: Before Phase 4 start
