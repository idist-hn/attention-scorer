# Attention Detection Algorithm

## 1. Tổng quan Pipeline

```
Video Frame
    │
    ▼
┌─────────────────┐
│ Face Detection  │  → YOLOv8-face (multi-face)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Face Tracking   │  → ByteTrack (assign persistent IDs)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Landmark        │  → MediaPipe FaceMesh (478 points)
│ Detection       │
└────────┬────────┘
         │
    ┌────┴────┬──────────┐
    ▼         ▼          ▼
┌───────┐ ┌───────┐ ┌───────┐
│ Head  │ │ Gaze  │ │ Blink │
│ Pose  │ │ Track │ │ Detect│
└───┬───┘ └───┬───┘ └───┬───┘
    │         │         │
    └────┬────┴─────────┘
         ▼
┌─────────────────┐
│ Attention Score │  → Weighted combination
└─────────────────┘
```

## 2. Face Detection (YOLOv8-face)

### Model Selection
- **Model**: YOLOv8n-face (nano) hoặc YOLOv8s-face (small)
- **Input size**: 640x640
- **Output**: Bounding boxes + 5 keypoints (eyes, nose, mouth corners)

### Configuration
```python
FACE_DETECTION_CONFIG = {
    "model": "yolov8n-face.pt",
    "conf_threshold": 0.5,      # Confidence threshold
    "iou_threshold": 0.45,      # NMS IoU threshold
    "max_faces": 20,            # Maximum faces to detect
    "input_size": (640, 640)
}
```

## 3. Multi-Face Tracking (ByteTrack)

### Purpose
Gán ID cố định cho mỗi người qua các frames để theo dõi liên tục.

### Configuration
```python
TRACKER_CONFIG = {
    "track_thresh": 0.5,        # Detection threshold for tracking
    "track_buffer": 30,         # Frames to keep lost tracks
    "match_thresh": 0.8,        # IoU threshold for matching
    "min_box_area": 100         # Minimum face area
}
```

## 4. Facial Landmark Detection (MediaPipe)

### 478 Landmarks
MediaPipe FaceMesh cung cấp 478 điểm landmark bao gồm:
- **Face contour**: 36 points
- **Left eyebrow**: 10 points
- **Right eyebrow**: 10 points
- **Left eye**: 16 points
- **Right eye**: 16 points
- **Nose**: 34 points
- **Lips**: 40 points
- **Iris**: 10 points (5 per eye)

### Key Landmark Indices
```python
LANDMARK_INDICES = {
    # Eye landmarks for EAR calculation
    "left_eye": [362, 385, 387, 263, 373, 380],
    "right_eye": [33, 160, 158, 133, 153, 144],
    
    # Iris landmarks for gaze
    "left_iris": [468, 469, 470, 471, 472],
    "right_iris": [473, 474, 475, 476, 477],
    
    # Head pose landmarks
    "nose_tip": 1,
    "chin": 152,
    "left_eye_outer": 263,
    "right_eye_outer": 33,
    "left_mouth": 287,
    "right_mouth": 57
}
```

## 5. Head Pose Estimation

### Phương pháp: SolvePnP
Sử dụng 6 điểm landmark chính để ước lượng góc quay đầu.

### Algorithm
```python
def estimate_head_pose(landmarks, image_size):
    # 3D model points (generic face model)
    model_points = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left eye outer
        (225.0, 170.0, -135.0),      # Right eye outer
        (-150.0, -150.0, -125.0),    # Left mouth corner
        (150.0, -150.0, -125.0)      # Right mouth corner
    ])
    
    # Camera matrix
    focal_length = image_size[0]
    center = (image_size[0] / 2, image_size[1] / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ])
    
    # Solve PnP
    success, rotation_vec, translation_vec = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs
    )
    
    # Convert to Euler angles
    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    yaw, pitch, roll = rotation_matrix_to_euler(rotation_mat)
    
    return yaw, pitch, roll  # In degrees
```

