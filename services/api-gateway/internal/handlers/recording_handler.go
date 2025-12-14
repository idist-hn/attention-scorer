package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"gorm.io/gorm"

	"github.com/attention-detection/api-gateway/internal/models"
)

type RecordingHandler struct {
	db          *gorm.DB
	storagePath string
}

func NewRecordingHandler(db *gorm.DB) *RecordingHandler {
	storagePath := os.Getenv("VIDEO_STORAGE_PATH")
	if storagePath == "" {
		storagePath = "/app/recordings"
	}
	// Ensure storage directory exists
	os.MkdirAll(storagePath, 0755)

	return &RecordingHandler{db: db, storagePath: storagePath}
}

// UploadRecording handles video upload with detection timeline
func (h *RecordingHandler) UploadRecording(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)
	meetingIDStr := c.FormValue("meeting_id")
	durationStr := c.FormValue("duration_seconds")
	timelineJSON := c.FormValue("timeline")
	alertsJSON := c.FormValue("alerts")

	var meetingID uuid.UUID
	if meetingIDStr != "" {
		var err error
		meetingID, err = uuid.Parse(meetingIDStr)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid meeting_id"})
		}
	}

	// Get uploaded file
	file, err := c.FormFile("video")
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "No video file"})
	}

	// Generate unique filename
	recordingID := uuid.New()
	ext := filepath.Ext(file.Filename)
	if ext == "" {
		ext = ".webm"
	}
	filename := fmt.Sprintf("%s%s", recordingID.String(), ext)
	filePath := filepath.Join(h.storagePath, filename)

	// Save file
	if err := c.SaveFile(file, filePath); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save"})
	}

	// Parse duration
	var duration float64
	fmt.Sscanf(durationStr, "%f", &duration)

	// Parse alerts count
	alertCount := 0
	if alertsJSON != "" {
		var alerts []interface{}
		if err := json.Unmarshal([]byte(alertsJSON), &alerts); err == nil {
			alertCount = len(alerts)
		}
	}

	// Create recording record
	recording := models.VideoRecording{
		ID:              recordingID,
		MeetingID:       meetingID,
		UserID:          userID,
		Filename:        filename,
		FilePath:        filePath,
		FileSize:        file.Size,
		DurationSeconds: duration,
		Format:          ext[1:],
		Status:          "ready",
		AlertsData:      alertsJSON,
		AlertCount:      alertCount,
	}

	if err := h.db.Create(&recording).Error; err != nil {
		os.Remove(filePath)
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "DB error"})
	}

	// Save detection timeline if provided
	if timelineJSON != "" {
		var timeline []map[string]interface{}
		if err := json.Unmarshal([]byte(timelineJSON), &timeline); err == nil {
			h.saveTimeline(recordingID, timeline)
		}
	}

	return c.Status(fiber.StatusCreated).JSON(recording)
}

func (h *RecordingHandler) saveTimeline(recordingID uuid.UUID, timeline []map[string]interface{}) {
	for _, entry := range timeline {
		timestampMs, _ := entry["timestamp_ms"].(float64)
		facesData, _ := json.Marshal(entry["faces"])
		avgScore, _ := entry["avg_attention"].(float64)

		dt := models.DetectionTimeline{
			Time:              time.Now(),
			RecordingID:       recordingID,
			VideoTimestampMs:  int64(timestampMs),
			FacesData:         string(facesData),
			AvgAttentionScore: avgScore,
		}
		h.db.Create(&dt)
	}
}

// ListRecordings returns user's recordings
func (h *RecordingHandler) ListRecordings(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)
	meetingID := c.Query("meeting_id")

	var recordings []models.VideoRecording
	query := h.db.Where("user_id = ?", userID).Order("created_at DESC")
	if meetingID != "" {
		query = query.Where("meeting_id = ?", meetingID)
	}
	query.Find(&recordings)

	return c.JSON(recordings)
}

// GetRecording returns a single recording
func (h *RecordingHandler) GetRecording(c *fiber.Ctx) error {
	id := c.Params("id")
	var recording models.VideoRecording
	if err := h.db.First(&recording, "id = ?", id).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Not found"})
	}
	return c.JSON(recording)
}

// StreamVideo streams the video file
func (h *RecordingHandler) StreamVideo(c *fiber.Ctx) error {
	id := c.Params("id")
	var recording models.VideoRecording
	if err := h.db.First(&recording, "id = ?", id).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Not found"})
	}

	file, err := os.Open(recording.FilePath)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "File not found"})
	}
	defer file.Close()

	c.Set("Content-Type", "video/"+recording.Format)
	c.Set("Content-Disposition", fmt.Sprintf("inline; filename=%s", recording.Filename))

	_, err = io.Copy(c.Response().BodyWriter(), file)
	return err
}

// GetTimeline returns detection timeline for a recording
func (h *RecordingHandler) GetTimeline(c *fiber.Ctx) error {
	id := c.Params("id")
	recordingID, err := uuid.Parse(id)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid ID"})
	}

	var timeline []models.DetectionTimeline
	h.db.Where("recording_id = ?", recordingID).
		Order("video_timestamp_ms ASC").
		Find(&timeline)

	// Convert to response format
	result := make([]map[string]interface{}, len(timeline))
	for i, t := range timeline {
		var faces []interface{}
		json.Unmarshal([]byte(t.FacesData), &faces)
		result[i] = map[string]interface{}{
			"timestamp_ms":  t.VideoTimestampMs,
			"faces":         faces,
			"avg_attention": t.AvgAttentionScore,
		}
	}

	return c.JSON(result)
}

