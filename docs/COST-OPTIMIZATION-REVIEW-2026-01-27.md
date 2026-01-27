# Cost Optimization Review

**Date:** 2026-01-27
**Budget:** $310-360/month
**Target:** $200-250/month post-Phase 5

## Current Resource Inventory

### Container Instances (8 containers)

| Container | CPU | Memory | Estimated Cost/Month |
|-----------|-----|--------|---------------------|
| SLIM Gateway | 0.5 | 1 GB | ~$8-10 |
| NATS JetStream | 0.5 | 1 GB | ~$8-10 |
| Intent Classifier | 0.5 | 1 GB | ~$8-10 |
| Knowledge Retrieval | 0.5 | 1 GB | ~$8-10 |
| Response Generator | 0.5 | 1.5 GB | ~$10-12 |
| Escalation | 0.5 | 1 GB | ~$8-10 |
| Analytics | 0.5 | 1 GB | ~$8-10 |
| Critic/Supervisor | 0.5 | 1 GB | ~$8-10 |
| **Subtotal** | 4 vCPU | 9 GB | **~$66-82** |

### Data Services

| Service | SKU | Estimated Cost/Month |
|---------|-----|---------------------|
| Cosmos DB | Serverless | ~$10-30 (usage dependent) |
| Container Registry | Basic | ~$5 |
| Key Vault | Standard | ~$1-3 |
| Blob Storage (knowledge base) | Standard | ~$1 |
| **Subtotal** | | **~$17-39** |

### Networking

| Service | SKU | Estimated Cost/Month |
|---------|-----|---------------------|
| Application Gateway | Standard_v2 (0-2 instances) | ~$15-25 |
| Public IP | Standard | ~$3 |
| VNet | Free | $0 |
| Private Endpoints (2) | ~$0.01/hr each | ~$15 |
| Private DNS Zones | ~$0.50/zone | ~$1 |
| **Subtotal** | | **~$34-44** |

### Observability

| Service | SKU | Estimated Cost/Month |
|---------|-----|---------------------|
| Log Analytics | PerGB2018 | ~$10-20 |
| Application Insights | Pay-per-GB | ~$5-10 |
| Alert Rules | Basic | ~$0.10/rule (~$0.50) |
| **Subtotal** | | **~$15-31** |

### AI Services (Azure OpenAI)

| Model | Usage (tokens/month) | Cost/Month |
|-------|---------------------|-----------|
| GPT-4o-mini (intent, critic) | ~10M tokens | ~$1.50 |
| GPT-4o (response) | ~5M tokens | ~$12.50 |
| text-embedding-3-large | ~2M tokens | ~$0.26 |
| **Subtotal** | | **~$14-20** |

*Note: AI costs will scale with usage. Current estimates are for light/testing load.*

## Total Estimated Monthly Cost

| Category | Min | Max |
|----------|-----|-----|
| Container Instances | $66 | $82 |
| Data Services | $17 | $39 |
| Networking | $34 | $44 |
| Observability | $15 | $31 |
| AI Services | $14 | $20 |
| **TOTAL** | **$146** | **$216** |

✅ **Well under $310-360 budget**

## Cost Optimization Opportunities

### 1. Implemented Optimizations ✅

| Optimization | Savings | Status |
|--------------|---------|--------|
| Cosmos DB Serverless (vs. provisioned) | ~$50-70/mo | ✅ Implemented |
| Basic ACR (vs. Standard) | ~$15/mo | ✅ Implemented |
| 7-day log retention (vs. 30-day) | ~$10-15/mo | ✅ Implemented |
| GPT-4o-mini for intent/critic (vs. GPT-4o) | ~$20-30/mo | ✅ Implemented |
| Private DNS zones (vs. Azure DNS) | ~$5/mo | ✅ Implemented |
| Single region (vs. geo-redundant) | ~$100+/mo | ✅ Implemented |

### 2. Future Optimizations (Post-Phase 5)

| Optimization | Potential Savings | Priority |
|--------------|-------------------|----------|
| Auto-shutdown during off-peak (2am-6am) | ~$10-15/mo | High |
| Reduce container instances during idle | ~$20-30/mo | High |
| Response caching (reduce AI calls) | ~$5-10/mo | Medium |
| Consolidate SLIM + NATS container | ~$8-10/mo | Medium |
| Fine-tuned models (reduce tokens) | ~$5-10/mo | Low |

### 3. Scaling Recommendations

**Low Traffic (< 100 conversations/day):**
- Current configuration is optimal
- Estimated cost: $150-200/mo

**Medium Traffic (100-1000 conversations/day):**
- May need to scale response-generator to 2 instances
- Add Redis cache for customer profiles
- Estimated cost: $200-280/mo

**High Traffic (> 1000 conversations/day):**
- Scale all agents to 2-3 instances
- Add Redis cache cluster
- Consider reserved capacity for Cosmos DB
- Estimated cost: $280-360/mo

## Cost Alerts Configured

| Alert | Threshold | Action |
|-------|-----------|--------|
| Warning | $299 (83%) | Email notification |
| Critical | $335 (93%) | Email + SMS |
| Forecast | $360 (100%) | Auto-scale down |

## Weekly Cost Review Checklist

- [ ] Check Azure Cost Management for actual spend
- [ ] Review container CPU/memory utilization
- [ ] Check AI token usage in Azure OpenAI portal
- [ ] Verify log analytics data ingestion volume
- [ ] Review Application Gateway scaling metrics

## Recommendations

### Immediate Actions (No Cost)
1. ✅ Application Gateway autoscale 0-2 (scale to zero when idle)
2. ⏳ Configure off-peak shutdown (2am-6am ET)
3. ⏳ Set up monthly cost review calendar reminder

### Short-term (Next 30 days)
1. Monitor actual usage to refine estimates
2. Set up Azure Budget alerts in Azure Portal
3. Review container right-sizing based on actual metrics

### Long-term (Post-Phase 5)
1. Implement response caching to reduce AI API calls
2. Consolidate SLIM and NATS into single container group
3. Consider Azure Reserved Instances if traffic stabilizes

## Summary

| Metric | Value |
|--------|-------|
| Current Estimated Cost | $146-216/month |
| Budget | $310-360/month |
| Budget Utilization | 47-60% |
| Post-Phase 5 Target | $200-250/month |
| Status | ✅ On Track |

The platform is currently operating well within budget constraints. The cost-optimization strategies implemented in Phase 4 (serverless Cosmos, Basic ACR, GPT-4o-mini routing) are delivering significant savings compared to standard configurations.

---

**Reviewed By:** Claude Code
**Next Review:** 2026-02-03 (Weekly)
