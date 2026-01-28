# ============================================================================
# Azure App Configuration Throttling Update Script
# ============================================================================
# Purpose: Update throttling limits for Azure OpenAI and agent request rates
#
# Why throttling?
# - Azure OpenAI Rate Limiting: Avoid 429 errors during peak load
# - Cost Control: Limit spending by controlling request rates
# - System Protection: Prevent cascading failures
#
# Usage:
#   .\update-throttling.ps1 -OpenAIRPM 50
#   .\update-throttling.ps1 -OpenAIRPM 50 -QueueEnabled $true -QueueMaxSize 100
#   .\update-throttling.ps1 -AgentRPS 20 -NATSGlobalRPS 100
#
# Load Test Results (2026-01-27):
# - 3 concurrent users: 13-15 req/min (stable)
# - 10 concurrent users: degradation due to Azure OpenAI rate limiting
# Recommendation: OpenAI RPM = 50, enable queuing
#
# See: tests/load/LOAD-TEST-REPORT-2026-01-27.md
# See: docs/PHASE-5-CONFIGURATION-INTERFACE.md
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [int]$OpenAIRPM = 0,

    [Parameter(Mandatory=$false)]
    [bool]$QueueEnabled = $null,

    [Parameter(Mandatory=$false)]
    [int]$QueueMaxSize = 0,

    [Parameter(Mandatory=$false)]
    [int]$AgentRPS = 0,

    [Parameter(Mandatory=$false)]
    [int]$NATSGlobalRPS = 0,

    [Parameter(Mandatory=$false)]
    [string]$AppConfigName = "",

    [Parameter(Mandatory=$false)]
    [string]$Label = "production"
)

# Check if any parameter was provided
$anyParamProvided = ($OpenAIRPM -gt 0) -or ($QueueEnabled -ne $null) -or ($QueueMaxSize -gt 0) -or ($AgentRPS -gt 0) -or ($NATSGlobalRPS -gt 0)

if (-not $anyParamProvided) {
    Write-Host ""
    Write-Host "===== Throttling Update Script =====" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\update-throttling.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -OpenAIRPM <int>      Azure OpenAI requests per minute (10-100)"
    Write-Host "  -QueueEnabled <bool>  Enable request queuing (true/false)"
    Write-Host "  -QueueMaxSize <int>   Maximum queue size (10-500)"
    Write-Host "  -AgentRPS <int>       Per-agent requests per second (5-50)"
    Write-Host "  -NATSGlobalRPS <int>  NATS global events per second (50-500)"
    Write-Host "  -AppConfigName        App Configuration name (auto-discovered)"
    Write-Host "  -Label                Configuration label (default: production)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\update-throttling.ps1 -OpenAIRPM 50"
    Write-Host "  .\update-throttling.ps1 -OpenAIRPM 50 -QueueEnabled `$true"
    Write-Host "  .\update-throttling.ps1 -AgentRPS 20 -NATSGlobalRPS 100"
    Write-Host ""
    exit 0
}

# Auto-discover App Configuration name if not provided
if ([string]::IsNullOrEmpty($AppConfigName)) {
    Write-Host "Auto-discovering App Configuration name..." -ForegroundColor Cyan

    $appConfigs = az appconfig list --resource-group agntcy-prod-rg --query "[].name" -o tsv 2>$null

    if ([string]::IsNullOrEmpty($appConfigs)) {
        Write-Error "No App Configuration found in resource group 'agntcy-prod-rg'. Please specify -AppConfigName."
        exit 1
    }

    $AppConfigName = ($appConfigs -split "`n")[0].Trim()
    Write-Host "Found App Configuration: $AppConfigName" -ForegroundColor Green
}

Write-Host ""
Write-Host "===== Updating Throttling Limits =====" -ForegroundColor Cyan
Write-Host "App Configuration: $AppConfigName"
Write-Host "Label:             $Label"
Write-Host ""

$updatedCount = 0

# Update OpenAI requests per minute
if ($OpenAIRPM -gt 0) {
    if ($OpenAIRPM -lt 10 -or $OpenAIRPM -gt 100) {
        Write-Warning "OpenAIRPM should be between 10-100. Got: $OpenAIRPM"
    }

    Write-Host "Setting throttle:openai_requests_per_minute = $OpenAIRPM" -ForegroundColor Yellow

    az appconfig kv set `
        --name $AppConfigName `
        --key "throttle:openai_requests_per_minute" `
        --value "$OpenAIRPM" `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "  Updated." -ForegroundColor Green
    $updatedCount++
}

# Update queue enabled
if ($QueueEnabled -ne $null) {
    $queueEnabledValue = if ($QueueEnabled) { "true" } else { "false" }

    Write-Host "Setting throttle:queue_enabled = $queueEnabledValue" -ForegroundColor Yellow

    az appconfig kv set `
        --name $AppConfigName `
        --key "throttle:queue_enabled" `
        --value $queueEnabledValue `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "  Updated." -ForegroundColor Green
    $updatedCount++
}

# Update queue max size
if ($QueueMaxSize -gt 0) {
    if ($QueueMaxSize -lt 10 -or $QueueMaxSize -gt 500) {
        Write-Warning "QueueMaxSize should be between 10-500. Got: $QueueMaxSize"
    }

    Write-Host "Setting throttle:queue_max_size = $QueueMaxSize" -ForegroundColor Yellow

    az appconfig kv set `
        --name $AppConfigName `
        --key "throttle:queue_max_size" `
        --value "$QueueMaxSize" `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "  Updated." -ForegroundColor Green
    $updatedCount++
}

# Update agent requests per second
if ($AgentRPS -gt 0) {
    if ($AgentRPS -lt 5 -or $AgentRPS -gt 50) {
        Write-Warning "AgentRPS should be between 5-50. Got: $AgentRPS"
    }

    Write-Host "Setting throttle:agent_rps = $AgentRPS" -ForegroundColor Yellow

    az appconfig kv set `
        --name $AppConfigName `
        --key "throttle:agent_rps" `
        --value "$AgentRPS" `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "  Updated." -ForegroundColor Green
    $updatedCount++
}

# Update NATS global requests per second
if ($NATSGlobalRPS -gt 0) {
    if ($NATSGlobalRPS -lt 50 -or $NATSGlobalRPS -gt 500) {
        Write-Warning "NATSGlobalRPS should be between 50-500. Got: $NATSGlobalRPS"
    }

    Write-Host "Setting throttle:nats_global_rps = $NATSGlobalRPS" -ForegroundColor Yellow

    az appconfig kv set `
        --name $AppConfigName `
        --key "throttle:nats_global_rps" `
        --value "$NATSGlobalRPS" `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "  Updated." -ForegroundColor Green
    $updatedCount++
}

Write-Host ""
Write-Host "===== Update Complete =====" -ForegroundColor Green
Write-Host "Settings updated: $updatedCount"
Write-Host ""
Write-Host "Note: Agents will pick up new values within 30 seconds."
Write-Host "Monitor Application Insights for any rate limiting errors."
