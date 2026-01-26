# Phase 4 Azure Deployment Knowledge Base

## Overview

This document captures all details, issues, and resolution strategies from the Phase 4 Azure production deployment of the AGNTCY Multi-Agent Customer Service Platform. Use this as a reference for troubleshooting and future deployments.

**Deployment Date:** 2026-01-26
**Region:** East US 2
**Total Containers:** 8 (2 infrastructure + 6 agents)

---

## Infrastructure Summary

### Azure Resources Deployed

| Resource Type | Name | Purpose |
|--------------|------|---------|
| Resource Group | agntcy-prod-rg | Container for all resources |
| Virtual Network | agntcy-cs-prod-vnet | Private networking (10.0.0.0/16) |
| Subnet | agntcy-cs-prod-subnet-containers | Container subnet (10.0.1.0/24) |
| Container Registry | acragntcycsprodrc6vcp | Docker image storage |
| Cosmos DB | cosmos-agntcy-cs-prod-rc6vcp | Conversation/session storage |
| Key Vault | kv-agntcy-cs-prod-rc6vcp | Secrets management |
| Application Insights | agntcy-cs-prod-appinsights-rc6vcp | Monitoring/telemetry |
| Log Analytics Workspace | agntcy-cs-prod-log-rc6vcp | Log aggregation |
| User-Assigned Identity | agntcy-cs-prod-identity-containers | Container RBAC |

### Container Groups Deployed

| Container Group | Image | Private IP | CPU | Memory | Status |
|----------------|-------|------------|-----|--------|--------|
| agntcy-cs-prod-cg-slim | slim-gateway:latest | 10.0.1.4:8443 | 1.0 | 2.0 GB | Succeeded |
| agntcy-cs-prod-cg-nats | nats:2.10-alpine | 10.0.1.5:4222 | 0.5 | 1.0 GB | Succeeded |
| agntcy-cs-prod-cg-knowledge | knowledge-retrieval:latest | 10.0.1.6:8080 | 0.5 | 1.0 GB | Succeeded |
| agntcy-cs-prod-cg-critic | critic-supervisor:latest | 10.0.1.7:8080 | 0.5 | 1.0 GB | Succeeded |
| agntcy-cs-prod-cg-response | response-generator:latest | 10.0.1.8:8080 | 0.5 | 1.5 GB | Succeeded |
| agntcy-cs-prod-cg-analytics | analytics:latest | 10.0.1.9:8080 | 0.5 | 1.0 GB | Succeeded |
| agntcy-cs-prod-cg-intent | intent-classifier:latest | 10.0.1.10:8080 | 0.5 | 1.0 GB | Succeeded |
| agntcy-cs-prod-cg-escalation | escalation:latest | 10.0.1.11:8080 | 0.5 | 1.0 GB | Succeeded |

---

## Issues Encountered and Resolutions

### Issue 1: ACR Push Network Errors

**Symptoms:**
```
write tcp 10.0.0.1:61234->20.42.65.88:443: use of closed network connection
```

**Root Cause:** Intermittent network connectivity issues during large image pushes to Azure Container Registry.

**Resolution Strategy:**
1. Retry the `docker push` command multiple times
2. Use smaller layer sizes where possible (multi-stage builds help)
3. Ensure stable network connection before pushing
4. Consider using `--retry` flags if available in Docker CLI

**Commands Used:**
```bash
# Initial login
az acr login --name acragntcycsprodrc6vcp

# Push with retry (manual retry if fails)
docker push acragntcycsprodrc6vcp.azurecr.io/slim-gateway:latest
```

---

### Issue 2: SLIM Container "No Command Specified" Error

**Symptoms:**
```
to generate container spec: no command specified
```

Container failed to start immediately after creation.

**Root Cause:** The `ghcr.io/agntcy/slim:0.6.1` Docker image has null CMD and ENTRYPOINT directives. Azure Container Instances requires an explicit command when the image doesn't define one.

