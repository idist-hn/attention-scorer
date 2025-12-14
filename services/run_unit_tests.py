#!/usr/bin/env python3
"""
Run all unit tests for AI microservices
"""
import subprocess
import sys
from pathlib import Path

SERVICES = [
    "face-detection",
    "landmark-detection",
    "head-pose",
    "gaze-tracking",
    "blink-detection",
    "attention-scorer",
]

def run_tests():
    """Run pytest for each service."""
    services_dir = Path(__file__).parent
    results = {}
    
    for service in SERVICES:
        service_dir = services_dir / service
        test_file = service_dir / f"test_{service.replace('-', '_')}.py"
        
        if not test_file.exists():
            print(f"⚠️  No test file found for {service}")
            results[service] = "SKIPPED"
            continue
        
        print(f"\n{'='*60}")
        print(f"Running tests for: {service}")
        print(f"{'='*60}")
        
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            cwd=str(service_dir),
            capture_output=False
        )
        
        results[service] = "PASSED" if result.returncode == 0 else "FAILED"
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    skipped = 0
    
    for service, status in results.items():
        icon = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⚠️"
        print(f"  {icon} {service}: {status}")
        if status == "PASSED":
            passed += 1
        elif status == "FAILED":
            failed += 1
        else:
            skipped += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())

