<#
.SYNOPSIS
    Checks the codebase for optimization opportunities.

.DESCRIPTION
    This script analyzes the codebase and reports:
    - Files exceeding recommended line counts
    - CLAUDE.md archive status
    - Duplicate requirements across agents
    - Potential code duplication

.EXAMPLE
    .\scripts\check-optimization.ps1

.NOTES
    Run weekly or before optimization sessions.
    See docs/OPTIMIZATION-WORKFLOW.md for detailed procedures.
#>

param(
    [switch]$Verbose,
    [int]$ClaudeMdThreshold = 900,
    [int]$AgentFileThreshold = 500,
    [int]$GeneralFileThreshold = 300
)

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  OPTIMIZATION STATUS CHECK" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$issues = @()
$warnings = @()

# ============================================================================
# Check 1: CLAUDE.md Line Count
# ============================================================================
Write-Host "[1/5] Checking CLAUDE.md size..." -ForegroundColor Yellow

$claudeMdPath = Join-Path $projectRoot "CLAUDE.md"
if (Test-Path $claudeMdPath) {
    $claudeMdLines = (Get-Content $claudeMdPath | Measure-Object -Line).Lines

    if ($claudeMdLines -gt $ClaudeMdThreshold) {
        $issues += "CLAUDE.md has $claudeMdLines lines (threshold: $ClaudeMdThreshold)"
        Write-Host "  [!] CLAUDE.md: $claudeMdLines lines - NEEDS ARCHIVING" -ForegroundColor Red
    } else {
        $remaining = $ClaudeMdThreshold - $claudeMdLines
        Write-Host "  [OK] CLAUDE.md: $claudeMdLines lines ($remaining lines until archive needed)" -ForegroundColor Green
    }
} else {
    Write-Host "  [?] CLAUDE.md not found" -ForegroundColor Gray
}

# ============================================================================
# Check 2: Agent File Sizes
# ============================================================================
Write-Host "`n[2/5] Checking agent file sizes..." -ForegroundColor Yellow

