"""
Main Attention Detection Pipeline.

This module orchestrates all detection components into a unified pipeline
for processing video frames and generating attention metrics.
"""

import time
import numpy as np
from typing import Optional
from datetime import datetime
from loguru import logger

from ..config import settings
from ..core import (
    FaceDetector,
    FaceTracker,
    LandmarkDetector,
    HeadPoseEstimator,
    GazeTracker,
    BlinkDetector,
    AttentionScorer
)
from ..models.detection import Face, Detection, TrackInfo
from ..models.attention import AttentionResult, Alert, FrameResult


class AttentionPipeline:
    """
    Main pipeline for attention detection.
    
    Combines all detection modules into a single processing pipeline:
    1. Face Detection (YOLOv8-face)
    2. Face Tracking (ByteTrack)
    3. Landmark Detection (MediaPipe)
    4. Head Pose Estimation
    5. Gaze Tracking
    6. Blink Detection
    7. Attention Scoring
    """
    
    def __init__(self):
        """Initialize the attention detection pipeline."""
        self._initialized = False
        
        # Core modules
        self.face_detector: Optional[FaceDetector] = None
        self.face_tracker: Optional[FaceTracker] = None
        self.landmark_detector: Optional[LandmarkDetector] = None
        self.head_pose_estimator: Optional[HeadPoseEstimator] = None
        self.gaze_tracker: Optional[GazeTracker] = None
        self.blink_detector: Optional[BlinkDetector] = None
        self.attention_scorer: Optional[AttentionScorer] = None
        
        # State
        self._frame_count = 0
        self._meeting_id: Optional[str] = None
    
    def initialize(self) -> None:
        """Initialize all pipeline components."""
        if self._initialized:
            return
        
        logger.info("Initializing attention detection pipeline...")
        start_time = time.time()
        
        try:
            # Initialize components
            self.face_detector = FaceDetector()
            self.face_detector.initialize()
            
            self.face_tracker = FaceTracker()
            
            self.landmark_detector = LandmarkDetector()
            self.landmark_detector.initialize()
            
            self.head_pose_estimator = HeadPoseEstimator()
            self.gaze_tracker = GazeTracker()
            self.blink_detector = BlinkDetector()
            self.attention_scorer = AttentionScorer()
            
            self._initialized = True
            elapsed = time.time() - start_time
            logger.info(f"Pipeline initialized in {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise
    
    def process_frame(
        self, 
        frame: np.ndarray,
        meeting_id: str = "default"
    ) -> FrameResult:
        """
        Process a single video frame.
        
        Args:
            frame: BGR image as numpy array (H, W, 3)
            meeting_id: Meeting identifier
            
        Returns:
            FrameResult with attention scores for all participants
        """
        if not self._initialized:
            self.initialize()
        
        start_time = time.time()
        self._frame_count += 1
        self._meeting_id = meeting_id
        
        h, w = frame.shape[:2]
        self.head_pose_estimator.update_frame_size(w, h)
        
        # Step 1: Face Detection
        detections = self.face_detector.detect(frame)
        
        # Step 2: Face Tracking
        tracked_faces = self.face_tracker.update(detections)
        
        # Step 3-7: Process each tracked face
        attention_results = []
        all_alerts = []
        
        for detection, track_info in tracked_faces:
            result, alerts = self._process_single_face(
                frame, detection, track_info
            )
            if result:
                attention_results.append(result)
            all_alerts.extend(alerts)
        
        processing_time = (time.time() - start_time) * 1000
        
        return FrameResult(
            frame_id=self._frame_count,
            meeting_id=meeting_id,
            timestamp=datetime.now(),
            attention_results=attention_results,
            alerts=all_alerts,
            processing_time_ms=processing_time
        )
    
    def _process_single_face(
        self,
        frame: np.ndarray,
        detection: Detection,
        track_info: TrackInfo
    ) -> tuple[Optional[AttentionResult], list[Alert]]:
        """Process a single tracked face."""
        try:
            # Create Face object
            face = Face(detection=detection, track_info=track_info)
            track_id = track_info.track_id
            
            # Detect landmarks
            landmarks_list = self.landmark_detector.detect(frame, [detection])
            if landmarks_list and landmarks_list[0]:
                face.landmarks = landmarks_list[0]
                
                # Head pose estimation
                face.head_pose = self.head_pose_estimator.estimate(face.landmarks)
                
                # Gaze tracking
                face.gaze = self.gaze_tracker.estimate(face.landmarks)
                
                # Blink detection
                face.blink = self.blink_detector.analyze(face.landmarks, track_id)
            
            # Calculate attention score
            result = self.attention_scorer.process_face(face, track_id)
            
            # Check for alerts
            alerts = []
            if result.metrics:
                alerts = self.attention_scorer.check_alerts(
                    track_id, result.metrics, result.attention_score
                )
            
            return result, alerts
            
        except Exception as e:
            logger.warning(f"Failed to process face {track_info.track_id}: {e}")
            return None, []
    
    def reset(self, meeting_id: Optional[str] = None) -> None:
        """Reset pipeline state."""
        self._frame_count = 0
        if meeting_id:
            self._meeting_id = meeting_id
        
        if self.face_tracker:
            self.face_tracker.reset()
        if self.blink_detector:
            self.blink_detector.reset_all()
        if self.attention_scorer:
            self.attention_scorer.reset_all()
        
        logger.info("Pipeline state reset")
    
    def release(self) -> None:
        """Release all resources."""
        if self.face_detector:
            self.face_detector.release()
        if self.landmark_detector:
            self.landmark_detector.release()
        
        self._initialized = False
        logger.info("Pipeline released")

