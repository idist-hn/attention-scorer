#!/usr/bin/env python3
"""
Quick test for all microservices by importing and checking core functionality
"""
import sys
from pathlib import Path

services_dir = Path(__file__).parent

def test_landmark_detection():
    print("Testing Landmark Detection...", end=" ")
    sys.path.insert(0, str(services_dir / "landmark-detection"))
    exec(open(services_dir / "landmark-detection/main.py").read().split('if __name__')[0])
    from main import LandmarkDetectionServicer
    s = LandmarkDetectionServicer()
    assert s.face_mesh is not None
    print("✅")
    return True

def test_head_pose():
    print("Testing Head Pose...", end=" ")
    import importlib.util
    spec = importlib.util.spec_from_file_location("head_pose_main", services_dir / "head-pose/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    s = module.HeadPoseServicer()
    h = s.Health(None, None)
    assert h['healthy'] == True
    print("✅")
    return True

def test_gaze_tracking():
    print("Testing Gaze Tracking...", end=" ")
    sys.path.insert(0, str(services_dir / "gaze-tracking"))
    # Import by reading file
    import importlib.util
    spec = importlib.util.spec_from_file_location("gaze_main", services_dir / "gaze-tracking/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    s = module.GazeTrackingServicer()
    h = s.Health(None, None)
    assert h['healthy'] == True
    print("✅")
    return True

def test_blink_detection():
    print("Testing Blink Detection...", end=" ")
    import importlib.util
    spec = importlib.util.spec_from_file_location("blink_main", services_dir / "blink-detection/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    s = module.BlinkDetectionServicer()
    h = s.Health(None, None)
    assert h['healthy'] == True
    print("✅")
    return True

def test_attention_scorer():
    print("Testing Attention Scorer...", end=" ")
    import importlib.util
    spec = importlib.util.spec_from_file_location("attention_main", services_dir / "attention-scorer/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    s = module.AttentionScorerServicer()
    h = s.Health(None, None)
    assert h['healthy'] == True
    assert s.weights['gaze'] == 0.35
    print("✅")
    return True

def test_pipeline_orchestrator():
    print("Testing Pipeline Orchestrator...", end=" ")
    import importlib.util
    spec = importlib.util.spec_from_file_location("pipeline_main", services_dir / "pipeline-orchestrator/main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    s = module.PipelineOrchestrator()
    assert s.registry is not None
    assert s.redis_client is not None
    print("✅")
    return True

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🧪 MICROSERVICE HEALTH CHECKS")
    print("=" * 50 + "\n")
    
    passed = 0
    failed = 0
    
    tests = [
        ("Landmark Detection", test_landmark_detection),
        ("Head Pose", test_head_pose),
        ("Gaze Tracking", test_gaze_tracking),
        ("Blink Detection", test_blink_detection),
        ("Attention Scorer", test_attention_scorer),
        ("Pipeline Orchestrator", test_pipeline_orchestrator),
    ]
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ ({e})")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(tests)} passed")
    print("=" * 50)
    
    sys.exit(0 if failed == 0 else 1)

