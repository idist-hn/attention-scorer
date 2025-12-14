#!/usr/bin/env python3
"""
Full Demo - Attention Detection System.
Demonstrates all features with synthetic test data.
"""

import sys
import time
import numpy as np
import cv2
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")


def create_face_image(
    width: int = 640, 
    height: int = 480,
    face_x: int = None,
    face_y: int = None,
    eye_open: float = 1.0,  # 0-1, how open eyes are
    head_turn: float = 0.0  # -1 to 1, head rotation
) -> np.ndarray:
    """Create a realistic face-like image for testing."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 220
    
    if face_x is None:
        face_x = width // 2
    if face_y is None:
        face_y = height // 2
    
    # Apply head turn offset
    face_x_offset = int(head_turn * 30)
    
    # Face (oval)
    cv2.ellipse(img, (face_x + face_x_offset, face_y), (80, 100), 0, 0, 360, (200, 180, 160), -1)
    cv2.ellipse(img, (face_x + face_x_offset, face_y), (80, 100), 0, 0, 360, (180, 160, 140), 2)
    
    # Eyes
    eye_height = int(15 * eye_open)
    left_eye_x = face_x + face_x_offset - 30
    right_eye_x = face_x + face_x_offset + 30
    eye_y = face_y - 20
    
    # White of eyes
    if eye_height > 3:
        cv2.ellipse(img, (left_eye_x, eye_y), (20, eye_height), 0, 0, 360, (255, 255, 255), -1)
        cv2.ellipse(img, (right_eye_x, eye_y), (20, eye_height), 0, 0, 360, (255, 255, 255), -1)
        
        # Pupils
        pupil_offset = int(head_turn * 8)
        cv2.circle(img, (left_eye_x + pupil_offset, eye_y), 7, (50, 40, 30), -1)
        cv2.circle(img, (right_eye_x + pupil_offset, eye_y), 7, (50, 40, 30), -1)
        cv2.circle(img, (left_eye_x + pupil_offset, eye_y), 3, (20, 20, 20), -1)
        cv2.circle(img, (right_eye_x + pupil_offset, eye_y), 3, (20, 20, 20), -1)
    
    # Nose
    nose_pts = np.array([
        [face_x + face_x_offset, face_y - 5],
        [face_x + face_x_offset - 10, face_y + 25],
        [face_x + face_x_offset + 10, face_y + 25]
    ], np.int32)
    cv2.polylines(img, [nose_pts], False, (160, 140, 120), 2)
    
    # Mouth
    cv2.ellipse(img, (face_x + face_x_offset, face_y + 50), (25, 10), 0, 0, 180, (150, 100, 100), 2)
    
    # Eyebrows
    cv2.line(img, (left_eye_x - 15, eye_y - 20), (left_eye_x + 15, eye_y - 18), (100, 80, 60), 3)
    cv2.line(img, (right_eye_x - 15, eye_y - 18), (right_eye_x + 15, eye_y - 20), (100, 80, 60), 3)
    
    return img


def run_full_demo():
    """Run full attention detection demo."""
    from src.pipeline import AttentionPipeline
    from src.utils.visualization import Visualizer
    
    logger.info("=" * 60)
    logger.info("🎯 ATTENTION DETECTION SYSTEM - FULL DEMO")
    logger.info("=" * 60)
    
    # Initialize
    logger.info("\n📦 Initializing pipeline...")
    pipeline = AttentionPipeline()
    pipeline.initialize()
    visualizer = Visualizer()
    
    # Demo scenarios
    scenarios = [
        {"name": "👀 Full Attention", "eye_open": 1.0, "head_turn": 0.0},
        {"name": "👁️ Half Eyes", "eye_open": 0.5, "head_turn": 0.0},
        {"name": "😴 Eyes Closed (Drowsy)", "eye_open": 0.1, "head_turn": 0.0},
        {"name": "👈 Looking Left", "eye_open": 1.0, "head_turn": -0.8},
        {"name": "👉 Looking Right", "eye_open": 1.0, "head_turn": 0.8},
        {"name": "🔄 Slight Turn + Tired", "eye_open": 0.4, "head_turn": 0.4},
    ]
    
    logger.info("\n🎬 Running scenarios...\n")
    
    all_results = []
    
    for i, scenario in enumerate(scenarios):
        # Create test image
        img = create_face_image(
            eye_open=scenario["eye_open"],
            head_turn=scenario["head_turn"]
        )
        
        # Process
        start = time.time()
        result = pipeline.process_frame(img, meeting_id="demo")
        proc_time = (time.time() - start) * 1000
        
        # Log result
        logger.info(f"Scenario {i+1}: {scenario['name']}")
        logger.info(f"  Processing time: {proc_time:.1f}ms")
        logger.info(f"  Faces detected: {len(result.attention_results)}")
        
        if result.attention_results:
            r = result.attention_results[0]
            logger.info(f"  ✓ Attention Score: {r.attention_score:.1f}%")
            if r.metrics:
                logger.info(f"    Gaze: {r.metrics.gaze_score:.2f} | Head: {r.metrics.head_pose_score:.2f} | Eyes: {r.metrics.eye_openness_score:.2f}")
        else:
            # Simulate attention calculation for demo
            eye_score = scenario["eye_open"]
            head_score = 1.0 - abs(scenario["head_turn"])
            sim_score = (eye_score * 0.35 + head_score * 0.30 + eye_score * 0.20 + 1.0 * 0.15) * 100
            logger.info(f"  ⚡ Simulated Score: {sim_score:.1f}%")
        
        all_results.append(result)
        
        # Save image
        output = visualizer.draw_results(img, result)
        cv2.imwrite(f"demo_output_{i+1}.jpg", output)
        print()
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 DEMO SUMMARY")
    logger.info("=" * 60)
    
    logger.info(f"\n✓ Processed {len(scenarios)} scenarios")
    logger.info(f"✓ Average processing time: {sum(r.processing_time_ms for r in all_results)/len(all_results):.1f}ms")
    logger.info(f"✓ Output images saved: demo_output_1.jpg to demo_output_{len(scenarios)}.jpg")
    
    logger.info("\n🎉 Demo completed successfully!")
    
    pipeline.release()


if __name__ == "__main__":
    run_full_demo()

