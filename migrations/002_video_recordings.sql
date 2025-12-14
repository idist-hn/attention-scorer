-- Video recordings table
CREATE TABLE IF NOT EXISTS video_recordings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    filename VARCHAR(512) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_size BIGINT DEFAULT 0,
    duration_seconds DOUBLE PRECISION DEFAULT 0,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    format VARCHAR(50) DEFAULT 'webm',
    status VARCHAR(50) DEFAULT 'processing', -- processing, ready, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Detection timeline for video playback (stores detection results per frame/timestamp)
CREATE TABLE IF NOT EXISTS detection_timeline (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    recording_id UUID NOT NULL REFERENCES video_recordings(id) ON DELETE CASCADE,
    video_timestamp_ms BIGINT NOT NULL, -- milliseconds from video start
    faces_data JSONB NOT NULL, -- array of face detection results
    avg_attention_score DOUBLE PRECISION DEFAULT 0
);

-- Convert to hypertable for efficient time-series queries
SELECT create_hypertable('detection_timeline', 'time', if_not_exists => TRUE);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_recordings_meeting ON video_recordings(meeting_id);
CREATE INDEX IF NOT EXISTS idx_recordings_user ON video_recordings(user_id);
CREATE INDEX IF NOT EXISTS idx_recordings_status ON video_recordings(status);
CREATE INDEX IF NOT EXISTS idx_timeline_recording ON detection_timeline(recording_id, video_timestamp_ms);

