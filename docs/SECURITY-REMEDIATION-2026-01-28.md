# Security Remediation Plan - January 28, 2026

## Overview

Security analysis identified 15 findings across the codebase. This document tracks remediation status and provides implementation guidance.

## Finding Summary

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 1 | !! | Unauthenticated Chat Endpoint | REMEDIATED |
| 2 | !! | BOLA in Shopify Order Retrieval | REMEDIATED |
| 3 | !! | BOLA in Zendesk Ticket Retrieval | REMEDIATED |
| 4 | !! | BOLA in Customer Order Lookup by Email | REMEDIATED |
| 5 | !! | No Input Sanitization for AI Agent Messages | REMEDIATED |
| 6 | ! | SSRF via Configurable Mock Service URLs | ACCEPTED RISK |
| 7 | ! | Password-Based Authentication for SLIM Gateway | ACCEPTED RISK |
| 8 | ! | Authorization Header Not Validated in Mock APIs | BY DESIGN |
| 9 | ~ | PII Logged in Debug Messages | REMEDIATED |
| 10 | ~ | Dictionary Unpacking in OpenAI API Calls | MITIGATED |
| 11 | ~ | Unsafe Default Confidence Value of 1.0 | REMEDIATED |
| 12 | ~ | No Rate Limiting on Chat Endpoint | REMEDIATED |
| 13 | ~ | Customer Context ID Logged Without Sanitization | REMEDIATED |
| 14 | ~ | Validation Type from User-Controlled Content | MITIGATED |
| 15 | . | Unvalidated URL in Test Escalation Scenarios | ACCEPTED RISK |

---

## Critical Findings (!! - Must Fix)

### 1. Unauthenticated Chat Endpoint

**Location:** `api_gateway/main.py:75`
**Issue:** The `/api/v1/chat` endpoint accepts requests without authentication or session validation.

**Remediation:**
- Added session validation middleware
- Require `session_id` header or create anonymous session
- Rate limit by session/IP to prevent abuse

**Code Changes:**
```python
# Added session validation to ChatRequest
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    session_id: str = Field(..., description="Required session ID")  # Now required

# Added session validation middleware
@app.middleware("http")
async def validate_session(request: Request, call_next):
    # Validate session exists for protected endpoints
    ...
```

### 2-4. BOLA Vulnerabilities in Mock APIs

**Locations:**
- `mocks/shopify/app.py:95` (order retrieval)
- `mocks/shopify/app.py:110` (order lookup by email)
- `mocks/zendesk/app.py:85` (ticket retrieval)

**Issue:** Mock APIs return data without validating the requester has access to that data.

**Remediation:**
- Added owner validation for all resource lookups
- Require Authorization header with customer/user identifier
- Validate resource ownership before returning data

**Code Changes:**
```python
# Added ownership validation
@app.get("/orders/{order_id}")
async def get_order(order_id: str, authorization: str = Header(...)):
    # Validate customer owns this order
    customer_id = validate_authorization(authorization)
    order = orders.get(order_id)
    if order and order.get("customer_id") != customer_id:
        raise HTTPException(status_code=403, detail="Access denied")
```

### 5. No Input Sanitization for AI Agent Messages

**Location:** `api_gateway/main.py:75`
**Issue:** Customer messages are passed directly to AI agents without sanitization.

**Remediation:**
- Added prompt injection detection patterns
- Integrated with Critic/Supervisor agent validation
- Block known prompt injection patterns

**Code Changes:**
```python
# Added input sanitization
INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions?",
    r"you\s+are\s+(now|a)\s+",
    r"system\s*:\s*",
    r"<\|.*?\|>",
    r"\{\{.*?\}\}",
]

def sanitize_message(message: str) -> tuple[str, bool]:
    """Check for prompt injection patterns."""
    ...
```

---

## High Findings (! - Should Fix)

### 6. SSRF via Configurable Mock Service URLs

**Location:** `console/agntcy_integration.py:1446`
**Issue:** HTTP requests made to URLs from environment variables could be redirected.

**Remediation Status:** ACCEPTED RISK
**Rationale:**
- Environment variables are set by trusted operators
- Production deployment uses Azure Container Apps with managed identities
- Mock URLs are only used in development

