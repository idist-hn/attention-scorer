"""
Tests for Attention Scorer.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from src.core.attention_scorer import AttentionScorer
from src.models.detection import HeadPose, GazeInfo, BlinkInfo
from src.models.attention import AlertType


class TestAttentionScorer:
    @pytest.fixture
    def scorer(self):
        return AttentionScorer()
    
    def test_calculate_metrics_full_attention(self, scorer):
        """Test metrics calculation with full attention."""
        head_pose = HeadPose(yaw=0, pitch=0, roll=0)
        gaze = GazeInfo(gaze_x=0, gaze_y=0)
        blink = BlinkInfo(
            left_ear=0.3, right_ear=0.3, avg_ear=0.3,
            is_blinking=False, blink_rate=15, perclos=0.1
        )
        
        metrics = scorer.calculate(head_pose, gaze, blink, is_present=True)
        
        assert metrics.gaze_score == 1.0
        assert metrics.head_pose_score == 1.0
        assert metrics.presence_score == 1.0
        assert metrics.is_present is True
        assert metrics.is_looking_away is False
    
    def test_calculate_metrics_looking_away(self, scorer):
        """Test metrics when looking away."""
        head_pose = HeadPose(yaw=50, pitch=0, roll=0)  # Head turned > 45 degrees
        gaze = GazeInfo(gaze_x=0.5, gaze_y=0)
        blink = BlinkInfo(
            left_ear=0.3, right_ear=0.3, avg_ear=0.3,
            is_blinking=False, blink_rate=15, perclos=0.1
        )
        
        metrics = scorer.calculate(head_pose, gaze, blink, is_present=True)
        
        assert metrics.is_looking_away is True
        assert metrics.head_pose_score < 0.5
    
    def test_calculate_metrics_drowsy(self, scorer):
        """Test metrics when drowsy."""
        head_pose = HeadPose(yaw=0, pitch=0, roll=0)
        gaze = GazeInfo(gaze_x=0, gaze_y=0)
        blink = BlinkInfo(
            left_ear=0.15, right_ear=0.15, avg_ear=0.15,
            is_blinking=False, blink_rate=5, perclos=0.85  # High PERCLOS
        )
        
        metrics = scorer.calculate(head_pose, gaze, blink, is_present=True)
        
        assert metrics.is_drowsy is True
    
    def test_calculate_attention_score(self, scorer):
        """Test attention score calculation."""
        head_pose = HeadPose(yaw=0, pitch=0, roll=0)
        gaze = GazeInfo(gaze_x=0, gaze_y=0)
        blink = BlinkInfo(
            left_ear=0.3, right_ear=0.3, avg_ear=0.3,
            is_blinking=False, blink_rate=15, perclos=0.1
        )
        
        metrics = scorer.calculate(head_pose, gaze, blink, is_present=True)
        score = scorer.calculate_attention_score(metrics)
        
        # With full attention, score should be high
        assert score >= 80
    
    def test_calculate_attention_score_partial(self, scorer):
        """Test attention score with partial attention."""
        head_pose = HeadPose(yaw=20, pitch=15, roll=0)  # Slightly turned
        gaze = GazeInfo(gaze_x=0.2, gaze_y=0.1)  # Slightly off-center
        blink = BlinkInfo(
            left_ear=0.25, right_ear=0.25, avg_ear=0.25,
            is_blinking=False, blink_rate=15, perclos=0.2
        )
        
        metrics = scorer.calculate(head_pose, gaze, blink, is_present=True)
        score = scorer.calculate_attention_score(metrics)
        
        # Should be moderate attention
        assert 40 <= score <= 80
    
    def test_calculate_attention_score_low(self, scorer):
        """Test attention score with low attention."""
        head_pose = HeadPose(yaw=40, pitch=30, roll=0)  # Significantly turned
        gaze = GazeInfo(gaze_x=0.6, gaze_y=0.4)  # Looking away
        blink = BlinkInfo(
            left_ear=0.18, right_ear=0.18, avg_ear=0.18,
            is_blinking=False, blink_rate=5, perclos=0.6
        )
        
        metrics = scorer.calculate(head_pose, gaze, blink, is_present=True)
        score = scorer.calculate_attention_score(metrics)
        
        # Should be low attention
        assert score < 50
    
    def test_calculate_attention_not_present(self, scorer):
        """Test attention score when not present."""
        metrics = scorer.calculate(None, None, None, is_present=False)
        score = scorer.calculate_attention_score(metrics)
        
        # Only presence weight should contribute
        assert score < 20
    
    def test_gaze_score_center(self, scorer):
        """Test gaze score when looking at center."""
        gaze = GazeInfo(gaze_x=0, gaze_y=0)
        score = scorer._calculate_gaze_score(gaze)
        assert score == 1.0
    
    def test_gaze_score_edge(self, scorer):
        """Test gaze score when looking at edge."""
        gaze = GazeInfo(gaze_x=0.3, gaze_y=0)  # At threshold
        score = scorer._calculate_gaze_score(gaze)
        assert score == pytest.approx(0.0, abs=0.1)
    
    def test_head_pose_score_straight(self, scorer):
        """Test head pose score when looking straight."""
        pose = HeadPose(yaw=0, pitch=0, roll=0)
        score = scorer._calculate_head_pose_score(pose)
        assert score == 1.0
    
    def test_head_pose_score_turned(self, scorer):
        """Test head pose score when head is turned."""
        pose = HeadPose(yaw=30, pitch=25, roll=0)  # At thresholds
        score = scorer._calculate_head_pose_score(pose)
        assert score == pytest.approx(0.0, abs=0.1)


class TestAlertChecking:
    @pytest.fixture
    def scorer(self):
        return AttentionScorer()
    
    def test_no_alerts_high_attention(self, scorer):
        """Test no alerts with high attention."""
        from src.models.attention import AttentionMetrics
        
        metrics = AttentionMetrics(
            gaze_score=0.9, head_pose_score=0.9,
            eye_openness_score=0.9, presence_score=1.0,
            head_yaw=0, head_pitch=0, head_roll=0,
            eye_aspect_ratio=0.3, blink_rate=15, perclos=0.1,
            gaze_x=0, gaze_y=0,
            is_present=True, is_looking_away=False, is_drowsy=False
        )
        
        alerts = scorer.check_alerts(1, metrics, 90.0)
        assert len(alerts) == 0

