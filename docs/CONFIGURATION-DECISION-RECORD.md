# Configuration Management - Decision Record

**Decision Date**: January 25, 2026
**Decision Maker**: Project Team
**Status**: ✅ **APPROVED**
**Effective Phase**: Phase 4-5

---

## Decision Summary

**Approved Approach**: **Hierarchical Configuration Model with Azure Portal + CLI as primary interface**

The team has approved the dual-interface configuration management strategy for Phases 4-5, prioritizing cost-effectiveness and operational simplicity while maintaining production-grade capabilities.

---

## Approved Configuration Strategy

### Configuration Hierarchy (5 Layers)

```
Layer 1: Infrastructure (Terraform)
├─ Azure region, resource groups, networking
├─ Container specs, auto-scaling rules
├─ Budget alerts, log retention
└─ Storage: terraform/phase4_prod/terraform.tfvars

Layer 2: Secrets (Azure Key Vault)
├─ API keys, connection strings, certificates
├─ PII tokens (customer data tokenization)
└─ Access: Managed Identity (agents), RBAC (operators)

Layer 3: Application Settings (Azure App Configuration) ← 90% of changes
├─ Feature flags, LLM parameters, timeouts
├─ Rate limits, cache TTLs, escalation thresholds
├─ Language support, sampling rates
└─ Access: Managed Identity (agents), Azure Portal (operators)

Layer 4: Agent Behavior (Config Files in Git)
├─ LLM prompts, intent keywords, response templates
├─ Knowledge base metadata, escalation rules
└─ Storage: agents/{agent_name}/config.yaml in Git

Layer 5: Environment Variables (Container Instances)
├─ Container-specific overrides (AGENT_NAME, LOG_LEVEL)
├─ References to Layer 2 & 3 (@Microsoft.KeyVault(...))
└─ Storage: Terraform azurerm_container_group resource
```

### Configuration Precedence (Highest to Lowest)

1. **Environment Variables** (container-specific overrides)
2. **Azure App Configuration** (operational tuning)
3. **Config Files** (agent behavior from Git)
4. **Default Values** (hardcoded fallbacks)

**Azure Key Vault** always takes precedence for secrets.

---

## Approved Interfaces

### Primary Interface: Azure Portal + Azure CLI (FREE)

**Approved for**: Phase 4-5, all operational tuning

**Use Cases**:
- Daily confidence threshold adjustments
- Weekly throttling limit updates
- Quarterly API key rotation
- Feature flag management (A/B testing)
- Real-time metrics monitoring
- Cost tracking and alerts

**Cost**: **$0/month** (0% of budget)

**Training Requirements**:
- 2-hour Azure Portal training session (Phase 5 Week 1)
- CLI script documentation (backup, restore, bulk updates)
- Operational runbooks with screenshots

---

### Optional Interface: Custom Admin Dashboard ($15-25/month)

**Decision Point**: Phase 5 Week 4

**Criteria for Implementation** (must meet 2+ criteria):
1. Operations team struggles with Azure Portal UX
2. Business stakeholders need self-service access
3. A/B testing becomes very frequent (daily flag changes)
4. Blog post readers request it (educational value)

**If Approved in Week 4**:
- Development effort: 20-30 hours
- Cost: $15-25/month (6-10% of $250 budget)
- Features: Sliders, toggles, real-time charts, integrated view

**If Not Needed**:
- Continue with Azure Portal + CLI (free)
- Saves $15-25/month (contributes to $200-250 budget target)

---

## Configuration Change Workflows (Approved)

### Workflow 1: Daily Confidence Threshold Adjustment

**Frequency**: Daily during Phase 5 tuning
**Interface**: Azure Portal
**Duration**: <1 minute
**Downtime**: None (dynamic update)

**Steps**:
1. Azure Portal → App Configuration → appconfig-multi-agent
2. Find key: `intent:confidence_threshold`
3. Update value: `0.7` → `0.5`
4. Click Apply
5. Agents pick up new value within 30 seconds (no restart)

