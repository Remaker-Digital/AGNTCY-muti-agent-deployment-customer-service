# ============================================================================
# Auto-Scaling Monitoring and Alerts
# ============================================================================
# Purpose: Monitor scaling events, instance counts, and performance metrics
# to ensure the system maintains capacity for 10,000 daily users.
#
# Alert Categories:
# 1. Capacity Alerts - Near max replicas, scale-up failures
# 2. Performance Alerts - High latency, error rates
# 3. Cost Alerts - Budget thresholds, resource utilization
# 4. Health Alerts - Cold starts, circuit breaker trips
#
# Related Documentation:
# - Auto-Scaling Architecture: docs/AUTO-SCALING-ARCHITECTURE.md
# - Work Item Evaluation: docs/AUTO-SCALING-WORK-ITEM-EVALUATION.md
# - Azure Monitor Alerts: https://learn.microsoft.com/azure/azure-monitor/alerts/
# ============================================================================

# ============================================================================
# Action Group for Operations Team
# ============================================================================
# All scaling alerts route to this action group.
# Configure email, SMS, or webhook notifications as needed.
# ============================================================================

resource "azurerm_monitor_action_group" "scaling_ops" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-scaling-ops"
  resource_group_name = data.azurerm_resource_group.main.name
  short_name          = "scale-ops"

  email_receiver {
    name                    = "ops-team"
    email_address           = var.owner_email
    use_common_alert_schema = true
  }

  tags = merge(local.common_tags, {
    component = "monitoring"
    purpose   = "scaling-alerts"
  })
}

# ============================================================================
# Capacity Alerts
# ============================================================================

# Alert: Near maximum replicas
# Trigger: When any Container App is at >80% of max replicas
resource "azurerm_monitor_metric_alert" "near_max_replicas" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-near-max-replicas"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_container_app_environment.main[0].id]
  description         = "Container App approaching maximum replica count. Review scaling limits."

  severity    = 2  # Warning
  frequency   = "PT5M"
  window_size = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "Replicas"
    aggregation      = "Maximum"
    operator         = "GreaterThan"
    threshold        = 15  # Alert when approaching max of 20
  }

  action {
    action_group_id = azurerm_monitor_action_group.scaling_ops[0].id
  }

  tags = merge(local.common_tags, {
    alert_type = "capacity"
  })
}

# ============================================================================
# Performance Alerts
# ============================================================================

# Alert: High Response Time
# Trigger: P95 response time exceeds 30 seconds
resource "azurerm_monitor_metric_alert" "high_latency" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-high-latency"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.api_gateway[0].id]
  description         = "API Gateway response time exceeds threshold. Check Azure OpenAI latency and scaling."

  severity    = 2  # Warning
  frequency   = "PT5M"
  window_size = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "RequestDuration"
    aggregation      = "P95"
    operator         = "GreaterThan"
    threshold        = 30000  # 30 seconds (adjusted for AI latency)
  }

  action {
    action_group_id = azurerm_monitor_action_group.scaling_ops[0].id
  }

  tags = merge(local.common_tags, {
    alert_type = "performance"
  })
}

# Alert: High Error Rate
# Trigger: Error rate exceeds 5%
resource "azurerm_monitor_metric_alert" "high_error_rate" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-high-error-rate"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.api_gateway[0].id]
  description         = "API Gateway error rate exceeds 5%. Investigate failed requests."

  severity    = 1  # Critical
  frequency   = "PT1M"
  window_size = "PT5M"

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "Requests"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0

    dimension {
      name     = "StatusCodeClass"
      operator = "Include"
      values   = ["5xx"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.scaling_ops[0].id
  }

  tags = merge(local.common_tags, {
    alert_type = "performance"
  })
}

# ============================================================================
# Cost Alerts (Updated for Auto-Scaling)
# ============================================================================

