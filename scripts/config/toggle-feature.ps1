# ============================================================================
# Azure App Configuration Feature Flag Toggle Script
# ============================================================================
# Purpose: Enable or disable feature flags for A/B testing and gradual rollouts
#
# Why feature flags?
# - A/B Testing: Test new features with a subset of users
# - Gradual Rollout: 10% → 25% → 50% → 100%
# - Kill Switch: Disable problematic features instantly
# - No Code Deploy: Change behavior without redeployment
#
# Usage:
#   .\toggle-feature.ps1 -Feature rag_enabled -Enable
#   .\toggle-feature.ps1 -Feature critic_supervisor_enabled -Disable
#   .\toggle-feature.ps1 -List
#
# Available Features:
#   - rag_enabled: RAG pipeline for knowledge retrieval
#   - critic_supervisor_enabled: Content validation
#   - pii_tokenization_enabled: PII tokenization for AI calls
#   - multi_language_enabled: French Canadian and Spanish support
#   - auto_scaling_enabled: Container Apps auto-scaling
#
# See: docs/PHASE-5-CONFIGURATION-INTERFACE.md
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Feature = "",

    [Parameter(Mandatory=$false)]
    [switch]$Enable = $false,

    [Parameter(Mandatory=$false)]
    [switch]$Disable = $false,

    [Parameter(Mandatory=$false)]
    [switch]$List = $false,

    [Parameter(Mandatory=$false)]
    [string]$AppConfigName = "",

    [Parameter(Mandatory=$false)]
    [string]$Label = "production"
)

# Auto-discover App Configuration name if not provided
if ([string]::IsNullOrEmpty($AppConfigName)) {
    $appConfigs = az appconfig list --resource-group agntcy-prod-rg --query "[].name" -o tsv 2>$null

    if ([string]::IsNullOrEmpty($appConfigs)) {
        Write-Error "No App Configuration found in resource group 'agntcy-prod-rg'. Please specify -AppConfigName."
        exit 1
    }

    $AppConfigName = ($appConfigs -split "`n")[0].Trim()
}

# List all feature flags
if ($List) {
    Write-Host ""
    Write-Host "===== Feature Flags =====" -ForegroundColor Cyan
    Write-Host "App Configuration: $AppConfigName"
    Write-Host "Label:             $Label"
    Write-Host ""

    $features = az appconfig feature list --name $AppConfigName --label $Label -o json | ConvertFrom-Json

    if ($features.Count -eq 0) {
        Write-Host "No feature flags found." -ForegroundColor Yellow
    } else {
        Write-Host "Feature Name                    Enabled    Description"
        Write-Host "------------------------------  ---------  -----------"

        foreach ($f in $features) {
            $name = $f.name.PadRight(30)
            $enabled = if ($f.enabled) { "Yes".PadRight(9) } else { "No".PadRight(9) }
            $desc = if ($f.description) { $f.description.Substring(0, [Math]::Min(40, $f.description.Length)) } else { "" }

            $color = if ($f.enabled) { "Green" } else { "Yellow" }
            Write-Host "$name  $enabled  $desc" -ForegroundColor $color
        }
    }

    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\toggle-feature.ps1 -Feature <name> -Enable"
    Write-Host "  .\toggle-feature.ps1 -Feature <name> -Disable"
    Write-Host ""
    exit 0
}

# Validate parameters
if ([string]::IsNullOrEmpty($Feature)) {
    Write-Host ""
    Write-Host "===== Feature Flag Toggle Script =====" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\toggle-feature.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Feature <name>    Feature flag name"
    Write-Host "  -Enable            Enable the feature"
    Write-Host "  -Disable           Disable the feature"
    Write-Host "  -List              List all feature flags"
    Write-Host "  -AppConfigName     App Configuration name (auto-discovered)"
    Write-Host "  -Label             Configuration label (default: production)"
    Write-Host ""
    Write-Host "Available Features:"
    Write-Host "  - rag_enabled"
    Write-Host "  - critic_supervisor_enabled"
    Write-Host "  - pii_tokenization_enabled"
    Write-Host "  - multi_language_enabled"
    Write-Host "  - auto_scaling_enabled"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\toggle-feature.ps1 -List"
    Write-Host "  .\toggle-feature.ps1 -Feature rag_enabled -Enable"
    Write-Host "  .\toggle-feature.ps1 -Feature critic_supervisor_enabled -Disable"
    Write-Host ""
    exit 0
}

if (-not $Enable -and -not $Disable) {
    Write-Error "Please specify -Enable or -Disable"
    exit 1
}

if ($Enable -and $Disable) {
    Write-Error "Cannot specify both -Enable and -Disable"
    exit 1
}

Write-Host ""
Write-Host "===== Feature Flag Toggle =====" -ForegroundColor Cyan
Write-Host "App Configuration: $AppConfigName"
Write-Host "Label:             $Label"
Write-Host "Feature:           $Feature"
Write-Host ""

# Get current state
Write-Host "Checking current state..." -ForegroundColor Cyan
$currentFeature = az appconfig feature show --name $AppConfigName --feature $Feature --label $Label -o json 2>$null | ConvertFrom-Json

if (-not $currentFeature) {
    Write-Error "Feature '$Feature' not found. Use -List to see available features."
    exit 1
}

$currentState = if ($currentFeature.enabled) { "Enabled" } else { "Disabled" }
Write-Host "Current state: $currentState"

# Toggle the feature
if ($Enable) {
    if ($currentFeature.enabled) {
        Write-Host "Feature '$Feature' is already enabled." -ForegroundColor Yellow
        exit 0
    }

    Write-Host "Enabling feature '$Feature'..." -ForegroundColor Yellow

    az appconfig feature enable `
        --name $AppConfigName `
        --feature $Feature `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "Feature '$Feature' is now ENABLED." -ForegroundColor Green
} else {
    if (-not $currentFeature.enabled) {
        Write-Host "Feature '$Feature' is already disabled." -ForegroundColor Yellow
        exit 0
    }

    Write-Host "Disabling feature '$Feature'..." -ForegroundColor Yellow

    az appconfig feature disable `
        --name $AppConfigName `
        --feature $Feature `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "Feature '$Feature' is now DISABLED." -ForegroundColor Red
}

Write-Host ""
Write-Host "Note: Agents will pick up the change within 30 seconds."
Write-Host ""
Write-Host "Monitor impact in Application Insights:"
Write-Host "  - Feature flag state: customDimensions.$Feature"
Write-Host "  - Related errors: Failures blade"
