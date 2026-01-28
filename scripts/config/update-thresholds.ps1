# ============================================================================
# Azure App Configuration Threshold Update Script
# ============================================================================
# Purpose: Update agent confidence and escalation thresholds
#
# Why tune thresholds?
# - Escalation Rate: Lower confidence threshold = fewer escalations
# - Response Quality: Higher threshold = more human review
# - Sentiment Analysis: Adjust when to escalate based on customer mood
#
# Usage:
#   .\update-thresholds.ps1 -IntentConfidence 0.5
#   .\update-thresholds.ps1 -EscalationSentiment -0.7 -EscalationConfidence 0.5
#   .\update-thresholds.ps1 -CriticBlockThreshold 0.7 -CriticMaxRetries 3
#
# Tuning History:
# - 2026-01-25: Intent threshold 0.7 → 0.5 (reduced escalation rate 70% → 30%)
# - 2026-01-25: Escalation sentiment -0.5 → -0.7 (escalate only very negative)
#
# See: evaluation/results/intent-classification-results.md
# See: docs/PHASE-5-CONFIGURATION-INTERFACE.md
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [double]$IntentConfidence = 0,

    [Parameter(Mandatory=$false)]
    [int]$IntentMaxTokens = 0,

    [Parameter(Mandatory=$false)]
    [double]$EscalationSentiment = 0,

    [Parameter(Mandatory=$false)]
    [double]$EscalationConfidence = 0,

    [Parameter(Mandatory=$false)]
    [double]$ResponseTemperature = 0,

    [Parameter(Mandatory=$false)]
    [int]$ResponseMaxTokens = 0,

    [Parameter(Mandatory=$false)]
    [double]$CriticBlockThreshold = 0,

    [Parameter(Mandatory=$false)]
    [int]$CriticMaxRetries = 0,

    [Parameter(Mandatory=$false)]
    [int]$RAGTopK = 0,

    [Parameter(Mandatory=$false)]
    [double]$RAGSimilarityThreshold = 0,

    [Parameter(Mandatory=$false)]
    [string]$AppConfigName = "",

    [Parameter(Mandatory=$false)]
    [string]$Label = "production"
)

# Check if any parameter was provided
$anyParamProvided = (
    $IntentConfidence -gt 0 -or $IntentMaxTokens -gt 0 -or
    $EscalationSentiment -ne 0 -or $EscalationConfidence -gt 0 -or
    $ResponseTemperature -gt 0 -or $ResponseMaxTokens -gt 0 -or
    $CriticBlockThreshold -gt 0 -or $CriticMaxRetries -gt 0 -or
    $RAGTopK -gt 0 -or $RAGSimilarityThreshold -gt 0
)

if (-not $anyParamProvided) {
    Write-Host ""
    Write-Host "===== Agent Threshold Update Script =====" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\update-thresholds.ps1 [options]"
    Write-Host ""
    Write-Host "Intent Classification:"
    Write-Host "  -IntentConfidence <double>    Confidence threshold (0.0-1.0)"
    Write-Host "  -IntentMaxTokens <int>        Max tokens for intent response (50-500)"
    Write-Host ""
    Write-Host "Escalation:"
    Write-Host "  -EscalationSentiment <double>    Sentiment threshold (-1.0 to 0.0)"
    Write-Host "  -EscalationConfidence <double>   Confidence threshold (0.0-1.0)"
    Write-Host ""
    Write-Host "Response Generation:"
    Write-Host "  -ResponseTemperature <double>    LLM temperature (0.0-1.0)"
    Write-Host "  -ResponseMaxTokens <int>         Max tokens for response (100-2000)"
    Write-Host ""
    Write-Host "Critic/Supervisor:"
    Write-Host "  -CriticBlockThreshold <double>   Block confidence (0.5-0.95)"
    Write-Host "  -CriticMaxRetries <int>          Max regeneration attempts (1-5)"
    Write-Host ""
    Write-Host "RAG:"
    Write-Host "  -RAGTopK <int>                   Documents to retrieve (1-20)"
    Write-Host "  -RAGSimilarityThreshold <double> Minimum similarity (0.5-0.95)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\update-thresholds.ps1 -IntentConfidence 0.5"
    Write-Host "  .\update-thresholds.ps1 -EscalationSentiment -0.7"
    Write-Host "  .\update-thresholds.ps1 -ResponseTemperature 0.3 -ResponseMaxTokens 500"
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
Write-Host "===== Updating Agent Thresholds =====" -ForegroundColor Cyan
Write-Host "App Configuration: $AppConfigName"
Write-Host "Label:             $Label"
Write-Host ""

$updatedCount = 0

# Helper function to update a key
function Update-ConfigKey {
    param($Key, $Value, $ValidMin, $ValidMax, $Unit)

    if ($Value -lt $ValidMin -or $Value -gt $ValidMax) {
        Write-Warning "$Key should be between $ValidMin-$ValidMax. Got: $Value"
    }

    Write-Host "Setting $Key = $Value" -ForegroundColor Yellow

    az appconfig kv set `
        --name $AppConfigName `
        --key $Key `
        --value "$Value" `
        --label $Label `
        --yes 2>&1 | Out-Null

    Write-Host "  Updated." -ForegroundColor Green
    return 1
}

# Intent Classification
if ($IntentConfidence -gt 0) {
    $updatedCount += Update-ConfigKey "intent:confidence_threshold" $IntentConfidence 0.0 1.0 ""
}

if ($IntentMaxTokens -gt 0) {
    $updatedCount += Update-ConfigKey "intent:max_tokens" $IntentMaxTokens 50 500 "tokens"
}

# Escalation
if ($EscalationSentiment -ne 0) {
    $updatedCount += Update-ConfigKey "escalation:sentiment_threshold" $EscalationSentiment -1.0 0.0 ""
}

if ($EscalationConfidence -gt 0) {
    $updatedCount += Update-ConfigKey "escalation:confidence_threshold" $EscalationConfidence 0.0 1.0 ""
}

# Response Generation
if ($ResponseTemperature -gt 0) {
    $updatedCount += Update-ConfigKey "response:temperature" $ResponseTemperature 0.0 1.0 ""
}

if ($ResponseMaxTokens -gt 0) {
    $updatedCount += Update-ConfigKey "response:max_tokens" $ResponseMaxTokens 100 2000 "tokens"
}

# Critic/Supervisor
if ($CriticBlockThreshold -gt 0) {
    $updatedCount += Update-ConfigKey "critic:block_threshold" $CriticBlockThreshold 0.5 0.95 ""
}

if ($CriticMaxRetries -gt 0) {
    $updatedCount += Update-ConfigKey "critic:max_retries" $CriticMaxRetries 1 5 "attempts"
}

# RAG
if ($RAGTopK -gt 0) {
    $updatedCount += Update-ConfigKey "rag:top_k" $RAGTopK 1 20 "documents"
}

if ($RAGSimilarityThreshold -gt 0) {
    $updatedCount += Update-ConfigKey "rag:similarity_threshold" $RAGSimilarityThreshold 0.5 0.95 ""
}

Write-Host ""
Write-Host "===== Update Complete =====" -ForegroundColor Green
Write-Host "Settings updated: $updatedCount"
Write-Host ""
Write-Host "Note: Agents will pick up new values within 30 seconds."
Write-Host ""
Write-Host "Monitoring tips:"
Write-Host "  - Check escalation rate: Application Insights > Custom Metrics > escalation_rate"
Write-Host "  - Check confidence scores: Application Insights > Traces > 'confidence_score'"
Write-Host "  - Monitor for errors: Application Insights > Failures"
