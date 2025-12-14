#!/bin/bash
# Generate gRPC code from proto files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$ROOT_DIR/proto"

echo "=========================================="
echo "Generating gRPC code from proto files"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create output directories
PYTHON_OUT="$ROOT_DIR/services/ai-processor/src/generated"
GO_OUT="$ROOT_DIR/services/api-gateway/pkg/proto"

mkdir -p "$PYTHON_OUT"
mkdir -p "$GO_OUT"

# =============================================
# Generate Python gRPC code
# =============================================
echo -e "${BLUE}Generating Python gRPC code...${NC}"

cd "$ROOT_DIR"

# Generate for each proto file
for proto_file in "$PROTO_DIR"/*.proto; do
    filename=$(basename "$proto_file" .proto)
    echo "  - Processing $filename.proto"
    
    python3 -m grpc_tools.protoc \
        --proto_path="$PROTO_DIR" \
        --python_out="$PYTHON_OUT" \
        --grpc_python_out="$PYTHON_OUT" \
        "$proto_file"
done

# Create __init__.py
cat > "$PYTHON_OUT/__init__.py" << 'EOF'
"""Generated gRPC code from proto files."""

from .attention_pb2 import *
from .attention_pb2_grpc import *
from .face_detection_pb2 import *
from .face_detection_pb2_grpc import *
from .landmark_detection_pb2 import *
from .landmark_detection_pb2_grpc import *
from .head_pose_pb2 import *
from .head_pose_pb2_grpc import *
from .gaze_tracking_pb2 import *
from .gaze_tracking_pb2_grpc import *
from .blink_detection_pb2 import *
from .blink_detection_pb2_grpc import *
EOF

echo -e "${GREEN}✓ Python gRPC code generated in $PYTHON_OUT${NC}"

# =============================================
# Generate Go gRPC code
# =============================================
echo -e "${BLUE}Generating Go gRPC code...${NC}"

# Check if protoc-gen-go is installed
if ! command -v protoc-gen-go &> /dev/null; then
    echo "Installing protoc-gen-go..."
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
fi

# Generate for each proto file
for proto_file in "$PROTO_DIR"/*.proto; do
    filename=$(basename "$proto_file" .proto)
    echo "  - Processing $filename.proto"
    
    # Create package directory
    pkg_dir="$GO_OUT/$filename"
    mkdir -p "$pkg_dir"
    
    protoc \
        --proto_path="$PROTO_DIR" \
        --go_out="$pkg_dir" \
        --go_opt=paths=source_relative \
        --go-grpc_out="$pkg_dir" \
        --go-grpc_opt=paths=source_relative \
        "$proto_file" 2>/dev/null || echo "    (Go generation skipped - protoc not found)"
done

echo -e "${GREEN}✓ Go gRPC code generated in $GO_OUT${NC}"

# =============================================
# Summary
# =============================================
echo ""
echo "=========================================="
echo "Generated files:"
echo "=========================================="
echo "Python:"
ls -la "$PYTHON_OUT"/*.py 2>/dev/null || echo "  (no files)"
echo ""
echo "Go:"
find "$GO_OUT" -name "*.go" 2>/dev/null || echo "  (no files)"
echo ""
echo -e "${GREEN}Done!${NC}"

