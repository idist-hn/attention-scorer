"""
Blink Detection and Eye State Analysis Module.

This module detects eye blinks, calculates Eye Aspect Ratio (EAR),
and computes PERCLOS for drowsiness detection.
"""

import numpy as np
from typing import Optional
from collections import deque
from dataclasses import dataclass
from loguru import logger

from ..models.detection import FaceLandmarks, BlinkInfo


@dataclass
class BlinkState:
    """State for blink detection."""
    is_blinking: bool = False
    blink_start_frame: int = 0
    blink_count: int = 0
    frames_processed: int = 0


class BlinkDetector:
    """
    Detects eye blinks and analyzes eye state.
    
    Features:
    - Eye Aspect Ratio (EAR) calculation
    - Blink detection and counting
    - PERCLOS (Percentage of Eye Closure) calculation
    - Drowsiness detection
    """
    
    # Eye landmark indices for EAR calculation
    # Using 6 points: 2 for horizontal, 4 for vertical
    LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    
    def __init__(
        self,
        ear_threshold: float = 0.25,
        blink_consec_frames: int = 2,
        perclos_window: int = 90,  # ~3 seconds at 30 FPS
        drowsy_perclos_threshold: float = 0.8
    ):
        """
        Initialize blink detector.
        
        Args:
            ear_threshold: EAR threshold below which eyes are considered closed
            blink_consec_frames: Consecutive frames needed to register a blink
            perclos_window: Window size for PERCLOS calculation (in frames)
            drowsy_perclos_threshold: PERCLOS threshold for drowsiness detection
        """
        self.ear_threshold = ear_threshold
        self.blink_consec_frames = blink_consec_frames
        self.perclos_window = perclos_window
        self.drowsy_perclos_threshold = drowsy_perclos_threshold
        
        # Per-track state
        self._track_states: dict[int, BlinkState] = {}
        self._ear_history: dict[int, deque] = {}
        self._blink_times: dict[int, deque] = {}
    
    def analyze(
        self, 
        landmarks: FaceLandmarks, 
        track_id: int = 0
    ) -> BlinkInfo:
        """
        Analyze eye state from facial landmarks.
        
        Args:
            landmarks: Facial landmarks
            track_id: Track ID for maintaining state per person
            
        Returns:
            BlinkInfo with EAR, blink rate, PERCLOS
        """
        # Initialize state for new tracks
        if track_id not in self._track_states:
            self._track_states[track_id] = BlinkState()
            self._ear_history[track_id] = deque(maxlen=self.perclos_window)
            self._blink_times[track_id] = deque(maxlen=100)  # Last 100 blinks
        
        state = self._track_states[track_id]
        ear_history = self._ear_history[track_id]
        
        # Calculate EAR for both eyes
        left_ear = self._calculate_ear(landmarks.left_eye)
        right_ear = self._calculate_ear(landmarks.right_eye)
        avg_ear = (left_ear + right_ear) / 2
        
        # Update history
        ear_history.append(avg_ear)
        state.frames_processed += 1
        
        # Detect blink
        is_blinking = self._detect_blink(avg_ear, state, track_id)
        
        # Calculate PERCLOS
        perclos = self._calculate_perclos(ear_history)
        
        # Calculate blink rate (blinks per minute)
        blink_rate = self._calculate_blink_rate(track_id)
        
        return BlinkInfo(
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            is_blinking=is_blinking,
            blink_rate=blink_rate,
            perclos=perclos
        )
    
    def _calculate_ear(self, eye_landmarks: np.ndarray) -> float:
        """
        Calculate Eye Aspect Ratio.
        
        EAR = (|p2 - p6| + |p3 - p5|) / (2 * |p1 - p4|)
        
        Where p1-p6 are the 6 eye landmarks:
        p1, p4: horizontal corners
        p2, p6 and p3, p5: vertical points
        """
        if len(eye_landmarks) < 6:
            return 0.0
        
        # Vertical distances
        v1 = np.linalg.norm(eye_landmarks[1, :2] - eye_landmarks[5, :2])
        v2 = np.linalg.norm(eye_landmarks[2, :2] - eye_landmarks[4, :2])
        
        # Horizontal distance
        h = np.linalg.norm(eye_landmarks[0, :2] - eye_landmarks[3, :2])
        
        if h < 1:
            return 0.0
        
        ear = (v1 + v2) / (2.0 * h)
        return float(ear)
    
    def _detect_blink(
        self, 
        ear: float, 
        state: BlinkState, 
        track_id: int
    ) -> bool:
        """Detect if a blink occurred."""
        eye_closed = ear < self.ear_threshold
        
        if eye_closed:
            if not state.is_blinking:
                state.is_blinking = True
                state.blink_start_frame = state.frames_processed
        else:
            if state.is_blinking:
                # Check if blink duration was valid
                blink_duration = state.frames_processed - state.blink_start_frame
                if blink_duration >= self.blink_consec_frames:
                    state.blink_count += 1
                    self._blink_times[track_id].append(state.frames_processed)
                state.is_blinking = False
        
        return state.is_blinking
    
    def _calculate_perclos(self, ear_history: deque) -> float:
        """
        Calculate PERCLOS (Percentage of Eye Closure).
        
        PERCLOS = (frames with eyes closed) / (total frames in window)
        """
        if len(ear_history) == 0:
            return 0.0
        
        closed_frames = sum(1 for ear in ear_history if ear < self.ear_threshold)
        return closed_frames / len(ear_history)
    
    def _calculate_blink_rate(self, track_id: int) -> float:
        """Calculate blink rate in blinks per minute."""
        blink_times = self._blink_times[track_id]
        
        if len(blink_times) < 2:
            return 0.0
        
        # Assume 30 FPS for conversion
        fps = 30.0
        time_window = (blink_times[-1] - blink_times[0]) / fps
        
        if time_window < 1:
            return 0.0
        
        blinks = len(blink_times) - 1
        blink_rate = (blinks / time_window) * 60  # Convert to per minute
        
        return min(blink_rate, 60.0)  # Cap at 60 bpm
    
    def is_drowsy(self, track_id: int) -> bool:
        """Check if person shows signs of drowsiness."""
        ear_history = self._ear_history.get(track_id)
        if not ear_history or len(ear_history) < self.perclos_window // 2:
            return False
        
        perclos = self._calculate_perclos(ear_history)
        return perclos > self.drowsy_perclos_threshold
    
    def calculate_eye_openness_score(self, blink_info: BlinkInfo) -> float:
        """
        Calculate eye openness score for attention.
        
        Args:
            blink_info: BlinkInfo with EAR values
            
        Returns:
            Score from 0.0 to 1.0
        """
        if blink_info.avg_ear <= 0:
            return 0.0
        
        # Normalize EAR to score
        # Typical EAR range: 0.15 (closed) to 0.35 (wide open)
        min_ear = 0.15
        max_ear = 0.35
        
        normalized = (blink_info.avg_ear - min_ear) / (max_ear - min_ear)
        score = np.clip(normalized, 0.0, 1.0)
        
        # Penalize high PERCLOS
        if blink_info.perclos > 0.5:
            score *= (1.0 - blink_info.perclos)
        
        return float(score)
    
    def reset_track(self, track_id: int) -> None:
        """Reset state for a specific track."""
        self._track_states.pop(track_id, None)
        self._ear_history.pop(track_id, None)
        self._blink_times.pop(track_id, None)
    
    def reset_all(self) -> None:
        """Reset all tracking state."""
        self._track_states.clear()
        self._ear_history.clear()
        self._blink_times.clear()

