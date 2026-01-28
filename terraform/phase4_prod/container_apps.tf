# ============================================================================
# Azure Container Apps - Auto-Scaling Infrastructure
# ============================================================================
# Purpose: Deploy Container Apps with KEDA-based auto-scaling to support
# 10,000 daily users with horizontal scaling, load balancing, and scale-to-zero.
#
# Why Container Apps instead of Container Instances?
# - Native KEDA-based auto-scaling (HTTP triggers, CPU, custom metrics)
# - Scale-to-zero capability for cost optimization (~$0.036/vCPU-hour)
# - Built-in load balancing via Envoy proxy
# - Managed revision deployments for zero-downtime updates
# - See: docs/AUTO-SCALING-ARCHITECTURE.md for full analysis
#
# Architecture Overview:
# ┌─────────────────────────────────────────────────────────────────┐
# │              Container Apps Environment (agntcy-cs-prod-cae)    │
# │  ┌─────────────────────────────────────────────────────────┐   │
# │  │                    Ingress (HTTPS)                       │   │
# │  │         agntcy-cs-prod.azurecontainerapps.io            │   │
# │  └────────────────────────┬────────────────────────────────┘   │
# │                           │                                     │
# │  ┌────────────────────────▼────────────────────────────────┐   │
# │  │              API Gateway Container App                   │   │
# │  │              (Scale: 1-10 replicas)                     │   │
# │  └────────────────────────┬────────────────────────────────┘   │
# │                           │                                     │
# │  ┌────────────────────────▼────────────────────────────────┐   │
# │  │                   Agent Container Apps                   │   │
# │  │  Intent(0-5) Response(0-8) Critic(0-5) Escalation(0-3) │   │
# │  └─────────────────────────────────────────────────────────┘   │
# └─────────────────────────────────────────────────────────────────┘
#
# Cost Impact:
# - Off-peak (scale-to-zero): ~$80-130/month
# - Normal load: ~$230-350/month
# - Peak (10K users): ~$350-600/month
# - See: docs/AUTO-SCALING-WORK-ITEM-EVALUATION.md
#
# Related Documentation:
# - Azure Container Apps: https://learn.microsoft.com/azure/container-apps/
# - KEDA Scalers: https://keda.sh/docs/scalers/
# - Terraform ACA: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/container_app
# ============================================================================

# Enable Container Apps deployment via feature flag
# Set enable_container_apps = true in terraform.tfvars to activate
variable "enable_container_apps" {
  description = "Enable Container Apps deployment (replaces Container Instances)"
  type        = bool
  default     = true  # ENABLED 2026-01-27: Deploy Container Apps for 10K users scaling
}

# ============================================================================
# Container Apps Environment
# ============================================================================
# The environment provides shared infrastructure for all Container Apps:
# - Networking (VNet integration)
# - Log Analytics workspace
# - Internal DNS resolution
# ============================================================================

resource "azurerm_container_app_environment" "main" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-cae"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name

  # Use existing Log Analytics workspace
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  # VNet integration for private networking
  # Container Apps requires dedicated subnet with Microsoft.App/environments delegation
  # See: networking.tf for subnet configuration
  infrastructure_subnet_id = azurerm_subnet.container_apps[0].id

  # Zone redundancy disabled for cost optimization
  # Enable in production for HA (adds ~30% cost)
  zone_redundancy_enabled = false

  tags = merge(local.common_tags, {
    component = "container-apps-environment"
    purpose   = "auto-scaling-infrastructure"
  })

  lifecycle {
    # Prevent accidental deletion
    prevent_destroy = false  # Set to true in production
  }
}

# ============================================================================
# API Gateway Container App
# ============================================================================
# Entry point for all traffic. Scales based on HTTP concurrent requests.
# Critical path - should not scale to zero in production.
# ============================================================================

