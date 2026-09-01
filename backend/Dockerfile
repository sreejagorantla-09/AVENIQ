# Multi-stage Python 3.12 Dockerfile for AVENIQ Backend on Google Cloud Run

# Stage 1: Build dependencies
FROM python:3.12-slim as builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# Stage 2: Runtime image
FROM python:3.12-slim as runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Create non-root system user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder stage
COPY --from=builder /install /install
COPY . .

# Change ownership to non-root appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose default Cloud Run port
EXPOSE 8000

# Entrypoint runner for production container
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
