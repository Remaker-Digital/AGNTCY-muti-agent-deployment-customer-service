# ============================================================================
# Azure App Configuration - Operational Tuning Interface
# ============================================================================
# Purpose: Centralized configuration store for runtime settings that operators
#          can adjust without code deployments (confidence thresholds, throttling,
#          feature flags, A/B testing).
#
# Why App Configuration?
# - Dynamic updates: Agents poll for changes every 30 seconds (no restart needed)
# - Feature flags: Built-in support for gradual rollouts and A/B testing
# - Audit logging: All changes tracked in Azure Monitor Activity Log
# - Cost: ~$1.20/month (Free tier: 1,000 requests/day, Standard: $1.20/day)
#
# See: docs/PHASE-5-CONFIGURATION-INTERFACE.md for operational workflows
# See: CLAUDE.md for configuration management strategy
#
# Cost Impact: ~$1.20/month (Standard tier, <10% of budget)
# ============================================================================

# ============================================================================
# APP CONFIGURATION RESOURCE
# ============================================================================
# Standard tier chosen for:
# - Unlimited daily requests (Free tier limited to 1,000/day)
# - Private endpoint support (network security)
# - Replica support (disaster recovery)
#
# Cost: $1.20/day = ~$36/month
# Alternative: Free tier ($0) if <1,000 requests/day expected
# ============================================================================

resource "azurerm_app_configuration" "main" {
  count = var.enable_app_configuration ? 1 : 0

  name                = "appconfig-${local.name_prefix}-${random_string.suffix.result}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location

  # ============================================================================
  # SKU Selection
  # ============================================================================
  # Free: 1,000 requests/day, no private endpoints, no replicas
  # Standard: Unlimited requests, private endpoints, replicas available
  #
  # Recommendation: Start with Free, upgrade to Standard if:
  # - >1,000 config reads/day (6 agents × 2 reads/min × 8 hours = 5,760 reads)
  # - Private endpoint required for compliance
  # ============================================================================
  sku = "standard"

  # ============================================================================
  # Security Configuration
  # ============================================================================
  # Soft delete protects against accidental deletion
  # Purge protection prevents permanent deletion during retention period
  # ============================================================================
  soft_delete_retention_days = 7
  purge_protection_enabled   = false  # Set to true for production compliance

  # ============================================================================
  # Identity for Key Vault Integration
  # ============================================================================
  # Enables App Configuration to reference secrets from Key Vault
  # without exposing secret values in configuration
  # ============================================================================
  identity {
    type = "SystemAssigned"
  }

  # ============================================================================
  # Public Access
  # ============================================================================
  # Disabled for security - access via private endpoint or managed identity
  # Set to true for initial setup/debugging, then disable
  # ============================================================================
  public_network_access = "Enabled"  # Required for initial setup; consider disabling after private endpoint

  # Encryption uses Microsoft-managed keys (default)
  # Customer-managed keys available but add $0.03/key/month

  tags = merge(local.common_tags, {
    Component = "Configuration"
    Purpose   = "OperationalTuning"
  })
}

# ============================================================================
# CONFIGURATION SETTINGS - Agent Thresholds
# ============================================================================
# These settings control agent behavior and can be adjusted by operators
# without code deployments. Each setting includes:
# - Purpose explanation
# - Valid range
# - Tuning guidance
# - Default value rationale
# ============================================================================

# -----------------------------------------------------------------------------
# Intent Classification Thresholds
# -----------------------------------------------------------------------------
# Purpose: Controls when intent classification is considered confident enough
# Lower threshold = fewer escalations to humans, more automation
# Higher threshold = more human review, higher quality assurance
#
# History:
# - Initial: 0.7 (70% escalation rate in testing)
# - Tuned to 0.5 after Phase 3.5 evaluation (30% escalation rate)
# See: evaluation/results/intent-classification-results.md
# -----------------------------------------------------------------------------

