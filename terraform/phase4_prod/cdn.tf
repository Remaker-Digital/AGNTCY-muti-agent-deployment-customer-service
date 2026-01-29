# ============================================================================
# Phase 4: Azure CDN and Blob Storage for Widget Distribution
# ============================================================================
#
# Purpose: Host and distribute the AGNTCY Chat Widget via CDN
#
# Architecture:
# - Azure Blob Storage: Origin for static widget files
# - Azure CDN: Global distribution with caching
# - Custom domain: Optional CNAME for branded URLs
#
# Why Azure CDN Standard (not Premium)?
# - Standard tier sufficient for widget distribution
# - Lower cost (~$0.087/GB first 10TB)
# - Includes required features (HTTPS, caching rules, compression)
# - Premium features (geo-filtering, rules engine) not needed
#
# Cost Impact: ~$5-10/month
# - Storage: <$1/month (minimal file size)
# - CDN: ~$5-10/month (depends on traffic)
#
# Related Documentation:
# - Widget Source: widget/src/chat-widget.js
# - Deploy Script: widget/scripts/deploy-cdn.js
# - Phase 6-7 Planning: docs/PHASE-6-7-PLANNING-DECISIONS.md (Q1.B)
# ============================================================================

# ============================================================================
# STORAGE ACCOUNT FOR WIDGET FILES
# ============================================================================

resource "azurerm_storage_account" "widget" {
  name                     = "st${replace(local.name_prefix, "-", "")}widget"
  resource_group_name      = data.azurerm_resource_group.main.name
  location                 = local.location
  account_tier             = "Standard"
  account_replication_type = "LRS"  # Local redundancy sufficient for static files

  # Enable static website hosting
  static_website {
    index_document     = "index.html"
    error_404_document = "404.html"
  }

  # Security settings
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = true  # Required for CDN access

  # Blob properties for caching
  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "HEAD", "OPTIONS"]
      allowed_origins    = ["*"]  # Widgets can be embedded on any domain
      exposed_headers    = ["*"]
      max_age_in_seconds = 86400  # 24 hours CORS cache
    }

    # Versioning disabled - we use filename versioning instead
    versioning_enabled = false
  }

  tags = merge(local.common_tags, {
    component = "widget-cdn"
    purpose   = "chat-widget-distribution"
  })
}

# ============================================================================
# STORAGE CONTAINER FOR WIDGET FILES
# ============================================================================

resource "azurerm_storage_container" "widget" {
  name                  = "widget"
  storage_account_name  = azurerm_storage_account.widget.name
  container_access_type = "blob"  # Public read access for CDN
}

# ============================================================================
# CDN PROFILE
# ============================================================================

resource "azurerm_cdn_profile" "widget" {
  name                = "${local.name_prefix}-cdn-profile"
  location            = "global"  # CDN profiles are global
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = "Standard_Microsoft"  # Cost-effective for static content

  tags = merge(local.common_tags, {
    component = "widget-cdn"
    purpose   = "global-distribution"
  })
}

# ============================================================================
# CDN ENDPOINT
# ============================================================================

resource "azurerm_cdn_endpoint" "widget" {
  name                = "${local.name_prefix}-widget-cdn"
  profile_name        = azurerm_cdn_profile.widget.name
  location            = "global"
  resource_group_name = data.azurerm_resource_group.main.name

  # Origin: Azure Blob Storage
  origin {
    name      = "widget-storage"
    host_name = azurerm_storage_account.widget.primary_blob_host
  }

  origin_host_header = azurerm_storage_account.widget.primary_blob_host

  # Caching behavior
  # Widget files are versioned, so we can cache aggressively
  querystring_caching_behaviour = "IgnoreQueryString"

  # Enable compression for text files
  is_compression_enabled = true
  content_types_to_compress = [
    "application/javascript",
    "text/css",
    "text/html",
    "text/plain",
    "application/json",
  ]

  # Optimization for general web delivery
  optimization_type = "GeneralWebDelivery"

  # Delivery rules for cache control
  delivery_rule {
    name  = "VersionedFilesLongCache"
    order = 1

    # Match versioned files (e.g., agntcy-chat.1.0.0.min.js)
    url_path_condition {
      operator     = "RegEx"
      match_values = [".*\\.[0-9]+\\.[0-9]+\\.[0-9]+\\..*"]
    }

    # Set long cache for versioned files (1 year)
    cache_expiration_action {
      behavior = "Override"
      duration = "365.00:00:00"  # 365 days
    }

    # Add cache headers
    modify_response_header_action {
      action = "Overwrite"
      name   = "Cache-Control"
      value  = "public, max-age=31536000, immutable"
    }
  }

  delivery_rule {
    name  = "LatestFilesShortCache"
    order = 2

    # Match non-versioned files (e.g., agntcy-chat.min.js)
    url_path_condition {
      operator         = "RegEx"
      match_values     = [".*\\.min\\.js$", ".*\\.esm\\.js$"]
      negate_condition = false
    }

    # Set short cache for latest files (1 hour)
    cache_expiration_action {
      behavior = "Override"
      duration = "01:00:00"  # 1 hour
    }

    modify_response_header_action {
      action = "Overwrite"
      name   = "Cache-Control"
      value  = "public, max-age=3600"
    }
  }

  delivery_rule {
    name  = "AddSecurityHeaders"
    order = 3

    # Match all requests
    request_scheme_condition {
      operator     = "Equal"
      match_values = ["HTTPS", "HTTP"]
    }

    # Add security headers
    modify_response_header_action {
      action = "Append"
      name   = "X-Content-Type-Options"
      value  = "nosniff"
    }

    modify_response_header_action {
      action = "Append"
      name   = "X-Frame-Options"
      value  = "SAMEORIGIN"
    }
  }

  tags = merge(local.common_tags, {
    component = "widget-cdn"
    purpose   = "widget-endpoint"
  })
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "widget_cdn_endpoint" {
  description = "CDN endpoint URL for widget distribution"
  value       = "https://${azurerm_cdn_endpoint.widget.fqdn}"
}

output "widget_storage_account" {
  description = "Storage account name for widget files"
  value       = azurerm_storage_account.widget.name
}

output "widget_storage_primary_endpoint" {
  description = "Primary blob endpoint for widget storage"
  value       = azurerm_storage_account.widget.primary_blob_endpoint
}

output "widget_embed_url" {
  description = "URL for embedding the widget script"
  value       = "https://${azurerm_cdn_endpoint.widget.fqdn}/widget/agntcy-chat.min.js"
}
