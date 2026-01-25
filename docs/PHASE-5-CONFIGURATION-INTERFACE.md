# Phase 5: Configuration Interface & Operational Tuning

**Version**: 1.0
**Created**: January 25, 2026
**Phase**: Phase 5 Planning (Production Operations)
**Status**: Design Specification

---

## Executive Summary

**YES**, Phase 5 will require frequent configuration changes for operational tuning, A/B testing, and optimization. Based on the project's **educational blog post purpose** and **$200-250/month cost optimization target**, we recommend a **dual-interface approach**:

1. **Azure Portal + CLI** (Primary) - Free, built-in, sufficient for operations team
2. **Custom Admin Dashboard** (Optional, Phase 5 Week 4) - Enhanced UX, but adds $15-25/month cost

**Recommendation**: Start with Azure Portal/CLI (free), add custom dashboard only if operational complexity justifies the cost.

---

## Table of Contents

1. [Phase 5 Configuration Needs Analysis](#phase-5-configuration-needs-analysis)
2. [Configuration Change Frequency](#configuration-change-frequency)
3. [Recommended Dual-Interface Approach](#recommended-dual-interface-approach)
4. [Azure Portal Interface (Primary)](#azure-portal-interface-primary)
5. [Azure CLI Interface (Secondary)](#azure-cli-interface-secondary)
6. [Custom Admin Dashboard (Optional)](#custom-admin-dashboard-optional)
7. [Configuration Change Workflows](#configuration-change-workflows)
8. [Access Control & Audit](#access-control--audit)
9. [Cost Analysis](#cost-analysis)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Phase 5 Configuration Needs Analysis

### Configuration Changes During Phase 5

| Configuration Type | Change Frequency | Urgency | Complexity | Interface Needed |
|-------------------|------------------|---------|------------|------------------|
| **API Keys** | Quarterly (rotation) | High | Low | Azure Portal + Key Vault |
| **Throttling Limits** | Weekly (optimization) | Medium | Medium | Azure App Config |
| **PII Tokenization** | Rare (enable/disable) | High | Low | Azure App Config (feature flag) |
| **Confidence Thresholds** | Daily (tuning) | Medium | Medium | Azure App Config |
| **Escalation Thresholds** | Daily (tuning) | Medium | Medium | Azure App Config |
| **LLM Prompts** | Daily (prompt eng) | Low | High | Git + CI/CD |
| **RAG Configuration** | Weekly (tuning) | Medium | Medium | Azure App Config + Git |
| **Feature Flags** | Daily (A/B testing) | Medium | Low | Azure App Config |
| **Budget Alerts** | Rare (threshold change) | Medium | Low | Azure Portal |
| **Auto-Scaling Rules** | Weekly (cost optimization) | Medium | Medium | Terraform + Azure Portal |

### Key Insights

1. **Most Changes → Azure App Configuration**: 70% of operational tuning
2. **Secrets → Azure Key Vault**: 10% (quarterly rotation)
3. **Complex Behavior → Git + CI/CD**: 15% (prompt engineering)
4. **Infrastructure → Terraform/Portal**: 5% (rare)

**Conclusion**: Azure App Configuration is the primary operational interface.

---

## Configuration Change Frequency

### Daily Changes (High Frequency)

**Confidence Thresholds**:
```yaml
# Scenario: Intent classification confidence too low, too many escalations
# Current: 0.7 threshold → 70% of intents escalate
# New: 0.5 threshold → reduce escalations to 30%

Before: intent:confidence_threshold = 0.7
After:  intent:confidence_threshold = 0.5
```

**Escalation Thresholds**:
```yaml
# Scenario: Too many tickets created for minor issues
# Current: sentiment_score < -0.5 → escalate
# New: sentiment_score < -0.7 → escalate (only very negative)

Before: escalation:sentiment_threshold = -0.5
After:  escalation:sentiment_threshold = -0.7
```

**LLM Prompts** (via Git):
```yaml
# Scenario: GPT-4o too verbose, increasing costs
# Current: "Provide a detailed response..."
# New: "Provide a concise response..."

# Edit: agents/response_generation/config.yaml
# Commit → PR → Merge → CI/CD → Deploy
```

**Feature Flags** (A/B Testing):
```yaml
# Scenario: Test RAG pipeline with 10% of users
# Enable for 10% → monitor metrics → gradual rollout

rag_enabled:
  enabled: true
  targeting: 10%  # Canary release
```

---

### Weekly Changes (Medium Frequency)

**Throttling Limits**:
```yaml
# Scenario: Azure OpenAI rate limiting causing 429 errors
# Current: 60 req/min → hitting limit during peak hours
# New: Implement queuing, reduce burst to 50 req/min

Before: throttle:openai_requests_per_minute = 60
After:  throttle:openai_requests_per_minute = 50
        throttle:queue_enabled = true
        throttle:queue_max_size = 100
```

**RAG Configuration**:
```yaml
# Scenario: Vector search recall too low (50%) → increase top_k
# Current: top_k = 3 (3 most similar documents)
# New: top_k = 5 (5 most similar documents)

Before: rag:top_k = 3
        rag:similarity_threshold = 0.8
After:  rag:top_k = 5
        rag:similarity_threshold = 0.75  # Slightly lower threshold
```

**Auto-Scaling Rules**:
```yaml
# Scenario: Cost optimization - scale down during off-peak
# Current: min_instances = 1, max_instances = 10
# New: min_instances = 1 (no change), max_instances = 5 (reduce cost)

# Update via Azure Portal or Terraform
```

---

### Quarterly Changes (Low Frequency)

**API Key Rotation**:
```bash
# Scenario: Security policy requires quarterly rotation
# Current: shopify-api-token = "shpat_old123"
# New: shopify-api-token = "shpat_new456"

# Azure Key Vault → Create new version
# Agents auto-pick up new version within 5 minutes
```

**Budget Adjustments**:
```yaml
# Scenario: Cost optimization successful, reduce budget alerts
# Current: Budget = $360/month, alerts at 83% ($299), 93% ($335)
# New: Budget = $250/month, alerts at 80% ($200), 90% ($225)

# Update via Azure Portal → Cost Management → Budgets
```

---

## Recommended Dual-Interface Approach

### Primary Interface: Azure Portal + CLI (Free)

**Rationale**:
- ✅ **Free** (no additional cost)
- ✅ **Built-in** (no development effort)
- ✅ **Azure-native** (familiar to DevOps teams)
- ✅ **RBAC integrated** (Azure AD authentication)
- ✅ **Audit logs** (Azure Monitor Activity Log)
- ✅ **Sufficient for operations team** (small team, 2-3 operators)

**Use Cases**:
- Updating App Configuration settings (90% of changes)
- Rotating Key Vault secrets (10% of changes)
- Viewing dashboards (Application Insights, Cost Management)

---

### Secondary Interface: Azure CLI (Scripting)

**Rationale**:
- ✅ **Free** (no additional cost)
- ✅ **Scriptable** (automation, batch updates)
- ✅ **CI/CD integration** (Azure DevOps pipelines)
- ✅ **Repeatable** (versioned scripts in Git)

**Use Cases**:
- Bulk configuration updates (e.g., update all throttling limits)
- Disaster recovery (restore configuration from backup)
- Environment promotion (dev → staging → prod)

---

### Optional Interface: Custom Admin Dashboard (Week 4)

**Rationale**:
- ⚠️ **Costs $15-25/month** (Azure App Service or Container Instance)
- ⚠️ **Development effort** (~20-30 hours)
- ✅ **Better UX** (business users, non-technical stakeholders)
- ✅ **Integrated view** (all configurations in one place)
- ✅ **Educational value** (demonstrates full-stack AI app)

**Use Cases**:
- Business stakeholders reviewing/approving configuration changes
- A/B test management (enable/disable flags, view metrics)
- Cost dashboards (real-time spend vs budget)

**Decision Criteria**: Add custom dashboard if:
1. ✅ Operations team struggles with Azure Portal UX
2. ✅ Business stakeholders need self-service access
3. ✅ A/B testing becomes frequent (daily flags changes)
4. ✅ Blog post readers request it (educational value)

---

## Azure Portal Interface (Primary)

### 1. Azure App Configuration (Daily Operations)

**Access**: Azure Portal → App Configuration → appconfig-multi-agent

**Common Tasks**:

**Task 1: Update Confidence Threshold**
```
1. Navigate to: Configuration explorer
2. Filter by: Label = "production"
3. Find key: "intent:confidence_threshold"
4. Click "Edit"
5. Change value: 0.7 → 0.5
6. Click "Apply"
7. Result: Agents pick up new value within 30 seconds (no restart)
```

**Task 2: Enable/Disable Feature Flag**
```
1. Navigate to: Feature manager
2. Find flag: "rag_enabled"
3. Toggle: On → Off (or vice versa)
4. Click "Apply"
5. Result: RAG pipeline disabled for all users immediately
```

**Task 3: Gradual Rollout (A/B Testing)**
```
1. Navigate to: Feature manager
2. Find flag: "critic_supervisor_enabled"
3. Click "Edit"
4. Enable targeting:
   - Percentage: 10% (canary)
   - Groups: [] (empty, random sampling)
5. Click "Apply"
6. Monitor metrics in Application Insights
7. Gradually increase: 10% → 25% → 50% → 100%
```

**Screenshots** (for documentation):
```
┌─────────────────────────────────────────────────────────────────┐
│  Azure App Configuration - Configuration Explorer               │
├─────────────────────────────────────────────────────────────────┤
│  Filter by label: [production ▼]  [+ Create]                   │
│                                                                  │
│  Key                              Value      Label      Actions │
│  ─────────────────────────────────────────────────────────────  │
│  intent:confidence_threshold      0.7        production  [Edit] │
│  escalation:sentiment_threshold   -0.5       production  [Edit] │
│  rag:top_k                        3          production  [Edit] │
│  throttle:openai_rpm              60         production  [Edit] │
│  llm:temperature                  0.7        production  [Edit] │
│                                                                  │
│  Showing 5 of 23 items                               [1] [2] [>]│
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. Azure Key Vault (Secret Rotation)

**Access**: Azure Portal → Key Vault → kv-multi-agent

**Common Tasks**:

**Task 1: Rotate Shopify API Token**
```
1. Navigate to: Secrets
2. Find secret: "shopify-api-token"
3. Click "New Version"
4. Enter new token value
5. Click "Create"
6. Result: New version created, agents pick up within 5 minutes
7. Shopify: Revoke old token after confirming new one works
```

**Task 2: View Secret Access Audit Log**
```
1. Navigate to: Monitoring → Logs
2. Query:
   AzureDiagnostics
   | where ResourceProvider == "MICROSOFT.KEYVAULT"
   | where OperationName == "SecretGet"
   | where SecretName == "shopify-api-token"
   | project TimeGenerated, CallerIPAddress, ResultType
3. Result: See which agents/users accessed the secret
```

---

### 3. Application Insights (Monitoring)

**Access**: Azure Portal → Application Insights → multi-agent-appinsights

**Common Tasks**:

**Task 1: View Confidence Threshold Impact**
```
1. Navigate to: Logs
2. Query:
   traces
   | where timestamp > ago(1h)
   | where message contains "confidence_score"
   | summarize avg(todouble(customDimensions.confidence_score)) by bin(timestamp, 5m)
   | render timechart
3. Result: See if lowering threshold reduced escalations
```

**Task 2: Monitor Throttling Errors**
```
1. Navigate to: Failures
2. Filter: Exception type = "RateLimitExceeded"
3. Time range: Last 24 hours
4. Result: See if throttling limit needs adjustment
```

---

### 4. Cost Management (Budget Monitoring)

**Access**: Azure Portal → Cost Management → Budgets

**Common Tasks**:

**Task 1: View Current Spend vs Budget**
```
1. Navigate to: Cost analysis
2. View: ActualCost
3. Granularity: Daily
4. Time range: Current month
5. Result: See if on track for $200-250/month target
```

**Task 2: Adjust Budget Alert Thresholds**
```
1. Navigate to: Budgets
2. Find budget: "monthly-budget"
3. Click "Edit"
4. Update amount: $360 → $250
5. Update alerts:
   - 80% threshold → $200
   - 90% threshold → $225
6. Click "Save"
```

---

## Azure CLI Interface (Secondary)

### 1. Bulk Configuration Updates

**Use Case**: Update all throttling limits across multiple environments

**Script**: `scripts/update-throttling.sh`
```bash
#!/bin/bash
# Update throttling limits for all agents

APP_CONFIG_NAME="appconfig-multi-agent"
LABEL="production"

# Update OpenAI throttling
az appconfig kv set \
  --name $APP_CONFIG_NAME \
  --key "throttle:openai_rpm" \
  --value "50" \
  --label $LABEL \
  --yes

# Update NATS throttling
az appconfig kv set \
  --name $APP_CONFIG_NAME \
  --key "throttle:nats_global_rps" \
  --value "100" \
  --label $LABEL \
  --yes

# Update agent-specific throttling
az appconfig kv set \
  --name $APP_CONFIG_NAME \
  --key "throttle:agent_rps" \
  --value "20" \
  --label $LABEL \
  --yes

echo "Throttling limits updated successfully"
```

**Run**:
```bash
chmod +x scripts/update-throttling.sh
./scripts/update-throttling.sh
```

---

### 2. Configuration Backup & Restore

**Use Case**: Backup configuration before major changes, restore if issues

**Backup Script**: `scripts/backup-config.sh`
```bash
#!/bin/bash
# Backup all App Configuration settings

APP_CONFIG_NAME="appconfig-multi-agent"
BACKUP_FILE="config-backup-$(date +%Y%m%d-%H%M%S).json"

# Export all settings
az appconfig kv export \
  --name $APP_CONFIG_NAME \
  --destination file \
  --path $BACKUP_FILE \
  --format json \
  --yes

echo "Configuration backed up to: $BACKUP_FILE"
```

**Restore Script**: `scripts/restore-config.sh`
```bash
#!/bin/bash
# Restore configuration from backup

APP_CONFIG_NAME="appconfig-multi-agent"
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./restore-config.sh <backup-file>"
  exit 1
fi

# Import settings
az appconfig kv import \
  --name $APP_CONFIG_NAME \
  --source file \
  --path $BACKUP_FILE \
  --format json \
  --yes

echo "Configuration restored from: $BACKUP_FILE"
```

**Usage**:
```bash
# Backup before change
./scripts/backup-config.sh

# Make changes via Portal or CLI
# ...

# If issues, restore
./scripts/restore-config.sh config-backup-20260125-143022.json
```

---

### 3. Environment Promotion

**Use Case**: Promote staging configuration to production

**Script**: `scripts/promote-config.sh`
```bash
#!/bin/bash
# Promote configuration from staging to production

APP_CONFIG_NAME="appconfig-multi-agent"
SOURCE_LABEL="staging"
TARGET_LABEL="production"

# Export staging config
az appconfig kv export \
  --name $APP_CONFIG_NAME \
  --label $SOURCE_LABEL \
  --destination file \
  --path staging-config.json \
  --format json \
  --yes

# Import to production (with confirmation)
echo "This will overwrite production configuration with staging."
read -p "Continue? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
  az appconfig kv import \
    --name $APP_CONFIG_NAME \
    --source file \
    --path staging-config.json \
    --format json \
    --label $TARGET_LABEL \
    --yes

  echo "Configuration promoted: staging → production"
else
  echo "Operation cancelled"
fi
```

---

## Custom Admin Dashboard (Optional)

### Architecture (If Implemented)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Custom Admin Dashboard                        │
│                   (Azure App Service - $15-25/month)            │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Frontend (React/Vue.js)                                   │  │
│  │  - Configuration forms (sliders, toggles, inputs)          │  │
│  │  - Real-time metrics (charts, graphs)                      │  │
│  │  - A/B test management (feature flags)                     │  │
│  │  - Cost dashboards (spend vs budget)                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Backend (Python Flask/FastAPI)                            │  │
│  │  - Azure SDK integration (App Config, Key Vault, Monitor)  │  │
│  │  - Managed Identity authentication (no API keys)           │  │
│  │  - RBAC (Azure AD integration)                             │  │
│  │  - Audit logging (all changes tracked)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Azure Services                                             │  │
│  │  - Azure App Configuration (read/write)                    │  │
│  │  - Azure Key Vault (read only for dashboard)              │  │
│  │  - Application Insights (read metrics)                     │  │
│  │  - Cost Management (read spend data)                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Sample Dashboard Views

**View 1: Configuration Management**
```
┌─────────────────────────────────────────────────────────────────┐
│  Multi-Agent Customer Service - Admin Dashboard                 │
├─────────────────────────────────────────────────────────────────┤
│  [Configuration] [Monitoring] [Cost] [A/B Tests] [Audit Log]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Intent Classification                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Confidence Threshold          [────●────────] 0.5          │ │
│  │  (Lower = fewer escalations)     0.0 ──────── 1.0          │ │
│  │                                                             │ │
│  │  LLM Model                     [GPT-4o-mini ▼]             │ │
│  │  Temperature                   [────●────────] 0.3          │ │
│  │  Max Tokens                    [────────●────] 100          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Escalation                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Sentiment Threshold           [──────●──────] -0.7         │ │
│  │  (Lower = escalate only very negative)                      │ │
│  │                                                             │ │
│  │  Confidence Threshold          [────●────────] 0.5          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Throttling                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  OpenAI RPM Limit              [──────●──────] 50           │ │
│  │  NATS Global RPS               [────────●────] 100          │ │
│  │  Agent RPS                     [──●──────────] 20           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [Save Changes] [Reset] [Export Config] [View History]         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**View 2: A/B Test Management**
```
┌─────────────────────────────────────────────────────────────────┐
│  A/B Test Management                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Active Tests                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  RAG Pipeline Enabled                                       │ │
│  │  Status: [●] Active    Rollout: [────●────] 25%            │ │
│  │  Start: Jan 20, 2026   Duration: 7 days                    │ │
│  │                                                             │ │
│  │  Metrics (vs Control):                                      │ │
│  │  - Response accuracy:  +12% ✓                              │ │
│  │  - Avg response time:  +350ms ⚠                            │ │
│  │  - Cost per request:   +$0.02 ⚠                            │ │
│  │                                                             │ │
│  │  [Increase to 50%] [Pause] [Stop] [Full Rollout]          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  │  Critic/Supervisor Validation                               │ │
│  │  Status: [●] Active    Rollout: [──●──────] 10%            │ │
│  │  Start: Jan 23, 2026   Duration: 3 days                    │ │
│  │                                                             │ │
│  │  Metrics:                                                   │ │
│  │  - Blocked malicious: 23 (100% catch rate) ✓              │ │
│  │  - False positives:   2 (3% rate) ✓                       │ │
│  │  - Avg latency:       +120ms ✓                            │ │
│  │                                                             │ │
│  │  [Increase to 25%] [Pause] [Stop] [Full Rollout]          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [+ New A/B Test]                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**View 3: Cost Dashboard**
```
┌─────────────────────────────────────────────────────────────────┐
│  Cost Dashboard - January 2026                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current Month Spend                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  $187 / $250 budget (75% used, 10 days remaining)          │ │
│  │  [████████████████░░░░░░░░]                                │ │
│  │                                                             │ │
│  │  Projected: $218 (within budget ✓)                        │ │
│  │  vs Last Month: -$42 (16% reduction ✓)                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Top Cost Drivers                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. Azure OpenAI              $72  (38%)  ▼12% vs last mo │ │
│  │  2. Cosmos DB                 $48  (26%)  ▼8% vs last mo  │ │
│  │  3. Application Insights      $31  (17%)  ▲5% vs last mo  │ │
│  │  4. Networking (App Gateway)  $22  (12%)  → no change     │ │
│  │  5. Container Instances       $14  (7%)   ▼20% vs last mo │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Cost by Agent                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Response Generation:  $89  (most expensive, GPT-4o)       │ │
│  │  Intent Classification: $42  (GPT-4o-mini)                 │ │
│  │  Knowledge Retrieval:  $28  (embeddings + Cosmos)         │ │
│  │  Critic/Supervisor:    $18  (GPT-4o-mini)                  │ │
│  │  Escalation:           $12  (Zendesk API)                  │ │
│  │  Analytics:            $8   (minimal LLM usage)            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Optimization Recommendations                                    │
│  • Cache response generation prompts (save ~$15/month)          │
│  • Reduce Application Insights sampling to 30% (save ~$8/mo)   │
│  • Consider GPT-4o-mini for simple responses (save ~$20/mo)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Effort

**Development Time**: ~20-30 hours
- Frontend (React): ~10 hours
- Backend (Flask/FastAPI): ~8 hours
- Azure SDK integration: ~4 hours
- Testing: ~3 hours
- Deployment: ~2 hours

**Cost**: $15-25/month
- Azure App Service Basic (B1): ~$13/month
- Or Azure Container Instance (1 vCPU, 1.5 GB): ~$20/month
- Bandwidth: ~$2/month

**Decision Point**: Implement in Phase 5 Week 4 if:
1. Operations team requests it (Azure Portal too complex)
2. Business stakeholders need visibility (self-service access)
3. A/B testing frequency justifies it (daily flag changes)

---

## Configuration Change Workflows

### Workflow 1: Daily Confidence Threshold Adjustment

**Scenario**: Too many escalations (70%) → Reduce confidence threshold

**Steps**:
1. **Monitor**: Application Insights shows 70% of intents escalated
2. **Diagnose**: Check confidence score distribution
   ```kusto
   traces
   | where message contains "confidence_score"
   | summarize avg(todouble(customDimensions.confidence_score))
   | Result: avg = 0.62 (just below 0.7 threshold)
   ```
3. **Decision**: Lower threshold from 0.7 to 0.5
4. **Update**: Azure Portal → App Configuration → intent:confidence_threshold = 0.5
5. **Monitor**: Application Insights for next hour
   ```kusto
   traces
   | where timestamp > ago(1h)
   | where message contains "escalated"
   | count
   | Result: Escalations reduced to 30% ✓
   ```
6. **Document**: Log change in runbook

**Time**: 5-10 minutes
**Downtime**: None (dynamic update)

---

### Workflow 2: Weekly Throttling Adjustment

**Scenario**: Azure OpenAI rate limiting errors (429) during peak hours

**Steps**:
1. **Alert**: Application Insights alert fires (429 errors > 10/hour)
2. **Diagnose**: Check error frequency
   ```kusto
   exceptions
   | where type == "RateLimitExceeded"
   | summarize count() by bin(timestamp, 1h)
   | Result: 45 errors between 2-3 PM (peak)
   ```
3. **Decision**: Reduce burst rate, enable queuing
4. **Update** (Azure CLI):
   ```bash
   az appconfig kv set --name appconfig-multi-agent \
     --key "throttle:openai_rpm" --value "50" --label production --yes

   az appconfig kv set --name appconfig-multi-agent \
     --key "throttle:queue_enabled" --value "true" --label production --yes

   az appconfig kv set --name appconfig-multi-agent \
     --key "throttle:queue_max_size" --value "100" --label production --yes
   ```
5. **Monitor**: Application Insights for 24 hours
6. **Verify**: 429 errors reduced to <5/day ✓

**Time**: 15-20 minutes
**Downtime**: None (gradual queue adoption)

---

### Workflow 3: Prompt Engineering Iteration

**Scenario**: GPT-4o responses too verbose, increasing costs

**Steps**:
1. **Monitor**: Cost Management shows Azure OpenAI spend $95/month (target: $60)
2. **Diagnose**: Check token usage
   ```kusto
   traces
   | where message contains "tokens_used"
   | summarize avg(todouble(customDimensions.output_tokens))
   | Result: avg = 250 tokens/response (target: 150)
   ```
3. **Decision**: Update system prompt to encourage conciseness
4. **Update** (Git workflow):
   ```bash
   # Local development
   vim agents/response_generation/config.yaml
   # Change: "Provide a detailed response..."
   #     → "Provide a concise response in 2-3 sentences..."

   git add agents/response_generation/config.yaml
   git commit -m "Optimize GPT-4o prompt for conciseness (cost reduction)"
   git push origin optimize-prompt
   ```
5. **PR Review**: Team approves prompt change
6. **Merge**: CI/CD pipeline triggers
7. **Deploy**: New container image deployed (rolling update)
8. **Monitor**: Cost Management for 7 days
9. **Verify**: Azure OpenAI spend reduced to $68/month (24% reduction) ✓

**Time**: 1-2 hours (including PR review)
**Downtime**: <1 minute (rolling update)

---

### Workflow 4: A/B Test Gradual Rollout

**Scenario**: Test RAG pipeline with gradual rollout (10% → 100%)

**Steps**:
1. **Create Feature Flag** (Azure Portal):
   - Feature manager → Create flag: "rag_enabled"
   - Enable targeting: 10% of users
2. **Day 1**: Monitor metrics for 10% cohort
   ```kusto
   customMetrics
   | where name == "response_accuracy"
   | where customDimensions.rag_enabled == "true"
   | summarize avg(value)
   | Result: 87% accuracy (vs 75% baseline) ✓
   ```
3. **Day 2**: Increase to 25% (metrics still good)
4. **Day 3**: Increase to 50%
5. **Day 5**: Increase to 100% (full rollout)
6. **Day 7**: Remove feature flag (always enabled)

**Time**: 7 days (gradual rollout)
**Risk**: Low (can rollback at any stage)

---

## Access Control & Audit

### RBAC (Role-Based Access Control)

**Roles**:

1. **Platform Operator** (DevOps Engineer):
   - **Azure App Configuration**: Reader + Data Owner
   - **Azure Key Vault**: Secrets Officer (Get, List, Set)
   - **Application Insights**: Reader
   - **Cost Management**: Reader
   - **Terraform**: Contributor (infrastructure changes)

2. **Operations Engineer**:
   - **Azure App Configuration**: Data Owner (full access)
   - **Azure Key Vault**: Secrets User (Get, List only, no Set)
   - **Application Insights**: Reader
   - **Cost Management**: Reader

3. **Business Stakeholder** (optional, via custom dashboard):
   - **App Configuration**: Reader only (view settings)
   - **Cost Management**: Reader
   - **Application Insights**: Reader (metrics only)
   - **No Key Vault access**

### Audit Logging

**All Configuration Changes Logged**:

**Azure App Configuration**:
```kusto
// View all configuration changes in last 7 days
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.APPCONFIGURATION"
| where OperationName == "ConfigurationSettingWritten"
| project TimeGenerated, CallerIPAddress, ConfigurationSettingKey, PreviousValue, NewValue
| order by TimeGenerated desc
```

**Azure Key Vault**:
```kusto
// View all secret accesses
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where OperationName in ("SecretGet", "SecretSet", "SecretList")
| project TimeGenerated, CallerIdentity, OperationName, SecretName, ResultType
| order by TimeGenerated desc
```

**Custom Dashboard** (if implemented):
```python
# Backend logs all changes
@app.route('/api/config/update', methods=['POST'])
def update_config():
    old_value = get_current_value(key)
    new_value = request.json['value']

    # Update App Configuration
    app_config.set_configuration_setting(key, new_value)

    # Audit log
    logger.info(f"Config updated: {key} = {old_value} → {new_value} by {current_user}")

    return {"success": True}
```

---

## Cost Analysis

### Option 1: Azure Portal + CLI (Free)

**Costs**: $0/month
- Azure Portal: Free (built-in)
- Azure CLI: Free (open-source tool)

**Trade-offs**:
- ⚠️ Less intuitive UX (learning curve for non-technical users)
- ⚠️ Requires Azure training for operators
- ✅ Zero additional cost
- ✅ Audit logs built-in
- ✅ RBAC integrated

**Recommendation**: Start here (Phase 5 Week 1-3)

---

### Option 2: Custom Admin Dashboard (Optional)

**Development Costs**: One-time effort
- 20-30 hours @ $0 (in-house development)

**Operational Costs**: $15-25/month
- Azure App Service (B1): $13/month
- Or Container Instance: $20/month
- Bandwidth: ~$2/month
- **Total**: $15-25/month (6-10% of $250 budget)

**Trade-offs**:
- ✅ Better UX (intuitive interface)
- ✅ Business stakeholder access (self-service)
- ✅ Integrated view (all settings in one place)
- ✅ Educational value (blog post content)
- ⚠️ Development effort (20-30 hours)
- ⚠️ Ongoing cost ($15-25/month)
- ⚠️ Maintenance burden (security updates, bug fixes)

**Recommendation**: Add in Phase 5 Week 4 if justified

---

### Cost Comparison (Total Phase 5 Budget)

| Interface | Dev Effort | Monthly Cost | % of $250 Budget | Recommendation |
|-----------|-----------|--------------|------------------|----------------|
| **Azure Portal + CLI** | 0 hours | $0 | 0% | ✅ Start here |
| **+ Custom Dashboard** | 20-30 hours | $15-25 | 6-10% | ⚠️ Optional |

**Decision Framework**:
- **If operators comfortable with Azure Portal**: Skip custom dashboard (save $15-25/month)
- **If frequent A/B testing or business stakeholder access needed**: Add custom dashboard (Phase 5 Week 4)

---

## Implementation Roadmap

### Phase 5 Week 1-2: Azure Portal + CLI (Free)

**Deliverables**:
1. ✅ Document Azure Portal workflows (screenshots, step-by-step)
2. ✅ Create CLI scripts (backup, restore, bulk updates, promotion)
3. ✅ Train operators on Azure Portal (2-hour session)
4. ✅ Set up RBAC (Platform Operator, Operations Engineer roles)
5. ✅ Configure audit logging (App Configuration, Key Vault)

**Cost**: $0

---

### Phase 5 Week 3: Production Tuning

**Deliverables**:
1. ✅ Daily confidence threshold adjustments (optimize escalation rate)
2. ✅ Weekly throttling adjustments (avoid 429 errors)
3. ✅ Prompt engineering iterations (reduce token usage, cost)
4. ✅ RAG configuration tuning (optimize top_k, similarity threshold)

**Cost**: $0 (using free Azure Portal + CLI)

---

### Phase 5 Week 4: Custom Dashboard (Optional Decision Point)

**Decision Criteria**:
- [ ] Operations team struggles with Azure Portal UX?
- [ ] Business stakeholders need self-service access?
- [ ] A/B testing frequency justifies integrated view?
- [ ] Blog post readers request it (educational value)?

**If YES to 2+ criteria**: Implement custom dashboard

**Deliverables** (if implemented):
1. ✅ Frontend (React): Configuration forms, metrics charts, A/B test management
2. ✅ Backend (Flask): Azure SDK integration, Managed Identity auth
3. ✅ Deploy to Azure App Service (B1 tier)
4. ✅ Document dashboard workflows

**Cost**: $15-25/month (if implemented)

---

## Conclusion

### Recommended Approach for Phase 5

**Primary Interface**: **Azure Portal + Azure CLI** (Free)

**Rationale**:
- ✅ **Zero additional cost** (important for $200-250/month target)
- ✅ **Built-in audit logging** (Azure Monitor Activity Log)
- ✅ **RBAC integrated** (Azure AD authentication)
- ✅ **Sufficient for operations team** (2-3 operators)
- ✅ **Educational value** (demonstrates Azure-native operational patterns)

**Configuration Storage**:
1. **Secrets** → Azure Key Vault (quarterly rotation)
2. **Application Settings** → Azure App Configuration (daily tuning)
3. **Agent Behavior** → Git + YAML configs (prompt engineering)
4. **Infrastructure** → Terraform (rare changes)

**Optional Addition**: **Custom Admin Dashboard** (Phase 5 Week 4)
- Add if operators struggle with Azure Portal UX
- Add if business stakeholders need self-service access
- Add if A/B testing becomes frequent
- Cost: $15-25/month (6-10% of budget)

**Next Steps**:
1. Review this strategy with team
2. Week 1-2: Document Azure Portal workflows, create CLI scripts
3. Week 3: Production tuning using Azure Portal + CLI
4. Week 4: Decision point on custom dashboard (based on operator feedback)

---

**Document Status**: Design Specification
**Created**: January 25, 2026
**Author**: Development Team
**Review Required**: Before Phase 5 Week 1
**Decision Point**: Custom Dashboard (Phase 5 Week 4)
