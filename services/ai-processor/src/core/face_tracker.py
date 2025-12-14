"""
Multi-Face Tracking Module using ByteTrack algorithm.

This module provides persistent ID assignment for faces across frames
to enable continuous tracking of participants.
"""

import numpy as np
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass
from loguru import logger

from ..config import TrackerConfig, settings
from ..models.detection import Detection, TrackInfo, BoundingBox


@dataclass
class Track:
    """Internal track representation."""
    track_id: int
    bbox: np.ndarray  # [x1, y1, x2, y2]
    score: float
    is_confirmed: bool = False
    frames_since_update: int = 0
    hit_streak: int = 0
    age: int = 0
    
    def update(self, detection: Detection) -> None:
        """Update track with new detection."""
        bbox = detection.bbox
        self.bbox = np.array([bbox.x, bbox.y, bbox.x2, bbox.y2])
        self.score = detection.confidence
        self.frames_since_update = 0
        self.hit_streak += 1
        self.age += 1
        
        if self.hit_streak >= 3:
            self.is_confirmed = True
    
    def mark_missed(self) -> None:
        """Mark track as missed in current frame."""
        self.frames_since_update += 1
        self.hit_streak = 0


class FaceTracker:
    """
    Multi-face tracker using simplified ByteTrack algorithm.
    
    Features:
    - Persistent ID assignment across frames
    - Handles occlusion and temporary disappearance
    - Configurable track buffer for lost tracks
    """
    
    def __init__(self, config: Optional[TrackerConfig] = None):
        """
        Initialize face tracker.
        
        Args:
            config: Tracker configuration. Uses default if not provided.
        """
        self.config = config or settings.tracker
        self._tracks: dict[int, Track] = {}
        self._next_id = 1
        self._frame_count = 0
        
    def reset(self) -> None:
        """Reset tracker state."""
        self._tracks.clear()
        self._next_id = 1
        self._frame_count = 0
        logger.debug("Tracker reset")
    
    def update(self, detections: list[Detection]) -> list[tuple[Detection, TrackInfo]]:
        """
        Update tracks with new detections.
        
        Args:
            detections: List of face detections from current frame
            
        Returns:
            List of (detection, track_info) tuples
        """
        self._frame_count += 1
        results = []
        
        if not detections:
            # Mark all tracks as missed
            self._handle_missed_tracks()
            return results
        
        # Convert detections to numpy array for IoU calculation
        det_boxes = np.array([
            [d.bbox.x, d.bbox.y, d.bbox.x2, d.bbox.y2]
            for d in detections
        ])
        det_scores = np.array([d.confidence for d in detections])
        
        # Get existing track boxes
        track_ids = list(self._tracks.keys())
        if track_ids:
            track_boxes = np.array([
                self._tracks[tid].bbox for tid in track_ids
            ])
            
            # Calculate IoU matrix
            iou_matrix = self._calculate_iou(det_boxes, track_boxes)
            
            # Match detections to tracks using Hungarian algorithm (greedy for simplicity)
            matched_dets, matched_tracks, unmatched_dets = self._match_detections(
                iou_matrix, det_scores, track_ids
            )
            
            # Update matched tracks
            for det_idx, track_id in zip(matched_dets, matched_tracks):
                self._tracks[track_id].update(detections[det_idx])
                track_info = TrackInfo(
                    track_id=track_id,
                    is_confirmed=self._tracks[track_id].is_confirmed,
                    frames_since_update=0,
                    hit_streak=self._tracks[track_id].hit_streak,
                    age=self._tracks[track_id].age
                )
                results.append((detections[det_idx], track_info))
            
            # Create new tracks for unmatched detections
            for det_idx in unmatched_dets:
                if det_scores[det_idx] >= self.config.track_thresh:
                    track_id = self._create_track(detections[det_idx])
                    track_info = TrackInfo(
                        track_id=track_id,
                        is_confirmed=False,
                        frames_since_update=0,
                        hit_streak=1,
                        age=1
                    )
                    results.append((detections[det_idx], track_info))
        else:
            # No existing tracks, create new ones
            for i, det in enumerate(detections):
                if det_scores[i] >= self.config.track_thresh:
                    track_id = self._create_track(det)
                    track_info = TrackInfo(
                        track_id=track_id,
                        is_confirmed=False,
                        frames_since_update=0,
                        hit_streak=1,
                        age=1
                    )
                    results.append((det, track_info))
        
        # Handle unmatched tracks
        self._handle_missed_tracks()
        
        logger.debug(f"Tracking: {len(results)} faces, {len(self._tracks)} active tracks")
        
        return results
    
    def _create_track(self, detection: Detection) -> int:
        """Create a new track."""
        track_id = self._next_id
        self._next_id += 1
        
        bbox = detection.bbox
        self._tracks[track_id] = Track(
            track_id=track_id,
            bbox=np.array([bbox.x, bbox.y, bbox.x2, bbox.y2]),
            score=detection.confidence,
            age=1,
            hit_streak=1
        )
        
        return track_id
    
    def _handle_missed_tracks(self) -> None:
        """Handle tracks that were not matched."""
        tracks_to_remove = []
        
        for track_id, track in self._tracks.items():
            if track.frames_since_update > 0:
                track.mark_missed()
                
                if track.frames_since_update > self.config.track_buffer:
                    tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self._tracks[track_id]
    
    def _calculate_iou(self, boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
        """Calculate IoU between two sets of boxes."""
        # boxes format: [x1, y1, x2, y2]
        n1, n2 = len(boxes1), len(boxes2)
        iou_matrix = np.zeros((n1, n2))
        
        for i in range(n1):
            for j in range(n2):
                iou_matrix[i, j] = self._iou(boxes1[i], boxes2[j])
        
        return iou_matrix
    
    @staticmethod
    def _iou(box1: np.ndarray, box2: np.ndarray) -> float:
        """Calculate IoU between two boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union_area = area1 + area2 - inter_area
        
        return inter_area / union_area if union_area > 0 else 0
    
    def _match_detections(
        self, 
        iou_matrix: np.ndarray, 
        det_scores: np.ndarray,
        track_ids: list[int]
    ) -> tuple[list[int], list[int], list[int]]:
        """Match detections to tracks using greedy algorithm."""
        matched_dets = []
        matched_tracks = []
        used_dets = set()
        used_tracks = set()
        
        # Sort by IoU score (descending)
        indices = np.unravel_index(
            np.argsort(iou_matrix, axis=None)[::-1], 
            iou_matrix.shape
        )
        
        for det_idx, track_idx in zip(indices[0], indices[1]):
            if det_idx in used_dets or track_idx in used_tracks:
                continue
            
            if iou_matrix[det_idx, track_idx] >= self.config.match_thresh:
                matched_dets.append(det_idx)
                matched_tracks.append(track_ids[track_idx])
                used_dets.add(det_idx)
                used_tracks.add(track_idx)
        
        unmatched_dets = [i for i in range(len(det_scores)) if i not in used_dets]
        
        return matched_dets, matched_tracks, unmatched_dets

