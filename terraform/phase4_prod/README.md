# Phase 4 Terraform Configuration

This directory contains Terraform configuration for deploying the AGNTCY Multi-Agent Customer Service Platform to Azure.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Azure East US 2                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Virtual Network (10.0.0.0/16)                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │              Container Subnet (10.0.1.0/24)                      │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │  │  │
│  │  │  │  SLIM    │ │  NATS    │ │  Intent  │ │Knowledge │           │  │  │
│  │  │  │ Gateway  │ │JetStream │ │Classifier│ │Retrieval │           │  │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │  │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │  │  │
│  │  │  │Response  │ │Escalation│ │Analytics │ │  Critic/ │           │  │  │
│  │  │  │Generator │ │  Agent   │ │  Agent   │ │Supervisor│           │  │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │           Private Endpoints Subnet (10.0.2.0/24)                │  │  │
│  │  │  ┌──────────────────┐  ┌──────────────────┐                     │  │  │
│  │  │  │   Cosmos DB PE   │  │   Key Vault PE   │                     │  │  │
│  │  │  └──────────────────┘  └──────────────────┘                     │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   Cosmos DB     │  │    Key Vault    │  │ Container       │             │
│  │   Serverless    │  │    Standard     │  │ Registry Basic  │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                                   │
│  │  Log Analytics  │  │   Application   │                                   │
│  │   (7-day)       │  │   Insights      │                                   │
│  └─────────────────┘  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         Azure West US (Existing)                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                       Azure OpenAI Service                               ││
│  │  GPT-4o-mini | GPT-4o | text-embedding-3-large                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Azure CLI** installed and authenticated
   ```bash
   az login --tenant 1836296d-c9f8-4fd3-8cf3-ce94f6358cc3
   az account set --subscription "828eb521-88bb-4b01-ac3e-7ba779c55212"
   ```

2. **Terraform** >= 1.5.0
   ```bash
   terraform --version
   ```

3. **Existing Resource Group**
   - Name: `agntcy-prod-rg` (East US 2)

4. **Existing Azure OpenAI** in West US
   - Resource: `myOAIResource3aa68d`
   - Deployments: `gpt-4o-mini`, `gpt-4o`, `text-embedding-3-large`

## Quick Start

### 1. Configure Variables

```bash
cd terraform/phase4_prod

# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values (NEVER commit this file)
notepad terraform.tfvars
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Plan Deployment

```bash
terraform plan -out=phase4.plan
```

### 4. Apply Configuration

```bash
terraform apply phase4.plan
```

## Cost Breakdown

| Resource | Monthly Cost |
|----------|-------------|
| Container Instances (8 total) | ~$130-150 |
| - SLIM Gateway (1 vCPU, 2GB) | ~$30-40 |
| - NATS JetStream (0.5 vCPU, 1GB) | ~$12-18 |
| - 6 Agents (0.5 vCPU, 1-1.5GB each) | ~$90-100 |
| Cosmos DB Serverless | ~$15-30 |
| Container Registry (Basic) | ~$5 |
| Key Vault (Standard) | ~$0.30 |
| Log Analytics (7-day) | ~$15-25 |
| Application Insights (50% sampling) | ~$6-8 |
| Azure OpenAI (existing) | ~$48-62 |
| Networking | ~$5-10 |
| **Total** | **~$230-290** |

**Note:** Azure OpenAI costs are variable based on token usage.

## File Structure

```
terraform/phase4_prod/
├── main.tf                    # Provider config, locals
├── variables.tf               # Input variables
├── networking.tf              # VNet, subnets, NSGs
├── keyvault.tf                # Key Vault and secrets
├── cosmosdb.tf                # Cosmos DB Serverless
├── container_registry.tf      # ACR Basic
├── containers.tf              # Container Instances (8)
├── observability.tf           # Log Analytics, App Insights
├── outputs.tf                 # Output values
├── terraform.tfvars.example   # Example variable values
└── README.md                  # This file
```

## Deployed Resources

### Container Instances

| Name | Purpose | CPU | Memory |
|------|---------|-----|--------|
| slim-gateway | AGNTCY transport layer | 1.0 | 2.0 GB |
| nats | Event bus (JetStream) | 0.5 | 1.0 GB |
| intent-classifier | Intent classification | 0.5 | 1.0 GB |
| knowledge-retrieval | RAG and product search | 0.5 | 1.0 GB |
| response-generator | LLM response generation | 0.5 | 1.5 GB |
| escalation | Human handoff | 0.5 | 1.0 GB |
| analytics | Metrics collection | 0.5 | 1.0 GB |
| critic-supervisor | Content validation | 0.5 | 1.0 GB |

### Cosmos DB Containers

| Database | Container | Partition Key | TTL |
|----------|-----------|---------------|-----|
| conversations | sessions | /sessionId | 30 days |
| conversations | messages | /conversationId | 90 days |
| conversations | analytics | /metricDate | None |
| conversations | pii-tokens | /tokenId | 90 days |
| knowledge | documents | /category | None |

### Key Vault Secrets

| Secret Name | Purpose |
|-------------|---------|
| azure-openai-api-key | Azure OpenAI authentication |
| shopify-api-key | Shopify API (if configured) |
| shopify-api-secret | Shopify API (if configured) |
| zendesk-api-token | Zendesk API (if configured) |
| mailchimp-api-key | Mailchimp API (if configured) |
| google-analytics-credentials | GA4 service account (if configured) |

## Security

- **Private Endpoints**: Cosmos DB and Key Vault accessible only via VNet
- **Managed Identity**: Containers use user-assigned identity (no API keys in env vars)
- **Network Security Groups**: Container subnet restricted to necessary ports
- **Key Vault RBAC**: Secrets accessed via role assignments, not access policies

## Operations

### View Container Logs

```bash
az container logs --resource-group agntcy-prod-rg --name agntcy-cs-prod-cg-intent
```

### Restart a Container

```bash
az container restart --resource-group agntcy-prod-rg --name agntcy-cs-prod-cg-intent
```

### Check Budget Status

```bash
az consumption budget show --resource-group agntcy-prod-rg --budget-name agntcy-cs-prod-budget-monthly
```

### View Costs

```bash
az cost management query --type ActualCost --timeframe MonthToDate --scope "/subscriptions/828eb521-88bb-4b01-ac3e-7ba779c55212/resourceGroups/agntcy-prod-rg"
```

## Outputs

After deployment, retrieve important values:

```bash
# Get all outputs
terraform output

