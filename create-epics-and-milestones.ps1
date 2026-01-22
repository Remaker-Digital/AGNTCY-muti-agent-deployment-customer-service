# Create Milestones and Epic Issues
# Purpose: Set up project structure before creating detailed user stories

$ErrorActionPreference = "Continue"  # Continue on errors
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"
$repo = "Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Creating Milestones and Epics" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create remaining milestones
Write-Host "[1/2] Creating milestones..." -ForegroundColor Yellow

$milestones = @(
    @{ title = "Phase 2 - Business Logic"; desc = "Implement agent business logic. Budget `$0/month"; due = "2026-04-30T23:59:59Z" },
    @{ title = "Phase 3 - Testing"; desc = "Functional testing and validation. Budget `$0/month"; due = "2026-06-30T23:59:59Z" },
    @{ title = "Phase 4 - Production Deployment"; desc = "Azure deployment. Budget `$200/month"; due = "2026-08-31T23:59:59Z" },
    @{ title = "Phase 5 - Go-Live"; desc = "Production testing and cutover. Budget `$200/month"; due = "2026-09-30T23:59:59Z" }
)

foreach ($ms in $milestones) {
    Write-Host "  Creating: $($ms.title)"
    & $ghExe api "repos/$repo/milestones" -f title=$ms.title -f description=$ms.desc -f due_on=$ms.due --method POST 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] May already exist" -ForegroundColor Gray
    }
}

Write-Host ""

# Step 2: Create 7 Epic issues
Write-Host "[2/2] Creating Epic issues..." -ForegroundColor Yellow
Write-Host ""

# Use simpler issue creation - create via web would be easier for complex bodies
# So let's output the GitHub CLI commands for manual execution

$epics = @(
    @{
        title = "EPIC: Customer Stories (40 stories)"
        labels = "type: epic,actor: customer,priority: critical"
    },
    @{
        title = "EPIC: Prospect Stories (25 stories)"
        labels = "type: epic,actor: prospect,priority: high"
    },
    @{
        title = "EPIC: Support Agent Stories (15 stories)"
        labels = "type: epic,actor: support,priority: high"
    },
    @{
        title = "EPIC: Service Agent Stories (15 stories)"
        labels = "type: epic,actor: service,priority: medium"
    },
    @{
        title = "EPIC: Sales Agent Stories (15 stories)"
        labels = "type: epic,actor: sales,priority: medium"
    },
    @{
        title = "EPIC: AI Customer Assistant Stories (5 stories)"
        labels = "type: epic,actor: ai-assistant,priority: medium"
    },
    @{
        title = "EPIC: Operator Stories (15 stories)"
        labels = "type: epic,actor: operator,priority: critical"
    }
)

foreach ($epic in $epics) {
    Write-Host "Creating: $($epic.title)" -ForegroundColor Cyan

    $body = "This epic tracks all stories for this actor persona. See user-stories-phased.md for details."

    $result = & $ghExe issue create `
        --repo $repo `
        --title $epic.title `
        --body $body `
        --label $epic.labels 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $result" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] $result" -ForegroundColor Red
    }

    Start-Sleep -Milliseconds 500
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Complete!" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "View issues: https://github.com/$repo/issues" -ForegroundColor Yellow
Write-Host "View milestones: https://github.com/$repo/milestones" -ForegroundColor Yellow
Write-Host ""