resource "azurerm_app_configuration_key" "intent_confidence_threshold" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "intent:confidence_threshold"
  value = "0.5"
  label = "production"

  tags = {
    Category    = "AgentThresholds"
    Agent       = "IntentClassification"
    ValidRange  = "0.0-1.0"
    TunedDate   = "2026-01-25"
    TunedReason = "Reduce escalation rate from 70% to 30%"
  }

  # Wait for RBAC permissions to propagate before creating keys
  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "intent_max_tokens" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "intent:max_tokens"
  value = "100"
  label = "production"

  tags = {
    Category   = "AgentThresholds"
    Agent      = "IntentClassification"
    ValidRange = "50-500"
    Rationale  = "Intent classification needs minimal tokens"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

# -----------------------------------------------------------------------------
# Escalation Agent Thresholds
# -----------------------------------------------------------------------------
# Purpose: Controls when conversations are escalated to human support
# sentiment_threshold: -1.0 (very negative) to 1.0 (very positive)
# confidence_threshold: When to trust the escalation decision
#
# History:
# - Initial: -0.5 (too many escalations for mildly negative sentiment)
# - Tuned to -0.7 (escalate only very negative sentiment)
# See: evaluation/results/escalation-detection-results.md
# -----------------------------------------------------------------------------

resource "azurerm_app_configuration_key" "escalation_sentiment_threshold" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "escalation:sentiment_threshold"
  value = "-0.7"
  label = "production"

  tags = {
    Category    = "AgentThresholds"
    Agent       = "Escalation"
    ValidRange  = "-1.0-0.0"
    TunedDate   = "2026-01-25"
    TunedReason = "Reduce false escalations for mildly negative sentiment"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "escalation_confidence_threshold" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "escalation:confidence_threshold"
  value = "0.5"
  label = "production"

  tags = {
    Category   = "AgentThresholds"
    Agent      = "Escalation"
    ValidRange = "0.0-1.0"
    Rationale  = "Match intent classification threshold"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

# -----------------------------------------------------------------------------
# Response Generation Thresholds
# -----------------------------------------------------------------------------
# Purpose: Controls GPT-4o response generation behavior
# temperature: 0.0 (deterministic) to 1.0 (creative)
# max_tokens: Controls response length and cost
#
# Rationale:
# - Temperature 0.3: Consistent but not robotic responses
# - Max tokens 500: Sufficient for e-commerce support, limits cost
# See: evaluation/results/response-generation-results.md
# -----------------------------------------------------------------------------

resource "azurerm_app_configuration_key" "response_temperature" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "response:temperature"
  value = "0.3"
  label = "production"

  tags = {
    Category   = "AgentThresholds"
    Agent      = "ResponseGeneration"
    ValidRange = "0.0-1.0"
    Rationale  = "Consistent customer-facing responses"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "response_max_tokens" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "response:max_tokens"
  value = "500"
  label = "production"

  tags = {
    Category   = "AgentThresholds"
    Agent      = "ResponseGeneration"
    ValidRange = "100-2000"
    Rationale  = "Balance quality and cost"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

# -----------------------------------------------------------------------------
# Critic/Supervisor Thresholds
# -----------------------------------------------------------------------------
# Purpose: Controls content validation strictness
# block_threshold: Confidence level to block potentially harmful content
# max_retries: How many times to regenerate blocked content
#
# Rationale:
# - Block threshold 0.7: Block when 70%+ confident content is harmful
# - Max retries 3: Give response generator 3 chances before human escalation
# See: evaluation/results/critic-supervisor-results.md
# -----------------------------------------------------------------------------

resource "azurerm_app_configuration_key" "critic_block_threshold" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "critic:block_threshold"
  value = "0.7"
  label = "production"

  tags = {
    Category   = "AgentThresholds"
    Agent      = "CriticSupervisor"
    ValidRange = "0.5-0.95"
    Rationale  = "Balance security with usability"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "critic_max_retries" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "critic:max_retries"
  value = "3"
  label = "production"

  tags = {
    Category   = "AgentThresholds"
    Agent      = "CriticSupervisor"
    ValidRange = "1-5"
    Rationale  = "3 attempts before human escalation"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

# -----------------------------------------------------------------------------
# RAG Configuration
# -----------------------------------------------------------------------------
# Purpose: Controls knowledge retrieval behavior
# top_k: Number of documents to retrieve
# similarity_threshold: Minimum similarity score for results
#
# History:
# - Initial: top_k=3, threshold=0.8 (50% recall)
# - Tuned to top_k=5, threshold=0.75 (90%+ recall)
# See: evaluation/results/rag-retrieval-results.md
# -----------------------------------------------------------------------------

resource "azurerm_app_configuration_key" "rag_top_k" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "rag:top_k"
  value = "5"
  label = "production"

  tags = {
    Category    = "RAGConfiguration"
    Agent       = "KnowledgeRetrieval"
    ValidRange  = "1-20"
    TunedDate   = "2026-01-25"
    TunedReason = "Improve recall from 50% to 90%+"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "rag_similarity_threshold" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "rag:similarity_threshold"
  value = "0.75"
  label = "production"

  tags = {
    Category    = "RAGConfiguration"
    Agent       = "KnowledgeRetrieval"
    ValidRange  = "0.5-0.95"
    TunedDate   = "2026-01-25"
    TunedReason = "Lower threshold for better recall"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

# ============================================================================
# CONFIGURATION SETTINGS - Throttling
# ============================================================================
# These settings protect against rate limiting and cost overruns.
# Adjust based on observed usage patterns and Azure OpenAI quotas.
#
# Load Test Results (2026-01-27):
# - 3 concurrent users stable at 13-15 req/min
# - 10 concurrent users shows degradation (Azure OpenAI rate limiting)
# See: tests/load/LOAD-TEST-REPORT-2026-01-27.md
# ============================================================================

resource "azurerm_app_configuration_key" "throttle_openai_rpm" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "throttle:openai_requests_per_minute"
  value = "50"
  label = "production"

  tags = {
    Category   = "Throttling"
    Service    = "AzureOpenAI"
    ValidRange = "10-100"
    Rationale  = "Stay under Azure OpenAI quota"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "throttle_queue_enabled" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "throttle:queue_enabled"
  value = "true"
  label = "production"

  tags = {
    Category  = "Throttling"
    Service   = "AzureOpenAI"
    Rationale = "Queue requests instead of failing with 429"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "throttle_queue_max_size" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "throttle:queue_max_size"
  value = "100"
  label = "production"

  tags = {
    Category   = "Throttling"
    Service    = "AzureOpenAI"
    ValidRange = "10-500"
    Rationale  = "Queue up to 100 requests before rejecting"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "throttle_nats_global_rps" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "throttle:nats_global_rps"
  value = "100"
  label = "production"

  tags = {
    Category   = "Throttling"
    Service    = "NATS"
    ValidRange = "50-500"
    Rationale  = "Global NATS event rate limit"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_key" "throttle_agent_rps" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  key   = "throttle:agent_rps"
  value = "20"
  label = "production"

  tags = {
    Category   = "Throttling"
    Service    = "Agents"
    ValidRange = "5-50"
    Rationale  = "Per-agent request rate limit"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================
# Enable/disable features without code deployments.
# Supports gradual rollout via percentage targeting.
#
# Pattern:
# - Enabled: Feature active for all users
# - Disabled: Feature inactive
# - Targeting: Gradual rollout (10% → 25% → 50% → 100%)
# ============================================================================

resource "azurerm_app_configuration_feature" "rag_enabled" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  name        = "rag_enabled"
  label       = "production"
  enabled     = true
  description = "Enable RAG pipeline for knowledge retrieval"

  tags = {
    Category = "FeatureFlags"
    Agent    = "KnowledgeRetrieval"
    RolloutDate = "2026-01-25"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_feature" "critic_enabled" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  name        = "critic_supervisor_enabled"
  label       = "production"
  enabled     = true
  description = "Enable Critic/Supervisor content validation"

  tags = {
    Category    = "FeatureFlags"
    Agent       = "CriticSupervisor"
    RolloutDate = "2026-01-25"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_feature" "pii_tokenization_enabled" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  name        = "pii_tokenization_enabled"
  label       = "production"
  enabled     = true
  description = "Enable PII tokenization for third-party AI services"

  tags = {
    Category = "FeatureFlags"
    Purpose  = "Security"
    Rationale = "Protect PII in external AI calls"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_feature" "multi_language_enabled" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  name        = "multi_language_enabled"
  label       = "production"
  enabled     = var.enable_multi_language
  description = "Enable multi-language response generation (en, fr-ca, es)"

  tags = {
    Category  = "FeatureFlags"
    Languages = "en,fr-ca,es"
    Rationale = "Expand to Canadian French and Spanish markets"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

resource "azurerm_app_configuration_feature" "auto_scaling_enabled" {
  count                  = var.enable_app_configuration ? 1 : 0
  configuration_store_id = azurerm_app_configuration.main[0].id

  name        = "auto_scaling_enabled"
  label       = "production"
  enabled     = var.enable_container_apps
  description = "Enable auto-scaling via Container Apps (10K daily users)"

  tags = {
    Category = "FeatureFlags"
    Purpose  = "Scalability"
    Rationale = "Support 10,000 daily users with horizontal scaling"
  }

  depends_on = [time_sleep.appconfig_rbac_propagation]
}

# ============================================================================
# RBAC - Role Assignments
# ============================================================================
# Grant managed identity access to read configuration at runtime.
# Grant container identity access for agents to read config.
#
# Roles:
# - App Configuration Data Reader: Read configuration values
# - App Configuration Data Owner: Read/write configuration (operators only)
# ============================================================================

# Container identity can read configuration
resource "azurerm_role_assignment" "appconfig_container_reader" {
  count = var.enable_app_configuration ? 1 : 0

  scope                = azurerm_app_configuration.main[0].id
  role_definition_name = "App Configuration Data Reader"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

# Current Terraform principal needs Data Owner to create keys/features
# This allows Terraform to manage configuration keys during deployment
resource "azurerm_role_assignment" "appconfig_terraform_owner" {
  count = var.enable_app_configuration ? 1 : 0

  scope                = azurerm_app_configuration.main[0].id
  role_definition_name = "App Configuration Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ============================================================================
# RBAC Propagation Delay
# ============================================================================
# Azure RBAC can take up to 10 minutes to propagate for App Configuration
# data plane operations. This sleep ensures the role assignment is active
# before attempting to create configuration keys.
#
# Without this, Terraform may fail with "Forbidden" errors.
# See: https://learn.microsoft.com/azure/azure-app-configuration/howto-integrate-azure-managed-service-identity
# ============================================================================

resource "time_sleep" "appconfig_rbac_propagation" {
  count = var.enable_app_configuration ? 1 : 0

  depends_on = [azurerm_role_assignment.appconfig_terraform_owner]

  create_duration = "120s"  # Wait 2 minutes for RBAC to propagate
}

# Key Vault access for App Configuration (to reference secrets)
resource "azurerm_key_vault_access_policy" "appconfig" {
  count = var.enable_app_configuration ? 1 : 0

  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_app_configuration.main[0].identity[0].principal_id

  secret_permissions = [
    "Get",
    "List"
  ]
}

# ============================================================================
# DIAGNOSTIC SETTINGS
# ============================================================================
# Send audit logs to Log Analytics for compliance and troubleshooting.
# All configuration changes are logged with user identity.
#
# Log Categories:
# - HttpRequest: API requests (read/write operations)
# - Audit: Configuration changes with before/after values
# ============================================================================

resource "azurerm_monitor_diagnostic_setting" "appconfig" {
  count = var.enable_app_configuration ? 1 : 0

  name                       = "appconfig-diagnostics"
  target_resource_id         = azurerm_app_configuration.main[0].id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "HttpRequest"
  }

  enabled_log {
    category = "Audit"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

# ============================================================================
# DATA SOURCE - Current Client Config
# ============================================================================
# Used for tenant_id in access policies
# NOTE: Defined in keyvault.tf to avoid duplication
# Reference: data.azurerm_client_config.current
