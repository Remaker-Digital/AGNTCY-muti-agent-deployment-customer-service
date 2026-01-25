# GitHub Actions CI/CD Workflows

## Overview

This directory contains GitHub Actions workflows for continuous integration and deployment of the Multi-Agent Customer Service platform.

## Workflows

### `ci.yml` - Main CI Pipeline

**Purpose**: Automated testing, code quality checks, and PR validation

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Nightly cron schedule (2 AM UTC) for regression suite
- Manual workflow dispatch

**Jobs**:

1. **Code Quality Checks** (`lint`)
   - Black formatter validation (line length 100)
   - Flake8 linting (syntax errors, undefined names)
   - Bandit security scanning
   - Runs on: All triggers
   - Reports uploaded as artifacts (30-day retention)

2. **Unit Tests** (`unit-tests`)
   - Tests: `tests/unit/`
   - Coverage: `shared/` module
   - Runs on: All triggers
   - Coverage reports uploaded to Codecov (PR comments)
   - Artifacts: XML and HTML coverage reports (30-day retention)

3. **Integration Tests** (`integration-tests`)
   - Tests: `tests/integration/`
   - Coverage: `agents/` module
   - Docker services: SLIM, mock-shopify, mock-zendesk, mock-mailchimp, mock-analytics
   - Runs on: All triggers
   - Artifacts: Coverage reports (30-day), Docker logs on failure (7-day retention)

4. **Performance Benchmarking** (`performance-tests`)
   - Tests: `tests/performance/test_response_time_benchmarking.py`
   - Measures P50/P95/P99 response times for all 17 intent types
   - Runs on: Nightly schedule, manual dispatch only
   - Artifacts: Performance results JSON (90-day retention)

5. **Multi-Turn Conversation Tests** (`multi-turn-tests`)
   - Tests: `tests/e2e/test_multi_turn_conversations.py`
   - Validates context preservation, intent chaining, clarification loops
   - Runs on: Nightly schedule, manual dispatch only
   - Continues on error (expected Phase 2 limitations)

6. **Agent Communication Tests** (`agent-comm-tests`)
   - Tests: `tests/e2e/test_agent_communication.py`
   - Validates A2A message routing, topic-based routing, error handling
   - Runs on: Nightly schedule, manual dispatch only
   - Fails on error (critical functionality)

7. **PR Validation Summary** (`pr-validation`)
   - Runs on: Pull requests only
   - Depends on: lint, unit-tests, integration-tests
   - Provides summary of all required checks

## PR Validation Requirements

For a PR to be approved, the following jobs must pass:
- ✅ Code Quality Checks (lint)
- ✅ Unit Tests (unit-tests)
- ✅ Integration Tests (integration-tests)

Performance, multi-turn, and agent communication tests run nightly but are not PR blockers.

## Nightly Regression Suite

**Schedule**: Daily at 2 AM UTC (9 PM ET / 6 PM PT)

**Tests Included**:
- All PR validation jobs (lint, unit, integration)
- Performance benchmarking (17 intent types)
- Multi-turn conversation tests (10 scenarios)
- Agent communication tests (10 scenarios)

**Purpose**:
- Catch regressions not covered by PR checks
- Monitor performance trends over time
- Validate expected Phase 2 limitations remain stable
- Educational: Demonstrate comprehensive testing strategy

## Manual Workflow Dispatch

All workflows can be triggered manually via GitHub Actions UI:
1. Go to Actions tab
2. Select workflow (CI - Multi-Agent Customer Service)
3. Click "Run workflow"
4. Select branch
5. Click "Run workflow" button

Useful for:
- Testing workflow changes
- Running full regression suite on-demand
- Debugging CI issues
- Generating fresh performance baselines

## Artifacts

| Artifact | Retention | Jobs |
|----------|-----------|------|
| Bandit security report | 30 days | lint |
| Coverage reports (unit) | 30 days | unit-tests |
| Coverage reports (integration) | 30 days | integration-tests |
| Docker logs (on failure) | 7 days | integration-tests, multi-turn-tests, agent-comm-tests |
| Performance benchmark results | 90 days | performance-tests |