---

### Workflow 2: Weekly Throttling Adjustment

**Frequency**: Weekly during Phase 5 optimization
**Interface**: Azure CLI (scripted)
**Duration**: 5-10 minutes
**Downtime**: None (gradual adoption)

**Script**: `scripts/update-throttling.sh`
```bash
#!/bin/bash
az appconfig kv set \
  --name appconfig-multi-agent \
  --key "throttle:openai_rpm" \
  --value "50" \
  --label production \
  --yes
```

---

### Workflow 3: Prompt Engineering Iteration

**Frequency**: Daily during Phase 5 tuning
**Interface**: Git + CI/CD
**Duration**: 1-2 hours (including PR review)
**Downtime**: <1 minute (rolling update)

**Steps**:
1. Edit `agents/response_generation/config.yaml`
2. Commit changes, create PR
3. Team review and approve
4. Merge → CI/CD pipeline triggers
5. New container deployed (rolling update)

---

### Workflow 4: Quarterly API Key Rotation

**Frequency**: Quarterly (security requirement)
**Interface**: Azure Portal
**Duration**: 5-10 minutes
**Downtime**: None (seamless rotation)

**Steps**:
1. Generate new API token (Shopify/Zendesk/etc.)
2. Azure Portal → Key Vault → Update secret (new version)
3. Agents auto-pick up within 5 minutes
4. Revoke old token after confirming new one works

---

## Cost Impact (Approved Budget)

### Configuration Infrastructure Costs

| Component | Monthly Cost | % of $250 Budget | Status |
|-----------|--------------|------------------|--------|
| **Azure Key Vault** | $5-10 | 2-4% | ✅ Approved |
| **Azure App Configuration** | $1-5 | 0.4-2% | ✅ Approved |
| **Config Files (Git)** | $0 | 0% | ✅ Approved |
| **Environment Variables** | $0 | 0% | ✅ Approved |
| **Terraform State** | $0.50 | 0.2% | ✅ Approved |
| **Custom Dashboard** | $0 (Phase 5 W4 decision) | 0% | ⏳ Deferred |
| **TOTAL (Phase 5 Start)** | **$6.50-15.50** | **2.6-6.2%** | ✅ Approved |

### Phase 5 Budget Allocation

| Category | Budget | Configuration % |
|----------|--------|-----------------|
| **Total Phase 5 Budget** | $200-250/month | 100% |
| **Configuration Infrastructure** | $6.50-15.50/month | 2.6-6.2% |
| **Remaining for Agents/APIs** | $184.50-243.50/month | 93.8-97.4% |

**Conclusion**: Configuration infrastructure consumes <7% of budget, leaving >93% for core services.

---

## Implementation Plan (Approved)

### Phase 4: Infrastructure Setup (Week 1-4)

**Week 1-2**:
- ✅ Create Azure Key Vault (store all secrets)
- ✅ Create Terraform variables (infrastructure configuration)
- ✅ Update `.gitignore` (exclude terraform.tfvars, secrets)

**Week 3-4**:
- ✅ Create Azure App Configuration (application settings)
- ✅ Create config files in Git (agent behavior)
- ✅ Implement ConfigManager class (shared/config.py)

---

### Phase 5: Production Operations (Week 1-4)

**Week 1-2: Azure Portal + CLI Training**
- ✅ Document Azure Portal workflows (screenshots, step-by-step)
- ✅ Create CLI scripts (backup, restore, bulk updates, promotion)
- ✅ Train operators on Azure Portal (2-hour session)
- ✅ Set up RBAC (Platform Operator, Operations Engineer roles)
- ✅ Configure audit logging (App Configuration, Key Vault)

**Week 3: Production Tuning**
- ✅ Daily confidence threshold adjustments
- ✅ Weekly throttling adjustments
- ✅ Prompt engineering iterations
- ✅ RAG configuration tuning
- ✅ A/B testing (feature flags)

