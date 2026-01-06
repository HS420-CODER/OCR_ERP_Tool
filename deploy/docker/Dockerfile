# ==============================================================================
# ERP Arabic OCR Microservice - Docker Image
# ==============================================================================
#
# Multi-stage build for optimized production image.
#
# Build:
#   docker build -t erp-ocr-service:latest -f deploy/docker/Dockerfile .
#
# Run:
#   docker run -p 8000:8000 erp-ocr-service:latest
#
# Build with specific Python version:
#   docker build --build-arg PYTHON_VERSION=3.10 -t erp-ocr-service:latest .
#
# ==============================================================================

# Build arguments
ARG PYTHON_VERSION=3.10

# ==============================================================================
# Stage 1: Builder (install dependencies)
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim as builder

# Prevent Python from writing bytecode and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements-microservice.txt /tmp/requirements.txt
RUN pip install --upgrade pip wheel setuptools && \
    pip install -r /tmp/requirements.txt

# ==============================================================================
# Stage 2: Production Image
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim as production

# Labels
LABEL maintainer="ERP Team <admin@erp.local>" \
      version="2.0.0" \
      description="ERP Arabic OCR Microservice with PaddleOCR and EasyOCR"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    # Application settings
    FLASK_ENV=production \
    FLASK_APP=wsgi:app \
    # PaddleOCR settings
    DISABLE_MODEL_SOURCE_CHECK=True \
    PADDLEPADDLE_PNGFILE=off \
    # Gunicorn settings
    GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=2 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_BIND=0.0.0.0:8000 \
    # Application paths
    APP_HOME=/app \
    UPLOAD_DIR=/app/uploads \
    MODEL_DIR=/app/models

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Image processing
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    # PDF processing
    poppler-utils \
    # Tesseract OCR (fallback)
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    # File type detection
    libmagic1 \
    # Arabic fonts (critical for OCR accuracy)
    fonts-noto-core \
    fonts-noto-extra \
    fonts-noto-color-emoji \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    fonts-hosny-amiri \
    fonts-kacst \
    fonts-kacst-one \
    # Utilities
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create application directories
WORKDIR /app
RUN mkdir -p ${UPLOAD_DIR} ${MODEL_DIR} /var/log/ocr-service && \
    chown -R appuser:appuser /app /var/log/ocr-service

# Copy application code
COPY --chown=appuser:appuser . /app

# Pre-download OCR models (optional - makes container larger but faster startup)
# Uncomment to include models in image:
# RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='ar', use_gpu=False)"
# RUN python -c "import easyocr; easyocr.Reader(['ar', 'en'], gpu=False)"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v2/ocr/health || exit 1

# Default command
CMD ["gunicorn", \
     "--config", "config/gunicorn.conf.py", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "wsgi:app"]

# ==============================================================================
# Alternative: Development Image
# ==============================================================================
FROM production as development

# Switch to root for additional installs
USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install development dependencies
RUN pip install pytest pytest-cov black flake8 mypy

# Switch back to appuser
USER appuser

# Development command (with reload)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--threads", "1", \
     "--reload", \
     "--access-logfile", "-", \
     "wsgi:app"]

# ==============================================================================
# Build Notes:
# ==============================================================================
#
# Image size optimization:
# - Base slim image: ~150MB
# - With OCR dependencies: ~1.5GB
# - With pre-downloaded models: ~3GB
#
# Memory requirements:
# - Minimum: 2GB RAM
# - Recommended: 4GB RAM
# - With GPU: 8GB RAM + 4GB VRAM
#
# GPU Support (NVIDIA):
# - Use nvidia/cuda base image
# - Install paddlepaddle-gpu
# - Run with: docker run --gpus all ...
#
# ==============================================================================
