# Build: docker build -t meta-env:latest .
# Run:   docker run -p 7860:7860 meta-env:latest

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer cache)
COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else
COPY . .

# PYTHONPATH = /app so "from server.xxx" and "from models" both work
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${PORT}"]