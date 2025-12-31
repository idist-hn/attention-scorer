# API Specification

## 1. Tổng quan

| Protocol  | Port  | Mục đích                                      |
| --------- | ----- | --------------------------------------------- |
| REST API  | 8080  | CRUD operations, authentication               |
| WebSocket | 8080  | Real-time video streaming, attention updates  |
| gRPC      | 50051 | Internal communication (Gateway ↔ AI Service) |

## 2. REST API Endpoints

### 2.1 Authentication

#### POST /api/v1/auth/register
Đăng ký tài khoản mới.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "full_name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### POST /api/v1/auth/login
Đăng nhập và nhận JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 3600
}
```

### 2.2 Meetings

#### GET /api/v1/meetings
Lấy danh sách meetings.

**Query Parameters:**
- `status`: filter by status (scheduled, active, ended)
- `page`: page number (default: 1)
- `limit`: items per page (default: 20)

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Weekly Standup",
      "host_id": "uuid",
      "status": "scheduled",
      "scheduled_start": "2024-01-15T09:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45
  }
}
```

#### POST /api/v1/meetings
Tạo meeting mới.

**Request:**
```json
{
  "title": "Weekly Standup",
  "description": "Team sync meeting",
  "scheduled_start": "2024-01-15T09:00:00Z",
  "scheduled_end": "2024-01-15T10:00:00Z",
  "settings": {
    "attention_threshold": 0.3,
    "alert_enabled": true
  }
}
```

#### GET /api/v1/meetings/:id
Lấy chi tiết meeting.

#### PUT /api/v1/meetings/:id
Cập nhật meeting.

#### POST /api/v1/meetings/:id/start
Bắt đầu meeting (chuyển status sang active).

#### POST /api/v1/meetings/:id/end
Kết thúc meeting.

### 2.3 Participants

#### GET /api/v1/meetings/:id/participants
Lấy danh sách participants của meeting.

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "full_name": "John Doe",
      "status": "joined",
      "joined_at": "2024-01-15T09:02:00Z",
      "current_attention": 0.85
    }
  ]
}
```

#### POST /api/v1/meetings/:id/participants
Thêm participant vào meeting.

### 2.4 Analytics & Reports

#### GET /api/v1/analytics/meetings/:id/metrics
Lấy attention metrics của meeting.

**Query Parameters:**
- `start`: ISO timestamp (optional)
- `end`: ISO timestamp (optional)

**Response:** `200 OK`
```json
[
  {
    "time": "2024-01-15T09:00:00Z",
    "meeting_id": "uuid",
    "participant_id": "uuid",
    "attention_score": 0.85,
    "gaze_score": 0.90,
    "head_pose_score": 0.80,
    "eye_openness_score": 0.95,
    "is_looking_away": false,
    "is_drowsy": false
  }
]
```

#### GET /api/v1/analytics/meetings/:id/participants
Lấy thống kê attention theo participant.

**Response:** `200 OK`
```json
[
  {
    "participant_id": "uuid",
    "avg_attention": 0.82,
    "min_attention": 0.45,
    "max_attention": 0.98,
    "total_samples": 150
  }
]
```

#### GET /api/v1/analytics/meetings/:id/alerts
Lấy danh sách alerts của meeting.

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "meeting_id": "uuid",
    "participant_id": "uuid",
    "alert_type": "not_attentive",
    "severity": "warning",
    "message": "Attention below threshold",
    "duration_seconds": 15.5,
    "created_at": "2024-01-15T09:15:00Z"
  }
]
```

