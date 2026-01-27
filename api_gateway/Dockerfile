# API Gateway Dockerfile
# Provides HTTP REST API for Application Gateway integration
#
# Build: docker build -t api-gateway:latest -f api_gateway/Dockerfile .
# Run: docker run -p 8080:8080 api-gateway:latest

FROM python:3.12-slim

# Metadata
LABEL maintainer="AGNTCY Project"
LABEL version="1.0.0"
LABEL description="HTTP REST API Gateway for multi-agent customer service"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional API gateway dependencies
# Note: openai package required for Azure OpenAI integration
RUN pip install --no-cache-dir \
    fastapi>=0.109.0 \
    uvicorn[standard]>=0.27.0 \
    pydantic>=2.5.0 \
    openai>=1.12.0

# Copy application code
# Note: We need the full evaluation module for Azure OpenAI integration
# The console/azure_openai_mode.py imports from evaluation.azure_openai_client
COPY api_gateway/ ./api_gateway/
COPY console/ ./console/
COPY shared/ ./shared/
COPY evaluation/ ./evaluation/

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Run the API server
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
