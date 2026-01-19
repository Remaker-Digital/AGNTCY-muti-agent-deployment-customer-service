# Phase 5: Multi-Agent Customer Service Platform - Azure Production Architecture
# Region: East US
# Budget: $200/month maximum
# Purpose: Educational example - cost-optimized multi-agent AI system using AGNTCY SDK

# ============================================================================
# NETWORKING & SECURITY
# ============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-customerservice-prod"
  location            = "eastus"
  address_space       = ["10.0.0.0/16"]

  # Cost: $0 (VNet is free)
}

resource "azurerm_subnet" "container_subnet" {
  name                 = "subnet-containers"
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  # Delegated to Container Instances
  delegation {
    name = "aci-delegation"
    service_delegation {
      name = "Microsoft.ContainerInstance/containerGroups"
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "subnet-privateendpoints"
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]

  # For Cosmos DB, Key Vault private endpoints
}

resource "azurerm_network_security_group" "container_nsg" {
  name     = "nsg-containers"
  location = "eastus"

  # Only allow HTTPS inbound from Application Gateway
  security_rule {
    name                       = "allow-https-from-appgw"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "10.0.3.0/24"
    destination_address_prefix = "10.0.1.0/24"
  }
}

resource "azurerm_subnet" "appgw_subnet" {
  name                 = "subnet-appgw"
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]
}

# ============================================================================
# APPLICATION GATEWAY (Ingress)
# ============================================================================

resource "azurerm_public_ip" "appgw_public_ip" {
  name              = "pip-appgw-customerservice"
  location          = "eastus"
  allocation_method = "Static"
  sku               = "Standard"

  # Cost: ~$3-5/month
}

resource "azurerm_application_gateway" "main" {
  name     = "appgw-customerservice-prod"
  location = "eastus"
  sku {
    name     = "Standard_v2"  # Basic tier
    tier     = "Standard_v2"
    capacity = 1              # Auto-scale 1-2 instances
  }

  # TLS 1.3 termination
  # Routes to Intent Classification Agent
  # Health probes for all container instances

  # Cost: ~$20-30/month (smallest config)
}

# ============================================================================
# CONTAINER REGISTRY
# ============================================================================

resource "azurerm_container_registry" "main" {
  name                = "acrcustomerserviceprod"
  location            = "eastus"
  sku                 = "Basic"  # Not Premium - cost optimization
  admin_enabled       = false

  # Stores 5 agent images + 4 mock API images
  # Images tagged with version + commit SHA

  # Cost: ~$5/month (Basic tier)
}

# ============================================================================
# AGENT CONTAINER INSTANCES
# ============================================================================

# Intent Classification Agent
resource "azurerm_container_group" "intent_classifier" {
  name                = "aci-intent-classifier"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "intent-classifier"
    image  = "acrcustomerserviceprod.azurecr.io/intent-classifier:v1.0.0"
    cpu    = "0.5"  # 0.5 vCPU - minimal resources
    memory = "1.0"  # 1 GB RAM

    ports {
      port     = 8080
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_ENDPOINT           = azurerm_container_group.slim_gateway.ip_address
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
      LANGUAGE_SUPPORT       = "en,fr-ca,es"
    }
  }

  identity {
    type = "SystemAssigned"  # Managed identity for Key Vault access
  }

  # Auto-restart on failure
  restart_policy = "Always"

  # Cost: ~$15-20/month (0.5 vCPU + 1GB RAM, ~730 hrs/month)
}

# Knowledge Retrieval Agent
resource "azurerm_container_group" "knowledge_retrieval" {
  name                = "aci-knowledge-retrieval"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "knowledge-retrieval"
    image  = "acrcustomerserviceprod.azurecr.io/knowledge-retrieval:v1.0.0"
    cpu    = "0.5"
    memory = "1.0"

    ports {
      port     = 8080
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_ENDPOINT           = azurerm_container_group.slim_gateway.ip_address
      COSMOS_ENDPOINT         = azurerm_cosmosdb_account.main.endpoint
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
    }
  }

  identity {
    type = "SystemAssigned"
  }

  restart_policy = "Always"

  # Cost: ~$15-20/month
}

# Response Generation Agent (English)
resource "azurerm_container_group" "response_generator_en" {
  name                = "aci-response-generator-en"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "response-generator-en"
    image  = "acrcustomerserviceprod.azurecr.io/response-generator:v1.0.0"
    cpu    = "0.5"
    memory = "1.5"  # Slightly more memory for LLM responses

    ports {
      port     = 8080
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_ENDPOINT           = azurerm_container_group.slim_gateway.ip_address
      AZURE_OPENAI_ENDPOINT   = "https://customerservice-openai.openai.azure.com/"
      LANGUAGE                = "en"
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
    }
  }

  identity {
    type = "SystemAssigned"
  }

  restart_policy = "Always"

  # Cost: ~$18-25/month
}

