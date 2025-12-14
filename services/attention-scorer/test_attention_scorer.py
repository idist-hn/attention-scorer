"""
Unit tests for Attention Scorer Service
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import AttentionScorerServicer


@pytest.fixture
def servicer():
    """Create an AttentionScorerServicer instance."""
    return AttentionScorerServicer()


class MockRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestAttentionScorerServicer:
    """Tests for AttentionScorerServicer."""

    def test_calculate_attention_returns_dict(self, servicer):
        """Test that CalculateAttention returns a dictionary."""
        request = MockRequest(
            request_id="test-1",
            gaze_x=0.0, gaze_y=0.0,
            yaw=0.0, pitch=0.0, roll=0.0,
            left_ear=0.35, right_ear=0.35,
            is_present=True
        )
        result = servicer.CalculateAttention(request, None)
        assert isinstance(result, dict)

    def test_calculate_attention_has_required_keys(self, servicer):
        """Test that result has required keys."""
        request = MockRequest(
            request_id="test-2",
            gaze_x=0.0, gaze_y=0.0,
            yaw=0.0, pitch=0.0, roll=0.0,
            left_ear=0.35, right_ear=0.35,
            is_present=True
        )
        result = servicer.CalculateAttention(request, None)
        assert 'success' in result
        assert 'attention' in result
        assert 'processing_time_ms' in result

    def test_calculate_attention_success(self, servicer):
        """Test successful attention calculation."""
        request = MockRequest(
            request_id="test-3",
            gaze_x=0.0, gaze_y=0.0,
            yaw=0.0, pitch=0.0, roll=0.0,
            left_ear=0.35, right_ear=0.35,
            is_present=True
        )
        result = servicer.CalculateAttention(request, None)
        assert result['success'] == True

    def test_attention_values(self, servicer):
        """Test that attention contains expected values."""
        request = MockRequest(
            request_id="test-4",
            gaze_x=0.0, gaze_y=0.0,
            yaw=0.0, pitch=0.0, roll=0.0,
            left_ear=0.35, right_ear=0.35,
            is_present=True
        )
        result = servicer.CalculateAttention(request, None)
        if result['attention']:
            assert 'score' in result['attention']
            assert 'level' in result['attention']

    def test_high_attention_score(self, servicer):
        """Test high attention score for attentive user."""
        request = MockRequest(
            request_id="test-5",
            gaze_x=0.0, gaze_y=0.0,  # Looking at camera
            yaw=0.0, pitch=0.0, roll=0.0,  # Facing forward
            left_ear=0.35, right_ear=0.35,  # Eyes open
            is_present=True
        )
        result = servicer.CalculateAttention(request, None)
        assert result['attention']['score'] >= 70

    def test_low_attention_looking_away(self, servicer):
        """Test lower attention when looking away."""
        request = MockRequest(
            request_id="test-6",
            gaze_x=0.5, gaze_y=0.5,  # Looking away
            yaw=45.0, pitch=0.0, roll=0.0,  # Head turned
            left_ear=0.35, right_ear=0.35,
            is_present=True
        )
        result = servicer.CalculateAttention(request, None)
        assert result['attention']['score'] < 70

    def test_not_present(self, servicer):
        """Test zero attention when not present."""
        request = MockRequest(
            request_id="test-7",
            gaze_x=0.0, gaze_y=0.0,
            yaw=0.0, pitch=0.0, roll=0.0,
            left_ear=0.35, right_ear=0.35,
            is_present=False
        )
        result = servicer.CalculateAttention(request, None)
        assert result['attention']['score'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

