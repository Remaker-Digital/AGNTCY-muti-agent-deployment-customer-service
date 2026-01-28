# Azure DevOps Pipeline Setup Guide

**Created:** 2026-01-28
**Purpose:** Step-by-step guide to configure Azure DevOps for production CI/CD

---

## Overview

This guide walks through setting up Azure DevOps Pipelines for the multi-agent customer service platform. The pipeline handles:

1. **Build**: Lint, test, and build Docker images
2. **Push**: Push images to Azure Container Registry
3. **Deploy**: Deploy to Container Apps with approval gates

## Prerequisites

Before starting, ensure you have:

- [ ] Azure DevOps organization and project
- [ ] Azure subscription with existing infrastructure (from Terraform)
- [ ] Service principal for Azure DevOps (created in Phase 4)
- [ ] Access to Azure Container Registry (ACR)

## Step 1: Create Azure DevOps Project

1. Go to [Azure DevOps](https://dev.azure.com)
2. Create a new organization (if needed) or select existing
3. Create a new project:
   - Name: `agntcy-customer-service`
   - Visibility: Private (recommended)
   - Version control: Git
   - Work item process: Agile

## Step 2: Connect to GitHub Repository

1. Navigate to **Project Settings** > **Service connections**
2. Click **New service connection**
3. Select **GitHub**
4. Authenticate with GitHub account
5. Name the connection: `github-agntcy`

## Step 3: Create Azure Service Connection

This allows Azure DevOps to deploy to your Azure subscription.

### Option A: Service Principal (Recommended)

```bash
# Create service principal if not already created
az ad sp create-for-rbac \
  --name "agntcy-cs-prod-devops-sp" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/agntcy-prod-rg \
  --sdk-auth
```

Save the output JSON - you'll need it for the service connection.

### Configure in Azure DevOps

1. Go to **Project Settings** > **Service connections**
2. Click **New service connection**
3. Select **Azure Resource Manager**
4. Choose **Service principal (manual)**
5. Fill in details from the service principal:
   - Subscription ID: `{your-subscription-id}`
   - Subscription Name: `{your-subscription-name}`
   - Service Principal ID: `{appId from JSON}`
   - Service Principal Key: `{password from JSON}`
   - Tenant ID: `{tenant from JSON}`
6. Name: `agntcy-prod-connection`
7. **Grant access permission to all pipelines**: Check this box

## Step 4: Create ACR Service Connection

1. Go to **Project Settings** > **Service connections**
2. Click **New service connection**
3. Select **Docker Registry**
4. Choose **Azure Container Registry**
5. Select:
   - Subscription: Your Azure subscription
   - Registry: `acragntcycsprodrc6vcp`
6. Name: `agntcy-acr-connection`
7. **Grant access permission to all pipelines**: Check this box

## Step 5: Create Variable Groups

Variable groups store secrets securely for the pipeline.

### Create Production Secrets Group

1. Go to **Pipelines** > **Library**
2. Click **+ Variable group**
3. Name: `agntcy-prod-secrets`
4. Add the following variables (mark as secret):

| Variable | Description | Secret |
|----------|-------------|--------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | No |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | **Yes** |
| `COSMOS_CONNECTION_STRING` | Cosmos DB connection string | **Yes** |
| `KEY_VAULT_URI` | Key Vault URI | No |

5. Click **Link secrets from an Azure key vault** (optional but recommended):
   - Service connection: `agntcy-prod-connection`
   - Key vault: `kv-agntcy-cs-prod-rc6vcp`
   - Authorize and select secrets

6. Click **Save**

## Step 6: Create Environments

Environments control deployment approvals and gates.

### Staging Environment

1. Go to **Pipelines** > **Environments**
2. Click **New environment**
3. Name: `staging`
4. Resource: None (for now)
5. Click **Create**

### Production Environment

1. Go to **Pipelines** > **Environments**
2. Click **New environment**
3. Name: `production`
4. Resource: None
5. Click **Create**
6. Click on the environment > **More options** (...)
7. Select **Approvals and checks**
8. Add **Approvals**:
   - Approvers: Add yourself and/or team
   - Instructions: "Review staging deployment before approving production"
   - Timeout: 72 hours
9. Add **Business hours** (optional):
   - Limit deployments to business hours only

## Step 7: Create the Pipeline

1. Go to **Pipelines** > **Pipelines**
2. Click **New pipeline**
3. Select **GitHub** as code source
4. Select the repository: `Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service`
5. Select **Existing Azure Pipelines YAML file**
6. Path: `/azure-pipelines.yml`
7. Click **Continue**
8. Review the pipeline configuration
9. Click **Run** to trigger first build

## Step 8: Link Variable Group to Pipeline

1. Edit the pipeline
2. Click **Variables** button
3. Click **Variable groups**
4. Link `agntcy-prod-secrets`
5. Save

## Step 9: Verify Pipeline Runs

### First Run Expectations

The first run will:
1. **Build Stage**: Should pass (lint may warn, tests should pass)
2. **Push Stage**: Will push images to ACR (main branch only)
3. **Deploy Staging**: Will update Container Apps
4. **Deploy Production**: Will wait for approval

### Common Issues and Fixes

| Issue | Cause | Solution |
|-------|-------|----------|
| "Service connection not found" | Connection not linked | Go to pipeline settings > Resources |
| "Docker push failed" | ACR auth issue | Verify ACR connection and permissions |
| "Container App not found" | Name mismatch | Check Container App names match variables |
| "Approval timeout" | No one approved | Approve in Environments > production |

## Step 10: Configure Branch Policies (Optional)

Protect the main branch with required checks:

1. Go to **Repos** > **Branches**
2. Click on `main` > **Branch policies**
3. Add **Build validation**:
   - Build pipeline: Select the pipeline
   - Trigger: Automatic
   - Policy requirement: Required
4. Add **Reviewers** (optional)

## Pipeline Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Commit    │───▶│    Build    │───▶│    Push     │───▶│  Deploy     │
│             │    │  Lint/Test  │    │   to ACR    │    │  Staging    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                                ▼
                                                         ┌─────────────┐
                                                         │  Approval   │
                                                         │    Gate     │
                                                         └─────────────┘
                                                                │
                                                                ▼
                                                         ┌─────────────┐
                                                         │   Deploy    │
                                                         │ Production  │
                                                         └─────────────┘
```

## Rollback Procedure

If a production deployment fails:

### Option 1: Re-deploy Previous Build

1. Go to **Pipelines** > **Runs**
2. Find the last successful run
3. Click **Re-run** > **Re-run failed jobs** or **Run new**

### Option 2: Manual Rollback

```bash
# Get previous image tag
az containerapp revision list \
  --name agntcy-cs-prod-api-gateway \
  --resource-group agntcy-prod-rg \
  --query "[].{Name:name, Image:properties.template.containers[0].image}" \
  -o table

# Rollback to specific revision
az containerapp revision activate \
  --name agntcy-cs-prod-api-gateway \
  --resource-group agntcy-prod-rg \
  --revision <revision-name>
```

## Monitoring

After deployment, monitor via:

1. **Azure Monitor**: Container Apps metrics
2. **Application Insights**: Request telemetry
3. **Pipeline runs**: Build and deployment history
4. **Cost Management**: Budget alerts

## Troubleshooting

### Pipeline Stuck at Approval

```bash
# Check environment approvals
az pipelines runs list --pipeline-id <pipeline-id> --status inProgress
```

### Container App Not Updating

```bash
# Force restart
az containerapp revision restart \
  --name agntcy-cs-prod-api-gateway \
  --resource-group agntcy-prod-rg \
  --revision <revision-name>
```

### Image Not Found in ACR

```bash
# Verify image exists
az acr repository show-tags \
  --name acragntcycsprodrc6vcp \
  --repository api-gateway
```

## Security Best Practices

1. **Never store secrets in YAML** - Use variable groups
2. **Use Key Vault linking** - Secrets auto-rotate
3. **Limit service principal scope** - Only resource group access
4. **Enable audit logs** - Track who approved what
5. **Review approvals** - Don't auto-approve production

## Cost Considerations

Azure DevOps pricing:
- **Free tier**: 1 parallel job, 1800 minutes/month
- **Basic tier**: $40/user/month for unlimited minutes
- **Build minutes**: First 1800 free, then $0.002/minute

For this project, free tier is sufficient for:
- ~1-2 deployments per day
- ~10-minute build times

---

## Quick Reference

| Item | Value |
|------|-------|
| Pipeline file | `/azure-pipelines.yml` |
| Service connection | `agntcy-prod-connection` |
| ACR connection | `agntcy-acr-connection` |
| Variable group | `agntcy-prod-secrets` |
| Staging environment | `staging` |
| Production environment | `production` |

## Related Documentation

- [Azure DevOps Pipelines](https://learn.microsoft.com/azure/devops/pipelines/)
- [Container Apps Deployment](https://learn.microsoft.com/azure/container-apps/azure-pipelines)
- [Service Connections](https://learn.microsoft.com/azure/devops/pipelines/library/service-endpoints)
- [Approval Gates](https://learn.microsoft.com/azure/devops/pipelines/process/approvals)
