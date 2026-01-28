# ============================================================================
# Azure App Configuration Backup Script
# ============================================================================
# Purpose: Export all App Configuration settings to a JSON backup file
#
# Why backup?
# - Disaster recovery: Restore configuration after accidental deletion
# - Environment promotion: Copy settings from staging to production
# - Audit trail: Track configuration changes over time
#
# Usage:
#   .\backup-config.ps1
#   .\backup-config.ps1 -AppConfigName "appconfig-agntcy-cs-prod-abc123"
#   .\backup-config.ps1 -Label "production"
#
# Prerequisites:
# - Azure CLI installed and logged in (az login)
# - App Configuration Data Reader role on the resource
#
# See: docs/PHASE-5-CONFIGURATION-INTERFACE.md
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$AppConfigName = "",

    [Parameter(Mandatory=$false)]
    [string]$Label = "production",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "config-backups"
)

# Generate timestamp for backup filename
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $PSScriptRoot "..\..\$OutputDir"
$backupFile = Join-Path $backupDir "config-backup-$timestamp.json"
$featureFile = Join-Path $backupDir "features-backup-$timestamp.json"

# Create backup directory if it doesn't exist
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    Write-Host "Created backup directory: $backupDir" -ForegroundColor Green
}

# Auto-discover App Configuration name if not provided
if ([string]::IsNullOrEmpty($AppConfigName)) {
    Write-Host "Auto-discovering App Configuration name..." -ForegroundColor Cyan

    $appConfigs = az appconfig list --resource-group agntcy-prod-rg --query "[].name" -o tsv 2>$null

    if ([string]::IsNullOrEmpty($appConfigs)) {
        Write-Error "No App Configuration found in resource group 'agntcy-prod-rg'. Please specify -AppConfigName."
        exit 1
    }

    # Use the first (and likely only) App Configuration
    $AppConfigName = ($appConfigs -split "`n")[0].Trim()
    Write-Host "Found App Configuration: $AppConfigName" -ForegroundColor Green
}

Write-Host ""
Write-Host "===== Azure App Configuration Backup =====" -ForegroundColor Cyan
Write-Host "App Configuration: $AppConfigName"
Write-Host "Label:             $Label"
Write-Host "Backup File:       $backupFile"
Write-Host "Features File:     $featureFile"
Write-Host ""

# Export configuration settings
Write-Host "Exporting configuration settings..." -ForegroundColor Yellow
try {
    az appconfig kv export `
        --name $AppConfigName `
        --destination file `
        --path $backupFile `
        --format json `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "Configuration settings exported successfully." -ForegroundColor Green
} catch {
    Write-Error "Failed to export configuration settings: $_"
    exit 1
}

# Export feature flags
Write-Host "Exporting feature flags..." -ForegroundColor Yellow
try {
    az appconfig feature list `
        --name $AppConfigName `
        --label $Label `
        -o json > $featureFile 2>&1

    Write-Host "Feature flags exported successfully." -ForegroundColor Green
} catch {
    Write-Warning "Failed to export feature flags (may not exist): $_"
}

# Show summary
$configCount = (Get-Content $backupFile | ConvertFrom-Json).Count
$featureCount = 0
if (Test-Path $featureFile) {
    $featureContent = Get-Content $featureFile -Raw
    if (-not [string]::IsNullOrWhiteSpace($featureContent)) {
        $featureCount = ($featureContent | ConvertFrom-Json).Count
    }
}

Write-Host ""
Write-Host "===== Backup Complete =====" -ForegroundColor Green
Write-Host "Configuration settings: $configCount"
Write-Host "Feature flags:          $featureCount"
Write-Host ""
Write-Host "Backup files:"
Write-Host "  - $backupFile"
Write-Host "  - $featureFile"
Write-Host ""
Write-Host "To restore, run:"
Write-Host "  .\restore-config.ps1 -BackupFile `"$backupFile`" -FeatureFile `"$featureFile`"" -ForegroundColor Cyan
