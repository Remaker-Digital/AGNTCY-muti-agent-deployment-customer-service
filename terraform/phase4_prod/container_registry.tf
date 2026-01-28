# Phase 4: Azure Container Registry
# Stores container images for all 6 agents

# ============================================================================
# CONTAINER REGISTRY
# ============================================================================

resource "azurerm_container_registry" "main" {
  name                = "acr${replace(local.name_prefix, "-", "")}${random_string.suffix.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = var.container_registry_sku
  admin_enabled       = true  # Required for Container Apps registry authentication

  # Disable public network access in production (Phase 5)
  public_network_access_enabled = true

  # Trust policy for signed images (Phase 5 enhancement)
  trust_policy {
    enabled = false
  }

  tags = local.common_tags

  # Cost: ~$5/month (Basic tier)
}

# ============================================================================
# RBAC FOR CONTAINER REGISTRY
# ============================================================================

# Allow current user to push images during deployment
resource "azurerm_role_assignment" "acr_push" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ============================================================================
# OUTPUTS FOR CI/CD
# ============================================================================

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.main.login_server
}

output "acr_name" {
  description = "ACR name"
  value       = azurerm_container_registry.main.name
}
