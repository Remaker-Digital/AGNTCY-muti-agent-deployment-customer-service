# Security Advisory: protobuf CVE-2026-0994

**Date:** 2026-01-27
**Status:** Monitoring - No Patch Available
**Risk Level:** Low (for this project)

## Vulnerability Details

| Field | Value |
|-------|-------|
| **CVE** | CVE-2026-0994 |
| **GHSA** | GHSA-7gcm-g887-7qv7 |
| **Severity** | High |
| **Package** | protobuf |
| **Current Version** | 6.33.4 |
| **Affected Versions** | All versions ≤ 6.33.4 |
| **Patched Version** | None available (as of 2026-01-27) |
| **Published** | 2026-01-23 |

## Description

A denial-of-service (DoS) vulnerability exists in `google.protobuf.json_format.ParseDict()` in Python. The `max_recursion_depth` limit can be bypassed when parsing nested `google.protobuf.Any` messages.

An attacker can supply deeply nested Any structures that bypass the intended recursion limit, eventually exhausting Python's recursion stack and causing a `RecursionError`.

## Impact Assessment

### This Project's Exposure

| Factor | Assessment |
|--------|------------|
| **Direct Usage** | None - protobuf is a transitive dependency |
| **Dependency Chain** | streamlit → protobuf |
| **Attack Surface** | Console UI (internal testing tool) |
| **Public Exposure** | None - console runs locally |
| **Untrusted Input** | No untrusted protobuf JSON parsing |

### Risk Rating: **LOW**

The vulnerability requires:
1. Attacker-controlled protobuf JSON input
2. Application parsing that input with `ParseDict()`

This project:
- Does not directly use protobuf
- Does not parse untrusted protobuf JSON
- Console is for internal testing only
- Production agents don't use streamlit

## Mitigation Strategy

### Current Action: Monitor for Patch

1. **No immediate action required** due to low exposure
2. **Monitor** for patched protobuf version release
3. **Update** when patch becomes available

### Monitoring Commands

```powershell
# Check for new protobuf versions
pip index versions protobuf | head -5

# Check Dependabot status
gh api repos/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/dependabot/alerts --jq '.[] | select(.security_vulnerability.package.name == "protobuf") | {state: .state, patched: .security_vulnerability.first_patched_version}'
```

### When Patch is Available

```powershell
# Update protobuf
pip install --upgrade protobuf

# Verify fix
pip show protobuf | grep Version

# Re-run tests
pytest tests/ -v
```

## Alternative Mitigations (Not Recommended)

### Option A: Downgrade to protobuf 5.x
- **Risk:** May break streamlit compatibility
- **Status:** Not tested

### Option B: Remove streamlit dependency
- **Impact:** Removes console testing UI
- **Status:** Not recommended - console is useful for development

### Option C: Dismiss Dependabot Alerts
- **Risk:** May miss future related vulnerabilities
- **Status:** Not recommended

## Timeline

| Date | Action |
|------|--------|
| 2026-01-23 | CVE published |
| 2026-01-27 | Investigation completed, documented |
| TBD | Patched protobuf version released |
| TBD | Update applied |

## References

- [GitHub Advisory GHSA-7gcm-g887-7qv7](https://github.com/advisories/GHSA-7gcm-g887-7qv7)
- [CVE-2026-0994](https://nvd.nist.gov/vuln/detail/CVE-2026-0994)
- [Dependabot Alerts](https://github.com/Remaker-Digital/AGNTCY-muti-agent-deployment-customer-service/security/dependabot)

## Review Schedule

- **Next Review:** 2026-02-03 (1 week)
- **Action:** Check if patched version is available