$agentFiles = Get-ChildItem -Path (Join-Path $projectRoot "agents") -Recurse -Filter "agent.py"
foreach ($file in $agentFiles) {
    $lineCount = (Get-Content $file.FullName | Measure-Object -Line).Lines
    $relativePath = $file.FullName.Replace($projectRoot, "").TrimStart("\", "/")

    if ($lineCount -gt $AgentFileThreshold) {
        $issues += "$relativePath has $lineCount lines (threshold: $AgentFileThreshold)"
        Write-Host "  [!] $relativePath : $lineCount lines - CONSIDER SPLITTING" -ForegroundColor Red
    } else {
        if ($Verbose) {
            Write-Host "  [OK] $relativePath : $lineCount lines" -ForegroundColor Green
        }
    }
}

$totalAgentLines = ($agentFiles | ForEach-Object { (Get-Content $_.FullName | Measure-Object -Line).Lines } | Measure-Object -Sum).Sum
Write-Host "  Total agent code: $totalAgentLines lines" -ForegroundColor Cyan

# ============================================================================
# Check 3: Large Python Files (non-agent)
# ============================================================================
Write-Host "`n[3/5] Checking for large Python files..." -ForegroundColor Yellow

$pythonFiles = Get-ChildItem -Path $projectRoot -Recurse -Include "*.py" | Where-Object {
    $_.FullName -notmatch "\\\.venv\\" -and
    $_.FullName -notmatch "\\venv\\" -and
    $_.FullName -notmatch "\\__pycache__\\" -and
    $_.FullName -notmatch "\\\.git\\" -and
    $_.FullName -notmatch "\\node_modules\\" -and
    $_.Name -ne "agent.py"
}

$largeFiles = @()
foreach ($file in $pythonFiles) {
    $lineCount = (Get-Content $file.FullName | Measure-Object -Line).Lines
    if ($lineCount -gt $GeneralFileThreshold) {
        $relativePath = $file.FullName.Replace($projectRoot, "").TrimStart("\", "/")
        $largeFiles += [PSCustomObject]@{
            Path = $relativePath
            Lines = $lineCount
        }
    }
}

if ($largeFiles.Count -gt 0) {
    Write-Host "  Large files found:" -ForegroundColor Yellow
    $largeFiles | Sort-Object -Property Lines -Descending | ForEach-Object {
        if ($_.Lines -gt 500) {
            Write-Host "    [!] $($_.Path): $($_.Lines) lines" -ForegroundColor Red
            $warnings += "$($_.Path) has $($_.Lines) lines"
        } else {
            Write-Host "    [~] $($_.Path): $($_.Lines) lines" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [OK] No oversized Python files found" -ForegroundColor Green
}

# ============================================================================
# Check 4: Requirements Consistency
# ============================================================================
Write-Host "`n[4/5] Checking requirements consistency..." -ForegroundColor Yellow

$sharedReqPath = Join-Path $projectRoot "requirements-agents.txt"
$sharedPackages = @()

if (Test-Path $sharedReqPath) {
    $sharedPackages = Get-Content $sharedReqPath | Where-Object {
        $_ -match "^[a-zA-Z]" -and $_ -notmatch "^#"
    } | ForEach-Object { ($_ -split "[<>=]")[0].Trim() }
    Write-Host "  Shared packages in requirements-agents.txt: $($sharedPackages.Count)" -ForegroundColor Cyan
}

$agentReqFiles = Get-ChildItem -Path (Join-Path $projectRoot "agents") -Recurse -Filter "requirements.txt"
$duplicatePackages = @{}

foreach ($reqFile in $agentReqFiles) {
    $packages = Get-Content $reqFile.FullName | Where-Object {
        $_ -match "^[a-zA-Z]" -and $_ -notmatch "^#"
    }

    foreach ($pkg in $packages) {
        $pkgName = ($pkg -split "[<>=]")[0].Trim()
        if ($sharedPackages -contains $pkgName) {
            $warnings += "Package '$pkgName' in $($reqFile.Name) is already in shared requirements"
        }
        if (-not $duplicatePackages.ContainsKey($pkgName)) {
            $duplicatePackages[$pkgName] = @()
        }
        $duplicatePackages[$pkgName] += $reqFile.Directory.Name
    }
}

$packagesToConsolidate = $duplicatePackages.GetEnumerator() | Where-Object { $_.Value.Count -ge 3 }
if ($packagesToConsolidate) {
    Write-Host "  Packages appearing in 3+ agents (consider consolidating):" -ForegroundColor Yellow
    foreach ($pkg in $packagesToConsolidate) {
        Write-Host "    [~] $($pkg.Key): $($pkg.Value -join ', ')" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [OK] No duplicate packages to consolidate" -ForegroundColor Green
}

# ============================================================================
# Check 5: Base Class Usage
# ============================================================================
Write-Host "`n[5/5] Checking BaseAgent adoption..." -ForegroundColor Yellow

$baseAgentPath = Join-Path $projectRoot "shared\base_agent.py"
if (Test-Path $baseAgentPath) {
    $agentsUsingBase = 0
    $agentsNotUsingBase = @()

    foreach ($file in $agentFiles) {
        $content = Get-Content $file.FullName -Raw
        if ($content -match "class \w+\(BaseAgent\)") {
            $agentsUsingBase++
        } else {
            $agentsNotUsingBase += $file.Directory.Name
        }
    }

    Write-Host "  Agents using BaseAgent: $agentsUsingBase / $($agentFiles.Count)" -ForegroundColor Cyan

    if ($agentsNotUsingBase.Count -gt 0) {
        Write-Host "  Agents NOT using BaseAgent:" -ForegroundColor Yellow
        foreach ($agent in $agentsNotUsingBase) {
            Write-Host "    [~] $agent" -ForegroundColor Yellow
            $warnings += "Agent '$agent' does not extend BaseAgent"
        }
    } else {
        Write-Host "  [OK] All agents use BaseAgent" -ForegroundColor Green
    }
} else {
    Write-Host "  [?] BaseAgent not found at shared/base_agent.py" -ForegroundColor Gray
}

# ============================================================================
# Summary
# ============================================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($issues.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "[OK] No optimization issues found!" -ForegroundColor Green
    Write-Host "     Next check recommended: $(Get-Date (Get-Date).AddDays(7) -Format 'yyyy-MM-dd')" -ForegroundColor Gray
} else {
    if ($issues.Count -gt 0) {
        Write-Host "ISSUES ($($issues.Count)):" -ForegroundColor Red
        foreach ($issue in $issues) {
            Write-Host "  - $issue" -ForegroundColor Red
        }
    }

    if ($warnings.Count -gt 0) {
        Write-Host "`nWARNINGS ($($warnings.Count)):" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  - $warning" -ForegroundColor Yellow
        }
    }

    Write-Host "`nSee docs/OPTIMIZATION-WORKFLOW.md for procedures." -ForegroundColor Cyan
}

Write-Host "`n"

# Return exit code based on issues
if ($issues.Count -gt 0) {
    exit 1
} else {
    exit 0
}
