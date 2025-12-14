"""
Attention-related data models.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class AlertType(str, Enum):
    """Types of attention alerts."""
    NOT_ATTENTIVE = "not_attentive"
    LOOKING_AWAY = "looking_away"
    DROWSY = "drowsy"
    ABSENT = "absent"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AttentionMetrics:
    """Individual attention metrics."""
    # Scores (0.0 - 1.0)
    gaze_score: float
    head_pose_score: float
    eye_openness_score: float
    presence_score: float
    
    # Raw measurements
    head_yaw: float
    head_pitch: float
    head_roll: float
    eye_aspect_ratio: float
    blink_rate: float
    perclos: float
    gaze_x: float
    gaze_y: float
    
    # Flags
    is_present: bool = True
    is_looking_away: bool = False
    is_drowsy: bool = False


@dataclass
class AttentionResult:
    """Complete attention result for a participant."""
    # Identification
    track_id: int
    attention_score: float  # 0-100

    # Optional fields
    participant_id: Optional[str] = None
    metrics: Optional[AttentionMetrics] = None

    # Bounding box for visualization
    bbox_x: int = 0
    bbox_y: int = 0
    bbox_width: int = 0
    bbox_height: int = 0

    # Timestamp
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "track_id": self.track_id,
            "participant_id": self.participant_id,
            "attention_score": self.attention_score,
            "bbox": {
                "x": self.bbox_x,
                "y": self.bbox_y,
                "width": self.bbox_width,
                "height": self.bbox_height
            },
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
        
        if self.metrics:
            result["metrics"] = {
                "gaze_score": self.metrics.gaze_score,
                "head_pose_score": self.metrics.head_pose_score,
                "eye_openness_score": self.metrics.eye_openness_score,
                "is_looking_away": self.metrics.is_looking_away,
                "is_drowsy": self.metrics.is_drowsy,
                "head_yaw": self.metrics.head_yaw,
                "head_pitch": self.metrics.head_pitch,
                "perclos": self.metrics.perclos
            }
        
        return result


@dataclass
class Alert:
    """Attention alert."""
    alert_type: AlertType
    severity: AlertSeverity
    track_id: int
    participant_id: Optional[str] = None
    message: str = ""
    triggered_at: datetime = None
    duration_seconds: float = 0.0
    
    def __post_init__(self):
        if self.triggered_at is None:
            self.triggered_at = datetime.now()
        
        if not self.message:
            self.message = self._generate_message()
    
    def _generate_message(self) -> str:
        """Generate alert message based on type."""
        messages = {
            AlertType.NOT_ATTENTIVE: f"Attention score below threshold for {self.duration_seconds:.1f}s",
            AlertType.LOOKING_AWAY: f"Looking away from screen for {self.duration_seconds:.1f}s",
            AlertType.DROWSY: f"Signs of drowsiness detected for {self.duration_seconds:.1f}s",
            AlertType.ABSENT: "Participant not visible in frame"
        }
        return messages.get(self.alert_type, "Unknown alert")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "track_id": self.track_id,
            "participant_id": self.participant_id,
            "message": self.message,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "duration_seconds": self.duration_seconds
        }


@dataclass
class FrameResult:
    """Result of processing a single frame."""
    frame_id: int
    meeting_id: str
    timestamp: datetime
    attention_results: list[AttentionResult]
    alerts: list[Alert]
    processing_time_ms: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "frame_id": self.frame_id,
            "meeting_id": self.meeting_id,
            "timestamp": self.timestamp.isoformat(),
            "participants": [r.to_dict() for r in self.attention_results],
            "alerts": [a.to_dict() for a in self.alerts],
            "processing_time_ms": self.processing_time_ms
        }

