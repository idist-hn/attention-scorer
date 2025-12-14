"""
Visualization utilities for attention detection.
"""

import cv2
import numpy as np
from typing import Optional

from ..models.attention import AttentionResult, FrameResult


class Visualizer:
    """
    Draws attention detection results on video frames.
    """
    
    # Color scheme
    COLORS = {
        "high_attention": (0, 255, 0),      # Green
        "medium_attention": (0, 255, 255),  # Yellow
        "low_attention": (0, 0, 255),       # Red
        "text": (255, 255, 255),            # White
        "background": (0, 0, 0),            # Black
    }
    
    def __init__(self, font_scale: float = 0.6, thickness: int = 2):
        """
        Initialize visualizer.
        
        Args:
            font_scale: Font size for text
            thickness: Line thickness
        """
        self.font_scale = font_scale
        self.thickness = thickness
        self.font = cv2.FONT_HERSHEY_SIMPLEX
    
    def draw_results(
        self, 
        frame: np.ndarray, 
        result: FrameResult,
        show_metrics: bool = True
    ) -> np.ndarray:
        """
        Draw all attention results on frame.
        
        Args:
            frame: Input frame
            result: FrameResult with attention data
            show_metrics: Whether to show detailed metrics
            
        Returns:
            Frame with visualizations
        """
        output = frame.copy()
        
        for attention in result.attention_results:
            self._draw_face_result(output, attention, show_metrics)
        
        # Draw FPS and processing time
        self._draw_info(output, result)
        
        return output
    
    def _draw_face_result(
        self, 
        frame: np.ndarray, 
        result: AttentionResult,
        show_metrics: bool
    ) -> None:
        """Draw attention result for a single face."""
        # Determine color based on attention score
        color = self._get_attention_color(result.attention_score)
        
        # Draw bounding box
        x, y = result.bbox_x, result.bbox_y
        w, h = result.bbox_width, result.bbox_height
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, self.thickness)
        
        # Draw attention score
        score_text = f"ID:{result.track_id} | {result.attention_score:.0f}%"
        self._draw_label(frame, score_text, x, y - 10, color)
        
        # Draw additional metrics if enabled
        if show_metrics and result.metrics:
            self._draw_metrics(frame, result, x, y + h + 20)
    
    def _draw_label(
        self, 
        frame: np.ndarray, 
        text: str, 
        x: int, 
        y: int,
        color: tuple
    ) -> None:
        """Draw text label with background."""
        (text_w, text_h), _ = cv2.getTextSize(
            text, self.font, self.font_scale, self.thickness
        )
        
        # Draw background
        cv2.rectangle(
            frame, 
            (x, y - text_h - 5), 
            (x + text_w + 5, y + 5), 
            self.COLORS["background"], 
            -1
        )
        
        # Draw text
        cv2.putText(
            frame, text, (x + 2, y),
            self.font, self.font_scale, color, self.thickness
        )
    
    def _draw_metrics(
        self, 
        frame: np.ndarray, 
        result: AttentionResult,
        x: int, 
        y: int
    ) -> None:
        """Draw detailed metrics."""
        metrics = result.metrics
        if not metrics:
            return
        
        texts = [
            f"Gaze: {metrics.gaze_score:.2f}",
            f"Head: {metrics.head_pose_score:.2f}",
            f"Eyes: {metrics.eye_openness_score:.2f}",
        ]
        
        # Add flags
        flags = []
        if metrics.is_looking_away:
            flags.append("AWAY")
        if metrics.is_drowsy:
            flags.append("DROWSY")
        if flags:
            texts.append(" ".join(flags))
        
        for i, text in enumerate(texts):
            cv2.putText(
                frame, text, (x, y + i * 18),
                self.font, 0.4, self.COLORS["text"], 1
            )
    
    def _draw_info(self, frame: np.ndarray, result: FrameResult) -> None:
        """Draw frame info (FPS, processing time)."""
        fps = 1000 / result.processing_time_ms if result.processing_time_ms > 0 else 0
        
        info_text = f"FPS: {fps:.1f} | Proc: {result.processing_time_ms:.1f}ms | Faces: {len(result.attention_results)}"
        
        h, w = frame.shape[:2]
        cv2.putText(
            frame, info_text, (10, h - 20),
            self.font, 0.5, self.COLORS["text"], 1
        )
        
        # Draw alerts if any
        if result.alerts:
            alert_text = f"ALERTS: {len(result.alerts)}"
            cv2.putText(
                frame, alert_text, (10, 30),
                self.font, 0.7, self.COLORS["low_attention"], 2
            )
    
    def _get_attention_color(self, score: float) -> tuple:
        """Get color based on attention score."""
        if score >= 70:
            return self.COLORS["high_attention"]
        elif score >= 40:
            return self.COLORS["medium_attention"]
        else:
            return self.COLORS["low_attention"]

