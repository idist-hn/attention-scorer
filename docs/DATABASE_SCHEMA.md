# Database Schema

## 1. Tổng quan

Hệ thống sử dụng 2 database chính:

| Database | Loại | Mục đích |
|----------|------|----------|
| **PostgreSQL** | Relational | Lưu trữ dữ liệu meetings, users, participants |
| **TimescaleDB** | Time-series | Lưu trữ attention metrics theo thời gian |

## 2. PostgreSQL Schema

### 2.1 Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    face_encoding BYTEA,          -- Stored face encoding for recognition
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);
```

### 2.2 Meetings Table

```sql
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    host_id UUID NOT NULL REFERENCES users(id),
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'scheduled',  -- scheduled, active, ended, cancelled
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meetings_host ON meetings(host_id);
CREATE INDEX idx_meetings_status ON meetings(status);
CREATE INDEX idx_meetings_scheduled ON meetings(scheduled_start);
```

### 2.3 Participants Table

```sql
CREATE TABLE participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    guest_name VARCHAR(255),          -- For guest participants
    face_encoding BYTEA,              -- Session-specific face encoding
    track_id VARCHAR(100),            -- ByteTrack assigned ID
    joined_at TIMESTAMPTZ,
    left_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'invited',  -- invited, joined, left
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_participants_meeting ON participants(meeting_id);
CREATE INDEX idx_participants_user ON participants(user_id);
CREATE INDEX idx_participants_track ON participants(meeting_id, track_id);
```

### 2.4 Alerts Table

```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,  -- not_attentive, drowsy, looking_away, absent
    severity VARCHAR(20) NOT NULL,    -- info, warning, critical
    message TEXT,
    triggered_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_alerts_meeting ON alerts(meeting_id);
CREATE INDEX idx_alerts_participant ON alerts(participant_id);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
```

### 2.5 Meeting Reports Table

```sql
CREATE TABLE meeting_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    total_duration_seconds INTEGER,
    avg_attention_score FLOAT,
    min_attention_score FLOAT,
    max_attention_score FLOAT,
    total_alerts INTEGER,
    participant_count INTEGER,
    summary JSONB,                    -- Detailed summary data
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_reports_meeting ON meeting_reports(meeting_id);
```

### 2.6 Video Analyses Table

```sql
CREATE TABLE video_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    duration FLOAT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    progress INTEGER DEFAULT 0,            -- 0-100
    results JSONB,                         -- Analysis results
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_video_analyses_user ON video_analyses(user_id);
CREATE INDEX idx_video_analyses_status ON video_analyses(status);
```

### 2.7 Recordings Table

```sql
CREATE TABLE recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,
    format VARCHAR(20) DEFAULT 'webm',
    status VARCHAR(20) DEFAULT 'recording',  -- recording, completed, failed
    alert_count INTEGER DEFAULT 0,
    alerts_data JSONB,
    timeline_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recordings_meeting ON recordings(meeting_id);
CREATE INDEX idx_recordings_user ON recordings(user_id);
```

## 3. TimescaleDB Schema (Attention Metrics)

### 3.1 Attention Metrics Hypertable

```sql
-- Create extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create table
CREATE TABLE attention_metrics (
    time TIMESTAMPTZ NOT NULL,
    meeting_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    track_id VARCHAR(100),
    
    -- Attention scores (0.0 - 1.0)
    attention_score FLOAT NOT NULL,
    gaze_score FLOAT,
    head_pose_score FLOAT,
    eye_openness_score FLOAT,
    
    -- Raw measurements
    head_yaw FLOAT,                   -- Góc quay ngang (-90 to 90)
    head_pitch FLOAT,                 -- Góc gật đầu (-90 to 90)
    head_roll FLOAT,                  -- Góc nghiêng (-90 to 90)
    eye_aspect_ratio FLOAT,           -- EAR value
    blink_rate FLOAT,                 -- Blinks per minute
    perclos FLOAT,                    -- Percentage of eye closure
    
    -- Gaze direction
    gaze_x FLOAT,                     -- Normalized gaze X (-1 to 1)
    gaze_y FLOAT,                     -- Normalized gaze Y (-1 to 1)
    
    -- Flags
    is_present BOOLEAN DEFAULT true,
    is_looking_away BOOLEAN DEFAULT false,
    is_drowsy BOOLEAN DEFAULT false,
    
    -- Bounding box (for visualization)
    bbox_x INTEGER,
    bbox_y INTEGER,
    bbox_width INTEGER,
    bbox_height INTEGER
);

-- Convert to hypertable
SELECT create_hypertable('attention_metrics', 'time');

-- Create indexes
CREATE INDEX idx_metrics_meeting ON attention_metrics(meeting_id, time DESC);
CREATE INDEX idx_metrics_participant ON attention_metrics(participant_id, time DESC);
```

### 3.2 Compression Policy

```sql
-- Enable compression
ALTER TABLE attention_metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'meeting_id, participant_id'
);

-- Add compression policy (compress data older than 1 day)
SELECT add_compression_policy('attention_metrics', INTERVAL '1 day');
```

### 3.3 Retention Policy

```sql
-- Add retention policy (delete data older than 90 days)
SELECT add_retention_policy('attention_metrics', INTERVAL '90 days');
```

### 3.4 Continuous Aggregates

```sql
-- 1-minute aggregates
CREATE MATERIALIZED VIEW attention_metrics_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    meeting_id,
    participant_id,
    AVG(attention_score) AS avg_attention,
    MIN(attention_score) AS min_attention,
    MAX(attention_score) AS max_attention,
    AVG(gaze_score) AS avg_gaze,
    AVG(head_pose_score) AS avg_head_pose,
    COUNT(*) AS sample_count
FROM attention_metrics
GROUP BY bucket, meeting_id, participant_id;

-- Refresh policy
SELECT add_continuous_aggregate_policy('attention_metrics_1min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');
```

## 4. Redis Data Structures

### 4.1 Frame Queue
```
Key: frame_queue:{meeting_id}
Type: List (LPUSH/BRPOP)
Value: JSON encoded frame data
TTL: 60 seconds
```

### 4.2 Attention Results
```
Key: attention:{meeting_id}:{participant_id}
Type: Hash
Fields: attention_score, gaze_score, head_pose_score, ...
TTL: 300 seconds
```

### 4.3 Active Meetings
```
Key: active_meetings
Type: Set
Value: meeting_id
```

### 4.4 WebSocket Sessions
```
Key: ws_sessions:{meeting_id}
Type: Set
Value: session_id
```

