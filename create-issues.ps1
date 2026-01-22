# Create GitHub Issues from Project Requirements
# Purpose: Generate user stories and tasks for AGNTCY project board

$ErrorActionPreference = "Stop"
$ghExe = "C:\Program Files\GitHub CLI\gh.exe"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Creating GitHub Issues from PROJECT-README" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$repoFullName = "Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service"
$projectNumber = 1

# Define user stories for Phase 1 (Infrastructure & Containers)
$phase1Stories = @(
    @{
        title = "Set up Docker Compose infrastructure for local development"
        body = @"
## User Story
As a developer
I want a fully containerized local development environment
So that I can develop and test the multi-agent system without cloud resources

## Acceptance Criteria
- [ ] Docker Compose file defines all 13 services
- [ ] All containers start successfully with docker-compose up
- [ ] Services can communicate via Docker network
- [ ] Health checks configured for all services
- [ ] Environment variables configured via .env file

## Technical Notes
- Services: 5 agents + 4 mock APIs + observability stack (Grafana, ClickHouse, OTLP collector)
- Use docker-compose.yml in project root
- .env.example provided as template

## Definition of Done
- [ ] All containers running without errors
- [ ] Documentation updated in README.md
- [ ] Health check endpoints responding
- [ ] Local testing validated
"@
        labels = @("type: feature", "priority: high", "component: infrastructure", "phase: phase-1")
        milestone = "Phase 1 - Infrastructure"
    },
    @{
        title = "Implement mock Shopify API service"
        body = @"
## User Story
As a developer
I want a mock Shopify API service
So that I can test agent integrations without real API calls or costs

## Acceptance Criteria
- [ ] Mock endpoints for products, orders, customers
- [ ] Realistic test data fixtures
- [ ] RESTful API following Shopify conventions
- [ ] Dockerized service
- [ ] Unit tests for all endpoints

## Technical Notes
- Location: mocks/shopify/
- Framework: Flask or FastAPI
- Test data: test-data/shopify/
- Port: 8001

## Definition of Done
- [ ] Service responds to API calls
- [ ] Test coverage >80%
- [ ] Documentation complete
- [ ] Integrated into docker-compose.yml
"@
        labels = @("type: feature", "priority: high", "component: api", "phase: phase-1")
        milestone = "Phase 1 - Infrastructure"
    },
    @{
        title = "Implement mock Zendesk API service"
        body = @"
## User Story
As a developer
I want a mock Zendesk API service
So that I can test ticketing integrations without external dependencies

## Acceptance Criteria
- [ ] Mock endpoints for tickets, users, comments
- [ ] Realistic test data fixtures
- [ ] RESTful API following Zendesk conventions
- [ ] Dockerized service
- [ ] Unit tests for all endpoints

## Technical Notes
- Location: mocks/zendesk/
- Framework: Flask or FastAPI
- Test data: test-data/zendesk/
- Port: 8002

## Definition of Done
- [ ] Service responds to API calls
- [ ] Test coverage >80%
- [ ] Documentation complete
- [ ] Integrated into docker-compose.yml
"@
        labels = @("type: feature", "priority: high", "component: api", "phase: phase-1")
        milestone = "Phase 1 - Infrastructure"
    },
    @{
        title = "Implement Intent Classification Agent foundation"
        body = @"
## User Story
As a developer
I want an Intent Classification Agent foundation
So that incoming customer requests can be properly categorized and routed

## Acceptance Criteria
- [ ] Agent skeleton with AGNTCY SDK integration
- [ ] Factory pattern implementation
- [ ] A2A protocol support
- [ ] Basic routing logic (mock/demo mode)
- [ ] Dockerized agent service
- [ ] Unit tests for agent initialization

## Technical Notes
- Location: agents/intent_classification/
- Protocol: A2A (agent-to-agent)
- Transport: SLIM (secure, low-latency)
- Factory: Use shared/factory.py singleton pattern

## Definition of Done
- [ ] Agent starts and registers successfully
- [ ] Can receive and route messages
- [ ] Test coverage >70%
- [ ] Documentation complete
"@
        labels = @("type: feature", "priority: critical", "component: agent", "phase: phase-1")
        milestone = "Phase 1 - Infrastructure"
    },
    @{
        title = "Set up observability stack (Grafana + ClickHouse + OTLP)"
        body = @"
## User Story
As a developer
I want an observability stack for local development
So that I can monitor agent performance and debug issues

## Acceptance Criteria
- [ ] Grafana dashboard accessible at localhost:3001
- [ ] ClickHouse database for trace storage
- [ ] OTLP collector receiving telemetry
- [ ] Basic dashboards for agent metrics
- [ ] All services configured in docker-compose.yml

## Technical Notes
- Grafana: Port 3001
- ClickHouse: Port 9000
- OTLP Collector: Port 4318 (HTTP)
- Enable tracing: AgntcyFactory(enable_tracing=True)

## Definition of Done
- [ ] All observability services running
- [ ] Telemetry data flowing to ClickHouse
- [ ] Dashboard displays agent metrics
- [ ] Documentation for accessing dashboards
"@
        labels = @("type: feature", "priority: medium", "component: observability", "phase: phase-1")
        milestone = "Phase 1 - Infrastructure"
    },
    @{
        title = "Create shared utilities (factory, models, utils)"
        body = @"
## User Story
As a developer
I want shared utility modules
So that agents can reuse common functionality and patterns

## Acceptance Criteria
- [ ] AgntcyFactory singleton implementation
- [ ] Common message models (Request, Response, Message)
- [ ] Utility functions (logging, config, validation)
- [ ] Unit tests for all utilities
- [ ] Documentation with usage examples

## Technical Notes
- Location: shared/
- Files: factory.py, models.py, utils.py
- Factory pattern: Single instance per application
- Type hints for all public APIs

## Definition of Done
- [ ] All utilities tested (>90% coverage)
- [ ] Documentation complete
- [ ] Used by at least one agent
- [ ] No circular dependencies
"@
        labels = @("type: feature", "priority: high", "component: shared", "phase: phase-1")
        milestone = "Phase 1 - Infrastructure"
    },
    @{
        title = "Set up GitHub Actions CI pipeline"
        body = @"
## User Story
As a developer
I want automated CI/CD pipeline
So that code quality is maintained and tests run automatically

## Acceptance Criteria
- [ ] Workflow file in .github/workflows/dev-ci.yml
- [ ] Runs on push and pull request
- [ ] Executes pytest test suite
- [ ] Reports code coverage
- [ ] Linting with flake8 and black
- [ ] Docker image build validation

## Technical Notes
- Trigger: push to main, pull requests
- Python version: 3.12+
- Coverage threshold: 70% (Phase 1 baseline)
- Use GitHub Actions free tier

## Definition of Done
- [ ] Pipeline runs successfully
- [ ] All tests passing
- [ ] Coverage report generated
- [ ] Badge added to README.md
"@
        labels = @("type: feature", "priority: high", "component: ci-cd", "phase: phase-1")
        milestone = "Phase 1 - Infrastructure"
    },
    @{
        title = "Write comprehensive test suite for mock APIs"
        body = @"
## User Story
As a developer
I want comprehensive tests for mock APIs
So that integrations are reliable and regressions are caught early

## Acceptance Criteria
- [ ] Unit tests for all mock API endpoints
- [ ] Test fixtures in test-data/ directories
- [ ] Integration tests for API workflows
- [ ] >80% code coverage for all mocks
- [ ] Pytest configuration optimized

## Technical Notes
- Location: tests/unit/, tests/integration/
- Framework: pytest with fixtures
- Mock data: test-data/{shopify,zendesk,mailchimp,google_analytics}/
- Run via: pytest tests/

## Definition of Done
- [ ] All tests passing
- [ ] Coverage meets threshold (>80%)
- [ ] Documentation for running tests
- [ ] CI pipeline executes tests
"@
        labels = @("type: test", "priority: high", "component: testing", "phase: phase-1")
        milestone = "Phase 1 - Infrastructure"
    }
)

