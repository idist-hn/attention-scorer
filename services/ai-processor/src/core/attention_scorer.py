"""
Attention Score Calculator Module.

This module combines all detection results to calculate a comprehensive
attention score for each participant.
"""

import numpy as np
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from ..config import AttentionConfig, settings
from ..models.detection import Face, HeadPose, GazeInfo, BlinkInfo
from ..models.attention import (
    AttentionMetrics, 
    AttentionResult, 
    Alert, 
    AlertType, 
    AlertSeverity
)


@dataclass
class AlertState:
    """State for alert tracking per participant."""
    low_attention_start: Optional[datetime] = None
    looking_away_start: Optional[datetime] = None
    drowsy_start: Optional[datetime] = None
    absent_start: Optional[datetime] = None


class AttentionScorer:
    """
    Calculates attention scores from all detection components.
    
    Combines:
    - Gaze direction score
    - Head pose score
    - Eye openness score
    - Presence score
    
    Into a weighted attention score.
    """
    
    def __init__(self, config: Optional[AttentionConfig] = None):
        """
        Initialize attention scorer.
        
        Args:
            config: Attention scoring configuration
        """
        self.config = config or settings.attention
        self._alert_states: dict[int, AlertState] = defaultdict(AlertState)
    
    def calculate(
        self,
        head_pose: Optional[HeadPose],
        gaze: Optional[GazeInfo],
        blink: Optional[BlinkInfo],
        is_present: bool = True
    ) -> AttentionMetrics:
        """
        Calculate attention metrics.
        
        Args:
            head_pose: Head pose estimation result
            gaze: Gaze tracking result
            blink: Blink detection result
            is_present: Whether face is detected
            
        Returns:
            AttentionMetrics with individual scores and flags
        """
        # Calculate individual scores
        gaze_score = self._calculate_gaze_score(gaze) if gaze else 0.0
        head_pose_score = self._calculate_head_pose_score(head_pose) if head_pose else 0.0
        eye_openness_score = self._calculate_eye_openness_score(blink) if blink else 0.0
        presence_score = 1.0 if is_present else 0.0
        
        # Extract raw measurements
        head_yaw = head_pose.yaw if head_pose else 0.0
        head_pitch = head_pose.pitch if head_pose else 0.0
        head_roll = head_pose.roll if head_pose else 0.0
        
        ear = blink.avg_ear if blink else 0.0
        blink_rate = blink.blink_rate if blink else 0.0
        perclos = blink.perclos if blink else 0.0
        
        gaze_x = gaze.gaze_x if gaze else 0.0
        gaze_y = gaze.gaze_y if gaze else 0.0
        
        # Determine flags
        is_looking_away = self._is_looking_away(head_pose)
        is_drowsy = self._is_drowsy(blink)
        
        return AttentionMetrics(
            gaze_score=gaze_score,
            head_pose_score=head_pose_score,
            eye_openness_score=eye_openness_score,
            presence_score=presence_score,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            head_roll=head_roll,
            eye_aspect_ratio=ear,
            blink_rate=blink_rate,
            perclos=perclos,
            gaze_x=gaze_x,
            gaze_y=gaze_y,
            is_present=is_present,
            is_looking_away=is_looking_away,
            is_drowsy=is_drowsy
        )
    
    def calculate_attention_score(self, metrics: AttentionMetrics) -> float:
        """
        Calculate final attention score (0-100).
        
        Args:
            metrics: AttentionMetrics with individual scores
            
        Returns:
            Attention score from 0 to 100
        """
        weighted_score = (
            self.config.gaze_weight * metrics.gaze_score +
            self.config.head_pose_weight * metrics.head_pose_score +
            self.config.eye_openness_weight * metrics.eye_openness_score +
            self.config.presence_weight * metrics.presence_score
        )
        
        return round(weighted_score * 100, 2)
    
    def process_face(self, face: Face, track_id: int) -> AttentionResult:
        """
        Process a complete face detection to attention result.
        
        Args:
            face: Face object with all detection results
            track_id: Tracking ID for the face
            
        Returns:
            AttentionResult with score and metrics
        """
        is_present = face.landmarks is not None
        
        metrics = self.calculate(
            head_pose=face.head_pose,
            gaze=face.gaze,
            blink=face.blink,
            is_present=is_present
        )
        
        attention_score = self.calculate_attention_score(metrics)
        
        return AttentionResult(
            track_id=track_id,
            attention_score=attention_score,
            metrics=metrics,
            bbox_x=face.bbox.x,
            bbox_y=face.bbox.y,
            bbox_width=face.bbox.width,
            bbox_height=face.bbox.height,
            timestamp=datetime.now()
        )
    
    def check_alerts(
        self, 
        track_id: int, 
        metrics: AttentionMetrics,
        attention_score: float
    ) -> list[Alert]:
        """
        Check if any alert conditions are met.
        
        Args:
            track_id: Track ID
            metrics: Current attention metrics
            attention_score: Current attention score
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        now = datetime.now()
        state = self._alert_states[track_id]
        
        # Check low attention
        alert = self._check_low_attention(track_id, attention_score, now, state)
        if alert:
            alerts.append(alert)
        
        # Check looking away
        alert = self._check_looking_away(track_id, metrics, now, state)
        if alert:
            alerts.append(alert)
        
        # Check drowsiness
        alert = self._check_drowsiness(track_id, metrics, now, state)
        if alert:
            alerts.append(alert)
        
        return alerts
    
    def _calculate_gaze_score(self, gaze: GazeInfo) -> float:
        """Calculate gaze-based attention score."""
        distance = np.sqrt(gaze.gaze_x ** 2 + gaze.gaze_y ** 2)
        score = 1.0 - min(distance / self.config.gaze_threshold, 1.0)
        return max(0.0, score)
    
    def _calculate_head_pose_score(self, head_pose: HeadPose) -> float:
        """Calculate head pose-based attention score."""
        yaw_penalty = min(abs(head_pose.yaw) / self.config.head_yaw_threshold, 1.0)
        pitch_penalty = min(abs(head_pose.pitch) / self.config.head_pitch_threshold, 1.0)
        score = 1.0 - (yaw_penalty * 0.6 + pitch_penalty * 0.4)
        return max(0.0, score)
    
    def _calculate_eye_openness_score(self, blink: BlinkInfo) -> float:
        """Calculate eye openness score."""
        if blink.avg_ear <= 0:
            return 0.0
        
        normalized = min(blink.avg_ear / self.config.ear_threshold, 1.0)
        
        # Penalize high PERCLOS
        if blink.perclos > 0.5:
            normalized *= (1.0 - blink.perclos)
        
        return normalized
    
    def _is_looking_away(self, head_pose: Optional[HeadPose]) -> bool:
        """Check if person is looking away."""
        if head_pose is None:
            return False
        return abs(head_pose.yaw) > self.config.looking_away_yaw
    
    def _is_drowsy(self, blink: Optional[BlinkInfo]) -> bool:
        """Check if person shows drowsiness signs."""
        if blink is None:
            return False
        return blink.perclos > self.config.drowsy_perclos

    def _check_low_attention(
        self,
        track_id: int,
        score: float,
        now: datetime,
        state: AlertState
    ) -> Optional[Alert]:
        """Check for low attention alert."""
        threshold = self.config.not_attentive_score * 100

        if score < threshold:
            if state.low_attention_start is None:
                state.low_attention_start = now
            else:
                duration = (now - state.low_attention_start).total_seconds()
                if duration >= self.config.not_attentive_duration:
                    return Alert(
                        alert_type=AlertType.NOT_ATTENTIVE,
                        severity=AlertSeverity.WARNING,
                        track_id=track_id,
                        duration_seconds=duration
                    )
        else:
            state.low_attention_start = None

        return None

    def _check_looking_away(
        self,
        track_id: int,
        metrics: AttentionMetrics,
        now: datetime,
        state: AlertState
    ) -> Optional[Alert]:
        """Check for looking away alert."""
        if metrics.is_looking_away:
            if state.looking_away_start is None:
                state.looking_away_start = now
            else:
                duration = (now - state.looking_away_start).total_seconds()
                if duration >= self.config.looking_away_duration:
                    return Alert(
                        alert_type=AlertType.LOOKING_AWAY,
                        severity=AlertSeverity.INFO,
                        track_id=track_id,
                        duration_seconds=duration
                    )
        else:
            state.looking_away_start = None

        return None

    def _check_drowsiness(
        self,
        track_id: int,
        metrics: AttentionMetrics,
        now: datetime,
        state: AlertState
    ) -> Optional[Alert]:
        """Check for drowsiness alert."""
        if metrics.is_drowsy:
            if state.drowsy_start is None:
                state.drowsy_start = now
            else:
                duration = (now - state.drowsy_start).total_seconds()
                if duration >= self.config.drowsy_duration:
                    return Alert(
                        alert_type=AlertType.DROWSY,
                        severity=AlertSeverity.CRITICAL,
                        track_id=track_id,
                        duration_seconds=duration
                    )
        else:
            state.drowsy_start = None

        return None

    def reset_track(self, track_id: int) -> None:
        """Reset alert state for a track."""
        self._alert_states.pop(track_id, None)

    def reset_all(self) -> None:
        """Reset all alert states."""
        self._alert_states.clear()

