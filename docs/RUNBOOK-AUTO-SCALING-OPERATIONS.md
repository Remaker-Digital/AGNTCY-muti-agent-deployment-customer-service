# Operational Runbook: Auto-Scaling Operations

**Document Version:** 1.0
**Created:** 2026-01-27
**Last Updated:** 2026-01-27
**Owner:** Operations Team

---

## Purpose

This runbook provides procedures for operating and troubleshooting the auto-scaling infrastructure supporting 10,000 daily users on Azure Container Apps.

---

## Quick Reference

### Key Metrics

| Metric | Normal Range | Warning | Critical |
|--------|--------------|---------|----------|
| Replica Count (API Gateway) | 1-5 | 6-8 | >8 |
| Response Time P95 | <15s | 15-30s | >30s |
| Error Rate | <1% | 1-5% | >5% |
| Azure OpenAI 429s | 0/min | 1-5/min | >10/min |
| Monthly Cost | <$400 | $400-500 | >$500 |

### Emergency Contacts

| Role | Contact |
|------|---------|
| On-Call Engineer | Configured in Azure Action Group |
| Azure Support | Azure Portal > Help + Support |

---

## Runbook 1: Scale-Up Emergency Response

### When to Use
- Response time consistently >30s
- Error rate >5%
- Near maximum replicas alert triggered

### Procedure

1. **Verify the Issue**
   ```bash
   # Check current replica counts
   az containerapp list -g agntcy-prod-rg -o table

   # Check recent scaling events
   az monitor activity-log list \
     --resource-group agntcy-prod-rg \
     --start-time $(date -d '1 hour ago' -Iseconds) \
     --query "[?contains(operationName.value, 'scale')]"
   ```

2. **Manual Scale-Up (if auto-scaling is delayed)**
   ```bash
   # Increase API Gateway replicas
   az containerapp update \
     --name agntcy-cs-prod-api-gateway \
     --resource-group agntcy-prod-rg \
     --min-replicas 5 \
     --max-replicas 15

   # Increase Response Generator (most resource-intensive)
   az containerapp update \
     --name agntcy-cs-prod-response \
     --resource-group agntcy-prod-rg \
     --min-replicas 3 \
     --max-replicas 12
   ```

3. **Monitor Recovery**
   ```bash
   # Watch replica count and response time
   az containerapp logs show \
     --name agntcy-cs-prod-api-gateway \
     --resource-group agntcy-prod-rg \
     --tail 50
   ```

4. **Post-Incident**
   - Document the event in incident log
   - Review if permanent scaling adjustment needed
   - Consider Azure OpenAI TPM quota increase

### Rollback
```bash
# Return to normal scaling settings
az containerapp update \
  --name agntcy-cs-prod-api-gateway \
  --resource-group agntcy-prod-rg \
  --min-replicas 1 \
  --max-replicas 10
```

---

## Runbook 2: Cold Start Troubleshooting

### When to Use
- Users report slow initial responses
- Frequent cold start alerts
- Scale-to-zero is causing issues

### Symptoms
- First request after idle period takes >10s
- Sporadic timeout errors
- Log shows container initialization messages

### Procedure

1. **Check Current State**
   ```bash
   # List all container apps and their replica counts
   az containerapp list -g agntcy-prod-rg \
     --query "[].{name:name, replicas:properties.template.scale.minReplicas}" -o table
   ```

2. **Increase Minimum Replicas (Prevent Cold Starts)**
   ```bash
   # Set minimum replicas to 1 for critical path
   az containerapp update \
     --name agntcy-cs-prod-intent \
     --resource-group agntcy-prod-rg \
     --min-replicas 1

   az containerapp update \
     --name agntcy-cs-prod-critic \
     --resource-group agntcy-prod-rg \
     --min-replicas 1
   ```

3. **Verify Readiness Probes**
   ```bash
   # Check probe configuration
   az containerapp show \
     --name agntcy-cs-prod-api-gateway \
     --resource-group agntcy-prod-rg \
     --query "properties.template.containers[0].probes"
   ```

### Cost Impact
- Each additional always-on replica: ~$15-30/month
- Trade-off: Latency vs cost