**Week 4: Custom Dashboard Decision Point**
- ⏳ Evaluate operator feedback (Azure Portal UX sufficient?)
- ⏳ Assess A/B testing frequency (daily flag changes?)
- ⏳ Decision: Implement custom dashboard or continue with Portal/CLI
- ✅ If approved: Develop dashboard (20-30 hours), deploy to Azure App Service
- ✅ If not needed: Continue with free Portal/CLI (save $15-25/month)

---

## Access Control (Approved)

### RBAC Roles

**Platform Operator** (DevOps Engineer):
- Azure App Configuration: Reader + Data Owner
- Azure Key Vault: Secrets Officer (Get, List, Set)
- Application Insights: Reader
- Cost Management: Reader
- Terraform: Contributor

**Operations Engineer**:
- Azure App Configuration: Data Owner (full access)
- Azure Key Vault: Secrets User (Get, List only, no Set)
- Application Insights: Reader
- Cost Management: Reader

**Business Stakeholder** (optional, via custom dashboard if implemented):
- App Configuration: Reader only
- Cost Management: Reader
- Application Insights: Reader
- No Key Vault access

### Audit Logging (Approved)

**All configuration changes logged**:
- Azure App Configuration: All setting updates tracked
- Azure Key Vault: All secret accesses logged
- Custom Dashboard (if implemented): Backend logs all changes
- Retention: 90 days (Azure Monitor)

---

## Success Criteria (Approved)

### Phase 4 Success Criteria

- ✅ Azure Key Vault created and populated with all secrets
- ✅ Azure App Configuration created with initial settings
- ✅ Config files in Git for all agents
- ✅ ConfigManager class implemented (hierarchical lookup)
- ✅ Terraform variables configured (infrastructure)
- ✅ Environment variables configured (containers)

### Phase 5 Success Criteria

**Week 1-2**:
- ✅ Operators trained on Azure Portal (2-hour session)
- ✅ CLI scripts documented (backup, restore, bulk updates)
- ✅ RBAC configured (Platform Operator, Operations Engineer)
- ✅ Audit logging enabled (App Configuration, Key Vault)

**Week 3**:
- ✅ Confidence thresholds tuned (escalation rate optimized)
- ✅ Throttling limits adjusted (zero 429 errors)
- ✅ Prompts optimized (cost reduction achieved)
- ✅ RAG configuration tuned (accuracy >90%)
- ✅ A/B tests conducted (at least 2 feature flags tested)

**Week 4**:
- ✅ Custom dashboard decision made (implement or defer)
- ✅ If implemented: Dashboard deployed and operational
- ✅ If deferred: Documented decision (cost savings $15-25/month)

---

## Risks & Mitigations (Approved)

### Risk 1: Azure Portal Learning Curve

**Risk**: Operations team unfamiliar with Azure Portal
**Probability**: Medium
**Impact**: Medium (slower operations)
**Mitigation**:
- 2-hour training session (Phase 5 Week 1)
- Screenshot-based runbooks
- CLI scripts for repetitive tasks
- Custom dashboard option (Week 4 decision)

**Status**: ✅ Mitigated with training plan

---

### Risk 2: Configuration Errors

**Risk**: Incorrect configuration values causing service disruption
**Probability**: Low
**Impact**: High (service outage)
**Mitigation**:
- Backup configuration before changes (CLI script)
- Test changes in staging first
- Gradual rollout (feature flags)
- Audit logging (all changes tracked)
- Rollback capability (restore from backup)

**Status**: ✅ Mitigated with backup/restore procedures

---

### Risk 3: Cost Overruns (Custom Dashboard)

**Risk**: Custom dashboard adds $15-25/month, exceeding budget
**Probability**: Low (optional feature)
**Impact**: Medium (6-10% of budget)
**Mitigation**:
- Start with free Portal/CLI (Phase 5 Week 1-3)
- Decision point in Week 4 (based on actual need)
- Can defer indefinitely if not needed

**Status**: ✅ Mitigated with phased decision approach

