<#
.SYNOPSIS
    Archives historical content from CLAUDE.md to CLAUDE-HISTORY.md

.DESCRIPTION
    This script moves older session summaries and completed phase documentation
    from CLAUDE.md to docs/CLAUDE-HISTORY.md to reduce token usage.

    Safe operations:
    - Only moves content marked with specific date headers
    - Preserves current phase documentation
    - Creates backup before modification
    - Validates file integrity after changes

.PARAMETER DaysOld
    Archive content older than this many days (default: 14)

.PARAMETER DryRun
    Show what would be archived without making changes

.EXAMPLE
    .\scripts\archive-claude-history.ps1 -DryRun
    .\scripts\archive-claude-history.ps1 -DaysOld 7

.NOTES
    Run weekly or when CLAUDE.md exceeds 900 lines.
    See docs/OPTIMIZATION-WORKFLOW.md for detailed procedures.
#>

param(
    [int]$DaysOld = 14,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectRoot

$claudeMdPath = Join-Path $projectRoot "CLAUDE.md"
$historyPath = Join-Path $projectRoot "docs\CLAUDE-HISTORY.md"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  CLAUDE.md ARCHIVE TOOL" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "  [DRY RUN MODE]" -ForegroundColor Yellow
}
Write-Host "========================================`n" -ForegroundColor Cyan

# Check files exist
if (-not (Test-Path $claudeMdPath)) {
    Write-Host "[ERROR] CLAUDE.md not found" -ForegroundColor Red
    exit 1
}

# Get current line counts
$beforeLines = (Get-Content $claudeMdPath | Measure-Object -Line).Lines
Write-Host "Current CLAUDE.md: $beforeLines lines" -ForegroundColor Cyan

if ($beforeLines -lt 800) {
    Write-Host "[OK] CLAUDE.md is under 800 lines - no archiving needed" -ForegroundColor Green
    exit 0
}

# Read content
$content = Get-Content $claudeMdPath -Raw

# Find the "Recent Updates" section
# Pattern: ### YYYY-MM-DD: Description
$datePattern = '### (\d{4}-\d{2}-\d{2}):'
$matches = [regex]::Matches($content, $datePattern)

if ($matches.Count -eq 0) {
    Write-Host "[INFO] No dated sections found to archive" -ForegroundColor Yellow
    exit 0
}

$cutoffDate = (Get-Date).AddDays(-$DaysOld)
$sectionsToArchive = @()

Write-Host "`nAnalyzing dated sections (archiving content older than $DaysOld days)..." -ForegroundColor Yellow

foreach ($match in $matches) {
    $dateStr = $match.Groups[1].Value
    $sectionDate = [DateTime]::ParseExact($dateStr, "yyyy-MM-dd", $null)

    if ($sectionDate -lt $cutoffDate) {
        $sectionsToArchive += $dateStr
        Write-Host "  [ARCHIVE] $dateStr ($(((Get-Date) - $sectionDate).Days) days old)" -ForegroundColor Yellow
    } else {
        Write-Host "  [KEEP] $dateStr ($(((Get-Date) - $sectionDate).Days) days old)" -ForegroundColor Green
    }
}

if ($sectionsToArchive.Count -eq 0) {
    Write-Host "`n[OK] No sections old enough to archive" -ForegroundColor Green
    exit 0
}

Write-Host "`nSections to archive: $($sectionsToArchive.Count)" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "`n[DRY RUN] Would archive the following dates:" -ForegroundColor Yellow
    foreach ($date in $sectionsToArchive) {
        Write-Host "  - $date" -ForegroundColor Yellow
    }
    Write-Host "`n[DRY RUN] No changes made. Remove -DryRun to perform archiving." -ForegroundColor Yellow
    exit 0
}

# Create backup
$backupPath = "$claudeMdPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $claudeMdPath $backupPath
Write-Host "`nBackup created: $backupPath" -ForegroundColor Gray

# Extract sections to archive
$archiveContent = ""
$newContent = $content

foreach ($dateStr in $sectionsToArchive) {
    # Find the section start
    $sectionPattern = "### $dateStr[:\s][\s\S]*?(?=###|\z)"
    $sectionMatch = [regex]::Match($newContent, $sectionPattern)

    if ($sectionMatch.Success) {
        $archiveContent += "`n" + $sectionMatch.Value
        $newContent = $newContent.Replace($sectionMatch.Value, "")
    }
}

# Clean up extra newlines
$newContent = $newContent -replace "`n{3,}", "`n`n"

# Append to history file
if (Test-Path $historyPath) {
    $existingHistory = Get-Content $historyPath -Raw
    $archiveContent = $existingHistory + "`n---`n`n## Archived $(Get-Date -Format 'yyyy-MM-dd')`n" + $archiveContent
} else {
    $archiveContent = @"
# CLAUDE.md - Historical Updates Archive

This file contains the historical update log moved from CLAUDE.md to reduce token usage.
For current project context, see CLAUDE.md.

---

## Archived $(Get-Date -Format 'yyyy-MM-dd')
$archiveContent
"@
}

# Write files
Set-Content -Path $historyPath -Value $archiveContent -NoNewline
Set-Content -Path $claudeMdPath -Value $newContent -NoNewline

# Verify
$afterLines = (Get-Content $claudeMdPath | Measure-Object -Line).Lines
$historyLines = (Get-Content $historyPath | Measure-Object -Line).Lines

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ARCHIVE COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "CLAUDE.md: $beforeLines -> $afterLines lines (reduced by $($beforeLines - $afterLines))" -ForegroundColor Green
Write-Host "CLAUDE-HISTORY.md: $historyLines lines" -ForegroundColor Cyan
Write-Host "`nBackup saved to: $backupPath" -ForegroundColor Gray

# Cleanup old backups (keep last 5)
$backups = Get-ChildItem -Path $projectRoot -Filter "CLAUDE.md.backup-*" | Sort-Object LastWriteTime -Descending
if ($backups.Count -gt 5) {
    $backups | Select-Object -Skip 5 | ForEach-Object {
        Remove-Item $_.FullName
        Write-Host "Removed old backup: $($_.Name)" -ForegroundColor Gray
    }
}

Write-Host "`n[OK] Archive complete. Review changes and commit when ready." -ForegroundColor Green