**Diagnosis Steps:**
```bash
# Check container events
az container show --name agntcy-cs-prod-cg-slim --resource-group agntcy-prod-rg --query "containers[0].instanceView.events" --output table

# Inspect image locally
docker inspect ghcr.io/agntcy/slim:0.6.1 --format='{{.Config.Cmd}} {{.Config.Entrypoint}}'
# Output: [] []  (both null)
```

**Resolution:**
Add explicit `commands` parameter to the Terraform container configuration:

```hcl
# In containers.tf
container {
  name   = "slim-gateway"
  image  = "${azurerm_container_registry.main.login_server}/slim-gateway:latest"
  cpu    = 1.0
  memory = 2.0

  # SLIM requires explicit command - image has no default CMD/ENTRYPOINT
  commands = ["/slim", "--port", "8443"]

  ports {
    port     = 8443
    protocol = "TCP"
  }
  # ... rest of configuration
}
```

**Recovery Steps After Failed Container:**
```bash
# Delete failed container group
az container delete --name agntcy-cs-prod-cg-slim --resource-group agntcy-prod-rg --yes

# Refresh Terraform state
cd terraform/phase4_prod
terraform refresh

# Create new plan with fix
terraform plan -out=phase4-containers-fixed.plan

# Apply fixed plan
terraform apply phase4-containers-fixed.plan
```

---

### Issue 3: Missing Critic/Supervisor Agent

**Symptoms:** Only 5 agent directories existed in `agents/` but Phase 4 requires 6 agents.

**Root Cause:** The Critic/Supervisor agent was specified in architecture requirements but not yet implemented.

**Resolution:** Created complete agent implementation:

**Files Created:**
- `agents/critic_supervisor/agent.py` - Main agent implementation
- `agents/critic_supervisor/requirements.txt` - Dependencies
- `agents/critic_supervisor/Dockerfile` - Multi-stage build

**Key Implementation Details:**

```python
# agents/critic_supervisor/agent.py
class CriticSupervisorAgent:
    """Content validation agent for input/output safety."""

    INPUT_VALIDATION_PROMPT = """..."""  # From Phase 3.5 optimization
    OUTPUT_VALIDATION_PROMPT = """..."""

    async def validate_input(self, message: dict) -> dict:
        """Validates incoming messages for prompt injection, jailbreak, PII extraction."""

    async def validate_output(self, message: dict) -> dict:
        """Validates AI responses for profanity, PII leakage, harmful content."""
```

**Dockerfile Pattern (Multi-Stage):**
```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc
COPY agents/critic_supervisor/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-warn-script-location -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
COPY --chown=appuser:appuser shared/ /app/shared/
COPY --chown=appuser:appuser agents/critic_supervisor/agent.py .
USER appuser
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1
CMD ["python", "agent.py"]
```

---

### Issue 4: Long Container Creation Times

**Symptoms:** SLIM gateway and NATS containers took 20+ minutes to create initially.

**Root Cause:**
1. First deployment to subnet requires VNet integration setup
2. Large image pull times from ACR
3. Azure Container Instances provisioning in new region

**Observations:**
- First container groups (SLIM, NATS) took longest (up to 26+ minutes in some cases)
- Subsequent containers created faster (1-5 minutes) as infrastructure was warmed up
- Private VNet integration adds overhead

**Mitigation Strategies:**
1. Pre-pull images to ACR before deployment
2. Use smaller base images where possible
3. Consider deploying infrastructure containers first, then agents
4. Set appropriate Terraform timeouts:

```hcl
resource "azurerm_container_group" "slim_gateway" {
  # ...
  timeouts {
    create = "30m"
    delete = "15m"
  }
}
```

---

## Docker Build and Push Workflow

### Complete Build Sequence

