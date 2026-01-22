# Configure GitHub Project Board
# Purpose: Set up fields, columns, and settings for AGNTCY project board

$ErrorActionPreference = "Stop"
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Configuring GitHub Project Board" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$projectNumber = 1
$owner = "Remaker-Digital"

# Step 1: Update project title and description
Write-Host "[1/3] Updating project title and description..." -ForegroundColor Yellow

$projectTitle = "AGNTCY Multi-Agent Customer Service Platform"
$projectDescription = "Multi-agent AI customer service platform using AGNTCY SDK and Azure. Educational project demonstrating cost-effective deployment strategies."

# GitHub CLI doesn't have direct project edit commands for new projects
# We'll need to use GraphQL API
Write-Host "[INFO] Project title update requires GraphQL API" -ForegroundColor Gray
Write-Host "      Current title: @Quartermark's untitled project" -ForegroundColor Gray
Write-Host "      Please update manually via web UI if needed" -ForegroundColor Gray
Write-Host "      URL: https://github.com/orgs/$owner/projects/$projectNumber/settings" -ForegroundColor Gray

# Step 2: Document current project structure
Write-Host ""
Write-Host "[2/3] Documenting project structure..." -ForegroundColor Yellow

$projectInfo = & $ghExe project view $projectNumber --owner $owner --format json | ConvertFrom-Json

Write-Host "[OK] Project Number: $projectNumber" -ForegroundColor Green
Write-Host "[OK] Project URL: $($projectInfo.url)" -ForegroundColor Green
Write-Host "[OK] Current Fields: $($projectInfo.fields.totalCount)" -ForegroundColor Green
Write-Host "[OK] Current Items: $($projectInfo.items.totalCount)" -ForegroundColor Green

# Save project info
$projectData = @{
    number = $projectNumber
    url = $projectInfo.url
    id = $projectInfo.id
    owner = $owner
    title = $projectInfo.title
    configured = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
}

$projectData | ConvertTo-Json | Out-File "github-project-info.json" -Encoding UTF8
Write-Host "[OK] Project info saved to github-project-info.json" -ForegroundColor Green

# Step 3: Instructions for manual configuration
Write-Host ""
Write-Host "[3/3] Manual configuration steps needed..." -ForegroundColor Yellow
Write-Host ""
Write-Host "GitHub CLI has limited support for project field configuration." -ForegroundColor Cyan
Write-Host "Please complete these steps via the web interface:" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. UPDATE PROJECT TITLE:" -ForegroundColor Yellow
Write-Host "   URL: https://github.com/orgs/$owner/projects/$projectNumber/settings" -ForegroundColor White
Write-Host "   - Change title to: AGNTCY Multi-Agent Customer Service Platform" -ForegroundColor White
Write-Host "   - Add description: $projectDescription" -ForegroundColor White
Write-Host ""

Write-Host "2. CONFIGURE STATUS FIELD (Columns):" -ForegroundColor Yellow
Write-Host "   URL: https://github.com/orgs/$owner/projects/$projectNumber" -ForegroundColor White
Write-Host "   - Click on 'Status' field dropdown" -ForegroundColor White
Write-Host "   - Add/rename statuses to match:" -ForegroundColor White
Write-Host "     * Backlog (for unrefined ideas)" -ForegroundColor Gray
Write-Host "     * To Do (ready for development)" -ForegroundColor Gray
Write-Host "     * In Progress (active work)" -ForegroundColor Gray
Write-Host "     * Review (code review phase)" -ForegroundColor Gray
Write-Host "     * Done (completed)" -ForegroundColor Gray
Write-Host ""

Write-Host "3. ADD CUSTOM FIELDS:" -ForegroundColor Yellow
Write-Host "   - Click '+' next to field names" -ForegroundColor White
Write-Host "   - Add these fields:" -ForegroundColor White
Write-Host ""
Write-Host "   a) Priority (Single select):" -ForegroundColor Cyan
Write-Host "      Options: Critical, High, Medium, Low" -ForegroundColor Gray
Write-Host ""
Write-Host "   b) Component (Single select):" -ForegroundColor Cyan
Write-Host "      Options: API, Frontend, Backend, Database, Auth, Shared, Docs" -ForegroundColor Gray
Write-Host ""
Write-Host "   c) Phase (Single select):" -ForegroundColor Cyan
Write-Host "      Options: Phase 1, Phase 2, Phase 3, Phase 4, Phase 5" -ForegroundColor Gray
Write-Host ""
Write-Host "   d) Story Points (Number):" -ForegroundColor Cyan
Write-Host "      For estimation (1, 2, 3, 5, 8, 13)" -ForegroundColor Gray
Write-Host ""

Write-Host "4. LINK REPOSITORY:" -ForegroundColor Yellow
Write-Host "   - Go to project settings" -ForegroundColor White
Write-Host "   - Under 'Manage access', add repository:" -ForegroundColor White
Write-Host "     Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service" -ForegroundColor Gray
Write-Host ""

Write-Host "5. ENABLE WORKFLOWS (Automation):" -ForegroundColor Yellow
Write-Host "   - Go to Workflows in settings" -ForegroundColor White
Write-Host "   - Enable these workflows:" -ForegroundColor White
Write-Host "     * Item added to project -> Set status to 'To Do'" -ForegroundColor Gray
Write-Host "     * Pull request merged -> Set status to 'Done'" -ForegroundColor Gray
Write-Host "     * Item closed -> Set status to 'Done'" -ForegroundColor Gray
Write-Host ""

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Configuration Guide Complete!" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "After completing the manual steps above, run:" -ForegroundColor Yellow
Write-Host "  .\create-issues.ps1" -ForegroundColor White
Write-Host ""
Write-Host "This will populate the board with user stories from PROJECT-README.txt" -ForegroundColor Gray
Write-Host ""
