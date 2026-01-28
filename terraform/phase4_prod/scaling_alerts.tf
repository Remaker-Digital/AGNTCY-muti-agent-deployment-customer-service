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
# NOTE: The "Replicas" metric is not available at the managedEnvironments level.
# Container App replica monitoring should use Log Analytics queries or Application
# Insights custom metrics instead. These alerts are disabled for now.
#
# Available metrics on managedEnvironments:
# - EnvCoresQuotaLimit, EnvCoresQuotaUtilization (deprecated)
# - NodeCount (preview)
# - IngressUsageNanoCores, IngressUsageBytes, IngressCpuPercentage, IngressMemoryPercentage
# ============================================================================

# Alert: High environment CPU usage
# Trigger: When ingress CPU exceeds 80%
resource "azurerm_monitor_metric_alert" "high_env_cpu" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-high-env-cpu"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_container_app_environment.main[0].id]
  description         = "Container Apps Environment ingress CPU usage high. Review scaling."

  severity    = 2  # Warning
  frequency   = "PT5M"
  window_size = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/managedEnvironments"
    metric_name      = "IngressCpuPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.scaling_ops[0].id
  }

  tags = merge(local.common_tags, {
    alert_type = "capacity"
  })
}

# ============================================================================
# Performance Alerts (Log Analytics based)
# ============================================================================
# Container App-level metrics (Requests, RequestDuration) require the apps to
# exist first. Using Log Analytics scheduled query alerts instead for
# reliability during deployment.
# ============================================================================

# Alert: High Response Time (Log Analytics based)
# Trigger: Average response time exceeds 20 seconds
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "high_latency" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-high-latency"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "API Gateway response time exceeds threshold. Check Azure OpenAI latency."

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-QUERY
      requests
      | where timestamp > ago(15m)
      | where cloud_RoleName has "api-gateway"
      | summarize AvgDuration = avg(duration) by bin(timestamp, 5m)
      | where AvgDuration > 20000
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.scaling_ops[0].id]
  }

  tags = merge(local.common_tags, {
    alert_type = "performance"
  })
}

# Alert: High Error Rate (Log Analytics based)
# Trigger: More than 5% of requests are 5xx errors
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "high_error_rate" {
  count = var.enable_container_apps ? 1 : 0

  name                = "${local.name_prefix}-high-error-rate"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "API Gateway error rate exceeds 5%. Investigate failed requests."

  scopes               = [azurerm_application_insights.main.id]
  severity             = 1  # Critical
  evaluation_frequency = "PT5M"  # 5-minute frequency required for this query type
  window_duration      = "PT5M"

  criteria {
    query = <<-QUERY
      requests
      | where timestamp > ago(5m)
      | where cloud_RoleName has "api-gateway"
      | summarize
          TotalRequests = count(),
          ErrorCount = countif(resultCode startswith "5")
      | extend ErrorRate = 100.0 * ErrorCount / TotalRequests
      | where ErrorRate > 5
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.scaling_ops[0].id]
  }

  tags = merge(local.common_tags, {
    alert_type = "performance"
  })
}

# ============================================================================
# Cost Alerts (Using Consumption Budget)
# ============================================================================
# Note: Azure Monitor metric alerts don't support Microsoft.CostManagement
# directly. Using azurerm_consumption_budget for proper budget monitoring.
#
# Why Consumption Budget?
# - Native Azure Cost Management integration
# - Proper forecasting support
# - Action group notifications
# - See: https://learn.microsoft.com/azure/cost-management-billing/costs/tutorial-acm-create-budgets
# ============================================================================

resource "azurerm_consumption_budget_resource_group" "scaling_budget" {
  count = var.enable_container_apps ? 1 : 0

  name              = "${local.name_prefix}-scaling-budget"
  resource_group_id = data.azurerm_resource_group.main.id

  amount     = 600  # Monthly budget in USD
  time_grain = "Monthly"

  time_period {
    start_date = "2026-02-01T00:00:00Z"  # Start of next budget period
  }

  # Warning notification at 70% ($420)
  notification {
    enabled        = true
    threshold      = 70
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"

    contact_emails = [var.owner_email]
  }

  # Critical notification at 85% ($510)
  notification {
    enabled        = true
    threshold      = 85
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"

    contact_emails = [var.owner_email]
  }

  # Forecast notification at 100%
  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Forecasted"

    contact_emails = [var.owner_email]
  }
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

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT5M"
  window_duration      = "PT5M"

  criteria {
    query = <<-QUERY
      requests
      | where timestamp > ago(5m)
      | where name contains "openai"
      | where resultCode == "429"
      | summarize ThrottleCount = count() by bin(timestamp, 5m)
    QUERY

    time_aggregation_method = "Total"
    threshold               = 10
    operator                = "GreaterThan"
    metric_measure_column   = "ThrottleCount"
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
