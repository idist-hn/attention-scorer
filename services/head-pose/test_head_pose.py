"""
Unit tests for Head Pose Service
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import HeadPoseServicer


@pytest.fixture
def servicer():
    """Create a HeadPoseServicer instance."""
    return HeadPoseServicer()


@pytest.fixture
def mock_landmarks():
    """Create mock landmarks for testing."""
    class MockLandmark:
        def __init__(self, x, y, z=0):
            self.x = x
            self.y = y
            self.z = z
    
    # Create 478 landmarks (MediaPipe FaceMesh)
    landmarks = []
    for i in range(478):
        landmarks.append(MockLandmark(0.5 + (i % 10) * 0.01, 0.5 + (i // 10) * 0.01, 0.0))
    
    # Set key landmarks for head pose estimation
    # Nose tip (1)
    landmarks[1] = MockLandmark(0.5, 0.5, 0.0)
    # Chin (152)
    landmarks[152] = MockLandmark(0.5, 0.7, 0.0)
    # Left eye corner (33)
    landmarks[33] = MockLandmark(0.4, 0.45, 0.0)
    # Right eye corner (263)
    landmarks[263] = MockLandmark(0.6, 0.45, 0.0)
    # Left mouth corner (61)
    landmarks[61] = MockLandmark(0.45, 0.6, 0.0)
    # Right mouth corner (291)
    landmarks[291] = MockLandmark(0.55, 0.6, 0.0)
    
    return landmarks


class MockRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestHeadPoseServicer:
    """Tests for HeadPoseServicer."""

    def test_estimate_pose_returns_dict(self, servicer, mock_landmarks):
        """Test that EstimatePose returns a dictionary."""
        request = MockRequest(
            request_id="test-1",
            landmarks=mock_landmarks,
            frame_width=640,
            frame_height=480
        )
        result = servicer.EstimatePose(request, None)
        assert isinstance(result, dict)

    def test_estimate_pose_has_required_keys(self, servicer, mock_landmarks):
        """Test that result has required keys."""
        request = MockRequest(
            request_id="test-2",
            landmarks=mock_landmarks,
            frame_width=640,
            frame_height=480
        )
        result = servicer.EstimatePose(request, None)
        assert 'success' in result
        assert 'pose' in result
        assert 'processing_time_ms' in result

    def test_estimate_pose_success(self, servicer, mock_landmarks):
        """Test successful pose estimation."""
        request = MockRequest(
            request_id="test-3",
            landmarks=mock_landmarks,
            frame_width=640,
            frame_height=480
        )
        result = servicer.EstimatePose(request, None)
        assert result['success'] == True

    def test_pose_angles(self, servicer, mock_landmarks):
        """Test that pose contains yaw, pitch, roll."""
        request = MockRequest(
            request_id="test-4",
            landmarks=mock_landmarks,
            frame_width=640,
            frame_height=480
        )
        result = servicer.EstimatePose(request, None)
        if result['pose']:
            assert 'yaw' in result['pose']
            assert 'pitch' in result['pose']
            assert 'roll' in result['pose']

    def test_empty_landmarks(self, servicer):
        """Test with empty landmarks."""
        request = MockRequest(
            request_id="test-5",
            landmarks=[],
            frame_width=640,
            frame_height=480
        )
        result = servicer.EstimatePose(request, None)
        assert result['success'] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

