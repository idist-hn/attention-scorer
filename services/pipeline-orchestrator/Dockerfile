# Pipeline Orchestrator Microservice
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 50051

ENV GRPC_PORT=50051
ENV REDIS_URL=redis://redis:6379

# Service discovery
ENV FACE_DETECTION_HOST=face-detection
ENV FACE_DETECTION_PORT=50052
ENV LANDMARK_DETECTION_HOST=landmark-detection
ENV LANDMARK_DETECTION_PORT=50053
ENV HEAD_POSE_HOST=head-pose
ENV HEAD_POSE_PORT=50054
ENV GAZE_TRACKING_HOST=gaze-tracking
ENV GAZE_TRACKING_PORT=50055
ENV BLINK_DETECTION_HOST=blink-detection
ENV BLINK_DETECTION_PORT=50056
ENV ATTENTION_SCORER_HOST=attention-scorer
ENV ATTENTION_SCORER_PORT=50057

CMD ["python", "main.py"]

