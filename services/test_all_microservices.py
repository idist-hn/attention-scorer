"""
Test script for all AI Microservices
"""
import sys
import cv2
import numpy as np
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "landmark-detection"))
sys.path.insert(0, str(Path(__file__).parent / "head-pose"))
sys.path.insert(0, str(Path(__file__).parent / "gaze-tracking"))
sys.path.insert(0, str(Path(__file__).parent / "blink-detection"))
sys.path.insert(0, str(Path(__file__).parent / "attention-scorer"))


def create_test_frame() -> bytes:
    """Create a test frame with face-like pattern."""
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    test_image[:] = (200, 200, 200)
    cv2.circle(test_image, (320, 240), 100, (180, 150, 130), -1)  # Face
    cv2.circle(test_image, (290, 220), 15, (50, 50, 50), -1)  # Left eye
    cv2.circle(test_image, (350, 220), 15, (50, 50, 50), -1)  # Right eye
    cv2.ellipse(test_image, (320, 280), (30, 15), 0, 0, 180, (100, 80, 80), 2)
    _, buffer = cv2.imencode('.jpg', test_image)
    return buffer.tobytes()


class MockRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MockLandmark:
    def __init__(self, index, x, y, z=0):
        self.index = index
        self.x = x
        self.y = y
        self.z = z


def test_landmark_detection():
    print("\n" + "=" * 60)
    print("Test: Landmark Detection Service")
    print("=" * 60)
    
    from landmark_main import LandmarkDetectionServicer
    servicer = LandmarkDetectionServicer()
    
    request = MockRequest(frame_data=create_test_frame(), request_id="test-landmark")
    result = servicer.DetectLandmarks(request, None)
    
    print(f"  Success: {result['success']}")
    print(f"  Faces detected: {len(result['faces'])}")
    print(f"  Processing time: {result['processing_time_ms']:.2f}ms")
    
    if result['faces']:
        print(f"  Landmarks per face: {len(result['faces'][0]['landmarks'])}")
    
    assert result['success'] == True
    print("  ✅ Landmark Detection test passed!")
    return result


def test_head_pose(landmarks):
    print("\n" + "=" * 60)
    print("Test: Head Pose Service")
    print("=" * 60)
    
    from head_pose_main import HeadPoseServicer
    servicer = HeadPoseServicer()
    
    mock_landmarks = [MockLandmark(i, l['x'], l['y'], l['z']) for i, l in enumerate(landmarks)]
    request = MockRequest(
        request_id="test-headpose",
        landmarks=mock_landmarks,
        frame_width=640,
        frame_height=480
    )
    result = servicer.EstimatePose(request, None)
    
    print(f"  Success: {result['success']}")
    if result['pose']:
        print(f"  Yaw: {result['pose']['yaw']:.2f}°")
        print(f"  Pitch: {result['pose']['pitch']:.2f}°")
        print(f"  Roll: {result['pose']['roll']:.2f}°")
    print(f"  Processing time: {result['processing_time_ms']:.2f}ms")
    
    assert result['success'] == True
    print("  ✅ Head Pose test passed!")
    return result


def test_gaze_tracking(landmarks):
    print("\n" + "=" * 60)
    print("Test: Gaze Tracking Service")
    print("=" * 60)
    
    from gaze_main import GazeTrackingServicer
    servicer = GazeTrackingServicer()
    
    mock_landmarks = [MockLandmark(i, l['x'], l['y'], l['z']) for i, l in enumerate(landmarks)]
    request = MockRequest(request_id="test-gaze", landmarks=mock_landmarks)
    result = servicer.EstimateGaze(request, None)
    
    print(f"  Success: {result['success']}")
    if result['gaze']:
        print(f"  Gaze X: {result['gaze']['gaze_x']:.3f}")
        print(f"  Looking at camera: {result['gaze']['is_looking_at_camera']}")
    print(f"  Processing time: {result['processing_time_ms']:.2f}ms")
    
    print("  ✅ Gaze Tracking test passed!")
    return result


def test_blink_detection(landmarks):
    print("\n" + "=" * 60)
    print("Test: Blink Detection Service")
    print("=" * 60)
    
    from blink_main import BlinkDetectionServicer
    servicer = BlinkDetectionServicer()
    
    mock_landmarks = [MockLandmark(i, l['x'], l['y'], l['z']) for i, l in enumerate(landmarks)]
    request = MockRequest(request_id="test-blink", landmarks=mock_landmarks)
    result = servicer.DetectBlink(request, None)
    
    print(f"  Success: {result['success']}")
    if result['blink_info']:
        print(f"  Left EAR: {result['blink_info']['left_ear']:.3f}")
        print(f"  Right EAR: {result['blink_info']['right_ear']:.3f}")
        print(f"  Is Blinking: {result['blink_info']['is_blinking']}")
    print(f"  Processing time: {result['processing_time_ms']:.2f}ms")
    
    print("  ✅ Blink Detection test passed!")
    return result


def test_attention_scorer():
    print("\n" + "=" * 60)
    print("Test: Attention Scorer Service")
    print("=" * 60)
    
    from attention_main import AttentionScorerServicer
    servicer = AttentionScorerServicer()
    
    request = MockRequest(
        request_id="test-attention",
        gaze_x=0.1, gaze_y=0.0,
        yaw=5.0, pitch=3.0, roll=0.0,
        left_ear=0.35, right_ear=0.35,
        is_present=True
    )
    result = servicer.CalculateAttention(request, None)
    
    print(f"  Success: {result['success']}")
    if result['attention']:
        print(f"  Attention Score: {result['attention']['score']:.2f}")
        print(f"  Level: {result['attention']['level']}")
    print(f"  Processing time: {result['processing_time_ms']:.2f}ms")
    
    assert result['success'] == True
    print("  ✅ Attention Scorer test passed!")
    return result


if __name__ == "__main__":
    print("\n🧪 TESTING ALL AI MICROSERVICES\n")
    
    # Rename main.py files for import (workaround)
    import shutil
    services_dir = Path(__file__).parent
    
    try:
        shutil.copy(services_dir / "landmark-detection/main.py", services_dir / "landmark-detection/landmark_main.py")
        shutil.copy(services_dir / "head-pose/main.py", services_dir / "head-pose/head_pose_main.py")
        shutil.copy(services_dir / "gaze-tracking/main.py", services_dir / "gaze-tracking/gaze_main.py")
        shutil.copy(services_dir / "blink-detection/main.py", services_dir / "blink-detection/blink_main.py")
        shutil.copy(services_dir / "attention-scorer/main.py", services_dir / "attention-scorer/attention_main.py")
    except: pass
    
    sys.path.insert(0, str(services_dir / "landmark-detection"))
    sys.path.insert(0, str(services_dir / "head-pose"))
    sys.path.insert(0, str(services_dir / "gaze-tracking"))
    sys.path.insert(0, str(services_dir / "blink-detection"))
    sys.path.insert(0, str(services_dir / "attention-scorer"))

    passed = 0
    failed = 0

    try:
        # Test Landmark Detection
        landmark_result = test_landmark_detection()
        passed += 1

        # Get landmarks for subsequent tests
        if landmark_result['faces']:
            landmarks = landmark_result['faces'][0]['landmarks']

            # Test Head Pose
            test_head_pose(landmarks)
            passed += 1

            # Test Gaze Tracking
            test_gaze_tracking(landmarks)
            passed += 1

            # Test Blink Detection
            test_blink_detection(landmarks)
            passed += 1

        # Test Attention Scorer
        test_attention_scorer()
        passed += 1

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)

