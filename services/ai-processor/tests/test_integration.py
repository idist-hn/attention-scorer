"""
Integration tests for the attention detection pipeline.
Tests end-to-end flow without requiring actual models.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Optional


# ================== MOCK DATA ==================

@dataclass
class MockBBox:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class MockFaceDetection:
    bbox: MockBBox
    confidence: float
    track_id: Optional[int] = None


@dataclass 
class MockHeadPose:
    yaw: float
    pitch: float
    roll: float


@dataclass
class MockGazeInfo:
    gaze_x: float
    gaze_y: float
    is_looking_at_camera: bool


@dataclass
class MockBlinkInfo:
    left_ear: float
    right_ear: float
    avg_ear: float
    is_blinking: bool
    blink_rate: float
    perclos: float


@dataclass
class MockAttentionResult:
    track_id: int
    attention_score: float
    attention_level: str
    is_attentive: bool
    head_pose: MockHeadPose
    gaze: MockGazeInfo
    blink: MockBlinkInfo


# ================== MOCK PIPELINE ==================

class MockAttentionPipeline:
    """Mock pipeline for integration testing."""
    
    def __init__(self):
        self.face_detector = Mock()
        self.landmark_detector = Mock()
        self.head_pose_estimator = Mock()
        self.gaze_tracker = Mock()
        self.blink_detector = Mock()
        self.attention_scorer = Mock()
        self._initialized = False
    
    def initialize(self):
        self._initialized = True
    
    def process_frame(self, frame: np.ndarray) -> List[MockAttentionResult]:
        """Process a single frame through the pipeline."""
        if not self._initialized:
            self.initialize()
        
        results = []
        
        # Step 1: Detect faces
        faces = self.face_detector.detect(frame)
        
        for face in faces:
            # Step 2: Detect landmarks
            roi = frame[face.bbox.y1:face.bbox.y2, face.bbox.x1:face.bbox.x2]
            landmarks = self.landmark_detector.detect(roi)
            
            # Step 3: Estimate head pose
            head_pose = self.head_pose_estimator.estimate(landmarks)
            
            # Step 4: Track gaze
            gaze = self.gaze_tracker.track(landmarks)
            
            # Step 5: Detect blinks
            blink = self.blink_detector.analyze(landmarks, face.track_id)
            
            # Step 6: Calculate attention score
            score = self.attention_scorer.calculate(
                gaze_score=0.8 if gaze.is_looking_at_camera else 0.2,
                head_pose_score=0.9 if abs(head_pose.yaw) < 15 else 0.3,
                eye_openness_score=1.0 - blink.perclos,
                presence_score=1.0
            )
            
            results.append(MockAttentionResult(
                track_id=face.track_id,
                attention_score=score,
                attention_level='high' if score >= 70 else 'low',
                is_attentive=score >= 50,
                head_pose=head_pose,
                gaze=gaze,
                blink=blink
            ))
        
        return results


# ================== TESTS ==================

class TestPipelineIntegration:
    """Integration tests for the attention pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a mock pipeline."""
        return MockAttentionPipeline()
    
    @pytest.fixture
    def sample_frame(self):
        """Create a sample video frame."""
        return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline._initialized is False
        pipeline.initialize()
        assert pipeline._initialized is True
    
    def test_pipeline_auto_initializes(self, pipeline, sample_frame):
        """Test pipeline auto-initializes on first frame."""
        pipeline.face_detector.detect.return_value = []

        pipeline.process_frame(sample_frame)
        assert pipeline._initialized is True

    def test_no_faces_returns_empty(self, pipeline, sample_frame):
        """Test empty result when no faces detected."""
        pipeline.face_detector.detect.return_value = []

        results = pipeline.process_frame(sample_frame)
        assert results == []

    def test_single_face_processing(self, pipeline, sample_frame):
        """Test processing a single detected face."""
        # Setup face detection mock
        mock_face = MockFaceDetection(
            bbox=MockBBox(100, 100, 200, 200),
            confidence=0.95,
            track_id=1
        )
        pipeline.face_detector.detect.return_value = [mock_face]

        # Setup other mocks
        mock_landmarks = Mock()
        mock_landmarks.landmarks = np.zeros((478, 3))
        pipeline.landmark_detector.detect.return_value = mock_landmarks

        pipeline.head_pose_estimator.estimate.return_value = MockHeadPose(0, 0, 0)
        pipeline.gaze_tracker.track.return_value = MockGazeInfo(0, 0, True)
        pipeline.blink_detector.analyze.return_value = MockBlinkInfo(
            0.35, 0.35, 0.35, False, 15, 0.1
        )
        pipeline.attention_scorer.calculate.return_value = 85.0

        results = pipeline.process_frame(sample_frame)

        assert len(results) == 1
        assert results[0].track_id == 1
        assert results[0].attention_score == 85.0

    def test_multiple_faces_processing(self, pipeline, sample_frame):
        """Test processing multiple detected faces."""
        mock_faces = [
            MockFaceDetection(MockBBox(50, 50, 150, 150), 0.95, track_id=1),
            MockFaceDetection(MockBBox(200, 50, 300, 150), 0.90, track_id=2),
            MockFaceDetection(MockBBox(350, 50, 450, 150), 0.85, track_id=3),
        ]
        pipeline.face_detector.detect.return_value = mock_faces

        # Setup mocks
        mock_landmarks = Mock()
        mock_landmarks.landmarks = np.zeros((478, 3))
        pipeline.landmark_detector.detect.return_value = mock_landmarks
        pipeline.head_pose_estimator.estimate.return_value = MockHeadPose(0, 0, 0)
        pipeline.gaze_tracker.track.return_value = MockGazeInfo(0, 0, True)
        pipeline.blink_detector.analyze.return_value = MockBlinkInfo(
            0.35, 0.35, 0.35, False, 15, 0.1
        )
        pipeline.attention_scorer.calculate.return_value = 80.0

        results = pipeline.process_frame(sample_frame)

        assert len(results) == 3
        assert [r.track_id for r in results] == [1, 2, 3]

    def test_inattentive_detection(self, pipeline, sample_frame):
        """Test detection of inattentive user."""
        mock_face = MockFaceDetection(
            bbox=MockBBox(100, 100, 200, 200),
            confidence=0.95,
            track_id=1
        )
        pipeline.face_detector.detect.return_value = [mock_face]

        # Setup mocks for inattentive state
        mock_landmarks = Mock()
        mock_landmarks.landmarks = np.zeros((478, 3))
        pipeline.landmark_detector.detect.return_value = mock_landmarks

        # Looking away, drowsy
        pipeline.head_pose_estimator.estimate.return_value = MockHeadPose(45, 30, 0)
        pipeline.gaze_tracker.track.return_value = MockGazeInfo(0.8, 0.5, False)
        pipeline.blink_detector.analyze.return_value = MockBlinkInfo(
            0.15, 0.15, 0.15, False, 5, 0.7
        )
        pipeline.attention_scorer.calculate.return_value = 25.0

        results = pipeline.process_frame(sample_frame)

        assert len(results) == 1
        assert results[0].is_attentive is False
        assert results[0].attention_level == 'low'


class TestPipelineDataFlow:
    """Test data flows correctly between pipeline stages."""

    @pytest.fixture
    def pipeline(self):
        return MockAttentionPipeline()

    def test_face_detection_called_with_frame(self, pipeline):
        """Test face detector receives the frame."""
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        pipeline.face_detector.detect.return_value = []

        pipeline.process_frame(frame)

        pipeline.face_detector.detect.assert_called_once()
        call_args = pipeline.face_detector.detect.call_args[0][0]
        np.testing.assert_array_equal(call_args, frame)

    def test_all_components_called_for_each_face(self, pipeline):
        """Test all components are called for each detected face."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_face = MockFaceDetection(
            MockBBox(100, 100, 200, 200), 0.95, track_id=1
        )
        pipeline.face_detector.detect.return_value = [mock_face]

        mock_landmarks = Mock()
        mock_landmarks.landmarks = np.zeros((478, 3))
        pipeline.landmark_detector.detect.return_value = mock_landmarks
        pipeline.head_pose_estimator.estimate.return_value = MockHeadPose(0, 0, 0)
        pipeline.gaze_tracker.track.return_value = MockGazeInfo(0, 0, True)
        pipeline.blink_detector.analyze.return_value = MockBlinkInfo(
            0.35, 0.35, 0.35, False, 15, 0.1
        )
        pipeline.attention_scorer.calculate.return_value = 80.0

        pipeline.process_frame(frame)

        assert pipeline.landmark_detector.detect.called
        assert pipeline.head_pose_estimator.estimate.called
        assert pipeline.gaze_tracker.track.called
        assert pipeline.blink_detector.analyze.called
        assert pipeline.attention_scorer.calculate.called

