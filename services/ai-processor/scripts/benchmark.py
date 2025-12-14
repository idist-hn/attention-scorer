#!/usr/bin/env python3
"""
Performance benchmark script for AI Processor.
"""

import sys
import os
import time
import argparse
import numpy as np
from typing import List, Dict
from collections import deque
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    fps: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')


class LatencyTracker:
    """Latency tracking with statistics."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._latencies: deque = deque(maxlen=window_size)

    def record(self, latency_ms: float) -> None:
        self._latencies.append(latency_ms)

    def get_stats(self) -> dict:
        if not self._latencies:
            return {'avg': 0, 'min': 0, 'max': 0, 'count': 0}

        latencies = list(self._latencies)
        return {
            'avg': sum(latencies) / len(latencies),
            'min': min(latencies),
            'max': max(latencies),
            'count': len(latencies)
        }


def generate_test_frames(count: int, width: int = 640, height: int = 480) -> List[np.ndarray]:
    """Generate synthetic test frames."""
    print(f"Generating {count} test frames ({width}x{height})...")
    frames = []
    for i in range(count):
        # Random frame with some structure
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        frames.append(frame)
    return frames


def benchmark_ear_calculation(iterations: int = 10000) -> Dict:
    """Benchmark EAR calculation."""
    from collections import deque
    
    # Create sample eye landmarks
    eye_landmarks = np.array([
        [100, 100, 0],
        [110, 90, 0],
        [120, 90, 0],
        [130, 100, 0],
        [120, 110, 0],
        [110, 110, 0],
    ], dtype=np.float32)
    
    def calculate_ear(eye: np.ndarray) -> float:
        v1 = np.linalg.norm(eye[1, :2] - eye[5, :2])
        v2 = np.linalg.norm(eye[2, :2] - eye[4, :2])
        h = np.linalg.norm(eye[0, :2] - eye[3, :2])
        return (v1 + v2) / (2.0 * h) if h > 0 else 0.0
    
    tracker = LatencyTracker(window_size=iterations)
    
    for _ in range(iterations):
        start = time.perf_counter()
        calculate_ear(eye_landmarks)
        elapsed_ms = (time.perf_counter() - start) * 1000
        tracker.record(elapsed_ms)
    
    stats = tracker.get_stats()
    return {
        'name': 'EAR Calculation',
        'iterations': iterations,
        'avg_ms': stats['avg'],
        'min_ms': stats['min'],
        'max_ms': stats['max'],
        'ops_per_sec': 1000 / stats['avg'] if stats['avg'] > 0 else 0
    }


def benchmark_attention_scoring(iterations: int = 10000) -> Dict:
    """Benchmark attention score calculation."""
    
    def calculate_attention(gaze: float, head: float, eye: float, presence: float) -> float:
        weights = (0.35, 0.30, 0.20, 0.15)
        return sum(w * s for w, s in zip(weights, [gaze, head, eye, presence])) * 100
    
    tracker = LatencyTracker(window_size=iterations)
    
    for _ in range(iterations):
        gaze = np.random.random()
        head = np.random.random()
        eye = np.random.random()
        presence = np.random.random()
        
        start = time.perf_counter()
        calculate_attention(gaze, head, eye, presence)
        elapsed_ms = (time.perf_counter() - start) * 1000
        tracker.record(elapsed_ms)
    
    stats = tracker.get_stats()
    return {
        'name': 'Attention Scoring',
        'iterations': iterations,
        'avg_ms': stats['avg'],
        'min_ms': stats['min'],
        'max_ms': stats['max'],
        'ops_per_sec': 1000 / stats['avg'] if stats['avg'] > 0 else 0
    }


def benchmark_numpy_operations(iterations: int = 1000) -> Dict:
    """Benchmark NumPy operations used in pipeline."""
    tracker = LatencyTracker(window_size=iterations)
    
    for _ in range(iterations):
        start = time.perf_counter()
        
        # Typical operations
        landmarks = np.random.rand(478, 3)
        distances = np.linalg.norm(landmarks[1:] - landmarks[:-1], axis=1)
        mean_dist = np.mean(distances)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        tracker.record(elapsed_ms)
    
    stats = tracker.get_stats()
    return {
        'name': 'NumPy Operations',
        'iterations': iterations,
        'avg_ms': stats['avg'],
        'min_ms': stats['min'],
        'max_ms': stats['max'],
        'ops_per_sec': 1000 / stats['avg'] if stats['avg'] > 0 else 0
    }


def check_gpu() -> tuple:
    """Simple GPU check."""
    try:
        import torch
        if torch.cuda.is_available():
            return True, torch.cuda.get_device_name(0), "cuda:0"
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return True, "Apple MPS", "mps"
    except ImportError:
        pass
    return False, "CPU", "cpu"


def run_benchmarks():
    """Run all benchmarks."""
    print("=" * 60)
    print("AI PROCESSOR PERFORMANCE BENCHMARK")
    print("=" * 60)

    # System info
    has_gpu, gpu_name, device = check_gpu()

    print(f"\nDevice: {device}")
    if has_gpu:
        print(f"GPU: {gpu_name}")

    print("\n" + "-" * 60)
    print("BENCHMARKS")
    print("-" * 60)

    # Run benchmarks
    results = [
        benchmark_ear_calculation(),
        benchmark_attention_scoring(),
        benchmark_numpy_operations(),
    ]

    for r in results:
        print(f"\n{r['name']}:")
        print(f"  Iterations: {r['iterations']:,}")
        print(f"  Avg: {r['avg_ms']:.4f} ms")
        print(f"  Min: {r['min_ms']:.4f} ms")
        print(f"  Max: {r['max_ms']:.4f} ms")
        print(f"  Throughput: {r['ops_per_sec']:,.0f} ops/sec")

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmarks()

