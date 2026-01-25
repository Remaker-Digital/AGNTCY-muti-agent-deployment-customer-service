# Deployment Guide - Multi-Agent Customer Service Platform

**Version**: 1.0 (Phase 4 Preparation)
**Last Updated**: January 25, 2026
**Target Phase**: Phase 4 - Azure Production Setup
**Status**: Preparation (Pre-Phase 4)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Deployment Phases](#deployment-phases)
3. [Azure Service Architecture](#azure-service-architecture)
4. [Prerequisites](#prerequisites)
5. [Terraform Setup](#terraform-setup)
6. [Azure Service Configuration](#azure-service-configuration)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Deployment Process](#deployment-process)
9. [Cost Management](#cost-management)
10. [Monitoring & Observability](#monitoring--observability)
11. [Security](#security)
12. [Disaster Recovery](#disaster-recovery)
13. [Troubleshooting](#troubleshooting)

---

## Introduction

This guide prepares you for Phase 4 deployment to Azure. While Phase 3 (current) runs entirely locally with $0 cloud costs, Phase 4 will deploy the Multi-Agent Customer Service platform to Microsoft Azure with a budget of **$310-360/month**.

### Deployment Timeline

- **Phase 3 (Current)**: Local development and testing ($0/month)
- **Phase 4 (Next)**: Azure production setup ($310-360/month)
  - Terraform infrastructure provisioning
  - Multi-language support (English, French, Spanish)
  - Real API integration (Shopify, Zendesk, Mailchimp, Google Analytics)
  - Azure OpenAI integration (GPT-4o-mini, GPT-4o, text-embedding-3-large)
  - Azure DevOps CI/CD pipelines
- **Phase 5 (Final)**: Production deployment, load testing, security validation, go-live

### Key Objectives for Phase 4

1. ✅ Deploy to Azure East US region
2. ✅ Implement cost controls (budget alerts at 83% and 93%)
3. ✅ Integrate real APIs (Shopify, Zendesk, Mailchimp, Google Analytics)
4. ✅ Enable Azure OpenAI for intent classification and response generation
5. ✅ Implement RAG pipeline with Cosmos DB vector search
6. ✅ Deploy PII tokenization service (Azure Key Vault)
7. ✅ Set up event-driven architecture (NATS JetStream)
8. ✅ Deploy Critic/Supervisor Agent (6th agent) for content validation
9. ✅ Implement execution tracing with Azure Monitor + Application Insights

---

## Deployment Phases

### Phase 1-3: Local Development ($0/month) ✅ COMPLETE

**Environment**: Docker Compose on localhost
**Services**: 5 agents + 4 mock APIs + SLIM transport + observability stack
**Testing**: Unit, integration, E2E, performance, load, stress
**Status**: 100% complete

### Phase 4: Azure Production Setup ($310-360/month)

**Duration**: ~6-8 weeks
**Focus**: Infrastructure provisioning and integration

**Week 1-2: Infrastructure Setup**
- Terraform configuration for all Azure resources
- Azure subscription setup with budget alerts
- Service Principal and Managed Identity configuration
- Network security groups and private endpoints

**Week 3-4: Service Deployment**
- Deploy 6 agents to Azure Container Instances
- Configure Azure OpenAI Service (GPT-4o-mini, GPT-4o, embeddings)
- Set up Cosmos DB (Serverless mode with vector search)
- Configure Azure Key Vault for PII tokenization
- Deploy NATS JetStream for event-driven architecture

**Week 5-6: API Integration**
- Integrate real Shopify API (orders, products, inventory)
- Integrate real Zendesk API (tickets, conversations)
- Integrate real Mailchimp API (email campaigns)
- Integrate Google Analytics API (tracking, reporting)

**Week 7-8: Testing & Validation**
- Staging environment smoke tests
- Performance testing with real APIs
- Load testing with Azure Load Testing service
- Security scanning (OWASP ZAP, Snyk, Bandit)
- Cost optimization iteration

### Phase 5: Production Deployment ($310-360/month)

**Duration**: ~4 weeks
**Focus**: Go-live, load testing, DR validation

**Week 1-2: Pre-Production**
- Final security audit
- Disaster recovery drill (full environment rebuild)
- Load testing: 100 concurrent users, 1000 req/min
- Blue-green deployment preparation

**Week 3: Go-Live**
- Production cutover
- Monitor metrics for 72 hours
- Fix any critical issues

**Week 4: Post-Launch Optimization**
- Cost optimization (target: reduce to $200-250/month)
- Performance tuning based on production metrics
- Final documentation and blog post

---

## Azure Service Architecture

### Phase 4 Service Map

```
┌─────────────────────────────────────────────────────────────────┐
│                      Azure East US Region                        │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Container Instances (6 agents @ ~$30-40/month total)     │  │
│  │  - intent-classifier                                       │  │
│  │  - knowledge-retrieval                                     │  │
│  │  - response-generator-en/fr/es (3 instances)              │  │
│  │  - escalation-handler                                      │  │
│  │  - analytics-processor                                     │  │
│  │  - critic-supervisor (NEW - content validation)           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Azure OpenAI Service (~$48-62/month)                      │  │
│  │  - GPT-4o-mini (intent + critic) ~$0.15/1M tokens         │  │
│  │  - GPT-4o (response generation) ~$2.50/1M tokens          │  │
│  │  - text-embedding-3-large (RAG) ~$0.13/1M tokens          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Cosmos DB Serverless (~$50-70/month)                      │  │
│  │  - Real-time data (orders, inventory, tickets)            │  │
│  │  - Vector search (MongoDB API, 1536 dimensions)           │  │
│  │  - Analytical store (analytics agent)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Azure Key Vault (~$5-10/month)                            │  │
│  │  - PII tokenization (UUID tokens)                         │  │
│  │  - API keys (Shopify, Zendesk, Mailchimp, Analytics)     │  │
│  │  - Secrets management                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Blob Storage + CDN (~$10-15/month)                        │  │
│  │  - Knowledge base (75 documents, 1hr cache TTL)           │  │
│  │  - Static content                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Azure Monitor + Application Insights (~$32-43/month)     │  │
│  │  - Execution tracing (OpenTelemetry)                      │  │
│  │  - Metrics (response times, error rates)                  │  │
│  │  - Logs (7-day retention)                                 │  │
│  │  - Alerts (latency, costs, errors)                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  NATS JetStream (~$0 - reuses AGNTCY transport)           │  │
│  │  - Event bus (webhooks, cron, RSS)                        │  │
│  │  - 12 event types, 7-day retention                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Networking (~$40-50/month)                                │  │
│  │  - Virtual Network (private endpoints)                    │  │
│  │  - Application Gateway (WAF, TLS termination)             │  │
│  │  - DNS Zone                                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  **TOTAL ESTIMATED COST**: $310-360/month                        │
└─────────────────────────────────────────────────────────────────┘
```

### Service Dependencies

```
Customer → App Gateway → Intent Agent → Azure OpenAI (GPT-4o-mini)
                            ↓
                     Critic/Supervisor ← Azure OpenAI (GPT-4o-mini)
                            ↓
                     Knowledge Agent ← Cosmos DB Vector Search
                            ↓                ← Blob Storage + CDN
                     Response Agent ← Azure OpenAI (GPT-4o)
                            ↓
                     Critic/Supervisor ← Azure OpenAI (GPT-4o-mini)
                            ↓
                       Customer Response

Parallel:
  - Escalation Agent ← Cosmos DB (ticket data) ← Zendesk API
  - Analytics Agent ← Cosmos DB Analytical Store ← GA API
  - Event Bus (NATS) ← Shopify/Zendesk Webhooks
```

---

## Prerequisites

### Azure Subscription

1. **Create Azure Account**:
   - https://azure.microsoft.com/en-us/free/
   - Credit card required (charges begin immediately in Phase 4)
   - Billing threshold: $310-360/month

2. **Set Up Billing Alerts**:
   ```bash
   # Azure Portal → Cost Management → Budgets
   # Create budget: $360/month
   # Alert thresholds: 83% ($299), 93% ($335)
   ```

3. **Create Service Principal**:
   ```bash
   az login
   az account set --subscription "Your Subscription Name"

   az ad sp create-for-rbac \
     --name "multi-agent-customer-service-sp" \
     --role="Contributor" \
     --scopes="/subscriptions/{subscription-id}"

   # Save output (needed for Terraform):
   # - appId (client_id)
   # - password (client_secret)
   # - tenant (tenant_id)
   ```

### Third-Party Service Accounts

**Required for Phase 4**:

1. **Shopify Partner Account** (free):
   - https://partners.shopify.com/
   - Create Development Store (free)
   - Generate API credentials (Admin API access token)

2. **Zendesk Trial/Sandbox** ($0-19/month):
   - https://www.zendesk.com/register/
   - Use trial or sandbox for development
   - Generate API token (Settings → API)

3. **Mailchimp Free Tier** (free, up to 500 contacts):
   - https://mailchimp.com/signup/
   - Generate API key (Account → Extras → API keys)

4. **Google Analytics GA4** (free):
   - https://analytics.google.com/
   - Create GA4 property
   - Create Service Account (IAM → Service Accounts)
   - Download JSON key file

### Development Tools

**Install locally**:

```bash
# Terraform (infrastructure-as-code)
# Windows: choco install terraform
# macOS: brew install terraform
# Linux: https://www.terraform.io/downloads
terraform --version  # Should be v1.6+

# Azure CLI
# Windows: https://aka.ms/installazurecliwindows
# macOS: brew install azure-cli
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az --version  # Should be v2.50+

# GitHub CLI (for Azure DevOps integration)
# Windows: choco install gh
# macOS: brew install gh
# Linux: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
gh --version  # Should be v2.30+

# kubectl (Kubernetes CLI, optional for future AKS migration)
# Windows: choco install kubernetes-cli
# macOS: brew install kubectl
# Linux: sudo apt install kubectl
kubectl version --client  # Should be v1.28+
```

---

## Terraform Setup

### Directory Structure

```
terraform/
├── phase4_prod/                  # Phase 4 production infrastructure
│   ├── main.tf                   # Main Terraform configuration
│   ├── variables.tf              # Input variables
│   ├── outputs.tf                # Output values
│   ├── providers.tf              # Azure provider configuration
│   ├── resource_groups.tf        # Resource group definitions
│   ├── networking.tf             # VNet, subnets, NSGs
│   ├── container_instances.tf   # Agent containers
│   ├── cosmos_db.tf              # Cosmos DB Serverless
│   ├── key_vault.tf              # Azure Key Vault
│   ├── openai.tf                 # Azure OpenAI Service
│   ├── storage.tf                # Blob Storage + CDN
│   ├── monitoring.tf             # Application Insights + Monitor
│   ├── app_gateway.tf            # Application Gateway (WAF)
│   ├── budget_alerts.tf          # Cost Management budgets
│   └── terraform.tfvars          # Variable values (DO NOT COMMIT)
└── modules/                      # Reusable Terraform modules
    ├── agent/                    # Container Instance module
    ├── cosmos/                   # Cosmos DB module
    └── monitoring/               # Observability module
```

### Initial Terraform Configuration

**File: `terraform/phase4_prod/providers.tf`**
```hcl
terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }

  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "tfstatemultiagent"
    container_name       = "tfstate"
    key                  = "phase4-prod.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
      recover_soft_deleted_key_vaults = true
    }

    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }

  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  client_id       = var.client_id
  client_secret   = var.client_secret
}
```

**File: `terraform/phase4_prod/variables.tf`**
```hcl
variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Azure Tenant ID"
  type        = string
  sensitive   = true
}

variable "client_id" {
  description = "Service Principal Client ID"
  type        = string
  sensitive   = true
}

variable "client_secret" {
  description = "Service Principal Client Secret"
  type        = string
  sensitive   = true
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "budget_amount" {
  description = "Monthly budget in USD"
  type        = number
  default     = 360
}

variable "alert_thresholds" {
  description = "Budget alert thresholds"
  type        = list(number)
  default     = [0.83, 0.93]  # 83% ($299), 93% ($335)
}
```

**File: `terraform/phase4_prod/terraform.tfvars` (DO NOT COMMIT)**
```hcl
# Azure credentials
subscription_id = "YOUR_SUBSCRIPTION_ID"
tenant_id       = "YOUR_TENANT_ID"
client_id       = "YOUR_CLIENT_ID"
client_secret   = "YOUR_CLIENT_SECRET"

# Configuration
location    = "East US"
environment = "production"

# Cost controls
budget_amount     = 360
alert_thresholds  = [0.83, 0.93]
```

**Add to `.gitignore`**:
```
terraform/*.tfvars
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/.terraform.lock.hcl
```

### Terraform Commands

```bash
# Navigate to Terraform directory
cd terraform/phase4_prod

# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Plan deployment (preview changes)
terraform plan -out=tfplan

# Apply deployment (create resources)
terraform apply tfplan

# Show current state
terraform show

# Destroy all resources (CAUTION)
terraform destroy
```

---

## Azure Service Configuration

### Azure OpenAI Service

**Deployment Steps**:
1. Create Azure OpenAI resource (East US region)
2. Deploy 3 models:
   - **GPT-4o-mini**: Intent classification, Critic/Supervisor validation
   - **GPT-4o**: Response generation
   - **text-embedding-3-large**: RAG embeddings (1536 dimensions)
3. Configure rate limits: 60 req/min (GPT-4o-mini), 30 req/min (GPT-4o)
4. Store API key in Azure Key Vault

**Terraform Configuration**:
```hcl
resource "azurerm_cognitive_account" "openai" {
  name                = "openai-multi-agent"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = "S0"

  tags = {
    environment = var.environment
    cost-center = "ai-models"
  }
}

resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }

  sku {
    name     = "Standard"
    capacity = 60  # 60K tokens/min
  }
}

# Similar for gpt-4o and text-embedding-3-large
```

### Cosmos DB Serverless

**Configuration**:
- **Mode**: Serverless (pay-per-request)
- **API**: MongoDB (for vector search support)
- **Consistency**: Session (balance of performance and consistency)
- **Backup**: Continuous (30-day point-in-time restore)
- **Containers**:
  - `orders` (real-time order data)
  - `tickets` (Zendesk ticket data)
  - `knowledge-base` (vector embeddings, 1536 dimensions)
  - `analytics` (analytical store)

**Terraform Configuration**:
```hcl
resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-multi-agent"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "MongoDB"

  capabilities {
    name = "EnableServerless"
  }

  capabilities {
    name = "EnableMongo"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  backup {
    type = "Continuous"
  }
}
```

### Azure Key Vault

**Configuration**:
- **Purpose**: PII tokenization, secrets management
- **Access Policy**: Managed Identity for agents
- **Soft Delete**: 90 days (purge protection enabled)
- **Secrets**:
  - Shopify API token
  - Zendesk API token
  - Mailchimp API key
  - Google Analytics service account JSON
  - Azure OpenAI API key
  - Cosmos DB connection string

**Terraform Configuration**:
```hcl
resource "azurerm_key_vault" "main" {
  name                       = "kv-multi-agent"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  access_policy {
    tenant_id = var.tenant_id
    object_id = azurerm_user_assigned_identity.agents.principal_id

    secret_permissions = [
      "Get",
      "List"
    ]
  }
}
```

---

## CI/CD Pipeline

### Azure DevOps Setup

**Phase 4 replaces GitHub Actions** with Azure DevOps Pipelines for production deployment.

**Why Azure DevOps?**
- Integrated with Azure resources
- Better support for Terraform state management
- Self-hosted agents for cost control
- Enterprise-grade deployment gates

**Pipeline Stages**:
1. **Build**: Install dependencies, run linters
2. **Test**: Unit + integration tests
3. **Terraform Plan**: Preview infrastructure changes
4. **Manual Approval**: Human review before deploy
5. **Terraform Apply**: Deploy infrastructure
6. **Deploy Agents**: Push container images to ACR
7. **Smoke Tests**: Validate deployment
8. **Rollback** (if smoke tests fail)

**File: `azure-pipelines.yml`**
```yaml
trigger:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

stages:
- stage: Build
  jobs:
  - job: BuildAndTest
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '3.14'

    - script: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
      displayName: 'Install dependencies'

    - script: |
        pytest tests/unit/ -v --cov=shared --cov-report=xml
      displayName: 'Run unit tests'

    - task: PublishCodeCoverageResults@1
      inputs:
        codeCoverageTool: 'Cobertura'
        summaryFileLocation: '$(System.DefaultWorkingDirectory)/coverage.xml'

- stage: TerraformPlan
  dependsOn: Build
  jobs:
  - job: Plan
    steps:
    - task: TerraformInstaller@0
      inputs:
        terraformVersion: '1.6.0'

    - task: TerraformTaskV4@4
      inputs:
        command: 'init'
        workingDirectory: '$(System.DefaultWorkingDirectory)/terraform/phase4_prod'
        backendServiceArm: 'Azure-Service-Connection'

    - task: TerraformTaskV4@4
      inputs:
        command: 'plan'
        workingDirectory: '$(System.DefaultWorkingDirectory)/terraform/phase4_prod'
        environmentServiceNameAzureRM: 'Azure-Service-Connection'

- stage: Deploy
  dependsOn: TerraformPlan
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - deployment: DeployProduction
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: TerraformTaskV4@4
            inputs:
              command: 'apply'
              workingDirectory: '$(System.DefaultWorkingDirectory)/terraform/phase4_prod'
              environmentServiceNameAzureRM: 'Azure-Service-Connection'

          - task: AzureCLI@2
            inputs:
              azureSubscription: 'Azure-Service-Connection'
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                # Deploy agents to Container Instances
                az container create --resource-group multi-agent-rg \
                  --name intent-classifier \
                  --image acrname.azurecr.io/intent-classifier:$(Build.BuildId) \
                  --cpu 1 --memory 2

- stage: SmokeTests
  dependsOn: Deploy
  jobs:
  - job: Validate
    steps:
    - script: |
        # Test SLIM endpoint
        curl -f https://multi-agent.eastus.cloudapp.azure.com/health

        # Run quick E2E test
        pytest tests/e2e/test_scenarios.py::test_S001_greeting -v
      displayName: 'Run smoke tests'
```

---

## Deployment Process

### Step-by-Step Deployment

**Pre-Deployment Checklist**:
- [ ] Azure subscription created with budget alerts
- [ ] Service Principal created with Contributor role
- [ ] Third-party API accounts created (Shopify, Zendesk, Mailchimp, GA)
- [ ] Terraform installed and configured
- [ ] Azure CLI installed and logged in
- [ ] terraform.tfvars populated with credentials
- [ ] .gitignore updated to exclude secrets
- [ ] Phase 3 tests passing locally

**Deployment Steps**:

```bash
# Step 1: Verify Azure login
az login
az account show

# Step 2: Create Terraform state storage
az group create --name tfstate-rg --location "East US"
az storage account create \
  --name tfstatemultiagent \
  --resource-group tfstate-rg \
  --location "East US" \
  --sku Standard_LRS

az storage container create \
  --name tfstate \
  --account-name tfstatemultiagent

# Step 3: Initialize Terraform
cd terraform/phase4_prod
terraform init

# Step 4: Plan deployment
terraform plan -out=tfplan

# Review plan output:
# - Resources to create
# - Estimated costs
# - Security implications

# Step 5: Apply deployment
terraform apply tfplan

# Expected duration: 15-30 minutes
# Resources created:
# - Resource groups
# - Virtual network
# - Container Instances (6 agents)
# - Azure OpenAI Service
# - Cosmos DB
# - Key Vault
# - Blob Storage + CDN
# - Application Insights
# - Application Gateway

# Step 6: Verify deployment
az resource list --resource-group multi-agent-rg --output table

# Step 7: Configure secrets in Key Vault
az keyvault secret set \
  --vault-name kv-multi-agent \
  --name shopify-api-token \
  --value "YOUR_SHOPIFY_TOKEN"

az keyvault secret set \
  --vault-name kv-multi-agent \
  --name zendesk-api-token \
  --value "YOUR_ZENDESK_TOKEN"

# Repeat for all secrets

# Step 8: Deploy agent containers
# (Handled by Azure DevOps pipeline in Phase 4)
az container create \
  --resource-group multi-agent-rg \
  --name intent-classifier \
  --image acrname.azurecr.io/intent-classifier:latest \
  --cpu 1 --memory 2 \
  --environment-variables \
    SLIM_ENDPOINT=http://slim-service:8080 \
    OPENAI_API_KEY=@keyvault-reference

# Step 9: Run smoke tests
curl https://multi-agent.eastus.cloudapp.azure.com/health
pytest tests/e2e/test_scenarios.py::test_S001_greeting -v

# Step 10: Monitor costs
az consumption budget list
```

**Post-Deployment Validation**:
```bash
# Check all agents running
az container list --resource-group multi-agent-rg --output table

# Check Application Insights for traces
az monitor app-insights component show \
  --app multi-agent-appinsights \
  --resource-group multi-agent-rg

# Query recent requests
az monitor app-insights query \
  --app multi-agent-appinsights \
  --analytics-query "requests | where timestamp > ago(1h) | summarize count() by name"

# Check budget alerts
az consumption budget list --output table
```

---

## Cost Management

### Budget Breakdown ($310-360/month)

| Service | Estimated Cost | Optimization Strategy |
|---------|----------------|----------------------|
| Container Instances (6 agents) | $30-40/month | Auto-scale to 1 instance, auto-shutdown 2-6 AM |
| Azure OpenAI | $48-62/month | Use GPT-4o-mini where possible, cache responses |
| Cosmos DB Serverless | $50-70/month | Optimize query patterns, use staleness tolerances |
| Key Vault | $5-10/month | Standard tier, minimize operations |
| Blob Storage + CDN | $10-15/month | 1hr cache TTL, minimize data transfer |
| Application Insights | $32-43/month | 7-day retention, 50% sampling |
| Networking | $40-50/month | Private endpoints, optimize egress |
| NATS JetStream | $0 | Reuses AGNTCY transport layer |
| **TOTAL** | **$310-360/month** | **Target: $200-250 post-Phase 5** |

### Cost Monitoring

**Budget Alerts**:
```hcl
# terraform/phase4_prod/budget_alerts.tf
resource "azurerm_consumption_budget_subscription" "main" {
  name            = "monthly-budget"
  subscription_id = var.subscription_id

  amount     = var.budget_amount  # $360
  time_grain = "Monthly"

  time_period {
    start_date = "2026-02-01T00:00:00Z"
  }

  notification {
    enabled   = true
    threshold = 83  # $299
    operator  = "GreaterThan"

    contact_emails = [
      "billing@remaker.digital"
    ]
  }

  notification {
    enabled   = true
    threshold = 93  # $335
    operator  = "GreaterThan"

    contact_emails = [
      "billing@remaker.digital",
      "cto@remaker.digital"
    ]
  }
}
```

**Cost Optimization Checklist**:
- [ ] Auto-scale agents to 1 instance during idle
- [ ] Auto-shutdown 2-6 AM ET (low traffic)
- [ ] Use GPT-4o-mini for intent + critic (cheaper than GPT-4o)
- [ ] Implement response caching (Redis optional in Phase 5)
- [ ] 7-day log retention (not 30-day default)
- [ ] 50% trace sampling (reduce ingestion costs)
- [ ] Private endpoints (reduce egress charges)
- [ ] Review costs weekly, optimize continuously

---

## Monitoring & Observability

### Execution Tracing with OpenTelemetry

**Purpose**: Enable operators to understand agent decisions and diagnose issues

**Components**:
- **Instrumentation**: OpenTelemetry spans in all agents
- **Collection**: Azure Application Insights + Monitor Logs
- **Visualization**: Azure Monitor workbooks (timeline, decision tree)
- **Retention**: 7 days (cost optimized)

**Example Trace**:
```json
{
  "trace_id": "a7f3c9e1-4b2d-8f6a-9c3e-1d8f7a2b5c4e",
  "conversation_id": "ctx-001",
  "customer_id": "TOKEN_8f6a9c3e",  // PII tokenized
  "spans": [
    {
      "span_id": "span-001",
      "agent": "intent-classifier",
      "action": "classify_intent",
      "inputs": {"message": "Where is my order?"},  // PII removed
      "outputs": {"intent": "order_status", "confidence": 0.92},
      "reasoning": "High confidence keyword match + GPT-4o-mini classification",
      "latency_ms": 345,
      "cost_usd": 0.00012
    },
    {
      "span_id": "span-002",
      "agent": "critic-supervisor",
      "action": "validate_input",
      "inputs": {"message": "Where is my order?"},
      "outputs": {"is_safe": true, "threats": []},
      "reasoning": "No prompt injection detected, no malicious content",
      "latency_ms": 120,
      "cost_usd": 0.00008
    }
  ]
}
```

**Querying Traces**:
```kusto
// Azure Monitor Logs - Kusto Query
traces
| where timestamp > ago(1h)
| where customDimensions.agent == "intent-classifier"
| summarize avg(customDimensions.latency_ms), sum(customDimensions.cost_usd) by bin(timestamp, 5m)
| render timechart
```

### Metrics & Alerts

**Key Metrics**:
- Response time P95 (<2000ms target)
- Throughput (req/min)
- Error rate (<5% target)
- Cost per request
- Agent CPU/Memory usage

**Alerts**:
```hcl
resource "azurerm_monitor_metric_alert" "high_latency" {
  name                = "high-latency-alert"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when P95 latency > 2000ms"

  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "requests/duration"
    aggregation      = "Percentile95"
    operator         = "GreaterThan"
    threshold        = 2000
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
}
```

---

## Security

### Security Checklist

**Phase 4 Security Requirements**:
- [ ] All secrets in Azure Key Vault (no hardcoded credentials)
- [ ] Managed identities for all agents (no passwords)
- [ ] TLS 1.3 for all connections (HTTPS only)
- [ ] Private endpoints for backend services (no public access)
- [ ] Network Security Groups (NSG) configured (least privilege)
- [ ] PII tokenization for third-party AI services
- [ ] Web Application Firewall (WAF) on Application Gateway
- [ ] Secrets rotation quarterly (automated)
- [ ] Vulnerability scanning (Dependabot, Snyk, Bandit)
- [ ] OWASP ZAP security scan in CI/CD
- [ ] Critic/Supervisor agent validates all input/output

### PII Tokenization

**Scope**: Third-party AI services only (OpenAI API, Anthropic API)
**Exempt**: Azure OpenAI Service, Microsoft Foundry (within secure perimeter)

**Implementation**:
```python
# PII tokenization before sending to third-party AI
from azure.keyvault.secrets import SecretClient

def tokenize_pii(data: dict) -> dict:
    """Replace PII with UUID tokens stored in Key Vault"""
    token = str(uuid.uuid4())
    token_id = f"TOKEN_{token}"

    # Store original value in Key Vault
    secret_client.set_secret(token_id, data["customer_email"])

    # Replace with token
    data["customer_email"] = token_id
    return data

def detokenize_pii(data: dict) -> dict:
    """Replace tokens with original PII from Key Vault"""
    token_id = data["customer_email"]
    if token_id.startswith("TOKEN_"):
        original_value = secret_client.get_secret(token_id).value
        data["customer_email"] = original_value
    return data
```

---

## Disaster Recovery

### RPO/RTO Targets

- **RPO** (Recovery Point Objective): 1 hour (max data loss)
- **RTO** (Recovery Time Objective): 4 hours (max downtime)

### Backup Strategy

**Cosmos DB**:
- Continuous backup (30-day point-in-time restore)
- Test restore monthly

**Terraform State**:
- Azure Blob Storage with versioning
- 30-day retention
- Weekly manual backup to separate storage account

**Container Images**:
- All production images retained indefinitely
- Tagged with version + commit SHA

**Azure Key Vault**:
- Soft-delete (90 days)
- Purge protection enabled

### DR Testing Schedule

- **Monthly**: Cosmos DB restore validation
- **Quarterly**: Full Terraform destroy/rebuild drill
- **Annually**: Tabletop exercise for all 5 DR scenarios

### DR Drill Procedure

```bash
# Quarterly DR Drill: Full environment rebuild

# 1. Document current state
terraform show > pre-drill-state.txt
az resource list > pre-drill-resources.txt

# 2. Destroy all resources (CAUTION: Only in DR drill)
terraform destroy -auto-approve

# 3. Wait 5 minutes (simulate disaster recovery delay)
sleep 300

# 4. Rebuild from Terraform
terraform init
terraform apply -auto-approve

# 5. Restore Cosmos DB data
az cosmosdb mongodb database restore \
  --account-name cosmos-multi-agent \
  --name orders \
  --restore-timestamp "2026-01-25T12:00:00Z"

# 6. Redeploy agents
az container create --resource-group multi-agent-rg ...

# 7. Run smoke tests
pytest tests/e2e/test_scenarios.py::test_S001_greeting -v

# 8. Document recovery time
echo "Recovery completed in X minutes" > dr-drill-results.txt

# 9. Compare state
terraform show > post-drill-state.txt
diff pre-drill-state.txt post-drill-state.txt
```

---

## Troubleshooting

### Common Phase 4 Issues

**See TROUBLESHOOTING-GUIDE.md for comprehensive troubleshooting**

**Azure-Specific Issues**:

1. **Terraform Apply Fails**
   - Check Service Principal permissions
   - Verify subscription quota limits
   - Review Terraform logs for specific error

2. **Container Instance Won't Start**
   - Check image pull permissions (ACR credentials)
   - Verify environment variables set correctly
   - Review container logs: `az container logs --name intent-classifier`

3. **Azure OpenAI Rate Limiting**
   - Error: `429 Too Many Requests`
   - Solution: Implement exponential backoff, request queuing

4. **Cosmos DB High Latency**
   - Symptom: P95 > 100ms for PII tokenization
   - Solution: Fallback to Cosmos DB if Key Vault slow

5. **Budget Alert Firing**
   - Check Azure Cost Management for unexpected charges
   - Review resource usage in Azure Portal
   - Scale down non-essential resources

---

**Document Status**: Phase 4 Preparation
**Maintained By**: Development Team
**Next Review**: Phase 4 Kickoff
**Feedback**: GitHub Issues or deployment@remaker.digital

---

**Version History**:
- v1.0 (2026-01-25): Initial release for Phase 3 completion, Phase 4 preparation
