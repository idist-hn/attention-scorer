"""
Attention Scorer Microservice

Standalone gRPC + REST service for attention score calculation.
Combines head pose, gaze, blink metrics into attention score.
"""

import os
import grpc
from concurrent import futures
import numpy as np
import time
import threading
from loguru import logger
from dataclasses import dataclass, field
from collections import deque
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn


app = FastAPI(title="Attention Scorer Service", version="1.0.0")


class HeadPoseInput(BaseModel):
    yaw: float = 0
    pitch: float = 0
    roll: float = 0


class GazeInput(BaseModel):
    gaze_x: float = 0
    gaze_y: float = 0
    is_looking_at_camera: bool = True


class BlinkInput(BaseModel):
    avg_ear: float = 0.25
    perclos: float = 0
    is_drowsy: bool = False


class ScoreRequest(BaseModel):
    track_id: str = "0"
    head_pose: HeadPoseInput = HeadPoseInput()
    gaze: GazeInput = GazeInput()
    blink: BlinkInput = BlinkInput()
    request_id: str = ""


class ScoreResponse(BaseModel):
    attention_score: float
    alerts: List[Dict[str, Any]] = []
    request_id: str = ""
    success: bool = True
    error: str = ""


servicer_instance = None


@dataclass
class ParticipantState:
    """State for attention scoring."""
    score_history: deque = field(default_factory=lambda: deque(maxlen=30))
    consecutive_low: int = 0
    last_alert_time: float = 0


class AttentionScorerServicer:
    """gRPC servicer for attention scoring."""
    
    def __init__(self):
        self.version = "1.0.0"
        
        # Weights for attention score
        self.weights = {
            'gaze': 0.35,
            'head_pose': 0.30,
            'eye_openness': 0.20,
            'presence': 0.15
        }
        
        # Thresholds
        self.yaw_threshold = 30.0
        self.pitch_threshold = 25.0
        self.gaze_threshold = 0.3
        self.low_attention_threshold = 50.0
        self.alert_cooldown = 30.0  # seconds
        
        self.participant_states: dict[str, ParticipantState] = {}
    
    def CalculateScore(self, request, context):
        """Calculate attention score from metrics."""
        try:
            start_time = time.time()
            
            track_id = request.track_id
            
            # Get or create state
            if track_id not in self.participant_states:
                self.participant_states[track_id] = ParticipantState()
            state = self.participant_states[track_id]
            
            # Extract metrics
            head_pose = request.head_pose
            gaze = request.gaze
            blink = request.blink
            
            # Calculate component scores (0-1)
            # Head pose score
            yaw_score = max(0, 1 - abs(head_pose.yaw) / self.yaw_threshold)
            pitch_score = max(0, 1 - abs(head_pose.pitch) / self.pitch_threshold)
            head_score = (yaw_score + pitch_score) / 2
            
            # Gaze score
            gaze_score = 1.0 if gaze.is_looking_at_camera else max(0, 1 - abs(gaze.gaze_x) / 0.5)
            
            # Eye openness score (based on EAR and PERCLOS)
            ear_normalized = min(1, blink.avg_ear / 0.3) if blink.avg_ear > 0 else 0
            perclos_score = 1 - (blink.perclos / 100)
            eye_score = (ear_normalized + perclos_score) / 2
            
            # Presence score (always 1 if detected)
            presence_score = 1.0
            
            # Calculate weighted attention score
            attention_score = (
                self.weights['gaze'] * gaze_score +
                self.weights['head_pose'] * head_score +
                self.weights['eye_openness'] * eye_score +
                self.weights['presence'] * presence_score
            ) * 100
            
            # Smooth with history
            state.score_history.append(attention_score)
            smoothed_score = np.mean(list(state.score_history))
            
            # Check for alerts
            alerts = []
            current_time = time.time()
            
            if smoothed_score < self.low_attention_threshold:
                state.consecutive_low += 1
                if state.consecutive_low >= 10:  # 10 consecutive low frames
                    if current_time - state.last_alert_time > self.alert_cooldown:
                        alerts.append({
                            'type': 'LOW_ATTENTION',
                            'message': f'Attention below {self.low_attention_threshold}%',
                            'severity': 'warning'
                        })
                        state.last_alert_time = current_time
            else:
                state.consecutive_low = 0
            
            if blink.is_drowsy:
                alerts.append({
                    'type': 'DROWSINESS',
                    'message': 'Drowsiness detected',
                    'severity': 'critical'
                })
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'request_id': request.request_id,
                'attention_score': float(smoothed_score),
                'raw_score': float(attention_score),
                'component_scores': {
                    'gaze': float(gaze_score),
                    'head_pose': float(head_score),
                    'eye_openness': float(eye_score),
                    'presence': float(presence_score)
                },
                'alerts': alerts,
                'processing_time_ms': processing_time,
                'success': True,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Attention scoring error: {e}")
            return self._error_response(request.request_id, str(e))
    
    def Health(self, request, context):
        """Health check."""
        return {'healthy': True, 'version': self.version}
    
    def _error_response(self, request_id: str, error: str):
        return {
            'request_id': request_id,
            'attention_score': 0,
            'success': False,
            'error': error
        }


