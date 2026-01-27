# Load Test Prerequisites

**Date:** 2026-01-27
**Target:** https://agntcy-cs-prod-rc6vcp.eastus2.cloudapp.azure.com

## Current Status

The Application Gateway is deployed and accepting connections, but backend services are not yet reachable through the gateway.

**Current Response:** 502 Bad Gateway

## Prerequisites for Load Testing

### 1. Backend Health Probe Configuration

The SLIM gateway (10.0.1.4:8443) needs to respond to health probes. Options:

a) **Add health endpoint to SLIM** - Create `/health` endpoint in SLIM configuration
b) **Adjust health probe** - Change probe path to match SLIM's available endpoints
c) **Trusted root certificate** - Configure Application Gateway to trust SLIM's self-signed certificate

### 2. NSG Rules Verification

Ensure NSG allows traffic from Application Gateway subnet (10.0.3.0/24) to container subnet (10.0.1.0/24):
- Port 8443 (SLIM)
- Port 8080 (Agent containers)

### 3. Backend Certificate Trust

Application Gateway needs to trust the backend certificate. Options:
- Add SLIM's root certificate as trusted_root_certificate
- Or disable backend certificate verification (not recommended for production)

## Recommended Approach

1. **Create SLIM health endpoint** - Update SLIM configuration to expose `/health`
2. **Update Application Gateway backend settings** - Add proper health probe configuration
3. **Add trusted root certificate** - For SLIM's self-signed cert
4. **Run Locust load test** against the public endpoint

## Alternative: Direct Container Testing

While gateway configuration is being fixed, load test can run against:
- Container private IPs (requires VPN or jump box)
- Local Docker environment with `docker-compose up`

## Load Test Configuration (When Ready)

```bash
# Target: 100 concurrent users, 1000 requests/minute
locust -f tests/load/locustfile.py \
  --host https://agntcy-cs-prod-rc6vcp.eastus2.cloudapp.azure.com \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 300s
```

## Expected Results

| Metric | Target | Phase 5 Requirement |
|--------|--------|---------------------|
| Concurrent Users | 100 | ≥100 |
| Throughput | 1000 req/min | ≥1000 req/min |
| P95 Response Time | <2000ms | <2 minutes |
| Error Rate | <1% | <1% |

## Next Steps

1. Fix Application Gateway → SLIM connectivity
2. Re-run OWASP ZAP scan (after backend responds)
3. Execute full Locust load test
4. Document results in load-test-results-{date}.md

---

**Status:** Blocked on Application Gateway backend configuration
**Next Action:** Configure SLIM health endpoint or adjust gateway health probe
