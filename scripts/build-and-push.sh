#!/bin/bash

# Build and push all Docker images to registry.idist.dev
REGISTRY="registry.idist.dev"
PROJECT="attention"
TAG="latest"

# Services to build
SERVICES=(
    "face-detection:services/face-detection"
    "landmark-detection:services/landmark-detection"
    "head-pose:services/head-pose"
    "gaze-tracking:services/gaze-tracking"
    "blink-detection:services/blink-detection"
    "attention-scorer:services/attention-scorer"
    "pipeline-orchestrator:services/pipeline-orchestrator"
    "api-gateway:services/api-gateway"
    "web-dashboard:services/web-dashboard"
)

echo "🚀 Building and tagging Docker images..."
echo "Registry: $REGISTRY/$PROJECT"
echo ""

# Login to registry
echo "🔐 Logging in to registry..."
echo 'HanhHanh2508@' | docker login $REGISTRY -u idist-hn --password-stdin

if [ $? -ne 0 ]; then
    echo "❌ Failed to login to registry"
    exit 1
fi

echo ""
echo "✅ Logged in successfully"
echo ""

# Build and push each service
for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r name path <<< "$service_info"
    
    echo "📦 Building $name from $path..."
    
    # Build image
    docker build -t $REGISTRY/$PROJECT/$name:$TAG $path
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to build $name"
        continue
    fi
    
    echo "🚀 Pushing $REGISTRY/$PROJECT/$name:$TAG..."
    docker push $REGISTRY/$PROJECT/$name:$TAG
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to push $name"
        continue
    fi
    
    echo "✅ $name pushed successfully"
    echo ""
done

echo ""
echo "🎉 All images built and pushed!"
echo ""
echo "Images:"
for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r name path <<< "$service_info"
    echo "  - $REGISTRY/$PROJECT/$name:$TAG"
done

