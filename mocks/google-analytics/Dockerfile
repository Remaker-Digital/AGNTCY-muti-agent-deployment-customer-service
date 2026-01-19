# =============================================================================
# Mock Google Analytics API - Optimized Multi-Stage Dockerfile
# =============================================================================
# Optimizations Applied:
# - Multi-stage build to separate build and runtime environments
# - Layer caching optimized (requirements first, then code)
# - Non-root user for security
# - Specific Python version pinning
# - Minimal final image size with proper health check
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies for compiled packages (uvloop, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements (cached layer if requirements unchanged)
COPY mocks/google-analytics/requirements.txt .
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

# Create data directory (populated by volume mount)
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Copy application code (last for better layer caching)
COPY --chown=appuser:appuser mocks/google-analytics/app.py .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check - verify FastAPI is responding
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
