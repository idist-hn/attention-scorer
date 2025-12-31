# Meeting Attention Detection System

## 🎯 Tổng quan

Hệ thống nhận dạng sự chú ý trong cuộc họp (Meeting Attention Detection System) là một giải pháp AI-powered để theo dõi và phân tích mức độ tập trung của người tham gia trong các cuộc họp trực tuyến.

## 📋 Mục tiêu

- **Real-time Monitoring**: Theo dõi sự chú ý của participants với tốc độ 17+ FPS
- **Multi-face Tracking**: Hỗ trợ theo dõi nhiều người cùng lúc (10-20 người)
- **Accurate Detection**: Độ chính xác > 90% trong việc phát hiện attention
- **Low Latency**: Độ trễ ~60ms per frame
- **Scalable**: Microservices architecture, hỗ trợ 100+ cuộc họp đồng thời

## 🏗️ Kiến trúc Microservices

Hệ thống được thiết kế theo mô hình **Microservices** với các service độc lập:

### AI Microservices (Python)

| Service                   | gRPC Port | REST Port | Technology       | Chức năng                 |
| ------------------------- | --------- | --------- | ---------------- | ------------------------- |
| **Pipeline Orchestrator** | 50051     | 8051      | gRPC + Redis     | Điều phối các AI services |
| **Face Detection**        | 50052     | 8052      | YOLOv8           | Phát hiện khuôn mặt       |
| **Landmark Detection**    | 50053     | 8053      | MediaPipe        | 478 facial landmarks      |
| **Head Pose**             | 50054     | 8054      | OpenCV SolvePnP  | Yaw, Pitch, Roll          |
| **Gaze Tracking**         | 50055     | 8055      | Iris Analysis    | Hướng nhìn                |
| **Blink Detection**       | 50056     | 8056      | EAR/PERCLOS      | Chớp mắt, drowsiness      |
| **Attention Scorer**      | 50057     | 8057      | Weighted Scoring | Attention score           |

### Backend & Frontend

| Component         | Port | Technology     | Chức năng                 |
| ----------------- | ---- | -------------- | ------------------------- |
| **API Gateway**   | 8080 | Golang + Fiber | REST API, WebSocket, Auth |
| **Web Dashboard** | 3000 | Next.js 14     | Real-time visualization   |

## 📁 Cấu trúc Project

```
attention-detection/
├── services/
│   ├── pipeline-orchestrator/  # AI Pipeline Orchestrator
│   ├── face-detection/         # Face Detection Service
│   ├── landmark-detection/     # Landmark Detection Service
│   ├── head-pose/              # Head Pose Service
│   ├── gaze-tracking/          # Gaze Tracking Service
│   ├── blink-detection/        # Blink Detection Service
│   ├── attention-scorer/       # Attention Scorer Service
│   ├── ai-processor/           # Legacy Monolithic (testing)
│   ├── api-gateway/            # Golang API Gateway
│   └── web-dashboard/          # Next.js Frontend
├── proto/                      # gRPC Protocol Buffers
├── k8s/                        # Kubernetes manifests
│   ├── base/                   # Base configurations
│   └── overlays/               # Environment overlays (dev/prod)
├── docs/                       # Documentation
├── migrations/                 # Database migrations
├── monitoring/                 # Prometheus/Grafana configs
├── docker-compose.yml          # Docker orchestration
└── Makefile                    # Build commands
```

## 🚀 Tính năng chính

### Core Features
- ✅ Face Detection & Multi-face Tracking
- ✅ Facial Landmark Detection (478 points)
- ✅ Head Pose Estimation
- ✅ Eye Gaze Tracking
- ✅ Blink Detection & PERCLOS
- ✅ Attention Score Calculation

### Meeting-Specific Features
- 📊 Real-time Attention Dashboard
- 📈 Attention Timeline & Analytics
- 🔔 Alert System (Not Attentive, Drowsy, Looking Away)
- 📝 Meeting Summary Report
- 👥 Participant Engagement Metrics

### Video Analysis (Offline)
- 📹 Upload video files for offline analysis
- 📊 Attention timeline visualization
- 📈 Summary statistics (avg, min, max attention)
- 🔔 Alert detection throughout video
- 📁 Support MP4, WebM, AVI, MOV, MKV formats

## 🌐 Production URLs

| Service | URL |
|---------|-----|
| Web Dashboard | https://attention-scorer.idist.dev |
| API Gateway | https://api.attention-scorer.idist.dev |

## 📚 Tài liệu

| Tài liệu                                           | Mô tả                            |
| -------------------------------------------------- | -------------------------------- |
| [ARCHITECTURE.md](./ARCHITECTURE.md)               | Kiến trúc microservices chi tiết |
| [MICROSERVICES.md](./MICROSERVICES.md)             | Hướng dẫn AI Microservices       |
| [TECH_STACK.md](./TECH_STACK.md)                   | Công nghệ sử dụng                |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)         | Thiết kế database                |
| [API_SPECIFICATION.md](./API_SPECIFICATION.md)     | Đặc tả API                       |
| [ATTENTION_ALGORITHM.md](./ATTENTION_ALGORITHM.md) | Thuật toán Attention             |
| [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) | Kế hoạch triển khai              |

## 🚀 Quick Start

### Development (Docker Compose)

```bash
# 1. Clone và chạy với Docker Compose
docker-compose up -d

# 2. Access
# - Web Dashboard: http://localhost:3000
# - API Gateway: http://localhost:8080
# - Grafana: http://localhost:3001
```

### Production (Kubernetes)

```bash
# Deploy lên K8s cluster
kubectl apply -k k8s/overlays/prod

# Hoặc từng bước
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/secrets.yaml
kubectl apply -f k8s/base/postgres.yaml
kubectl apply -f k8s/base/redis.yaml
kubectl apply -f k8s/base/ -n attention-detection
```

## 🛠️ Yêu cầu hệ thống

### Hardware
- **GPU**: NVIDIA GPU với CUDA support (khuyến nghị, optional cho CPU mode)
- **RAM**: Tối thiểu 8GB (16GB khuyến nghị)
- **CPU**: 4+ cores

### Software
- Python 3.10+
- Go 1.21+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ / TimescaleDB
- Redis 7+

## 📊 Performance

| Metric          | Value               |
| --------------- | ------------------- |
| Processing Time | ~58ms/frame (CPU)   |
| FPS             | ~17 FPS             |
| Latency         | <100ms end-to-end   |
| Memory          | ~2GB per AI service |

## 📄 License

MIT License - Xem file [LICENSE](../LICENSE) để biết thêm chi tiết.

