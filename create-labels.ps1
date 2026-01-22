# Create GitHub Labels for AGNTCY Project
# Purpose: Set up all required labels before creating issues

$ErrorActionPreference = "Stop"
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Creating GitHub Labels" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$repoFullName = "Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service"

# Define all labels
$labels = @(
    # Type Labels
    @{ name = "type: epic"; color = "5319e7"; description = "Top-level actor epic" },
    @{ name = "type: feature"; color = "0e8a16"; description = "New functionality" },
    @{ name = "type: bug"; color = "d73a4a"; description = "Bug fix" },
    @{ name = "type: enhancement"; color = "0075ca"; description = "Enhancement to existing feature" },
    @{ name = "type: test"; color = "5319e7"; description = "Testing story" },
    @{ name = "type: documentation"; color = "0075ca"; description = "Documentation only" },

    # Priority Labels
    @{ name = "priority: critical"; color = "b60205"; description = "Must-have, blocking" },
    @{ name = "priority: high"; color = "d93f0b"; description = "Important for phase goals" },
    @{ name = "priority: medium"; color = "fbca04"; description = "Nice-to-have" },
    @{ name = "priority: low"; color = "0e8a16"; description = "Future enhancement" },

    # Component Labels
    @{ name = "component: infrastructure"; color = "5EBEFF"; description = "Docker, networking, deployment" },
    @{ name = "component: agent"; color = "D4C5F9"; description = "AI agent implementation" },
    @{ name = "component: api"; color = "1D76DB"; description = "API integration (Shopify, Zendesk, Mailchimp)" },
    @{ name = "component: observability"; color = "BFD4F2"; description = "Monitoring, logging, tracing" },
    @{ name = "component: testing"; color = "F9D0C4"; description = "Test infrastructure" },
    @{ name = "component: ci-cd"; color = "C5DEF5"; description = "Automation pipelines" },
    @{ name = "component: security"; color = "B60205"; description = "Security features" },
    @{ name = "component: shared"; color = "BFDADC"; description = "Shared utilities" },

    # Phase Labels
    @{ name = "phase: phase-1"; color = "1D76DB"; description = "Phase 1 - Infrastructure & Containers" },
    @{ name = "phase: phase-2"; color = "0e8a16"; description = "Phase 2 - Business Logic" },
    @{ name = "phase: phase-3"; color = "fbca04"; description = "Phase 3 - Testing & Validation" },
    @{ name = "phase: phase-4"; color = "d93f0b"; description = "Phase 4 - Production Deployment" },
    @{ name = "phase: phase-5"; color = "5319e7"; description = "Phase 5 - Go-Live" },

    # Actor Labels
    @{ name = "actor: customer"; color = "0e8a16"; description = "Customer persona stories" },
    @{ name = "actor: prospect"; color = "0075ca"; description = "Prospect persona stories" },
    @{ name = "actor: support"; color = "d93f0b"; description = "Support agent stories" },
    @{ name = "actor: service"; color = "fbca04"; description = "Service agent stories" },
    @{ name = "actor: sales"; color = "5319e7"; description = "Sales agent stories" },
    @{ name = "actor: ai-assistant"; color = "D4C5F9"; description = "AI proactive engagement stories" },
    @{ name = "actor: operator"; color = "1D76DB"; description = "DevOps/admin stories" }
)

Write-Host "Creating $($labels.Count) labels..." -ForegroundColor Yellow
Write-Host ""

$created = 0
$exists = 0
$errors = 0

foreach ($label in $labels) {
    Write-Host "Creating: $($label.name)" -ForegroundColor Cyan

    try {
        $result = & $ghExe label create $label.name `
            --description $label.description `
            --color $label.color `
            --repo $repoFullName 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Created" -ForegroundColor Green
            $created++
        } else {
            if ($result -match "already exists") {
                Write-Host "[INFO] Already exists" -ForegroundColor Gray
                $exists++
            } else {
                Write-Host "[ERROR] Failed: $result" -ForegroundColor Red
                $errors++
            }
        }
    } catch {
        Write-Host "[ERROR] Exception: $_" -ForegroundColor Red
        $errors++
    }

    Start-Sleep -Milliseconds 200
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Label Creation Complete!" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  Created: $created labels" -ForegroundColor Green
Write-Host "  Already Exist: $exists labels" -ForegroundColor Gray
Write-Host "  Errors: $errors labels" -ForegroundColor $(if ($errors -eq 0) { "Green" } else { "Red" })
Write-Host ""
Write-Host "Next Step:" -ForegroundColor Yellow
Write-Host "  Run: .\generate-all-user-stories.ps1" -ForegroundColor White
Write-Host ""