@app.get("/health")
def health():
    global servicer_instance
    return {"healthy": servicer_instance is not None, "version": "1.0.0"}


@app.post("/score", response_model=ScoreResponse)
def score(request: ScoreRequest):
    global servicer_instance
    if servicer_instance is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        track_id = request.track_id
        if track_id not in servicer_instance.participant_states:
            servicer_instance.participant_states[track_id] = ParticipantState()
        state = servicer_instance.participant_states[track_id]

        head_pose = request.head_pose
        gaze = request.gaze
        blink = request.blink

        # Component scores
        yaw_score = max(0, 1 - abs(head_pose.yaw) / servicer_instance.yaw_threshold)
        pitch_score = max(0, 1 - abs(head_pose.pitch) / servicer_instance.pitch_threshold)
        head_score = (yaw_score + pitch_score) / 2

        gaze_score = 1.0 if gaze.is_looking_at_camera else max(0, 1 - abs(gaze.gaze_x) / 0.5)

        ear_normalized = min(1, blink.avg_ear / 0.3) if blink.avg_ear > 0 else 0
        perclos_score = 1 - (blink.perclos / 100)
        eye_score = (ear_normalized + perclos_score) / 2

        # Weighted attention score
        attention_score = (
            servicer_instance.weights['gaze'] * gaze_score +
            servicer_instance.weights['head_pose'] * head_score +
            servicer_instance.weights['eye_openness'] * eye_score +
            servicer_instance.weights['presence'] * 1.0
        ) * 100

        state.score_history.append(attention_score)
        smoothed_score = float(np.mean(list(state.score_history)))

        # Alerts
        alerts = []
        if smoothed_score < servicer_instance.low_attention_threshold:
            state.consecutive_low += 1
            if state.consecutive_low >= 10:
                alerts.append({'type': 'LOW_ATTENTION', 'message': 'Low attention detected', 'severity': 'warning'})
        else:
            state.consecutive_low = 0

        if blink.is_drowsy:
            alerts.append({'type': 'DROWSINESS', 'message': 'Drowsiness detected', 'severity': 'critical'})

        return ScoreResponse(attention_score=smoothed_score, alerts=alerts, request_id=request.request_id)
    except Exception as e:
        return ScoreResponse(attention_score=75.0, alerts=[], request_id=request.request_id,
                            success=False, error=str(e))


def run_rest_server(port: int):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def serve(grpc_port: int = 50057, rest_port: int = 8057):
    global servicer_instance
    servicer_instance = AttentionScorerServicer()

    rest_thread = threading.Thread(target=run_rest_server, args=(rest_port,), daemon=True)
    rest_thread.start()
    logger.info(f"🌐 REST API on port {rest_port}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_insecure_port(f'[::]:{grpc_port}')
    server.start()
    logger.info(f"🎯 Attention Scorer Service started (gRPC: {grpc_port})")
    server.wait_for_termination()


if __name__ == "__main__":
    grpc_port = int(os.environ.get("GRPC_PORT", 50057))
    rest_port = int(os.environ.get("REST_PORT", 8057))
    serve(grpc_port, rest_port)

