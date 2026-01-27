# Phase 4: Container Instances
# 6 Agent containers + SLIM Gateway + NATS JetStream
# Set deploy_containers = true after building and pushing images to ACR

# ============================================================================
# USER-ASSIGNED MANAGED IDENTITY (shared by all containers)
# ============================================================================

resource "azurerm_user_assigned_identity" "containers" {
  name                = "${local.name_prefix}-identity-containers"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name

  tags = local.common_tags
}

# RBAC: Allow identity to read secrets from Key Vault
resource "azurerm_role_assignment" "containers_keyvault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

# RBAC: Allow identity to pull from Container Registry
resource "azurerm_role_assignment" "containers_acr" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.containers.principal_id
}

# RBAC: Allow identity to read/write Cosmos DB
resource "azurerm_cosmosdb_sql_role_assignment" "containers_cosmos" {
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = azurerm_cosmosdb_sql_role_definition.contributor.id
  principal_id        = azurerm_user_assigned_identity.containers.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

# ============================================================================
# SLIM GATEWAY (AGNTCY Transport)
# ============================================================================

resource "azurerm_container_group" "slim_gateway" {
  count               = var.deploy_containers ? 1 : 0
  name                = "${local.name_prefix}-cg-slim"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  image_registry_credential {
    server                    = azurerm_container_registry.main.login_server
    user_assigned_identity_id = azurerm_user_assigned_identity.containers.id
  }

  container {
    name   = "slim-gateway"
    image  = "${azurerm_container_registry.main.login_server}/slim-gateway:latest"
    cpu    = 1.0
    memory = 2.0

    # SLIM requires explicit command - see docker-compose.yml
    commands = ["/slim", "--port", "8443"]

    ports {
      port     = 8443
      protocol = "TCP"
    }

    environment_variables = {
      SLIM_TLS_ENABLED                      = "true"
      SLIM_AUTH_ENABLED                     = "true"
      APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
    }
  }

  tags = local.common_tags

  # Cost: ~$30-40/month (1 vCPU + 2GB RAM)
}

# ============================================================================
# NATS JETSTREAM (Event Bus)
# ============================================================================

resource "azurerm_container_group" "nats" {
  count               = var.deploy_containers && var.enable_nats_jetstream ? 1 : 0
  name                = "${local.name_prefix}-cg-nats"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  container {
    name   = "nats"
    image  = "nats:2.10-alpine"
    cpu    = 0.5
    memory = 1.0

    ports {
      port     = 4222
      protocol = "TCP"
    }

    ports {
      port     = 8222
      protocol = "TCP"
    }

    commands = ["nats-server", "-js", "-m", "8222"]

    environment_variables = {
      # JetStream configuration
      NATS_JETSTREAM_STORE_DIR = "/data/jetstream"
    }

    volume {
      name       = "jetstream-data"
      mount_path = "/data"
      empty_dir  = true
    }
  }

  tags = local.common_tags

  # Cost: ~$12-18/month (0.5 vCPU + 1GB RAM)
}

# ============================================================================
# INTENT CLASSIFICATION AGENT
# ============================================================================

resource "azurerm_container_group" "intent_classifier" {
  count               = var.deploy_containers ? 1 : 0
  name                = "${local.name_prefix}-cg-intent"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  image_registry_credential {
    server                    = azurerm_container_registry.main.login_server
    user_assigned_identity_id = azurerm_user_assigned_identity.containers.id
  }

  container {
    name   = "intent-classifier"
    image  = "${azurerm_container_registry.main.login_server}/intent-classifier:v1.1.0-openai"
    cpu    = local.agents["intent-classifier"].cpu
    memory = local.agents["intent-classifier"].memory

    ports {
      port     = local.agents["intent-classifier"].port
      protocol = "TCP"
    }

    environment_variables = {
      AGENT_NAME                            = "intent-classifier"
      SLIM_ENDPOINT                         = var.deploy_containers ? azurerm_container_group.slim_gateway[0].ip_address : ""
      SLIM_PORT                             = "8443"
      AZURE_OPENAI_ENDPOINT                 = var.azure_openai_endpoint
      AZURE_OPENAI_DEPLOYMENT               = var.gpt4o_mini_deployment
      AZURE_OPENAI_API_KEY                  = var.azure_openai_api_key
      USE_AZURE_OPENAI                      = "true"
      COSMOS_ENDPOINT                       = azurerm_cosmosdb_account.main.endpoint
      KEYVAULT_URI                          = azurerm_key_vault.main.vault_uri
      APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
      NATS_URL                              = var.deploy_containers && var.enable_nats_jetstream ? "nats://${azurerm_container_group.nats[0].ip_address}:4222" : ""
    }
  }

  tags = merge(local.common_tags, { Agent = "intent-classifier" })

  depends_on = [azurerm_container_group.slim_gateway]

  # Cost: ~$15-20/month (0.5 vCPU + 1GB RAM)
}

# ============================================================================
# KNOWLEDGE RETRIEVAL AGENT
# ============================================================================

resource "azurerm_container_group" "knowledge_retrieval" {
  count               = var.deploy_containers ? 1 : 0
  name                = "${local.name_prefix}-cg-knowledge"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  image_registry_credential {
    server                    = azurerm_container_registry.main.login_server
    user_assigned_identity_id = azurerm_user_assigned_identity.containers.id
  }

  container {
    name   = "knowledge-retrieval"
    image  = "${azurerm_container_registry.main.login_server}/knowledge-retrieval:v1.1.0-openai"
    cpu    = local.agents["knowledge-retrieval"].cpu
    memory = local.agents["knowledge-retrieval"].memory

    ports {
      port     = local.agents["knowledge-retrieval"].port
      protocol = "TCP"
    }

    environment_variables = {
      AGENT_NAME                            = "knowledge-retrieval"
      SLIM_ENDPOINT                         = var.deploy_containers ? azurerm_container_group.slim_gateway[0].ip_address : ""
      SLIM_PORT                             = "8443"
      AZURE_OPENAI_ENDPOINT                 = var.azure_openai_endpoint
      AZURE_OPENAI_EMBEDDING_DEPLOYMENT     = var.embedding_deployment
      AZURE_OPENAI_API_KEY                  = var.azure_openai_api_key
      USE_AZURE_OPENAI                      = "true"
      COSMOS_ENDPOINT                       = azurerm_cosmosdb_account.main.endpoint
      KEYVAULT_URI                          = azurerm_key_vault.main.vault_uri
      APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
      SHOPIFY_STORE_URL                     = var.shopify_store_url
    }
  }

  tags = merge(local.common_tags, { Agent = "knowledge-retrieval" })

  depends_on = [azurerm_container_group.slim_gateway]

  # Cost: ~$15-20/month (0.5 vCPU + 1GB RAM)
}

# ============================================================================
# RESPONSE GENERATION AGENT
# ============================================================================

resource "azurerm_container_group" "response_generator" {
  count               = var.deploy_containers ? 1 : 0
  name                = "${local.name_prefix}-cg-response"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  image_registry_credential {
    server                    = azurerm_container_registry.main.login_server
    user_assigned_identity_id = azurerm_user_assigned_identity.containers.id
  }

  container {
    name   = "response-generator"
    image  = "${azurerm_container_registry.main.login_server}/response-generator:v1.1.0-openai"
    cpu    = local.agents["response-generator"].cpu
    memory = local.agents["response-generator"].memory

    ports {
      port     = local.agents["response-generator"].port
      protocol = "TCP"
    }

    environment_variables = {
      AGENT_NAME                            = "response-generator"
      SLIM_ENDPOINT                         = var.deploy_containers ? azurerm_container_group.slim_gateway[0].ip_address : ""
      SLIM_PORT                             = "8443"
      AZURE_OPENAI_ENDPOINT                 = var.azure_openai_endpoint
      AZURE_OPENAI_DEPLOYMENT               = var.gpt4o_deployment
      AZURE_OPENAI_API_KEY                  = var.azure_openai_api_key
      USE_AZURE_OPENAI                      = "true"
      COSMOS_ENDPOINT                       = azurerm_cosmosdb_account.main.endpoint
      KEYVAULT_URI                          = azurerm_key_vault.main.vault_uri
      APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
      SUPPORTED_LANGUAGES                   = var.enable_multi_language ? "en,fr-ca,es" : "en"
    }
  }

  tags = merge(local.common_tags, { Agent = "response-generator" })

  depends_on = [azurerm_container_group.slim_gateway]

  # Cost: ~$18-25/month (0.5 vCPU + 1.5GB RAM)
}

# ============================================================================
# ESCALATION AGENT
# ============================================================================

resource "azurerm_container_group" "escalation" {
  count               = var.deploy_containers ? 1 : 0
  name                = "${local.name_prefix}-cg-escalation"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  image_registry_credential {
    server                    = azurerm_container_registry.main.login_server
    user_assigned_identity_id = azurerm_user_assigned_identity.containers.id
  }

  container {
    name   = "escalation"
    image  = "${azurerm_container_registry.main.login_server}/escalation:v1.1.0-openai"
    cpu    = local.agents["escalation"].cpu
    memory = local.agents["escalation"].memory

    ports {
      port     = local.agents["escalation"].port
      protocol = "TCP"
    }

    environment_variables = {
      AGENT_NAME                            = "escalation"
      SLIM_ENDPOINT                         = var.deploy_containers ? azurerm_container_group.slim_gateway[0].ip_address : ""
      SLIM_PORT                             = "8443"
      AZURE_OPENAI_ENDPOINT                 = var.azure_openai_endpoint
      AZURE_OPENAI_DEPLOYMENT               = var.gpt4o_mini_deployment
      AZURE_OPENAI_API_KEY                  = var.azure_openai_api_key
      USE_AZURE_OPENAI                      = "true"
      COSMOS_ENDPOINT                       = azurerm_cosmosdb_account.main.endpoint
      KEYVAULT_URI                          = azurerm_key_vault.main.vault_uri
      APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
      ZENDESK_SUBDOMAIN                     = var.zendesk_subdomain
      ZENDESK_EMAIL                         = var.zendesk_email
      NATS_URL                              = var.deploy_containers && var.enable_nats_jetstream ? "nats://${azurerm_container_group.nats[0].ip_address}:4222" : ""
    }
  }

  tags = merge(local.common_tags, { Agent = "escalation" })

  depends_on = [azurerm_container_group.slim_gateway]

  # Cost: ~$15-20/month (0.5 vCPU + 1GB RAM)
}

# ============================================================================
# ANALYTICS AGENT
# ============================================================================

resource "azurerm_container_group" "analytics" {
  count               = var.deploy_containers ? 1 : 0
  name                = "${local.name_prefix}-cg-analytics"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  image_registry_credential {
    server                    = azurerm_container_registry.main.login_server
    user_assigned_identity_id = azurerm_user_assigned_identity.containers.id
  }

  container {
    name   = "analytics"
    image  = "${azurerm_container_registry.main.login_server}/analytics:v1.1.0-openai"
    cpu    = local.agents["analytics"].cpu
    memory = local.agents["analytics"].memory

    ports {
      port     = local.agents["analytics"].port
      protocol = "TCP"
    }

    environment_variables = {
      AGENT_NAME                            = "analytics"
      SLIM_ENDPOINT                         = var.deploy_containers ? azurerm_container_group.slim_gateway[0].ip_address : ""
      SLIM_PORT                             = "8443"
      USE_AZURE_OPENAI                      = "true"
      COSMOS_ENDPOINT                       = azurerm_cosmosdb_account.main.endpoint
      KEYVAULT_URI                          = azurerm_key_vault.main.vault_uri
      APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
      GA4_PROPERTY_ID                       = var.google_analytics_property_id
      NATS_URL                              = var.deploy_containers && var.enable_nats_jetstream ? "nats://${azurerm_container_group.nats[0].ip_address}:4222" : ""
    }
  }

  tags = merge(local.common_tags, { Agent = "analytics" })

  depends_on = [azurerm_container_group.slim_gateway]

  # Cost: ~$15-20/month (0.5 vCPU + 1GB RAM)
}

# ============================================================================
# CRITIC/SUPERVISOR AGENT
# ============================================================================

resource "azurerm_container_group" "critic_supervisor" {
  count               = var.deploy_containers ? 1 : 0
  name                = "${local.name_prefix}-cg-critic"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  os_type             = "Linux"
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  image_registry_credential {
    server                    = azurerm_container_registry.main.login_server
    user_assigned_identity_id = azurerm_user_assigned_identity.containers.id
  }

  container {
    name   = "critic-supervisor"
    image  = "${azurerm_container_registry.main.login_server}/critic-supervisor:v1.1.0-openai"
    cpu    = local.agents["critic-supervisor"].cpu
    memory = local.agents["critic-supervisor"].memory

    ports {
      port     = local.agents["critic-supervisor"].port
      protocol = "TCP"
    }

    environment_variables = {
      AGENT_NAME                            = "critic-supervisor"
      SLIM_ENDPOINT                         = var.deploy_containers ? azurerm_container_group.slim_gateway[0].ip_address : ""
      SLIM_PORT                             = "8443"
      AZURE_OPENAI_ENDPOINT                 = var.azure_openai_endpoint
      AZURE_OPENAI_DEPLOYMENT               = var.gpt4o_mini_deployment
      AZURE_OPENAI_API_KEY                  = var.azure_openai_api_key
      USE_AZURE_OPENAI                      = "true"
      COSMOS_ENDPOINT                       = azurerm_cosmosdb_account.main.endpoint
      KEYVAULT_URI                          = azurerm_key_vault.main.vault_uri
      APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
      MAX_REGENERATE_ATTEMPTS               = "3"
    }
  }

  tags = merge(local.common_tags, { Agent = "critic-supervisor" })

  depends_on = [azurerm_container_group.slim_gateway]

  # Cost: ~$15-20/month (0.5 vCPU + 1GB RAM)
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "slim_gateway_ip" {
  description = "SLIM Gateway private IP address"
  value       = var.deploy_containers ? azurerm_container_group.slim_gateway[0].ip_address : null
}

output "nats_ip" {
  description = "NATS JetStream private IP address"
  value       = var.deploy_containers && var.enable_nats_jetstream ? azurerm_container_group.nats[0].ip_address : null
}

output "agent_ips" {
  description = "Agent container private IP addresses"
  value = var.deploy_containers ? {
    intent-classifier   = azurerm_container_group.intent_classifier[0].ip_address
    knowledge-retrieval = azurerm_container_group.knowledge_retrieval[0].ip_address
    response-generator  = azurerm_container_group.response_generator[0].ip_address
    escalation          = azurerm_container_group.escalation[0].ip_address
    analytics           = azurerm_container_group.analytics[0].ip_address
    critic-supervisor   = azurerm_container_group.critic_supervisor[0].ip_address
  } : null
}
