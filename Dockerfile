# syntax=docker/dockerfile:1

# ==============================================================================
# Multi-stage Dockerfile for Digital Actors
# ==============================================================================
# Stage 1: Builder - Install dependencies and prepare environment
# Stage 2: Production - Minimal runtime image
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies in a virtual environment
# Using uv for faster dependency resolution and installation
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -e .

# ------------------------------------------------------------------------------
# Stage 2: Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies (minimal)
# - ca-certificates: For HTTPS connections to APIs
# - curl: For health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8888

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/voicecache /app/audio && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose WebSocket server port (default: 8888)
EXPOSE 8888

# Health check
# Check if the web server is responding on the health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8888}/health || exit 1

# Default command: Run the web server
CMD ["python", "web_server.py"]
