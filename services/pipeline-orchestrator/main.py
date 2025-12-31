"""
Pipeline Orchestrator Microservice

Orchestrates all AI microservices for attention detection.
Manages the processing flow and aggregates results from all services.
"""

import os
import grpc
from concurrent import futures
import requests
import numpy as np
import cv2
import time
import json
import base64
import redis
import threading
from loguru import logger
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn


# FastAPI app
app = FastAPI(title="Pipeline Orchestrator", version="1.0.0")


class FrameRequest(BaseModel):
    frame_data: str  # base64 encoded image
    meeting_id: str = ""
    request_id: str = ""


class VideoAnalysisRequest(BaseModel):
    analysis_id: str
    video_path: str


class ProcessResponse(BaseModel):
    request_id: str
    meeting_id: str
    participants: List[Dict[str, Any]]
    processing_time_ms: float
    success: bool
    error: str = ""


@dataclass
class ServiceConfig:
    """Service URL configuration."""
    url: str
    name: str
    timeout: float = 5.0


class ServiceRegistry:
    """Service registry with REST URLs."""

    def __init__(self):
        self.services = {
            'face-detection': ServiceConfig(
                os.getenv('FACE_DETECTION_URL', 'http://localhost:8052'),
                'Face Detection'
            ),
            'landmark-detection': ServiceConfig(
                os.getenv('LANDMARK_DETECTION_URL', 'http://localhost:8053'),
                'Landmark Detection'
            ),
            'head-pose': ServiceConfig(
                os.getenv('HEAD_POSE_URL', 'http://localhost:8054'),
                'Head Pose'
            ),
            'gaze-tracking': ServiceConfig(
                os.getenv('GAZE_TRACKING_URL', 'http://localhost:8055'),
                'Gaze Tracking'
            ),
            'blink-detection': ServiceConfig(
                os.getenv('BLINK_DETECTION_URL', 'http://localhost:8056'),
                'Blink Detection'
            ),
            'attention-scorer': ServiceConfig(
                os.getenv('ATTENTION_SCORER_URL', 'http://localhost:8057'),
                'Attention Scorer'
            )
        }

    def get(self, name: str) -> Optional[ServiceConfig]:
        return self.services.get(name)

    def all(self) -> dict:
        return self.services


# Global orchestrator instance
orchestrator_instance = None


