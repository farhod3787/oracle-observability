FROM python:3.12-slim

WORKDIR /app

# Install minimal build and networking tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter/ ./exporter/

EXPOSE 9161

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:9161/metrics || exit 1

CMD ["python", "-m", "exporter.main"]
