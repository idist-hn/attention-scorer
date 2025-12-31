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
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
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
    status VARCHAR(20) DEFAULT 'scheduled',  -- scheduled, active, ended
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meetings_host ON meetings(host_id);
CREATE INDEX idx_meetings_status ON meetings(status);
```
CREATE INDEX idx_meetings_status ON meetings(status);
```

### 2.3 Participants Table

```sql
CREATE TABLE participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    track_id INTEGER,                 -- Face tracking ID
    joined_at TIMESTAMPTZ,
    left_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_participants_meeting ON participants(meeting_id);
CREATE INDEX idx_participants_user ON participants(user_id);
```

### 2.4 Alerts Table

```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,  -- not_attentive, looking_away, drowsy
    severity VARCHAR(20) NOT NULL,    -- info, warning, critical
    message TEXT,
    duration_seconds FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_meeting ON alerts(meeting_id);
CREATE INDEX idx_alerts_participant ON alerts(participant_id);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
```

### 2.5 Meeting Summaries Table

```sql
CREATE TABLE meeting_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID UNIQUE NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    duration_minutes INTEGER,
    participant_count INTEGER,
    avg_attention_score FLOAT,
    min_attention_score FLOAT,
    max_attention_score FLOAT,
    total_alerts INTEGER,
    low_attention_segments INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_summaries_meeting ON meeting_summaries(meeting_id);
```

### 2.6 Video Analyses Table

```sql
CREATE TABLE video_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    duration FLOAT,
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

### 2.7 Video Recordings Table

```sql
CREATE TABLE video_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id),
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    duration_seconds FLOAT,
    width INTEGER,
    height INTEGER,
    format VARCHAR(20) DEFAULT 'webm',
    status VARCHAR(20) DEFAULT 'processing',  -- processing, ready, failed
    alerts_data JSONB,                        -- JSON array of alerts
    alert_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recordings_meeting ON video_recordings(meeting_id);
CREATE INDEX idx_recordings_user ON video_recordings(user_id);
```

### 2.8 Detection Timeline Table

```sql
CREATE TABLE detection_timeline (
    time TIMESTAMPTZ NOT NULL,
    recording_id UUID NOT NULL REFERENCES video_recordings(id) ON DELETE CASCADE,
    video_timestamp_ms BIGINT NOT NULL,
    faces_data JSONB NOT NULL,                -- JSON array of face detections
    avg_attention_score FLOAT
);

CREATE INDEX idx_timeline_recording ON detection_timeline(recording_id);
CREATE INDEX idx_timeline_time ON detection_timeline(time);
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

    -- Attention scores (0.0 - 100.0)
    attention_score FLOAT NOT NULL,
    gaze_score FLOAT,
    head_pose_score FLOAT,
    eye_openness_score FLOAT,

    -- Flags
    is_looking_away BOOLEAN DEFAULT false,
    is_drowsy BOOLEAN DEFAULT false
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