```bash
# 1. Login to ACR
az acr login --name acragntcycsprodrc6vcp

# 2. Pull and tag SLIM gateway
docker pull ghcr.io/agntcy/slim:0.6.1
docker tag ghcr.io/agntcy/slim:0.6.1 acragntcycsprodrc6vcp.azurecr.io/slim-gateway:latest
docker push acragntcycsprodrc6vcp.azurecr.io/slim-gateway:latest

# 3. Build all agent images
cd "C:/Users/micha/OneDrive/Desktop/AGNTCY-muti-agent-deployment-customer-service"

docker build -t acragntcycsprodrc6vcp.azurecr.io/intent-classifier:latest -f agents/intent_classification/Dockerfile .
docker build -t acragntcycsprodrc6vcp.azurecr.io/knowledge-retrieval:latest -f agents/knowledge_retrieval/Dockerfile .
docker build -t acragntcycsprodrc6vcp.azurecr.io/response-generator:latest -f agents/response_generation/Dockerfile .
docker build -t acragntcycsprodrc6vcp.azurecr.io/escalation:latest -f agents/escalation/Dockerfile .
docker build -t acragntcycsprodrc6vcp.azurecr.io/analytics:latest -f agents/analytics/Dockerfile .
docker build -t acragntcycsprodrc6vcp.azurecr.io/critic-supervisor:latest -f agents/critic_supervisor/Dockerfile .

# 4. Push all images
docker push acragntcycsprodrc6vcp.azurecr.io/intent-classifier:latest
docker push acragntcycsprodrc6vcp.azurecr.io/knowledge-retrieval:latest
docker push acragntcycsprodrc6vcp.azurecr.io/response-generator:latest
docker push acragntcycsprodrc6vcp.azurecr.io/escalation:latest
docker push acragntcycsprodrc6vcp.azurecr.io/analytics:latest
docker push acragntcycsprodrc6vcp.azurecr.io/critic-supervisor:latest

# 5. Verify images in ACR
az acr repository list --name acragntcycsprodrc6vcp --output table
```

### Verification Commands

```bash
# List all container groups
az container list --resource-group agntcy-prod-rg --output table

# Check specific container logs
az container logs --name agntcy-cs-prod-cg-intent --resource-group agntcy-prod-rg

# Check container events (for troubleshooting)
az container show --name agntcy-cs-prod-cg-slim --resource-group agntcy-prod-rg \
  --query "containers[0].instanceView.events" --output table

# Restart a container group
az container restart --name agntcy-cs-prod-cg-intent --resource-group agntcy-prod-rg
```

---

## Terraform Configuration Notes

### Key Variables (terraform.tfvars)

```hcl
# Container deployment flag
deploy_containers = true

# Resource naming
project_name = "agntcy-cs"
environment  = "prod"
location     = "eastus2"

# Budget constraints
monthly_budget = 360

# Feature flags
enable_multi_language = false
enable_nats           = true
enable_private_endpoints = true
```

### Container Dependencies

The Terraform configuration uses `depends_on` to ensure proper deployment order:

1. **SLIM Gateway** and **NATS** - No dependencies (deployed first)
2. **Agent containers** - Depend on SLIM Gateway completion

```hcl
resource "azurerm_container_group" "intent_classifier" {
  count = var.deploy_containers ? 1 : 0

  depends_on = [
    azurerm_container_group.slim_gateway
  ]
  # ...
}
```

### State Management

```bash
# Refresh state after manual changes
terraform refresh

# Import existing resources if needed
terraform import azurerm_container_group.slim_gateway[0] \
  /subscriptions/.../resourceGroups/agntcy-prod-rg/providers/Microsoft.ContainerInstance/containerGroups/agntcy-cs-prod-cg-slim

# Plan with specific targets
terraform plan -target=azurerm_container_group.slim_gateway
```

---

## Environment Variables for Containers

All containers receive these environment variables via Terraform:

```hcl
environment_variables = {
  SLIM_ENDPOINT           = "https://10.0.1.4:8443"
  NATS_URL                = "nats://10.0.1.5:4222"
  COSMOS_ENDPOINT         = azurerm_cosmosdb_account.main.endpoint
  KEY_VAULT_URL           = azurerm_key_vault.main.vault_uri
  APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
  AZURE_OPENAI_ENDPOINT   = "https://remaker.openai.azure.com/"
  AZURE_CLIENT_ID         = azurerm_user_assigned_identity.containers.client_id
}
```

