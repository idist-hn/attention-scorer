"""
Video capture utilities.
"""

import cv2
import numpy as np
from typing import Optional, Generator
from loguru import logger


class VideoCapture:
    """
    Video capture wrapper with support for camera and video files.
    """
    
    def __init__(
        self, 
        source: int | str = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30
    ):
        """
        Initialize video capture.
        
        Args:
            source: Camera index or video file path
            width: Frame width
            height: Frame height
            fps: Target FPS
        """
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None
    
    def open(self) -> bool:
        """Open video capture."""
        try:
            self._cap = cv2.VideoCapture(self.source)
            
            if not self._cap.isOpened():
                logger.error(f"Failed to open video source: {self.source}")
                return False
            
            # Set properties for camera
            if isinstance(self.source, int):
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self._cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Get actual properties
            actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self._cap.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Video capture opened: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            return True
            
        except Exception as e:
            logger.error(f"Error opening video capture: {e}")
            return False
    
    def read(self) -> tuple[bool, Optional[np.ndarray]]:
        """Read a single frame."""
        if self._cap is None or not self._cap.isOpened():
            return False, None
        
        ret, frame = self._cap.read()
        return ret, frame
    
    def frames(self) -> Generator[np.ndarray, None, None]:
        """Generator for reading frames."""
        if self._cap is None:
            if not self.open():
                return
        
        while True:
            ret, frame = self.read()
            if not ret:
                break
            yield frame
    
    def release(self) -> None:
        """Release video capture."""
        if self._cap:
            self._cap.release()
            self._cap = None
            logger.info("Video capture released")
    
    @property
    def is_opened(self) -> bool:
        """Check if capture is opened."""
        return self._cap is not None and self._cap.isOpened()
    
    @property
    def frame_count(self) -> int:
        """Get total frame count (for video files)."""
        if self._cap:
            return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return 0
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

