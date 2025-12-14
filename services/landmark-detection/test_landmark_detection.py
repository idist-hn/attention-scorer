"""
Unit tests for Landmark Detection Service
"""
import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import LandmarkDetectionServicer


@pytest.fixture
def servicer():
    """Create a LandmarkDetectionServicer instance."""
    return LandmarkDetectionServicer()


@pytest.fixture
def test_frame_with_face():
    """Create a test frame with a face-like pattern."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)
    cv2.circle(img, (320, 240), 100, (180, 150, 130), -1)
    cv2.circle(img, (290, 220), 15, (50, 50, 50), -1)
    cv2.circle(img, (350, 220), 15, (50, 50, 50), -1)
    cv2.ellipse(img, (320, 280), (30, 15), 0, 0, 180, (100, 80, 80), 2)
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


class MockRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestLandmarkDetectionServicer:
    """Tests for LandmarkDetectionServicer."""

    def test_detect_landmarks_returns_dict(self, servicer, test_frame_with_face):
        """Test that DetectLandmarks returns a dictionary."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-1")
        result = servicer.DetectLandmarks(request, None)
        assert isinstance(result, dict)

    def test_detect_landmarks_has_required_keys(self, servicer, test_frame_with_face):
        """Test that result has required keys."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-2")
        result = servicer.DetectLandmarks(request, None)
        assert 'success' in result
        assert 'faces' in result
        assert 'processing_time_ms' in result

    def test_detect_landmarks_success(self, servicer, test_frame_with_face):
        """Test successful landmark detection."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-3")
        result = servicer.DetectLandmarks(request, None)
        assert result['success'] == True

    def test_landmarks_structure(self, servicer, test_frame_with_face):
        """Test that landmarks have correct structure."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-4")
        result = servicer.DetectLandmarks(request, None)
        if result['faces']:
            face = result['faces'][0]
            assert 'landmarks' in face
            assert 'face_index' in face
            # MediaPipe FaceMesh has 478 landmarks
            if face['landmarks']:
                landmark = face['landmarks'][0]
                assert 'x' in landmark
                assert 'y' in landmark
                assert 'z' in landmark

    def test_bbox_in_result(self, servicer, test_frame_with_face):
        """Test that bbox is included in result."""
        request = MockRequest(frame_data=test_frame_with_face, request_id="test-5")
        result = servicer.DetectLandmarks(request, None)
        if result['faces']:
            face = result['faces'][0]
            assert 'bbox' in face
            bbox = face['bbox']
            assert 'x1' in bbox
            assert 'y1' in bbox
            assert 'x2' in bbox
            assert 'y2' in bbox

    def test_invalid_data(self, servicer):
        """Test with invalid data."""
        request = MockRequest(frame_data=b"invalid", request_id="test-6")
        result = servicer.DetectLandmarks(request, None)
        assert result['success'] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