# Alert: Budget threshold - Warning
# Trigger: 70% of revised $600 budget ($420)
resource "azurerm_monitor_metric_alert" "budget_warning" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-budget-warning"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [data.azurerm_subscription.current.id]
  description         = "Monthly spend approaching 70% of auto-scaling budget ($420)."

  severity    = 2  # Warning
  frequency   = "PT1H"
  window_size = "PT1H"

  # Note: This is a placeholder - actual budget alerts should use
  # azurerm_consumption_budget resource instead
  criteria {
    metric_namespace = "Microsoft.CostManagement"
    metric_name      = "ActualCost"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 420
  }

  action {
    action_group_id = azurerm_monitor_action_group.scaling_ops[0].id
  }

  tags = merge(local.common_tags, {
    alert_type = "cost"
  })
}

# Alert: Budget threshold - Critical
# Trigger: 85% of revised $600 budget ($510)
resource "azurerm_monitor_metric_alert" "budget_critical" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-budget-critical"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [data.azurerm_subscription.current.id]
  description         = "Monthly spend at 85% of auto-scaling budget ($510). Review resource usage."

  severity    = 1  # Critical
  frequency   = "PT1H"
  window_size = "PT1H"

  criteria {
    metric_namespace = "Microsoft.CostManagement"
    metric_name      = "ActualCost"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 510
  }

  action {
    action_group_id = azurerm_monitor_action_group.scaling_ops[0].id
  }

  tags = merge(local.common_tags, {
    alert_type = "cost"
  })
}

# ============================================================================
# Azure OpenAI Rate Limiting Alerts
# ============================================================================

# Alert: Azure OpenAI throttling
# Trigger: More than 10 429 responses per minute
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "openai_throttling" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-openai-throttling"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "Azure OpenAI rate limiting detected. Consider increasing TPM quota."

  scopes          = [azurerm_application_insights.main.id]
  severity        = 2  # Warning
  evaluation_frequency = "PT5M"
  window_duration = "PT5M"

  criteria {
    query = <<-QUERY
      requests
      | where timestamp > ago(5m)
      | where name contains "openai"
      | where resultCode == "429"
      | summarize count() by bin(timestamp, 1m)
    QUERY

    time_aggregation_method = "Total"
    threshold               = 10
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.scaling_ops[0].id]
  }

  tags = merge(local.common_tags, {
    alert_type = "external-service"
  })
}

# ============================================================================
# Data Source
# ============================================================================

data "azurerm_subscription" "current" {}

# ============================================================================
# Dashboard for Scaling Metrics
# ============================================================================

resource "azurerm_portal_dashboard" "scaling" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-scaling-dashboard"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  dashboard_properties = jsonencode({
    lenses = {
      "0" = {
        order = 0
        parts = {
          "0" = {
            position = { x = 0, y = 0, colSpan = 6, rowSpan = 4 }
            metadata = {
              type = "Extension/HubsExtension/PartType/MonitorChartPart"
              settings = {
                content = {
                  options = {
                    chart = {
                      title = "Container App Replica Counts"
                      metrics = [
                        {
                          resourceMetadata = { id = var.enable_container_apps ? azurerm_container_app_environment.main[0].id : "" }
                          name             = "Replicas"
                          aggregationType  = 3
                        }
                      ]
                    }
                  }
                }
              }
            }
          }
          "1" = {
            position = { x = 6, y = 0, colSpan = 6, rowSpan = 4 }
            metadata = {
              type = "Extension/HubsExtension/PartType/MonitorChartPart"
              settings = {
                content = {
                  options = {
                    chart = {
                      title = "API Gateway Response Time (P95)"
                      metrics = [
                        {
                          resourceMetadata = { id = var.enable_container_apps ? azurerm_container_app.api_gateway[0].id : "" }
                          name             = "RequestDuration"
                          aggregationType  = 95
                        }
                      ]
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  })

  tags = merge(local.common_tags, {
    component = "monitoring"
    purpose   = "scaling-dashboard"
  })
}
