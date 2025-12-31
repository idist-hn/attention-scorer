# Kiến trúc Hệ thống

## 1. Tổng quan Kiến trúc

Hệ thống được thiết kế theo mô hình **Microservices** với các đặc điểm:

- **Loosely Coupled**: Các service độc lập, giao tiếp qua gRPC
- **Horizontally Scalable**: Có thể scale từng service riêng biệt
- **Technology Agnostic**: Mỗi service sử dụng công nghệ phù hợp nhất
- **Fault Tolerant**: Một service lỗi không ảnh hưởng toàn bộ hệ thống

## 2. Sơ đồ Kiến trúc Tổng quan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WEB CLIENT (3000)                               │
│                         (Next.js 14 + TypeScript)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Video Capture │  │  Dashboard   │  │ Real-time    │  │   Alerts     │     │
│  │  (WebRTC)    │  │     UI       │  │   Charts     │  │   Panel      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ WebSocket / REST API
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (8080) - Golang                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  REST API    │  │  WebSocket   │  │    Auth      │  │ Rate Limiter │     │
│  │   (Fiber)    │  │     Hub      │  │ (JWT/Bcrypt) │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ gRPC
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PIPELINE ORCHESTRATOR (50051)                            │
│                    Service Discovery + Request Routing                       │
└───────────┬───────────────┬───────────────┬───────────────┬─────────────────┘
            │               │               │               │
            ▼               ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│Face Detection │  │   Landmark    │  │  Head Pose    │  │ Gaze Tracking │
│   (50052)     │  │  Detection    │  │   (50054)     │  │    (50055)    │
│   YOLOv8      │  │   (50053)     │  │   SolvePnP    │  │  Iris-based   │
│   GPU-ready   │  │  MediaPipe    │  └───────────────┘  └───────────────┘
└───────────────┘  └───────────────┘
                                        ┌───────────────┐  ┌───────────────┐
                                        │Blink Detection│  │   Attention   │
                                        │    (50056)    │  │    Scorer     │
                                        │  EAR/PERCLOS  │  │    (50057)    │
                                        └───────────────┘  └───────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA STORAGE LAYER                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │
│  │ PostgreSQL   │  │ TimescaleDB  │  │    Redis     │                       │
│  │(Meeting Data)│  │  (Metrics)   │  │(Cache/PubSub)│                       │
│  └──────────────┘  └──────────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.1 AI Microservices Architecture

```
                              ┌─────────────────────────────┐
                              │    Pipeline Orchestrator    │
                              │         :50051              │
                              └──────────────┬──────────────┘
                                             │
          ┌──────────────────────────────────┼──────────────────────────────────┐
          │                                  │                                  │
          ▼                                  ▼                                  ▼
┌─────────────────┐              ┌─────────────────────┐            ┌─────────────────┐
│ Face Detection  │              │ Landmark Detection  │            │  Parallel AI    │
│     :50052      │─────────────▶│       :50053        │───────────▶│   Processing    │
│    YOLOv8       │              │    MediaPipe        │            │                 │
│  (GPU-capable)  │              │   478 landmarks     │            │ ┌─────────────┐ │
└─────────────────┘              └─────────────────────┘            │ │ Head Pose   │ │
                                                                    │ │   :50054    │ │
                                                                    │ ├─────────────┤ │
                                                                    │ │Gaze Tracking│ │
                                                                    │ │   :50055    │ │
                                                                    │ ├─────────────┤ │
                                                                    │ │Blink Detect │ │
                                                                    │ │   :50056    │ │
                                                                    │ └─────────────┘ │
                                                                    └────────┬────────┘
                                                                             │
                                                                             ▼
                                                                    ┌─────────────────┐
                                                                    │Attention Scorer │
                                                                    │     :50057      │
                                                                    └─────────────────┘
```

## 3. Chi tiết các Components

### 3.1 Web Client (Next.js 14)

| Module           | File                            | Chức năng                                 |
| ---------------- | ------------------------------- | ----------------------------------------- |
| Video Capture    | `components/VideoFeed.tsx`      | Thu video từ webcam qua WebRTC            |
| Dashboard UI     | `app/page.tsx`                  | Hiển thị attention grid, participant list |
| Real-time Charts | `components/AttentionChart.tsx` | Biểu đồ attention timeline                |
| Alerts Panel     | `components/AlertPanel.tsx`     | Hiển thị và quản lý alerts                |
| Video Analysis   | `app/analyze/page.tsx`          | Upload video, hiển thị kết quả phân tích  |
| State Management | `store/index.ts`                | Zustand stores (Auth, Meeting, Alert)     |

