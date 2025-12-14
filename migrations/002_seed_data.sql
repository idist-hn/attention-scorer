-- Seed data for testing

-- Create test users (password is 'password123' hashed with bcrypt)
INSERT INTO users (id, email, password, name, avatar_url) VALUES
    ('11111111-1111-1111-1111-111111111111', 'admin@example.com', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'Admin User', 'https://api.dicebear.com/7.x/avataaars/svg?seed=admin'),
    ('22222222-2222-2222-2222-222222222222', 'john@example.com', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'John Doe', 'https://api.dicebear.com/7.x/avataaars/svg?seed=john'),
    ('33333333-3333-3333-3333-333333333333', 'jane@example.com', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'Jane Smith', 'https://api.dicebear.com/7.x/avataaars/svg?seed=jane')
ON CONFLICT (email) DO NOTHING;

-- Create test meeting
INSERT INTO meetings (id, title, description, host_id, status, start_time) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Team Standup', 'Daily standup meeting', '11111111-1111-1111-1111-111111111111', 'active', NOW())
ON CONFLICT DO NOTHING;

-- Add participants
INSERT INTO participants (id, meeting_id, user_id, track_id, is_active) VALUES
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 1, true),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '22222222-2222-2222-2222-222222222222', 2, true),
    ('dddddddd-dddd-dddd-dddd-dddddddddddd', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '33333333-3333-3333-3333-333333333333', 3, true)
ON CONFLICT DO NOTHING;

-- Add sample attention metrics for participant 1
INSERT INTO attention_metrics (time, meeting_id, participant_id, attention_score, gaze_score, head_pose_score, eye_openness_score, is_looking_away, is_drowsy)
SELECT 
    NOW() - (n * interval '1 second'),
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid,
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid,
    0.7 + random() * 0.3,
    0.8 + random() * 0.2,
    0.75 + random() * 0.25,
    0.85 + random() * 0.15,
    false,
    false
FROM generate_series(1, 30) AS n;

-- Add sample attention metrics for participant 2
INSERT INTO attention_metrics (time, meeting_id, participant_id, attention_score, gaze_score, head_pose_score, eye_openness_score, is_looking_away, is_drowsy)
SELECT 
    NOW() - (n * interval '1 second'),
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid,
    'cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid,
    0.5 + random() * 0.5,
    0.6 + random() * 0.4,
    0.65 + random() * 0.35,
    0.7 + random() * 0.3,
    random() < 0.15,
    random() < 0.05
FROM generate_series(1, 30) AS n;

-- Add sample attention metrics for participant 3
INSERT INTO attention_metrics (time, meeting_id, participant_id, attention_score, gaze_score, head_pose_score, eye_openness_score, is_looking_away, is_drowsy)
SELECT 
    NOW() - (n * interval '1 second'),
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid,
    'dddddddd-dddd-dddd-dddd-dddddddddddd'::uuid,
    0.4 + random() * 0.4,
    0.5 + random() * 0.4,
    0.55 + random() * 0.35,
    0.6 + random() * 0.3,
    random() < 0.25,
    random() < 0.1
FROM generate_series(1, 30) AS n;

-- Add sample alerts
INSERT INTO alerts (meeting_id, participant_id, alert_type, severity, message, duration_seconds) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'low_attention', 'warning', 'Participant attention dropped below threshold', 15.5),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'looking_away', 'info', 'Participant looking away from screen', 8.2);