---

## Documentation Deliverables (Approved)

### Phase 4 Deliverables

1. ✅ CONFIGURATION-MANAGEMENT-STRATEGY.md (comprehensive strategy)
2. ✅ PHASE-5-CONFIGURATION-INTERFACE.md (operational interface design)
3. ✅ CONFIGURATION-DECISION-RECORD.md (this document)
4. ✅ shared/config.py (ConfigManager implementation)
5. ✅ agents/{agent_name}/config.yaml (behavior configuration files)

### Phase 5 Deliverables

1. ✅ Azure Portal Runbook (screenshots, step-by-step workflows)
2. ✅ CLI Scripts (backup, restore, bulk updates, promotion)
3. ✅ Operator Training Materials (2-hour session slides)
4. ✅ RBAC Configuration Guide (role assignments)
5. ✅ Audit Logging Queries (KQL examples)
6. ⏳ Custom Dashboard Documentation (if implemented in Week 4)

---

## Key Decisions Summary

| Decision | Approved Approach | Rationale |
|----------|------------------|-----------|
| **Primary Interface** | Azure Portal + CLI (FREE) | Zero cost, built-in audit, RBAC integrated |
| **Configuration Hierarchy** | 5-layer model (Key Vault, App Config, Git, Terraform, Env Vars) | Security, flexibility, version control |
| **Configuration Precedence** | Env Vars > App Config > Git > Defaults | Clear override behavior |
| **Custom Dashboard** | Optional (Week 4 decision) | Start free, add if justified |
| **Budget Allocation** | $6.50-15.50/month (2.6-6.2% of $250) | Minimal infrastructure cost |
| **Audit Logging** | Azure Monitor (90-day retention) | Compliance, security |
| **Access Control** | RBAC (Platform Operator, Operations Engineer) | Least privilege principle |
| **Training** | 2-hour Azure Portal session | Operator enablement |

---

## Next Actions

### Immediate (Phase 4 Week 1)

1. ✅ Create Azure Key Vault (terraform/phase4_prod/key_vault.tf)
2. ✅ Create Azure App Configuration (terraform/phase4_prod/app_configuration.tf)
3. ✅ Update .gitignore (exclude terraform.tfvars, secrets)

### Phase 4 Week 3-4

4. ✅ Implement ConfigManager class (shared/config.py)
5. ✅ Create agent config files (agents/{agent_name}/config.yaml)
6. ✅ Test hierarchical configuration (unit tests)

### Phase 5 Week 1

7. ✅ Document Azure Portal workflows (runbook with screenshots)
8. ✅ Create CLI scripts (scripts/backup-config.sh, restore-config.sh, etc.)
9. ✅ Train operators (2-hour session)

### Phase 5 Week 4

10. ⏳ Evaluate custom dashboard need (operator feedback, A/B test frequency)
11. ⏳ Decision: Implement or defer custom dashboard
12. ✅ Document decision (cost savings if deferred)

---

## Approval

**Approved By**: Project Team
**Approval Date**: January 25, 2026
**Effective Date**: Phase 4 Week 1 (TBD)

**Signatures**:
- ✅ Technical Lead: Approved
- ✅ Project Manager: Approved
- ✅ Cost Controller: Approved (within budget)

---

**Document Status**: ✅ **APPROVED**
**Version**: 1.0
**Last Updated**: January 25, 2026
**Next Review**: Phase 5 Week 4 (Custom Dashboard Decision Point)

---

## Related Documents

- CONFIGURATION-MANAGEMENT-STRATEGY.md (comprehensive strategy, 50+ pages)
- PHASE-5-CONFIGURATION-INTERFACE.md (interface design, workflows)
- DEPLOYMENT-GUIDE.md (Phase 4 preparation, Terraform examples)
- PHASE-4-KICKOFF.md (Phase 4 planning)
- PHASE-3-COMPLETION-SUMMARY.md (Phase 3 handoff)

---

**END OF DECISION RECORD**