### 3.2 API Gateway (Golang Fiber)

| Module          | File                           | Chức năng                                    |
| --------------- | ------------------------------ | -------------------------------------------- |
| REST API        | `handlers/*.go`                | CRUD operations cho meetings, users, reports |
| Video Analysis  | `handlers/video_analysis.go`   | Upload và phân tích video offline            |
| Video Analyzer  | `services/video_analyzer.go`   | Xử lý video với FFmpeg, gọi AI pipeline      |
| WebSocket Hub   | `websocket/hub.go`             | Quản lý connections, room-based broadcast    |
| Auth Middleware | `middleware/auth.go`           | JWT authentication với bcrypt                |
| gRPC Client     | `services/grpc_client.go`      | Connection pooling đến AI services           |
| Redis Service   | `services/redis.go`            | Caching + Pub/Sub                            |

### 3.3 AI Microservices (Python)

| Service                   | Port  | Technology         | Chức năng                         |
| ------------------------- | ----- | ------------------ | --------------------------------- |
| **Pipeline Orchestrator** | 50051 | gRPC + Redis       | Điều phối tất cả AI services      |
| **Face Detection**        | 50052 | YOLOv8             | Phát hiện khuôn mặt (GPU-capable) |
| **Landmark Detection**    | 50053 | MediaPipe FaceMesh | Phát hiện 478 facial landmarks    |
| **Head Pose**             | 50054 | OpenCV SolvePnP    | Ước lượng yaw, pitch, roll        |
| **Gaze Tracking**         | 50055 | Iris Analysis      | Theo dõi hướng nhìn               |
| **Blink Detection**       | 50056 | EAR/PERCLOS        | Phát hiện chớp mắt, drowsiness    |
| **Attention Scorer**      | 50057 | Weighted Scoring   | Tính toán attention score         |

### 3.4 Data Storage

| Service    | Technology  | Chức năng                         |
| ---------- | ----------- | --------------------------------- |
| PostgreSQL | TimescaleDB | Meeting data, user accounts       |
| Redis      | Redis 7     | Real-time cache, Pub/Sub, session |
| Prometheus | Metrics     | System monitoring                 |
| Grafana    | Dashboards  | Visualization                     |

## 4. Communication Patterns

### 4.1 Real-time Video Processing Flow

```
                         ┌──────────────────────────┐
                         │      Web Client          │
                         │   (Video Capture)        │
                         └───────────┬──────────────┘
                                     │ WebSocket (binary frames)
                                     ▼
                         ┌──────────────────────────┐
                         │      API Gateway         │
                         │   (Golang + Fiber)       │
                         └───────────┬──────────────┘
                                     │ gRPC
                                     ▼
                         ┌──────────────────────────┐
                         │  Pipeline Orchestrator   │
                         └───────────┬──────────────┘
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
   ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
   │Face Detection │───────▶│   Landmark    │───────▶│  AI Analysis  │
   │   (YOLOv8)    │        │  (MediaPipe)  │        │ (Pose/Gaze/   │
   └───────────────┘        └───────────────┘        │  Blink/Score) │
                                                     └───────┬───────┘
                                                             │
                                     ┌───────────────────────┘
                                     ▼
                         ┌──────────────────────────┐
                         │    Redis Pub/Sub         │
                         └───────────┬──────────────┘
                                     │
                                     ▼
                         ┌──────────────────────────┐
                         │    API Gateway           │
                         │   (WebSocket Hub)        │
                         └───────────┬──────────────┘
                                     │ WebSocket (JSON)
                                     ▼
                         ┌──────────────────────────┐
                         │      Web Client          │
                         │ (Real-time Dashboard)    │
                         └──────────────────────────┘
```

### 4.2 Video Analysis Flow (Offline)

