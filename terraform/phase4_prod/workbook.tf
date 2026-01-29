# ============================================================================
# Azure Monitor Workbook - Operational Dashboard
# ============================================================================
# Purpose: Comprehensive operational dashboard for the multi-agent customer
# service platform. Provides real-time visibility into:
# - Agent performance and health
# - LLM provider costs and usage
# - Request metrics and error tracking
# - System capacity and scaling status
#
# Phase 6 - Issue #169: Azure Workbooks Operational Dashboard
#
# Related Documentation:
# - Azure Workbooks: https://learn.microsoft.com/azure/azure-monitor/visualize/workbooks-overview
# - KQL Reference: https://learn.microsoft.com/azure/data-explorer/kusto/query/
# - docs/ISSUE-169-IMPLEMENTATION-SUMMARY.md
#
# Cost Impact: Minimal (~$0-2/month for workbook queries)
# Workbooks themselves are free; costs are from underlying Log Analytics queries.
# ============================================================================

# ============================================================================
# Workbook: Agent Performance & Operations
# ============================================================================
resource "azurerm_application_insights_workbook" "operations" {
  name                = "agntcy-operations-workbook"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  display_name        = "AGNTCY - Operations Dashboard"
  description         = "Operational dashboard for AGNTCY Multi-Agent Customer Service Platform"

  # Category for Azure Portal navigation
  category = "workbook"

  # Source: Application Insights linked to this workbook
  source_id = azurerm_application_insights.main.id

  # Workbook JSON template
  data_json = jsonencode({
    version = "Notebook/1.0"
    items = [
      # =====================================================================
      # Overview Section
      # =====================================================================
      {
        type = 1  # Markdown
        content = {
          json = <<-MARKDOWN
            # AGNTCY Operations Dashboard

            Real-time monitoring for the Multi-Agent Customer Service Platform.

            **Quick Links:**
            - [Application Insights](${azurerm_application_insights.main.id})
            - [Log Analytics](${azurerm_log_analytics_workspace.main.id})
            - [Cost Analysis](https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/costanalysis)
          MARKDOWN
        }
        name = "overview-header"
      },

      # =====================================================================
      # Time Range Parameter
      # =====================================================================
      {
        type = 9  # Parameter
        content = {
          version       = "KqlParameterItem/1.0"
          parameters    = [
            {
              id            = "time-range"
              version       = "KqlParameterItem/1.0"
              name          = "TimeRange"
              type          = 4  # Time range
              isRequired    = true
              value         = { durationMs = 3600000 }  # 1 hour default
              typeSettings  = {
                selectableValues = [
                  { durationMs = 300000, displayName = "Last 5 minutes" },
                  { durationMs = 900000, displayName = "Last 15 minutes" },
                  { durationMs = 1800000, displayName = "Last 30 minutes" },
                  { durationMs = 3600000, displayName = "Last hour" },
                  { durationMs = 14400000, displayName = "Last 4 hours" },
                  { durationMs = 43200000, displayName = "Last 12 hours" },
                  { durationMs = 86400000, displayName = "Last 24 hours" },
                  { durationMs = 604800000, displayName = "Last 7 days" }
                ]
              }
            }
          ]
          style         = "pills"
          queryType     = 0
        }
        name = "time-range-parameter"
      },

      # =====================================================================
      # Key Metrics Summary (Tiles)
      # =====================================================================
      {
        type = 3  # Query
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            requests
            | where timestamp >= ago(1h)
            | summarize
                TotalRequests = count(),
                SuccessfulRequests = countif(success == true),
                FailedRequests = countif(success == false),
                AvgDuration = avg(duration)
            | extend
                SuccessRate = round(100.0 * SuccessfulRequests / TotalRequests, 2),
                AvgDurationSec = round(AvgDuration / 1000, 2)
            | project
                ['Total Requests'] = TotalRequests,
                ['Success Rate (%)'] = SuccessRate,
                ['Failed Requests'] = FailedRequests,
                ['Avg Response (sec)'] = AvgDurationSec
          KQL
          size         = 4  # Tiles
          queryType    = 0  # Log Analytics
          resourceType = "microsoft.insights/components"
          visualization = "tiles"
          tileSettings = {
            showBorder    = false
            titleContent  = { columnMatch = "column", formatter = 1 }
            leftContent   = { columnMatch = "value", formatter = 12 }
          }
        }
        name = "key-metrics-tiles"
      },

      # =====================================================================
      # Agent Performance Section
      # =====================================================================
      {
        type = 1
        content = {
          json = "## Agent Performance"
        }
        name = "agent-performance-header"
      },

      # Agent Request Distribution Chart
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            requests
            | where timestamp >= ago(1h)
            | extend AgentName = case(
                name contains "intent", "Intent Classifier",
                name contains "knowledge", "Knowledge Retrieval",
                name contains "response", "Response Generator",
                name contains "escalation", "Escalation Handler",
                name contains "analytics", "Analytics Agent",
                name contains "critic", "Critic/Supervisor",
                cloud_RoleName
            )
            | summarize RequestCount = count() by AgentName
            | order by RequestCount desc
          KQL
          size         = 1
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "piechart"
          chartSettings = {
            showLegend = true
          }
        }
        customWidth = "50"
        name = "agent-request-distribution"
      },

      # Agent Response Time Chart
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            requests
            | where timestamp >= ago(1h)
            | extend AgentName = case(
                name contains "intent", "Intent Classifier",
                name contains "knowledge", "Knowledge Retrieval",
                name contains "response", "Response Generator",
                name contains "escalation", "Escalation Handler",
                name contains "analytics", "Analytics Agent",
                name contains "critic", "Critic/Supervisor",
                cloud_RoleName
            )
            | summarize
                AvgDuration = avg(duration),
                P95Duration = percentile(duration, 95),
                P99Duration = percentile(duration, 99)
                by AgentName
            | project
                AgentName,
                ['Avg (ms)'] = round(AvgDuration, 1),
                ['P95 (ms)'] = round(P95Duration, 1),
                ['P99 (ms)'] = round(P99Duration, 1)
            | order by ['Avg (ms)'] desc
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
          gridSettings = {
            formatters = [
              { columnMatch = "Avg (ms)", formatter = 3, formatOptions = { palette = "greenRed" } },
              { columnMatch = "P95 (ms)", formatter = 3, formatOptions = { palette = "greenRed" } },
              { columnMatch = "P99 (ms)", formatter = 3, formatOptions = { palette = "greenRed" } }
            ]
          }
        }
        customWidth = "50"
        name = "agent-response-times"
      },

      # Agent Performance Over Time
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            requests
            | where timestamp >= ago(4h)
            | extend AgentName = case(
                name contains "intent", "Intent Classifier",
                name contains "knowledge", "Knowledge Retrieval",
                name contains "response", "Response Generator",
                name contains "escalation", "Escalation Handler",
                name contains "analytics", "Analytics Agent",
                name contains "critic", "Critic/Supervisor",
                cloud_RoleName
            )
            | summarize AvgDuration = avg(duration) by AgentName, bin(timestamp, 5m)
            | render timechart
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "timechart"
          chartSettings = {
            showLegend = true
            yAxis      = { label = "Duration (ms)" }
          }
        }
        name = "agent-performance-timechart"
      },

      # =====================================================================
      # LLM Provider Cost Tracking Section
      # =====================================================================
      {
        type = 1
        content = {
          json = "## LLM Provider Metrics"
        }
        name = "llm-metrics-header"
      },

      # Token Usage by Model
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            customMetrics
            | where timestamp >= ago(1h)
            | where name in ("prompt_tokens", "completion_tokens", "total_tokens")
            | extend Model = tostring(customDimensions.model)
            | summarize TotalTokens = sum(value) by Model, name
            | evaluate pivot(name, sum(TotalTokens))
            | project
                Model,
                ['Prompt Tokens'] = prompt_tokens,
                ['Completion Tokens'] = completion_tokens,
                ['Total Tokens'] = total_tokens
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
          gridSettings = {
            formatters = [
              { columnMatch = "Prompt Tokens", formatter = 0, numberFormat = { unit = 0, options = { style = "decimal" } } },
              { columnMatch = "Completion Tokens", formatter = 0, numberFormat = { unit = 0, options = { style = "decimal" } } },
              { columnMatch = "Total Tokens", formatter = 0, numberFormat = { unit = 0, options = { style = "decimal" } } }
            ]
          }
        }
        customWidth = "50"
        name = "token-usage-by-model"
      },

      # Estimated Cost by Provider
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            customMetrics
            | where timestamp >= ago(24h)
            | where name == "estimated_cost"
            | extend Provider = tostring(customDimensions.provider)
            | summarize
                TotalCost = sum(value),
                RequestCount = count()
                by Provider
            | project
                Provider,
                ['Est. Cost ($)'] = round(TotalCost, 4),
                ['Requests'] = RequestCount,
                ['Avg Cost/Req ($)'] = round(TotalCost / RequestCount, 6)
            | order by ['Est. Cost ($)'] desc
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
        }
        customWidth = "50"
        name = "cost-by-provider"
      },

      # Cost Over Time
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            customMetrics
            | where timestamp >= ago(7d)
            | where name == "estimated_cost"
            | extend Provider = tostring(customDimensions.provider)
            | summarize DailyCost = sum(value) by Provider, bin(timestamp, 1d)
            | render timechart
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "timechart"
          chartSettings = {
            showLegend = true
            yAxis      = { label = "Cost ($)" }
          }
        }
        name = "cost-over-time"
      },

      # =====================================================================
      # Error Tracking Section
      # =====================================================================
      {
        type = 1
        content = {
          json = "## Error Tracking"
        }
        name = "error-tracking-header"
      },

      # Error Rate Over Time
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            requests
            | where timestamp >= ago(4h)
            | summarize
                TotalRequests = count(),
                FailedRequests = countif(success == false)
                by bin(timestamp, 5m)
            | extend ErrorRate = round(100.0 * FailedRequests / TotalRequests, 2)
            | project timestamp, ErrorRate
            | render timechart
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "timechart"
          chartSettings = {
            yAxis = { label = "Error Rate (%)" }
          }
        }
        customWidth = "50"
        name = "error-rate-chart"
      },

      # Top Errors Table
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            exceptions
            | where timestamp >= ago(1h)
            | summarize Count = count() by type, outerMessage
            | order by Count desc
            | take 10
            | project
                ['Exception Type'] = type,
                ['Message'] = outerMessage,
                ['Count'] = Count
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
          gridSettings = {
            formatters = [
              { columnMatch = "Count", formatter = 3, formatOptions = { palette = "redGreen", max = 100 } }
            ]
          }
        }
        customWidth = "50"
        name = "top-errors-table"
      },

      # =====================================================================
      # System Health Section
      # =====================================================================
      {
        type = 1
        content = {
          json = "## System Health"
        }
        name = "system-health-header"
      },

      # Dependency Health
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            dependencies
            | where timestamp >= ago(1h)
            | extend ServiceName = case(
                target contains "openai", "Azure OpenAI",
                target contains "cosmos", "Cosmos DB",
                target contains "shopify", "Shopify API",
                target contains "zendesk", "Zendesk API",
                target contains "whatsapp", "WhatsApp API",
                type
            )
            | summarize
                TotalCalls = count(),
                SuccessfulCalls = countif(success == true),
                AvgDuration = avg(duration)
                by ServiceName
            | extend SuccessRate = round(100.0 * SuccessfulCalls / TotalCalls, 2)
            | project
                ServiceName,
                ['Success Rate (%)'] = SuccessRate,
                ['Calls'] = TotalCalls,
                ['Avg Duration (ms)'] = round(AvgDuration, 1)
            | order by ['Success Rate (%)'] asc
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
          gridSettings = {
            formatters = [
              { columnMatch = "Success Rate (%)", formatter = 3, formatOptions = { palette = "redGreen", min = 90, max = 100 } },
              { columnMatch = "Avg Duration (ms)", formatter = 3, formatOptions = { palette = "greenRed" } }
            ]
          }
        }
        customWidth = "50"
        name = "dependency-health"
      },

      # Request Volume Over Time
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            requests
            | where timestamp >= ago(4h)
            | summarize RequestCount = count() by bin(timestamp, 5m)
            | render timechart
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "timechart"
          chartSettings = {
            yAxis = { label = "Requests / 5 min" }
          }
        }
        customWidth = "50"
        name = "request-volume-chart"
      },

      # =====================================================================
      # Multi-Channel Metrics Section
      # =====================================================================
      {
        type = 1
        content = {
          json = "## Multi-Channel Activity"
        }
        name = "multi-channel-header"
      },

      # Channel Distribution
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            requests
            | where timestamp >= ago(1h)
            | extend Channel = case(
                name contains "widget", "Web Widget",
                name contains "whatsapp", "WhatsApp",
                name contains "api/v1", "API",
                "Other"
            )
            | summarize RequestCount = count() by Channel
            | order by RequestCount desc
          KQL
          size         = 1
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "piechart"
        }
        customWidth = "50"
        name = "channel-distribution"
      },

      # Sessions by Channel
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            customEvents
            | where timestamp >= ago(1h)
            | where name == "session_created" or name == "conversation_started"
            | extend Channel = tostring(customDimensions.channel)
            | summarize SessionCount = dcount(tostring(customDimensions.session_id)) by Channel
            | order by SessionCount desc
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
        }
        customWidth = "50"
        name = "sessions-by-channel"
      },

      # =====================================================================
      # Footer
      # =====================================================================
      {
        type = 1
        content = {
          json = <<-MARKDOWN
            ---
            **Dashboard Version:** 1.0.0 | **Last Updated:** Phase 6 - Issue #169

            For support, see [Operations Runbook](../docs/RUNBOOK-AUTO-SCALING-OPERATIONS.md)
          MARKDOWN
        }
        name = "footer"
      }
    ]
    isLocked = false
    fallbackResourceIds = [azurerm_application_insights.main.id]
  })

  tags = merge(local.common_tags, {
    component = "monitoring"
    purpose   = "operational-dashboard"
    phase     = "6"
  })
}

