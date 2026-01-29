# ============================================================================
# Mock Shopify Customer Accounts API - Dockerfile
# ============================================================================
# Purpose: Container for mock Shopify Customer Accounts API service
#
# Port: 8010
# Health check: GET /health
#
# Test credentials:
# - test@example.com / test123
# - vip@example.com / vip456
# ============================================================================

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create data directory for fixtures
RUN mkdir -p /app/data

# Expose port
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010"]
