package models

import (
	"time"

	"github.com/google/uuid"
)

// User represents a user in the system
type User struct {
	ID        uuid.UUID `json:"id" gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	Email     string    `json:"email" gorm:"uniqueIndex;not null"`
	Password  string    `json:"-" gorm:"not null"`
	Name      string    `json:"name"`
	AvatarURL string    `json:"avatar_url,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Meeting represents a video meeting session
type Meeting struct {
	ID           uuid.UUID     `json:"id" gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	Title        string        `json:"title" gorm:"not null"`
	Description  string        `json:"description,omitempty"`
	HostID       uuid.UUID     `json:"host_id" gorm:"type:uuid;not null"`
	Host         User          `json:"host,omitempty" gorm:"foreignKey:HostID"`
	Status       string        `json:"status" gorm:"default:'scheduled'"` // scheduled, active, ended
	StartTime    time.Time     `json:"start_time,omitempty"`
	EndTime      time.Time     `json:"end_time,omitempty"`
	Participants []Participant `json:"participants,omitempty" gorm:"foreignKey:MeetingID"`
	CreatedAt    time.Time     `json:"created_at"`
	UpdatedAt    time.Time     `json:"updated_at"`
}

// Participant represents a user participating in a meeting
type Participant struct {
	ID        uuid.UUID `json:"id" gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	MeetingID uuid.UUID `json:"meeting_id" gorm:"type:uuid;not null"`
	UserID    uuid.UUID `json:"user_id" gorm:"type:uuid;not null"`
	User      User      `json:"user,omitempty" gorm:"foreignKey:UserID"`
	TrackID   int       `json:"track_id"` // Face tracking ID
	JoinedAt  time.Time `json:"joined_at"`
	LeftAt    time.Time `json:"left_at,omitempty"`
	IsActive  bool      `json:"is_active" gorm:"default:true"`
}

// AttentionMetric stores real-time attention data (TimescaleDB hypertable)
type AttentionMetric struct {
	Time             time.Time `json:"time" gorm:"not null;index"`
	MeetingID        uuid.UUID `json:"meeting_id" gorm:"type:uuid;not null"`
	ParticipantID    uuid.UUID `json:"participant_id" gorm:"type:uuid;not null"`
	AttentionScore   float64   `json:"attention_score"`
	GazeScore        float64   `json:"gaze_score"`
	HeadPoseScore    float64   `json:"head_pose_score"`
	EyeOpennessScore float64   `json:"eye_openness_score"`
	IsLookingAway    bool      `json:"is_looking_away"`
	IsDrowsy         bool      `json:"is_drowsy"`
}

// Alert represents an attention alert
type Alert struct {
	ID            uuid.UUID `json:"id" gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	MeetingID     uuid.UUID `json:"meeting_id" gorm:"type:uuid;not null"`
	ParticipantID uuid.UUID `json:"participant_id" gorm:"type:uuid;not null"`
	AlertType     string    `json:"alert_type"` // not_attentive, looking_away, drowsy
	Severity      string    `json:"severity"`   // info, warning, critical
	Message       string    `json:"message"`
	Duration      float64   `json:"duration_seconds"`
	CreatedAt     time.Time `json:"created_at"`
	ResolvedAt    time.Time `json:"resolved_at,omitempty"`
}

// MeetingSummary stores aggregated meeting statistics
type MeetingSummary struct {
	ID                   uuid.UUID `json:"id" gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	MeetingID            uuid.UUID `json:"meeting_id" gorm:"type:uuid;uniqueIndex;not null"`
	Meeting              Meeting   `json:"meeting,omitempty" gorm:"foreignKey:MeetingID"`
	Duration             int       `json:"duration_minutes"`
	ParticipantCount     int       `json:"participant_count"`
	AvgAttentionScore    float64   `json:"avg_attention_score"`
	MinAttentionScore    float64   `json:"min_attention_score"`
	MaxAttentionScore    float64   `json:"max_attention_score"`
	TotalAlerts          int       `json:"total_alerts"`
	LowAttentionSegments int       `json:"low_attention_segments"`
	CreatedAt            time.Time `json:"created_at"`
}

// TableName for TimescaleDB
func (AttentionMetric) TableName() string {
	return "attention_metrics"
}

// VideoRecording stores recorded meeting videos
type VideoRecording struct {
	ID              uuid.UUID `json:"id" gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	MeetingID       uuid.UUID `json:"meeting_id" gorm:"type:uuid"`
	Meeting         Meeting   `json:"meeting,omitempty" gorm:"foreignKey:MeetingID"`
	UserID          uuid.UUID `json:"user_id" gorm:"type:uuid"`
	User            User      `json:"user,omitempty" gorm:"foreignKey:UserID"`
	Filename        string    `json:"filename" gorm:"not null"`
	FilePath        string    `json:"file_path" gorm:"not null"`
	FileSize        int64     `json:"file_size"`
	DurationSeconds float64   `json:"duration_seconds"`
	Width           int       `json:"width"`
	Height          int       `json:"height"`
	Format          string    `json:"format" gorm:"default:'webm'"`
	Status          string    `json:"status" gorm:"default:'processing'"` // processing, ready, failed
	AlertsData      string    `json:"alerts_data" gorm:"type:jsonb"`      // JSON array of alerts
	AlertCount      int       `json:"alert_count" gorm:"default:0"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

// DetectionTimeline stores detection results for video playback
type DetectionTimeline struct {
	Time              time.Time `json:"time" gorm:"not null;index"`
	RecordingID       uuid.UUID `json:"recording_id" gorm:"type:uuid;not null"`
	VideoTimestampMs  int64     `json:"video_timestamp_ms" gorm:"not null"`
	FacesData         string    `json:"faces_data" gorm:"type:jsonb;not null"` // JSON array
	AvgAttentionScore float64   `json:"avg_attention_score"`
}

// TableName for DetectionTimeline
func (DetectionTimeline) TableName() string {
	return "detection_timeline"
}

// VideoAnalysis stores video analysis jobs for offline attention detection
type VideoAnalysis struct {
	ID           uuid.UUID `json:"id" gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	UserID       uuid.UUID `json:"user_id" gorm:"type:uuid;not null"`
	User         User      `json:"user,omitempty" gorm:"foreignKey:UserID"`
	Filename     string    `json:"filename" gorm:"not null"`
	FilePath     string    `json:"file_path" gorm:"not null"`
	FileSize     int64     `json:"file_size"`
	Duration     float64   `json:"duration"`
	Status       string    `json:"status" gorm:"default:'pending'"` // pending, processing, completed, failed
	Progress     int       `json:"progress" gorm:"default:0"`       // 0-100
	Results      string    `json:"results" gorm:"type:jsonb"`       // JSON results
	ErrorMessage string    `json:"error_message,omitempty"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}