#### GET /api/v1/analytics/meetings/:id/summary
Lấy báo cáo tổng hợp meeting.

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "meeting_id": "uuid",
  "duration_minutes": 30,
  "participant_count": 8,
  "avg_attention_score": 0.72,
  "min_attention_score": 0.35,
  "max_attention_score": 0.95,
  "total_alerts": 5,
  "low_attention_segments": 3
}
```

### 2.5 Alerts

#### GET /api/v1/analytics/meetings/:id/alerts
Lấy danh sách alerts của meeting.

**Query Parameters:**
- `type`: filter by type (not_attentive, drowsy, looking_away)
- `severity`: filter by severity (info, warning, critical)

### 2.6 Video Analysis (Offline)

Phân tích attention từ video file đã ghi sẵn.

#### POST /api/v1/video-analysis/upload
Upload video để phân tích attention offline.

**Request:** `multipart/form-data`
- `video`: Video file (MP4, WebM, AVI, MOV, MKV)

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "filename": "meeting_recording.mp4",
  "file_size": 52428800,
  "status": "pending",
  "progress": 0,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/v1/video-analysis
Lấy danh sách video analyses của user.

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "filename": "meeting_recording.mp4",
    "file_size": 52428800,
    "duration": 1800,
    "status": "completed",
    "progress": 100,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### GET /api/v1/video-analysis/:id
Lấy chi tiết và kết quả phân tích.

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "filename": "meeting_recording.mp4",
  "status": "completed",
  "duration": 1800,
  "results": {
    "avg_attention": 72.5,
    "min_attention": 35.0,
    "max_attention": 95.0,
    "total_alerts": 5,
    "analyzed_frames": 900,
    "timeline": [
      {"timestamp_ms": 0, "avg_attention": 85.0, "faces": 3},
      {"timestamp_ms": 2000, "avg_attention": 78.0, "faces": 3}
    ],
    "alerts": [
      {"type": "low_attention", "severity": "warning", "timestamp_ms": 120000}
    ]
  }
}
```

#### DELETE /api/v1/video-analysis/:id
Xóa video analysis.

### 2.7 Recordings

#### POST /api/v1/recordings/start
Bắt đầu recording session mới.

#### POST /api/v1/recordings/:id/chunk
Append video chunk vào recording đang chạy.

#### POST /api/v1/recordings/:id/complete
Hoàn thành recording session.

#### GET /api/v1/recordings
Lấy danh sách recordings.

#### GET /api/v1/recordings/:id/stream
Stream video recording.

## 3. WebSocket API

### 3.1 Connection
```
ws://localhost:8080/ws/meeting/:meeting_id?token=JWT_TOKEN
```

### 3.2 Client → Server Messages

#### Join Meeting
```json
{
  "type": "join",
  "payload": {
    "meeting_id": "uuid",
    "user_id": "uuid"
  }
}
```

#### Send Video Frame
```json
{
  "type": "frame",
  "payload": {
    "meeting_id": "uuid",
    "timestamp": 1705312800000,
    "frame": "base64_encoded_image"
  }
}
```

### 3.3 Server → Client Messages

#### Attention Update
```json
{
  "type": "attention_update",
  "payload": {
    "meeting_id": "uuid",
    "timestamp": 1705312800000,
    "participants": [
      {
        "id": "uuid",
        "track_id": "1",
        "attention_score": 0.85,
        "gaze_score": 0.90,
        "head_pose_score": 0.80,
        "is_looking_away": false,
        "is_drowsy": false,
        "bbox": {"x": 100, "y": 50, "w": 150, "h": 180}
      }
    ]
  }
}
```

#### Alert Notification
```json
{
  "type": "alert",
  "payload": {
    "id": "uuid",
    "participant_id": "uuid",
    "participant_name": "John Doe",
    "alert_type": "not_attentive",
    "severity": "warning",
    "message": "Attention below threshold for 10 seconds"
  }
}
```

#### Participant Joined/Left
```json
{
  "type": "participant_update",
  "payload": {
    "action": "joined",
    "participant": {
      "id": "uuid",
      "name": "John Doe"
    }
  }
}
```

## 4. Error Responses

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request body",
    "details": [
      {"field": "email", "message": "Invalid email format"}
    ]
  }
}
```

| HTTP Code | Error Code       | Mô tả                  |
| --------- | ---------------- | ---------------------- |
| 400       | VALIDATION_ERROR | Request không hợp lệ   |
| 401       | UNAUTHORIZED     | Chưa đăng nhập         |
| 403       | FORBIDDEN        | Không có quyền         |
| 404       | NOT_FOUND        | Resource không tồn tại |
| 429       | RATE_LIMITED     | Quá nhiều requests     |
| 500       | INTERNAL_ERROR   | Lỗi server             |