### Head Pose Score
```python
def calculate_head_pose_score(yaw, pitch, roll):
    YAW_THRESHOLD = 30      # Looking left/right
    PITCH_THRESHOLD = 25    # Looking up/down
    
    yaw_penalty = min(abs(yaw) / YAW_THRESHOLD, 1.0)
    pitch_penalty = min(abs(pitch) / PITCH_THRESHOLD, 1.0)
    
    score = 1.0 - (yaw_penalty * 0.6 + pitch_penalty * 0.4)
    return max(0.0, score)
```

## 6. Eye Gaze Tracking

### Iris-based Gaze Estimation
```python
def estimate_gaze(landmarks, eye_indices, iris_indices):
    # Get eye corners
    eye_left = landmarks[eye_indices[0]]
    eye_right = landmarks[eye_indices[3]]
    
    # Get iris center
    iris_center = np.mean([landmarks[i] for i in iris_indices], axis=0)
    
    # Calculate relative position
    eye_width = np.linalg.norm(eye_right - eye_left)
    iris_offset = iris_center - eye_left
    
    # Normalize to [-1, 1]
    gaze_x = (iris_offset[0] / eye_width) * 2 - 1
    gaze_y = (iris_offset[1] / eye_width) * 2 - 1
    
    return gaze_x, gaze_y
```

### Gaze Score
```python
def calculate_gaze_score(gaze_x, gaze_y):
    GAZE_THRESHOLD = 0.3  # Looking at center region
    
    distance = np.sqrt(gaze_x**2 + gaze_y**2)
    score = 1.0 - min(distance / GAZE_THRESHOLD, 1.0)
    
    return max(0.0, score)
```

## 7. Blink Detection & PERCLOS

### Eye Aspect Ratio (EAR)
```python
def calculate_ear(eye_landmarks):
    # Vertical distances
    v1 = np.linalg.norm(eye_landmarks[1] - eye_landmarks[5])
    v2 = np.linalg.norm(eye_landmarks[2] - eye_landmarks[4])
    
    # Horizontal distance
    h = np.linalg.norm(eye_landmarks[0] - eye_landmarks[3])
    
    ear = (v1 + v2) / (2.0 * h)
    return ear
```

### PERCLOS (Percentage of Eye Closure)
```python
class PERCLOSCalculator:
    def __init__(self, window_size=60):  # 60 frames ≈ 2-3 seconds
        self.ear_history = deque(maxlen=window_size)
        self.EAR_THRESHOLD = 0.25
    
    def update(self, ear):
        self.ear_history.append(ear)
        
        closed_frames = sum(1 for e in self.ear_history if e < self.EAR_THRESHOLD)
        perclos = closed_frames / len(self.ear_history)
        
        return perclos
    
    def is_drowsy(self, perclos):
        return perclos > 0.8  # 80% eyes closed = drowsy
```

## 8. Final Attention Score

### Weighted Combination
```python
class AttentionScorer:
    def __init__(self):
        self.weights = {
            "gaze": 0.35,
            "head_pose": 0.30,
            "eye_openness": 0.20,
            "presence": 0.15
        }
    
    def calculate(self, gaze_score, head_pose_score, ear, is_present):
        # Eye openness score
        eye_score = min(1.0, ear / 0.25) if ear > 0.15 else 0.0
        
        # Presence score
        presence_score = 1.0 if is_present else 0.0
        
        # Weighted sum
        attention = (
            self.weights["gaze"] * gaze_score +
            self.weights["head_pose"] * head_pose_score +
            self.weights["eye_openness"] * eye_score +
            self.weights["presence"] * presence_score
        )
        
        return round(attention * 100, 2)  # 0-100%
```

### Thresholds for Alerts
```python
ALERT_THRESHOLDS = {
    "not_attentive": {
        "score": 30,           # Below 30%
        "duration": 10         # For 10 seconds
    },
    "looking_away": {
        "head_yaw": 45,        # Head turned > 45 degrees
        "duration": 5          # For 5 seconds
    },
    "drowsy": {
        "perclos": 0.8,        # PERCLOS > 80%
        "duration": 3          # For 3 seconds
    }
}
```

