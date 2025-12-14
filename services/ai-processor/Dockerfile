# Attention Detection AI Processor
# Multi-stage build for optimized image size

# Stage 1: Base image with CUDA support
FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04 AS base

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-venv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Stage 2: Dependencies
FROM base AS dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Stage 3: Application
FROM dependencies AS app

# Copy application code
COPY src/ ./src/
COPY demo.py .
COPY .env.example .env

# Create models directory
RUN mkdir -p models

# Download model (optional - can mount from host)
# RUN wget -O models/yolov8n-face.pt https://github.com/akanametov/yolov8-face/releases/download/v0.0.0/yolov8n-face.pt

# Set environment variables
ENV ATTENTION_FACE_DETECTION__DEVICE=cuda
ENV ATTENTION_LOG_LEVEL=INFO

# Expose port for gRPC
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "from src.pipeline import AttentionPipeline; print('OK')"

# Default command
CMD ["python3", "-m", "src.main"]