# ============================================================================
# Workbook: Cost Analysis Deep Dive
# ============================================================================
resource "azurerm_application_insights_workbook" "cost_analysis" {
  name                = "agntcy-cost-analysis-workbook"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = local.location
  display_name        = "AGNTCY - Cost Analysis"
  description         = "Detailed cost tracking for LLM providers and Azure resources"
  category            = "workbook"
  source_id           = azurerm_application_insights.main.id

  data_json = jsonencode({
    version = "Notebook/1.0"
    items = [
      {
        type = 1
        content = {
          json = <<-MARKDOWN
            # LLM Cost Analysis Dashboard

            Track and optimize LLM provider costs across the platform.

            ## Budget Status
            - **Monthly Budget:** $60.00 (AI models)
            - **Alert at:** 80% ($48.00)
          MARKDOWN
        }
        name = "cost-header"
      },

      # Daily Cost Trend
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            customMetrics
            | where timestamp >= ago(30d)
            | where name == "estimated_cost"
            | summarize DailyCost = sum(value) by bin(timestamp, 1d)
            | render timechart
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "timechart"
          chartSettings = {
            yAxis      = { label = "Daily Cost ($)" }
            seriesLabelSettings = [
              { series = "DailyCost", label = "Daily Cost" }
            ]
          }
        }
        name = "daily-cost-trend"
      },

      # Cost by Agent
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            customMetrics
            | where timestamp >= ago(7d)
            | where name == "estimated_cost"
            | extend AgentName = tostring(customDimensions.agent_name)
            | summarize
                TotalCost = sum(value),
                TotalTokens = sumif(value, name == "total_tokens"),
                RequestCount = count()
                by AgentName
            | project
                AgentName,
                ['Total Cost ($)'] = round(TotalCost, 4),
                ['Requests'] = RequestCount,
                ['Cost/Request ($)'] = round(TotalCost / RequestCount, 6)
            | order by ['Total Cost ($)'] desc
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
        }
        name = "cost-by-agent"
      },

      # Model Comparison
      {
        type = 3
        content = {
          version      = "KqlItem/1.0"
          query        = <<-KQL
            customMetrics
            | where timestamp >= ago(7d)
            | where name in ("prompt_tokens", "completion_tokens", "estimated_cost")
            | extend Model = tostring(customDimensions.model)
            | summarize
                TotalCost = sumif(value, name == "estimated_cost"),
                PromptTokens = sumif(value, name == "prompt_tokens"),
                CompletionTokens = sumif(value, name == "completion_tokens")
                by Model
            | extend
                TotalTokens = PromptTokens + CompletionTokens,
                CostPer1KTokens = round(1000 * TotalCost / (PromptTokens + CompletionTokens), 4)
            | project
                Model,
                ['Total Cost ($)'] = round(TotalCost, 4),
                ['Total Tokens'] = TotalTokens,
                ['$/1K Tokens'] = CostPer1KTokens
            | order by ['Total Cost ($)'] desc
          KQL
          size         = 0
          queryType    = 0
          resourceType = "microsoft.insights/components"
          visualization = "table"
        }
        name = "model-comparison"
      }
    ]
    isLocked = false
    fallbackResourceIds = [azurerm_application_insights.main.id]
  })

  tags = merge(local.common_tags, {
    component = "monitoring"
    purpose   = "cost-analysis"
    phase     = "6"
  })
}

# ============================================================================
# Output: Workbook URLs
# ============================================================================
output "operations_workbook_id" {
  description = "Operations Dashboard Workbook ID"
  value       = azurerm_application_insights_workbook.operations.id
}

output "cost_analysis_workbook_id" {
  description = "Cost Analysis Workbook ID"
  value       = azurerm_application_insights_workbook.cost_analysis.id
}