---

## Runbook 3: Azure OpenAI Rate Limiting Response

### When to Use
- Throttling alert triggered (>10 429s/min)
- Response times spiking
- "Rate limit exceeded" errors in logs

### Procedure

1. **Verify Rate Limiting**
   ```bash
   # Check Application Insights for 429 errors
   az monitor app-insights query \
     --app agntcy-cs-prod-appinsights-rc6vcp \
     --analytics-query "requests | where resultCode == '429' | summarize count() by bin(timestamp, 1m)" \
     --offset 1h
   ```

2. **Immediate Mitigation**
   - Connection pool will automatically back off
   - Circuit breaker may trip (check pool health endpoint)

3. **Request TPM Increase**
   - Navigate to Azure Portal > Azure OpenAI > Quotas
   - Request increase for affected deployments
   - Typical approval: 1-3 business days

4. **Temporary Workaround**
   ```bash
   # Reduce concurrent connections per instance
   # Edit environment variable and redeploy
   az containerapp update \
     --name agntcy-cs-prod-api-gateway \
     --resource-group agntcy-prod-rg \
     --set-env-vars "OPENAI_POOL_MAX_CONNECTIONS=30"
   ```

### Prevention
- Monitor daily token usage trends
- Request quota increase before peak periods
- Consider caching frequent responses

---

## Runbook 4: Cost Optimization Review

### When to Use
- Weekly cost review (every Monday)
- Budget warning alert triggered
- End of month cost analysis

### Procedure

1. **Check Current Spend**
   ```bash
   # Get cost breakdown
   az consumption usage list \
     --start-date $(date -d 'first day of this month' +%Y-%m-%d) \
     --end-date $(date +%Y-%m-%d) \
     --query "[?contains(instanceName, 'agntcy')].{name:instanceName, cost:pretaxCost}" \
     -o table
   ```

2. **Review Scaling Efficiency**
   ```bash
   # Check average replica count over past week
   az monitor metrics list \
     --resource $(az containerapp show -n agntcy-cs-prod-api-gateway -g agntcy-prod-rg --query id -o tsv) \
     --metric "Replicas" \
     --aggregation Average \
     --interval PT1H \
     --start-time $(date -d '7 days ago' -Iseconds)
   ```

3. **Optimization Actions**

   | Finding | Action |
   |---------|--------|
   | Replicas rarely >2 | Reduce max replicas |
   | Night replicas >0 | Verify scale-to-zero working |
   | Weekend same as weekday | Add scheduled scaling |
   | High Analytics replicas | Reduce Analytics max |

4. **Apply Scheduled Scaling (if not already configured)**
   ```bash
   # Business hours profile (higher capacity)
   # Note: Scheduled scaling requires Azure CLI extension
   az containerapp update \
     --name agntcy-cs-prod-api-gateway \
     --resource-group agntcy-prod-rg \
     --min-replicas 2 \
     --max-replicas 10

   # Off-peak profile (reduce costs)
   # Run at 8 PM ET
   az containerapp update \
     --name agntcy-cs-prod-api-gateway \
     --resource-group agntcy-prod-rg \
     --min-replicas 1 \
     --max-replicas 5
   ```

---

## Runbook 5: Capacity Planning

### When to Use
- Monthly capacity review
- Before expected traffic increase
- After significant architecture changes

### Procedure

1. **Gather Baseline Metrics**
   ```bash
   # Export last 30 days of metrics
   az monitor metrics list \
     --resource $(az containerapp show -n agntcy-cs-prod-api-gateway -g agntcy-prod-rg --query id -o tsv) \
     --metric "Requests" "RequestDuration" "Replicas" \
     --aggregation Total Average Maximum \
     --interval PT1D \
     --start-time $(date -d '30 days ago' -Iseconds) \
     -o json > capacity-metrics.json
   ```

2. **Calculate Capacity Utilization**

   | Metric | Formula | Target |
   |--------|---------|--------|
   | Peak Utilization | Peak Replicas / Max Replicas | <80% |
   | Average Utilization | Avg Replicas / Max Replicas | <50% |
   | Headroom | (Max - Peak) × Cost/Replica | Budget allowance |

