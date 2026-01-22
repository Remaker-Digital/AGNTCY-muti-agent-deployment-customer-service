# GitHub CLI Setup and Project Board Creation Script
# Purpose: Configure GitHub CLI PATH and create project board for AGNTCY platform

$ErrorActionPreference = "Stop"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " GitHub CLI Setup & Project Board Creation" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Locate GitHub CLI
Write-Host "[1/6] Locating GitHub CLI..." -ForegroundColor Yellow
$ghPath = "C:\Program Files\GitHub CLI"
$ghExe = Join-Path $ghPath "gh.exe"

if (Test-Path $ghExe) {
    Write-Host "[OK] GitHub CLI found at: $ghExe" -ForegroundColor Green
} else {
    Write-Host "[ERROR] GitHub CLI not found" -ForegroundColor Red
    Write-Host "  Install via: winget install --id GitHub.cli" -ForegroundColor Yellow
    exit 1
}

# Step 2: Add to User PATH
Write-Host ""
Write-Host "[2/6] Checking PATH configuration..." -ForegroundColor Yellow

$currentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($currentUserPath -like "*$ghPath*") {
    Write-Host "[OK] GitHub CLI already in User PATH" -ForegroundColor Green
} else {
    Write-Host "Adding GitHub CLI to User PATH..." -ForegroundColor Yellow
    try {
        $newUserPath = $currentUserPath + ";" + $ghPath
        [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
        Write-Host "[OK] GitHub CLI added to User PATH" -ForegroundColor Green
        Write-Host "     (Restart terminal for persistence)" -ForegroundColor Gray
    } catch {
        Write-Host "[ERROR] Failed to add to PATH: $_" -ForegroundColor Red
    }
}

# Update PATH for current session
$env:Path += ";$ghPath"

# Step 3: Verify gh command works
Write-Host ""
Write-Host "[3/6] Verifying gh command..." -ForegroundColor Yellow

try {
    $ghVersion = & $ghExe --version 2>&1 | Select-Object -First 1
    Write-Host "[OK] $ghVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to run gh command: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Check authentication
Write-Host ""
Write-Host "[4/6] Checking GitHub authentication..." -ForegroundColor Yellow

$authStatus = & $ghExe auth status 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Already authenticated to GitHub" -ForegroundColor Green
} else {
    Write-Host "[!] Not authenticated to GitHub" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Starting authentication process..." -ForegroundColor Yellow
    Write-Host "You will be prompted to authenticate via web browser" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "Choose authentication method:" -ForegroundColor Cyan
    Write-Host "  1) Browser (recommended - opens browser for OAuth)" -ForegroundColor White
    Write-Host "  2) Token (paste Personal Access Token)" -ForegroundColor White
    $authChoice = Read-Host "Enter choice (1 or 2)"

    if ($authChoice -eq "1") {
        & $ghExe auth login --web --git-protocol https
    } elseif ($authChoice -eq "2") {
        & $ghExe auth login --with-token --git-protocol https
    } else {
        Write-Host "[ERROR] Invalid choice. Exiting." -ForegroundColor Red
        exit 1
    }

    # Verify authentication succeeded
    $authStatus = & $ghExe auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Authentication successful!" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Authentication failed" -ForegroundColor Red
        exit 1
    }
}

# Step 5: Get repository information
Write-Host ""
Write-Host "[5/6] Gathering repository information..." -ForegroundColor Yellow

$repoOwner = "Remaker-Digital"
$repoName = "AGNTCY-muti-agent-deployment-customer-service"
$repoFullName = "$repoOwner/$repoName"

Write-Host "Repository: $repoFullName" -ForegroundColor Gray

# Verify repo access
$repoCheck = & $ghExe repo view $repoFullName --json name 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Repository access verified" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Cannot access repository" -ForegroundColor Red
    Write-Host "  Ensure you have access to $repoFullName" -ForegroundColor Yellow
    exit 1
}

# Step 6: Create GitHub Project Board
Write-Host ""
Write-Host "[6/6] Creating GitHub Project Board..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Ready to create project board with these settings:" -ForegroundColor Cyan
Write-Host "  Name: AGNTCY Multi-Agent Customer Service Platform" -ForegroundColor White
Write-Host "  Owner: $repoOwner (organization-level)" -ForegroundColor White
Write-Host "  Type: Board (Kanban)" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "Create project board? (yes/no)"

if ($confirm -ne "yes" -and $confirm -ne "y") {
    Write-Host "[CANCELLED] Project creation cancelled by user" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Creating project board..." -ForegroundColor Yellow

try {
    $projectTitle = "AGNTCY Multi-Agent Customer Service Platform"

    $createResult = & $ghExe project create --owner $repoOwner --title $projectTitle --format json 2>&1

    if ($LASTEXITCODE -eq 0) {
        $projectData = $createResult | ConvertFrom-Json
        $projectNumber = $projectData.number
        $projectUrl = $projectData.url

        Write-Host "[OK] Project board created successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Project Details:" -ForegroundColor Cyan
        Write-Host "  Number: #$projectNumber" -ForegroundColor White
        Write-Host "  URL: $projectUrl" -ForegroundColor White
        Write-Host ""

        # Save project details
        $projectInfo = @{
            number = $projectNumber
            url = $projectUrl
            title = $projectTitle
            owner = $repoOwner
            created = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        }

        $projectInfo | ConvertTo-Json | Out-File "github-project-info.json" -Encoding UTF8
        Write-Host "[OK] Project info saved to github-project-info.json" -ForegroundColor Green

    } else {
        Write-Host "[ERROR] Failed to create project" -ForegroundColor Red
        Write-Host "Output: $createResult" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Note: Organization-level projects require admin permissions" -ForegroundColor Yellow
        Write-Host "      You may need to create via web interface" -ForegroundColor Yellow
    }

} catch {
    Write-Host "[ERROR] Error creating project: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
    Write-Host "  1. Ensure you have admin access to the organization" -ForegroundColor White
    Write-Host "  2. Verify authentication includes project scopes" -ForegroundColor White
    Write-Host "  3. Try creating via web interface" -ForegroundColor White
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Setup Complete!" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Restart terminal to use gh command globally" -ForegroundColor White
Write-Host "  2. Visit project board to customize" -ForegroundColor White
Write-Host "  3. Run issue creation script" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  gh project list --owner $repoOwner" -ForegroundColor Gray
Write-Host "  gh issue create --repo $repoFullName" -ForegroundColor Gray
Write-Host ""
