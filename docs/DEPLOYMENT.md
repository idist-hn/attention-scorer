# Deployment Guide

This guide covers deploying the Attention Detection System to production.

## Production Environment

| Component | URL | Description |
|-----------|-----|-------------|
| Web Dashboard | https://attention-scorer.idist.dev | Frontend UI |
| API Gateway | https://api.attention-scorer.idist.dev | REST API + WebSocket |
| Container Registry | registry.idist.dev/attention/* | Docker images |

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- Docker with buildx support
- Container registry access (registry.idist.dev)

## Quick Start

### 1. Build and Push Images

```bash
# Build and push all services
docker buildx build --platform linux/amd64 \
  -t registry.idist.dev/attention/api-gateway:latest \
  --push services/api-gateway

docker buildx build --platform linux/amd64 \
  -t registry.idist.dev/attention/web-dashboard:latest \
  --push services/web-dashboard

docker buildx build --platform linux/amd64 \
  -t registry.idist.dev/attention/pipeline-orchestrator:latest \
  --push services/pipeline-orchestrator

# AI Services
for svc in face-detection landmark-detection head-pose gaze-tracking blink-detection attention-scorer; do
  docker buildx build --platform linux/amd64 \
    -t registry.idist.dev/attention/$svc:latest \
    --push services/$svc
done
```

### 2. Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace attention-detection

# Apply secrets
kubectl apply -f k8s/secrets.yaml -n attention-detection

# Deploy databases
kubectl apply -f k8s/postgres.yaml -n attention-detection
kubectl apply -f k8s/redis.yaml -n attention-detection

# Deploy AI services
kubectl apply -f k8s/ai-services.yaml -n attention-detection

# Deploy backend and frontend
kubectl apply -f k8s/api-gateway.yaml -n attention-detection
kubectl apply -f k8s/web-dashboard.yaml -n attention-detection

# Deploy ingress
kubectl apply -f k8s/ingress.yaml -n attention-detection
```

### 3. Verify Deployment

```bash
# Check all pods
kubectl get pods -n attention-detection

# Expected output:
# NAME                                    READY   STATUS    RESTARTS   AGE
# api-gateway-xxx                         1/1     Running   0          1m
# attention-scorer-xxx                    1/1     Running   0          1m
# blink-detection-xxx                     1/1     Running   0          1m
# face-detection-xxx                      1/1     Running   0          1m
# gaze-tracking-xxx                       1/1     Running   0          1m
# head-pose-xxx                           1/1     Running   0          1m
# landmark-detection-xxx                  1/1     Running   0          1m
# pipeline-orchestrator-xxx               1/1     Running   0          1m
# postgres-0                              1/1     Running   0          1m
# redis-xxx                               1/1     Running   0          1m
# web-dashboard-xxx                       1/1     Running   0          1m

# Check services
kubectl get svc -n attention-detection

# Check ingress
kubectl get ingress -n attention-detection
```

## Rolling Updates

```bash
# Update a specific service
kubectl rollout restart deployment/api-gateway -n attention-detection
kubectl rollout restart deployment/web-dashboard -n attention-detection

# Watch rollout status
kubectl rollout status deployment/api-gateway -n attention-detection
```

## Service Ports (Internal)

| Service | Port | Protocol |
|---------|------|----------|
| API Gateway | 8080 | HTTP/WS |
| Web Dashboard | 3000 | HTTP |
| Pipeline Orchestrator | 50051 | gRPC |
| Face Detection | 50052 | gRPC |
| Landmark Detection | 50053 | gRPC |
| Head Pose | 50054 | gRPC |
| Gaze Tracking | 50055 | gRPC |
| Blink Detection | 50056 | gRPC |
| Attention Scorer | 50057 | gRPC |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |

## Monitoring

```bash
# Check pod status
kubectl get pods -n attention-detection

# View logs
kubectl logs -f deployment/api-gateway -n attention-detection

# Port forward for local access
kubectl port-forward svc/web-dashboard 3000:3000 -n attention-detection
```

## Troubleshooting

```bash
# Check events
kubectl get events -n attention-detection --sort-by='.lastTimestamp'

# Describe pod issues
kubectl describe pod <pod-name> -n attention-detection

# Check GPU allocation
kubectl describe nodes | grep -A5 "nvidia.com/gpu"
```

