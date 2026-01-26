# Phase 4: Azure Key Vault
# Secrets management for API keys and certificates

# ============================================================================
# KEY VAULT
# ============================================================================

resource "azurerm_key_vault" "main" {
  name                = "kv-${local.name_prefix}-${random_string.suffix.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  tenant_id           = var.tenant_id
  sku_name            = "standard" # Not Premium - cost optimization

  # Security settings
  enabled_for_disk_encryption     = false
  enabled_for_deployment          = false
  enabled_for_template_deployment = false
  enable_rbac_authorization       = true
  purge_protection_enabled        = true
  soft_delete_retention_days      = 90

  # Network ACLs - allow public access for initial deployment
  # This will be tightened after deployment via Azure Portal or subsequent apply
  network_acls {
    bypass                     = "AzureServices"
    default_action             = "Allow" # Allow initially for Terraform to write secrets
    virtual_network_subnet_ids = var.enable_private_endpoints ? [azurerm_subnet.containers.id] : []
  }

  tags = local.common_tags

  # Cost: ~$0.30/month (Standard tier, 10,000 operations free)
}

# ============================================================================
# PRIVATE ENDPOINT FOR KEY VAULT
# ============================================================================

resource "azurerm_private_endpoint" "keyvault" {
  count               = var.enable_private_endpoints ? 1 : 0
  name                = "${local.name_prefix}-pe-keyvault"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.private_endpoints.id

  private_service_connection {
    name                           = "${local.name_prefix}-psc-keyvault"
    private_connection_resource_id = azurerm_key_vault.main.id
    is_manual_connection           = false
    subresource_names              = ["vault"]
  }

  private_dns_zone_group {
    name                 = "keyvault-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.keyvault[0].id]
  }

  tags = local.common_tags
}

# ============================================================================
# SECRETS
# ============================================================================

# Azure OpenAI API Key
resource "azurerm_key_vault_secret" "azure_openai_api_key" {
  name         = "azure-openai-api-key"
  value        = var.azure_openai_api_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.terraform_keyvault_admin]

  tags = {
    Purpose = "Azure OpenAI authentication"
    Service = "Azure OpenAI"
  }
}

# Shopify credentials (if provided)
resource "azurerm_key_vault_secret" "shopify_api_key" {
  count        = var.shopify_api_key != "" ? 1 : 0
  name         = "shopify-api-key"
  value        = var.shopify_api_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.terraform_keyvault_admin]

  tags = {
    Purpose = "Shopify API authentication"
    Service = "Shopify"
  }
}

resource "azurerm_key_vault_secret" "shopify_api_secret" {
  count        = var.shopify_api_secret != "" ? 1 : 0
  name         = "shopify-api-secret"
  value        = var.shopify_api_secret
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.terraform_keyvault_admin]

  tags = {
    Purpose = "Shopify API authentication"
    Service = "Shopify"
  }
}

# Zendesk credentials (if provided)
resource "azurerm_key_vault_secret" "zendesk_api_token" {
  count        = var.zendesk_api_token != "" ? 1 : 0
  name         = "zendesk-api-token"
  value        = var.zendesk_api_token
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.terraform_keyvault_admin]

  tags = {
    Purpose = "Zendesk API authentication"
    Service = "Zendesk"
  }
}

# Mailchimp credentials (if provided)
resource "azurerm_key_vault_secret" "mailchimp_api_key" {
  count        = var.mailchimp_api_key != "" ? 1 : 0
  name         = "mailchimp-api-key"
  value        = var.mailchimp_api_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.terraform_keyvault_admin]

  tags = {
    Purpose = "Mailchimp API authentication"
    Service = "Mailchimp"
  }
}

# Google Analytics credentials (if provided)
resource "azurerm_key_vault_secret" "google_analytics_credentials" {
  count        = var.google_analytics_credentials_json != "" ? 1 : 0
  name         = "google-analytics-credentials"
  value        = var.google_analytics_credentials_json
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_role_assignment.terraform_keyvault_admin]

  tags = {
    Purpose = "Google Analytics service account"
    Service = "Google Analytics"
  }
}

# ============================================================================
# RBAC ASSIGNMENTS
# ============================================================================

# Current user/service principal needs admin access during deployment
data "azurerm_client_config" "current" {}

resource "azurerm_role_assignment" "terraform_keyvault_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}
