#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the AGNTCY Development Console

.DESCRIPTION
    This script starts the Streamlit-based development console for the AGNTCY
    multi-agent customer service platform. The console provides:
    
    - Interactive chatbot client for end-user simulation
    - Real-time agent metrics and performance monitoring  
    - Conversation trace viewer with decision trees
    - System status and health monitoring
    
.PARAMETER Port
    Port to run the console on (default: 8080)
    
.PARAMETER Mode
    Run mode: 'local' for local Python, 'docker' for containerized (default: local)
    
.EXAMPLE
    .\start-console.ps1
    Start console on default port 8080
    
.EXAMPLE
    .\start-console.ps1 -Port 8090 -Mode docker
    Start console in Docker on port 8090
#>

param(
    [int]$Port = 8080,
    [ValidateSet("local", "docker")]
    [string]$Mode = "local"
)

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "🤖 Starting AGNTCY Development Console..." -ForegroundColor Cyan
Write-Host "Mode: $Mode | Port: $Port" -ForegroundColor Gray

try {
    if ($Mode -eq "docker") {
        # Docker mode - run via docker-compose
        Write-Host "Starting console via Docker Compose..." -ForegroundColor Yellow
        
        # Check if Docker is running
        docker info 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker is not running. Please start Docker Desktop."
        }
        
        # Start just the console service and its dependencies
        Write-Host "Building and starting console container..." -ForegroundColor Gray
        docker-compose up --build console
        
    } else {
        # Local mode - run with Python/Streamlit
        Write-Host "Starting console locally with Streamlit..." -ForegroundColor Yellow
        
        # Check if Python is available
        python --version 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Python is not available. Please install Python 3.8+ or use Docker mode."
        }
        
        # Check if virtual environment exists
        if (Test-Path "venv") {
            Write-Host "Activating virtual environment..." -ForegroundColor Gray
            if ($IsWindows -or $env:OS -eq "Windows_NT") {
                & "venv\Scripts\Activate.ps1"
            } else {
                & "venv/bin/activate"
            }
        } else {
            Write-Host "⚠️  Virtual environment not found. Installing dependencies globally..." -ForegroundColor Yellow
        }
        
        # Install console requirements if needed
        Write-Host "Checking console dependencies..." -ForegroundColor Gray
        pip install -q streamlit plotly pandas requests websockets
        
        # Set environment variables for local development
        $env:SLIM_ENDPOINT = "http://localhost:46357"
        $env:SLIM_GATEWAY_PASSWORD = "changeme_local_dev_password"
        $env:OTLP_HTTP_ENDPOINT = "http://localhost:4318"
        $env:LOG_LEVEL = "INFO"
        $env:AGNTCY_ENABLE_TRACING = "true"
        
        # Start Streamlit
        Write-Host "🚀 Starting Streamlit console on port $Port..." -ForegroundColor Green
        Write-Host "Console will be available at: http://localhost:$Port" -ForegroundColor Cyan
        Write-Host "Press Ctrl+C to stop the console" -ForegroundColor Gray
        Write-Host ""
        
        streamlit run console/app.py --server.port $Port --server.headless true --theme.base dark
    }
    
} catch {
    Write-Host "❌ Error starting console: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
    Write-Host "1. For Docker mode: Ensure Docker Desktop is running" -ForegroundColor Gray
    Write-Host "2. For local mode: Ensure Python 3.8+ is installed" -ForegroundColor Gray
    Write-Host "3. Check if port $Port is already in use" -ForegroundColor Gray
    Write-Host "4. Run 'docker-compose up -d' to start infrastructure services first" -ForegroundColor Gray
    exit 1
}