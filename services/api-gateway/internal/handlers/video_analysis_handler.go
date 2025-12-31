package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"gorm.io/gorm"

	"github.com/attention-detection/api-gateway/internal/models"
)

type VideoAnalysisHandler struct {
	db          *gorm.DB
	storagePath string
	aiURL       string
}

func NewVideoAnalysisHandler(db *gorm.DB) *VideoAnalysisHandler {
	storagePath := os.Getenv("VIDEO_STORAGE_PATH")
	if storagePath == "" {
		storagePath = "/app/recordings"
	}
	os.MkdirAll(filepath.Join(storagePath, "analysis"), 0755)

	aiURL := os.Getenv("AI_PROCESSOR_URL")
	if aiURL == "" {
		aiURL = "http://pipeline-orchestrator:8000"
	}

	return &VideoAnalysisHandler{
		db:          db,
		storagePath: filepath.Join(storagePath, "analysis"),
		aiURL:       aiURL,
	}
}

// Upload handles video upload for analysis
func (h *VideoAnalysisHandler) Upload(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)

	file, err := c.FormFile("video")
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "No video file provided"})
	}

	// Validate file type
	ext := filepath.Ext(file.Filename)
	validExts := map[string]bool{".mp4": true, ".webm": true, ".avi": true, ".mov": true, ".mkv": true}
	if !validExts[ext] {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid video format"})
	}

	// Generate unique filename
	analysisID := uuid.New()
	filename := fmt.Sprintf("%s%s", analysisID.String(), ext)
	filePath := filepath.Join(h.storagePath, filename)

	// Save file
	if err := c.SaveFile(file, filePath); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to save file"})
	}

	// Create analysis record
	analysis := models.VideoAnalysis{
		ID:       analysisID,
		UserID:   userID,
		Filename: file.Filename,
		FilePath: filePath,
		FileSize: file.Size,
		Status:   "pending",
		Progress: 0,
	}

	if err := h.db.Create(&analysis).Error; err != nil {
		os.Remove(filePath)
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to create analysis"})
	}

	// Trigger async processing
	go h.triggerAnalysis(analysisID, filePath)

	return c.Status(fiber.StatusCreated).JSON(analysis)
}

// triggerAnalysis calls AI processor to analyze video
func (h *VideoAnalysisHandler) triggerAnalysis(analysisID uuid.UUID, filePath string) {
	payload := map[string]string{
		"analysis_id": analysisID.String(),
		"video_path":  filePath,
	}

	jsonData, _ := json.Marshal(payload)
	resp, err := http.Post(h.aiURL+"/analyze-video", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		h.db.Model(&models.VideoAnalysis{}).Where("id = ?", analysisID).Updates(map[string]interface{}{
			"status":        "failed",
			"error_message": "Failed to connect to AI processor",
		})
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusAccepted {
		h.db.Model(&models.VideoAnalysis{}).Where("id = ?", analysisID).Updates(map[string]interface{}{
			"status":        "failed",
			"error_message": fmt.Sprintf("AI processor returned status %d", resp.StatusCode),
		})
	}
}

// GetByID returns analysis by ID
func (h *VideoAnalysisHandler) GetByID(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)
	id := c.Params("id")

	var analysis models.VideoAnalysis
	if err := h.db.Where("id = ? AND user_id = ?", id, userID).First(&analysis).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Analysis not found"})
	}

	return c.JSON(analysis)
}

// List returns all analyses for user
func (h *VideoAnalysisHandler) List(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)

	var analyses []models.VideoAnalysis
	if err := h.db.Where("user_id = ?", userID).Order("created_at DESC").Find(&analyses).Error; err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to fetch analyses"})
	}

	return c.JSON(analyses)
}

// Delete removes an analysis
func (h *VideoAnalysisHandler) Delete(c *fiber.Ctx) error {
	userID := c.Locals("userID").(uuid.UUID)
	id := c.Params("id")

	var analysis models.VideoAnalysis
	if err := h.db.Where("id = ? AND user_id = ?", id, userID).First(&analysis).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Analysis not found"})
	}

	// Remove file
	os.Remove(analysis.FilePath)

	// Delete record
	h.db.Delete(&analysis)

	return c.JSON(fiber.Map{"message": "Analysis deleted"})
}

// UpdateProgress updates analysis progress (called by AI processor)
func (h *VideoAnalysisHandler) UpdateProgress(c *fiber.Ctx) error {
	id := c.Params("id")

	var body struct {
		Progress int     `json:"progress"`
		Status   string  `json:"status"`
		Duration float64 `json:"duration,omitempty"`
		Results  string  `json:"results,omitempty"`
		Error    string  `json:"error,omitempty"`
	}

	if err := c.BodyParser(&body); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid body"})
	}

	updates := map[string]interface{}{
		"progress": body.Progress,
	}

	if body.Status != "" {
		updates["status"] = body.Status
	}
	if body.Duration > 0 {
		updates["duration"] = body.Duration
	}
	if body.Results != "" {
		updates["results"] = body.Results
	}
	if body.Error != "" {
		updates["error_message"] = body.Error
	}

	if err := h.db.Model(&models.VideoAnalysis{}).Where("id = ?", id).Updates(updates).Error; err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to update"})
	}

	return c.JSON(fiber.Map{"message": "Updated"})
}
