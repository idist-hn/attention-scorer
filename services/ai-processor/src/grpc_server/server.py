"""gRPC Server for AI Processing Service."""

import grpc
from concurrent import futures
import numpy as np
import cv2
import time
from loguru import logger

from ..config import Settings
from ..pipeline.attention_pipeline import AttentionPipeline


class AttentionServicer:
    """gRPC Servicer for attention detection."""
    
    def __init__(self, pipeline: AttentionPipeline):
        self.pipeline = pipeline
        self.active_sessions = 0
        self.version = "1.0.0"
    
    def ProcessFrame(self, request, context):
        """Process a single frame."""
        try:
            # Decode frame
            nparr = np.frombuffer(request.frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return self._error_response(request, "Failed to decode frame")
            
            # Process frame
            start_time = time.time()
            results = self.pipeline.process_frame(frame)
            processing_time = (time.time() - start_time) * 1000
            
            # Build response
            response = {
                'meeting_id': request.meeting_id,
                'participant_id': request.participant_id,
                'timestamp': request.timestamp,
                'faces': self._convert_results(results),
                'processing_time_ms': processing_time,
                'success': True,
                'error_message': ''
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return self._error_response(request, str(e))
    
    def StreamFrames(self, request_iterator, context):
        """Stream processing for real-time frames."""
        self.active_sessions += 1
        try:
            for request in request_iterator:
                yield self.ProcessFrame(request, context)
        finally:
            self.active_sessions -= 1
    
    def HealthCheck(self, request, context):
        """Health check endpoint."""
        return {
            'healthy': True,
            'version': self.version,
            'device': self.pipeline.device,
            'gpu_memory_used_mb': 0.0,
            'active_sessions': self.active_sessions
        }
    
    def _convert_results(self, results):
        """Convert pipeline results to gRPC format."""
        faces = []
        for result in results:
            face = {
                'track_id': result.track_id,
                'bbox': {
                    'x1': result.bbox[0],
                    'y1': result.bbox[1],
                    'x2': result.bbox[2],
                    'y2': result.bbox[3],
                    'confidence': result.confidence
                },
                'attention': {
                    'attention_score': result.attention_score,
                    'gaze_score': result.gaze_score,
                    'head_pose_score': result.head_pose_score,
                    'eye_openness_score': result.eye_openness_score,
                    'presence_score': result.presence_score,
                    'attention_level': result.attention_level,
                    'is_attentive': result.is_attentive
                },
                'head_pose': {
                    'yaw': result.head_pose.get('yaw', 0),
                    'pitch': result.head_pose.get('pitch', 0),
                    'roll': result.head_pose.get('roll', 0)
                },
                'gaze': {
                    'gaze_x': result.gaze_direction[0] if result.gaze_direction else 0,
                    'gaze_y': result.gaze_direction[1] if result.gaze_direction else 0,
                    'is_looking_at_camera': result.is_looking_at_camera
                },
                'eyes': {
                    'left_ear': result.left_ear,
                    'right_ear': result.right_ear,
                    'avg_ear': result.avg_ear,
                    'perclos': result.perclos,
                    'is_blinking': result.is_blinking,
                    'is_drowsy': result.is_drowsy
                },
                'alerts': [{'alert_type': a.type, 'severity': a.severity, 
                           'message': a.message, 'duration_seconds': a.duration}
                          for a in result.alerts]
            }
            faces.append(face)
        return faces
    
    def _error_response(self, request, error_msg):
        """Create error response."""
        return {
            'meeting_id': request.meeting_id,
            'participant_id': request.participant_id,
            'timestamp': request.timestamp,
            'faces': [],
            'processing_time_ms': 0,
            'success': False,
            'error_message': error_msg
        }


def serve(port: int = 50051):
    """Start the gRPC server."""
    settings = Settings()
    pipeline = AttentionPipeline(settings)
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = AttentionServicer(pipeline)
    
    # Note: In production, you'd use generated protobuf stubs
    # add_AttentionServicer_to_server(servicer, server)
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logger.info(f"gRPC server started on port {port}")
    server.wait_for_termination()

