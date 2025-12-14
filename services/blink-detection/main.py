"""
Blink Detection Microservice

Standalone gRPC + REST service for EAR-based blink and drowsiness detection.
Tracks blink patterns and calculates PERCLOS metric.
"""

import os
import grpc
from concurrent import futures
import numpy as np
import time
import threading
from loguru import logger
from collections import deque
from dataclasses import dataclass, field
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn


app = FastAPI(title="Blink Detection Service", version="1.0.0")


class DetectRequest(BaseModel):
    landmarks: List[Dict[str, Any]]
    track_id: str = "0"
    request_id: str = ""


class DetectResponse(BaseModel):
    avg_ear: float
    perclos: float
    is_drowsy: bool
    is_blinking: bool = False
    blink_count: int = 0
    request_id: str = ""
    success: bool = True
    error: str = ""


servicer_instance = None


# Eye landmark indices (MediaPipe)
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]


@dataclass
class TrackState:
    """State for a tracked face."""
    ear_history: deque = field(default_factory=lambda: deque(maxlen=90))  # 3 seconds at 30fps
    blink_count: int = 0
    last_blink_time: float = 0
    is_eye_closed: bool = False
    closed_frames: int = 0
    start_time: float = field(default_factory=time.time)


class BlinkDetectionServicer:
    """gRPC servicer for blink detection."""
    
    def __init__(self):
        self.version = "1.0.0"
        self.ear_threshold = 0.21
        self.consecutive_frames = 2
        self.perclos_threshold = 0.8
        self.track_states: dict[str, TrackState] = {}
    
    def _calculate_ear(self, landmarks: dict, eye_indices: list) -> float:
        """Calculate Eye Aspect Ratio."""
        try:
            p = [landmarks[i] for i in eye_indices]
            
            # Vertical distances
            v1 = np.sqrt((p[1][0] - p[5][0])**2 + (p[1][1] - p[5][1])**2)
            v2 = np.sqrt((p[2][0] - p[4][0])**2 + (p[2][1] - p[4][1])**2)
            
            # Horizontal distance
            h = np.sqrt((p[0][0] - p[3][0])**2 + (p[0][1] - p[3][1])**2)
            
            if h == 0:
                return 0.0
            
            return (v1 + v2) / (2.0 * h)
        except:
            return 0.0
    
    def AnalyzeBlink(self, request, context):
        """Analyze blink from landmarks."""
        try:
            start_time = time.time()
            
            track_id = request.track_id
            landmarks = {lm.index: (lm.x, lm.y, lm.z) for lm in request.landmarks}
            
            # Get or create track state
            if track_id not in self.track_states:
                self.track_states[track_id] = TrackState()
            state = self.track_states[track_id]
            
            # Calculate EAR for both eyes
            left_ear = self._calculate_ear(landmarks, LEFT_EYE)
            right_ear = self._calculate_ear(landmarks, RIGHT_EYE)
            avg_ear = (left_ear + right_ear) / 2
            
            # Update history
            state.ear_history.append(avg_ear)
            
            # Blink detection
            is_blinking = avg_ear < self.ear_threshold
            
            if is_blinking:
                state.closed_frames += 1
                if not state.is_eye_closed and state.closed_frames >= self.consecutive_frames:
                    state.is_eye_closed = True
            else:
                if state.is_eye_closed:
                    state.blink_count += 1
                    state.last_blink_time = time.time()
                state.is_eye_closed = False
                state.closed_frames = 0
            
            # Calculate PERCLOS
            if len(state.ear_history) > 0:
                closed_count = sum(1 for ear in state.ear_history if ear < self.ear_threshold)
                perclos = (closed_count / len(state.ear_history)) * 100
            else:
                perclos = 0
            
            # Drowsiness detection
            is_drowsy = perclos > (self.perclos_threshold * 100)
            
            # Calculate blink rate (per minute)
            elapsed = time.time() - state.start_time
            blink_rate = (state.blink_count / elapsed * 60) if elapsed > 0 else 0
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'request_id': request.request_id,
                'blink': {
                    'left_ear': float(left_ear),
                    'right_ear': float(right_ear),
                    'avg_ear': float(avg_ear),
                    'perclos': float(perclos),
                    'is_blinking': is_blinking,
                    'is_drowsy': is_drowsy,
                    'blink_count': state.blink_count,
                    'blink_rate': float(blink_rate)
                },
                'processing_time_ms': processing_time,
                'success': True,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Blink detection error: {e}")
            return self._error_response(request.request_id, str(e))
    
    def ResetTrack(self, request, context):
        """Reset state for a track."""
        if request.track_id in self.track_states:
            del self.track_states[request.track_id]
        return {'success': True}
    
    def Health(self, request, context):
        """Health check."""
        return {'healthy': True, 'version': self.version}
    
    def _error_response(self, request_id: str, error: str):
        return {
            'request_id': request_id,
            'blink': None,
            'processing_time_ms': 0,
            'success': False,
            'error': error
        }


@app.get("/health")
def health():
    global servicer_instance
    return {"healthy": servicer_instance is not None, "version": "1.0.0"}


@app.post("/detect", response_model=DetectResponse)
def detect(request: DetectRequest):
    global servicer_instance
    if servicer_instance is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        landmarks = {lm['index']: (lm['x'], lm['y'], lm.get('z', 0)) for lm in request.landmarks}
        track_id = request.track_id

        if track_id not in servicer_instance.track_states:
            servicer_instance.track_states[track_id] = TrackState()
        state = servicer_instance.track_states[track_id]

        # Calculate EAR
        left_ear = servicer_instance._calculate_ear(landmarks, LEFT_EYE)
        right_ear = servicer_instance._calculate_ear(landmarks, RIGHT_EYE)
        avg_ear = (left_ear + right_ear) / 2

        state.ear_history.append(avg_ear)
        is_blinking = avg_ear < servicer_instance.ear_threshold

        if is_blinking:
            state.closed_frames += 1
            if not state.is_eye_closed and state.closed_frames >= servicer_instance.consecutive_frames:
                state.is_eye_closed = True
        else:
            if state.is_eye_closed:
                state.blink_count += 1
            state.is_eye_closed = False
            state.closed_frames = 0

        # PERCLOS
        if len(state.ear_history) > 0:
            closed_count = sum(1 for ear in state.ear_history if ear < servicer_instance.ear_threshold)
            perclos = (closed_count / len(state.ear_history)) * 100
        else:
            perclos = 0

        is_drowsy = perclos > (servicer_instance.perclos_threshold * 100)

        return DetectResponse(
            avg_ear=float(avg_ear), perclos=float(perclos), is_drowsy=is_drowsy,
            is_blinking=is_blinking, blink_count=state.blink_count,
            request_id=request.request_id
        )
    except Exception as e:
        return DetectResponse(avg_ear=0.25, perclos=0, is_drowsy=False,
                             request_id=request.request_id, success=False, error=str(e))


def run_rest_server(port: int):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def serve(grpc_port: int = 50056, rest_port: int = 8056):
    global servicer_instance
    servicer_instance = BlinkDetectionServicer()

    rest_thread = threading.Thread(target=run_rest_server, args=(rest_port,), daemon=True)
    rest_thread.start()
    logger.info(f"🌐 REST API on port {rest_port}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()
    logger.info(f"😴 Blink Detection Service started (gRPC: {grpc_port})")
    server.wait_for_termination()


if __name__ == "__main__":
    grpc_port = int(os.environ.get("GRPC_PORT", 50056))
    rest_port = int(os.environ.get("REST_PORT", 8056))
    serve(grpc_port, rest_port)

