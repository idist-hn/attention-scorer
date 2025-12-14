"""
Configuration management for AI Processor Service.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path


class FaceDetectionConfig(BaseSettings):
    """Face detection configuration."""
    model_path: str = Field(default="yolov8n.pt", description="Path to YOLOv8 model (auto-downloads)")
    conf_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    max_faces: int = Field(default=20, ge=1)
    input_size: tuple[int, int] = Field(default=(640, 640))
    device: str = Field(default="cpu", description="Device to use: cuda or cpu")


class TrackerConfig(BaseSettings):
    """ByteTrack configuration."""
    track_thresh: float = Field(default=0.5, ge=0.0, le=1.0)
    track_buffer: int = Field(default=30, ge=1)
    match_thresh: float = Field(default=0.8, ge=0.0, le=1.0)
    min_box_area: int = Field(default=100, ge=1)


class LandmarkConfig(BaseSettings):
    """MediaPipe FaceMesh configuration."""
    max_num_faces: int = Field(default=20, ge=1)
    refine_landmarks: bool = Field(default=True)
    min_detection_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    min_tracking_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class AttentionConfig(BaseSettings):
    """Attention scoring configuration."""
    # Weights for attention score calculation
    gaze_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    head_pose_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    eye_openness_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    presence_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    
    # Thresholds
    head_yaw_threshold: float = Field(default=30.0, description="Max yaw angle in degrees")
    head_pitch_threshold: float = Field(default=25.0, description="Max pitch angle in degrees")
    ear_threshold: float = Field(default=0.25, description="Eye Aspect Ratio threshold")
    gaze_threshold: float = Field(default=0.3, description="Gaze offset threshold")
    
    # Alert thresholds
    not_attentive_score: float = Field(default=0.3, description="Score below this triggers alert")
    not_attentive_duration: float = Field(default=10.0, description="Duration in seconds")
    looking_away_yaw: float = Field(default=45.0, description="Head yaw threshold for looking away")
    looking_away_duration: float = Field(default=5.0, description="Duration in seconds")
    drowsy_perclos: float = Field(default=0.8, description="PERCLOS threshold for drowsiness")
    drowsy_duration: float = Field(default=3.0, description="Duration in seconds")


class RedisConfig(BaseSettings):
    """Redis configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: Optional[str] = Field(default=None)
    
    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    """Main application settings."""
    
    # General
    app_name: str = Field(default="attention-ai-processor")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    # Paths
    models_dir: Path = Field(default=Path("models"))
    
    # Processing
    target_fps: int = Field(default=24, ge=1)
    batch_size: int = Field(default=1, ge=1)
    
    # Sub-configs
    face_detection: FaceDetectionConfig = Field(default_factory=FaceDetectionConfig)
    tracker: TrackerConfig = Field(default_factory=TrackerConfig)
    landmark: LandmarkConfig = Field(default_factory=LandmarkConfig)
    attention: AttentionConfig = Field(default_factory=AttentionConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    
    class Config:
        env_prefix = "ATTENTION_"
        env_nested_delimiter = "__"
        env_file = ".env"


# Global settings instance
settings = Settings()

