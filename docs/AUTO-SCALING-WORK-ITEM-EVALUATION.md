# Auto-Scaling Work Item Evaluation

**Created:** 2026-01-27
**Purpose:** Evaluate new work items resulting from the 10,000 daily users auto-scaling requirement
**Scope:** Phase 5 inclusion assessment

---

## Executive Summary

The requirement to support 10,000 daily customer users with enterprise-class auto-scaling introduces significant new work items that must be evaluated for inclusion in Phase 5. This document assesses each work item across cost, technical risk, maintenance impact, security, observability, and operational concerns.

**Recommendation:** Include auto-scaling implementation in Phase 5 scope with Azure Container Apps (Option 1) as the recommended approach. The work is achievable within the Phase 5 timeline with moderate budget impact.

---

## Work Item Inventory

### WI-1: Infrastructure Migration to Azure Container Apps

| Attribute | Assessment |
|-----------|------------|
| **Description** | Migrate from Azure Container Instances to Azure Container Apps for native auto-scaling |
| **Effort** | 16-24 hours |
| **Complexity** | Medium-High |
| **Dependencies** | WI-3, WI-5 |

#### Cost Impact

| Scenario | Current (ACI) | Container Apps | Delta |
|----------|---------------|----------------|-------|
| **Off-Peak** (nights/weekends) | $180-200/month | $80-130/month | **-$50 to -$120** |
| **Normal Load** (business hours) | $200-220/month | $230-350/month | **+$30 to +$130** |
| **Peak Load** (10K users) | N/A (can't scale) | $350-600/month | **+$150 to +$400** |
| **Average Monthly** | ~$200/month | ~$250-400/month | **+$50 to +$200** |

**Budget Analysis:**
- Current Phase 5 budget: $310-360/month
- Auto-scaling adds: $50-200/month (average)
- New budget requirement: $360-560/month at peak
- **Recommendation:** Increase budget ceiling to $500/month for elastic capacity, with expected average of $350-400/month

#### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Container Apps service limits** | Low | Medium | Pre-validate quotas, request increases if needed |
| **SLIM gRPC incompatibility** | Medium | High | Test SLIM container in ACA environment early |
| **Revision management complexity** | Medium | Low | Use single revision mode initially |
| **Cold start latency** | Medium | Medium | Set minReplicas=1 for critical paths |
| **Network policy differences** | Low | Medium | Document ACA networking vs ACI |

#### Maintenance Impact

| Area | Current (ACI) | With Container Apps |
|------|---------------|---------------------|
| **Deployment** | Direct `az container` commands | Terraform + revision management |
| **Monitoring** | Basic container metrics | Enhanced KEDA metrics + scaling events |
| **Debugging** | Simple container logs | Log Analytics + Container App Console |
| **Updates** | Manual image updates | Blue-green revision deployments |
| **Learning Curve** | Low | Medium (new concepts: revisions, scaling rules) |

---

### WI-2: Connection Pooling Implementation

| Attribute | Assessment |
|-----------|------------|
| **Description** | Implement connection pooling for Azure OpenAI, Cosmos DB, and external APIs |
| **Effort** | 8-12 hours |
| **Complexity** | Medium |
| **Dependencies** | None (can start immediately) |

#### Cost Impact

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| **Azure OpenAI** | Sequential calls, blocking | Parallel with pool | -10-20% token costs |
| **Cosmos DB** | Per-request connections | Pooled connections | -15-30% RU consumption |
| **External APIs** | Individual connections | Shared pools | Reduced connection overhead |
| **Net Monthly Savings** | - | - | **$15-40/month** |

#### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Connection leaks** | Medium | High | Implement proper context managers, add monitoring |
| **Pool exhaustion** | Low | High | Configure max_connections appropriately, add alerts |
| **Timeout handling** | Medium | Medium | Implement circuit breakers with configurable timeouts |
| **State management in pool** | Low | Medium | Ensure stateless client usage |

#### Security Implications

| Concern | Assessment | Mitigation |
|---------|------------|------------|
| **Credential reuse** | Pool shares API keys across connections | API keys already shared; no change |
| **Connection hijacking** | Pool could be targeted | Use TLS 1.3, private endpoints |
| **Memory exposure** | Credentials in memory longer | Clear credentials on shutdown |

---

### WI-3: Horizontal Pod Autoscaler / KEDA Configuration

| Attribute | Assessment |
|-----------|------------|
| **Description** | Configure auto-scaling rules for each agent type based on HTTP requests, CPU, and queue depth |
| **Effort** | 6-10 hours |
| **Complexity** | Medium |
| **Dependencies** | WI-1 |

#### Scaling Rules by Agent

| Agent | Trigger | Scale Range | Rationale |
|-------|---------|-------------|-----------|
| **API Gateway** | HTTP concurrent requests >10 | 0-10 | Entry point, must scale with traffic |
| **SLIM Gateway** | CPU >70% | 1-5 | Stateful gRPC, needs baseline |
| **Intent Classifier** | HTTP requests | 0-5 | Fast, stateless classification |
| **Critic/Supervisor** | HTTP requests | 0-5 | Must match Intent scaling |
| **Response Generator** | CPU >70% + HTTP | 0-8 | Most resource-intensive |
| **Escalation** | HTTP requests | 0-3 | Lower volume, fewer instances |
| **Knowledge Retrieval** | HTTP requests | 0-3 | Depends on RAG queries |
| **Analytics** | Queue depth | 0-2 | Batch processing, lower priority |

#### Cost Impact

Scaling rules directly control cost. Configuration choices:

| Approach | Monthly Cost | Responsiveness | Risk |
|----------|--------------|----------------|------|
| **Aggressive (fast scale-up)** | $400-600 | High | Over-provisioning |
| **Balanced (moderate)** | $300-450 | Medium | Occasional lag |
| **Conservative (slow scale-up)** | $200-350 | Low | User-facing delays |

**Recommendation:** Balanced approach with 5-minute scale-down cooldown

#### Observability Requirements

New metrics to monitor:
- `keda_scaler_active` - Scaling rule activation
- `container_app_replica_count` - Instance counts
- `container_app_requests_total` - Request volume
- `container_app_scale_events` - Scale up/down events

---

### WI-4: Load Balancing Configuration

| Attribute | Assessment |
|-----------|------------|
| **Description** | Configure Envoy-based load balancing in Container Apps |
| **Effort** | 2-4 hours |
| **Complexity** | Low |
| **Dependencies** | WI-1 |

#### Configuration Options

| Algorithm | Use Case | Recommendation |
|-----------|----------|----------------|
| **Round Robin** | Even distribution | Default, suitable for most agents |
| **Least Connections** | Long-running requests | Good for Response Generator |
| **Random** | Simple, low overhead | Not recommended |

#### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Sticky sessions needed** | Low | Medium | Use session affinity if stateful |
| **Health check misconfiguration** | Medium | High | Test health endpoints thoroughly |
| **Uneven distribution** | Low | Low | Monitor with metrics |

---

### WI-5: Scheduled Scaling Profiles

| Attribute | Assessment |
|-----------|------------|
| **Description** | Configure time-based scaling profiles for business hours, off-peak, and weekends |
| **Effort** | 4-6 hours |
| **Complexity** | Low-Medium |
| **Dependencies** | WI-1, WI-3 |

#### Profile Schedule

| Profile | Days | Hours (ET) | Min Replicas | Max Replicas | Cost Impact |
|---------|------|------------|--------------|--------------|-------------|
| **Business** | Mon-Fri | 8AM-6PM | 4 | 16 | Full capacity |
| **Evening** | Mon-Fri | 6PM-11PM | 2 | 8 | ~50% reduction |
| **Night** | Mon-Fri | 11PM-7AM | 0-1 | 3 | ~80% reduction |
| **Weekend** | Sat-Sun | All day | 1 | 4 | ~75% reduction |

#### Cost Savings

| Without Scheduled Scaling | With Scheduled Scaling | Savings |
|---------------------------|------------------------|---------|
| $400-500/month (constant capacity) | $250-350/month | **$100-200/month** |

---

### WI-6: Resource Reclamation & Scale-to-Zero

| Attribute | Assessment |
|-----------|------------|
| **Description** | Configure automatic resource release when agents are idle |
| **Effort** | 4-6 hours |
| **Complexity** | Medium |
| **Dependencies** | WI-1, WI-3 |

#### Scale-to-Zero Eligibility

| Agent | Can Scale to Zero? | Rationale |
|-------|-------------------|-----------|
| **API Gateway** | Yes (with caution) | Cold start ~3-5s acceptable |
| **SLIM Gateway** | **No** | Requires baseline for gRPC |
| **Intent Classifier** | Yes | Stateless, fast restart |
| **Critic/Supervisor** | Yes | Stateless, fast restart |
| **Response Generator** | Yes (with caution) | Larger cold start ~5-10s |
| **Escalation** | Yes | Lower traffic |
| **Knowledge Retrieval** | Yes | Lower traffic |
| **Analytics** | Yes | Batch processing |

#### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Cold start latency** | High | Medium | Set minReplicas=1 for critical paths |
| **Request timeout during cold start** | Medium | High | Increase client timeout to 30s |
| **Memory state loss** | N/A | N/A | Agents are stateless |

---

### WI-7: Monitoring & Alerting Enhancement

| Attribute | Assessment |
|-----------|------------|
| **Description** | Add scaling-specific dashboards, alerts, and operational runbooks |
| **Effort** | 6-10 hours |
| **Complexity** | Medium |
| **Dependencies** | WI-1, WI-3 |

#### New Dashboards Required

| Dashboard | Purpose | Metrics |
|-----------|---------|---------|
| **Scaling Overview** | Real-time instance counts | Replica counts, scale events |
| **Capacity Planning** | Trend analysis | Historical load, projections |
| **Cost Attribution** | Resource cost tracking | vCPU-hours, memory-hours |
| **Azure OpenAI Quotas** | TPM usage monitoring | Tokens consumed, 429 errors |

#### New Alerts Required

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| **Scale-up failure** | Any failure | Critical | Page on-call |
| **Near max replicas** | >80% of max | Warning | Investigate capacity |
| **Sustained high latency** | P95 >30s for 5min | Warning | Check scaling rules |
| **Azure OpenAI rate limit** | >10 429s/min | Warning | Increase TPM quota |
| **Cold start spike** | >10 cold starts/min | Info | Review scale-to-zero settings |

#### Cost Impact

| Component | Monthly Cost |
|-----------|--------------|
| Log Analytics (additional metrics) | +$5-10 |
| Dashboard hosting | $0 (included) |
| Alert actions | +$2-5 |
| **Total** | **+$7-15/month** |

---

### WI-8: Operational Runbooks

| Attribute | Assessment |
|-----------|------------|
| **Description** | Create runbooks for scaling interventions, troubleshooting, and capacity planning |
| **Effort** | 8-12 hours |
| **Complexity** | Low (documentation) |
| **Dependencies** | WI-1 through WI-7 |

#### Runbooks Required

| Runbook | Purpose |
|---------|---------|
| **Scaling Emergency Response** | Manual scale-up during incidents |
| **Cold Start Troubleshooting** | Diagnose slow scaling |
| **Cost Optimization Review** | Weekly scaling efficiency check |
| **Capacity Planning** | Monthly projection updates |
| **Azure OpenAI Quota Management** | Request TPM increases |

---

## Security Assessment

### New Attack Surfaces

| Surface | Risk Level | Mitigation |
|---------|------------|------------|
| **Increased instance count** | Low | Each instance has same security posture |
| **Container Apps control plane** | Low | Azure-managed, SOC2 compliant |
| **KEDA metrics exposure** | Low | Internal only, no public exposure |
| **Connection pool credentials** | Medium | Same as current, in-memory only |

### Security Benefits

| Benefit | Description |
|---------|-------------|
| **Reduced blast radius** | Multiple instances isolate failures |
| **Faster incident response** | Can scale down compromised instances |
| **Better audit trail** | Scaling events logged |

### Security Work Items

| Item | Effort | Priority |
|------|--------|----------|
| **Review network policies for ACA** | 2 hours | High |
| **Validate managed identity propagation** | 2 hours | High |
| **Test secret rotation with multiple instances** | 4 hours | Medium |

---

## Observability Assessment

### Current State

- Application Insights with 50% sampling
- Basic container metrics (CPU, memory)
- Log Analytics with 30-day retention
- Manual dashboard updates

### Required Enhancements

| Enhancement | Effort | Priority | Cost |
|-------------|--------|----------|------|
| **Scaling event tracking** | 4 hours | High | +$5/month |
| **Replica count dashboards** | 2 hours | High | $0 |
| **Auto-scaling correlation** | 4 hours | Medium | $0 |
| **Cost attribution metrics** | 4 hours | Medium | +$5/month |
| **Cold start monitoring** | 2 hours | Medium | $0 |

### Observability Gaps After Implementation

| Gap | Risk | Mitigation |
|-----|------|------------|
| **Cross-instance tracing** | Medium | Ensure trace ID propagation |
| **Scaling decision visibility** | Low | Log KEDA decisions |
| **Cost forecasting** | Medium | Add budget projections |

---

## Total Cost Summary

### Implementation Cost (One-Time)

| Work Item | Effort (Hours) | Estimated Cost* |
|-----------|----------------|-----------------|
| WI-1: Infrastructure Migration | 16-24 | $800-1,200 |
| WI-2: Connection Pooling | 8-12 | $400-600 |
| WI-3: KEDA Configuration | 6-10 | $300-500 |
| WI-4: Load Balancing | 2-4 | $100-200 |
| WI-5: Scheduled Scaling | 4-6 | $200-300 |
| WI-6: Scale-to-Zero | 4-6 | $200-300 |
| WI-7: Monitoring Enhancement | 6-10 | $300-500 |
| WI-8: Operational Runbooks | 8-12 | $400-600 |
| **Total** | **54-84 hours** | **$2,700-4,200** |

*Assuming $50/hour development cost

### Ongoing Operational Cost

| Component | Current | After Auto-Scaling | Delta |
|-----------|---------|-------------------|-------|
| **Compute (average)** | $180-200 | $250-400 | +$70-200 |
| **Azure OpenAI (scaled)** | $48-62 | $80-150 | +$32-88 |
| **Monitoring** | $32-43 | $45-60 | +$13-17 |
| **Connection pooling** | N/A | -$15-40 (savings) | -$15-40 |
| **Total Monthly** | ~$260-305 | ~$360-570 | **+$100-265** |

### Budget Recommendation

| Budget Category | Current | Proposed |
|-----------------|---------|----------|
| **Base Infrastructure** | $310-360/month | $400-450/month |
| **Elastic Burst (peak)** | N/A | +$100-150/month |
| **Total Ceiling** | $360/month | **$600/month** |
| **Expected Average** | ~$260/month | **~$400/month** |

---

## Risk Summary

### High-Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **SLIM gRPC incompatibility with ACA** | Medium | High | POC in first week |
| **Cold start affecting user experience** | Medium | Medium | minReplicas=1 for critical paths |
| **Budget overrun during peak** | Medium | Medium | Cost alerts, scaling caps |

### Medium-Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Connection pool exhaustion** | Low | High | Monitoring, alerts, circuit breakers |
| **Scaling too aggressive** | Medium | Low | Conservative initial settings |
| **Operational complexity increase** | Medium | Medium | Runbooks, training |

### Low-Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Azure Container Apps service issues** | Low | Medium | Multi-region DR plan |
| **KEDA configuration errors** | Low | Low | Terraform validation |

---

## Phase 5 Inclusion Recommendation

### Recommended Scope

Include in Phase 5:
- ✅ WI-1: Infrastructure Migration to Container Apps
- ✅ WI-2: Connection Pooling Implementation
- ✅ WI-3: KEDA Configuration (basic scaling rules)
- ✅ WI-4: Load Balancing Configuration
- ✅ WI-5: Scheduled Scaling Profiles
- ✅ WI-7: Monitoring Enhancement (core dashboards)
- ✅ WI-8: Operational Runbooks (critical paths)

Defer to Post-Phase 5:
- ⏳ WI-6: Full Scale-to-Zero (start with minReplicas=1)
- ⏳ Advanced cost attribution dashboards
- ⏳ Fine-tuned scaling algorithms

### Implementation Timeline

| Week | Work Items | Deliverables |
|------|------------|--------------|
| **Week 1** | WI-1 (POC), WI-2 | Container Apps POC, Connection pooling code |
| **Week 2** | WI-1 (migration), WI-3 | Full migration, Basic scaling rules |
| **Week 3** | WI-4, WI-5, WI-7 | Load balancing, Schedules, Dashboards |
| **Week 4** | WI-8, Testing | Runbooks, Load testing at scale |

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Peak capacity** | 16+ instances | Load test with 50 concurrent users |
| **Scale-up time** | <2 minutes | From trigger to ready |
| **Scale-down efficiency** | 80% reduction off-peak | Cost monitoring |
| **Cold start latency** | <10 seconds | Application Insights |
| **Cost within budget** | <$500/month average | Azure Cost Management |

---

## Final Assessment

### Pros of Including in Phase 5

1. **Enterprise readiness** - 10K users is mandatory requirement
2. **Cost optimization potential** - Scale-to-zero saves money during off-peak
3. **Operational maturity** - Demonstrates production-ready architecture
4. **Educational value** - Blog readers benefit from auto-scaling patterns

### Cons of Including in Phase 5

1. **Increased complexity** - More moving parts to manage
2. **Budget increase** - $100-265/month additional cost on average
3. **Timeline pressure** - 54-84 hours of additional work
4. **Technical risk** - Migration introduces potential issues

### Verdict

**PROCEED WITH PHASE 5 IMPLEMENTATION**

The auto-scaling requirement is mandatory and foundational for enterprise use. The implementation complexity is manageable within the Phase 5 timeline, and the cost increase is justified by the business requirement.

**Key Mitigations:**
1. Start with POC in Week 1 to validate SLIM compatibility
2. Use conservative scaling settings initially
3. Set budget alerts at $400 and $500 thresholds
4. Document thoroughly for educational value

---

**Document Version:** 1.0
**Author:** AGNTCY Development Team
**Review Required:** Project Stakeholder
