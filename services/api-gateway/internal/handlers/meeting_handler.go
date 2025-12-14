package handlers

import (
	"time"

	"github.com/attention-detection/api-gateway/internal/middleware"
	"github.com/attention-detection/api-gateway/internal/models"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"gorm.io/gorm"
)

type MeetingHandler struct {
	db *gorm.DB
}

func NewMeetingHandler(db *gorm.DB) *MeetingHandler {
	return &MeetingHandler{db: db}
}

type CreateMeetingRequest struct {
	Title       string `json:"title" validate:"required"`
	Description string `json:"description"`
}

type UpdateMeetingRequest struct {
	Title       string `json:"title,omitempty"`
	Description string `json:"description,omitempty"`
	Status      string `json:"status,omitempty"`
}

// Create creates a new meeting
func (h *MeetingHandler) Create(c *fiber.Ctx) error {
	userID, ok := middleware.GetUserID(c)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "unauthorized"})
	}

	var req CreateMeetingRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request"})
	}

	meeting := models.Meeting{
		Title:       req.Title,
		Description: req.Description,
		HostID:      userID,
		Status:      "scheduled",
	}

	if err := h.db.Create(&meeting).Error; err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "failed to create meeting"})
	}

	h.db.Preload("Host").First(&meeting, "id = ?", meeting.ID)
	return c.Status(fiber.StatusCreated).JSON(meeting)
}

// List returns all meetings for the current user
func (h *MeetingHandler) List(c *fiber.Ctx) error {
	userID, _ := middleware.GetUserID(c)

	var meetings []models.Meeting
	h.db.Preload("Host").Preload("Participants").
		Where("host_id = ?", userID).
		Or("id IN (SELECT meeting_id FROM participants WHERE user_id = ?)", userID).
		Order("created_at DESC").
		Find(&meetings)

	return c.JSON(meetings)
}

// Get returns a single meeting by ID
func (h *MeetingHandler) Get(c *fiber.Ctx) error {
	id, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid meeting ID"})
	}

	var meeting models.Meeting
	if err := h.db.Preload("Host").Preload("Participants.User").First(&meeting, "id = ?", id).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "meeting not found"})
	}

	return c.JSON(meeting)
}

// Update updates a meeting
func (h *MeetingHandler) Update(c *fiber.Ctx) error {
	userID, _ := middleware.GetUserID(c)
	id, err := uuid.Parse(c.Params("id"))
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid meeting ID"})
	}

	var meeting models.Meeting
	if err := h.db.First(&meeting, "id = ? AND host_id = ?", id, userID).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "meeting not found"})
	}

	var req UpdateMeetingRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid request"})
	}

	updates := make(map[string]interface{})
	if req.Title != "" {
		updates["title"] = req.Title
	}
	if req.Description != "" {
		updates["description"] = req.Description
	}
	if req.Status != "" {
		updates["status"] = req.Status
		if req.Status == "active" {
			updates["start_time"] = time.Now()
		} else if req.Status == "ended" {
			updates["end_time"] = time.Now()
		}
	}

	h.db.Model(&meeting).Updates(updates)
	h.db.Preload("Host").First(&meeting, "id = ?", id)

	return c.JSON(meeting)
}

// Start starts a meeting
func (h *MeetingHandler) Start(c *fiber.Ctx) error {
	userID, _ := middleware.GetUserID(c)
	id, _ := uuid.Parse(c.Params("id"))

	var meeting models.Meeting
	if err := h.db.First(&meeting, "id = ? AND host_id = ?", id, userID).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "meeting not found"})
	}

	h.db.Model(&meeting).Updates(map[string]interface{}{
		"status":     "active",
		"start_time": time.Now(),
	})

	return c.JSON(fiber.Map{"message": "meeting started", "meeting_id": id})
}

// End ends a meeting
func (h *MeetingHandler) End(c *fiber.Ctx) error {
	userID, _ := middleware.GetUserID(c)
	id, _ := uuid.Parse(c.Params("id"))

	var meeting models.Meeting
	if err := h.db.First(&meeting, "id = ? AND host_id = ?", id, userID).Error; err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "meeting not found"})
	}

	h.db.Model(&meeting).Updates(map[string]interface{}{
		"status":   "ended",
		"end_time": time.Now(),
	})

	return c.JSON(fiber.Map{"message": "meeting ended", "meeting_id": id})
}

