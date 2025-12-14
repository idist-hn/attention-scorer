"""
Face Detection Microservice

Standalone gRPC + REST service for face detection using MediaPipe.
Can be scaled independently and deployed on GPU nodes.
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
from typing import List, Optional
import uvicorn


# FastAPI app for REST endpoints
app = FastAPI(title="Face Detection Service", version="1.0.0")


class DetectRequest(BaseModel):
    frame_data: str  # base64 encoded image
    request_id: str = ""
    confidence_threshold: float = 0.5


class Face(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


class DetectResponse(BaseModel):
    request_id: str
    faces: List[Face]
    processing_time_ms: float
    success: bool
    error: str = ""


# Global servicer instance
servicer_instance = None


class FaceDetectionServicer:
    """gRPC servicer for face detection using MediaPipe."""

    def __init__(self, model_path: str = "", device: str = "cpu"):
        self.device = device
        self.model_path = model_path
        self.face_detection = None
        self.version = "1.0.0"
        self._load_model()

    def _load_model(self):
        """Load MediaPipe Face Detection model."""
        logger.info("Loading MediaPipe Face Detection model")
        logger.info(f"Using device: {self.device}")

        # Close existing instance if any
        if self.face_detection is not None:
            try:
                self.face_detection.close()
            except:
                pass

        mp_face_detection = mp.solutions.face_detection
        # Use short-range model (0) with lower confidence for better detection
        # model_selection=0: short-range (2m), better for webcam
        # model_selection=1: full-range (5m), for larger distances
        self.face_detection = mp_face_detection.FaceDetection(
            model_selection=0,  # Short-range model works better for webcam
            min_detection_confidence=0.3  # Lower threshold for better detection
        )
        self._error_count = 0

        logger.info("Face detection model loaded successfully (short-range, confidence=0.3)")
    
    def DetectFaces(self, request, context):
        """Detect faces in a frame using MediaPipe."""
        try:
            start_time = time.time()

            # Decode frame
            nparr = np.frombuffer(request.frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                logger.error(f"Failed to decode frame, data length: {len(request.frame_data)}")
                return self._error_response(request.request_id, "Failed to decode frame")

            h, w = frame.shape[:2]
            logger.debug(f"Frame decoded: {w}x{h}")

            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Run detection with error recovery
            try:
                results = self.face_detection.process(rgb_frame)
                self._error_count = 0  # Reset on success
            except Exception as process_error:
                self._error_count = getattr(self, '_error_count', 0) + 1
                logger.warning(f"MediaPipe process error (count={self._error_count}): {process_error}")

                # Reinitialize model after errors
                if self._error_count >= 2:
                    logger.info("Reinitializing MediaPipe Face Detection due to errors")
                    self._load_model()

                return self._error_response(request.request_id, f"Process error: {process_error}")

            # Parse results
            faces = []
            if results and results.detections:
                logger.debug(f"MediaPipe detected {len(results.detections)} faces")
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    x1 = max(0, bbox.xmin * w)
                    y1 = max(0, bbox.ymin * h)
                    x2 = min(w, (bbox.xmin + bbox.width) * w)
                    y2 = min(h, (bbox.ymin + bbox.height) * h)
                    conf = detection.score[0] if detection.score else 0.5

                    faces.append({
                        'x1': float(x1),
                        'y1': float(y1),
                        'x2': float(x2),
                        'y2': float(y2),
                        'confidence': float(conf)
                    })

            processing_time = (time.time() - start_time) * 1000

            return {
                'request_id': request.request_id,
                'faces': faces,
                'processing_time_ms': processing_time,
                'success': True,
                'error': ''
            }

        except Exception as e:
            logger.error(f"Detection error: {e}")
            return self._error_response(request.request_id, str(e))
    
    def StreamDetect(self, request_iterator, context):
        """Stream detection for real-time processing."""
        for request in request_iterator:
            yield self.DetectFaces(request, context)
    
    def Health(self, request, context):
        """Health check."""
        return {
            'healthy': self.face_detection is not None,
            'version': self.version,
            'device': self.device
        }
    
    def _error_response(self, request_id: str, error: str):
        return {
            'request_id': request_id,
            'faces': [],
            'processing_time_ms': 0,
            'success': False,
            'error': error
        }


# REST endpoints
@app.get("/health")
def health():
    """Health check endpoint."""
    global servicer_instance
    if servicer_instance is None:
        return {"healthy": False, "error": "Model not loaded"}
    return {"healthy": True, "version": servicer_instance.version, "device": servicer_instance.device}


@app.post("/detect", response_model=DetectResponse)
def detect(request: DetectRequest):
    """Detect faces in an image."""
    global servicer_instance
    if servicer_instance is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Decode base64 image
        if "," in request.frame_data:
            request.frame_data = request.frame_data.split(",")[1]

        frame_bytes = base64.b64decode(request.frame_data)

        # Create mock request object
        class MockRequest:
            def __init__(self):
                self.frame_data = frame_bytes
                self.request_id = request.request_id
                self.confidence_threshold = request.confidence_threshold

        mock_req = MockRequest()
        result = servicer_instance.DetectFaces(mock_req, None)

        return DetectResponse(**result)
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def run_rest_server(port: int):
    """Run REST server."""
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def serve(grpc_port: int = 50052, rest_port: int = 8052):
    """Start both gRPC and REST servers."""
    global servicer_instance

    device = os.environ.get("DEVICE", "cpu")
    model_path = os.environ.get("MODEL_PATH", "yolov8n.pt")

    # Initialize servicer
    servicer_instance = FaceDetectionServicer(model_path=model_path, device=device)

    # Start REST server in background thread
    rest_thread = threading.Thread(target=run_rest_server, args=(rest_port,), daemon=True)
    rest_thread.start()
    logger.info(f"🌐 REST API started on port {rest_port}")

    # Start gRPC server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
        ]
    )

    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()

    logger.info(f"🔍 Face Detection Service started")
    logger.info(f"   gRPC: port {grpc_port}, REST: port {rest_port}")
    logger.info(f"   Device: {device}, Model: {model_path}")

    server.wait_for_termination()


if __name__ == "__main__":
    grpc_port = int(os.environ.get("GRPC_PORT", 50052))
    rest_port = int(os.environ.get("REST_PORT", 8052))
    serve(grpc_port, rest_port)

