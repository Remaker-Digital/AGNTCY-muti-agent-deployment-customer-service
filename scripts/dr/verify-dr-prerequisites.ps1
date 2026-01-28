# ============================================================================
# DR Drill Prerequisites Verification
# ============================================================================
# Purpose: Verify all prerequisites are met before running DR drill
#
# Prerequisites:
# 1. Azure CLI installed and logged in
# 2. Terraform installed (>=1.5.0)
# 3. Access to agntcy-prod-rg resource group
# 4. PowerShell 7+ (recommended)
#
# Usage:
#   .\verify-dr-prerequisites.ps1
#
# See: scripts/dr/run-dr-drill.ps1 for full DR drill
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "agntcy-prod-rg"
)

$ErrorActionPreference = "Continue"
$allPassed = $true

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "DR DRILL PREREQUISITES VERIFICATION"
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# CHECK 1: Azure CLI
# ============================================================================
Write-Host "[1/5] Checking Azure CLI..." -NoNewline

try {
    $azVersion = az version --output json 2>$null | ConvertFrom-Json
    $cliVersion = $azVersion.'azure-cli'
    Write-Host " PASS" -ForegroundColor Green
    Write-Host "      Azure CLI version: $cliVersion"
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    Write-Host "      Azure CLI not installed or not in PATH"
    Write-Host "      Install from: https://aka.ms/installazurecli"
    $allPassed = $false
}

# ============================================================================
# CHECK 2: Azure Login
# ============================================================================
Write-Host "[2/5] Checking Azure login..." -NoNewline

try {
    $account = az account show --output json 2>$null | ConvertFrom-Json
    $subscriptionName = $account.name
    $subscriptionId = $account.id
    Write-Host " PASS" -ForegroundColor Green
    Write-Host "      Subscription: $subscriptionName"
    Write-Host "      ID: $subscriptionId"
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    Write-Host "      Not logged in to Azure CLI"
    Write-Host "      Run: az login"
    $allPassed = $false
}

# ============================================================================
# CHECK 3: Resource Group Access
# ============================================================================
Write-Host "[3/5] Checking resource group access..." -NoNewline

try {
    $rg = az group show --name $ResourceGroup --output json 2>$null | ConvertFrom-Json
    Write-Host " PASS" -ForegroundColor Green
    Write-Host "      Resource Group: $($rg.name)"
    Write-Host "      Location: $($rg.location)"
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    Write-Host "      Cannot access resource group: $ResourceGroup"
    Write-Host "      Verify permissions and resource group exists"
    $allPassed = $false
}

# ============================================================================
# CHECK 4: Terraform
# ============================================================================
Write-Host "[4/5] Checking Terraform..." -NoNewline

try {
    $tfVersionJson = terraform version -json 2>$null
    $tfVersion = ($tfVersionJson | ConvertFrom-Json).terraform_version
    $minVersion = [version]"1.5.0"
    $currentVersion = [version]$tfVersion

    if ($currentVersion -ge $minVersion) {
        Write-Host " PASS" -ForegroundColor Green
        Write-Host "      Terraform version: $tfVersion"
    } else {
        Write-Host " WARN" -ForegroundColor Yellow
        Write-Host "      Terraform version $tfVersion is below recommended $minVersion"
    }
} catch {
    Write-Host " FAIL" -ForegroundColor Red
    Write-Host "      Terraform not installed or not in PATH"
    Write-Host "      Install from: https://www.terraform.io/downloads"
    $allPassed = $false
}

# ============================================================================
# CHECK 5: Terraform Directory
# ============================================================================
Write-Host "[5/5] Checking Terraform configuration..." -NoNewline

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$tfDir = Join-Path $projectRoot "terraform\phase4_prod"

if (Test-Path (Join-Path $tfDir "main.tf")) {
    Write-Host " PASS" -ForegroundColor Green
    Write-Host "      Terraform directory: $tfDir"

    # Check for state file
    $stateFile = Join-Path $tfDir "terraform.tfstate"
    if (Test-Path $stateFile) {
        $stateSize = (Get-Item $stateFile).Length / 1KB
        Write-Host "      State file: Present ($([math]::Round($stateSize, 1)) KB)"
    } else {
        Write-Host "      State file: Not found (may need init)" -ForegroundColor Yellow
    }
} else {
    Write-Host " FAIL" -ForegroundColor Red
    Write-Host "      Terraform configuration not found at: $tfDir"
    $allPassed = $false
}

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

if ($allPassed) {
    Write-Host "RESULT: ALL PREREQUISITES MET" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run the DR drill:"
    Write-Host "  .\run-dr-drill.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or run a dry run first:"
    Write-Host "  .\run-dr-drill.ps1 -DryRun" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "RESULT: PREREQUISITES NOT MET" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please resolve the issues above before running DR drill."
    exit 1
}
