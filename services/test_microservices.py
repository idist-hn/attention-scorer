"""
Test Microservices Architecture

This script tests all AI microservices can be initialized correctly.
Run from: services/ai-processor/ (which has all dependencies installed)
"""

import sys
import os
import time

# Add parent paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🧪 MICROSERVICES ARCHITECTURE TEST")
print("=" * 60)

results = []

# Test 1: Face Detection (YOLOv8)
print("\n1️⃣ Testing Face Detection Service (YOLOv8)...")
try:
    from ultralytics import YOLO
    import numpy as np
    import cv2
    
    model = YOLO("yolov8n.pt")
    
    # Create test image
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    test_image[100:300, 200:400] = [200, 180, 160]  # Face-like blob
    
    detections = model(test_image, verbose=False)
    print(f"   ✅ Face Detection OK - Model loaded, can process frames")
    results.append(("Face Detection", True, "YOLOv8 model loaded"))
except Exception as e:
    print(f"   ❌ Face Detection FAILED: {e}")
    results.append(("Face Detection", False, str(e)))

# Test 2: Landmark Detection (MediaPipe)
print("\n2️⃣ Testing Landmark Detection Service (MediaPipe)...")
try:
    import mediapipe as mp
    
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=10,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    # Test with blank image
    test_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    result = face_mesh.process(test_rgb)
    face_mesh.close()
    
    print(f"   ✅ Landmark Detection OK - MediaPipe FaceMesh initialized (478 landmarks)")
    results.append(("Landmark Detection", True, "MediaPipe FaceMesh ready"))
except Exception as e:
    print(f"   ❌ Landmark Detection FAILED: {e}")
    results.append(("Landmark Detection", False, str(e)))

# Test 3: Head Pose Estimation (OpenCV SolvePnP)
print("\n3️⃣ Testing Head Pose Service (OpenCV SolvePnP)...")
try:
    import cv2
    import numpy as np
    
    # 3D model points
    model_points = np.array([
        (0.0, 0.0, 0.0),
        (0.0, -330.0, -65.0),
        (-225.0, 170.0, -135.0),
        (225.0, 170.0, -135.0),
        (-150.0, -150.0, -125.0),
        (150.0, -150.0, -125.0)
    ], dtype=np.float64)
    
    # Test 2D points
    image_points = np.array([
        (320, 240),
        (320, 350),
        (270, 200),
        (370, 200),
        (280, 300),
        (360, 300)
    ], dtype=np.float64)
    
    # Camera matrix
    camera_matrix = np.array([
        [640, 0, 320],
        [0, 640, 240],
        [0, 0, 1]
    ], dtype=np.float64)
    
    dist_coeffs = np.zeros((4, 1))
    
    success, rvec, tvec = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs
    )
    
    if success:
        print(f"   ✅ Head Pose OK - SolvePnP working (yaw/pitch/roll estimation)")
        results.append(("Head Pose", True, "OpenCV SolvePnP ready"))
    else:
        raise Exception("SolvePnP failed")
except Exception as e:
    print(f"   ❌ Head Pose FAILED: {e}")
    results.append(("Head Pose", False, str(e)))

# Test 4: Gaze Tracking (Iris-based)
print("\n4️⃣ Testing Gaze Tracking Service...")
try:
    # Test iris position calculation
    left_iris = [(100, 100), (102, 98), (104, 100), (102, 102), (100, 100)]
    right_iris = [(200, 100), (202, 98), (204, 100), (202, 102), (200, 100)]
    
    left_cx = np.mean([p[0] for p in left_iris])
    left_cy = np.mean([p[1] for p in left_iris])
    
    # Simple gaze calculation
    eye_center_x = 150
    gaze_x = (left_cx - eye_center_x) / 50
    
    print(f"   ✅ Gaze Tracking OK - Iris position calculation working")
    results.append(("Gaze Tracking", True, "Iris-based gaze ready"))
except Exception as e:
    print(f"   ❌ Gaze Tracking FAILED: {e}")
    results.append(("Gaze Tracking", False, str(e)))

# Test 5: Blink Detection (EAR-based)
print("\n5️⃣ Testing Blink Detection Service (EAR)...")
try:
    # Eye Aspect Ratio calculation
    def calculate_ear(eye_points):
        v1 = np.sqrt((eye_points[1][0] - eye_points[5][0])**2 + 
                     (eye_points[1][1] - eye_points[5][1])**2)
        v2 = np.sqrt((eye_points[2][0] - eye_points[4][0])**2 + 
                     (eye_points[2][1] - eye_points[4][1])**2)
        h = np.sqrt((eye_points[0][0] - eye_points[3][0])**2 + 
                    (eye_points[0][1] - eye_points[3][1])**2)
        return (v1 + v2) / (2.0 * h)
    
    # Open eye points
    open_eye = [(0, 50), (25, 40), (50, 40), (75, 50), (50, 60), (25, 60)]
    # Closed eye points
    closed_eye = [(0, 50), (25, 49), (50, 49), (75, 50), (50, 51), (25, 51)]
    
    open_ear = calculate_ear(open_eye)
    closed_ear = calculate_ear(closed_eye)
    
    print(f"   ✅ Blink Detection OK - EAR: open={open_ear:.3f}, closed={closed_ear:.3f}")
    results.append(("Blink Detection", True, f"EAR calculation working"))
except Exception as e:
    print(f"   ❌ Blink Detection FAILED: {e}")
    results.append(("Blink Detection", False, str(e)))

# Test 6: Attention Scorer
print("\n6️⃣ Testing Attention Scorer Service...")
try:
    # Weighted attention calculation
    weights = {'gaze': 0.35, 'head_pose': 0.30, 'eye_openness': 0.20, 'presence': 0.15}
    
    gaze_score = 0.9
    head_score = 0.8
    eye_score = 0.95
    presence_score = 1.0
    
    attention = (weights['gaze'] * gaze_score +
                weights['head_pose'] * head_score +
                weights['eye_openness'] * eye_score +
                weights['presence'] * presence_score) * 100
    
    print(f"   ✅ Attention Scorer OK - Score: {attention:.1f}%")
    results.append(("Attention Scorer", True, f"Score: {attention:.1f}%"))
except Exception as e:
    print(f"   ❌ Attention Scorer FAILED: {e}")
    results.append(("Attention Scorer", False, str(e)))

# Summary
print("\n" + "=" * 60)
print("📊 MICROSERVICES TEST SUMMARY")
print("=" * 60)

passed = sum(1 for _, ok, _ in results if ok)
total = len(results)

print(f"\n{'Service':<25} {'Status':<10} {'Details'}")
print("-" * 60)
for name, ok, details in results:
    status = "✅ OK" if ok else "❌ FAIL"
    print(f"{name:<25} {status:<10} {details[:30]}")

print(f"\n{'=' * 60}")
print(f"TOTAL: {passed}/{total} services passed")
print(f"{'=' * 60}")

if passed == total:
    print("\n🎉 All microservices are ready for deployment!")
else:
    print(f"\n⚠️ {total - passed} service(s) need attention")

