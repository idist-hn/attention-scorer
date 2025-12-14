"""
Head Pose Estimation Module.

This module estimates head orientation (yaw, pitch, roll) from facial landmarks
using the Perspective-n-Point (PnP) algorithm.
"""

import numpy as np
import cv2
from typing import Optional, Tuple
from loguru import logger

from ..models.detection import FaceLandmarks, HeadPose


class HeadPoseEstimator:
    """
    Estimates head pose from facial landmarks.
    
    Uses 6 key facial landmarks and a generic 3D face model
    to estimate head orientation via solvePnP.
    """
    
    # Generic 3D face model points (in mm, centered at nose)
    MODEL_POINTS = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left eye outer corner
        (225.0, 170.0, -135.0),      # Right eye outer corner
        (-150.0, -150.0, -125.0),    # Left mouth corner
        (150.0, -150.0, -125.0)      # Right mouth corner
    ], dtype=np.float64)
    
    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        """
        Initialize head pose estimator.
        
        Args:
            frame_width: Width of the video frame
            frame_height: Height of the video frame
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Camera matrix (assuming no lens distortion)
        self._camera_matrix = self._create_camera_matrix()
        self._dist_coeffs = np.zeros((4, 1), dtype=np.float64)
    
    def _create_camera_matrix(self) -> np.ndarray:
        """Create camera intrinsic matrix."""
        focal_length = self.frame_width
        center = (self.frame_width / 2, self.frame_height / 2)
        
        return np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
    
    def update_frame_size(self, width: int, height: int) -> None:
        """Update frame size and recalculate camera matrix."""
        if width != self.frame_width or height != self.frame_height:
            self.frame_width = width
            self.frame_height = height
            self._camera_matrix = self._create_camera_matrix()
    
    def estimate(self, landmarks: FaceLandmarks) -> Optional[HeadPose]:
        """
        Estimate head pose from facial landmarks.
        
        Args:
            landmarks: Facial landmarks from FaceMesh
            
        Returns:
            HeadPose with yaw, pitch, roll angles in degrees
        """
        try:
            # Get 6 key points for head pose
            image_points = self._get_image_points(landmarks)
            
            # Solve PnP
            success, rotation_vec, translation_vec = cv2.solvePnP(
                self.MODEL_POINTS,
                image_points,
                self._camera_matrix,
                self._dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
            
            if not success:
                return None
            
            # Convert rotation vector to Euler angles
            yaw, pitch, roll = self._rotation_vector_to_euler(rotation_vec)
            
            return HeadPose(
                yaw=float(yaw),
                pitch=float(pitch),
                roll=float(roll)
            )
            
        except Exception as e:
            logger.warning(f"Head pose estimation failed: {e}")
            return None
    
    def _get_image_points(self, landmarks: FaceLandmarks) -> np.ndarray:
        """Extract 6 key points from landmarks."""
        points = landmarks.head_pose_points[:, :2]  # Get x, y only
        return points.astype(np.float64)
    
    def _rotation_vector_to_euler(
        self, 
        rotation_vec: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        Convert rotation vector to Euler angles.
        
        Returns:
            Tuple of (yaw, pitch, roll) in degrees
        """
        # Convert rotation vector to rotation matrix
        rotation_mat, _ = cv2.Rodrigues(rotation_vec)
        
        # Calculate Euler angles from rotation matrix
        # Using the convention: yaw (Y), pitch (X), roll (Z)
        sy = np.sqrt(rotation_mat[0, 0] ** 2 + rotation_mat[1, 0] ** 2)
        
        singular = sy < 1e-6
        
        if not singular:
            pitch = np.arctan2(rotation_mat[2, 1], rotation_mat[2, 2])
            yaw = np.arctan2(-rotation_mat[2, 0], sy)
            roll = np.arctan2(rotation_mat[1, 0], rotation_mat[0, 0])
        else:
            pitch = np.arctan2(-rotation_mat[1, 2], rotation_mat[1, 1])
            yaw = np.arctan2(-rotation_mat[2, 0], sy)
            roll = 0
        
        # Convert to degrees
        yaw = np.degrees(yaw)
        pitch = np.degrees(pitch)
        roll = np.degrees(roll)
        
        return yaw, pitch, roll
    
    def calculate_head_pose_score(
        self, 
        head_pose: HeadPose,
        yaw_threshold: float = 30.0,
        pitch_threshold: float = 25.0
    ) -> float:
        """
        Calculate attention score based on head pose.
        
        Args:
            head_pose: HeadPose object with yaw, pitch, roll
            yaw_threshold: Maximum yaw angle for full attention
            pitch_threshold: Maximum pitch angle for full attention
            
        Returns:
            Score from 0.0 to 1.0
        """
        # Calculate penalties for head rotation
        yaw_penalty = min(abs(head_pose.yaw) / yaw_threshold, 1.0)
        pitch_penalty = min(abs(head_pose.pitch) / pitch_threshold, 1.0)
        
        # Weighted combination (yaw is more important for "looking away")
        score = 1.0 - (yaw_penalty * 0.6 + pitch_penalty * 0.4)
        
        return max(0.0, score)
    
    def is_looking_away(
        self, 
        head_pose: HeadPose, 
        yaw_threshold: float = 45.0
    ) -> bool:
        """
        Check if person is looking away from screen.
        
        Args:
            head_pose: HeadPose object
            yaw_threshold: Yaw angle threshold in degrees
            
        Returns:
            True if looking away
        """
        return abs(head_pose.yaw) > yaw_threshold

