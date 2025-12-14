"""
Unit tests for Blink Detection Service
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import BlinkDetectionServicer


@pytest.fixture
def servicer():
    """Create a BlinkDetectionServicer instance."""
    return BlinkDetectionServicer()


@pytest.fixture
def mock_landmarks_open_eyes():
    """Create mock landmarks with open eyes."""
    class MockLandmark:
        def __init__(self, x, y, z=0):
            self.x = x
            self.y = y
            self.z = z
    
    landmarks = []
    for i in range(478):
        landmarks.append(MockLandmark(0.5, 0.5, 0.0))
    
    # Left eye landmarks (open - high EAR)
    landmarks[159] = MockLandmark(0.4, 0.42, 0.0)  # Top
    landmarks[145] = MockLandmark(0.4, 0.48, 0.0)  # Bottom
    landmarks[33] = MockLandmark(0.35, 0.45, 0.0)  # Outer
    landmarks[133] = MockLandmark(0.45, 0.45, 0.0)  # Inner
    landmarks[158] = MockLandmark(0.38, 0.43, 0.0)
    landmarks[153] = MockLandmark(0.38, 0.47, 0.0)
    
    # Right eye landmarks (open - high EAR)
    landmarks[386] = MockLandmark(0.6, 0.42, 0.0)  # Top
    landmarks[374] = MockLandmark(0.6, 0.48, 0.0)  # Bottom
    landmarks[362] = MockLandmark(0.55, 0.45, 0.0)  # Inner
    landmarks[263] = MockLandmark(0.65, 0.45, 0.0)  # Outer
    landmarks[385] = MockLandmark(0.62, 0.43, 0.0)
    landmarks[380] = MockLandmark(0.62, 0.47, 0.0)
    
    return landmarks


@pytest.fixture
def mock_landmarks_closed_eyes():
    """Create mock landmarks with closed eyes."""
    class MockLandmark:
        def __init__(self, x, y, z=0):
            self.x = x
            self.y = y
            self.z = z
    
    landmarks = []
    for i in range(478):
        landmarks.append(MockLandmark(0.5, 0.5, 0.0))
    
    # Left eye landmarks (closed - low EAR)
    landmarks[159] = MockLandmark(0.4, 0.45, 0.0)  # Top
    landmarks[145] = MockLandmark(0.4, 0.46, 0.0)  # Bottom (close to top)
    landmarks[33] = MockLandmark(0.35, 0.45, 0.0)
    landmarks[133] = MockLandmark(0.45, 0.45, 0.0)
    landmarks[158] = MockLandmark(0.38, 0.455, 0.0)
    landmarks[153] = MockLandmark(0.38, 0.455, 0.0)
    
    # Right eye landmarks (closed - low EAR)
    landmarks[386] = MockLandmark(0.6, 0.45, 0.0)
    landmarks[374] = MockLandmark(0.6, 0.46, 0.0)
    landmarks[362] = MockLandmark(0.55, 0.45, 0.0)
    landmarks[263] = MockLandmark(0.65, 0.45, 0.0)
    landmarks[385] = MockLandmark(0.62, 0.455, 0.0)
    landmarks[380] = MockLandmark(0.62, 0.455, 0.0)
    
    return landmarks


class MockRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestBlinkDetectionServicer:
    """Tests for BlinkDetectionServicer."""

    def test_detect_blink_returns_dict(self, servicer, mock_landmarks_open_eyes):
        """Test that DetectBlink returns a dictionary."""
        request = MockRequest(request_id="test-1", landmarks=mock_landmarks_open_eyes)
        result = servicer.DetectBlink(request, None)
        assert isinstance(result, dict)

    def test_detect_blink_has_required_keys(self, servicer, mock_landmarks_open_eyes):
        """Test that result has required keys."""
        request = MockRequest(request_id="test-2", landmarks=mock_landmarks_open_eyes)
        result = servicer.DetectBlink(request, None)
        assert 'success' in result
        assert 'blink_info' in result
        assert 'processing_time_ms' in result

    def test_detect_blink_success(self, servicer, mock_landmarks_open_eyes):
        """Test successful blink detection."""
        request = MockRequest(request_id="test-3", landmarks=mock_landmarks_open_eyes)
        result = servicer.DetectBlink(request, None)
        assert result['success'] == True

    def test_blink_info_values(self, servicer, mock_landmarks_open_eyes):
        """Test that blink_info contains expected values."""
        request = MockRequest(request_id="test-4", landmarks=mock_landmarks_open_eyes)
        result = servicer.DetectBlink(request, None)
        if result['blink_info']:
            assert 'left_ear' in result['blink_info']
            assert 'right_ear' in result['blink_info']
            assert 'is_blinking' in result['blink_info']

    def test_empty_landmarks(self, servicer):
        """Test with empty landmarks."""
        request = MockRequest(request_id="test-5", landmarks=[])
        result = servicer.DetectBlink(request, None)
        assert result['success'] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

