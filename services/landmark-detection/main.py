"""
Landmark Detection Microservice

Standalone gRPC + REST service for MediaPipe FaceMesh landmark detection.
Detects 478 facial landmarks for each face.
"""

import os
import grpc
from concurrent import futures
import numpy as np
import cv2
import time
import base64
import threading
from loguru import logger
import mediapipe as mp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn


app = FastAPI(title="Landmark Detection Service", version="1.0.0")


class DetectRequest(BaseModel):
    frame_data: str
    faces: List[Dict[str, Any]] = []
    request_id: str = ""


class DetectResponse(BaseModel):
    request_id: str
    faces: List[Dict[str, Any]]
    processing_time_ms: float
    success: bool
    error: str = ""


servicer_instance = None


class LandmarkDetectionServicer:
    """gRPC servicer for landmark detection."""

    def __init__(self):
        self.version = "1.0.0"
        self.mp_face_mesh = mp.solutions.face_mesh
        self._lock = threading.Lock()
        self._error_count = 0
        self._max_errors = 3
        self._create_face_mesh()

    def _create_face_mesh(self):
        """Create a new MediaPipe FaceMesh instance."""
        logger.info("Creating MediaPipe FaceMesh instance")
        if hasattr(self, 'face_mesh') and self.face_mesh is not None:
            try:
                self.face_mesh.close()
            except:
                pass

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,  # Process each frame independently
            max_num_faces=20,
            refine_landmarks=True,  # Include iris landmarks
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self._error_count = 0
        logger.info("Landmark detection initialized successfully")
    
    def DetectLandmarks(self, request, context):
        """Detect landmarks in face regions."""
        start_time = time.time()

        # Decode frame
        nparr = np.frombuffer(request.frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return self._error_response(request.request_id, "Failed to decode frame")

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]

        # Process with MediaPipe - with error recovery
        results = None
        for attempt in range(2):
            try:
                with self._lock:
                    results = self.face_mesh.process(rgb_frame)
                    self._error_count = 0  # Reset on success
                break
            except Exception as e:
                logger.warning(f"MediaPipe error (attempt {attempt + 1}): {e}")
                with self._lock:
                    self._error_count += 1
                    if self._error_count >= self._max_errors or "timestamp" in str(e).lower():
                        logger.info("Recreating FaceMesh due to errors")
                        self._create_face_mesh()

        faces = []
        if results and results.multi_face_landmarks:
            for face_idx, face_landmarks in enumerate(results.multi_face_landmarks):
                landmarks = []
                min_x, min_y = float('inf'), float('inf')
                max_x, max_y = 0, 0

                for idx, lm in enumerate(face_landmarks.landmark):
                    x_px = lm.x * w
                    y_px = lm.y * h
                    landmarks.append({
                        'index': idx,
                        'x': x_px,
                        'y': y_px,
                        'z': lm.z * w  # Z is relative to width
                    })
                    # Calculate bounding box from landmarks
                    min_x = min(min_x, x_px)
                    min_y = min(min_y, y_px)
                    max_x = max(max_x, x_px)
                    max_y = max(max_y, y_px)

                # Add padding to bbox (10%)
                padding_x = (max_x - min_x) * 0.1
                padding_y = (max_y - min_y) * 0.1

                faces.append({
                    'face_index': face_idx,
                    'landmarks': landmarks,
                    'bbox': {
                        'x1': max(0, min_x - padding_x),
                        'y1': max(0, min_y - padding_y),
                        'x2': min(w, max_x + padding_x),
                        'y2': min(h, max_y + padding_y),
                        'confidence': 0.95  # FaceMesh is usually confident
                    }
                })

        processing_time = (time.time() - start_time) * 1000

        return {
            'request_id': request.request_id,
            'faces': faces,
            'processing_time_ms': processing_time,
            'success': True,
            'error': ''
        }
    
    def StreamDetect(self, request_iterator, context):
        """Stream detection."""
        for request in request_iterator:
            yield self.DetectLandmarks(request, context)
    
    def Health(self, request, context):
        """Health check."""
        return {
            'healthy': self.face_mesh is not None,
            'version': self.version
        }
    
    def _error_response(self, request_id: str, error: str):
        return {
            'request_id': request_id,
            'faces': [],
            'processing_time_ms': 0,
            'success': False,
            'error': error
        }
    
    def __del__(self):
        if self.face_mesh:
            self.face_mesh.close()


@app.get("/health")
def health():
    global servicer_instance
    if servicer_instance is None:
        return {"healthy": False}
    return {"healthy": True, "version": servicer_instance.version}


@app.post("/detect", response_model=DetectResponse)
def detect(request: DetectRequest):
    global servicer_instance
    if servicer_instance is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        if "," in request.frame_data:
            request.frame_data = request.frame_data.split(",")[1]
        frame_bytes = base64.b64decode(request.frame_data)

        class MockRequest:
            def __init__(self):
                self.frame_data = frame_bytes
                self.request_id = request.request_id

        result = servicer_instance.DetectLandmarks(MockRequest(), None)
        return DetectResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_rest_server(port: int):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def serve(grpc_port: int = 50053, rest_port: int = 8053):
    global servicer_instance
    servicer_instance = LandmarkDetectionServicer()

    rest_thread = threading.Thread(target=run_rest_server, args=(rest_port,), daemon=True)
    rest_thread.start()
    logger.info(f"🌐 REST API on port {rest_port}")

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
        ]
    )

    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()

    logger.info(f"👁️ Landmark Detection Service started (gRPC: {grpc_port})")
    server.wait_for_termination()


if __name__ == "__main__":
    grpc_port = int(os.environ.get("GRPC_PORT", 50053))
    rest_port = int(os.environ.get("REST_PORT", 8053))
    serve(grpc_port, rest_port)