---

## Cost Tracking

### Estimated Monthly Costs (Phase 4)

| Resource | Estimated Cost |
|----------|---------------|
| Container Instances (8 groups) | ~$120-150/month |
| Cosmos DB (Serverless) | ~$25-40/month |
| Azure OpenAI API | ~$48-62/month |
| Application Insights | ~$10-15/month |
| Key Vault | ~$1-3/month |
| Container Registry (Basic) | ~$5/month |
| VNet/Networking | ~$5-10/month |
| **Total** | **~$214-285/month** |

*Note: Within revised budget of $310-360/month*

---

## Troubleshooting Checklist

### Container Won't Start

1. Check container events: `az container show --name <name> --resource-group agntcy-prod-rg --query "containers[0].instanceView.events"`
2. Verify image exists in ACR: `az acr repository show --name acragntcycsprodrc6vcp --image <image>:latest`
3. Check if image has CMD/ENTRYPOINT: `docker inspect <image> --format='{{.Config.Cmd}} {{.Config.Entrypoint}}'`
4. Verify managed identity has ACR pull permission

### Network Connectivity Issues

1. Verify subnet has service endpoints enabled
2. Check NSG rules allow required ports
3. Verify containers are in correct subnet
4. Test from within VNet (use bastion or jumpbox)

### ACR Authentication Fails

1. Verify managed identity exists and is assigned to container group
2. Check ACR role assignment: `az role assignment list --scope /subscriptions/.../resourceGroups/agntcy-prod-rg/providers/Microsoft.ContainerRegistry/registries/acragntcycsprodrc6vcp`
3. Ensure identity has `AcrPull` role

---

## Lessons Learned

1. **Always check image CMD/ENTRYPOINT** before deploying to ACI - many official images assume docker-compose or Kubernetes which handle this differently.

2. **Network retries are normal** - Azure networking can be intermittent; build retry logic into deployment scripts.

3. **First deployment is slowest** - VNet integration and image caching make subsequent deployments much faster.

4. **Multi-stage Dockerfiles are essential** - Keep images small for faster pulls and lower storage costs.

5. **Use managed identities** - Avoid storing ACR credentials; use RBAC with user-assigned managed identities.

6. **Test locally first** - docker-compose.yml should mirror ACI configuration to catch issues early.

7. **Monitor costs from day 1** - Set up budget alerts immediately after deployment.

---

## Phase 4 Remaining Work

This section enumerates all remaining work to complete Phase 4. Use this as a checklist for new sessions.

### Completed ✅

| Task | Status | Date |
|------|--------|------|
| Deploy Azure infrastructure (VNet, Cosmos, Key Vault, ACR, App Insights) | ✅ Done | 2026-01-26 |
| Create Critic/Supervisor agent implementation | ✅ Done | 2026-01-26 |
| Build and push all 7 container images to ACR | ✅ Done | 2026-01-26 |
| Deploy 8 container groups (SLIM, NATS, 6 agents) | ✅ Done | 2026-01-26 |
| Configure private VNet networking | ✅ Done | 2026-01-26 |
| Fix SLIM gateway startup (explicit command) | ✅ Done | 2026-01-26 |

---

### Category 1: Azure OpenAI Integration (Priority: HIGH)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 1.1 | Configure Azure OpenAI API keys in Key Vault | 1 hr | None | Key already stored, verify access |
| 1.2 | Update agent code to use Azure OpenAI SDK | 4-6 hrs | 1.1 | Replace mock LLM calls with real API |
| 1.3 | Implement token usage tracking per agent | 2-3 hrs | 1.2 | For cost monitoring |
| 1.4 | Test Intent Classification with real GPT-4o-mini | 2 hrs | 1.2, 1.3 | Use Phase 3.5 prompts |
| 1.5 | Test Critic/Supervisor with real GPT-4o-mini | 2 hrs | 1.2, 1.3 | Use Phase 3.5 prompts |
| 1.6 | Test Response Generation with real GPT-4o | 2 hrs | 1.2, 1.3 | Use Phase 3.5 prompts |
| 1.7 | Test Knowledge Retrieval with text-embedding-3-large | 2 hrs | 1.2 | RAG embeddings |
| 1.8 | Validate end-to-end conversation flow | 3-4 hrs | 1.4-1.7 | Full multi-agent test |

