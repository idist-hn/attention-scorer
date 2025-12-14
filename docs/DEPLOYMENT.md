# Deployment Guide

This guide covers deploying the Attention Detection System to production.

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- Helm 3.x
- Container registry access
- GPU nodes (for face detection)

## Quick Start

### 1. Build and Push Images

```bash
# Build all images
docker-compose build

# Tag and push to registry
docker tag attention/face-detection:latest your-registry/face-detection:v1.0.0
docker tag attention/api-gateway:latest your-registry/api-gateway:v1.0.0
docker tag attention/web-dashboard:latest your-registry/web-dashboard:v1.0.0

docker push your-registry/face-detection:v1.0.0
docker push your-registry/api-gateway:v1.0.0
docker push your-registry/web-dashboard:v1.0.0
```

### 2. Deploy with Kustomize

```bash
# Development
kubectl apply -k k8s/overlays/dev

# Production
kubectl apply -k k8s/overlays/prod
```

### 3. Deploy with Helm

```bash
# Add dependencies
cd helm/attention-detection
helm dependency update

# Install
helm install attention ./helm/attention-detection \
  --namespace attention-detection \
  --create-namespace \
  --set secrets.jwtSecret=your-secret \
  --set postgresql.auth.password=your-db-password
```

## Cloud-Specific Deployment

### AWS EKS

```bash
# Create EKS cluster
eksctl create cluster \
  --name attention-cluster \
  --region us-east-1 \
  --nodegroup-name gpu-nodes \
  --node-type p3.2xlarge \
  --nodes 2

# Install NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/nvidia-device-plugin.yml

# Deploy
helm install attention ./helm/attention-detection -f values-aws.yaml
```

### GCP GKE

```bash
# Create GKE cluster with GPU
gcloud container clusters create attention-cluster \
  --zone us-central1-a \
  --accelerator type=nvidia-tesla-t4,count=1 \
  --num-nodes 3

# Install NVIDIA driver
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml

# Deploy
helm install attention ./helm/attention-detection -f values-gcp.yaml
```

### Azure AKS

```bash
# Create AKS cluster
az aks create \
  --resource-group attention-rg \
  --name attention-cluster \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Add GPU node pool
az aks nodepool add \
  --resource-group attention-rg \
  --cluster-name attention-cluster \
  --name gpupool \
  --node-count 2 \
  --node-vm-size Standard_NC6

# Deploy
helm install attention ./helm/attention-detection -f values-azure.yaml
```

## Scaling

```bash
# Manual scaling
kubectl scale deployment face-detection --replicas=5 -n attention-detection

# HPA will auto-scale based on CPU/Memory metrics
kubectl get hpa -n attention-detection
```

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

