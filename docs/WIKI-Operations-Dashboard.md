# Operations Dashboard Guide

This guide explains how to use the AGNTCY Operations Dashboard to monitor the multi-agent customer service platform.

## Overview

The Operations Dashboard provides real-time visibility into:
- **Agent Performance**: Response times, success rates, and request distribution
- **LLM Costs**: Token usage, cost per provider, and budget tracking
- **Error Monitoring**: Error rates, top exceptions, and failure patterns
- **Multi-Channel Activity**: Widget, WhatsApp, and API usage metrics
- **System Health**: Dependency status and request volumes

## Accessing the Dashboard

### Azure Portal
1. Navigate to **Azure Portal** → **Monitor** → **Workbooks**
2. Select **AGNTCY - Operations Dashboard**

### Direct Link
After deployment, the dashboard is available at:
```
https://portal.azure.com/#@{tenant}/resource/{app-insights-id}/workbooks
```

## Dashboard Sections

### 1. Time Range Selection

At the top of the dashboard, select the time range for analysis:
- **Last 5 minutes**: Real-time troubleshooting
- **Last hour**: Default operational view
- **Last 24 hours**: Daily review
- **Last 7 days**: Weekly trends

### 2. Key Metrics Tiles

Quick overview metrics showing:

| Metric | Description | Good Value |
|--------|-------------|------------|
| Total Requests | Request count in period | N/A |
| Success Rate | Percentage of 2xx responses | >99% |
| Failed Requests | Count of 4xx/5xx responses | <1% of total |
| Avg Response | Mean response time | <2 seconds |

### 3. Agent Performance

#### Request Distribution (Pie Chart)
Shows which agents handle the most traffic:
- **Intent Classifier**: Should be ~100% of incoming requests
- **Response Generator**: Varies based on automation rate
- **Escalation Handler**: Should be <30% (target automation)

#### Response Times Table
| Agent | Target Avg | Target P95 |
|-------|------------|------------|
| Intent Classifier | <100ms | <500ms |
| Knowledge Retrieval | <200ms | <800ms |
| Response Generator | <3s | <5s |
| Critic/Supervisor | <100ms | <200ms |

#### Performance Over Time
- Look for **spikes**: May indicate load issues
- Look for **gradual increases**: May indicate degradation
- **Flat lines at zero**: Agent not receiving requests

### 4. LLM Provider Metrics

#### Token Usage by Model
Track token consumption to predict costs:

| Model | Typical Usage |
|-------|---------------|
| gpt-4o-mini | High volume (intent, validation) |
| gpt-4o | Lower volume (response generation) |
| text-embedding-3-large | Varies with knowledge queries |

#### Cost by Provider
- **Azure OpenAI**: Primary provider (should be highest)
- **Anthropic**: Fallback only (should be minimal)
- **Mock**: Development only (should be $0)

#### Budget Monitoring
- **Daily budget target**: ~$2/day ($60/month)
- **Warning threshold**: $4/day
- **Critical threshold**: $5/day

### 5. Error Tracking

#### Error Rate Chart
- **Normal**: <1% error rate
- **Warning**: 1-5% error rate
- **Critical**: >5% error rate

Common error patterns:
- **Spikes**: Sudden issues (deployment, external service)
- **Gradual increase**: Degradation, resource exhaustion
- **Periodic spikes**: Scheduled jobs, traffic patterns

#### Top Errors Table
Review most frequent exceptions:
- **Connection errors**: Network issues, service outages
- **Timeout errors**: Performance issues, overload
- **Validation errors**: Bad input data, schema changes

### 6. System Health

#### Dependency Health
Monitor external service reliability:

| Service | Expected Success Rate |
|---------|----------------------|
| Azure OpenAI | >99.5% |
| Cosmos DB | >99.9% |
| Shopify API | >99% |
| WhatsApp API | >99% |

#### Request Volume
- **Business hours**: Expect higher volume
- **Off-peak**: Should see reduced traffic
- **Sudden drops**: May indicate issues

### 7. Multi-Channel Activity

#### Channel Distribution
Track how customers interact:
- **Web Widget**: Primary channel for website visitors
- **WhatsApp**: Mobile and messaging users
- **API**: Developer/integration usage

#### Sessions
- **New sessions**: Customer acquisition
- **Active sessions**: Current engagement
- **Session duration**: User experience quality

## Alert Reference

The dashboard includes automated alerts:

| Alert | Condition | Action |
|-------|-----------|--------|
| Intent Slow | P95 > 500ms | Check Azure OpenAI latency |
| Response Slow | P95 > 5s | Check model performance |
| High Block Rate | >10% blocked | Review Critic rules |
| Cost Spike | >$5/day | Check for abuse/bugs |
| Token Anomaly | >100K tokens/hr | Investigate high usage |
| Provider Fallback | >5 fallbacks | Check primary provider |
| WhatsApp Failures | >3 errors | Check webhook config |
| Widget Errors | >5% error rate | Review widget logs |
| Session Expiry | >50% expiry | Check connectivity |
| High Escalation | >30% escalated | Review model accuracy |

## Troubleshooting with the Dashboard

### Scenario: Slow Response Times

1. Check **Agent Performance** section for which agent is slow
2. Look at **Dependency Health** for external service issues
3. Review **LLM Provider Metrics** for model latency
4. Check **Error Rate** for timeout patterns

### Scenario: High Error Rate

1. Check **Top Errors** table for error types
2. Review **Dependency Health** for failing services
3. Look at **Request Volume** for traffic patterns
4. Check alert history for recent issues

### Scenario: Cost Spike

1. Check **Cost by Provider** for unusual providers
2. Review **Token Usage by Model** for high consumption
3. Look at **Cost Over Time** for when spike started
4. Check **Request Volume** for traffic increase

### Scenario: Channel Issues

1. Check **Multi-Channel Activity** for affected channel
2. Review channel-specific alerts (WhatsApp/Widget)
3. Look at **Dependency Health** for service status
4. Check **Error Rate** filtered by channel

## Custom Queries

For advanced analysis, use Log Analytics with these queries:

### Find Slow Requests
```kql
requests
| where duration > 5000
| project timestamp, name, duration, resultCode
| order by duration desc
| take 100
```

### Track Specific Agent
```kql
requests
| where name contains "intent"
| summarize
    count(),
    avg(duration),
    percentile(duration, 95)
    by bin(timestamp, 5m)
| render timechart
```

### Cost Analysis by Hour
```kql
customMetrics
| where name == "estimated_cost"
| summarize HourlyCost = sum(value) by bin(timestamp, 1h)
| render timechart
```

## Best Practices

1. **Daily Review**: Check dashboard at start of business day
2. **Alert Response**: Investigate alerts within 15 minutes
3. **Weekly Analysis**: Review 7-day trends for optimization
4. **Cost Monitoring**: Track daily costs against budget
5. **Incident Documentation**: Record findings for post-mortems

## Support

For dashboard issues:
- Check [Troubleshooting Guide](RUNBOOK-AUTO-SCALING-OPERATIONS.md)
- Review [Implementation Summary](ISSUE-169-IMPLEMENTATION-SUMMARY.md)
- Contact operations team via configured action group
