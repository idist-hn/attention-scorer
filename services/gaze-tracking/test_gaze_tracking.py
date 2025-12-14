"""
Unit tests for Gaze Tracking Service
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import GazeTrackingServicer


@pytest.fixture
def servicer():
    """Create a GazeTrackingServicer instance."""
    return GazeTrackingServicer()


@pytest.fixture
def mock_landmarks():
    """Create mock landmarks for testing."""
    class MockLandmark:
        def __init__(self, x, y, z=0):
            self.x = x
            self.y = y
            self.z = z
    
    landmarks = []
    for i in range(478):
        landmarks.append(MockLandmark(0.5, 0.5, 0.0))
    
    # Left eye landmarks (468-472)
    landmarks[468] = MockLandmark(0.4, 0.45, 0.0)  # Left iris center
    landmarks[469] = MockLandmark(0.39, 0.45, 0.0)
    landmarks[470] = MockLandmark(0.4, 0.44, 0.0)
    landmarks[471] = MockLandmark(0.41, 0.45, 0.0)
    landmarks[472] = MockLandmark(0.4, 0.46, 0.0)
    
    # Right eye landmarks (473-477)
    landmarks[473] = MockLandmark(0.6, 0.45, 0.0)  # Right iris center
    landmarks[474] = MockLandmark(0.59, 0.45, 0.0)
    landmarks[475] = MockLandmark(0.6, 0.44, 0.0)
    landmarks[476] = MockLandmark(0.61, 0.45, 0.0)
    landmarks[477] = MockLandmark(0.6, 0.46, 0.0)
    
    # Eye corners
    landmarks[33] = MockLandmark(0.35, 0.45, 0.0)  # Left outer
    landmarks[133] = MockLandmark(0.45, 0.45, 0.0)  # Left inner
    landmarks[362] = MockLandmark(0.55, 0.45, 0.0)  # Right inner
    landmarks[263] = MockLandmark(0.65, 0.45, 0.0)  # Right outer
    
    return landmarks


class MockRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestGazeTrackingServicer:
    """Tests for GazeTrackingServicer."""

    def test_estimate_gaze_returns_dict(self, servicer, mock_landmarks):
        """Test that EstimateGaze returns a dictionary."""
        request = MockRequest(request_id="test-1", landmarks=mock_landmarks)
        result = servicer.EstimateGaze(request, None)
        assert isinstance(result, dict)

    def test_estimate_gaze_has_required_keys(self, servicer, mock_landmarks):
        """Test that result has required keys."""
        request = MockRequest(request_id="test-2", landmarks=mock_landmarks)
        result = servicer.EstimateGaze(request, None)
        assert 'success' in result
        assert 'gaze' in result
        assert 'processing_time_ms' in result

    def test_estimate_gaze_success(self, servicer, mock_landmarks):
        """Test successful gaze estimation."""
        request = MockRequest(request_id="test-3", landmarks=mock_landmarks)
        result = servicer.EstimateGaze(request, None)
        assert result['success'] == True

    def test_gaze_values(self, servicer, mock_landmarks):
        """Test that gaze contains expected values."""
        request = MockRequest(request_id="test-4", landmarks=mock_landmarks)
        result = servicer.EstimateGaze(request, None)
        if result['gaze']:
            assert 'gaze_x' in result['gaze']
            assert 'gaze_y' in result['gaze']
            assert 'is_looking_at_camera' in result['gaze']

    def test_empty_landmarks(self, servicer):
        """Test with empty landmarks."""
        request = MockRequest(request_id="test-5", landmarks=[])
        result = servicer.EstimateGaze(request, None)
        assert result['success'] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