# Create Phase 1 milestone if it doesn't exist
Write-Host "[1/2] Creating milestone..." -ForegroundColor Yellow
try {
    $milestone = & $ghExe api "repos/$repoFullName/milestones" `
        -f title="Phase 1 - Infrastructure" `
        -f description="Create infrastructure and deployable containers with all essential software. Budget: `$0/month (local development only)" `
        -f due_on="2026-02-28T23:59:59Z" `
        --method POST 2>&1

    Write-Host "[OK] Milestone created" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Milestone may already exist, continuing..." -ForegroundColor Gray
}

# Create issues
Write-Host ""
Write-Host "[2/2] Creating issues..." -ForegroundColor Yellow
Write-Host ""

$createdCount = 0
$errorCount = 0

foreach ($story in $phase1Stories) {
    Write-Host "Creating: $($story.title)" -ForegroundColor Cyan

    try {
        # Create the issue
        $labelArgs = $story.labels | ForEach-Object { "-l", $_ }

        $result = & $ghExe issue create `
            --repo $repoFullName `
            --title $story.title `
            --body $story.body `
            @labelArgs `
            --milestone $story.milestone

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Created: $result" -ForegroundColor Green
            $createdCount++

            # Add to project (if project number is available)
            # Note: This requires GraphQL API for new projects
            # For now, issues can be added manually to project board

        } else {
            Write-Host "[ERROR] Failed to create issue" -ForegroundColor Red
            $errorCount++
        }
    } catch {
        Write-Host "[ERROR] Exception: $_" -ForegroundColor Red
        $errorCount++
    }

    Start-Sleep -Milliseconds 500
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Issue Creation Complete!" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  Created: $createdCount issues" -ForegroundColor Green
Write-Host "  Errors: $errorCount issues" -ForegroundColor $(if ($errorCount -eq 0) { "Green" } else { "Red" })
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Visit: https://github.com/$repoFullName/issues" -ForegroundColor White
Write-Host "  2. Add issues to project board manually (or via GraphQL API)" -ForegroundColor White
Write-Host "  3. Configure labels if not auto-created" -ForegroundColor White
Write-Host ""
Write-Host "To add issues to project board:" -ForegroundColor Cyan
Write-Host "  https://github.com/orgs/Remaker-Digital/projects/$projectNumber" -ForegroundColor White
Write-Host ""
