# Phase 4: Observability & Monitoring
# Log Analytics, Application Insights, Budget Alerts

# ============================================================================
# LOG ANALYTICS WORKSPACE
# ============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.name_prefix}-log-${random_string.suffix.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  # Daily cap to prevent runaway costs (optional)
  # daily_quota_gb = 1

  tags = local.common_tags

  # Cost: ~$15-25/month (pay per GB, 7-day retention)
}

# ============================================================================
# APPLICATION INSIGHTS
# ============================================================================

resource "azurerm_application_insights" "main" {
  name                = "${local.name_prefix}-appi-${random_string.suffix.result}"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  sampling_percentage = var.application_insights_sampling_percentage

  # Disable IP masking for debugging (enable in production)
  disable_ip_masking = false

  tags = local.common_tags

  # Cost: ~$6-8/month (included in Log Analytics ingestion)
}

# ============================================================================
# AZURE MONITOR ACTION GROUP
# ============================================================================

resource "azurerm_monitor_action_group" "alerts" {
  name                = "${local.name_prefix}-ag-alerts"
  resource_group_name = data.azurerm_resource_group.main.name
  short_name          = "agntcy-alrt"

  email_receiver {
    name                    = "admin"
    email_address           = var.owner_email
    use_common_alert_schema = true
  }

  tags = local.common_tags
}

# ============================================================================
# METRIC ALERTS
# ============================================================================

# Alert: High error rate
resource "azurerm_monitor_metric_alert" "error_rate" {
  name                = "${local.name_prefix}-alert-error-rate"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when error rate exceeds 5%"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/failed"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 50 # More than 50 failed requests in 15 min
  }

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }

  tags = local.common_tags
}

# Alert: High response latency
resource "azurerm_monitor_metric_alert" "latency" {
  name                = "${local.name_prefix}-alert-latency"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when response time exceeds 2 minutes"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/duration"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 120000 # 2 minutes in milliseconds
  }

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }

  tags = local.common_tags
}

# ============================================================================
# BUDGET ALERTS
# ============================================================================

resource "azurerm_consumption_budget_resource_group" "monthly" {
  name              = "${local.name_prefix}-budget-monthly"
  resource_group_id = data.azurerm_resource_group.main.id

  amount     = var.budget_amount
  time_grain = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", timestamp())
  }

  # Warning alert at 83% ($299 of $360)
  notification {
    enabled        = true
    threshold      = var.budget_alert_threshold_warning
    operator       = "GreaterThan"
    threshold_type = "Actual"

    contact_emails = [var.owner_email]
  }

  # Critical alert at 93% ($335 of $360)
  notification {
    enabled        = true
    threshold      = var.budget_alert_threshold_critical
    operator       = "GreaterThan"
    threshold_type = "Actual"

    contact_emails = [var.owner_email]
  }

  # Forecasted overspend alert
  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Forecasted"

    contact_emails = [var.owner_email]
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.main.id
}

output "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}
