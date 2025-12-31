# Tech Stack

## 1. Tổng quan

| Layer         | Công nghệ                   | Lý do chọn                         |
| ------------- | --------------------------- | ---------------------------------- |
| AI/ML         | Python + MediaPipe + YOLOv8 | Ecosystem ML tốt nhất, GPU support |
| API Gateway   | Golang + Fiber              | Performance cao, concurrency tốt   |
| Frontend      | Next.js 14 + TypeScript     | Modern React, App Router           |
| Database      | PostgreSQL + TimescaleDB    | Reliable, time-series support      |
| Cache/Queue   | Redis                       | Fast, pub/sub support              |
| Communication | gRPC + Protocol Buffers     | High-performance RPC               |
| Container     | Docker + Kubernetes         | Scalable deployment                |

## 2. AI Microservices (Python)

### 2.1 Core Libraries

| Library         | Version | Mục đích                                   |
| --------------- | ------- | ------------------------------------------ |
| `mediapipe`     | 0.10.x  | Face Mesh (478 landmarks), lightweight GPU |
| `ultralytics`   | 8.x     | YOLOv8-face detection                      |
| `opencv-python` | 4.8.x   | Image processing                           |
| `numpy`         | 1.24.x  | Numerical computing                        |
| `cupy`          | 12.x    | GPU-accelerated NumPy                      |

### 2.2 Tracking & Processing

| Library     | Version | Mục đích                     |
| ----------- | ------- | ---------------------------- |
| `bytetrack` | -       | Multi-object tracking (SOTA) |
| `filterpy`  | 1.4.x   | Kalman filter cho smoothing  |
| `scipy`     | 1.11.x  | Scientific computing         |

### 2.3 Communication

| Library        | Version  | Mục đích                      |
| -------------- | -------- | ----------------------------- |
| `redis`        | 5.x      | Message queue client, pub/sub |
| `grpcio`       | 1.59.x   | gRPC server/client            |
| `grpcio-tools` | 1.59.x   | Proto compilation             |
| `asyncio`      | built-in | Async processing              |
| `uvloop`       | 0.19.x   | Fast event loop               |

### 2.4 Microservice Ports

| Service               | Port  | Technology       |
| --------------------- | ----- | ---------------- |
| Pipeline Orchestrator | 50051 | gRPC + Redis     |
| Face Detection        | 50052 | YOLOv8           |
| Landmark Detection    | 50053 | MediaPipe        |
| Head Pose             | 50054 | OpenCV SolvePnP  |
| Gaze Tracking         | 50055 | Iris Analysis    |
| Blink Detection       | 50056 | EAR/PERCLOS      |
| Attention Scorer      | 50057 | Weighted Scoring |

### 2.5 Utilities

| Library             | Version | Mục đích        |
| ------------------- | ------- | --------------- |
| `pydantic`          | 2.x     | Data validation |
| `loguru`            | 0.7.x   | Logging         |
| `prometheus-client` | 0.18.x  | Metrics         |

## 3. Golang API Gateway

### 3.1 Web Framework

| Library             | Version | Mục đích                 |
| ------------------- | ------- | ------------------------ |
| `fiber/v2`          | 2.50.x  | HTTP framework (fastest) |
| `gorilla/websocket` | 1.5.x   | WebSocket support        |

### 3.2 Database & Cache

| Library       | Version | Mục đích           |
| ------------- | ------- | ------------------ |
| `gorm`        | 1.25.x  | ORM cho PostgreSQL |
| `go-redis/v9` | 9.x     | Redis client       |

### 3.3 Authentication & Security

| Library          | Version | Mục đích           |
| ---------------- | ------- | ------------------ |
| `golang-jwt/jwt` | 5.x     | JWT authentication |
| `bcrypt`         | -       | Password hashing   |

### 3.4 Communication

| Library    | Version | Mục đích           |
| ---------- | ------- | ------------------ |
| `grpc-go`  | 1.59.x  | gRPC client/server |
| `protobuf` | 1.31.x  | Protocol buffers   |

## 4. Frontend (Next.js)

### 4.1 Core

| Library      | Version | Mục đích        |
| ------------ | ------- | --------------- |
| `next`       | 14.x    | React framework |
| `react`      | 18.x    | UI library      |
| `typescript` | 5.x     | Type safety     |

### 4.2 UI Components

| Library        | Version | Mục đích          |
| -------------- | ------- | ----------------- |
| `tailwindcss`  | 3.x     | Styling           |
| `shadcn/ui`    | -       | Component library |
| `recharts`     | 2.x     | Charts            |
| `lucide-react` | -       | Icons             |

### 4.3 Real-time & State

| Library            | Version | Mục đích         |
| ------------------ | ------- | ---------------- |
| `socket.io-client` | 4.x     | WebSocket client |
| `zustand`          | 4.x     | State management |
| `react-query`      | 5.x     | Data fetching    |

## 5. Infrastructure

### 5.1 Database

| Service     | Version | Mục đích              |
| ----------- | ------- | --------------------- |
| PostgreSQL  | 15.x    | Primary database      |
| TimescaleDB | 2.x     | Time-series extension |
| Redis       | 7.x     | Cache, message queue  |

### 5.2 DevOps

| Tool           | Mục đích              |
| -------------- | --------------------- |
| Docker         | Containerization      |
| Docker Compose | Local development     |
| Kubernetes     | Production deployment |
| Helm           | K8s package manager   |
| GitHub Actions | CI/CD                 |

### 5.3 Monitoring

| Tool       | Mục đích            |
| ---------- | ------------------- |
| Prometheus | Metrics collection  |
| Grafana    | Visualization       |
| Jaeger     | Distributed tracing |
| ELK Stack  | Log aggregation     |

## 6. Hardware Requirements

### Development

| Component | Minimum      | Recommended   |
| --------- | ------------ | ------------- |
| GPU       | GTX 1060 6GB | RTX 3060 12GB |
| RAM       | 16GB         | 32GB          |
| CPU       | 4 cores      | 8 cores       |
| Storage   | 50GB SSD     | 100GB NVMe    |

### Production (per node)

| Component | Specification         |
| --------- | --------------------- |
| GPU       | NVIDIA A10 / RTX 4090 |
| RAM       | 64GB                  |
| CPU       | 16 cores              |
| Storage   | 500GB NVMe            |