class PipelineOrchestrator:
    """Orchestrates the attention detection pipeline across microservices."""

    def __init__(self):
        self.registry = ServiceRegistry()
        self.redis_client = None

        # Connection pooling with optimized settings
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        self.session = requests.Session()

        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,      # Max connections per pool
            max_retries=Retry(total=2, backoff_factor=0.1)
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None

    def process_frame_rest(self, frame_data: str, meeting_id: str, request_id: str) -> Dict[str, Any]:
        """Process frame via REST API calls to microservices."""
        try:
            start_time = time.time()

            # Step 1: Face Detection
            faces = self._detect_faces(frame_data, request_id)
            logger.debug(f"Detected {len(faces)} faces")

            if not faces:
                # Still publish empty result to Redis for real-time updates
                if self.redis_client and meeting_id:
                    self._publish_results(meeting_id, [])
                return self._empty_response(request_id, meeting_id, start_time)

            # Step 2: Landmark Detection
            landmarks_result = self._detect_landmarks(frame_data, faces, request_id)
            logger.debug(f"Landmark result: {len(landmarks_result.get('faces', []))} faces with landmarks")

            results = []
            from concurrent.futures import ThreadPoolExecutor, as_completed

            for face_idx, face_landmarks in enumerate(landmarks_result.get('faces', [])):
                landmarks = face_landmarks.get('landmarks', [])
                # Get bbox from landmark service (more accurate since it's the actual detected face)
                face_bbox = face_landmarks.get('bbox', faces[face_idx] if face_idx < len(faces) else None)
                logger.debug(f"Face {face_idx}: {len(landmarks)} landmarks, bbox: {face_bbox}")

                # Step 3-5: Head pose, gaze, blink - run in parallel for performance
                with ThreadPoolExecutor(max_workers=3) as executor:
                    head_pose_future = executor.submit(self._estimate_head_pose, landmarks, request_id)
                    gaze_future = executor.submit(self._track_gaze, landmarks, request_id)
                    blink_future = executor.submit(self._detect_blink, landmarks, str(face_idx), request_id)

                    head_pose = head_pose_future.result()
                    gaze = gaze_future.result()
                    blink = blink_future.result()

                logger.debug(f"Head pose: yaw={head_pose.get('yaw', 0):.1f}")
                logger.debug(f"Gaze: {gaze}")
                logger.debug(f"Blink: {blink}")

                # Step 6: Attention Scoring
                attention = self._score_attention(
                    str(face_idx), head_pose, gaze, blink, request_id
                )
                logger.debug(f"Attention score: {attention.get('attention_score', 0)}")

                results.append({
                    'track_id': str(face_idx),
                    'face': face_bbox,
                    'head_pose': head_pose,
                    'gaze': gaze,
                    'blink': blink,
                    'attention_score': attention.get('attention_score', 0),
                    'alerts': attention.get('alerts', [])
                })

            total_time = (time.time() - start_time) * 1000

            # Publish to Redis
            if self.redis_client and meeting_id:
                self._publish_results(meeting_id, results)

            return {
                'request_id': request_id,
                'meeting_id': meeting_id,
                'participants': results,
                'processing_time_ms': total_time,
                'success': True,
                'error': ''
            }

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return {
                'request_id': request_id,
                'meeting_id': meeting_id,
                'participants': [],
                'processing_time_ms': 0,
                'success': False,
                'error': str(e)
            }

    def _detect_faces(self, frame_data: str, request_id: str) -> List[Dict]:
        """Call face detection service via REST."""
        try:
            service = self.registry.get('face-detection')
            response = self.session.post(
                f"{service.url}/detect",
                json={'frame_data': frame_data, 'request_id': request_id},
                timeout=service.timeout
            )
            if response.status_code == 200:
                result = response.json()
                return result.get('faces', [])
        except Exception as e:
            logger.error(f"Face detection error: {e}")
        return []

    def _detect_landmarks(self, frame_data: str, faces: List, request_id: str) -> Dict:
        """Call landmark detection service via REST."""
        try:
            service = self.registry.get('landmark-detection')
            response = self.session.post(
                f"{service.url}/detect",
                json={'frame_data': frame_data, 'faces': faces, 'request_id': request_id},
                timeout=service.timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Landmark detection error: {e}")
        return {'faces': []}

    def _estimate_head_pose(self, landmarks: List, request_id: str) -> Dict:
        """Call head pose service via REST."""
        try:
            service = self.registry.get('head-pose')
            response = self.session.post(
                f"{service.url}/estimate",
                json={'landmarks': landmarks, 'request_id': request_id},
                timeout=service.timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Head pose error: {e}")
        return {'yaw': 0, 'pitch': 0, 'roll': 0}

    def _track_gaze(self, landmarks: List, request_id: str) -> Dict:
        """Call gaze tracking service via REST."""
        try:
            service = self.registry.get('gaze-tracking')
            response = self.session.post(
                f"{service.url}/track",
                json={'landmarks': landmarks, 'request_id': request_id},
                timeout=service.timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Gaze tracking error: {e}")
        return {'gaze_x': 0, 'gaze_y': 0, 'is_looking_at_camera': True}

    def _detect_blink(self, landmarks: List, track_id: str, request_id: str) -> Dict:
        """Call blink detection service via REST."""
        try:
            service = self.registry.get('blink-detection')
            response = self.session.post(
                f"{service.url}/detect",
                json={'landmarks': landmarks, 'track_id': track_id, 'request_id': request_id},
                timeout=service.timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Blink detection error: {e}")
        return {'avg_ear': 0.25, 'perclos': 0, 'is_drowsy': False}

    def _score_attention(self, track_id: str, head_pose: Dict, gaze: Dict, blink: Dict, request_id: str) -> Dict:
        """Call attention scorer service via REST."""
        try:
            service = self.registry.get('attention-scorer')
            response = self.session.post(
                f"{service.url}/score",
                json={
                    'track_id': track_id,
                    'head_pose': head_pose,
                    'gaze': gaze,
                    'blink': blink,
                    'request_id': request_id
                },
                timeout=service.timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Attention scoring error: {e}")
        return {'attention_score': 75.0, 'alerts': []}

    def _publish_results(self, meeting_id: str, results: List):
        """Publish results to Redis."""
        channel = f"meeting:{meeting_id}:attention"
        logger.debug(f"Publishing to Redis channel: {channel}, results count: {len(results)}")
        self.redis_client.publish(channel, json.dumps(results))

    def _empty_response(self, request_id: str, meeting_id: str, start_time: float) -> Dict:
        return {
            'request_id': request_id,
            'meeting_id': meeting_id,
            'participants': [],
            'processing_time_ms': (time.time() - start_time) * 1000,
            'success': True,
            'error': ''
        }


# Metrics tracking
metrics_data = {
    "requests_total": 0,
    "requests_success": 0,
    "requests_failed": 0,
    "faces_detected_total": 0,
    "processing_time_sum": 0.0,
    "processing_time_count": 0,
}


# REST endpoints
@app.get("/health")
def health():
    """Health check."""
    global orchestrator_instance
    if orchestrator_instance is None:
        return {"healthy": False, "error": "Not initialized"}
    return {"healthy": True, "version": "1.0.0"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    lines = [
        "# HELP pipeline_requests_total Total number of pipeline requests",
        "# TYPE pipeline_requests_total counter",
        f"pipeline_requests_total {metrics_data['requests_total']}",
        "# HELP pipeline_requests_success Successful pipeline requests",
        "# TYPE pipeline_requests_success counter",
        f"pipeline_requests_success {metrics_data['requests_success']}",
        "# HELP pipeline_requests_failed Failed pipeline requests",
        "# TYPE pipeline_requests_failed counter",
        f"pipeline_requests_failed {metrics_data['requests_failed']}",
        "# HELP faces_detected_total Total faces detected",
        "# TYPE faces_detected_total counter",
        f"faces_detected_total {metrics_data['faces_detected_total']}",
        "# HELP pipeline_processing_seconds Processing time in seconds",
        "# TYPE pipeline_processing_seconds summary",
        f"pipeline_processing_seconds_sum {metrics_data['processing_time_sum']}",
        f"pipeline_processing_seconds_count {metrics_data['processing_time_count']}",
    ]
    return "\n".join(lines)


@app.post("/process", response_model=ProcessResponse)
def process_frame(request: FrameRequest):
    """Process a video frame through the attention detection pipeline."""
    global orchestrator_instance, metrics_data
    if orchestrator_instance is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    start_time = time.time()
    metrics_data["requests_total"] += 1

    try:
        result = orchestrator_instance.process_frame_rest(
            request.frame_data,
            request.meeting_id,
            request.request_id or str(time.time())
        )
        metrics_data["requests_success"] += 1
        metrics_data["faces_detected_total"] += result.get("num_faces", 0)
        return ProcessResponse(**result)
    except Exception as e:
        metrics_data["requests_failed"] += 1
        raise e
    finally:
        elapsed = time.time() - start_time
        metrics_data["processing_time_sum"] += elapsed
        metrics_data["processing_time_count"] += 1


@app.post("/analyze-video")
async def analyze_video(request: VideoAnalysisRequest):
    """Analyze a video file for attention detection."""
    global orchestrator_instance
    if orchestrator_instance is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    # Start async processing in background
    import asyncio
    asyncio.create_task(process_video_async(request.analysis_id, request.video_path))

    return {"status": "processing", "analysis_id": request.analysis_id}


async def process_video_async(analysis_id: str, video_path: str):
    """Process video file asynchronously."""
    global orchestrator_instance

    api_gateway_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8080")

    def update_progress(progress: int, status: str = "processing", **kwargs):
        try:
            data = {"progress": progress, "status": status, **kwargs}
            requests.put(f"{api_gateway_url}/api/v1/video-analysis/{analysis_id}/progress", json=data, timeout=5)
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")

    try:
        update_progress(0, "processing")

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            update_progress(0, "failed", error="Cannot open video file")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        duration = total_frames / fps if fps > 0 else 0

        # Process at 1 fps to save time
        frame_interval = max(1, int(fps))

        timeline = []
        all_alerts = []
        frame_idx = 0
        processed = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                # Encode frame
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')

                # Process frame
                result = orchestrator_instance.process_frame_rest(frame_b64, analysis_id, f"frame_{frame_idx}")

                timestamp_ms = int((frame_idx / fps) * 1000)
                avg_attention = 0
                if result.get('participants'):
                    scores = [p.get('attention_score', 0) for p in result['participants']]
                    avg_attention = sum(scores) / len(scores) if scores else 0

                    for p in result['participants']:
                        for alert in p.get('alerts', []):
                            all_alerts.append({**alert, 'timestamp_ms': timestamp_ms})

                timeline.append({
                    'timestamp_ms': timestamp_ms,
                    'faces': result.get('participants', []),
                    'avg_attention': avg_attention
                })

                processed += 1
                progress = min(95, int((frame_idx / total_frames) * 100))
                if processed % 10 == 0:
                    update_progress(progress)

            frame_idx += 1

        cap.release()

        # Calculate summary
        avg_scores = [t['avg_attention'] for t in timeline if t['avg_attention'] > 0]
        summary = {
            'duration': duration,
            'total_frames': total_frames,
            'analyzed_frames': len(timeline),
            'avg_attention': sum(avg_scores) / len(avg_scores) if avg_scores else 0,
            'min_attention': min(avg_scores) if avg_scores else 0,
            'max_attention': max(avg_scores) if avg_scores else 0,
            'total_alerts': len(all_alerts),
            'timeline': timeline,
            'alerts': all_alerts
        }

        update_progress(100, "completed", duration=duration, results=json.dumps(summary))
        logger.info(f"Video analysis completed: {analysis_id}")

    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        update_progress(0, "failed", error=str(e))


def run_rest_server(port: int):
    """Run REST server."""
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def serve(grpc_port: int = 50051, rest_port: int = 8051):
    """Start both gRPC and REST servers."""
    global orchestrator_instance

    orchestrator_instance = PipelineOrchestrator()

    # Start REST server in background
    rest_thread = threading.Thread(target=run_rest_server, args=(rest_port,), daemon=True)
    rest_thread.start()
    logger.info(f"🌐 REST API started on port {rest_port}")

    # Start gRPC server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=20),
        options=[
            ('grpc.max_receive_message_length', 100 * 1024 * 1024),
            ('grpc.max_send_message_length', 100 * 1024 * 1024),
        ]
    )

    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()

    logger.info(f"🎬 Pipeline Orchestrator started")
    logger.info(f"   gRPC: port {grpc_port}, REST: port {rest_port}")
    logger.info(f"   Services: {list(orchestrator_instance.registry.all().keys())}")

    server.wait_for_termination()


if __name__ == "__main__":
    grpc_port = int(os.environ.get("GRPC_PORT", 50051))
    rest_port = int(os.environ.get("REST_PORT", 8051))
    serve(grpc_port, rest_port)

