"""
Test script for Face Detection Microservice
"""
import sys
import cv2
import numpy as np
from pathlib import Path

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent))

from main import FaceDetectionServicer


class MockRequest:
    """Mock gRPC request."""
    def __init__(self, frame_data: bytes, request_id: str = "test-001", confidence_threshold: float = 0.5):
        self.frame_data = frame_data
        self.request_id = request_id
        self.confidence_threshold = confidence_threshold


def test_face_detection_with_synthetic_image():
    """Test face detection with a synthetic image (no real face)."""
    print("=" * 60)
    print("Test 1: Face Detection with synthetic image")
    print("=" * 60)
    
    # Create a simple test image
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    test_image[:] = (100, 100, 100)  # Gray background
    
    # Encode image
    _, buffer = cv2.imencode('.jpg', test_image)
    frame_data = buffer.tobytes()
    
    # Initialize service
    servicer = FaceDetectionServicer(model_path="yolov8n.pt", device="cpu")
    
    # Create request
    request = MockRequest(frame_data=frame_data)
    
    # Run detection
    result = servicer.DetectFaces(request, None)
    
    print(f"  Request ID: {result['request_id']}")
    print(f"  Success: {result['success']}")
    print(f"  Faces detected: {len(result['faces'])}")
    print(f"  Processing time: {result['processing_time_ms']:.2f}ms")
    
    assert result['success'] == True
    print("  ✅ Test passed!\n")


def test_face_detection_with_sample_face():
    """Test face detection with a face-like pattern."""
    print("=" * 60)
    print("Test 2: Face Detection with face-like pattern")
    print("=" * 60)
    
    # Create image with circle (face-like)
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    test_image[:] = (200, 200, 200)
    
    # Draw a face-like pattern
    cv2.circle(test_image, (320, 240), 100, (180, 150, 130), -1)  # Face
    cv2.circle(test_image, (290, 220), 15, (50, 50, 50), -1)  # Left eye
    cv2.circle(test_image, (350, 220), 15, (50, 50, 50), -1)  # Right eye
    cv2.ellipse(test_image, (320, 280), (30, 15), 0, 0, 180, (100, 80, 80), 2)  # Mouth
    
    _, buffer = cv2.imencode('.jpg', test_image)
    frame_data = buffer.tobytes()
    
    servicer = FaceDetectionServicer(model_path="yolov8n.pt", device="cpu")
    request = MockRequest(frame_data=frame_data)
    result = servicer.DetectFaces(request, None)
    
    print(f"  Request ID: {result['request_id']}")
    print(f"  Success: {result['success']}")
    print(f"  Faces detected: {len(result['faces'])}")
    print(f"  Processing time: {result['processing_time_ms']:.2f}ms")
    
    assert result['success'] == True
    print("  ✅ Test passed!\n")


def test_health_check():
    """Test health check endpoint."""
    print("=" * 60)
    print("Test 3: Health Check")
    print("=" * 60)
    
    servicer = FaceDetectionServicer(model_path="yolov8n.pt", device="cpu")
    result = servicer.Health(None, None)
    
    print(f"  Healthy: {result['healthy']}")
    print(f"  Version: {result['version']}")
    print(f"  Device: {result['device']}")
    
    assert result['healthy'] == True
    print("  ✅ Test passed!\n")


def test_invalid_image():
    """Test with invalid image data."""
    print("=" * 60)
    print("Test 4: Invalid Image Data")
    print("=" * 60)
    
    servicer = FaceDetectionServicer(model_path="yolov8n.pt", device="cpu")
    request = MockRequest(frame_data=b"invalid data")
    result = servicer.DetectFaces(request, None)
    
    print(f"  Success: {result['success']}")
    print(f"  Error: {result['error']}")
    
    assert result['success'] == False
    assert "Failed to decode" in result['error']
    print("  ✅ Test passed!\n")


if __name__ == "__main__":
    print("\n🔍 FACE DETECTION MICROSERVICE TESTS\n")
    
    try:
        test_health_check()
        test_face_detection_with_synthetic_image()
        test_face_detection_with_sample_face()
        test_invalid_image()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