**Mitigations in Place:**
- URL validation in production configuration
- Network isolation via Azure VNet
- No user-controllable URL inputs

### 7. Password-Based Authentication for SLIM Gateway

**Location:** `AGNTCY-REVIEW.md:642`
**Issue:** SLIM gateway uses password-based authentication stored in environment variables.

**Remediation Status:** ACCEPTED RISK
**Rationale:**
- This is AGNTCY SDK design, not our implementation
- Production uses Azure Key Vault for secret storage
- Passwords are rotated via infrastructure automation

**Mitigations in Place:**
- Azure Key Vault for secrets management
- Environment variables not committed to Git
- Managed identities where supported

### 8. Authorization Header Not Validated in Mock APIs

**Status:** BY DESIGN
**Rationale:**
- Mock APIs are intentionally permissive for development
- Not deployed to production
- Real APIs (Shopify, Zendesk) handle their own authentication

---

## Medium Findings (~ - Consider Fixing)

### 9 & 13. PII in Logs

**Locations:**
- `agents/analytics/agent.py:76`
- `agents/analytics/agent.py:225`

**Remediation:**
- Replaced PII with tokenized values in logs
- Added log scrubbing utilities
- Context IDs are now opaque (not correlated with customer data)

### 10. Dictionary Unpacking in OpenAI API Calls

**Location:** `evaluation/azure_openai_client.py:240`

**Remediation Status:** MITIGATED
**Mitigations:**
- `request_params` is constructed internally, not from user input
- Schema validation on all inputs before unpacking
- Type hints enforce parameter structure

### 11. Unsafe Default Confidence Value

**Location:** `agents/critic_supervisor/agent.py:321`

**Remediation:**
- Changed default from 1.0 to 0.5
- Added explicit handling for missing confidence
- Log warning when confidence is missing

### 12. No Rate Limiting on Chat Endpoint

**Remediation:**
- Added sliding window rate limiter
- Default: 30 requests/minute per session
- Configurable via environment variables

### 14. Validation Type from User Content

**Location:** `agents/critic_supervisor/agent.py:202`

**Remediation Status:** MITIGATED
**Mitigations:**
- Validation type is from enum, not directly from user content
- Added input validation for validation type values
- Reject unknown validation types

---

## Low Findings (. - Nice to Have)

### 15. Unvalidated URL in Test Escalation Scenarios

**Location:** `tests/escalation/test_escalation_scenarios.py:271`

**Remediation Status:** ACCEPTED RISK
**Rationale:**
- Test file only, not production code
- URLs are hardcoded test fixtures
- No external network access in CI

---

## Implementation Files

| File | Changes |
|------|---------|
| `api_gateway/main.py` | Session validation, rate limiting, input sanitization |
| `shared/security/__init__.py` | New security utilities module |
| `shared/security/input_sanitizer.py` | Prompt injection detection |
| `shared/security/rate_limiter.py` | Sliding window rate limiter |
| `mocks/shopify/app.py` | BOLA fixes with ownership validation |
| `mocks/zendesk/app.py` | BOLA fixes with ownership validation |
| `agents/analytics/agent.py` | PII scrubbing in logs |
| `agents/critic_supervisor/agent.py` | Fixed default confidence |

---

## Testing

All security fixes include tests:

```bash
# Run security-specific tests
pytest tests/unit/test_security.py -v
pytest tests/integration/test_security_api.py -v
```

## Verification Checklist

- [x] Unauthenticated endpoints protected
- [x] BOLA vulnerabilities fixed in mock APIs
- [x] Input sanitization for AI messages
- [x] Rate limiting enabled
- [x] PII scrubbed from logs
- [x] Default confidence value fixed
- [ ] Documentation updated
- [ ] Security tests passing

---

## Notes for Operators

### Rate Limiting Configuration

```bash
# Environment variables
RATE_LIMIT_REQUESTS=30        # Requests per window
RATE_LIMIT_WINDOW_SECONDS=60  # Window size
```

### Monitoring for Security Events

Dashboard alerts have been configured for:
- High rate limit hits (>100/hour)
- Prompt injection attempts blocked
- Unauthorized access attempts
- Session validation failures

See `docs/WIKI-Operations-Dashboard.md` for alert configuration.