```
┌──────────────────────────┐
│      Web Client          │
│   (Video Upload Form)    │
└───────────┬──────────────┘
            │ POST /api/v1/video-analysis/upload
            ▼
┌──────────────────────────┐
│      API Gateway         │
│   (Video Analyzer)       │
└───────────┬──────────────┘
            │ FFmpeg extract frames
            ▼
┌──────────────────────────┐
│  Pipeline Orchestrator   │
│   (Process each frame)   │
└───────────┬──────────────┘
            │ gRPC calls
            ▼
┌──────────────────────────┐
│    AI Services           │
│ Face → Landmark → Pose   │
│ → Gaze → Blink → Score   │
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│    Results Aggregation   │
│ Timeline, Alerts, Stats  │
└───────────┬──────────────┘
            │ Save to PostgreSQL
            ▼
┌──────────────────────────┐
│      Web Client          │
│  (Results Dashboard)     │
└──────────────────────────┘
```

### 4.3 gRPC Service Communication

```
┌─────────────────────────────────────────────────────────────┐
│                  Protocol Buffer Definitions                 │
├─────────────────────────────────────────────────────────────┤
│ proto/face_detection.proto   - Face detection interface     │
│ proto/landmark_detection.proto - Landmark detection         │
│ proto/head_pose.proto        - Head pose estimation         │
│ proto/gaze_tracking.proto    - Gaze tracking                │
│ proto/blink_detection.proto  - Blink & drowsiness           │
│ proto/attention.proto        - Unified attention service    │
└─────────────────────────────────────────────────────────────┘
```

## 5. Deployment Architecture

### 5.1 Docker Compose (Development)

```yaml
services:
  pipeline-orchestrator:  # Main AI entry point (:50051, :8051)
  face-detection:         # YOLOv8 (:50052, :8052)
  landmark-detection:     # MediaPipe (:50053, :8053)
  head-pose:              # SolvePnP (:50054, :8054)
  gaze-tracking:          # Iris-based (:50055, :8055)
  blink-detection:        # EAR/PERCLOS (:50056, :8056)
  attention-scorer:       # Weighted scoring (:50057, :8057)
  api-gateway:            # Golang Fiber (:8080)
  web-dashboard:          # Next.js (:3000)
  postgres:               # TimescaleDB (:5432)
  redis:                  # Cache + Pub/Sub (:6379)
  prometheus:             # Monitoring (:9090)
  grafana:                # Dashboards (:3001)
```

### 5.2 Kubernetes (Production)

**Namespace**: `attention-detection`

**Domains**:
- Frontend: `https://attention-scorer.idist.dev`
- API: `https://api.attention-scorer.idist.dev`

**Registry**: `registry.idist.dev/attention/*`

```
┌─────────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster (Production)               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Ingress (nginx + cert-manager)                │ │
│  │   attention-scorer.idist.dev → web-dashboard:3000          │ │
│  │   api.attention-scorer.idist.dev → api-gateway:8080        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Deployments                           │   │
│  │  web-dashboard    api-gateway    pipeline-orchestrator   │   │
│  │  face-detection   landmark-detection   head-pose         │   │
│  │  gaze-tracking    blink-detection   attention-scorer     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    StatefulSets                          │   │
│  │         postgres-0              redis                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 6. Service Ports Summary

| Service               | gRPC  | REST  | Protocol | Description          |
| --------------------- | ----- | ----- | -------- | -------------------- |
| Web Dashboard         | -     | 3000  | HTTP     | Next.js frontend     |
| API Gateway           | -     | 8080  | HTTP/WS  | REST API + WebSocket |
| Pipeline Orchestrator | 50051 | 8051  | gRPC/HTTP| AI orchestration     |
| Face Detection        | 50052 | 8052  | gRPC/HTTP| YOLOv8 detection     |
| Landmark Detection    | 50053 | 8053  | gRPC/HTTP| MediaPipe FaceMesh   |
| Head Pose             | 50054 | 8054  | gRPC/HTTP| SolvePnP estimation  |
| Gaze Tracking         | 50055 | 8055  | gRPC/HTTP| Iris-based gaze      |
| Blink Detection       | 50056 | 8056  | gRPC/HTTP| EAR/PERCLOS          |
| Attention Scorer      | 50057 | 8057  | gRPC/HTTP| Score calculation    |
| PostgreSQL            | -     | 5432  | TCP      | TimescaleDB          |
| Redis                 | -     | 6379  | TCP      | Cache/Pub-Sub        |
| Prometheus            | -     | 9090  | HTTP     | Metrics              |
| Grafana               | -     | 3001  | HTTP     | Dashboards           |