# Response Generation Agent (French Canadian)
resource "azurerm_container_group" "response_generator_fr_ca" {
  name                = "aci-response-generator-fr-ca"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "response-generator-fr-ca"
    image  = "acrcustomerserviceprod.azurecr.io/response-generator:v1.0.0"
    cpu    = "0.5"
    memory = "1.5"

    ports {
      port     = 8080
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_ENDPOINT           = azurerm_container_group.slim_gateway.ip_address
      AZURE_OPENAI_ENDPOINT   = "https://customerservice-openai.openai.azure.com/"
      LANGUAGE                = "fr-ca"
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
    }
  }

  identity {
    type = "SystemAssigned"
  }

  restart_policy = "Always"

  # Cost: ~$18-25/month
}

# Response Generation Agent (Spanish)
resource "azurerm_container_group" "response_generator_es" {
  name                = "aci-response-generator-es"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "response-generator-es"
    image  = "acrcustomerserviceprod.azurecr.io/response-generator:v1.0.0"
    cpu    = "0.5"
    memory = "1.5"

    ports {
      port     = 8080
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_ENDPOINT           = azurerm_container_group.slim_gateway.ip_address
      AZURE_OPENAI_ENDPOINT   = "https://customerservice-openai.openai.azure.com/"
      LANGUAGE                = "es"
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
    }
  }

  identity {
    type = "SystemAssigned"
  }

  restart_policy = "Always"

  # Cost: ~$18-25/month
}

# Escalation Agent
resource "azurerm_container_group" "escalation" {
  name                = "aci-escalation"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "escalation"
    image  = "acrcustomerserviceprod.azurecr.io/escalation:v1.0.0"
    cpu    = "0.5"
    memory = "1.0"

    ports {
      port     = 8080
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_ENDPOINT           = azurerm_container_group.slim_gateway.ip_address
      ZENDESK_ENDPOINT        = "https://customerservice.zendesk.com/api/v2"
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
    }
  }

  identity {
    type = "SystemAssigned"
  }

  restart_policy = "Always"

  # Cost: ~$15-20/month
}

# Analytics Agent
resource "azurerm_container_group" "analytics" {
  name                = "aci-analytics"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "analytics"
    image  = "acrcustomerserviceprod.azurecr.io/analytics:v1.0.0"
    cpu    = "0.5"
    memory = "1.0"

    ports {
      port     = 8080
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_ENDPOINT           = azurerm_container_group.slim_gateway.ip_address
      COSMOS_ENDPOINT         = azurerm_cosmosdb_account.main.endpoint
      GA4_PROPERTY_ID         = "G-XXXXXXXXXX"
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
    }
  }

  identity {
    type = "SystemAssigned"
  }

  restart_policy = "Always"

  # Cost: ~$15-20/month
}

# ============================================================================
# AGNTCY SDK SLIM GATEWAY
# ============================================================================

resource "azurerm_container_group" "slim_gateway" {
  name                = "aci-slim-gateway"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "slim-gateway"
    image  = "agntcy/slim-gateway:latest"  # Official AGNTCY SLIM transport
    cpu    = "1.0"  # More resources for gateway
    memory = "2.0"

    ports {
      port     = 8443
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_TLS_ENABLED       = "true"
      SLIM_AUTH_ENABLED      = "true"
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
    }
  }

  identity {
    type = "SystemAssigned"
  }

  restart_policy = "Always"

  # Cost: ~$30-40/month (1 vCPU + 2GB RAM)
}

# ============================================================================
# DATA STORAGE
# ============================================================================

resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-customerservice-prod"
  location            = "eastus"
  offer_type          = "Standard"
  kind                = "NoSQL"

  # Serverless mode - pay-per-request (NOT provisioned RU/s)
  capabilities {
    name = "EnableServerless"
  }

  # Single region (no geo-replication - cost optimization)
  geo_location {
    location          = "eastus"
    failover_priority = 0
  }

  # Continuous backup for DR
  backup {
    type                = "Continuous"
    interval_in_minutes = 240
    retention_in_hours  = 720  # 30 days
  }

  # Network isolation
  is_virtual_network_filter_enabled = true
  virtual_network_rule {
    id = azurerm_subnet.private_endpoints.id
  }

  # Cost: ~$15-30/month (serverless, variable based on usage)
}

