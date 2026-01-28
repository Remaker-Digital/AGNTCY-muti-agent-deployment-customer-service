# OWASP ZAP Active Security Scan Summary

**Date:** 2026-01-28
**Target:** https://agntcy-cs-prod-rc6vcp.eastus2.cloudapp.azure.com
**Scanner:** OWASP ZAP (ghcr.io/zaproxy/zaproxy:stable Docker image)
**Scan Type:** Full Active Scan (zap-full-scan.py)

## Summary

| Result | Count |
|--------|-------|
| **PASS** | 139 |
| **WARN-NEW** | 3 |
| **FAIL-NEW** | 0 |
| **FAIL-INPROG** | 0 |

**Overall Status:** ✅ PASSED (0 failures, 3 low-severity warnings)

## Comparison to Baseline Scan

| Metric | Baseline (2026-01-27) | Active (2026-01-28) |
|--------|----------------------|---------------------|
| Tests Passed | 62 | 139 |
| Warnings | 4 | 3 |
| Failures | 0 | 0 |
| Scan Type | Passive | Full Active |

### Previously Fixed (No Longer Warning)
- ✅ **HSTS Header** - Now set via Application Gateway rewrite rules
- ✅ **Server Header** - Removed via rewrite rules
- ✅ **CSP Header** - Not flagged in active scan (API-only endpoint)
- ✅ **Permissions Policy** - Not flagged in active scan (API-only endpoint)

## New Warnings (Low Severity)

### 1. Proxy Disclosure [40025]
**Severity:** Low
**Affected URLs:** 4
**Description:** Detection of proxy servers in the response chain.
**Details:** Azure Application Gateway is a legitimate proxy; this is expected behavior.
**Risk:** None - This is the intended architecture (AppGW as reverse proxy).
**Action:** Accept risk - This is by design for load balancing and TLS termination.

### 2. CORS Misconfiguration [40040]
**Severity:** Low
**Affected URLs:** 4
**Description:** Cross-Origin Resource Sharing (CORS) headers detected.
**Details:** API endpoints return CORS headers for cross-origin requests.
**Risk:** Low - CORS is configured for API access; only trusted origins should be allowed.
**Action:** Verify CORS configuration limits origins appropriately for production.
**Recommendation:** Configure specific allowed origins instead of `*` if currently using wildcard.

### 3. Insufficient Site Isolation Against Spectre Vulnerability [90004]
**Severity:** Low
**Affected URLs:** 2
**Description:** Missing `Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy` headers.
**Details:** These headers provide additional isolation against Spectre-class vulnerabilities.
**Risk:** Low - Primarily affects browser-based applications with sensitive data processing.
**Action:** Consider adding headers for defense in depth.
**Recommendation:** Add to Application Gateway rewrite rules:
```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

## Major Security Tests Passed (139 Total)

### Critical Vulnerability Tests ✅
- Remote Code Execution - Shell Shock [10048] ✅ PASS
- Log4Shell [40043] ✅ PASS
- Spring4Shell [40045] ✅ PASS
- Text4shell (CVE-2022-42889) [40047] ✅ PASS
- Remote Code Execution (React2Shell) [40048] ✅ PASS
- Remote OS Command Injection [90020] ✅ PASS

### Injection Tests ✅
- SQL Injection [40018] ✅ PASS
- SQL Injection - MySQL (Time Based) [40019] ✅ PASS
- SQL Injection - PostgreSQL (Time Based) [40022] ✅ PASS
- SQL Injection - MsSQL (Time Based) [40027] ✅ PASS
- NoSQL Injection - MongoDB [40033] ✅ PASS
- XPath Injection [90021] ✅ PASS
- XML External Entity Attack [90023] ✅ PASS
- Expression Language Injection [90025] ✅ PASS
- XSLT Injection [90017] ✅ PASS
- Server Side Template Injection [90035] ✅ PASS
- SOAP XML Injection [90029] ✅ PASS
- CRLF Injection [40003] ✅ PASS

### Cross-Site Scripting Tests ✅
- Cross Site Scripting (Reflected) [40012] ✅ PASS
- Cross Site Scripting (Persistent) [40014] ✅ PASS
- Cross Site Scripting (DOM Based) [40026] ✅ PASS
- Out of Band XSS [40031] ✅ PASS

### Authentication & Session Tests ✅
- Weak Authentication Method [10105] ✅ PASS
- Session Fixation [40013] ✅ PASS
- Session ID in URL Rewrite [3] ✅ PASS
- Absence of Anti-CSRF Tokens [10202] ✅ PASS

### Information Disclosure Tests ✅
- Source Code Disclosure [10099] ✅ PASS
- Source Code Disclosure - Git [41] ✅ PASS
- Source Code Disclosure - SVN [42] ✅ PASS
- .env Information Leak [40034] ✅ PASS
- .htaccess Information Leak [40032] ✅ PASS
- Private IP Disclosure [2] ✅ PASS
- Cloud Metadata Potentially Exposed [90034] ✅ PASS
- PII Disclosure [10062] ✅ PASS
- Heartbleed OpenSSL Vulnerability [20015] ✅ PASS

### Server-Side Tests ✅
- Server Side Request Forgery [40046] ✅ PASS
- Server Side Code Injection [90019] ✅ PASS
- Path Traversal [6] ✅ PASS
- Remote File Inclusion [7] ✅ PASS
- Buffer Overflow [30001] ✅ PASS
- Integer Overflow Error [30003] ✅ PASS
- Format String Error [30002] ✅ PASS

## Remediation Plan

| Issue | Priority | Effort | Action |
|-------|----------|--------|--------|
| Proxy Disclosure | Informational | N/A | Accept risk - intended architecture |
| CORS Config | Low | 30 min | Verify allowed origins list |
| Spectre Isolation | Low | 30 min | Add COOP/COEP headers (optional) |

## Reports Generated

- `security-scans/zap-active-report.html` - Full HTML report
- `security-scans/zap-active-report.json` - Machine-readable JSON report

## Conclusion

The full OWASP ZAP active security scan **passed with 0 failures and 139 passed tests**. The 3 low-severity warnings are:

1. **Proxy Disclosure** - Expected behavior (Azure Application Gateway)
2. **CORS Misconfiguration** - Review allowed origins for production
3. **Spectre Isolation** - Optional additional headers for defense in depth

### Security Posture Assessment

| Category | Status |
|----------|--------|
| **Critical Vulnerabilities** | ✅ None detected |
| **High Severity** | ✅ None detected |
| **Medium Severity** | ✅ None detected |
| **Low Severity** | ⚠️ 3 (acceptable for production) |
| **Injection Attacks** | ✅ Protected |
| **XSS Attacks** | ✅ Protected |
| **RCE Attacks** | ✅ Protected |
| **Information Disclosure** | ✅ Protected |

**Recommendation:** Proceed with production deployment. The 3 low-severity warnings do not block go-live.

---

**Scanned By:** OWASP ZAP Full Active Scan (Docker)
**Report Generated:** 2026-01-28
**Scan Duration:** ~8 minutes