resource "azurerm_container_app" "api_gateway" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "${local.name_prefix}-api-gateway"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "api-gateway"
      image  = "${azurerm_container_registry.main.login_server}/api-gateway:v1.1.2-openai"
      cpu    = 0.5
      memory = "1Gi"

      # Environment variables
      env {
        name  = "API_PORT"
        value = "8080"
      }
      env {
        name  = "API_HOST"
        value = "0.0.0.0"
      }
      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-key"
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-02-15-preview"
      }
      env {
        name  = "AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT"
        value = var.gpt4o_mini_deployment
      }
      env {
        name  = "AZURE_OPENAI_GPT4O_DEPLOYMENT"
        value = var.gpt4o_deployment
      }
      env {
        name  = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        value = var.embedding_deployment
      }

      # Liveness probe
      # Note: initial_delay not supported in azurerm provider v3.x
      # Container Apps use default initial delay based on transport type
      liveness_probe {
        path             = "/health"
        port             = 8080
        transport        = "HTTP"
        interval_seconds = 30
        timeout          = 3
        failure_count_threshold = 3
      }

      # Readiness probe
      readiness_probe {
        path             = "/health"
        port             = 8080
        transport        = "HTTP"
        interval_seconds = 10
        timeout          = 3
        success_count_threshold = 1
        failure_count_threshold = 3
      }
    }

    # Auto-scaling configuration
    # Critical path: minReplicas=1 to avoid cold start on first request
    min_replicas = 1
    max_replicas = 10

    # HTTP-based scaling: scale up when concurrent requests exceed threshold
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "10"  # Scale up when >10 concurrent requests per replica
    }
  }

  # Secrets for sensitive configuration
  secret {
    name  = "azure-openai-endpoint"
    value = var.azure_openai_endpoint
  }
  secret {
    name  = "azure-openai-key"
    value = var.azure_openai_api_key
  }

  # Public ingress configuration
  ingress {
    external_enabled = true
    target_port      = 8080
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # Registry credentials
  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  tags = merge(local.common_tags, {
    component = "api-gateway"
    scaling   = "http-based"
  })
}

# ============================================================================
# Intent Classifier Container App
# ============================================================================
# Classifies customer intent. Fast, stateless - can scale to zero.
# ============================================================================

resource "azurerm_container_app" "intent_classifier" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "${local.name_prefix}-intent"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "intent-classifier"
      image  = "${azurerm_container_registry.main.login_server}/intent-classifier:v1.1.0-openai"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-key"
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-02-15-preview"
      }
      env {
        name  = "AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT"
        value = var.gpt4o_mini_deployment
      }
    }

    # Scale to zero during off-peak for cost optimization
    min_replicas = 0
    max_replicas = 5

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "5"
    }
  }

  secret {
    name  = "azure-openai-endpoint"
    value = var.azure_openai_endpoint
  }
  secret {
    name  = "azure-openai-key"
    value = var.azure_openai_api_key
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  tags = merge(local.common_tags, {
    component = "intent-classifier"
    scaling   = "scale-to-zero"
  })
}

# ============================================================================
# Critic/Supervisor Container App
# ============================================================================
# Content validation. Must match Intent scaling for request flow.
# ============================================================================

resource "azurerm_container_app" "critic_supervisor" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "${local.name_prefix}-critic"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "critic-supervisor"
      image  = "${azurerm_container_registry.main.login_server}/critic-supervisor:v1.1.0-openai"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-key"
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-02-15-preview"
      }
      env {
        name  = "AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT"
        value = var.gpt4o_mini_deployment
      }
    }

    min_replicas = 0
    max_replicas = 5

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "5"
    }
  }

  secret {
    name  = "azure-openai-endpoint"
    value = var.azure_openai_endpoint
  }
  secret {
    name  = "azure-openai-key"
    value = var.azure_openai_api_key
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  tags = merge(local.common_tags, {
    component = "critic-supervisor"
    scaling   = "scale-to-zero"
  })
}

# ============================================================================
# Response Generator Container App
# ============================================================================
# Most resource-intensive agent. Higher scale limit for throughput.
# ============================================================================

resource "azurerm_container_app" "response_generator" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "${local.name_prefix}-response"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "response-generator"
      image  = "${azurerm_container_registry.main.login_server}/response-generator:v1.1.0-openai"
      cpu    = 1.0    # Higher CPU for response generation
      memory = "2Gi"  # More memory for larger context windows

      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-key"
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-02-15-preview"
      }
      env {
        name  = "AZURE_OPENAI_GPT4O_DEPLOYMENT"
        value = var.gpt4o_deployment
      }
    }

    # Higher max for response generation (most resource-intensive)
    min_replicas = 0
    max_replicas = 8

    # CPU-based scaling for compute-intensive operations
    custom_scale_rule {
      name             = "cpu-scaling"
      custom_rule_type = "cpu"
      metadata = {
        type  = "Utilization"
        value = "70"  # Scale up at 70% CPU utilization
      }
    }
  }

  secret {
    name  = "azure-openai-endpoint"
    value = var.azure_openai_endpoint
  }
  secret {
    name  = "azure-openai-key"
    value = var.azure_openai_api_key
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  tags = merge(local.common_tags, {
    component = "response-generator"
    scaling   = "cpu-based"
  })
}

