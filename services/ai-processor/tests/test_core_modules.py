"""
Unit tests for core AI modules.
Tests run independently without importing the full package.
"""

import pytest
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import Optional


# ================== MOCK DATA CLASSES ==================

@dataclass
class MockHeadPose:
    yaw: float
    pitch: float
    roll: float


@dataclass
class MockGazeInfo:
    gaze_x: float
    gaze_y: float
    is_looking_at_camera: bool


@dataclass
class MockBlinkInfo:
    left_ear: float
    right_ear: float
    avg_ear: float
    is_blinking: bool
    blink_rate: float
    perclos: float


@dataclass
class MockAttentionScore:
    attention_score: float
    attention_level: str
    is_attentive: bool
    gaze_score: float
    head_pose_score: float
    eye_openness_score: float
    presence_score: float


# ================== STANDALONE FUNCTIONS TO TEST ==================

def calculate_ear(eye_landmarks: np.ndarray) -> float:
    """Calculate Eye Aspect Ratio."""
    if len(eye_landmarks) < 6:
        return 0.0
    
    v1 = np.linalg.norm(eye_landmarks[1, :2] - eye_landmarks[5, :2])
    v2 = np.linalg.norm(eye_landmarks[2, :2] - eye_landmarks[4, :2])
    h = np.linalg.norm(eye_landmarks[0, :2] - eye_landmarks[3, :2])
    
    if h < 1:
        return 0.0
    
    ear = (v1 + v2) / (2.0 * h)
    return float(ear)


def calculate_perclos(ear_history: deque, threshold: float = 0.25) -> float:
    """Calculate PERCLOS."""
    if len(ear_history) == 0:
        return 0.0
    
    closed_frames = sum(1 for ear in ear_history if ear < threshold)
    return closed_frames / len(ear_history)


def calculate_attention_score(
    gaze_score: float,
    head_pose_score: float,
    eye_openness_score: float,
    presence_score: float,
    weights: tuple = (0.35, 0.30, 0.20, 0.15)
) -> float:
    """Calculate weighted attention score."""
    gaze_w, head_w, eye_w, presence_w = weights
    
    # Clamp inputs to [0, 1]
    gaze_score = max(0, min(1, gaze_score))
    head_pose_score = max(0, min(1, head_pose_score))
    eye_openness_score = max(0, min(1, eye_openness_score))
    presence_score = max(0, min(1, presence_score))
    
    score = (
        gaze_w * gaze_score +
        head_w * head_pose_score +
        eye_w * eye_openness_score +
        presence_w * presence_score
    ) * 100
    
    return max(0, min(100, score))


def get_attention_level(score: float) -> str:
    """Get attention level from score."""
    if score >= 70:
        return 'high'
    elif score >= 50:
        return 'medium'
    elif score >= 30:
        return 'low'
    else:
        return 'very_low'


def calculate_head_pose_score(yaw: float, pitch: float, roll: float) -> float:
    """Calculate head pose score based on angles."""
    yaw_threshold = 30
    pitch_threshold = 20
    roll_threshold = 15
    
    yaw_score = max(0, 1 - abs(yaw) / yaw_threshold)
    pitch_score = max(0, 1 - abs(pitch) / pitch_threshold)
    roll_score = max(0, 1 - abs(roll) / roll_threshold)
    
    return (yaw_score + pitch_score + roll_score) / 3


def calculate_gaze_score(gaze_x: float, gaze_y: float) -> float:
    """Calculate gaze score from gaze direction."""
    distance = np.sqrt(gaze_x**2 + gaze_y**2)
    max_distance = np.sqrt(2)  # Max when both are 1
    score = 1 - (distance / max_distance)
    return max(0, min(1, score))


# ================== TESTS ==================

class TestEARCalculation:
    """Tests for Eye Aspect Ratio calculation."""

    def test_ear_open_eyes(self):
        """Open eyes should have high EAR."""
        eye_landmarks = np.array([
            [100, 100, 0],
            [110, 80, 0],
            [120, 80, 0],
            [130, 100, 0],
            [120, 120, 0],
            [110, 120, 0],
        ])

        ear = calculate_ear(eye_landmarks)
        assert ear > 0.5, f"Open eyes EAR should be > 0.5, got {ear}"

    def test_ear_closed_eyes(self):
        """Closed eyes should have low EAR."""
        eye_landmarks = np.array([
            [100, 100, 0],
            [110, 99, 0],
            [120, 99, 0],
            [130, 100, 0],
            [120, 101, 0],
            [110, 101, 0],
        ])

        ear = calculate_ear(eye_landmarks)
        assert ear < 0.2, f"Closed eyes EAR should be < 0.2, got {ear}"

    def test_ear_empty_landmarks(self):
        """Empty landmarks should return 0."""
        ear = calculate_ear(np.array([]))
        assert ear == 0.0


