# Landmark Detection Microservice
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose gRPC port
EXPOSE 50053

ENV GRPC_PORT=50053

CMD ["python", "main.py"]

