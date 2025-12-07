FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for DuckDB spatial extension
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install DuckDB extensions during build (faster cold starts)
RUN python -c "import duckdb; conn = duckdb.connect(); conn.execute('INSTALL httpfs'); conn.execute('INSTALL spatial'); conn.close()"

# Copy application code
COPY api/ ./api/
COPY static/ ./static/

# Create non-root user for security
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api')" || exit 1

# Run with uvicorn - single worker for serverless (container scaling handles concurrency)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