# ============================================================================
# Escalation Container App
# ============================================================================
# Handles escalation routing. Lower volume, fewer instances needed.
# ============================================================================

resource "azurerm_container_app" "escalation" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "${local.name_prefix}-escalation"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "escalation"
      image  = "${azurerm_container_registry.main.login_server}/escalation:v1.1.0-openai"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-key"
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-02-15-preview"
      }
      env {
        name  = "AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT"
        value = var.gpt4o_mini_deployment
      }
    }

    # Lower scale for escalation (typically ~10% of traffic)
    min_replicas = 0
    max_replicas = 3

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "10"
    }
  }

  secret {
    name  = "azure-openai-endpoint"
    value = var.azure_openai_endpoint
  }
  secret {
    name  = "azure-openai-key"
    value = var.azure_openai_api_key
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  tags = merge(local.common_tags, {
    component = "escalation"
    scaling   = "scale-to-zero"
  })
}

# ============================================================================
# Knowledge Retrieval Container App
# ============================================================================
# RAG queries. Lower volume, depends on product/policy questions.
# ============================================================================

resource "azurerm_container_app" "knowledge_retrieval" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "${local.name_prefix}-knowledge"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "knowledge-retrieval"
      image  = "${azurerm_container_registry.main.login_server}/knowledge-retrieval:v1.1.1-fix"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-key"
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = "2024-02-15-preview"
      }
      env {
        name  = "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        value = var.embedding_deployment
      }
    }

    min_replicas = 0
    max_replicas = 3

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "10"
    }
  }

  secret {
    name  = "azure-openai-endpoint"
    value = var.azure_openai_endpoint
  }
  secret {
    name  = "azure-openai-key"
    value = var.azure_openai_api_key
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  tags = merge(local.common_tags, {
    component = "knowledge-retrieval"
    scaling   = "scale-to-zero"
  })
}

# ============================================================================
# Analytics Container App
# ============================================================================
# Batch processing for metrics. Lowest priority, scale to zero.
# ============================================================================

resource "azurerm_container_app" "analytics" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "${local.name_prefix}-analytics"
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "analytics"
      image  = "${azurerm_container_registry.main.login_server}/analytics:v1.1.0-openai"
      cpu    = 0.25  # Lower CPU for batch processing
      memory = "0.5Gi"

      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "azure-openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-key"
      }
    }

    # Lowest priority - aggressive scale-to-zero
    min_replicas = 0
    max_replicas = 2

    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "20"  # Higher threshold for batch
    }
  }

  secret {
    name  = "azure-openai-endpoint"
    value = var.azure_openai_endpoint
  }
  secret {
    name  = "azure-openai-key"
    value = var.azure_openai_api_key
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  tags = merge(local.common_tags, {
    component = "analytics"
    scaling   = "batch-processing"
  })
}

# ============================================================================
# Scheduled Scaling Configuration (WI-5)
# ============================================================================
# Time-based scaling profiles to optimize costs during off-peak hours.
#
# Schedule (EST/EDT):
# - Business Hours (8am-6pm): Full scaling capacity
# - Evening (6pm-10pm): Moderate capacity (50% reduction in max)
# - Night (10pm-6am): Minimal capacity (API Gateway only)
# - Weekend: Reduced baseline throughout
#
# Note: Azure Container Apps doesn't have native scheduled scaling.
# Use Azure Logic Apps or Azure Functions to update min_replicas via API.
# This section defines the scaling rules that will be applied by the scheduler.
#
# Implementation Option: Azure Automation Account with PowerShell Runbook
# See: docs/RUNBOOK-AUTO-SCALING-OPERATIONS.md
# ============================================================================

# Variables for scheduled scaling profiles
variable "enable_scheduled_scaling" {
  description = "Enable time-based scaling profiles"
  type        = bool
  default     = true  # ENABLED 2026-01-27: Deploy scheduled scaling for cost optimization
}

variable "scheduled_scaling_timezone" {
  description = "Timezone for scheduled scaling (IANA format)"
  type        = string
  default     = "America/New_York"
}

# Logic App for scheduled scaling automation
resource "azurerm_logic_app_workflow" "scaling_scheduler" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  name                = "${local.name_prefix}-scaling-scheduler"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name

  # Note: Logic App definition will be configured via ARM template or Azure portal
  # This creates the shell for the automation workflow

  tags = merge(local.common_tags, {
    component = "scheduled-scaling"
    purpose   = "cost-optimization"
  })
}

