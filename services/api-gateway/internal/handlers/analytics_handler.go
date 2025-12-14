package handlers

import (
	"time"

	"github.com/attention-detection/api-gateway/internal/models"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type AnalyticsHandler struct {
	db *gorm.DB
}

func NewAnalyticsHandler(db *gorm.DB) *AnalyticsHandler {
	return &AnalyticsHandler{db: db}
}

type TimeRange struct {
	Start time.Time `query:"start"`
	End   time.Time `query:"end"`
}

type AttentionSummary struct {
	ParticipantID    uuid.UUID `json:"participant_id"`
	ParticipantName  string    `json:"participant_name"`
	AvgAttention     float64   `json:"avg_attention"`
	MinAttention     float64   `json:"min_attention"`
	MaxAttention     float64   `json:"max_attention"`
	LookingAwayCount int       `json:"looking_away_count"`
	DrowsyCount      int       `json:"drowsy_count"`
}

// GetMeetingMetrics returns attention metrics for a meeting
func (h *AnalyticsHandler) GetMeetingMetrics(c *fiber.Ctx) error {
	meetingID, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid meeting ID"})
	}

	var timeRange TimeRange
	if err := c.QueryParser(&timeRange); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid time range"})
	}

	// Default to last hour if not specified
	if timeRange.End.IsZero() {
		timeRange.End = time.Now()
	}
	if timeRange.Start.IsZero() {
		timeRange.Start = timeRange.End.Add(-1 * time.Hour)
	}

	var metrics []models.AttentionMetric
	h.db.Where("meeting_id = ? AND time BETWEEN ? AND ?", meetingID, timeRange.Start, timeRange.End).
		Order("time ASC").
		Find(&metrics)

	return c.JSON(metrics)
}

// GetParticipantSummary returns aggregated attention for each participant
func (h *AnalyticsHandler) GetParticipantSummary(c *fiber.Ctx) error {
	meetingID, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid meeting ID"})
	}

	var summaries []AttentionSummary
	
	query := `
		SELECT 
			p.user_id as participant_id,
			u.name as participant_name,
			COALESCE(AVG(m.attention_score), 0) as avg_attention,
			COALESCE(MIN(m.attention_score), 0) as min_attention,
			COALESCE(MAX(m.attention_score), 0) as max_attention,
			COUNT(CASE WHEN m.is_looking_away THEN 1 END) as looking_away_count,
			COUNT(CASE WHEN m.is_drowsy THEN 1 END) as drowsy_count
		FROM participants p
		JOIN users u ON p.user_id = u.id
		LEFT JOIN attention_metrics m ON p.id = m.participant_id
		WHERE p.meeting_id = ?
		GROUP BY p.user_id, u.name
	`
	
	h.db.Raw(query, meetingID).Scan(&summaries)

	return c.JSON(summaries)
}

// GetMeetingAlerts returns alerts for a meeting
func (h *AnalyticsHandler) GetMeetingAlerts(c *fiber.Ctx) error {
	meetingID, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid meeting ID"})
	}

	var alerts []models.Alert
	h.db.Where("meeting_id = ?", meetingID).
		Order("created_at DESC").
		Limit(100).
		Find(&alerts)

	return c.JSON(alerts)
}

// GetMeetingSummary returns overall meeting summary
func (h *AnalyticsHandler) GetMeetingSummary(c *fiber.Ctx) error {
	meetingID, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid meeting ID"})
	}

	var summary models.MeetingSummary
	if err := h.db.Where("meeting_id = ?", meetingID).First(&summary).Error; err != nil {
		// Generate summary on the fly if not exists
		var meeting models.Meeting
		h.db.First(&meeting, "id = ?", meetingID)

		var avgScore, minScore, maxScore float64
		h.db.Model(&models.AttentionMetric{}).
			Where("meeting_id = ?", meetingID).
			Select("COALESCE(AVG(attention_score), 0), COALESCE(MIN(attention_score), 0), COALESCE(MAX(attention_score), 0)").
			Row().Scan(&avgScore, &minScore, &maxScore)

		var alertCount int64
		h.db.Model(&models.Alert{}).Where("meeting_id = ?", meetingID).Count(&alertCount)

		var participantCount int64
		h.db.Model(&models.Participant{}).Where("meeting_id = ?", meetingID).Count(&participantCount)

		summary = models.MeetingSummary{
			MeetingID:         meetingID,
			AvgAttentionScore: avgScore,
			MinAttentionScore: minScore,
			MaxAttentionScore: maxScore,
			TotalAlerts:       int(alertCount),
			ParticipantCount:  int(participantCount),
		}

		if !meeting.StartTime.IsZero() && !meeting.EndTime.IsZero() {
			summary.Duration = int(meeting.EndTime.Sub(meeting.StartTime).Minutes())
		}
	}

	return c.JSON(summary)
}

