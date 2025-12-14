"""
Gaze Tracking Microservice

Standalone gRPC + REST service for iris-based gaze estimation.
Tracks eye gaze direction from facial landmarks.
"""

import os
import grpc
from concurrent import futures
import numpy as np
import time
import threading
from loguru import logger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn


app = FastAPI(title="Gaze Tracking Service", version="1.0.0")


class TrackRequest(BaseModel):
    landmarks: List[Dict[str, Any]]
    request_id: str = ""


class TrackResponse(BaseModel):
    gaze_x: float
    gaze_y: float
    is_looking_at_camera: bool
    gaze_angle: float = 0
    request_id: str = ""
    success: bool = True
    error: str = ""


servicer_instance = None


# MediaPipe iris landmark indices
LEFT_IRIS = [468, 469, 470, 471, 472]
RIGHT_IRIS = [473, 474, 475, 476, 477]
LEFT_EYE_CENTER = [33, 133]   # Inner and outer corners
RIGHT_EYE_CENTER = [362, 263]


class GazeTrackingServicer:
    """gRPC servicer for gaze tracking."""
    
    def __init__(self):
        self.version = "1.0.0"
        self.gaze_threshold = 0.3  # Threshold for looking at camera
    
    def EstimateGaze(self, request, context):
        """Estimate gaze direction from landmarks."""
        try:
            start_time = time.time()
            
            landmarks = {lm.index: (lm.x, lm.y, lm.z) for lm in request.landmarks}
            
            # Check if iris landmarks are available
            if not all(idx in landmarks for idx in LEFT_IRIS + RIGHT_IRIS):
                return self._error_response(request.request_id, "Iris landmarks not available")
            
            # Calculate iris centers
            left_iris_x = np.mean([landmarks[i][0] for i in LEFT_IRIS])
            left_iris_y = np.mean([landmarks[i][1] for i in LEFT_IRIS])
            
            right_iris_x = np.mean([landmarks[i][0] for i in RIGHT_IRIS])
            right_iris_y = np.mean([landmarks[i][1] for i in RIGHT_IRIS])
            
            # Calculate eye centers
            left_eye_cx = (landmarks[33][0] + landmarks[133][0]) / 2
            left_eye_cy = (landmarks[33][1] + landmarks[133][1]) / 2
            left_eye_width = abs(landmarks[133][0] - landmarks[33][0])
            
            right_eye_cx = (landmarks[362][0] + landmarks[263][0]) / 2
            right_eye_cy = (landmarks[362][1] + landmarks[263][1]) / 2
            right_eye_width = abs(landmarks[263][0] - landmarks[362][0])
            
            # Calculate relative iris position (-1 to 1)
            left_gaze_x = (left_iris_x - left_eye_cx) / (left_eye_width / 2) if left_eye_width > 0 else 0
            right_gaze_x = (right_iris_x - right_eye_cx) / (right_eye_width / 2) if right_eye_width > 0 else 0
            
            # Average gaze
            gaze_x = (left_gaze_x + right_gaze_x) / 2
            gaze_y = 0  # Simplified - would need more landmarks for accurate Y
            
            # Calculate gaze angle
            gaze_angle = np.degrees(np.arctan2(abs(gaze_x), 1))
            
            # Determine if looking at camera
            is_looking_at_camera = abs(gaze_x) < self.gaze_threshold
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'request_id': request.request_id,
                'gaze': {
                    'gaze_x': float(gaze_x),
                    'gaze_y': float(gaze_y),
                    'left_iris_x': float(left_iris_x),
                    'left_iris_y': float(left_iris_y),
                    'right_iris_x': float(right_iris_x),
                    'right_iris_y': float(right_iris_y),
                    'is_looking_at_camera': is_looking_at_camera,
                    'gaze_angle': float(gaze_angle)
                },
                'processing_time_ms': processing_time,
                'success': True,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Gaze tracking error: {e}")
            return self._error_response(request.request_id, str(e))
    
    def BatchEstimate(self, request, context):
        """Batch estimation."""
        responses = [self.EstimateGaze(req, context) for req in request.requests]
        return {'responses': responses}
    
    def Health(self, request, context):
        """Health check."""
        return {'healthy': True, 'version': self.version}
    
    def _error_response(self, request_id: str, error: str):
        return {
            'request_id': request_id,
            'gaze': None,
            'processing_time_ms': 0,
            'success': False,
            'error': error
        }


@app.get("/health")
def health():
    global servicer_instance
    return {"healthy": servicer_instance is not None, "version": "1.0.0"}


@app.post("/track", response_model=TrackResponse)
def track(request: TrackRequest):
    global servicer_instance
    if servicer_instance is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        landmarks = {lm['index']: (lm['x'], lm['y'], lm.get('z', 0)) for lm in request.landmarks}

        # Check iris landmarks
        if not all(idx in landmarks for idx in LEFT_IRIS + RIGHT_IRIS):
            return TrackResponse(gaze_x=0, gaze_y=0, is_looking_at_camera=True,
                                request_id=request.request_id, success=False,
                                error="Iris landmarks not available")

        # Calculate iris centers
        left_iris_x = np.mean([landmarks[i][0] for i in LEFT_IRIS])
        right_iris_x = np.mean([landmarks[i][0] for i in RIGHT_IRIS])

        # Calculate eye centers
        left_eye_cx = (landmarks[33][0] + landmarks[133][0]) / 2
        left_eye_width = abs(landmarks[133][0] - landmarks[33][0])
        right_eye_cx = (landmarks[362][0] + landmarks[263][0]) / 2
        right_eye_width = abs(landmarks[263][0] - landmarks[362][0])

        # Calculate relative gaze
        left_gaze_x = (left_iris_x - left_eye_cx) / (left_eye_width / 2) if left_eye_width > 0 else 0
        right_gaze_x = (right_iris_x - right_eye_cx) / (right_eye_width / 2) if right_eye_width > 0 else 0
        gaze_x = (left_gaze_x + right_gaze_x) / 2

        gaze_angle = float(np.degrees(np.arctan2(abs(gaze_x), 1)))
        is_looking = abs(gaze_x) < servicer_instance.gaze_threshold

        return TrackResponse(
            gaze_x=float(gaze_x), gaze_y=0.0, is_looking_at_camera=is_looking,
            gaze_angle=gaze_angle, request_id=request.request_id
        )
    except Exception as e:
        return TrackResponse(gaze_x=0, gaze_y=0, is_looking_at_camera=True,
                            request_id=request.request_id, success=False, error=str(e))


def run_rest_server(port: int):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def serve(grpc_port: int = 50055, rest_port: int = 8055):
    global servicer_instance
    servicer_instance = GazeTrackingServicer()

    rest_thread = threading.Thread(target=run_rest_server, args=(rest_port,), daemon=True)
    rest_thread.start()
    logger.info(f"🌐 REST API on port {rest_port}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()
    logger.info(f"👀 Gaze Tracking Service started (gRPC: {grpc_port})")
    server.wait_for_termination()


if __name__ == "__main__":
    grpc_port = int(os.environ.get("GRPC_PORT", 50055))
    rest_port = int(os.environ.get("REST_PORT", 8055))
    serve(grpc_port, rest_port)

