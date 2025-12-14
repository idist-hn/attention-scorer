#!/usr/bin/env python3
"""
Load testing script for AI Processor pipeline.
Tests concurrent request handling and throughput.
"""

import sys
import os
import time
import threading
import queue
import numpy as np
from typing import List, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque


@dataclass
class LoadTestResult:
    """Load test result container."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_sec: float
    requests_per_sec: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float


def simulate_frame_processing(frame: np.ndarray) -> Dict:
    """Simulate frame processing pipeline."""
    start = time.perf_counter()
    
    # Simulate face detection (heavy)
    time.sleep(0.005)  # 5ms
    
    # Simulate landmark detection
    landmarks = np.random.rand(478, 3)
    
    # Simulate EAR calculation
    def calculate_ear(eye: np.ndarray) -> float:
        v1 = np.linalg.norm(eye[1, :2] - eye[5, :2])
        v2 = np.linalg.norm(eye[2, :2] - eye[4, :2])
        h = np.linalg.norm(eye[0, :2] - eye[3, :2])
        return (v1 + v2) / (2.0 * h) if h > 0 else 0.0
    
    left_ear = calculate_ear(landmarks[:6])
    right_ear = calculate_ear(landmarks[6:12])
    
    # Simulate head pose estimation
    time.sleep(0.002)  # 2ms
    yaw, pitch, roll = np.random.uniform(-30, 30, 3)
    
    # Simulate attention scoring
    attention_score = np.random.uniform(60, 100)
    
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    return {
        'success': True,
        'latency_ms': elapsed_ms,
        'attention_score': attention_score,
        'head_pose': {'yaw': yaw, 'pitch': pitch, 'roll': roll},
        'ear': (left_ear + right_ear) / 2
    }


def run_concurrent_test(
    num_requests: int,
    num_workers: int,
    frame_size: tuple = (640, 480)
) -> LoadTestResult:
    """Run concurrent load test."""
    print(f"\n📊 Running load test: {num_requests} requests, {num_workers} workers")
    
    latencies: List[float] = []
    successful = 0
    failed = 0
    lock = threading.Lock()
    
    # Generate test frames
    frames = [np.random.randint(0, 255, (*frame_size, 3), dtype=np.uint8) 
              for _ in range(min(num_requests, 100))]
    
    def process_request(request_id: int) -> Dict:
        nonlocal successful, failed
        try:
            frame = frames[request_id % len(frames)]
            result = simulate_frame_processing(frame)
            
            with lock:
                latencies.append(result['latency_ms'])
                successful += 1
            
            return result
        except Exception as e:
            with lock:
                failed += 1
            return {'success': False, 'error': str(e)}
    
    # Run test
    start_time = time.perf_counter()
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(process_request, i) for i in range(num_requests)]
        for _ in as_completed(futures):
            pass
    
    total_time = time.perf_counter() - start_time
    
    # Calculate statistics
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    
    result = LoadTestResult(
        total_requests=num_requests,
        successful_requests=successful,
        failed_requests=failed,
        total_time_sec=total_time,
        requests_per_sec=successful / total_time if total_time > 0 else 0,
        avg_latency_ms=sum(latencies) / n if n > 0 else 0,
        p50_latency_ms=sorted_latencies[int(n * 0.50)] if n > 0 else 0,
        p95_latency_ms=sorted_latencies[int(n * 0.95)] if n > 0 else 0,
        p99_latency_ms=sorted_latencies[int(n * 0.99)] if n > 0 else 0,
        max_latency_ms=max(latencies) if latencies else 0
    )
    
    return result


def print_result(result: LoadTestResult):
    """Print load test result."""
    print("\n" + "=" * 50)
    print("LOAD TEST RESULTS")
    print("=" * 50)
    print(f"Total Requests:     {result.total_requests:,}")
    print(f"Successful:         {result.successful_requests:,}")
    print(f"Failed:             {result.failed_requests:,}")
    print(f"Total Time:         {result.total_time_sec:.2f}s")
    print(f"Throughput:         {result.requests_per_sec:.1f} req/s")
    print("-" * 50)
    print("Latency Statistics:")
    print(f"  Average:          {result.avg_latency_ms:.2f}ms")
    print(f"  P50:              {result.p50_latency_ms:.2f}ms")
    print(f"  P95:              {result.p95_latency_ms:.2f}ms")
    print(f"  P99:              {result.p99_latency_ms:.2f}ms")
    print(f"  Max:              {result.max_latency_ms:.2f}ms")
    print("=" * 50)


def main():
    print("🚀 AI Processor Load Test")
    print("-" * 50)
    
    # Test scenarios
    scenarios = [
        (100, 4, "Low load (100 req, 4 workers)"),
        (500, 8, "Medium load (500 req, 8 workers)"),
        (1000, 16, "High load (1000 req, 16 workers)"),
    ]
    
    for num_req, workers, desc in scenarios:
        print(f"\n🔄 {desc}")
        result = run_concurrent_test(num_req, workers)
        print_result(result)


if __name__ == "__main__":
    main()

