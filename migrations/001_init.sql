-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    avatar_url VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Meetings table
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    host_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Participants table
CREATE TABLE IF NOT EXISTS participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    track_id INTEGER,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    left_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Attention metrics (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS attention_metrics (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    meeting_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    attention_score DOUBLE PRECISION,
    gaze_score DOUBLE PRECISION,
    head_pose_score DOUBLE PRECISION,
    eye_openness_score DOUBLE PRECISION,
    is_looking_away BOOLEAN DEFAULT FALSE,
    is_drowsy BOOLEAN DEFAULT FALSE
);

-- Convert to hypertable
SELECT create_hypertable('attention_metrics', 'time', if_not_exists => TRUE);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    participant_id UUID REFERENCES participants(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT,
    duration_seconds DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Meeting summaries table
CREATE TABLE IF NOT EXISTS meeting_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID UNIQUE REFERENCES meetings(id) ON DELETE CASCADE,
    duration_minutes INTEGER,
    participant_count INTEGER,
    avg_attention_score DOUBLE PRECISION,
    min_attention_score DOUBLE PRECISION,
    max_attention_score DOUBLE PRECISION,
    total_alerts INTEGER DEFAULT 0,
    low_attention_segments INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_meetings_host ON meetings(host_id);
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);
CREATE INDEX IF NOT EXISTS idx_participants_meeting ON participants(meeting_id);
CREATE INDEX IF NOT EXISTS idx_participants_user ON participants(user_id);
CREATE INDEX IF NOT EXISTS idx_attention_meeting ON attention_metrics(meeting_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_attention_participant ON attention_metrics(participant_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_meeting ON alerts(meeting_id);
CREATE INDEX IF NOT EXISTS idx_alerts_participant ON alerts(participant_id);

