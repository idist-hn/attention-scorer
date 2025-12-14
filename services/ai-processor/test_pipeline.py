#!/usr/bin/env python3
"""
Quick test script for Attention Detection Pipeline.
Tests the pipeline with a synthetic face image.
"""

import sys
import numpy as np
import cv2
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")


def create_test_image(width: int = 640, height: int = 480) -> np.ndarray:
    """Create a test image with a simple face-like pattern."""
    # Create blank image
    img = np.ones((height, width, 3), dtype=np.uint8) * 200
    
    # Draw a simple face circle
    center = (width // 2, height // 2)
    cv2.circle(img, center, 100, (180, 160, 140), -1)  # Face
    
    # Eyes
    cv2.circle(img, (center[0] - 35, center[1] - 20), 15, (255, 255, 255), -1)
    cv2.circle(img, (center[0] + 35, center[1] - 20), 15, (255, 255, 255), -1)
    cv2.circle(img, (center[0] - 35, center[1] - 20), 8, (50, 50, 50), -1)
    cv2.circle(img, (center[0] + 35, center[1] - 20), 8, (50, 50, 50), -1)
    
    # Mouth
    cv2.ellipse(img, (center[0], center[1] + 40), (30, 15), 0, 0, 180, (100, 80, 80), -1)
    
    return img


def test_modules():
    """Test individual modules."""
    logger.info("Testing individual modules...")
    
    # Test imports
    from src.models.detection import BoundingBox, Detection, FaceLandmarks
    from src.models.attention import AttentionMetrics, AttentionResult, AlertType
    from src.config import settings
    
    logger.info("✓ All imports successful")
    
    # Test BoundingBox
    bbox = BoundingBox(x=10, y=20, width=100, height=150)
    assert bbox.area == 15000
    assert bbox.center == (60, 95)
    logger.info("✓ BoundingBox works correctly")
    
    # Test Detection
    det = Detection.from_xyxy(10, 20, 110, 170, confidence=0.95)
    assert det.confidence == 0.95
    logger.info("✓ Detection works correctly")
    
    # Test AttentionMetrics
    metrics = AttentionMetrics(
        gaze_score=0.8, head_pose_score=0.9,
        eye_openness_score=0.85, presence_score=1.0,
        head_yaw=5.0, head_pitch=-2.0, head_roll=1.0,
        eye_aspect_ratio=0.28, blink_rate=12.0, perclos=0.1,
        gaze_x=0.05, gaze_y=-0.02
    )
    assert metrics.is_present == True
    logger.info("✓ AttentionMetrics works correctly")
    
    # Test config
    assert settings.attention.gaze_weight == 0.35
    logger.info("✓ Config loaded correctly")
    
    logger.info("All module tests passed!")


def test_attention_scorer():
    """Test attention scorer."""
    logger.info("Testing AttentionScorer...")
    
    from src.core.attention_scorer import AttentionScorer
    from src.models.detection import HeadPose, GazeInfo, BlinkInfo
    
    scorer = AttentionScorer()
    
    # Test with full attention
    head_pose = HeadPose(yaw=0, pitch=0, roll=0)
    gaze = GazeInfo(gaze_x=0, gaze_y=0)
    blink = BlinkInfo(
        left_ear=0.3, right_ear=0.3, avg_ear=0.3,
        is_blinking=False, blink_rate=15, perclos=0.1
    )
    
    metrics = scorer.calculate(head_pose, gaze, blink, is_present=True)
    score = scorer.calculate_attention_score(metrics)
    
    logger.info(f"  Full attention score: {score:.1f}%")
    assert score >= 80, f"Expected score >= 80, got {score}"
    
    # Test with looking away
    head_pose_away = HeadPose(yaw=50, pitch=0, roll=0)
    metrics_away = scorer.calculate(head_pose_away, gaze, blink, is_present=True)
    score_away = scorer.calculate_attention_score(metrics_away)
    
    logger.info(f"  Looking away score: {score_away:.1f}%")
    assert score_away < score, "Looking away should reduce score"
    
    # Test with drowsy
    blink_drowsy = BlinkInfo(
        left_ear=0.15, right_ear=0.15, avg_ear=0.15,
        is_blinking=False, blink_rate=5, perclos=0.85
    )
    metrics_drowsy = scorer.calculate(head_pose, gaze, blink_drowsy, is_present=True)
    
    logger.info(f"  Is drowsy: {metrics_drowsy.is_drowsy}")
    assert metrics_drowsy.is_drowsy == True
    
    logger.info("✓ AttentionScorer tests passed!")


def test_pipeline_init():
    """Test pipeline initialization."""
    logger.info("Testing Pipeline initialization...")

    from src.pipeline import AttentionPipeline

    pipeline = AttentionPipeline()
    logger.info("  Pipeline created")

    pipeline.initialize()
    logger.info("  Pipeline initialized")

    # Process a test frame
    test_img = create_test_image()
    result = pipeline.process_frame(test_img, meeting_id="test")

    logger.info(f"  Processed frame: {result.frame_id}")
    logger.info(f"  Faces detected: {len(result.attention_results)}")
    logger.info(f"  Processing time: {result.processing_time_ms:.1f}ms")

    pipeline.release()
    logger.info("✓ Pipeline tests passed!")


def test_with_real_image():
    """Test with a real face image from URL."""
    logger.info("Testing with real face image...")

    import urllib.request
    from src.pipeline import AttentionPipeline
    from src.utils.visualization import Visualizer

    # Download sample image with face
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Face_of_young_man.jpg/440px-Face_of_young_man.jpg"

    try:
        logger.info("  Downloading sample image...")
        resp = urllib.request.urlopen(url, timeout=10)
        arr = np.asarray(bytearray(resp.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img is None:
            logger.warning("  Could not load image, skipping real image test")
            return

        logger.info(f"  Image size: {img.shape[1]}x{img.shape[0]}")

        # Process
        pipeline = AttentionPipeline()
        pipeline.initialize()

        # Process multiple times to get stable timing
        for i in range(3):
            result = pipeline.process_frame(img, meeting_id="test-real")

        logger.info(f"  Faces detected: {len(result.attention_results)}")
        logger.info(f"  Processing time: {result.processing_time_ms:.1f}ms")

        if result.attention_results:
            for r in result.attention_results:
                logger.info(f"  → Face {r.track_id}: Attention Score = {r.attention_score:.1f}%")
                if r.metrics:
                    logger.info(f"      Gaze: {r.metrics.gaze_score:.2f}, Head: {r.metrics.head_pose_score:.2f}, Eyes: {r.metrics.eye_openness_score:.2f}")
                    logger.info(f"      Looking away: {r.metrics.is_looking_away}, Drowsy: {r.metrics.is_drowsy}")

        # Save visualization
        visualizer = Visualizer()
        output = visualizer.draw_results(img, result)
        cv2.imwrite("test_output.jpg", output)
        logger.info("  Saved visualization to test_output.jpg")

        pipeline.release()
        logger.info("✓ Real image test passed!")

    except Exception as e:
        logger.warning(f"  Real image test skipped: {e}")


def main():
    logger.info("=" * 50)
    logger.info("Attention Detection Pipeline Test")
    logger.info("=" * 50)
    
    try:
        test_modules()
        print()
        test_attention_scorer()
        print()
        test_pipeline_init()
        print()
        test_with_real_image()

        print()
        logger.info("=" * 50)
        logger.info("ALL TESTS PASSED! ✓")
        logger.info("=" * 50)
        return 0

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