**Subtotal: 18-22 hours**

---

### Category 2: PII Tokenization Service (Priority: HIGH)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 2.1 | Create `shared/tokenization/` module structure | 1 hr | None | See architecture-requirements-phase2-5.md |
| 2.2 | Implement PII detection (regex + entity recognition) | 4-6 hrs | 2.1 | Names, emails, phones, addresses, order IDs |
| 2.3 | Implement token generation (UUID) | 1 hr | 2.1 | Format: TOKEN_uuid |
| 2.4 | Implement Key Vault token storage | 2-3 hrs | 2.1 | Primary storage |
| 2.5 | Implement Cosmos DB fallback storage | 2 hrs | 2.4 | If latency >100ms |
| 2.6 | Add tokenization to Critic/Supervisor input flow | 2 hrs | 2.2-2.5 | Before third-party AI |
| 2.7 | Add de-tokenization to response output flow | 2 hrs | 2.2-2.5 | After AI response |
| 2.8 | Test latency (<100ms P95 target) | 2 hrs | 2.6, 2.7 | Performance validation |

**Subtotal: 16-21 hours**

---

### Category 3: Real API Integrations (Priority: MEDIUM)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 3.1 | Create Shopify Partner account & dev store | 1 hr | None | Free tier |
| 3.2 | Implement Shopify MCP client (orders, customers, products) | 6-8 hrs | 3.1 | Replace mock API |
| 3.3 | Create Zendesk sandbox account | 1 hr | None | Free trial |
| 3.4 | Implement Zendesk MCP client (tickets, users) | 4-6 hrs | 3.3 | Replace mock API |
| 3.5 | Create Mailchimp free account | 0.5 hr | None | Free tier (500 contacts) |
| 3.6 | Implement Mailchimp MCP client (campaigns, subscribers) | 3-4 hrs | 3.5 | Replace mock API |
| 3.7 | Test Response Generation with real Shopify data | 2-3 hrs | 3.2 | Order status, product info |
| 3.8 | Test Escalation with real Zendesk ticketing | 2-3 hrs | 3.4 | Ticket creation, updates |

**Subtotal: 19.5-26.5 hours**

---

### Category 4: Event-Driven Architecture (Priority: MEDIUM)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 4.1 | Configure NATS JetStream subjects and streams | 2 hrs | None | Container already running |
| 4.2 | Implement event publisher (shared utility) | 2-3 hrs | 4.1 | Publish to NATS |
| 4.3 | Implement event subscriber pattern (shared utility) | 2-3 hrs | 4.1 | Subscribe from NATS |
| 4.4 | Register Shopify webhooks (orders, customers, inventory) | 2 hrs | 3.2, 4.2 | See event-driven-requirements.md |
| 4.5 | Implement webhook ingestion Azure Function | 4-6 hrs | 4.2 | HTTP trigger → NATS |
| 4.6 | Register Zendesk webhooks (tickets, satisfaction) | 2 hrs | 3.4, 4.2 | See event-driven-requirements.md |
| 4.7 | Implement scheduled triggers (Azure Functions Timer) | 3-4 hrs | 4.2 | Daily reports, promo schedules |
| 4.8 | Test event flow end-to-end | 3-4 hrs | 4.4-4.7 | Webhook → NATS → Agent |

**Subtotal: 20-26 hours**

---

