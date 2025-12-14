"""
Data models for attention detection.
"""

from .detection import Detection, Face, FaceLandmarks, TrackInfo
from .attention import AttentionMetrics, AttentionResult, AlertType, Alert

__all__ = [
    "Detection",
    "Face",
    "FaceLandmarks",
    "TrackInfo",
    "AttentionMetrics",
    "AttentionResult",
    "AlertType",
    "Alert",
]

