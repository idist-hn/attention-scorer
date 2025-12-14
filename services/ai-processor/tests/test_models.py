"""
Tests for data models.
"""

import pytest
import numpy as np
from datetime import datetime

from src.models.detection import (
    BoundingBox,
    Detection,
    TrackInfo,
    FaceLandmarks,
    HeadPose,
    GazeInfo,
    BlinkInfo,
    Face
)
from src.models.attention import (
    AttentionMetrics,
    AttentionResult,
    Alert,
    AlertType,
    AlertSeverity,
    FrameResult
)


class TestBoundingBox:
    def test_creation(self):
        bbox = BoundingBox(x=10, y=20, width=100, height=150)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 100
        assert bbox.height == 150
    
    def test_x2_y2(self):
        bbox = BoundingBox(x=10, y=20, width=100, height=150)
        assert bbox.x2 == 110
        assert bbox.y2 == 170
    
    def test_center(self):
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        assert bbox.center == (50, 50)
    
    def test_area(self):
        bbox = BoundingBox(x=0, y=0, width=10, height=20)
        assert bbox.area == 200
    
    def test_to_xyxy(self):
        bbox = BoundingBox(x=10, y=20, width=100, height=150)
        assert bbox.to_xyxy() == (10, 20, 110, 170)
    
    def test_to_xywh(self):
        bbox = BoundingBox(x=10, y=20, width=100, height=150)
        assert bbox.to_xywh() == (10, 20, 100, 150)


class TestDetection:
    def test_from_xyxy(self):
        det = Detection.from_xyxy(10, 20, 110, 170, confidence=0.95)
        assert det.bbox.x == 10
        assert det.bbox.y == 20
        assert det.bbox.width == 100
        assert det.bbox.height == 150
        assert det.confidence == 0.95


class TestHeadPose:
    def test_creation(self):
        pose = HeadPose(yaw=10.5, pitch=-5.2, roll=2.1)
        assert pose.yaw == 10.5
        assert pose.pitch == -5.2
        assert pose.roll == 2.1


class TestGazeInfo:
    def test_is_looking_center(self):
        gaze_center = GazeInfo(gaze_x=0.1, gaze_y=0.1)
        assert gaze_center.is_looking_center is True
        
        gaze_away = GazeInfo(gaze_x=0.5, gaze_y=0.1)
        assert gaze_away.is_looking_center is False


class TestBlinkInfo:
    def test_creation(self):
        blink = BlinkInfo(
            left_ear=0.28,
            right_ear=0.27,
            avg_ear=0.275,
            is_blinking=False,
            blink_rate=15.0,
            perclos=0.1
        )
        assert blink.avg_ear == 0.275
        assert blink.is_blinking is False


class TestAttentionMetrics:
    def test_creation(self):
        metrics = AttentionMetrics(
            gaze_score=0.8,
            head_pose_score=0.9,
            eye_openness_score=0.85,
            presence_score=1.0,
            head_yaw=5.0,
            head_pitch=-2.0,
            head_roll=1.0,
            eye_aspect_ratio=0.28,
            blink_rate=12.0,
            perclos=0.1,
            gaze_x=0.05,
            gaze_y=-0.02
        )
        assert metrics.gaze_score == 0.8
        assert metrics.is_present is True
        assert metrics.is_looking_away is False


class TestAttentionResult:
    def test_to_dict(self):
        result = AttentionResult(
            track_id=1,
            participant_id="user123",
            attention_score=85.5,
            bbox_x=10,
            bbox_y=20,
            bbox_width=100,
            bbox_height=150
        )
        
        data = result.to_dict()
        assert data["track_id"] == 1
        assert data["attention_score"] == 85.5
        assert data["bbox"]["x"] == 10


class TestAlert:
    def test_auto_message(self):
        alert = Alert(
            alert_type=AlertType.NOT_ATTENTIVE,
            severity=AlertSeverity.WARNING,
            track_id=1,
            duration_seconds=15.0
        )
        
        assert "15.0s" in alert.message
    
    def test_to_dict(self):
        alert = Alert(
            alert_type=AlertType.DROWSY,
            severity=AlertSeverity.CRITICAL,
            track_id=1,
            duration_seconds=5.0
        )
        
        data = alert.to_dict()
        assert data["alert_type"] == "drowsy"
        assert data["severity"] == "critical"


class TestFrameResult:
    def test_to_dict(self):
        result = FrameResult(
            frame_id=100,
            meeting_id="meeting123",
            timestamp=datetime.now(),
            attention_results=[],
            alerts=[],
            processing_time_ms=25.5
        )
        
        data = result.to_dict()
        assert data["frame_id"] == 100
        assert data["meeting_id"] == "meeting123"
        assert data["processing_time_ms"] == 25.5

