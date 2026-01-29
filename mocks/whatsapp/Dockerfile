# ============================================================================
# Mock WhatsApp Business Cloud API - Dockerfile
# ============================================================================
# Purpose: Container for mock WhatsApp API service
#
# Usage:
#     docker build -t mock-whatsapp .
#     docker run -p 8011:8011 mock-whatsapp
#
# Or via Docker Compose (recommended):
#     docker-compose up mock-whatsapp
# ============================================================================

FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Expose port
EXPOSE 8011

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8011"]
