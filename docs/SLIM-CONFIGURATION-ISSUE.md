# SLIM Configuration Issue - January 24-25, 2026

## Issue Summary

**Status**: **RESOLVED** - SLIM service now running correctly
**Resolution Date**: January 25, 2026
**Impact**: None - SLIM is fully operational
**Severity**: N/A (resolved)

---

## Problem Description (Historical)

The SLIM Docker container (ghcr.io/agntcy/slim:0.6.1) initially failed to start with configuration errors.

### Error Messages (Historical)

**First Error:**
```
thread 'main' panicked at core/slim/src/bin/main.rs:27:55:
failed to load configuration: InvalidKey("server")
```

**Second Error (after partial fix):**
```
thread 'main' panicked at core/slim/src/bin/main.rs:54:37:
failed to start service: RuntimeError("configuration error failed to run server: error parsing grpc endpoint")
```

### Root Causes

**Issue 1: Invalid Configuration Schema**
The original configuration file used an incorrect top-level key structure:
```yaml
# INCORRECT - SLIM v0.6.1 does not recognize "server" key
server:
  host: 0.0.0.0
  port: 46357
  gateway:
    enabled: true
    password: ${SLIM_GATEWAY_PASSWORD}
```

**Issue 2: Incorrect Endpoint Format**
The endpoint was specified with HTTP scheme, but SLIM expects just host:port:
```yaml
# INCORRECT - includes "http://" scheme
endpoint: "http://0.0.0.0:46357"

# CORRECT - just host:port
endpoint: "0.0.0.0:46357"
```

---

## Resolution

### Correct SLIM Configuration (v0.6.1)

**File**: `config/slim/server-config.yaml`

```yaml
# SLIM Server Configuration for AGNTCY Multi-Agent Platform
# This configuration sets up the SLIM messaging backbone for agent communication
#
# SLIM (Secure Low-Latency Interactive Messaging) v0.6.1
# Used in Phase 1-3 for local development
#
# Reference: https://docs.agntcy.org/slim/slim-data-plane-config/

# Tracing and logging configuration
tracing:
  log_level: info
  display_thread_names: true
  display_thread_ids: true

# Runtime configuration
runtime:
  n_cores: 0  # 0 = auto-detect available cores
  thread_name: "slim-data-plane"
  drain_timeout: 10s

# Service configuration
services:
  # Main SLIM service instance
  slim/1:
    dataplane:
      # Server endpoints this SLIM instance exposes
      servers:
        - endpoint: "0.0.0.0:46357"
          tls:
            insecure: true  # Disable TLS for local development (enable in Phase 4-5)
      # Client connections (none needed for standalone mode)
      clients: []
    # Controller configuration (optional - for multi-node setups)
    # controller:
    #   servers: []
    #   clients:
    #     - endpoint: "slim-controller:50052"
    #       tls:
    #         insecure: true
```

### Key Configuration Points

| Setting | Value | Purpose |
|---------|-------|---------|
| `tracing.log_level` | `info` | Log verbosity (debug, info, warn, error) |
| `runtime.n_cores` | `0` | Auto-detect CPU cores |
| `services.slim/1.dataplane.servers[0].endpoint` | `"0.0.0.0:46357"` | **Host:port only, no scheme** |
| `services.slim/1.dataplane.servers[0].tls.insecure` | `true` | Disable TLS for local dev |

### Docker Compose Configuration

**File**: `docker-compose.yml`

```yaml
slim:
  image: ghcr.io/agntcy/slim:0.6.1
  container_name: agntcy-slim
  ports:
    - "46357:46357"
  networks:
    - agntcy-network
  volumes:
    - ./config/slim/server-config.yaml:/config.yaml:ro
  environment:
    - SLIM_GATEWAY_PASSWORD=${SLIM_GATEWAY_PASSWORD:-changeme_local_dev_password}
  command: ["/slim", "--config", "/config.yaml"]
  restart: unless-stopped
  depends_on:
    - nats
```

---

## Verification

### SLIM Running Successfully

```bash
$ docker logs agntcy-slim --tail 10
INFO application_lifecycle: slim: Runtime started
INFO application_lifecycle: slim: Starting service: slim/1
INFO application_lifecycle: slim_service::service: starting service
INFO application_lifecycle: slim_service::service: starting server 0.0.0.0:46357
INFO application_lifecycle: slim_service::service: server configured: setting it up
INFO application_lifecycle: slim_controller::service: starting controller service
INFO slim-data-plane slim_config::grpc::server: running service
```

### Container Status

```bash
$ docker inspect agntcy-slim --format '{{.State.Status}} {{.State.Running}} {{.RestartCount}}'
running true 0
```

---

## Lessons Learned

### 1. SLIM Configuration Schema (v0.6.1)

SLIM uses a hierarchical configuration with three top-level keys:
- `tracing`: Logging and trace configuration
- `runtime`: Thread pool and drain settings
- `services`: Service definitions with dataplane/controller config

**Do NOT use:**
- `server:` - Not a valid top-level key
- `transport:` - Not part of SLIM config
- `observability:` - Use `tracing:` instead

### 2. Endpoint Format

SLIM endpoints must be specified as `host:port` without URL scheme:
- **Correct**: `"0.0.0.0:46357"`
- **Incorrect**: `"http://0.0.0.0:46357"`

### 3. Documentation Reference

Official SLIM configuration documentation:
- https://docs.agntcy.org/slim/slim-data-plane-config/
- https://docs.agntcy.org/slim/slim-howto/

---

## Current Status

### All Services Operational

| Service | Status | Port | Notes |
|---------|--------|------|-------|
| SLIM | **Running** | 46357 | Resolved |
| NATS | Running | 4222 | No issues |
| ClickHouse | Running | 8123 | No issues |
| OTel Collector | Running | 4318 | No issues |
| Grafana | Running | 3001 | No issues |
| Console | Running | 8080 | No issues |

### Agent Communication

With SLIM now operational:
- A2A protocol communication works
- MCP protocol communication works
- Topic-based routing functional
- All 5 agents can communicate via SLIM transport

---

## Historical Context

### Timeline

| Date | Event |
|------|-------|
| 2026-01-24 | Issue discovered - SLIM failing with `InvalidKey("server")` |
| 2026-01-24 | Initial workaround: Console operates in simulation mode |
| 2026-01-25 | Root cause identified: Incorrect YAML schema |
| 2026-01-25 | Fix applied: Updated configuration to correct format |
| 2026-01-25 | Second fix: Removed `http://` from endpoint |
| 2026-01-25 | **RESOLVED**: SLIM running successfully |

### Impact Assessment (Historical)

The issue only affected development from 2026-01-24 to 2026-01-25. During this time:
- Console operated in simulation mode (acceptable for Phase 1-3)
- No data loss or service disruption
- All other services continued operating normally

---

## References

- [SLIM Data Plane Configuration](https://docs.agntcy.org/slim/slim-data-plane-config/)
- [SLIM Getting Started](https://docs.agntcy.org/slim/slim-howto/)
- [AGNTCY SLIM GitHub](https://github.com/agntcy/slim)

---

**Document Created**: 2026-01-24
**Document Updated**: 2026-01-25
**Author**: Development Team
**Status**: **RESOLVED**
**Phase Impact**: None (resolved before Phase 4)
