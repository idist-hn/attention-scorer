# Face Detection Microservice using MediaPipe
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose gRPC and REST ports
EXPOSE 50052
EXPOSE 8052

# Environment variables
ENV GRPC_PORT=50052
ENV REST_PORT=8052
ENV DEVICE=cpu

CMD ["python", "main.py"]