class TestPERCLOSCalculation:
    """Tests for PERCLOS calculation."""

    def test_perclos_all_open(self):
        """All open eyes should have 0 PERCLOS."""
        history = deque([0.35, 0.34, 0.36, 0.33, 0.35])
        perclos = calculate_perclos(history, threshold=0.25)
        assert perclos == 0.0

    def test_perclos_all_closed(self):
        """All closed eyes should have 1.0 PERCLOS."""
        history = deque([0.15, 0.14, 0.16, 0.13, 0.15])
        perclos = calculate_perclos(history, threshold=0.25)
        assert perclos == 1.0

    def test_perclos_half(self):
        """Half open/closed should have 0.5 PERCLOS."""
        history = deque([0.35, 0.15, 0.34, 0.14])
        perclos = calculate_perclos(history, threshold=0.25)
        assert perclos == 0.5

    def test_perclos_empty(self):
        """Empty history should return 0."""
        perclos = calculate_perclos(deque(), threshold=0.25)
        assert perclos == 0.0


class TestAttentionScoring:
    """Tests for attention score calculation."""

    def test_full_attention(self):
        """Full attention should score 100."""
        score = calculate_attention_score(1.0, 1.0, 1.0, 1.0)
        assert abs(score - 100.0) < 0.001

    def test_no_attention(self):
        """No attention should score 0."""
        score = calculate_attention_score(0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_partial_attention(self):
        """Partial attention should be proportional."""
        score = calculate_attention_score(0.5, 0.5, 0.5, 0.5)
        assert 45 <= score <= 55, f"Expected ~50, got {score}"

    def test_weighted_correctly(self):
        """Weights should be applied correctly."""
        # Only gaze score (weight 0.35)
        score = calculate_attention_score(1.0, 0.0, 0.0, 0.0)
        assert abs(score - 35.0) < 1.0

    def test_clamped_inputs(self):
        """Inputs should be clamped to [0, 1]."""
        score = calculate_attention_score(1.5, 1.5, 1.5, 1.5)
        assert score <= 100.0

        score = calculate_attention_score(-0.5, -0.5, -0.5, -0.5)
        assert score >= 0.0


class TestAttentionLevel:
    """Tests for attention level categorization."""

    def test_high_level(self):
        assert get_attention_level(90) == 'high'
        assert get_attention_level(70) == 'high'

    def test_medium_level(self):
        assert get_attention_level(60) == 'medium'
        assert get_attention_level(50) == 'medium'

    def test_low_level(self):
        assert get_attention_level(40) == 'low'
        assert get_attention_level(30) == 'low'

    def test_very_low_level(self):
        assert get_attention_level(20) == 'very_low'
        assert get_attention_level(0) == 'very_low'


class TestHeadPoseScore:
    """Tests for head pose scoring."""

    def test_front_facing(self):
        """Front facing should score high."""
        score = calculate_head_pose_score(0, 0, 0)
        assert score == 1.0

    def test_turned_away(self):
        """Turned away should score lower."""
        score = calculate_head_pose_score(45, 30, 20)
        assert score < 0.5

    def test_slight_turn(self):
        """Slight turn should still score reasonably."""
        score = calculate_head_pose_score(10, 5, 3)
        assert score > 0.7


class TestGazeScore:
    """Tests for gaze scoring."""

    def test_center_gaze(self):
        """Center gaze should score 1.0."""
        score = calculate_gaze_score(0, 0)
        assert score == 1.0

    def test_side_gaze(self):
        """Side gaze should score lower."""
        score = calculate_gaze_score(0.5, 0.5)
        assert score < 0.7

    def test_extreme_gaze(self):
        """Extreme gaze should score near 0."""
        score = calculate_gaze_score(1.0, 1.0)
        assert score < 0.3

