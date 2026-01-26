# Create Phase 3.5 User Stories (15 stories)
# Purpose: Create GitHub issues for AI Model Optimization phase
# Estimated runtime: 2-3 minutes

$ErrorActionPreference = "Continue"
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"
$repo = "Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Creating Phase 3.5 User Stories (15 stories)" -ForegroundColor Cyan
Write-Host " AI Model Optimization Phase                  " -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will take approximately 2-3 minutes..." -ForegroundColor Yellow
Write-Host ""

$totalCreated = 0
$totalErrors = 0
$startTime = Get-Date

# Helper function to create issue
function Create-Issue {
    param([string]$Title, [string]$Body, [string]$Labels, [string]$Milestone)
    $tempFile = [System.IO.Path]::GetTempFileName()
    $Body | Out-File -FilePath $tempFile -Encoding UTF8
    try {
        $result = & $ghExe issue create --repo $repo --title $Title --body-file $tempFile --label $Labels --milestone $Milestone 2>&1
        Remove-Item $tempFile -Force
        if ($LASTEXITCODE -eq 0) { return @{ Success = $true; Result = $result } }
        else { return @{ Success = $false; Result = $result } }
    } catch {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        return @{ Success = $false; Result = $_.Exception.Message }
    }
}

# Helper function to create story
function Create-Story {
    param(
        [string]$Number,
        [string]$Title,
        [string]$Actor,
        [string]$Theme,
        [string]$Scenario1,
        [string]$Scenario2,
        [string]$Scenario3,
        [string]$TechnicalScope,
        [string]$Criteria1,
        [string]$Criteria2,
        [string]$Criteria3,
        [int]$EpicNumber,
        [string]$Phase,
        [string]$Labels,
        [string]$Milestone
    )
    $body = @"
## User Story (Story $Number)
As a $Actor
I want $Theme
So that I can achieve my goals

## Example Scenarios
- $Scenario1
- $Scenario2
- $Scenario3

## Technical Scope
$TechnicalScope

## Acceptance Criteria
- [ ] $Criteria1
- [ ] $Criteria2
- [ ] $Criteria3

**Related Epic**: #$EpicNumber
**Phase**: $Phase
"@
    return Create-Issue -Title $Title -Body $body -Labels $Labels -Milestone $Milestone
}

#region Create Phase 3.5 Milestone first
Write-Host "Creating Phase 3.5 Milestone..." -ForegroundColor Yellow
$milestoneResult = & $ghExe api repos/$repo/milestones --method POST -f title="Phase 3.5 - AI Model Optimization" -f description="AI model testing and prompt optimization before full Azure deployment" -f state="open" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Phase 3.5 Milestone created" -ForegroundColor Green
} else {
    Write-Host "[INFO] Milestone may already exist, continuing..." -ForegroundColor Yellow
}
Write-Host ""
#endregion

#region Create Phase 3.5 Label
Write-Host "Creating Phase 3.5 Label..." -ForegroundColor Yellow
$labelResult = & $ghExe label create "phase: phase-3.5" --repo $repo --description "Phase 3.5: AI Model Optimization" --color "7B68EE" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Phase 3.5 Label created" -ForegroundColor Green
} else {
    Write-Host "[INFO] Label may already exist, continuing..." -ForegroundColor Yellow
}
Write-Host ""
#endregion

#region Phase 3.5 Stories (15 stories - AI Model Optimization)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Phase 3.5: AI Model Optimization" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$phase35Count = 0
$phase35Errors = 0

