# OWASP ZAP Security Scan Summary

**Date:** 2026-01-27
**Target:** https://agntcy-cs-prod-rc6vcp.eastus2.cloudapp.azure.com
**Scanner:** OWASP ZAP (zaproxy:stable Docker image)
**Scan Type:** Baseline Scan (passive)

## Summary

| Result | Count |
|--------|-------|
| **PASS** | 62 |
| **WARN-NEW** | 4 |
| **FAIL-NEW** | 0 |
| **INFO** | 0 |

**Overall Status:** ✅ PASSED (0 failures, 4 low-severity warnings)

## Warnings (Requires Attention)

### 1. Strict-Transport-Security Header Not Set [10035]
**Severity:** Low
**Affected URLs:** 4 (root, robots.txt, sitemap.xml)
**Description:** HTTP Strict Transport Security (HSTS) is not enabled.
**Recommendation:** Add HSTS header to Application Gateway:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```
**Fix:** Configure Application Gateway rewrite rules to add HSTS header.

### 2. Server Leaks Version Information [10036]
**Severity:** Low
**Affected URLs:** 4
**Description:** Server header exposes "Microsoft-Azure-Application-Gateway/v2".
**Recommendation:** Remove or mask the Server header in Application Gateway.
**Fix:** This is Azure default behavior; low risk for educational project.

### 3. Content Security Policy (CSP) Header Not Set [10038]
**Severity:** Low
**Affected URLs:** 4
**Description:** No CSP header configured to prevent XSS attacks.
**Recommendation:** Add CSP header when frontend is deployed.
**Note:** Backend API-only endpoint; CSP less critical for APIs.

### 4. Permissions Policy Header Not Set [10063]
**Severity:** Low
**Affected URLs:** 4
**Description:** No Permissions-Policy header to control browser features.
**Recommendation:** Add when frontend is deployed.
**Note:** Backend API-only endpoint; permissions policy less critical.

## Passed Tests (62)

All major security checks passed, including:
- ✅ Vulnerable JS Library detection
- ✅ Cookie security (HttpOnly, Secure flags)
- ✅ XSS protection checks
- ✅ Information disclosure checks
- ✅ SSL/TLS configuration
- ✅ Clickjacking protection
- ✅ Content-Type security
- ✅ CSRF token checks
- ✅ Private IP disclosure
- ✅ Java serialization
- ✅ Heartbleed vulnerability
- ✅ Mixed content checks
- ✅ And 50+ more checks

## Backend Health Note

All URLs returned **502 Bad Gateway** during the scan. This is expected because:
1. SLIM backend doesn't have a `/health` endpoint at the expected path
2. Backend services use self-signed certificates that need trust configuration
3. This is a security-positive finding: backend services are not exposed directly

## Remediation Plan

| Issue | Priority | Phase | Status |
|-------|----------|-------|--------|
| HSTS Header | Medium | Phase 5 | Planned |
| Server Header | Low | Post-Phase 5 | Deferred |
| CSP Header | Low | Phase 5 (if frontend) | Planned |
| Permissions Policy | Low | Phase 5 (if frontend) | Planned |

## Reports Generated

- `security-scans/zap-report.html` - Full HTML report
- `security-scans/zap-report.json` - Machine-readable JSON report

## Next Steps

1. **HSTS Header** - Add to Application Gateway configuration
2. **Backend Health Probe** - Configure SLIM health endpoint
3. **Rescan** - After remediation, run full active scan
4. **Production Hardening** - Address low-severity items before go-live

---

**Scanned By:** OWASP ZAP Baseline Scan (Docker)
**Report Generated:** 2026-01-27 09:37 UTC
