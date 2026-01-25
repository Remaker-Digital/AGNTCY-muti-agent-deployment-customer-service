# AGNTCY Development Console
# Multi-stage build for optimized production image

# Stage 1: Base Python environment
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash console
USER console
WORKDIR /home/console

# Stage 2: Dependencies
FROM base as dependencies

# Copy requirements and install Python dependencies
COPY --chown=console:console console/requirements.txt ./
RUN pip install --user -r requirements.txt

# Stage 3: Application
FROM base as application

# Copy installed packages from dependencies stage
COPY --from=dependencies /home/console/.local /home/console/.local

# Add local bin to PATH
ENV PATH=/home/console/.local/bin:$PATH

# Copy application code
COPY --chown=console:console console/ ./console/
COPY --chown=console:console shared/ ./shared/
COPY --chown=console:console agents/ ./agents/
COPY --chown=console:console mocks/ ./mocks/

# Create necessary directories
RUN mkdir -p logs data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

# Expose port
EXPOSE 8080

# Default command
CMD ["streamlit", "run", "console/app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]