resource "azurerm_cosmosdb_sql_database" "conversations" {
  name                = "conversations"
  resource_group_name = azurerm_cosmosdb_account.main.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name

  # Stores conversation history, session state, routing metadata
}

resource "azurerm_cosmosdb_sql_container" "sessions" {
  name                = "sessions"
  database_name       = azurerm_cosmosdb_sql_database.conversations.name
  account_name        = azurerm_cosmosdb_account.main.name
  partition_key_path  = "/sessionId"

  # TTL enabled for auto-cleanup of old sessions (30 days)
  default_ttl = 2592000
}

resource "azurerm_cosmosdb_sql_container" "messages" {
  name                = "messages"
  database_name       = azurerm_cosmosdb_sql_database.conversations.name
  account_name        = azurerm_cosmosdb_account.main.name
  partition_key_path  = "/conversationId"

  # TTL enabled for auto-cleanup (90 days)
  default_ttl = 7776000
}

resource "azurerm_cosmosdb_sql_container" "analytics" {
  name                = "analytics"
  database_name       = azurerm_cosmosdb_sql_database.conversations.name
  account_name        = azurerm_cosmosdb_account.main.name
  partition_key_path  = "/metricDate"

  # Stores KPI metrics, agent performance data
}

# ============================================================================
# SECRETS MANAGEMENT
# ============================================================================

resource "azurerm_key_vault" "main" {
  name                = "kv-customerservice-prod"
  location            = "eastus"
  sku_name            = "standard"  # Not Premium - cost optimization

  # Soft-delete + purge protection for DR
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  # Network isolation
  network_acls {
    default_action = "Deny"
    virtual_network_subnet_ids = [
      azurerm_subnet.container_subnet.id,
      azurerm_subnet.private_endpoints.id
    ]
  }

  # Cost: ~$0.30/month (10,000 operations free tier)
}

# Secrets stored in Key Vault (accessed via Managed Identity):
# - SHOPIFY_API_KEY
# - SHOPIFY_API_SECRET
# - ZENDESK_API_TOKEN
# - MAILCHIMP_API_KEY
# - GOOGLE_ANALYTICS_SERVICE_ACCOUNT_KEY
# - AZURE_OPENAI_API_KEY
# - SLIM_GATEWAY_TLS_CERT
# - SLIM_GATEWAY_TLS_KEY

# ============================================================================
# OBSERVABILITY & MONITORING
# ============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-customerservice-prod"
  location            = "eastus"
  sku                 = "PerGB2018"
  retention_in_days   = 7  # Reduced from 30 days - cost optimization

  # Cost: ~$5-10/month (pay per GB ingested, 7-day retention)
}

resource "azurerm_application_insights" "main" {
  name                = "appi-customerservice-prod"
  location            = "eastus"
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  # Collects:
  # - Agent performance metrics (response time, routing accuracy)
  # - Container health and resource usage
  # - Application logs and traces
  # - Custom KPI metrics (automation rate, CSAT, etc.)

  # Cost: Included in Log Analytics workspace cost
}

resource "azurerm_monitor_workspace" "main" {
  name     = "amw-customerservice-prod"
  location = "eastus"

  # OpenTelemetry endpoint for AGNTCY SDK tracing
  # Cost: ~$2-5/month (managed Prometheus)
}

resource "azurerm_monitor_action_group" "budget_alerts" {
  name                = "ag-budget-alerts"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "budget"

  email_receiver {
    name          = "admin"
    email_address = "admin@example.com"
  }
}

# Budget alert at 80% ($160)
resource "azurerm_consumption_budget_resource_group" "alert_80_percent" {
  name              = "budget-alert-80percent"
  resource_group_id = azurerm_resource_group.main.id
  amount            = 200
  time_grain        = "Monthly"

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThan"
    contact_emails = ["admin@example.com"]
  }
}

# Budget alert at 95% ($190)
resource "azurerm_consumption_budget_resource_group" "alert_95_percent" {
  name              = "budget-alert-95percent"
  resource_group_id = azurerm_resource_group.main.id
  amount            = 200
  time_grain        = "Monthly"

  notification {
    enabled        = true
    threshold      = 95
    operator       = "GreaterThan"
    contact_emails = ["admin@example.com"]
  }
}

# ============================================================================
# EXTERNAL INTEGRATIONS (via MCP protocol)
# ============================================================================

# These are external SaaS services, not Azure resources
# Agents connect via HTTPS using API keys from Key Vault

