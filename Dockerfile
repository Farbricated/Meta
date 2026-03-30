# Root Dockerfile for HF Spaces deployment
# Repo structure: Meta/ (root) -> Meta/Meta/ (package) -> Meta/Meta/server/ (app)
#
# Build: docker build -t meta-env:latest .
# Run:   docker run -p 7860:7860 meta-env:latest

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy inner package requirements first (layer cache)
COPY Meta/server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Meta package
COPY Meta/ ./Meta/

# Set Python path so imports resolve correctly
ENV PYTHONPATH=/app/Meta
ENV PYTHONUNBUFFERED=1

# HF Spaces uses port 7860
ENV PORT=7860
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start the server
CMD ["sh", "-c", "cd /app/Meta && uvicorn server.app:app --host 0.0.0.0 --port ${PORT}"]