3. **Adjust Limits if Needed**
   ```bash
   # Increase max replicas if utilization >80%
   az containerapp update \
     --name agntcy-cs-prod-api-gateway \
     --resource-group agntcy-prod-rg \
     --max-replicas 15
   ```

4. **Document Findings**
   - Update capacity planning spreadsheet
   - Log any limit changes
   - Schedule next review

---

## Runbook 6: Connection Pool Health Check

### When to Use
- Slow response times
- Connection errors in logs
- Circuit breaker trips

### Procedure

1. **Check Pool Health Endpoint**
   ```bash
   curl -k https://agntcy-cs-prod-rc6vcp.eastus2.cloudapp.azure.com/api/v1/status
   ```

   Expected healthy response:
   ```json
   {
     "azure_openai_pool": {
       "state": "ready",
       "available_connections": 5,
       "active_connections": 2,
       "circuit_breaker_open": false
     }
   }
   ```

2. **If Circuit Breaker is Open**
   - Check Azure OpenAI service status
   - Review recent error logs
   - Circuit breaker will auto-recover after 30s

3. **If Pool Exhausted (available=0)**
   ```bash
   # Increase pool size via environment variable
   az containerapp update \
     --name agntcy-cs-prod-api-gateway \
     --resource-group agntcy-prod-rg \
     --set-env-vars "OPENAI_POOL_MAX_CONNECTIONS=100"
   ```

4. **Monitor Pool Metrics**
   - `openai_pool_connections_active` - Current in-use
   - `openai_pool_acquire_time_ms` - Wait time for connection
   - `openai_pool_errors_total` - Connection errors

---

## Scheduled Tasks

### Daily
- [ ] Review error rate dashboard
- [ ] Check for throttling alerts

### Weekly
- [ ] Cost review (Runbook 4)
- [ ] Scaling efficiency check

### Monthly
- [ ] Capacity planning review (Runbook 5)
- [ ] Azure OpenAI quota review

### Quarterly
- [ ] Load test with peak traffic simulation
- [ ] Review and update scaling thresholds

---

## Troubleshooting Decision Tree

```
Issue: Slow Response Times
│
├─ Is error rate high (>5%)?
│   ├─ Yes → Check Azure OpenAI status, review logs
│   └─ No → Continue
│
├─ Are replicas at max?
│   ├─ Yes → Manual scale-up (Runbook 1)
│   └─ No → Continue
│
├─ Is this after idle period?
│   ├─ Yes → Cold start issue (Runbook 2)
│   └─ No → Continue
│
├─ Are 429 errors present?
│   ├─ Yes → Rate limiting (Runbook 3)
│   └─ No → Continue
│
└─ Check connection pool health (Runbook 6)
```

---

## Alert Response Matrix

| Alert | Severity | Initial Response | Escalation |
|-------|----------|------------------|------------|
| Near Max Replicas | Warning | Review and consider increase | If sustained >1hr |
| High Latency | Warning | Check scaling, pool health | If >30min |
| High Error Rate | Critical | Immediate investigation | Immediate |
| Budget Warning | Warning | Cost review | At 85% |
| OpenAI Throttling | Warning | Reduce load, request quota | If sustained |

---

## Appendix: Useful Commands

### Container Apps
```bash
# List all apps with replica counts
az containerapp list -g agntcy-prod-rg -o table

# View logs
az containerapp logs show -n <app-name> -g agntcy-prod-rg --tail 100

# Check revision status
az containerapp revision list -n <app-name> -g agntcy-prod-rg -o table

# Update scaling
az containerapp update -n <app-name> -g agntcy-prod-rg --min-replicas X --max-replicas Y
```

### Monitoring
```bash
# Query Application Insights
az monitor app-insights query --app <app-insights-name> --analytics-query "<KQL>"

# List recent alerts
az monitor alert list -g agntcy-prod-rg --query "[?status=='Fired']"
```

### Cost
```bash
# Get resource costs
az consumption usage list --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-27 | AGNTCY Team | Initial version |

---

**Next Review Date:** 2026-02-27