### Category 5: Execution Tracing & Observability (Priority: MEDIUM)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 5.1 | Add OpenTelemetry instrumentation to all agents | 4-6 hrs | None | See execution-tracing-requirements.md |
| 5.2 | Implement trace context propagation (A2A messages) | 2-3 hrs | 5.1 | Trace across agents |
| 5.3 | Add LLM call tracing (tokens, latency, cost) | 2-3 hrs | 5.1 | Per-call metrics |
| 5.4 | Implement PII tokenization in traces | 2 hrs | 2.2, 5.1 | Privacy-safe traces |
| 5.5 | Configure Application Insights trace export | 2 hrs | 5.1 | OTLP → App Insights |
| 5.6 | Create Application Insights dashboards | 3-4 hrs | 5.5 | Conversation flow, latency, cost |
| 5.7 | Set up alerts (latency >2min, error rate >5%, cost >80%) | 2 hrs | 5.6 | Proactive monitoring |
| 5.8 | Test trace capture and visualization | 2 hrs | 5.6 | Validate full traces |

**Subtotal: 19-24 hours**

---

### Category 6: Multi-Language Support (Priority: LOW)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 6.1 | Create language detection in Intent Classification | 2-3 hrs | 1.4 | Detect en, fr-CA, es |
| 6.2 | Create fr-CA response templates | 4-6 hrs | None | Pre-translated, no real-time translation |
| 6.3 | Create es response templates | 4-6 hrs | None | Pre-translated |
| 6.4 | Implement language-based routing (topic-based) | 2-3 hrs | 6.1 | response-generator-en, -fr-ca, -es |
| 6.5 | Deploy additional Response Generation containers | 2 hrs | 6.2-6.4 | One per language |
| 6.6 | Test multi-language conversation flows | 3-4 hrs | 6.5 | E2E validation |

**Subtotal: 17-24 hours**

---

### Category 7: RAG Pipeline (Priority: MEDIUM)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 7.1 | Create knowledge base documents (75 docs target) | 4-6 hrs | None | 50 products, 20 articles, 5 policies |
| 7.2 | Implement document chunking strategy | 2-3 hrs | 7.1 | ~500 tokens per chunk |
| 7.3 | Generate embeddings with text-embedding-3-large | 2-3 hrs | 1.7, 7.2 | Via Azure OpenAI |
| 7.4 | Store vectors in Cosmos DB (MongoDB API) | 3-4 hrs | 7.3 | Vector search capability |
| 7.5 | Implement semantic search in Knowledge Retrieval Agent | 4-6 hrs | 7.4 | Top-3 retrieval |
| 7.6 | Test retrieval accuracy (>90% retrieval@3 target) | 2-3 hrs | 7.5 | Validation against Phase 3.5 dataset |

**Subtotal: 17-25 hours**

---

### Category 8: CI/CD & DevOps (Priority: MEDIUM)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 8.1 | Create Azure DevOps project and service connections | 2 hrs | None | Connect to ACR, Azure |
| 8.2 | Create pipeline for agent image builds | 4-6 hrs | 8.1 | Build, test, push to ACR |
| 8.3 | Create pipeline for Terraform deployment | 3-4 hrs | 8.1, 8.2 | Plan, apply with approval |
| 8.4 | Implement blue-green deployment strategy | 4-6 hrs | 8.3 | Zero-downtime updates |
| 8.5 | Add integration tests to pipeline | 3-4 hrs | 8.2 | Run against staging |
| 8.6 | Configure pipeline triggers (PR, main branch) | 1-2 hrs | 8.2-8.5 | Automated runs |

**Subtotal: 17-24 hours**

---

### Category 9: Security & Compliance (Priority: HIGH)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 9.1 | Enable managed identity for all container → Azure access | 2-3 hrs | None | Already partially done |
| 9.2 | Configure Key Vault access policies per agent | 2 hrs | 9.1 | Least privilege |
| 9.3 | Enable TLS 1.3 for all agent communication | 2-3 hrs | None | SLIM already supports |
| 9.4 | Run Dependabot security scan | 1 hr | None | GitHub integration |
| 9.5 | Run OWASP ZAP scan against SLIM gateway | 2-3 hrs | None | Security validation |
| 9.6 | Document secrets rotation procedures | 2 hrs | 9.2 | Quarterly rotation |
| 9.7 | Validate Critic/Supervisor blocks prompt injection | 2-3 hrs | 1.5 | 100+ test cases from Phase 3.5 |

