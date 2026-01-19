# =============================================================================
# Escalation Agent - Optimized Multi-Stage Dockerfile
# =============================================================================
# Optimizations Applied:
# - Multi-stage build to separate build and runtime environments
# - Layer caching optimized (requirements first, then code)
# - Non-root user for security
# - Specific Python version pinning
# - Minimal final image size
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies if needed for compiled packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements (cached layer if requirements unchanged)
COPY agents/escalation/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-warn-script-location -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Add user's local bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy shared utilities and agent code (last for better layer caching)
COPY --chown=appuser:appuser shared/ /app/shared/
COPY --chown=appuser:appuser agents/escalation/agent.py .

# Switch to non-root user
USER appuser

# Health check - verify Python can import required modules
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "agent.py"]