## Caching

**Pip dependencies** are cached across workflow runs to improve speed:
- Cache key: `${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}`
- Restore keys: `${{ runner.os }}-pip-`
- Cache location: `~/.cache/pip`

Cache invalidates when `requirements.txt` changes.

## Environment Variables

- `PYTHON_VERSION`: `3.14` (required by AGNTCY SDK)

## Docker Services

Integration, multi-turn, and agent communication tests require Docker services:

**Started services**:
- `slim-service` (AGNTCY transport layer)
- `mock-shopify` (Shopify API mock)
- `mock-zendesk` (Zendesk API mock)
- `mock-mailchimp` (Mailchimp API mock)
- `mock-analytics` (Google Analytics mock)

**Startup wait**: 10 seconds (allows services to initialize)

**Cleanup**: All services stopped with `docker compose down` in `if: always()` step

## Codecov Integration

Unit test coverage reports are automatically uploaded to Codecov on pull requests:
- Flag: `unittests`
- File: `coverage.xml`
- PR comments: Enabled (shows coverage diff)

**Note**: Requires `CODECOV_TOKEN` secret in repository settings (optional for public repos).

## Troubleshooting

### Job Failures

**Lint job fails**:
- Run `black --check --line-length 100 .` locally
- Run `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics` locally
- Fix formatting/linting issues and commit

**Unit tests fail**:
- Run `pytest tests/unit/ -v` locally
- Check test logs in job output
- Verify `requirements.txt` has all dependencies

**Integration tests fail**:
- Check Docker service logs in artifacts (if job failed)
- Verify `docker compose up -d` works locally
- Run `pytest tests/integration/ -v` locally with services running

**Performance tests fail**:
- Check if P95 > 2000ms (performance regression)
- Review performance results JSON artifact
- Compare with previous baseline in `docs/PHASE-3-DAY-6-7-SUMMARY.md`

### Workflow Not Triggering

**On push**:
- Verify push is to `main` or `develop` branch
- Check workflow syntax with `yamllint .github/workflows/ci.yml`

**On PR**:
- Verify PR targets `main` or `develop` branch
- Check PR not from fork (forks have limited permissions)

**Nightly**:
- Check GitHub Actions logs for cron trigger
- Verify cron syntax: `0 2 * * *` (2 AM UTC daily)

### Artifact Upload Failures

- Check artifact name is unique
- Verify path exists before upload
- Check artifact size < 2 GB limit

## Cost Optimization

**GitHub Actions minutes** (free tier: 2,000 min/month for public repos):

**Per workflow run** (estimated):
- Lint: ~2 minutes
- Unit tests: ~3 minutes
- Integration tests: ~5 minutes
- Performance tests: ~8 minutes (nightly only)
- Multi-turn tests: ~4 minutes (nightly only)
- Agent comm tests: ~4 minutes (nightly only)

**Total per PR**: ~10 minutes
**Total nightly**: ~26 minutes

**Monthly estimate**:
- 30 nightly runs: 30 × 26 = 780 minutes
- 60 PR runs (avg 2/day): 60 × 10 = 600 minutes
- **Total: ~1,380 minutes/month** (within free tier)

## Future Enhancements (Phase 4-5)

- [ ] Azure DevOps Pipelines integration
- [ ] Azure deployment workflows (staging, production)
- [ ] Load testing with Azure Load Testing service
- [ ] Security scanning with OWASP ZAP
- [ ] Dependency scanning with Snyk
- [ ] Container image builds and pushes to ACR
- [ ] Terraform plan/apply for infrastructure changes
- [ ] Blue-green deployment automation

## References

- GitHub Actions Docs: https://docs.github.com/en/actions
- Codecov Action: https://github.com/codecov/codecov-action
- Docker Compose in CI: https://docs.docker.com/compose/ci-cd/

---

**Created**: January 25, 2026
**Phase**: Phase 3, Week 3, Days 11-12
**Status**: Active