$phase35Stories = @(
    # Setup & Infrastructure (3 stories)
    @{
        num = "3.5.1"
        title = "Phase 3.5: Create Test Harness Framework"
        actor = "Developer"
        epic = 8
        theme = "create evaluation framework for Azure OpenAI testing"
        s1 = "Test harness connects to Azure OpenAI API"
        s2 = "Token usage tracked per request"
        s3 = "Results logged in structured format"
        tech = "evaluation/test_harness.py, evaluation/azure_openai_client.py, evaluation/config.py"
        c1 = "Azure OpenAI connection working"
        c2 = "Token usage tracked accurately"
        c3 = "Results exportable as JSON/Markdown"
        labels = "type: feature,priority: critical,component: testing,phase: phase-3.5,actor: operator"
    },
    @{
        num = "3.5.2"
        title = "Phase 3.5: Create Evaluation Datasets"
        actor = "Developer"
        epic = 8
        theme = "build comprehensive test data for AI evaluation"
        s1 = "50+ labeled intent classification samples"
        s2 = "30+ response quality conversation threads"
        s3 = "50+ adversarial inputs for Critic/Supervisor"
        tech = "evaluation/datasets/*.json (intent, response, escalation, adversarial, knowledge)"
        c1 = "150+ total evaluation samples created"
        c2 = "All samples labeled with expected outputs"
        c3 = "Datasets cover all 17 intent types"
        labels = "type: feature,priority: critical,component: testing,phase: phase-3.5,actor: operator"
    },
    @{
        num = "3.5.3"
        title = "Phase 3.5: Setup Metrics Collection & Reporting"
        actor = "Developer"
        epic = 8
        theme = "automate metrics collection and report generation"
        s1 = "Metrics collector tracks accuracy, latency, cost"
        s2 = "Reports generated in Markdown format"
        s3 = "Comparison charts for model selection"
        tech = "evaluation/metrics_collector.py, evaluation/report_generator.py"
        c1 = "All metrics tracked automatically"
        c2 = "Reports generated per iteration"
        c3 = "Cost tracking accurate to $0.01"
        labels = "type: feature,priority: high,component: observability,phase: phase-3.5,actor: operator"
    },
    # Intent Classification (2 stories)
    @{
        num = "3.5.4"
        title = "Phase 3.5: Intent Classification - Baseline"
        actor = "Developer"
        epic = 7
        theme = "establish intent classification baseline accuracy"
        s1 = "Run initial prompt against 50+ samples"
        s2 = "Measure accuracy per intent type"
        s3 = "Identify lowest-performing intents"
        tech = "evaluation/prompts/intent_classification_v1.txt"
        c1 = "Baseline accuracy measured"
        c2 = "Confusion matrix generated"
        c3 = "Problem areas identified"
        labels = "type: test,priority: critical,component: agent,phase: phase-3.5,actor: ai-assistant"
    },
    @{
        num = "3.5.5"
        title = "Phase 3.5: Intent Classification - Optimization"
        actor = "Developer"
        epic = 7
        theme = "achieve >85% intent classification accuracy"
        s1 = "Iterate prompts to improve accuracy"
        s2 = "Add few-shot examples for problem intents"
        s3 = "Validate final prompt meets threshold"
        tech = "evaluation/prompts/intent_classification_final.txt, evaluation/results/intent_accuracy_report.md"
        c1 = "Accuracy >85% achieved"
        c2 = "Max 5 iterations used"
        c3 = "Final prompt documented"
        labels = "type: enhancement,priority: critical,component: agent,phase: phase-3.5,actor: ai-assistant"
    },
    # Response Generation (2 stories)
    @{
        num = "3.5.6"
        title = "Phase 3.5: Response Generation - Baseline"
        actor = "Developer"
        epic = 7
        theme = "establish response quality baseline"
        s1 = "Generate responses for 30+ scenarios"
        s2 = "Human evaluation of quality (1-5 scale)"
        s3 = "Calculate weighted quality score"
        tech = "evaluation/prompts/response_generation_v1.txt"
        c1 = "Baseline quality score measured"
        c2 = "Human evaluation completed"
        c3 = "Quality dimensions assessed"
        labels = "type: test,priority: critical,component: agent,phase: phase-3.5,actor: ai-assistant"
    },
    @{
        num = "3.5.7"
        title = "Phase 3.5: Response Generation - Optimization"
        actor = "Developer"
        epic = 7
        theme = "achieve >80% response quality score"
        s1 = "Iterate prompts based on evaluation feedback"
        s2 = "Adjust tone, completeness, actionability"
        s3 = "Validate final prompt meets threshold"
        tech = "evaluation/prompts/response_generation_final.txt, evaluation/results/response_quality_report.md"
        c1 = "Quality score >80% achieved"
        c2 = "Inter-rater reliability >0.7"
        c3 = "Final prompt documented"
        labels = "type: enhancement,priority: critical,component: agent,phase: phase-3.5,actor: ai-assistant"
    },
    # Escalation Detection (2 stories)
    @{
        num = "3.5.8"
        title = "Phase 3.5: Escalation Detection - Baseline"
        actor = "Developer"
        epic = 7
        theme = "establish escalation detection baseline"
        s1 = "Run 20+ escalation scenarios"
        s2 = "Measure precision and recall"
        s3 = "Identify false positive patterns"
        tech = "evaluation/prompts/escalation_detection_v1.txt"
        c1 = "Baseline precision/recall measured"
        c2 = "False positive patterns identified"
        c3 = "Escalation triggers documented"
        labels = "type: test,priority: high,component: agent,phase: phase-3.5,actor: ai-assistant"
    },
    @{
        num = "3.5.9"
        title = "Phase 3.5: Escalation Detection - Optimization"
        actor = "Developer"
        epic = 7
        theme = "achieve <10% false positive, >95% true positive"
        s1 = "Tune escalation thresholds"
        s2 = "Add examples for edge cases"
        s3 = "Validate final prompt meets thresholds"
        tech = "evaluation/prompts/escalation_detection_final.txt, evaluation/results/escalation_threshold_report.md"
        c1 = "False positive rate <10%"
        c2 = "True positive rate >95%"
        c3 = "Final prompt documented"
        labels = "type: enhancement,priority: high,component: agent,phase: phase-3.5,actor: ai-assistant"
    },
    # Critic/Supervisor Validation (2 stories)
    @{
        num = "3.5.10"
        title = "Phase 3.5: Critic/Supervisor - Input Validation"
        actor = "Developer"
        epic = 7
        theme = "validate input protection against adversarial attacks"
        s1 = "Test 50+ adversarial inputs (prompt injection, jailbreak)"
        s2 = "Measure block rate for malicious inputs"
        s3 = "Measure false positive rate for normal inputs"
        tech = "evaluation/prompts/critic_input_validation.txt"
        c1 = "100% block rate for adversarial inputs"
        c2 = "False positive rate <5% for normal inputs"
        c3 = "Validation latency <200ms"
        labels = "type: test,priority: critical,component: security,phase: phase-3.5,actor: ai-assistant"
    },
    @{
        num = "3.5.11"
        title = "Phase 3.5: Critic/Supervisor - Output Validation"
        actor = "Developer"
        epic = 7
        theme = "validate output filtering for harmful content"
        s1 = "Test output filtering for profanity, PII leakage"
        s2 = "Verify harmful content blocked"
        s3 = "Ensure legitimate responses pass"
        tech = "evaluation/prompts/critic_output_validation.txt, evaluation/results/critic_validation_report.md"
        c1 = "100% block rate for harmful outputs"
        c2 = "False positive rate <5% for legitimate outputs"
        c3 = "Final prompts documented"
        labels = "type: test,priority: critical,component: security,phase: phase-3.5,actor: ai-assistant"
    },
    # RAG Testing (2 stories)
    @{
        num = "3.5.12"
        title = "Phase 3.5: RAG - Local FAISS Setup"
        actor = "Developer"
        epic = 7
        theme = "setup local vector store for retrieval testing"
        s1 = "Create embeddings for 75-document knowledge base"
        s2 = "Store in local FAISS index"
        s3 = "Implement retrieval interface"
        tech = "evaluation/rag/local_faiss_store.py, evaluation/rag/embedding_client.py"
        c1 = "75 documents embedded successfully"
        c2 = "FAISS index created and queryable"
        c3 = "Retrieval latency <100ms"
        labels = "type: feature,priority: high,component: agent,phase: phase-3.5,actor: ai-assistant"
    },
    @{
        num = "3.5.13"
        title = "Phase 3.5: RAG - Retrieval Accuracy Testing"
        actor = "Developer"
        epic = 7
        theme = "achieve >90% retrieval accuracy"
        s1 = "Test 25+ retrieval queries"
        s2 = "Measure retrieval@3 accuracy"
        s3 = "Validate semantic matching"
        tech = "evaluation/rag/retrieval_tester.py, evaluation/results/rag_accuracy_report.md"
        c1 = "Retrieval@3 accuracy >90%"
        c2 = "Semantic queries work correctly"
        c3 = "Out-of-scope queries return low confidence"
        labels = "type: test,priority: high,component: agent,phase: phase-3.5,actor: ai-assistant"
    },
    # Model Comparison & Final Report (2 stories)
    @{
        num = "3.5.14"
        title = "Phase 3.5: Model Comparison Analysis"
        actor = "Developer"
        epic = 8
        theme = "data-driven model selection per agent"
        s1 = "Compare GPT-4o vs GPT-4o-mini per task"
        s2 = "Measure quality, cost, latency trade-offs"
        s3 = "Generate decision matrix"
        tech = "evaluation/results/model_comparison_report.md"
        c1 = "All agent types compared"
        c2 = "Cost projections documented"
        c3 = "Model selection justified"
        labels = "type: documentation,priority: high,component: agent,phase: phase-3.5,actor: operator"
    },
    @{
        num = "3.5.15"
        title = "Phase 3.5: Completion Summary & Phase 4 Handoff"
        actor = "Developer"
        epic = 8
        theme = "document Phase 3.5 outcomes and prepare for Phase 4"
        s1 = "All exit criteria validated"
        s2 = "Prompt library finalized"
        s3 = "Phase 4 readiness confirmed"
        tech = "docs/PHASE-3.5-COMPLETION-SUMMARY.md, updated CLAUDE.md"
        c1 = "All exit criteria met or documented gaps"
        c2 = "Prompt library ready for Phase 4"
        c3 = "Cost projection <$60/month"
        labels = "type: documentation,priority: critical,component: documentation,phase: phase-3.5,actor: operator"
    }
)

