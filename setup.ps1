# AGNTCY Multi-Agent Customer Service Platform - Setup Script for Windows
# This script automates the initial setup for Phase 1 development
#
# Usage: .\setup.ps1

Write-Host "AGNTCY Multi-Agent Customer Service Platform - Setup" -ForegroundColor Cyan
Write-Host ("=" * 60)

# Check prerequisites
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow

# Check Python version
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.1[2-9]") {
        Write-Host "[OK] Python $pythonVersion found" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Python 3.12+ required. Found: $pythonVersion" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.12+" -ForegroundColor Red
    exit 1
}

# Check Docker
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "[OK] Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker Desktop not found. Please install Docker Desktop for Windows" -ForegroundColor Red
    exit 1
}

# Check Docker Compose
try {
    $composeVersion = docker-compose --version 2>&1
    Write-Host "[OK] Docker Compose found: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker Compose not found." -ForegroundColor Red
    exit 1
}

# Check Git
try {
    $gitVersion = git --version 2>&1
    Write-Host "[OK] Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Git not found. Install Git or GitHub Desktop for version control" -ForegroundColor Yellow
}

# Create Python virtual environment
Write-Host "`nSetting up Python virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists. Skipping..." -ForegroundColor Gray
} else {
    python -m venv venv
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment and install dependencies
Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Copy .env.example to .env if it doesn't exist
Write-Host "`nSetting up environment variables..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host ".env file already exists. Skipping..." -ForegroundColor Gray
} else {
    Copy-Item .env.example .env
    Write-Host "[OK] Created .env file from template" -ForegroundColor Green
    Write-Host "   NOTE: Review and update .env with your configuration" -ForegroundColor Cyan
}

# Create necessary directories
Write-Host "`nCreating directory structure..." -ForegroundColor Yellow
$directories = @(
    "logs",
    "docs/dr-test-results",
    "tests/unit",
    "tests/integration",
    "tests/e2e"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "[OK] Created $dir" -ForegroundColor Green
    }
}

# Pull Docker images (to avoid delays during first docker-compose up)
Write-Host "`nPulling Docker images (this may take a few minutes)..." -ForegroundColor Yellow
docker-compose pull

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Docker images pulled successfully" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Some images failed to pull. Will build locally instead." -ForegroundColor Yellow
}

# Build custom containers
Write-Host "`nBuilding custom Docker containers..." -ForegroundColor Yellow
docker-compose build

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Containers built successfully" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Some containers failed to build. Review logs above." -ForegroundColor Yellow
}

# Install pre-commit hooks (optional but recommended)
Write-Host "`nSetting up pre-commit hooks (optional)..." -ForegroundColor Yellow
try {
    pre-commit install
    Write-Host "[OK] Pre-commit hooks installed" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Pre-commit not configured. Run 'pre-commit install' manually if needed." -ForegroundColor Yellow
}

# Summary
Write-Host "`n" + ("=" * 60)
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Review and update .env file with your configuration"
Write-Host "  2. Start services: docker-compose up -d"
Write-Host "  3. View logs: docker-compose logs -f"
Write-Host "  4. Access Grafana: http://localhost:3001 (admin/admin)"
Write-Host "  5. Run tests: pytest tests/ -v"
Write-Host "`nDocumentation:"
Write-Host "  - README.md: Quick start guide"
Write-Host "  - PROJECT-README.txt: Detailed specifications"
Write-Host "  - AGNTCY-REVIEW.md: SDK integration guide"
Write-Host "  - CLAUDE.md: AI assistant guidance"
Write-Host "`nHelpful commands:"
Write-Host "  - docker-compose ps          # View service status"
Write-Host "  - docker-compose logs -f     # View all logs"
Write-Host "  - docker-compose down        # Stop services"
Write-Host "  - docker-compose down -v     # Stop and remove data"
Write-Host "`nTroubleshooting:"
Write-Host "  - If services fail to start, check Docker Desktop is running"
Write-Host "  - If ports are in use, edit docker-compose.yml"
Write-Host "  - For issues, see README.md Troubleshooting section"
Write-Host "`nCurrent Phase: Phase 1 - Infrastructure & Containers"
Write-Host "Budget: `$0/month (local development only)"
Write-Host "`n" + ("=" * 60)
