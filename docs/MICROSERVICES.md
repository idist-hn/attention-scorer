# Microservices Architecture

## Overview

Hệ thống AI Processing đã được tách thành các microservices độc lập, có thể scale riêng biệt.

## Service Map

```
                                    ┌─────────────────┐
                                    │  API Gateway    │
                                    │   (Golang)      │
                                    │   :8080         │
                                    └────────┬────────┘
                                             │
                                             │ gRPC
                                             ▼
                                    ┌─────────────────┐
                                    │    Pipeline     │
                                    │  Orchestrator   │
                                    │   :50051        │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
        ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
        │  Face Detection   │    │     Landmark      │    │   Parallel AI     │
        │    (YOLOv8)       │───▶│    Detection      │───▶│   Processing      │
        │     :50052        │    │   (MediaPipe)     │    │                   │
        └───────────────────┘    │     :50053        │    │  ┌─────────────┐  │
                                 └───────────────────┘    │  │ Head Pose   │  │
                                                          │  │   :50054    │  │
                                                          │  ├─────────────┤  │
                                                          │  │ Gaze Track  │  │
                                                          │  │   :50055    │  │
                                                          │  ├─────────────┤  │
                                                          │  │ Blink Det   │  │
                                                          │  │   :50056    │  │
                                                          │  └─────────────┘  │
                                                          └─────────┬─────────┘
                                                                    │
                                                                    ▼
                                                          ┌───────────────────┐
                                                          │ Attention Scorer  │
                                                          │     :50057        │
                                                          └───────────────────┘
```

## Services

| Service                   | Port  | Technology         | Description                             |
| ------------------------- | ----- | ------------------ | --------------------------------------- |
| **Pipeline Orchestrator** | 50051 | Python + gRPC      | Điều phối các microservices             |
| **Face Detection**        | 50052 | Python + YOLOv8    | Phát hiện khuôn mặt (GPU-capable)       |
| **Landmark Detection**    | 50053 | Python + MediaPipe | Phát hiện 478 facial landmarks          |
| **Head Pose**             | 50054 | Python + OpenCV    | Ước lượng tư thế đầu (yaw, pitch, roll) |
| **Gaze Tracking**         | 50055 | Python             | Theo dõi hướng nhìn dựa trên iris       |
| **Blink Detection**       | 50056 | Python             | Phát hiện chớp mắt + PERCLOS            |
| **Attention Scorer**      | 50057 | Python             | Tính điểm tập trung                     |
| **API Gateway**           | 8080  | Golang + Fiber     | REST API + WebSocket                    |
| **Web Dashboard**         | 3000  | Next.js 14         | Giao diện người dùng                    |

## Benefits

### 1. Independent Scaling
- **Face Detection** có thể scale trên GPU nodes
- **Lightweight services** (Head Pose, Gaze, Blink) có thể scale trên CPU

### 2. Fault Isolation
- Một service lỗi không ảnh hưởng các service khác
- Circuit breaker pattern để xử lý failures

### 3. Technology Flexibility
- Mỗi service có thể dùng công nghệ phù hợp nhất
- Dễ dàng thay thế hoặc upgrade từng service

### 4. Independent Deployment
- Deploy riêng từng service mà không ảnh hưởng system
- A/B testing và canary deployments

## Communication

### gRPC (Service-to-Service)
- Efficient binary protocol (Protocol Buffers)
- Bidirectional streaming for real-time processing
- Automatic code generation

### Redis Pub/Sub (Event Broadcasting)
- Publish attention updates to subscribers
- Decouple producers and consumers

## Scaling Strategies

```yaml
# Kubernetes HPA example
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: face-detection-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: face-detection
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Running Microservices

```bash
# Docker Compose (Development)
docker-compose up -d

# Individual services
docker-compose up face-detection landmark-detection

# Scale specific service
docker-compose up --scale face-detection=3

# Check service health
curl http://localhost:50052/health
```

## Proto Files

| Proto                            | Description                             |
| -------------------------------- | --------------------------------------- |
| `proto/face_detection.proto`     | Face detection service definition       |
| `proto/landmark_detection.proto` | Landmark detection service definition   |
| `proto/head_pose.proto`          | Head pose estimation service definition |
| `proto/gaze_tracking.proto`      | Gaze tracking service definition        |
| `proto/blink_detection.proto`    | Blink detection service definition      |
| `proto/attention.proto`          | Unified attention service (legacy)      |