# Automation Account for PowerShell-based scaling (alternative to Logic Apps)
resource "azurerm_automation_account" "scaling" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  name                = "${local.name_prefix}-scaling-automation"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku_name            = "Basic"  # Free tier for cost optimization

  identity {
    type = "SystemAssigned"
  }

  tags = merge(local.common_tags, {
    component = "scheduled-scaling"
    purpose   = "automation"
  })
}

# Role assignment for Automation Account to manage Container Apps
resource "azurerm_role_assignment" "automation_container_apps" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  scope                = data.azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_automation_account.scaling[0].identity[0].principal_id
}

# PowerShell Runbook: Scale to Business Hours Profile
resource "azurerm_automation_runbook" "scale_business_hours" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  name                    = "Scale-BusinessHours"
  location                = local.location
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  runbook_type            = "PowerShell"
  log_progress            = true
  log_verbose             = false

  content = <<-POWERSHELL
    # Scale-BusinessHours.ps1
    # Applies business hours scaling profile (8am-6pm EST)
    #
    # Profile: Full capacity for peak traffic
    # - API Gateway: minReplicas=2, maxReplicas=10
    # - Intent/Critic: minReplicas=1, maxReplicas=5
    # - Response: minReplicas=1, maxReplicas=8
    # - Others: minReplicas=0 (scale-to-zero enabled)

    param(
        [string]$ResourceGroup = "${data.azurerm_resource_group.main.name}",
        [string]$ContainerAppEnvironment = "${local.name_prefix}-cae"
    )

    # Connect using Managed Identity
    Connect-AzAccount -Identity

    Write-Output "Applying Business Hours scaling profile..."

    # API Gateway - always running during business hours
    az containerapp update `
        --name "${local.name_prefix}-api-gateway" `
        --resource-group $ResourceGroup `
        --min-replicas 2 `
        --max-replicas 10

    # Intent Classifier - warm start
    az containerapp update `
        --name "${local.name_prefix}-intent" `
        --resource-group $ResourceGroup `
        --min-replicas 1 `
        --max-replicas 5

    # Critic/Supervisor - warm start
    az containerapp update `
        --name "${local.name_prefix}-critic" `
        --resource-group $ResourceGroup `
        --min-replicas 1 `
        --max-replicas 5

    # Response Generator - warm start
    az containerapp update `
        --name "${local.name_prefix}-response" `
        --resource-group $ResourceGroup `
        --min-replicas 1 `
        --max-replicas 8

    Write-Output "Business Hours profile applied successfully."
  POWERSHELL

  tags = merge(local.common_tags, {
    profile = "business-hours"
  })
}

# PowerShell Runbook: Scale to Night Profile
resource "azurerm_automation_runbook" "scale_night" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  name                    = "Scale-Night"
  location                = local.location
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  runbook_type            = "PowerShell"
  log_progress            = true
  log_verbose             = false

  content = <<-POWERSHELL
    # Scale-Night.ps1
    # Applies night scaling profile (10pm-6am EST)
    #
    # Profile: Minimal capacity for cost optimization
    # - API Gateway: minReplicas=1, maxReplicas=3
    # - All others: minReplicas=0 (full scale-to-zero)

    param(
        [string]$ResourceGroup = "${data.azurerm_resource_group.main.name}",
        [string]$ContainerAppEnvironment = "${local.name_prefix}-cae"
    )

    # Connect using Managed Identity
    Connect-AzAccount -Identity

    Write-Output "Applying Night scaling profile..."

    # API Gateway - minimal
    az containerapp update `
        --name "${local.name_prefix}-api-gateway" `
        --resource-group $ResourceGroup `
        --min-replicas 1 `
        --max-replicas 3

    # All other agents - scale to zero
    $agents = @("intent", "critic", "response", "escalation", "knowledge", "analytics")
    foreach ($agent in $agents) {
        az containerapp update `
            --name "${local.name_prefix}-$agent" `
            --resource-group $ResourceGroup `
            --min-replicas 0 `
            --max-replicas 2
    }

    Write-Output "Night profile applied successfully."
  POWERSHELL

  tags = merge(local.common_tags, {
    profile = "night"
  })
}

