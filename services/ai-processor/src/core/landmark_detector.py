"""
Facial Landmark Detection Module using MediaPipe FaceMesh.

This module detects 478 facial landmarks for each face, which are used
for head pose estimation, gaze tracking, and blink detection.
"""

import numpy as np
from typing import Optional
import cv2
from loguru import logger

from ..config import LandmarkConfig, settings
from ..models.detection import Detection, FaceLandmarks, BoundingBox


class LandmarkDetector:
    """
    Facial landmark detector using MediaPipe FaceMesh.
    
    Features:
    - 478 3D facial landmarks
    - Iris landmarks for gaze tracking
    - GPU acceleration support
    """
    
    def __init__(self, config: Optional[LandmarkConfig] = None):
        """
        Initialize landmark detector.
        
        Args:
            config: Landmark detection configuration.
        """
        self.config = config or settings.landmark
        self._face_mesh = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize MediaPipe FaceMesh."""
        if self._initialized:
            return
        
        try:
            import mediapipe as mp
            
            logger.info("Initializing MediaPipe FaceMesh")
            
            self._mp_face_mesh = mp.solutions.face_mesh
            self._face_mesh = self._mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=self.config.max_num_faces,
                refine_landmarks=self.config.refine_landmarks,
                min_detection_confidence=self.config.min_detection_confidence,
                min_tracking_confidence=self.config.min_tracking_confidence
            )
            
            self._initialized = True
            logger.info("Landmark detector initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize landmark detector: {e}")
            raise
    
    def detect(
        self, 
        frame: np.ndarray, 
        detections: list[Detection]
    ) -> list[Optional[FaceLandmarks]]:
        """
        Detect landmarks for each face detection.
        
        Args:
            frame: BGR image as numpy array
            detections: List of face detections with bounding boxes
            
        Returns:
            List of FaceLandmarks (or None if detection failed)
        """
        if not self._initialized:
            self.initialize()
        
        if not detections:
            return []
        
        results = []
        h, w = frame.shape[:2]
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        for detection in detections:
            try:
                # Crop face region with padding
                landmarks = self._detect_single_face(
                    rgb_frame, detection.bbox, w, h
                )
                results.append(landmarks)
            except Exception as e:
                logger.warning(f"Landmark detection failed for face: {e}")
                results.append(None)
        
        return results
    
    def _detect_single_face(
        self,
        rgb_frame: np.ndarray,
        bbox: BoundingBox,
        frame_w: int,
        frame_h: int
    ) -> Optional[FaceLandmarks]:
        """Detect landmarks for a single face."""
        # Add padding to bbox
        padding = 0.2
        pad_x = int(bbox.width * padding)
        pad_y = int(bbox.height * padding)
        
        x1 = max(0, bbox.x - pad_x)
        y1 = max(0, bbox.y - pad_y)
        x2 = min(frame_w, bbox.x2 + pad_x)
        y2 = min(frame_h, bbox.y2 + pad_y)
        
        # Crop face region
        face_crop = rgb_frame[y1:y2, x1:x2]
        
        if face_crop.size == 0:
            return None
        
        # Run MediaPipe FaceMesh
        result = self._face_mesh.process(face_crop)
        
        if not result.multi_face_landmarks:
            return None
        
        # Get first face landmarks
        face_landmarks = result.multi_face_landmarks[0]
        
        # Convert to numpy array and transform back to original coordinates
        crop_h, crop_w = face_crop.shape[:2]
        landmarks = np.zeros((478, 3), dtype=np.float32)
        
        for i, lm in enumerate(face_landmarks.landmark):
            # Transform from crop coordinates to frame coordinates
            landmarks[i, 0] = lm.x * crop_w + x1
            landmarks[i, 1] = lm.y * crop_h + y1
            landmarks[i, 2] = lm.z * crop_w  # Z is relative to width
        
        return FaceLandmarks(landmarks=landmarks)
    
    def detect_full_frame(self, frame: np.ndarray) -> list[FaceLandmarks]:
        """
        Detect landmarks for all faces in the frame without prior detection.
        
        This is useful when face detection is skipped.
        
        Args:
            frame: BGR image as numpy array
            
        Returns:
            List of FaceLandmarks for all detected faces
        """
        if not self._initialized:
            self.initialize()
        
        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        result = self._face_mesh.process(rgb_frame)
        
        if not result.multi_face_landmarks:
            return []
        
        all_landmarks = []
        
        for face_landmarks in result.multi_face_landmarks:
            landmarks = np.zeros((478, 3), dtype=np.float32)
            
            for i, lm in enumerate(face_landmarks.landmark):
                landmarks[i, 0] = lm.x * w
                landmarks[i, 1] = lm.y * h
                landmarks[i, 2] = lm.z * w
            
            all_landmarks.append(FaceLandmarks(landmarks=landmarks))
        
        return all_landmarks
    
    def release(self) -> None:
        """Release resources."""
        if self._face_mesh:
            self._face_mesh.close()
        self._face_mesh = None
        self._initialized = False
        logger.info("Landmark detector released")

