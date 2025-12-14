"""
Face Detection Module using YOLOv8-face.

This module provides GPU-accelerated face detection with support for
multiple faces in a single frame.
"""

import numpy as np
from typing import Optional
from loguru import logger

from ..config import FaceDetectionConfig, settings
from ..models.detection import Detection, BoundingBox


class FaceDetector:
    """
    Face detector using YOLOv8-face model.
    
    Features:
    - GPU acceleration with CUDA
    - Multi-face detection
    - Configurable confidence threshold
    - Returns bounding boxes and 5 keypoints
    """
    
    def __init__(self, config: Optional[FaceDetectionConfig] = None):
        """
        Initialize face detector.
        
        Args:
            config: Face detection configuration. Uses default if not provided.
        """
        self.config = config or settings.face_detection
        self._model = None
        self._initialized = False
        
    def initialize(self) -> None:
        """Load and initialize the model."""
        if self._initialized:
            return
            
        try:
            from ultralytics import YOLO
            
            logger.info(f"Loading face detection model: {self.config.model_path}")
            logger.info(f"Using device: {self.config.device}")
            
            self._model = YOLO(self.config.model_path)
            
            # Warm up the model
            dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model.predict(
                dummy_input,
                device=self.config.device,
                verbose=False
            )
            
            self._initialized = True
            logger.info("Face detector initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize face detector: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> list[Detection]:
        """
        Detect faces in a frame.
        
        Args:
            frame: BGR image as numpy array (H, W, 3)
            
        Returns:
            List of Detection objects containing bounding boxes and keypoints
        """
        if not self._initialized:
            self.initialize()
        
        detections = []
        
        try:
            # Run inference
            results = self._model.predict(
                frame,
                conf=self.config.conf_threshold,
                iou=self.config.iou_threshold,
                max_det=self.config.max_faces,
                device=self.config.device,
                verbose=False
            )
            
            if not results or len(results) == 0:
                return detections
            
            result = results[0]
            
            # Extract detections
            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()
                
                # Get keypoints if available
                keypoints = None
                if hasattr(result, 'keypoints') and result.keypoints is not None:
                    keypoints = result.keypoints.xy.cpu().numpy()
                
                for i in range(len(boxes)):
                    x1, y1, x2, y2 = map(int, boxes[i])
                    confidence = float(confs[i])
                    
                    kpts = keypoints[i] if keypoints is not None else None
                    
                    detection = Detection.from_xyxy(
                        x1=x1, y1=y1, x2=x2, y2=y2,
                        confidence=confidence,
                        keypoints=kpts
                    )
                    detections.append(detection)
            
            logger.debug(f"Detected {len(detections)} faces")
            
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
        
        return detections
    
    def detect_batch(self, frames: list[np.ndarray]) -> list[list[Detection]]:
        """
        Detect faces in multiple frames (batch processing).
        
        Args:
            frames: List of BGR images
            
        Returns:
            List of detection lists, one per frame
        """
        if not self._initialized:
            self.initialize()
        
        all_detections = []
        
        try:
            results = self._model.predict(
                frames,
                conf=self.config.conf_threshold,
                iou=self.config.iou_threshold,
                max_det=self.config.max_faces,
                device=self.config.device,
                verbose=False
            )
            
            for result in results:
                frame_detections = []
                
                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confs = result.boxes.conf.cpu().numpy()
                    
                    keypoints = None
                    if hasattr(result, 'keypoints') and result.keypoints is not None:
                        keypoints = result.keypoints.xy.cpu().numpy()
                    
                    for i in range(len(boxes)):
                        x1, y1, x2, y2 = map(int, boxes[i])
                        confidence = float(confs[i])
                        kpts = keypoints[i] if keypoints is not None else None
                        
                        detection = Detection.from_xyxy(
                            x1=x1, y1=y1, x2=x2, y2=y2,
                            confidence=confidence,
                            keypoints=kpts
                        )
                        frame_detections.append(detection)
                
                all_detections.append(frame_detections)
        
        except Exception as e:
            logger.error(f"Batch face detection failed: {e}")
            all_detections = [[] for _ in frames]
        
        return all_detections
    
    def release(self) -> None:
        """Release model resources."""
        self._model = None
        self._initialized = False
        logger.info("Face detector released")

