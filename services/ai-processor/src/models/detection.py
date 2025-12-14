"""
Detection data models.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class BoundingBox:
    """Bounding box for detected face."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def x2(self) -> int:
        return self.x + self.width
    
    @property
    def y2(self) -> int:
        return self.y + self.height
    
    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    def to_xyxy(self) -> tuple[int, int, int, int]:
        """Return as (x1, y1, x2, y2) format."""
        return (self.x, self.y, self.x2, self.y2)
    
    def to_xywh(self) -> tuple[int, int, int, int]:
        """Return as (x, y, width, height) format."""
        return (self.x, self.y, self.width, self.height)


@dataclass
class Detection:
    """Raw detection from face detector."""
    bbox: BoundingBox
    confidence: float
    keypoints: Optional[np.ndarray] = None  # 5 keypoints: 2 eyes, nose, 2 mouth corners
    
    @classmethod
    def from_xyxy(cls, x1: int, y1: int, x2: int, y2: int, confidence: float, 
                  keypoints: Optional[np.ndarray] = None) -> "Detection":
        """Create Detection from xyxy format."""
        bbox = BoundingBox(x=x1, y=y1, width=x2-x1, height=y2-y1)
        return cls(bbox=bbox, confidence=confidence, keypoints=keypoints)


@dataclass
class TrackInfo:
    """Tracking information for a face."""
    track_id: int
    is_confirmed: bool = True
    frames_since_update: int = 0
    hit_streak: int = 0
    age: int = 0


@dataclass
class FaceLandmarks:
    """Facial landmarks from MediaPipe FaceMesh."""
    # All 478 landmarks as numpy array (478, 3)
    landmarks: np.ndarray
    
    # Key landmark indices
    LEFT_EYE_INDICES: list[int] = field(default_factory=lambda: [362, 385, 387, 263, 373, 380])
    RIGHT_EYE_INDICES: list[int] = field(default_factory=lambda: [33, 160, 158, 133, 153, 144])
    LEFT_IRIS_INDICES: list[int] = field(default_factory=lambda: [468, 469, 470, 471, 472])
    RIGHT_IRIS_INDICES: list[int] = field(default_factory=lambda: [473, 474, 475, 476, 477])
    
    # Head pose landmarks
    NOSE_TIP: int = 1
    CHIN: int = 152
    LEFT_EYE_OUTER: int = 263
    RIGHT_EYE_OUTER: int = 33
    LEFT_MOUTH: int = 287
    RIGHT_MOUTH: int = 57
    
    @property
    def left_eye(self) -> np.ndarray:
        """Get left eye landmarks."""
        return self.landmarks[self.LEFT_EYE_INDICES]
    
    @property
    def right_eye(self) -> np.ndarray:
        """Get right eye landmarks."""
        return self.landmarks[self.RIGHT_EYE_INDICES]
    
    @property
    def left_iris(self) -> np.ndarray:
        """Get left iris landmarks."""
        return self.landmarks[self.LEFT_IRIS_INDICES]
    
    @property
    def right_iris(self) -> np.ndarray:
        """Get right iris landmarks."""
        return self.landmarks[self.RIGHT_IRIS_INDICES]
    
    @property
    def head_pose_points(self) -> np.ndarray:
        """Get 6 points for head pose estimation."""
        indices = [
            self.NOSE_TIP,
            self.CHIN,
            self.LEFT_EYE_OUTER,
            self.RIGHT_EYE_OUTER,
            self.LEFT_MOUTH,
            self.RIGHT_MOUTH
        ]
        return self.landmarks[indices]


@dataclass
class HeadPose:
    """Head pose angles."""
    yaw: float    # Left/right rotation (-90 to 90)
    pitch: float  # Up/down rotation (-90 to 90)
    roll: float   # Tilt (-90 to 90)


@dataclass
class GazeInfo:
    """Gaze information."""
    gaze_x: float  # Normalized gaze X (-1 to 1)
    gaze_y: float  # Normalized gaze Y (-1 to 1)
    
    @property
    def is_looking_center(self) -> bool:
        """Check if looking at center region."""
        return abs(self.gaze_x) < 0.3 and abs(self.gaze_y) < 0.3


@dataclass
class BlinkInfo:
    """Blink detection information."""
    left_ear: float   # Left Eye Aspect Ratio
    right_ear: float  # Right Eye Aspect Ratio
    avg_ear: float    # Average EAR
    is_blinking: bool
    blink_rate: float  # Blinks per minute
    perclos: float     # Percentage of eye closure


@dataclass
class Face:
    """Complete face information with all detection results."""
    detection: Detection
    track_info: Optional[TrackInfo] = None
    landmarks: Optional[FaceLandmarks] = None
    head_pose: Optional[HeadPose] = None
    gaze: Optional[GazeInfo] = None
    blink: Optional[BlinkInfo] = None
    
    @property
    def track_id(self) -> Optional[int]:
        """Get track ID if available."""
        return self.track_info.track_id if self.track_info else None
    
    @property
    def bbox(self) -> BoundingBox:
        """Get bounding box."""
        return self.detection.bbox

