"""
Performance optimization utilities for AI processing.
"""

import time
import functools
import threading
from typing import Any, Callable, TypeVar, Optional
from collections import deque
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    fps: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    total_frames: int = 0
    dropped_frames: int = 0
    memory_mb: float = 0.0


class FPSCounter:
    """Thread-safe FPS counter with sliding window."""
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self._timestamps: deque = deque(maxlen=window_size)
        self._lock = threading.Lock()
    
    def tick(self) -> None:
        """Record a frame timestamp."""
        with self._lock:
            self._timestamps.append(time.time())
    
    def get_fps(self) -> float:
        """Calculate current FPS."""
        with self._lock:
            if len(self._timestamps) < 2:
                return 0.0
            
            elapsed = self._timestamps[-1] - self._timestamps[0]
            if elapsed <= 0:
                return 0.0
            
            return (len(self._timestamps) - 1) / elapsed
    
    def reset(self) -> None:
        """Reset the counter."""
        with self._lock:
            self._timestamps.clear()


class LatencyTracker:
    """Thread-safe latency tracking with statistics."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._latencies: deque = deque(maxlen=window_size)
        self._lock = threading.Lock()
    
    def record(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        with self._lock:
            self._latencies.append(latency_ms)
    
    def get_stats(self) -> dict:
        """Get latency statistics."""
        with self._lock:
            if not self._latencies:
                return {'avg': 0, 'min': 0, 'max': 0, 'count': 0}
            
            latencies = list(self._latencies)
            return {
                'avg': sum(latencies) / len(latencies),
                'min': min(latencies),
                'max': max(latencies),
                'count': len(latencies)
            }
    
    def reset(self) -> None:
        """Reset the tracker."""
        with self._lock:
            self._latencies.clear()


def measure_time(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        logger.debug(f"{func.__name__} took {elapsed:.2f}ms")
        return result
    return wrapper


class ConnectionPool:
    """Generic connection pool for gRPC or other connections."""
    
    def __init__(self, factory: Callable[[], T], max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self._pool: deque = deque()
        self._lock = threading.Lock()
        self._created = 0
    
    def get(self) -> T:
        """Get a connection from the pool or create a new one."""
        with self._lock:
            if self._pool:
                return self._pool.popleft()
            
            if self._created < self.max_size:
                self._created += 1
                return self.factory()
            
        # Wait for a connection
        while True:
            with self._lock:
                if self._pool:
                    return self._pool.popleft()
            time.sleep(0.01)
    
    def release(self, conn: T) -> None:
        """Return a connection to the pool."""
        with self._lock:
            self._pool.append(conn)
    
    def close_all(self) -> None:
        """Close all connections."""
        with self._lock:
            self._pool.clear()
            self._created = 0

