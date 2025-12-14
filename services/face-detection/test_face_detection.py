"""
Unit tests for Face Detection Service
"""
import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from main import FaceDetectionServicer


@pytest.fixture
def servicer():
    """Create a FaceDetectionServicer instance."""
    return FaceDetectionServicer()


@pytest.fixture
def test_frame_with_face():
    """Create a test frame with a face-like pattern."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)  # Gray background
    # Draw face-like circle
    cv2.circle(img, (320, 240), 100, (180, 150, 130), -1)
    # Draw eyes
    cv2.circle(img, (290, 220), 15, (50, 50, 50), -1)
    cv2.circle(img, (350, 220), 15, (50, 50, 50), -1)
    # Draw mouth
    cv2.ellipse(img, (320, 280), (30, 15), 0, 0, 180, (100, 80, 80), 2)
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


@pytest.fixture
def test_frame_empty():
    """Create an empty test frame."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


class MockRequest:
    """Mock gRPC request object."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestFaceDetectionServicer:
    """Tests for FaceDetectionServicer."""

    def test_detect_faces_returns_dict(self, servicer, test_frame_with_face):
        """Test that DetectFaces returns a dictionary."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-1")
        result = servicer.DetectFaces(request, None)
        assert isinstance(result, dict)

    def test_detect_faces_has_required_keys(self, servicer, test_frame_with_face):
        """Test that result has required keys."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-2")
        result = servicer.DetectFaces(request, None)
        assert 'success' in result
        assert 'faces' in result
        assert 'processing_time_ms' in result

    def test_detect_faces_success_flag(self, servicer, test_frame_with_face):
        """Test that success flag is True for valid input."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-3")
        result = servicer.DetectFaces(request, None)
        assert result['success'] == True

    def test_detect_faces_empty_frame(self, servicer, test_frame_empty):
        """Test detection on empty frame."""
        request = MockRequest(frame_data=test_frame_empty, request_id="test-4")
        result = servicer.DetectFaces(request, None)
        assert result['success'] == True
        assert isinstance(result['faces'], list)

    def test_detect_faces_invalid_data(self, servicer):
        """Test detection with invalid data."""
        request = MockRequest(frame_data=b"invalid", request_id="test-5")
        result = servicer.DetectFaces(request, None)
        assert result['success'] == False

    def test_processing_time_positive(self, servicer, test_frame_with_face):
        """Test that processing time is positive."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-6")
        result = servicer.DetectFaces(request, None)
        assert result['processing_time_ms'] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