// GetAlerts returns alerts for a recording
func (h *RecordingHandler) GetAlerts(c *fiber.Ctx) error {
	id := c.Params("id")
	var recording models.VideoRecording
	if err := h.db.First(&recording, "id = ?", id).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Not found"})
	}

	if recording.AlertsData == "" {
		return c.JSON([]interface{}{})
	}

	var alerts []interface{}
	if err := json.Unmarshal([]byte(recording.AlertsData), &alerts); err != nil {
		return c.JSON([]interface{}{})
	}

	return c.JSON(alerts)
}

// DeleteRecording deletes a recording
func (h *RecordingHandler) DeleteRecording(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)
	id := c.Params("id")

	var recording models.VideoRecording
	if err := h.db.First(&recording, "id = ? AND user_id = ?", id, userID).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Not found"})
	}

	// Delete file
	os.Remove(recording.FilePath)

	// Delete timeline
	h.db.Where("recording_id = ?", recording.ID).Delete(&models.DetectionTimeline{})

	// Delete record
	h.db.Delete(&recording)

	return c.JSON(fiber.Map{"message": "Deleted"})
}

// StartRecording creates a new recording session for streaming upload
func (h *RecordingHandler) StartRecording(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)

	type StartRequest struct {
		MeetingID string `json:"meeting_id"`
	}
	var req StartRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid request"})
	}

	var meetingID uuid.UUID
	if req.MeetingID != "" {
		var err error
		meetingID, err = uuid.Parse(req.MeetingID)
		if err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid meeting_id"})
		}
	}

	recordingID := uuid.New()
	filename := fmt.Sprintf("%s.webm", recordingID.String())
	filePath := filepath.Join(h.storagePath, filename)

	// Create empty file
	file, err := os.Create(filePath)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to create file"})
	}
	file.Close()

	recording := models.VideoRecording{
		ID:         recordingID,
		MeetingID:  meetingID,
		UserID:     userID,
		Filename:   filename,
		FilePath:   filePath,
		FileSize:   0,
		Format:     "webm",
		Status:     "recording",
		AlertsData: "[]",
		AlertCount: 0,
	}

	if err := h.db.Create(&recording).Error; err != nil {
		os.Remove(filePath)
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "DB error", "details": err.Error()})
	}

	return c.Status(fiber.StatusCreated).JSON(recording)
}

// AppendChunk appends a video chunk to an existing recording
func (h *RecordingHandler) AppendChunk(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)
	id := c.Params("id")

	recordingID, err := uuid.Parse(id)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid ID"})
	}

	var recording models.VideoRecording
	if err := h.db.First(&recording, "id = ? AND user_id = ?", recordingID, userID).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Not found"})
	}

	if recording.Status != "recording" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Recording not active"})
	}

	// Get chunk data from body
	chunkData := c.Body()
	if len(chunkData) == 0 {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Empty chunk"})
	}

	// Append to file
	file, err := os.OpenFile(recording.FilePath, os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to open file"})
	}
	defer file.Close()

	written, err := file.Write(chunkData)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to write chunk"})
	}

	// Update file size
	h.db.Model(&recording).Update("file_size", gorm.Expr("file_size + ?", written))

	return c.JSON(fiber.Map{"written": written, "total_size": recording.FileSize + int64(written)})
}

// CompleteRecording marks recording as complete and saves metadata
func (h *RecordingHandler) CompleteRecording(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)
	id := c.Params("id")

	recordingID, err := uuid.Parse(id)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid ID"})
	}

	var recording models.VideoRecording
	if err := h.db.First(&recording, "id = ? AND user_id = ?", recordingID, userID).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Not found"})
	}

	type CompleteRequest struct {
		Duration float64                  `json:"duration_seconds"`
		Alerts   []map[string]interface{} `json:"alerts"`
		Timeline []map[string]interface{} `json:"timeline"`
	}
	var req CompleteRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid request"})
	}

	// Get actual file size
	fileInfo, _ := os.Stat(recording.FilePath)
	fileSize := int64(0)
	if fileInfo != nil {
		fileSize = fileInfo.Size()
	}

	// Update recording
	alertsJSON := ""
	alertCount := 0
	if len(req.Alerts) > 0 {
		alertBytes, _ := json.Marshal(req.Alerts)
		alertsJSON = string(alertBytes)
		alertCount = len(req.Alerts)
	}

	h.db.Model(&recording).Updates(map[string]interface{}{
		"status":           "ready",
		"duration_seconds": req.Duration,
		"file_size":        fileSize,
		"alerts_data":      alertsJSON,
		"alert_count":      alertCount,
	})

	// Save timeline
	if len(req.Timeline) > 0 {
		h.saveTimeline(recordingID, req.Timeline)
	}

	// Reload recording
	h.db.First(&recording, "id = ?", recordingID)

	return c.JSON(recording)
}
