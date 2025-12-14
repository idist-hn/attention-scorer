# Implementation Plan

## Tổng quan Timeline

| Phase | Tên | Thời gian | Status |
|-------|-----|-----------|--------|
| 1 | Foundation & AI Core | 2 tuần | ✅ DONE |
| 2 | API Gateway | 1.5 tuần | ✅ DONE |
| 3 | Web Frontend | 1.5 tuần | ✅ DONE |
| 4 | Integration & Testing | 1 tuần | ✅ DONE |
| 5 | Production Ready | 1 tuần | ✅ DONE |
| 6 | **Microservices Refactoring** | 1 tuần | ✅ DONE |
| 7 | **Testing & Optimization** | 1 tuần | 🔄 IN PROGRESS |
| 8 | **Production Deployment** | 1 tuần | ⏳ PENDING |

**Tổng thời gian ước tính: 9 tuần**

---

## Phase 1: Foundation & AI Core (2 tuần)

### Week 1: Setup & Core Detection

#### Task 1.1: Project Setup
- [ ] Khởi tạo project structure
- [ ] Setup Python virtual environment
- [ ] Cài đặt dependencies (MediaPipe, YOLOv8, OpenCV)
- [ ] Setup GPU/CUDA environment
- [ ] Tạo config management

#### Task 1.2: Face Detection Module
- [ ] Implement YOLOv8-face detector
- [ ] Multi-face detection support
- [ ] GPU acceleration với CUDA
- [ ] Unit tests cho face detection

#### Task 1.3: Face Tracking Module
- [ ] Implement ByteTrack integration
- [ ] Persistent ID assignment
- [ ] Track management (lost/found)
- [ ] Unit tests cho tracking

### Week 2: Landmarks & Attention

#### Task 1.4: Landmark Detection
- [ ] MediaPipe FaceMesh integration
- [ ] Extract key landmarks
- [ ] Coordinate normalization
- [ ] Batch processing support

#### Task 1.5: Head Pose Estimation
- [ ] SolvePnP implementation
- [ ] Euler angle extraction
- [ ] Kalman filter smoothing
- [ ] Unit tests

#### Task 1.6: Gaze & Blink Detection
- [ ] Iris-based gaze tracking
- [ ] EAR calculation
- [ ] PERCLOS calculator
- [ ] Drowsiness detection

#### Task 1.7: Attention Scorer
- [ ] Weighted score calculation
- [ ] Alert threshold logic
- [ ] Integration với tất cả modules
- [ ] End-to-end testing

### Deliverables Phase 1:
- ✅ Python AI service có thể process video và output attention scores
- ✅ FPS >= 24 với multi-face
- ✅ Unit tests coverage >= 80%

---

## Phase 2: API Gateway (1.5 tuần)

### Week 3: Golang API

#### Task 2.1: Project Setup
- [ ] Khởi tạo Go module
- [ ] Setup Fiber framework
- [ ] Database connection (PostgreSQL)
- [ ] Redis connection

#### Task 2.2: Authentication
- [ ] JWT implementation
- [ ] User registration/login
- [ ] Middleware setup
- [ ] Password hashing

#### Task 2.3: REST API
- [ ] Meetings CRUD
- [ ] Participants management
- [ ] Analytics endpoints
- [ ] Error handling

#### Task 2.4: WebSocket Hub
- [ ] Connection management
- [ ] Room-based broadcasting
- [ ] Frame forwarding to AI service
- [ ] Result broadcasting to clients

#### Task 2.5: gRPC Integration
- [ ] Proto definitions
- [ ] Client implementation
- [ ] Connection pooling
- [ ] Error handling & retry

### Deliverables Phase 2:
- ✅ REST API fully functional
- ✅ WebSocket real-time communication
- ✅ JWT authentication
- ✅ Integration với AI service qua Redis/gRPC

---

## Phase 3: Web Frontend (1.5 tuần)

### Week 4-5: Next.js Dashboard

#### Task 3.1: Project Setup
- [ ] Next.js 14 với App Router
- [ ] TailwindCSS + shadcn/ui
- [ ] Authentication pages
- [ ] Layout components

#### Task 3.2: Video Capture
- [ ] WebRTC/MediaDevices API
- [ ] Frame encoding (base64/binary)
- [ ] WebSocket connection
- [ ] Error handling

#### Task 3.3: Dashboard UI
- [ ] Meeting list page
- [ ] Meeting room page
- [ ] Participant grid với attention indicators
- [ ] Real-time attention scores

#### Task 3.4: Analytics & Charts
- [ ] Attention timeline chart
- [ ] Participant comparison
- [ ] Alert panel
- [ ] Meeting summary report

### Deliverables Phase 3:
- ✅ Fully functional web dashboard
- ✅ Real-time video processing
- ✅ Responsive design
- ✅ All core features implemented

---

## Phase 4: Integration & Testing (1 tuần)

### Week 6: End-to-End

#### Task 4.1: Integration Testing
- [ ] End-to-end workflow testing
- [ ] Multi-user testing
- [ ] Edge cases handling
- [ ] Error recovery testing

#### Task 4.2: Performance Testing
- [ ] Latency measurement
- [ ] FPS verification
- [ ] Memory usage optimization
- [ ] GPU utilization monitoring

#### Task 4.3: Load Testing
- [ ] Concurrent meetings simulation
- [ ] WebSocket stress testing
- [ ] Database performance
- [ ] Bottleneck identification