# PowerShell Runbook: Scale to Weekend Profile
resource "azurerm_automation_runbook" "scale_weekend" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  name                    = "Scale-Weekend"
  location                = local.location
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  runbook_type            = "PowerShell"
  log_progress            = true
  log_verbose             = false

  content = <<-POWERSHELL
    # Scale-Weekend.ps1
    # Applies weekend scaling profile (Sat-Sun)
    #
    # Profile: Reduced capacity (50% of business hours max)
    # - API Gateway: minReplicas=1, maxReplicas=5
    # - Intent/Critic: minReplicas=0, maxReplicas=3
    # - Response: minReplicas=0, maxReplicas=4
    # - Others: minReplicas=0, maxReplicas=2

    param(
        [string]$ResourceGroup = "${data.azurerm_resource_group.main.name}",
        [string]$ContainerAppEnvironment = "${local.name_prefix}-cae"
    )

    # Connect using Managed Identity
    Connect-AzAccount -Identity

    Write-Output "Applying Weekend scaling profile..."

    # API Gateway - reduced
    az containerapp update `
        --name "${local.name_prefix}-api-gateway" `
        --resource-group $ResourceGroup `
        --min-replicas 1 `
        --max-replicas 5

    # Intent Classifier - 50% reduction
    az containerapp update `
        --name "${local.name_prefix}-intent" `
        --resource-group $ResourceGroup `
        --min-replicas 0 `
        --max-replicas 3

    # Critic/Supervisor - 50% reduction
    az containerapp update `
        --name "${local.name_prefix}-critic" `
        --resource-group $ResourceGroup `
        --min-replicas 0 `
        --max-replicas 3

    # Response Generator - 50% reduction
    az containerapp update `
        --name "${local.name_prefix}-response" `
        --resource-group $ResourceGroup `
        --min-replicas 0 `
        --max-replicas 4

    Write-Output "Weekend profile applied successfully."
  POWERSHELL

  tags = merge(local.common_tags, {
    profile = "weekend"
  })
}

# Schedule: Business Hours Start (8am EST weekdays)
resource "azurerm_automation_schedule" "business_hours_start" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  name                    = "BusinessHoursStart"
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  frequency               = "Week"
  interval                = 1
  timezone                = var.scheduled_scaling_timezone
  start_time              = "2026-01-28T08:00:00-05:00"  # 8am EST

  week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
}

# Schedule: Night Start (10pm EST daily)
resource "azurerm_automation_schedule" "night_start" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  name                    = "NightStart"
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  frequency               = "Day"
  interval                = 1
  timezone                = var.scheduled_scaling_timezone
  start_time              = "2026-01-27T22:00:00-05:00"  # 10pm EST
}

# Schedule: Weekend Start (Saturday 12am EST)
resource "azurerm_automation_schedule" "weekend_start" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  name                    = "WeekendStart"
  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  frequency               = "Week"
  interval                = 1
  timezone                = var.scheduled_scaling_timezone
  start_time              = "2026-02-01T00:00:00-05:00"  # Saturday 12am EST (future date required)

  week_days = ["Saturday"]
}

# Link runbooks to schedules
resource "azurerm_automation_job_schedule" "business_hours" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  schedule_name           = azurerm_automation_schedule.business_hours_start[0].name
  runbook_name            = azurerm_automation_runbook.scale_business_hours[0].name
}

resource "azurerm_automation_job_schedule" "night" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  schedule_name           = azurerm_automation_schedule.night_start[0].name
  runbook_name            = azurerm_automation_runbook.scale_night[0].name
}

resource "azurerm_automation_job_schedule" "weekend" {
  count = var.enable_container_apps && var.enable_scheduled_scaling ? 1 : 0

  resource_group_name     = data.azurerm_resource_group.main.name
  automation_account_name = azurerm_automation_account.scaling[0].name
  schedule_name           = azurerm_automation_schedule.weekend_start[0].name
  runbook_name            = azurerm_automation_runbook.scale_weekend[0].name
}

# ============================================================================
# Outputs
# ============================================================================

output "container_apps_environment_id" {
  description = "Container Apps Environment ID"
  value       = var.enable_container_apps ? azurerm_container_app_environment.main[0].id : null
}

output "api_gateway_url" {
  description = "API Gateway public URL"
  value       = var.enable_container_apps ? "https://${azurerm_container_app.api_gateway[0].ingress[0].fqdn}" : null
}

output "container_apps_enabled" {
  description = "Whether Container Apps are enabled"
  value       = var.enable_container_apps
}

output "scheduled_scaling_enabled" {
  description = "Whether scheduled scaling is enabled"
  value       = var.enable_container_apps && var.enable_scheduled_scaling
}

output "automation_account_id" {
  description = "Automation Account ID for scheduled scaling"
  value       = var.enable_container_apps && var.enable_scheduled_scaling ? azurerm_automation_account.scaling[0].id : null
}
