# Phase 4: Cosmos DB Serverless
# Data storage for conversations, sessions, analytics

# ============================================================================
# COSMOS DB ACCOUNT
# ============================================================================

resource "azurerm_cosmosdb_account" "main" {
  name                = "cosmos-${local.name_prefix}-${random_string.suffix.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  # Serverless mode - pay per request (NOT provisioned RU/s)
  capabilities {
    name = "EnableServerless"
  }

  # Consistency level
  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  # Single region (no geo-replication - cost optimization)
  geo_location {
    location          = local.location
    failover_priority = 0
  }

  # Continuous backup for disaster recovery
  backup {
    type = "Continuous"
    tier = "Continuous7Days" # 7-day PITR
    # Note: storage_redundancy not supported with Continuous backup type
  }

  # Network configuration
  is_virtual_network_filter_enabled = var.enable_private_endpoints
  public_network_access_enabled     = !var.enable_private_endpoints

  dynamic "virtual_network_rule" {
    for_each = var.enable_private_endpoints ? [1] : []
    content {
      id = azurerm_subnet.containers.id
    }
  }

  # Disable features we don't need
  local_authentication_disabled = false
  analytical_storage_enabled    = false

  tags = local.common_tags

  # Cost: ~$15-30/month (serverless, pay-per-request)
}

# ============================================================================
# PRIVATE ENDPOINT FOR COSMOS DB
# ============================================================================

resource "azurerm_private_endpoint" "cosmos" {
  count               = var.enable_private_endpoints ? 1 : 0
  name                = "${local.name_prefix}-pe-cosmos"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.private_endpoints.id

  private_service_connection {
    name                           = "${local.name_prefix}-psc-cosmos"
    private_connection_resource_id = azurerm_cosmosdb_account.main.id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }

  private_dns_zone_group {
    name                 = "cosmos-dns-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos[0].id]
  }

  tags = local.common_tags
}

# ============================================================================
# DATABASE: Conversations
# ============================================================================

resource "azurerm_cosmosdb_sql_database" "conversations" {
  name                = "conversations"
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

# ============================================================================
# Container: Customer Sessions (Phase 6 - Customer Authentication)
# ============================================================================
# Purpose: Store customer sessions for authenticated interactions
#
# Partition Key: /customer_id
# - Enables efficient cross-device session lookup
# - All sessions for a customer are colocated
# - Supports "Continue conversation" on new device
#
# TTL: 7 days (604800 seconds)
# - Automatic cleanup of expired sessions
# - Aligns with session expiry in application code
#
# Indexing Strategy:
# - Index session_id for direct lookup
# - Index device_id for anonymous session linking
# - Index auth_level for analytics queries
# - Exclude token data from indexing (security)
#
# Related Documentation:
# - Session Manager: shared/auth/session_manager.py
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q5.C)
# ============================================================================
resource "azurerm_cosmosdb_sql_container" "sessions" {
  name                = "sessions"
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.conversations.name

  # Partition by customer_id for cross-device session lookup
  # Anonymous sessions use device_id as customer_id
  partition_key_path = "/customer_id"

  # TTL: 7 days for session cleanup (matches application session expiry)
  default_ttl = 604800

  indexing_policy {
    indexing_mode = "consistent"

    # Index key fields for queries
    included_path {
      path = "/session_id/?"
    }

    included_path {
      path = "/device_id/?"
    }

    included_path {
      path = "/auth_level/?"
    }

    included_path {
      path = "/state/?"
    }

    included_path {
      path = "/created_at/?"
    }

    included_path {
      path = "/updated_at/?"
    }

    included_path {
      path = "/channel/?"
    }

    # Exclude token data from indexing (security - reduce attack surface)
    excluded_path {
      path = "/token/*"
    }

    # Exclude customer profile from indexing (large nested object)
    excluded_path {
      path = "/customer/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

# Container: Messages
resource "azurerm_cosmosdb_sql_container" "messages" {
  name                = "messages"
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.conversations.name
  partition_key_path  = "/conversationId"

  # TTL: 90 days for message history
  default_ttl = 7776000

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/content/?"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

# Container: Analytics
resource "azurerm_cosmosdb_sql_container" "analytics" {
  name                = "analytics"
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.conversations.name
  partition_key_path  = "/metricDate"

  # No TTL - keep analytics indefinitely
  default_ttl = -1

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}

# Container: PII Token Mappings (for tokenization service)
resource "azurerm_cosmosdb_sql_container" "pii_tokens" {
  name                = "pii-tokens"
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.conversations.name
  partition_key_path  = "/tokenId"

  # TTL: 90 days for PII token cleanup
  default_ttl = 7776000

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/tokenId/?"
    }

    excluded_path {
      path = "/*"
    }
  }
}

# ============================================================================
# DATABASE: Knowledge Base (for RAG)
# ============================================================================

resource "azurerm_cosmosdb_sql_database" "knowledge" {
  name                = "knowledge"
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

# Container: Documents (with vector search capability)
resource "azurerm_cosmosdb_sql_container" "documents" {
  name                = "documents"
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.knowledge.name
  partition_key_path  = "/category"

  # No TTL - knowledge base is persistent
  default_ttl = -1

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    # Exclude large text content from indexing
    excluded_path {
      path = "/content/?"
    }

    excluded_path {
      path = "/embedding/?"
    }
  }

  # Note: Vector search requires MongoDB API or preview features
  # For Phase 4, we'll use a simple embedding lookup approach
}

# ============================================================================
# RBAC FOR COSMOS DB
# ============================================================================

# Container instances will use managed identity
# This role allows read/write access to Cosmos DB data
resource "azurerm_cosmosdb_sql_role_definition" "contributor" {
  name                = "CosmosDBDataContributor"
  resource_group_name = data.azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  type                = "CustomRole"
  assignable_scopes   = [azurerm_cosmosdb_account.main.id]

  permissions {
    data_actions = [
      "Microsoft.DocumentDB/databaseAccounts/readMetadata",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*"
    ]
  }
}