foreach ($story in $phase35Stories) {
    $result = Create-Story -Number $story.num -Title $story.title -Actor $story.actor -Theme $story.theme -Scenario1 $story.s1 -Scenario2 $story.s2 -Scenario3 $story.s3 -TechnicalScope $story.tech -Criteria1 $story.c1 -Criteria2 $story.c2 -Criteria3 $story.c3 -EpicNumber $story.epic -Phase "3.5 - AI Model Optimization" -Labels $story.labels -Milestone "Phase 3.5 - AI Model Optimization"
    if ($result.Success) {
        Write-Host "[SUCCESS] Story $($story.num): $($story.title)" -ForegroundColor Green
        $phase35Count++
        $totalCreated++
    } else {
        Write-Host "[ERROR] Story $($story.num): $($result.Result)" -ForegroundColor Red
        $phase35Errors++
        $totalErrors++
    }
    Start-Sleep -Milliseconds 500
}

Write-Host ""
Write-Host "Phase 3.5 Complete: $phase35Count created, $phase35Errors errors" -ForegroundColor Cyan
Write-Host ""

#endregion

#region Final Summary
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " FINAL SUMMARY" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total Issues Created: $totalCreated" -ForegroundColor Green
Write-Host "Total Errors: $totalErrors" -ForegroundColor $(if ($totalErrors -eq 0) { "Green" } else { "Red" })
Write-Host "Duration: $($duration.Minutes) min $($duration.Seconds) sec" -ForegroundColor Cyan
Write-Host ""
Write-Host "Phase 3.5 Stories: $phase35Count / 15" -ForegroundColor Cyan
Write-Host ""

if ($totalErrors -eq 0) {
    Write-Host "All Phase 3.5 issues created successfully!" -ForegroundColor Green
} else {
    Write-Host "Some issues failed. Review errors above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "View issues at: https://github.com/$repo/issues" -ForegroundColor Cyan
Write-Host ""
#endregion
