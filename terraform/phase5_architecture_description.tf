# Phase 5: Multi-Agent Customer Service Platform - Azure Production Architecture
# Region: East US
# Budget: $310-360/month (Phase 4-5), optimize to $200-250/month post-Phase 5
# Purpose: Educational example - cost-optimized multi-agent AI system using AGNTCY SDK
# Updated: 2026-01-22 - Added Critic/Supervisor Agent (6th agent) + Execution Tracing

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

  # Stores 6 agent images + 4 mock API images (REVISED 2026-01-22)
  # Images tagged with version + commit SHA
  # NEW: critic-supervisor agent added

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

# Critic/Supervisor Agent (NEW 2026-01-22)
resource "azurerm_container_group" "critic_supervisor" {
  name                = "aci-critic-supervisor"
  location            = "eastus"
  os_type             = "Linux"
  subnet_ids          = [azurerm_subnet.container_subnet.id]

  container {
    name   = "critic-supervisor"
    image  = "acrcustomerserviceprod.azurecr.io/critic-supervisor:v1.0.0"
    cpu    = "0.5"
    memory = "1.0"

    ports {
      port     = 8080
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_ENDPOINT           = azurerm_container_group.slim_gateway.ip_address
      AZURE_OPENAI_ENDPOINT   = "https://customerservice-openai.openai.azure.com/"
      VALIDATION_MODEL        = "gpt-4o-mini"  # Cost-effective validation
      AZURE_KEYVAULT_ENDPOINT = azurerm_key_vault.main.vault_uri
      OTLP_ENDPOINT          = azurerm_monitor_workspace.main.endpoint
      MAX_REGENERATE_ATTEMPTS = "3"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  restart_policy = "Always"

  # Validates all input (customer messages) and output (AI responses)
  # Content policies: prompt injection, profanity, PII leaks, harmful content
  # Strategy: Block and regenerate (max 3 attempts), escalate if all fail

  # Cost: ~$15-20/month (container) + ~$5-8/month (GPT-4o-mini API calls)
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

  # Stores:
  # - Container logs (6 agents + SLIM gateway)
  # - OpenTelemetry execution traces (50% sampling, PII tokenized)
  # - Application Insights telemetry
  # - Azure Monitor metrics

  # Cost: ~$15-25/month (pay per GB ingested, 7-day retention)
  # REVISED 2026-01-22: Increased from $5-10 to account for trace ingestion
}

resource "azurerm_application_insights" "main" {
  name                = "appi-customerservice-prod"
  location            = "eastus"
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  sampling_percentage = 50  # 50% sampling to reduce costs (smart sampling)

  # Collects:
  # - Agent performance metrics (response time, routing accuracy)
  # - Container health and resource usage
  # - Application logs and traces
  # - Custom KPI metrics (automation rate, CSAT, etc.)
  # - OpenTelemetry execution traces (full decision tree for all 6 agents)
  # - Content validation metrics (Critic/Supervisor block rate, false positives)

  # REVISED 2026-01-22: Added 50% sampling for trace ingestion cost optimization
  # Cost: ~$6-8/month (included in Log Analytics, but drives ingestion volume)
}

resource "azurerm_monitor_workspace" "main" {
  name     = "amw-customerservice-prod"
  location = "eastus"

  # OpenTelemetry endpoint for AGNTCY SDK tracing
  # All 6 agents send execution traces here (via OTLP protocol)
  # Traces include: agent name, action, inputs (PII tokenized), outputs, reasoning, latency, cost
  # Visualization: Timeline view, decision tree diagram, searchable logs in Grafana

  # REVISED 2026-01-22: Now receives traces from 6 agents (was 5)
  # Cost: ~$10-15/month (managed Prometheus + increased trace volume)
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

# Budget alert at 83% ($299) - REVISED 2026-01-22
resource "azurerm_consumption_budget_resource_group" "alert_83_percent" {
  name              = "budget-alert-83percent"
  resource_group_id = azurerm_resource_group.main.id
  amount            = 360  # Phase 4-5 revised budget
  time_grain        = "Monthly"

  notification {
    enabled        = true
    threshold      = 83
    operator       = "GreaterThan"
    contact_emails = ["admin@example.com"]
  }
}

# Budget alert at 93% ($335) - REVISED 2026-01-22
resource "azurerm_consumption_budget_resource_group" "alert_93_percent" {
  name              = "budget-alert-93percent"
  resource_group_id = azurerm_resource_group.main.id
  amount            = 360  # Phase 4-5 revised budget
  time_grain        = "Monthly"

  notification {
    enabled        = true
    threshold      = 93
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
# - Used by: Response Generation Agents (all 3 languages), Intent Classification, Critic/Supervisor
# - Purpose: LLM-powered response generation and content validation
# - Models:
#   - GPT-4o: Response generation (customer-facing, high quality)
#   - GPT-4o-mini: Intent classification + Critic/Supervisor validation (cost-effective)
#   - text-embedding-3-large: Knowledge retrieval (RAG embeddings)
# - Cost: ~$48-62/month (token-based, variable) - REVISED 2026-01-22

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
# - Agents: 6 total (Intent, Knowledge, Response x3, Escalation, Analytics, Critic/Supervisor)
# - Minimum instances: 1 per agent (always-on)
# - Maximum instances: 3 per agent (peak load)
# - Scale-up trigger: CPU >70% for 5 minutes
# - Scale-down trigger: CPU <30% for 10 minutes
# - REVISED 2026-01-22: Added Critic/Supervisor agent to scaling policy

# Auto-Shutdown Schedule (via Azure Automation):
# - Weekdays: 2am-6am ET (low-traffic hours) - scale to 1 instance
# - Weekends: No auto-shutdown (maintain baseline availability)
# - Holiday override: Manual scale-down

# Log Retention Cost Optimization:
# - Application Insights: 7 days (not 30)
# - OpenTelemetry execution traces: 7 days (50% sampling, PII tokenized)
# - Cosmos DB query logs: Disabled (not needed)
# - Container logs: 7 days in Log Analytics
# - REVISED 2026-01-22: Added trace retention policy

# ============================================================================
# ESTIMATED MONTHLY COSTS (Phase 5) - REVISED 2026-01-22
# ============================================================================

# Application Gateway:              ~$25-30
# Container Instances (9 total):    ~$135-160
#   - Intent Classification:        ~$15-20
#   - Knowledge Retrieval:          ~$15-20
#   - Response Gen EN:              ~$18-25
#   - Response Gen FR-CA:           ~$18-25
#   - Response Gen ES:              ~$18-25
#   - Escalation:                   ~$15-20
#   - Analytics:                    ~$15-20
#   - Critic/Supervisor (NEW):      ~$15-20
#   - SLIM Gateway:                 ~$30-40
# Cosmos DB Serverless:             ~$15-30
# Container Registry (Basic):       ~$5
# Key Vault (Standard):             ~$0.30
# Log Analytics (7-day):            ~$15-25 (increased for trace ingestion)
# Application Insights:             ~$6-8 (50% sampling)
# Monitor Workspace:                ~$10-15 (increased for 6 agents)
# Storage Account (TF state):       ~$2-3
# Public IP:                        ~$3-5
# Azure OpenAI:                     ~$48-62 (variable, includes validation)
# Zendesk (if paid):                ~$0-19 (trial/sandbox preferred)
# Networking (VNet, egress):        ~$5-10
# Headroom (buffer):                ~$20-35
# -------------------------------------------------
# TOTAL:                            ~$310-360/month
# TARGET (Phase 4-5):               $310-360/month
# TARGET (Post Phase 5):            $200-250/month (via optimization)

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
    AgentCount  = "6"  # REVISED 2026-01-22: Added Critic/Supervisor
    Budget      = "310-360"  # Monthly budget in USD
    Updated     = "2026-01-22"
  }
}

# ============================================================================
# NEW CAPABILITIES (Added 2026-01-22)
# ============================================================================

# 1. CRITIC/SUPERVISOR AGENT (6th Agent)
#    - Purpose: Content validation for all input/output
#    - Input validation: Prompt injection, jailbreak attempts, malicious instructions
#    - Output validation: Profanity, PII leaks, harmful content, brand guidelines
#    - Strategy: Block and regenerate (max 3 attempts), escalate if all fail
#    - Model: GPT-4o-mini (cost-effective validation)
#    - Performance: <200ms P95 latency, <5% false positive rate
#    - Cost: ~$22-31/month (container + API calls)
#    - Documentation: docs/critic-supervisor-agent-requirements.md
#    - GitHub Issue: #144

# 2. EXECUTION TRACING & OBSERVABILITY
#    - Purpose: Full decision tree visibility for debugging and audit
#    - Instrumentation: OpenTelemetry SDK integrated into AGNTCY factory
#    - Trace format: Spans with agent name, action, inputs (PII tokenized), outputs, reasoning, latency, cost
#    - Visualization: Timeline view, decision tree diagram, searchable logs
#    - Retention: 7 days (cost optimized), exportable for long-term analysis
#    - Sampling: 50% (probabilistic) to reduce ingestion costs
#    - Performance: <50ms overhead for trace instrumentation
#    - Cost: ~$10-15/month (Application Insights + Monitor Workspace)
#    - Documentation: docs/execution-tracing-observability-requirements.md
#    - GitHub Issue: #145

# 3. REVISED BUDGET JUSTIFICATION
#    - Original budget: $200/month
#    - Phase 2-5 enhancements: +$65-100/month (PII tokenization, events, RAG, multi-store)
#    - Critic/Supervisor: +$22-31/month
#    - Execution Tracing: +$10-15/month
#    - Total increase: +$110-160/month (55-80% from original)
#    - New target: $310-360/month (Phase 4-5)
#    - Post Phase 5 optimization: $200-250/month (via agent consolidation, aggressive scaling, model optimization)
#    - ROI: Positive from day 1 (saves $2,100-2,700/month vs. human agents)
#    - Documentation: docs/BUDGET-SUMMARY.md
