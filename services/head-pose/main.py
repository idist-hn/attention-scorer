"""
Head Pose Estimation Microservice

Standalone gRPC + REST service for head pose estimation using PnP algorithm.
Estimates yaw, pitch, roll from facial landmarks.
"""

import os
import grpc
from concurrent import futures
import numpy as np
import cv2
import time
import threading
from loguru import logger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn


app = FastAPI(title="Head Pose Service", version="1.0.0")


class EstimateRequest(BaseModel):
    landmarks: List[Dict[str, Any]]
    frame_width: int = 640
    frame_height: int = 480
    request_id: str = ""


class EstimateResponse(BaseModel):
    yaw: float
    pitch: float
    roll: float
    request_id: str = ""
    success: bool = True
    error: str = ""


servicer_instance = None


# 3D model points for head pose estimation
MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye left corner
    (225.0, 170.0, -135.0),      # Right eye right corner
    (-150.0, -150.0, -125.0),    # Left Mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)

# MediaPipe landmark indices
LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]


class HeadPoseServicer:
    """gRPC servicer for head pose estimation."""
    
    def __init__(self):
        self.version = "1.0.0"
        self.camera_matrix = None
        self.dist_coeffs = np.zeros((4, 1), dtype=np.float64)
    
    def _get_camera_matrix(self, width: int, height: int) -> np.ndarray:
        """Get camera intrinsic matrix."""
        focal_length = width
        center = (width / 2, height / 2)
        return np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
    
    def EstimatePose(self, request, context):
        """Estimate head pose from landmarks."""
        try:
            start_time = time.time()
            
            landmarks = request.landmarks
            if len(landmarks) < max(LANDMARK_INDICES) + 1:
                return self._error_response(request.request_id, "Insufficient landmarks")
            
            # Get camera matrix
            camera_matrix = self._get_camera_matrix(
                request.frame_width, request.frame_height
            )
            
            # Extract 2D image points from landmarks
            image_points = np.array([
                (landmarks[idx].x, landmarks[idx].y)
                for idx in LANDMARK_INDICES
            ], dtype=np.float64)
            
            # Solve PnP
            success, rotation_vector, translation_vector = cv2.solvePnP(
                MODEL_POINTS,
                image_points,
                camera_matrix,
                self.dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
            
            if not success:
                return self._error_response(request.request_id, "PnP failed")
            
            # Convert rotation vector to Euler angles
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            
            # Calculate Euler angles
            sy = np.sqrt(rotation_matrix[0, 0]**2 + rotation_matrix[1, 0]**2)
            singular = sy < 1e-6
            
            if not singular:
                pitch = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
                yaw = np.arctan2(-rotation_matrix[2, 0], sy)
                roll = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
            else:
                pitch = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
                yaw = np.arctan2(-rotation_matrix[2, 0], sy)
                roll = 0
            
            # Convert to degrees
            yaw_deg = np.degrees(yaw)
            pitch_deg = np.degrees(pitch)
            roll_deg = np.degrees(roll)
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'request_id': request.request_id,
                'pose': {
                    'yaw': yaw_deg,
                    'pitch': pitch_deg,
                    'roll': roll_deg,
                    'rotation_vector': rotation_vector.flatten().tolist(),
                    'translation_vector': translation_vector.flatten().tolist()
                },
                'processing_time_ms': processing_time,
                'success': True,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Head pose estimation error: {e}")
            return self._error_response(request.request_id, str(e))
    
    def BatchEstimate(self, request, context):
        """Batch estimation."""
        responses = [self.EstimatePose(req, context) for req in request.requests]
        return {'responses': responses}
    
    def Health(self, request, context):
        """Health check."""
        return {'healthy': True, 'version': self.version}
    
    def _error_response(self, request_id: str, error: str):
        return {
            'request_id': request_id,
            'pose': None,
            'processing_time_ms': 0,
            'success': False,
            'error': error
        }


@app.get("/health")
def health():
    global servicer_instance
    return {"healthy": servicer_instance is not None, "version": "1.0.0"}


@app.post("/estimate", response_model=EstimateResponse)
def estimate(request: EstimateRequest):
    global servicer_instance
    if servicer_instance is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        landmarks = request.landmarks
        if len(landmarks) < max(LANDMARK_INDICES) + 1:
            return EstimateResponse(yaw=0, pitch=0, roll=0, request_id=request.request_id,
                                   success=False, error="Insufficient landmarks")

        camera_matrix = servicer_instance._get_camera_matrix(request.frame_width, request.frame_height)

        image_points = np.array([
            (landmarks[idx]['x'], landmarks[idx]['y'])
            for idx in LANDMARK_INDICES
        ], dtype=np.float64)

        success, rotation_vector, translation_vector = cv2.solvePnP(
            MODEL_POINTS, image_points, camera_matrix,
            servicer_instance.dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return EstimateResponse(yaw=0, pitch=0, roll=0, request_id=request.request_id,
                                   success=False, error="PnP failed")

        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        sy = np.sqrt(rotation_matrix[0, 0]**2 + rotation_matrix[1, 0]**2)

        if sy >= 1e-6:
            pitch = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            yaw = np.arctan2(-rotation_matrix[2, 0], sy)
            roll = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
        else:
            pitch = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
            yaw = np.arctan2(-rotation_matrix[2, 0], sy)
            roll = 0

        return EstimateResponse(
            yaw=float(np.degrees(yaw)),
            pitch=float(np.degrees(pitch)),
            roll=float(np.degrees(roll)),
            request_id=request.request_id,
            success=True
        )
    except Exception as e:
        return EstimateResponse(yaw=0, pitch=0, roll=0, request_id=request.request_id,
                               success=False, error=str(e))


def run_rest_server(port: int):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def serve(grpc_port: int = 50054, rest_port: int = 8054):
    global servicer_instance
    servicer_instance = HeadPoseServicer()

    rest_thread = threading.Thread(target=run_rest_server, args=(rest_port,), daemon=True)
    rest_thread.start()
    logger.info(f"🌐 REST API on port {rest_port}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()
    logger.info(f"🔄 Head Pose Service started (gRPC: {grpc_port})")
    server.wait_for_termination()


if __name__ == "__main__":
    grpc_port = int(os.environ.get("GRPC_PORT", 50054))
    rest_port = int(os.environ.get("REST_PORT", 8054))
    serve(grpc_port, rest_port)