# Shopify API
# - Endpoint: https://customerservice-store.myshopify.com/admin/api/2024-01
# - Used by: Knowledge Retrieval Agent
# - Purpose: Product catalog, order status, inventory
# - Cost: $0 (Partner Development Store)

# Zendesk API
# - Endpoint: https://customerservice.zendesk.com/api/v2
# - Used by: Escalation Agent
# - Purpose: Create tickets, assign to human agents
# - Cost: $0-49/month (Sandbox/Trial)

# Mailchimp API
# - Endpoint: https://us1.api.mailchimp.com/3.0
# - Used by: Analytics Agent (campaign tracking)
# - Purpose: Email campaign metrics, subscriber data
# - Cost: $0 (Free tier, <500 contacts)

# Google Analytics 4 API
# - Endpoint: https://analyticsdata.googleapis.com/v1beta
# - Used by: Analytics Agent
# - Purpose: Website traffic, conversion tracking
# - Cost: $0 (Standard GA4)

# Azure OpenAI Service
# - Endpoint: https://customerservice-openai.openai.azure.com/
# - Used by: Response Generation Agents (all 3 languages)
# - Purpose: LLM-powered response generation
# - Model: GPT-4 or GPT-3.5-turbo
# - Cost: ~$20-50/month (token-based, variable)

# ============================================================================
# DISASTER RECOVERY
# ============================================================================

# Terraform State Storage
resource "azurerm_storage_account" "terraform_state" {
  name                     = "sttfstatecustomerservice"
  location                 = "eastus"
  account_tier             = "Standard"
  account_replication_type = "LRS"  # Local redundancy only - cost optimization

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }
  }

  # Cost: ~$2-3/month (minimal storage)
}

resource "azurerm_storage_container" "terraform_state" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.terraform_state.name
  container_access_type = "private"
}

# Container Image Retention
# - All production images retained indefinitely in ACR
# - Tagged with semantic version + commit SHA
# - Enables rollback to any previous version

# ============================================================================
# CI/CD INTEGRATION
# ============================================================================

# Azure DevOps Service Connection
# - Used by: azure-pipelines.yml
# - Authentication: Service Principal with Contributor role
# - Permissions: ACR push, Container Instance deploy, Key Vault read

# Deployment Slots (simulated with Blue/Green container groups)
# - Blue: Current production containers
# - Green: New deployment for testing
# - Traffic cutover via Application Gateway backend pool update

# ============================================================================
# AUTO-SCALING & COST OPTIMIZATION
# ============================================================================

# Container Instance Auto-Scaling Strategy:
# - Minimum instances: 1 per agent (always-on)
# - Maximum instances: 3 per agent (peak load)
# - Scale-up trigger: CPU >70% for 5 minutes
# - Scale-down trigger: CPU <30% for 10 minutes

# Auto-Shutdown Schedule (via Azure Automation):
# - Weekdays: 2am-6am ET (low-traffic hours) - scale to 1 instance
# - Weekends: No auto-shutdown (maintain baseline availability)
# - Holiday override: Manual scale-down

# Log Retention Cost Optimization:
# - Application Insights: 7 days (not 30)
# - Cosmos DB query logs: Disabled (not needed)
# - Container logs: 7 days in Log Analytics

# ============================================================================
# ESTIMATED MONTHLY COSTS (Phase 5)
# ============================================================================

# Application Gateway:           ~$25-30
# Container Instances (8 total): ~$120-140
#   - 5 agents @ $15-25 each
#   - 3 response gen @ $18-25 each
#   - 1 SLIM gateway @ $30-40
# Cosmos DB Serverless:          ~$15-30
# Container Registry (Basic):    ~$5
# Key Vault (Standard):          ~$0.30
# Log Analytics (7-day):         ~$5-10
# Monitor Workspace:             ~$2-5
# Storage Account (TF state):    ~$2-3
# Public IP:                     ~$3-5
# Azure OpenAI:                  ~$20-50 (variable)
# Zendesk (if paid):             ~$0-49 (trial/sandbox preferred)
# -------------------------------------------------
# TOTAL:                         ~$180-220/month
# TARGET:                        <$200/month average

# ============================================================================
# RESOURCE TAGS (for cost allocation tracking)
# ============================================================================

locals {
  common_tags = {
    Project     = "CustomerService-MultiAgent"
    Environment = "Production"
    Phase       = "Phase5"
    ManagedBy   = "Terraform"
    CostCenter  = "Engineering"
    Owner       = "Platform-Team"
    Purpose     = "Educational-Example"
  }
}