# Get specific outputs
terraform output keyvault_uri
terraform output cosmosdb_endpoint
terraform output acr_login_server
terraform output agent_ips
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning:** This will delete all data in Cosmos DB. Ensure backups are available.

## Troubleshooting

### Container fails to start

1. Check container logs: `az container logs --name <container-name> --resource-group agntcy-prod-rg`
2. Verify managed identity has correct RBAC roles
3. Check if Key Vault secrets are populated
4. Verify container image exists in ACR

### Cosmos DB connection errors

1. Verify private endpoint is healthy
2. Check DNS resolution from container
3. Verify managed identity has CosmosDB role assignment

### Budget alerts not firing

1. Check action group email configuration
2. Verify budget thresholds in Azure portal
3. Budget updates may take 24 hours to activate

## Deployment Status

**Infrastructure:** ✅ Deployed (2026-01-26)
**Containers:** ⏳ Pending (set `deploy_containers = true` after pushing images)

### Deployed Resources

| Resource | Name | Status |
|----------|------|--------|
| VNet | agntcy-cs-prod-vnet | ✅ |
| Cosmos DB | cosmos-agntcy-cs-prod-rc6vcp | ✅ |
| Key Vault | kv-agntcy-cs-prod-rc6vcp | ✅ |
| ACR | acragntcycsprodrc6vcp | ✅ |
| App Insights | agntcy-cs-prod-appi-rc6vcp | ✅ |
| Managed Identity | agntcy-cs-prod-identity-containers | ✅ |
| Private Endpoints | Cosmos DB + Key Vault | ✅ |
| Budget Alerts | 83% + 93% | ✅ |

## Next Steps

1. **Build container images** for 6 agents + SLIM gateway
2. **Push images to ACR**: `acragntcycsprodrc6vcp.azurecr.io`
3. **Enable container deployment**: Set `deploy_containers = true` in terraform.tfvars
4. **Apply Terraform**: `terraform apply`
5. **Configure external services** (Shopify, Zendesk) if needed
6. **Deploy Application Gateway** for public ingress (Phase 5)
7. **Set up CI/CD pipeline** with Azure DevOps

---

**Created:** 2026-01-26
**Last Updated:** 2026-01-26
**Phase:** 4
**Budget:** $310-360/month
**Region:** East US 2 (compute), West US (Azure OpenAI)