**Subtotal: 13-17 hours**

---

### Category 10: Testing & Validation (Priority: HIGH)

| # | Task | Effort | Dependencies | Notes |
|---|------|--------|--------------|-------|
| 10.1 | Create Azure-specific integration test suite | 4-6 hrs | 1.8 | Against deployed containers |
| 10.2 | Run load tests (100 concurrent users, 1000 req/min) | 3-4 hrs | 10.1 | Azure Load Testing or Locust |
| 10.3 | Validate response time <2 min (P95) | 2 hrs | 10.2 | KPI target |
| 10.4 | Validate automation rate >70% | 2 hrs | 10.1 | KPI target |
| 10.5 | Test error handling and recovery | 3-4 hrs | 10.1 | Container restarts, network failures |
| 10.6 | Create smoke test suite for production | 2-3 hrs | 10.1 | Quick validation after deploy |

**Subtotal: 16-21 hours**

---

### Phase 4 Summary

| Category | Effort (Hours) | Priority |
|----------|---------------|----------|
| 1. Azure OpenAI Integration | 18-22 | HIGH |
| 2. PII Tokenization Service | 16-21 | HIGH |
| 3. Real API Integrations | 19.5-26.5 | MEDIUM |
| 4. Event-Driven Architecture | 20-26 | MEDIUM |
| 5. Execution Tracing & Observability | 19-24 | MEDIUM |
| 6. Multi-Language Support | 17-24 | LOW |
| 7. RAG Pipeline | 17-25 | MEDIUM |
| 8. CI/CD & DevOps | 17-24 | MEDIUM |
| 9. Security & Compliance | 13-17 | HIGH |
| 10. Testing & Validation | 16-21 | HIGH |
| **Total** | **172.5-230.5** | - |

**Recommended Order of Execution:**
1. **Azure OpenAI Integration** (Category 1) - Enables all agents to use real AI
2. **Security & Compliance** (Category 9) - Critical for production
3. **PII Tokenization** (Category 2) - Required before third-party AI calls
4. **Testing & Validation** (Category 10) - Validate as we go
5. **Execution Tracing** (Category 5) - Enables debugging
6. **Real API Integrations** (Category 3) - Replace mocks
7. **Event-Driven Architecture** (Category 4) - Webhooks and events
8. **RAG Pipeline** (Category 7) - Knowledge retrieval
9. **CI/CD & DevOps** (Category 8) - Automation
10. **Multi-Language Support** (Category 6) - Last priority

---

## Quick Reference: Starting a New Session

When starting a new Claude Code session for Phase 4 work:

1. **Read this file first:** `docs/PHASE-4-DEPLOYMENT-KNOWLEDGE-BASE.md`
2. **Check container status:**
   ```bash
   az container list --resource-group agntcy-prod-rg --output table
   ```
3. **Verify ACR login:**
   ```bash
   az acr login --name acragntcycsprodrc6vcp
   ```
4. **Review architecture requirements:**
   - `docs/architecture-requirements-phase2-5.md`
   - `docs/execution-tracing-observability-requirements.md`
   - `docs/event-driven-requirements.md`
5. **Check CLAUDE.md for project context**

**Key IPs for testing:**
- SLIM Gateway: 10.0.1.4:8443
- NATS: 10.0.1.5:4222
- Agents: 10.0.1.6-11:8080

---

**Last Updated:** 2026-01-26
**Author:** Claude Code Assistant
**Phase:** 4 - Azure Production Setup
**Infrastructure Status:** ✅ Complete
**Remaining Work:** ~172-230 hours across 10 categories