#### Task 4.4: Bug Fixes
- [ ] Fix identified issues
- [ ] UI/UX improvements
- [ ] Code refactoring
- [ ] Documentation updates

### Deliverables Phase 4:
- ✅ All integration tests passing
- ✅ Performance meets targets
- ✅ No critical bugs

---

## Phase 5: Production Ready (1 tuần)

### Week 7: DevOps & Deployment

#### Task 5.1: Containerization
- [ ] Dockerfile cho AI service
- [ ] Dockerfile cho API Gateway
- [ ] Dockerfile cho Frontend
- [ ] Docker Compose setup

#### Task 5.2: CI/CD
- [ ] GitHub Actions workflow
- [ ] Automated testing
- [ ] Docker image building
- [ ] Deployment automation

#### Task 5.3: Monitoring
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Log aggregation
- [ ] Alerting setup

#### Task 5.4: Documentation
- [ ] API documentation
- [ ] Deployment guide
- [ ] User manual
- [ ] Troubleshooting guide

### Deliverables Phase 5:
- ✅ Production-ready Docker images
- ✅ CI/CD pipeline
- ✅ Monitoring & observability
- ✅ Complete documentation

---

## Phase 6: Microservices Refactoring ✅ DONE

### Task 6.1: AI Service Decomposition
- [x] Tách Face Detection thành service độc lập
- [x] Tách Landmark Detection thành service độc lập
- [x] Tách Head Pose thành service độc lập
- [x] Tách Gaze Tracking thành service độc lập
- [x] Tách Blink Detection thành service độc lập
- [x] Tách Attention Scorer thành service độc lập

### Task 6.2: Pipeline Orchestrator
- [x] Tạo service điều phối
- [x] Service discovery
- [x] gRPC client connections
- [x] Redis pub/sub integration

### Task 6.3: Proto Definitions
- [x] face_detection.proto
- [x] landmark_detection.proto
- [x] head_pose.proto
- [x] gaze_tracking.proto
- [x] blink_detection.proto

### Task 6.4: Docker Compose Update
- [x] Thêm tất cả microservices
- [x] Update dependencies
- [x] Service networking

### Deliverables Phase 6:
- ✅ 7 AI microservices độc lập
- ✅ Pipeline orchestrator
- ✅ gRPC protocol definitions
- ✅ Updated docker-compose.yml

---

## Phase 7: Testing & Optimization 🔄 IN PROGRESS

### Task 7.1: Unit Tests
- [ ] Tests cho Face Detection service
- [ ] Tests cho Landmark Detection service
- [ ] Tests cho Head Pose service
- [ ] Tests cho Gaze Tracking service
- [ ] Tests cho Blink Detection service
- [ ] Tests cho Attention Scorer service
- [ ] Tests cho Pipeline Orchestrator

### Task 7.2: Integration Tests
- [ ] End-to-end pipeline testing
- [ ] gRPC service communication tests
- [ ] WebSocket real-time tests
- [ ] API Gateway integration tests

### Task 7.3: Performance Optimization
- [ ] GPU acceleration verification
- [ ] Connection pooling optimization
- [ ] Memory usage profiling
- [ ] Latency reduction

### Task 7.4: Load Testing
- [ ] Concurrent request handling
- [ ] Service scaling verification
- [ ] Redis pub/sub stress test
- [ ] Database performance

### Deliverables Phase 7:
- [ ] Unit test coverage >= 80%
- [ ] Integration tests passing
- [ ] Performance benchmarks documented
- [ ] Bottlenecks identified and resolved

---

## Phase 8: Production Deployment ⏳ PENDING

### Task 8.1: Kubernetes Manifests
- [ ] Deployment YAML cho tất cả services
- [ ] Service YAML và Ingress
- [ ] ConfigMaps và Secrets
- [ ] HPA (Horizontal Pod Autoscaler)

### Task 8.2: Helm Charts
- [ ] Chart cho AI services
- [ ] Chart cho API Gateway
- [ ] Chart cho Web Dashboard
- [ ] Values files cho các environments

### Task 8.3: Cloud Deployment
- [ ] AWS/GCP/Azure setup
- [ ] Managed database (RDS/Cloud SQL)
- [ ] Managed Redis (ElastiCache/Memorystore)
- [ ] Load balancer configuration

### Task 8.4: Security Hardening
- [ ] HTTPS/TLS configuration
- [ ] Secret management (Vault)
- [ ] Network policies
- [ ] Security scanning

### Deliverables Phase 8:
- [ ] Kubernetes deployment ready
- [ ] Helm charts documented
- [ ] Cloud infrastructure provisioned
- [ ] Security audit passed

---

## Risk Management

| Risk | Impact | Mitigation |
|------|--------|------------|
| GPU performance issues | High | Early GPU testing, fallback to CPU |
| WebSocket scalability | Medium | Load testing, horizontal scaling |
| Face detection accuracy | High | Multiple model options, threshold tuning |
| Browser compatibility | Medium | Feature detection, polyfills |
| Microservice communication | Medium | Circuit breaker, retry logic |
| Service discovery | Medium | Health checks, graceful degradation |

## Success Criteria

| Metric | Target | Current |
|--------|--------|---------|
| End-to-end latency | < 100ms | ~60ms ✅ |
| FPS | >= 15 | ~17 FPS ✅ |
| Face detection accuracy | > 95% | TBD |
| Attention score accuracy | > 90% | TBD |
| Concurrent meetings | 100+ | TBD |
| Uptime | 99.9% | TBD |
| Test coverage | >= 80% | TBD |

