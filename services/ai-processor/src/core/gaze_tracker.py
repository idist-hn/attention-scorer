"""
Eye Gaze Tracking Module.

This module estimates gaze direction using iris landmarks from MediaPipe FaceMesh.
"""

import numpy as np
from typing import Optional, Tuple
from loguru import logger

from ..models.detection import FaceLandmarks, GazeInfo


class GazeTracker:
    """
    Tracks eye gaze direction using iris landmarks.
    
    Uses the position of iris relative to eye corners to estimate
    where the person is looking.
    """
    
    def __init__(self, gaze_threshold: float = 0.3):
        """
        Initialize gaze tracker.
        
        Args:
            gaze_threshold: Threshold for "looking at center" detection
        """
        self.gaze_threshold = gaze_threshold
    
    def estimate(self, landmarks: FaceLandmarks) -> Optional[GazeInfo]:
        """
        Estimate gaze direction from facial landmarks.
        
        Args:
            landmarks: Facial landmarks including iris positions
            
        Returns:
            GazeInfo with normalized gaze coordinates
        """
        try:
            # Calculate gaze for both eyes
            left_gaze = self._estimate_single_eye_gaze(
                landmarks.left_eye,
                landmarks.left_iris
            )
            
            right_gaze = self._estimate_single_eye_gaze(
                landmarks.right_eye,
                landmarks.right_iris
            )
            
            if left_gaze is None and right_gaze is None:
                return None
            
            # Average both eyes (or use available one)
            if left_gaze is not None and right_gaze is not None:
                gaze_x = (left_gaze[0] + right_gaze[0]) / 2
                gaze_y = (left_gaze[1] + right_gaze[1]) / 2
            elif left_gaze is not None:
                gaze_x, gaze_y = left_gaze
            else:
                gaze_x, gaze_y = right_gaze
            
            return GazeInfo(gaze_x=gaze_x, gaze_y=gaze_y)
            
        except Exception as e:
            logger.warning(f"Gaze estimation failed: {e}")
            return None
    
    def _estimate_single_eye_gaze(
        self,
        eye_landmarks: np.ndarray,
        iris_landmarks: np.ndarray
    ) -> Optional[Tuple[float, float]]:
        """
        Estimate gaze for a single eye.
        
        Args:
            eye_landmarks: 6 landmarks defining eye corners and edges
            iris_landmarks: 5 landmarks defining iris position
            
        Returns:
            Tuple of (gaze_x, gaze_y) normalized to [-1, 1]
        """
        if len(eye_landmarks) < 6 or len(iris_landmarks) < 5:
            return None
        
        # Get eye corners (leftmost and rightmost points)
        # For left eye: indices 0 (outer) and 3 (inner)
        # For right eye: indices 0 (inner) and 3 (outer)
        eye_left = eye_landmarks[0, :2]
        eye_right = eye_landmarks[3, :2]
        
        # Get vertical points
        eye_top = eye_landmarks[1, :2]
        eye_bottom = eye_landmarks[5, :2]
        
        # Calculate eye dimensions
        eye_width = np.linalg.norm(eye_right - eye_left)
        eye_height = np.linalg.norm(eye_top - eye_bottom)
        
        if eye_width < 1 or eye_height < 1:
            return None
        
        # Get iris center
        iris_center = np.mean(iris_landmarks[:, :2], axis=0)
        
        # Calculate iris offset from eye center
        eye_center = (eye_left + eye_right) / 2
        iris_offset = iris_center - eye_center
        
        # Normalize to [-1, 1]
        gaze_x = (iris_offset[0] / (eye_width / 2))
        gaze_y = (iris_offset[1] / (eye_height / 2))
        
        # Clamp values
        gaze_x = np.clip(gaze_x, -1.0, 1.0)
        gaze_y = np.clip(gaze_y, -1.0, 1.0)
        
        return float(gaze_x), float(gaze_y)
    
    def calculate_gaze_score(self, gaze: GazeInfo) -> float:
        """
        Calculate attention score based on gaze direction.
        
        Args:
            gaze: GazeInfo with gaze_x and gaze_y
            
        Returns:
            Score from 0.0 to 1.0 (1.0 = looking at center)
        """
        # Calculate distance from center
        distance = np.sqrt(gaze.gaze_x ** 2 + gaze.gaze_y ** 2)
        
        # Convert to score (closer to center = higher score)
        score = 1.0 - min(distance / self.gaze_threshold, 1.0)
        
        return max(0.0, float(score))
    
    def is_looking_at_camera(
        self, 
        gaze: GazeInfo, 
        threshold: float = None
    ) -> bool:
        """
        Check if person is looking at camera/screen.
        
        Args:
            gaze: GazeInfo object
            threshold: Optional threshold override
            
        Returns:
            True if looking at camera
        """
        threshold = threshold or self.gaze_threshold
        distance = np.sqrt(gaze.gaze_x ** 2 + gaze.gaze_y ** 2)
        return distance < threshold


class GazeSmoother:
    """
    Smooths gaze values over time using exponential moving average.
    """
    
    def __init__(self, alpha: float = 0.3):
        """
        Initialize gaze smoother.
        
        Args:
            alpha: Smoothing factor (0-1). Higher = less smoothing.
        """
        self.alpha = alpha
        self._prev_gaze: Optional[GazeInfo] = None
    
    def smooth(self, gaze: GazeInfo) -> GazeInfo:
        """
        Apply smoothing to gaze values.
        
        Args:
            gaze: Current gaze estimation
            
        Returns:
            Smoothed gaze values
        """
        if self._prev_gaze is None:
            self._prev_gaze = gaze
            return gaze
        
        smoothed_x = self.alpha * gaze.gaze_x + (1 - self.alpha) * self._prev_gaze.gaze_x
        smoothed_y = self.alpha * gaze.gaze_y + (1 - self.alpha) * self._prev_gaze.gaze_y
        
        smoothed_gaze = GazeInfo(gaze_x=smoothed_x, gaze_y=smoothed_y)
        self._prev_gaze = smoothed_gaze
        
        return smoothed_gaze
    
    def reset(self) -> None:
        """Reset smoother state."""
        self._prev_gaze = None

