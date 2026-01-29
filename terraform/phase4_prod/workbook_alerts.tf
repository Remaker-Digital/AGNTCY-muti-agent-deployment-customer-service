# ============================================================================
# Workbook Alert Rules
# ============================================================================
# Purpose: Alert rules that complement the operational dashboard
#
# Phase 6 - Issue #169: Azure Workbooks Operational Dashboard
#
# Alert Categories:
# 1. Agent Performance - Response time, success rate per agent
# 2. LLM Provider - Cost spikes, token usage anomalies
# 3. Multi-Channel - WhatsApp webhook failures, widget errors
# 4. Session - Conversation anomalies, session expiry issues
#
# Related Documentation:
# - terraform/phase4_prod/workbook.tf - Dashboard visualizations
# - docs/ISSUE-169-IMPLEMENTATION-SUMMARY.md
# ============================================================================

# ============================================================================
# Action Group for Dashboard Alerts
# ============================================================================
resource "azurerm_monitor_action_group" "dashboard_alerts" {
  name                = "${local.name_prefix}-dashboard-alerts"
  resource_group_name = data.azurerm_resource_group.main.name
  short_name          = "dash-alrt"

  email_receiver {
    name                    = "ops-team"
    email_address           = var.owner_email
    use_common_alert_schema = true
  }

  tags = merge(local.common_tags, {
    component = "monitoring"
    purpose   = "dashboard-alerts"
  })
}

# ============================================================================
# Agent Performance Alerts
# ============================================================================

# Alert: Intent Classifier Slow Response
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "intent_classifier_slow" {
  name                = "${local.name_prefix}-intent-slow"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "Intent Classification agent P95 response time exceeds 500ms"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-KQL
      requests
      | where timestamp > ago(15m)
      | where name contains "intent"
      | summarize P95 = percentile(duration, 95)
      | where P95 > 500
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "agent-performance"
    agent      = "intent-classifier"
  })
}

# Alert: Response Generator Slow Response
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "response_generator_slow" {
  name                = "${local.name_prefix}-response-slow"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "Response Generator agent P95 response time exceeds 5 seconds"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-KQL
      requests
      | where timestamp > ago(15m)
      | where name contains "response"
      | summarize P95 = percentile(duration, 95)
      | where P95 > 5000
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "agent-performance"
    agent      = "response-generator"
  })
}

# Alert: Critic/Supervisor High Block Rate
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "critic_high_block_rate" {
  name                = "${local.name_prefix}-critic-high-block"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "Critic/Supervisor agent blocking >10% of legitimate requests"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-KQL
      customEvents
      | where timestamp > ago(15m)
      | where name == "content_validation"
      | extend Action = tostring(customDimensions.action)
      | summarize
          TotalValidations = count(),
          BlockCount = countif(Action == "BLOCK")
      | extend BlockRate = 100.0 * BlockCount / TotalValidations
      | where BlockRate > 10
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "agent-performance"
    agent      = "critic-supervisor"
  })
}

# ============================================================================
# LLM Provider Cost Alerts
# ============================================================================

# Alert: Daily Cost Spike
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "llm_cost_spike" {
  name                = "${local.name_prefix}-llm-cost-spike"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "LLM daily cost exceeds $5 (8% of monthly budget)"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT1H"
  window_duration      = "PT1H"

  criteria {
    query = <<-KQL
      customMetrics
      | where timestamp > ago(24h)
      | where name == "estimated_cost"
      | summarize DailyCost = sum(value)
      | where DailyCost > 5
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "cost"
    category   = "llm-provider"
  })
}

# Alert: Token Usage Anomaly
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "token_usage_anomaly" {
  name                = "${local.name_prefix}-token-anomaly"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "Unusually high token usage detected (>100K tokens/hour)"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT15M"
  window_duration      = "PT1H"

  criteria {
    query = <<-KQL
      customMetrics
      | where timestamp > ago(1h)
      | where name == "total_tokens"
      | summarize TotalTokens = sum(value)
      | where TotalTokens > 100000
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "cost"
    category   = "token-usage"
  })
}

# Alert: Provider Fallback Triggered
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "provider_fallback" {
  name                = "${local.name_prefix}-provider-fallback"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "LLM provider fallback triggered (primary provider failing)"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-KQL
      customEvents
      | where timestamp > ago(15m)
      | where name == "llm_request"
      | extend FallbackUsed = tobool(customDimensions.fallback_used)
      | where FallbackUsed == true
      | summarize FallbackCount = count()
      | where FallbackCount > 5
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "reliability"
    category   = "llm-provider"
  })
}

# ============================================================================
# Multi-Channel Alerts
# ============================================================================

# Alert: WhatsApp Webhook Failures
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "whatsapp_webhook_failures" {
  name                = "${local.name_prefix}-whatsapp-failures"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "WhatsApp webhook processing failures detected"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 1  # Critical
  evaluation_frequency = "PT5M"
  window_duration      = "PT5M"

  criteria {
    query = <<-KQL
      requests
      | where timestamp > ago(5m)
      | where name contains "whatsapp/webhook"
      | where success == false
      | summarize FailedCount = count()
      | where FailedCount > 3
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "channel"
    channel    = "whatsapp"
  })
}

# Alert: Widget Error Rate High
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "widget_error_rate" {
  name                = "${local.name_prefix}-widget-errors"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "Web widget error rate exceeds 5%"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"

  criteria {
    query = <<-KQL
      requests
      | where timestamp > ago(15m)
      | where name contains "widget"
      | summarize
          TotalRequests = count(),
          ErrorCount = countif(success == false)
      | extend ErrorRate = 100.0 * ErrorCount / TotalRequests
      | where ErrorRate > 5
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "channel"
    channel    = "web-widget"
  })
}

# ============================================================================
# Session Health Alerts
# ============================================================================

# Alert: High Session Expiry Rate
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "session_expiry_high" {
  name                = "${local.name_prefix}-session-expiry-high"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "High session expiry rate indicates possible connectivity issues"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT15M"
  window_duration      = "PT1H"

  criteria {
    query = <<-KQL
      customEvents
      | where timestamp > ago(1h)
      | where name in ("session_created", "session_expired")
      | summarize
          Created = countif(name == "session_created"),
          Expired = countif(name == "session_expired")
      | extend ExpiryRate = 100.0 * Expired / Created
      | where ExpiryRate > 50
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "session"
    category   = "health"
  })
}

# ============================================================================
# Escalation Alerts
# ============================================================================

# Alert: High Escalation Rate
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "high_escalation_rate" {
  name                = "${local.name_prefix}-high-escalation"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  description         = "Escalation rate exceeds 30% (may indicate model issues)"

  scopes               = [azurerm_application_insights.main.id]
  severity             = 2  # Warning
  evaluation_frequency = "PT15M"
  window_duration      = "PT1H"

  criteria {
    query = <<-KQL
      customEvents
      | where timestamp > ago(1h)
      | where name == "escalation_decision"
      | extend Escalated = tobool(customDimensions.escalate)
      | summarize
          TotalDecisions = count(),
          EscalatedCount = countif(Escalated == true)
      | extend EscalationRate = 100.0 * EscalatedCount / TotalDecisions
      | where EscalationRate > 30
    KQL

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.dashboard_alerts.id]
  }

  tags = merge(local.common_tags, {
    alert_type = "agent-performance"
    agent      = "escalation"
  })
}
