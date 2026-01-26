# Phase 4: Outputs
# Values needed for CI/CD, monitoring, and documentation

# ============================================================================
# RESOURCE IDENTIFIERS
# ============================================================================

output "resource_group_name" {
  description = "Resource group name"
  value       = data.azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "Resource group ID"
  value       = data.azurerm_resource_group.main.id
}

# ============================================================================
# NETWORKING
# ============================================================================

output "vnet_id" {
  description = "Virtual network ID"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "Virtual network name"
  value       = azurerm_virtual_network.main.name
}

output "container_subnet_id" {
  description = "Container subnet ID"
  value       = azurerm_subnet.containers.id
}

# ============================================================================
# KEY VAULT
# ============================================================================

output "keyvault_id" {
  description = "Key Vault ID"
  value       = azurerm_key_vault.main.id
}

output "keyvault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}

output "keyvault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

# ============================================================================
# COSMOS DB
# ============================================================================

output "cosmosdb_account_name" {
  description = "Cosmos DB account name"
  value       = azurerm_cosmosdb_account.main.name
}

output "cosmosdb_endpoint" {
  description = "Cosmos DB endpoint"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "cosmosdb_connection_string" {
  description = "Cosmos DB primary connection string"
  value       = azurerm_cosmosdb_account.main.primary_sql_connection_string
  sensitive   = true
}

# ============================================================================
# CONTAINER REGISTRY
# ============================================================================

# (Already defined in container_registry.tf)

# ============================================================================
# MANAGED IDENTITY
# ============================================================================

output "container_identity_id" {
  description = "User-assigned managed identity ID for containers"
  value       = azurerm_user_assigned_identity.containers.id
}

output "container_identity_client_id" {
  description = "User-assigned managed identity client ID"
  value       = azurerm_user_assigned_identity.containers.client_id
}

output "container_identity_principal_id" {
  description = "User-assigned managed identity principal ID"
  value       = azurerm_user_assigned_identity.containers.principal_id
}

# ============================================================================
# AZURE OPENAI (reference to existing)
# ============================================================================

output "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint (existing in West US)"
  value       = data.azurerm_cognitive_account.openai.endpoint
}

# ============================================================================
# DEPLOYMENT INFO
# ============================================================================

output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    phase               = "Phase 4"
    region              = local.location
    azure_openai_region = "westus"
    agent_count         = 6
    budget_monthly      = var.budget_amount
    log_retention_days  = var.log_retention_days
    multi_language      = var.enable_multi_language
    private_endpoints   = var.enable_private_endpoints
    nats_enabled        = var.enable_nats_jetstream
    containers_deployed = var.deploy_containers
  }
}
