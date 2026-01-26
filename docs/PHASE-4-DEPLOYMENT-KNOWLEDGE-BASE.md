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

## Next Steps

1. [ ] Configure Azure OpenAI API integration for agents
2. [ ] Set up Application Insights dashboards
3. [ ] Implement health check endpoints for all agents
4. [ ] Configure auto-scaling rules (scale down during off-hours)
5. [ ] Set up CI/CD pipeline for automated deployments
6. [ ] Run integration tests against deployed containers
7. [ ] Configure budget alerts at 83% and 93% thresholds

---

**Last Updated:** 2026-01-26
**Author:** Claude Code Assistant
**Phase:** 4 - Azure Production Setup
