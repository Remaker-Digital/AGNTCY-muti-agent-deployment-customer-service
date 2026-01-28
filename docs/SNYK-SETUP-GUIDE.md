# Snyk Integration Setup Guide

**Created:** 2026-01-28
**Purpose:** Configure Snyk dependency scanning in Azure DevOps pipeline
**Related Task:** Phase 5 Task #16

---

## Overview

Snyk provides automated security scanning for:
- **Python dependencies** (requirements.txt)
- **Container images** (Dockerfiles)
- **Infrastructure as Code** (Terraform files)
- **License compliance** (OSS license verification)

## Prerequisites

1. **Snyk Account** - Free tier available at [snyk.io](https://snyk.io)
2. **Azure DevOps Variable Group** - `agntcy-prod-secrets` with SNYK_TOKEN
3. **npm** - Available on Azure DevOps Ubuntu agents

## Setup Steps

### Step 1: Create Snyk Account

1. Go to [https://snyk.io/signup](https://snyk.io/signup)
2. Sign up with GitHub, Google, or email
3. Free tier includes:
   - 200 open source tests/month
   - 100 container tests/month
   - Unlimited projects

### Step 2: Get API Token

1. Log into [app.snyk.io](https://app.snyk.io)
2. Go to **Settings** (gear icon) > **General**
3. Find **API Token** section
4. Click **Click to show** to reveal token
5. Copy the token (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### Step 3: Add Token to Azure DevOps

1. Go to Azure DevOps project
2. Navigate to **Pipelines** > **Library**
3. Select variable group **agntcy-prod-secrets**
4. Click **+ Add**
5. Add variable:
   - **Name:** `SNYK_TOKEN`
   - **Value:** (paste your token)
   - **Keep this value secret:** ✅ Checked
6. Click **Save**

### Step 4: Verify Pipeline Configuration

The `azure-pipelines.yml` already includes Snyk scanning. Verify:

```yaml
- job: SnykScan
  displayName: 'Snyk Dependency Scan'
  pool:
    vmImage: 'ubuntu-latest'
  variables:
    - group: agntcy-prod-secrets  # Contains SNYK_TOKEN
```

### Step 5: Run Pipeline

1. Trigger pipeline via commit or manual run
2. Monitor the **Snyk Dependency Scan** job
3. Review artifacts in **snyk-security-reports**

## Vulnerability Thresholds

| Severity | Pipeline Behavior | Action Required |
|----------|------------------|-----------------|
| **Critical** | ❌ Fail build | Must fix before deploy |
| **High** | ❌ Fail build | Must fix before deploy |
| **Medium** | ⚠️ Warning | Review and plan fix |
| **Low** | ℹ️ Informational | Acknowledge risk |

## Scan Types

### 1. Python Dependency Scan

```bash
snyk test --file=requirements.txt
```

Checks all Python packages for:
- Known vulnerabilities (CVEs)
- Outdated packages with security issues
- Transitive dependency vulnerabilities

### 2. Container Image Scan

```bash
snyk container test --file=api_gateway/Dockerfile
```

Analyzes:
- Base image vulnerabilities
- Added package vulnerabilities
- Dockerfile best practices

### 3. Infrastructure as Code Scan (Optional)

```bash
snyk iac test terraform/
```

Detects:
- Misconfigured security settings
- Public exposure risks
- Compliance violations

## Reading Snyk Reports

### Pipeline Artifacts

After each run, check:
- `snyk-security-reports/snyk-results.json` - Machine-readable results
- `snyk-security-reports/snyk-report.txt` - Human-readable summary
- `snyk-security-reports/snyk-container-results.json` - Container scan results

### Report Fields

| Field | Description |
|-------|-------------|
| `vulnerabilities` | List of found issues |
| `severity` | critical, high, medium, low |
| `packageName` | Affected package |
| `version` | Vulnerable version |
| `fixedIn` | Version with fix (if available) |
| `paths` | Dependency chain |

## Fixing Vulnerabilities

### Option 1: Upgrade Package

```bash
# Check current version
pip show package-name

# Upgrade to fixed version
pip install package-name==fixed.version

# Update requirements.txt
pip freeze > requirements.txt
```

### Option 2: Snyk Wizard (Interactive)

```bash
# Install Snyk CLI locally
npm install -g snyk

# Run wizard
snyk wizard
```

### Option 3: Ignore (with justification)

Create `.snyk` file:

```yaml
# Snyk policy file
version: v1.25.0
ignore:
  'snyk:lic:pip:package-name:License':
    - '*':
        reason: 'Internal use only, license acceptable'
        expires: 2027-01-01
```

## Cost Considerations

| Plan | Price | Tests/Month | Features |
|------|-------|-------------|----------|
| **Free** | $0 | 200 OSS, 100 container | Basic scanning |
| **Team** | $98/dev/month | Unlimited | Priority fixes, reporting |
| **Enterprise** | Custom | Unlimited | SSO, SLA, support |

**Recommendation:** Free tier is sufficient for this project (~20 scans/month expected).

## Troubleshooting

### "SNYK_TOKEN not configured"

**Cause:** Token not in variable group or group not linked.

**Fix:**
1. Verify token in `agntcy-prod-secrets` variable group
2. Ensure variable group is linked to pipeline

### "No vulnerabilities found but scan failed"

**Cause:** Authentication or network issue.

**Fix:**
1. Verify token is valid (not expired)
2. Check Snyk service status at [status.snyk.io](https://status.snyk.io)

### "Container scan failed"

**Cause:** Dockerfile not found or malformed.

**Fix:**
1. Verify Dockerfile path is correct
2. Ensure Dockerfile is valid (no syntax errors)

## Integration with Other Tools

### GitHub Integration (Optional)

1. Install Snyk GitHub App
2. Automatic PR scanning
3. Fix PRs generated automatically

### IDE Integration (Recommended)

Install Snyk extension for VS Code:
- Real-time vulnerability detection
- Inline fix suggestions
- License information

## Monitoring and Alerts

### Snyk Dashboard

1. Log into [app.snyk.io](https://app.snyk.io)
2. View project vulnerabilities
3. Track fix progress over time

### Slack Notifications (Optional)

1. Go to Snyk Settings > Integrations
2. Configure Slack webhook
3. Receive alerts on new vulnerabilities

## Known Vulnerabilities (Current)

| CVE | Package | Severity | Status |
|-----|---------|----------|--------|
| CVE-2026-0994 | protobuf 6.33.4 | High | Monitoring (no patch) |

See `docs/SECURITY-ADVISORY-2026-01-27.md` for details.

---

## Quick Reference

### Local Testing

```bash
# Install Snyk CLI
npm install -g snyk

# Authenticate
snyk auth

# Test Python project
snyk test --file=requirements.txt

# Test with severity threshold
snyk test --severity-threshold=high

# Generate HTML report
snyk test --json | snyk-to-html > snyk-report.html
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SNYK_TOKEN` | API authentication token | Yes |
| `SNYK_ORG` | Organization ID (optional) | No |
| `SNYK_PROJECT_NAME` | Project name override | No |

---

**Document Maintainer:** Development Team
**Next Review:** 2026-02-28
