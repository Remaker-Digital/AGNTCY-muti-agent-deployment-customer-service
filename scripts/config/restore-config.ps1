# ============================================================================
# Azure App Configuration Restore Script
# ============================================================================
# Purpose: Restore App Configuration settings from a backup file
#
# Why restore?
# - Disaster recovery: Restore after accidental deletion or corruption
# - Rollback: Revert to previous configuration after problematic change
# - Environment setup: Initialize new environment from backup
#
# Usage:
#   .\restore-config.ps1 -BackupFile "config-backup-20260127-143022.json"
#   .\restore-config.ps1 -BackupFile "backup.json" -FeatureFile "features.json"
#   .\restore-config.ps1 -BackupFile "backup.json" -DryRun
#
# Prerequisites:
# - Azure CLI installed and logged in (az login)
# - App Configuration Data Owner role on the resource
#
# Warning: This will overwrite existing configuration values!
#
# See: docs/PHASE-5-CONFIGURATION-INTERFACE.md
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,

    [Parameter(Mandatory=$false)]
    [string]$FeatureFile = "",

    [Parameter(Mandatory=$false)]
    [string]$AppConfigName = "",

    [Parameter(Mandatory=$false)]
    [string]$Label = "production",

    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false
)

# Validate backup file exists
if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file not found: $BackupFile"
    exit 1
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
Write-Host "===== Azure App Configuration Restore =====" -ForegroundColor Cyan
Write-Host "App Configuration: $AppConfigName"
Write-Host "Label:             $Label"
Write-Host "Backup File:       $BackupFile"
if (-not [string]::IsNullOrEmpty($FeatureFile)) {
    Write-Host "Feature File:      $FeatureFile"
}
Write-Host "Dry Run:           $DryRun"
Write-Host ""

# Show what will be restored
$configContent = Get-Content $BackupFile | ConvertFrom-Json
Write-Host "Configuration settings to restore: $($configContent.Count)" -ForegroundColor Yellow

foreach ($item in $configContent) {
    $key = $item.key
    $value = if ($item.value.Length -gt 50) { $item.value.Substring(0, 50) + "..." } else { $item.value }
    Write-Host "  - $key = $value"
}

# Confirm restore (unless dry run)
if (-not $DryRun) {
    Write-Host ""
    Write-Host "WARNING: This will overwrite existing configuration values!" -ForegroundColor Red
    $confirm = Read-Host "Continue? (yes/no)"

    if ($confirm -ne "yes") {
        Write-Host "Operation cancelled." -ForegroundColor Yellow
        exit 0
    }
}

if ($DryRun) {
    Write-Host ""
    Write-Host "DRY RUN: No changes made." -ForegroundColor Cyan
    Write-Host "Remove -DryRun flag to perform actual restore."
    exit 0
}

# Restore configuration settings
Write-Host ""
Write-Host "Restoring configuration settings..." -ForegroundColor Yellow
try {
    az appconfig kv import `
        --name $AppConfigName `
        --source file `
        --path $BackupFile `
        --format json `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "Configuration settings restored successfully." -ForegroundColor Green
} catch {
    Write-Error "Failed to restore configuration settings: $_"
    exit 1
}

# Restore feature flags if file provided
if (-not [string]::IsNullOrEmpty($FeatureFile) -and (Test-Path $FeatureFile)) {
    Write-Host ""
    Write-Host "Restoring feature flags..." -ForegroundColor Yellow

    $features = Get-Content $FeatureFile | ConvertFrom-Json

    foreach ($feature in $features) {
        $featureName = $feature.name
        $enabled = if ($feature.enabled) { "true" } else { "false" }

        Write-Host "  - $featureName = $enabled"

        try {
            if ($feature.enabled) {
                az appconfig feature enable `
                    --name $AppConfigName `
                    --feature $featureName `
                    --label $Label `
                    --yes 2>&1 | Out-Null
            } else {
                az appconfig feature disable `
                    --name $AppConfigName `
                    --feature $featureName `
                    --label $Label `
                    --yes 2>&1 | Out-Null
            }
        } catch {
            Write-Warning "Failed to restore feature '$featureName': $_"
        }
    }

    Write-Host "Feature flags restored." -ForegroundColor Green
}

Write-Host ""
Write-Host "===== Restore Complete =====" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Verify configuration in Azure Portal"
Write-Host "2. Monitor agent behavior for next 30 minutes"
Write-Host "3. Check Application Insights for any errors"
