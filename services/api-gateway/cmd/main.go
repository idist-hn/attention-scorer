package main

import (
	"encoding/json"
	"fmt"
	"log"
	"strconv"
	"sync"
	"time"

	"github.com/attention-detection/api-gateway/internal/config"
	"github.com/attention-detection/api-gateway/internal/handlers"
	"github.com/attention-detection/api-gateway/internal/middleware"
	"github.com/attention-detection/api-gateway/internal/models"
	"github.com/attention-detection/api-gateway/internal/services"
	ws "github.com/attention-detection/api-gateway/internal/websocket"
	"github.com/attention-detection/api-gateway/pkg/auth"
	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/google/uuid"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func main() {
	// Load configuration
	cfg := config.Load()

	// Connect to database
	db, err := gorm.Open(postgres.Open(cfg.Database.DSN()), &gorm.Config{})
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	// Auto migrate
	if err := db.AutoMigrate(
		&models.User{},
		&models.Meeting{},
		&models.Participant{},
		&models.Alert{},
		&models.MeetingSummary{},
		&models.VideoRecording{},
		&models.DetectionTimeline{},
	); err != nil {
		log.Fatalf("Failed to migrate database: %v", err)
	}

	// Initialize JWT manager
	jwtManager := auth.NewJWTManager(cfg.JWT.Secret, cfg.JWT.ExpirationHours)

	// Initialize WebSocket hub
	wsHub := ws.NewHub()
	go wsHub.Run()

	// Initialize Redis service
	redisPort, _ := strconv.Atoi(cfg.Redis.Port)
	redisService, err := services.NewRedisService(cfg.Redis.Host, redisPort, cfg.Redis.Password, cfg.Redis.DB)
	if err != nil {
		log.Printf("Warning: Redis connection failed: %v", err)
	}

	// Initialize handlers
	authHandler := handlers.NewAuthHandler(db, jwtManager)
	meetingHandler := handlers.NewMeetingHandler(db)
	analyticsHandler := handlers.NewAnalyticsHandler(db)
	wsHandler := ws.NewHandler(wsHub)

	// Track last save time per meeting for sampling
	lastSaveTime := make(map[string]time.Time)
	saveMutex := &sync.Mutex{}

	// Start Redis subscriber to broadcast attention results to WebSocket
	if redisService != nil {
		redisService.StartAttentionSubscriber(func(meetingID string, result []byte) {
			meetingUUID, err := uuid.Parse(meetingID)
			if err != nil {
				log.Printf("Invalid meeting ID from Redis: %s", meetingID)
				return
			}

			// Pipeline sends an array of face results
			var facesArray []map[string]interface{}
			if err := json.Unmarshal(result, &facesArray); err != nil {
				log.Printf("Failed to unmarshal attention result: %v", err)
				return
			}

			// Wrap in object for WebSocket broadcast
			attentionData := map[string]interface{}{
				"faces": facesArray,
			}

			// Broadcast to WebSocket clients
			wsHandler.BroadcastAttentionResult(meetingUUID, attentionData)

			// Save to database with sampling (every 5 seconds)
			saveMutex.Lock()
			lastSave, exists := lastSaveTime[meetingID]
			shouldSave := !exists || time.Since(lastSave) >= 5*time.Second
			if shouldSave {
				lastSaveTime[meetingID] = time.Now()
			}
			saveMutex.Unlock()

			if shouldSave {
				go saveAttentionMetrics(db, meetingUUID, attentionData)
			}
		})
		log.Printf("📡 Redis subscriber started for attention results")
	}

	// Create Fiber app
	app := fiber.New(fiber.Config{
		AppName:      "Attention Detection API Gateway",
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
	})

	// Middleware
	app.Use(recover.New())
	app.Use(logger.New())
	app.Use(cors.New(cors.Config{
		AllowOrigins:     "*",
		AllowMethods:     "GET,POST,PUT,PATCH,DELETE,OPTIONS",
		AllowHeaders:     "Origin,Content-Type,Accept,Authorization",
		AllowCredentials: false,
	}))

	// Health check
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})

	// API v1 routes
	api := app.Group("/api/v1")

	// Auth routes (public)
	authGroup := api.Group("/auth")
	authGroup.Post("/register", authHandler.Register)
	authGroup.Post("/login", authHandler.Login)

	// Protected routes
	protected := api.Group("", middleware.AuthMiddleware(jwtManager))

	// User routes
	protected.Get("/me", authHandler.Me)
	protected.Put("/me", authHandler.UpdateProfile)
	protected.Put("/me/password", authHandler.ChangePassword)

	// Meeting routes
	meetings := protected.Group("/meetings")
	meetings.Post("/", meetingHandler.Create)
	meetings.Get("/", meetingHandler.List)
	meetings.Get("/:id", meetingHandler.Get)
	meetings.Put("/:id", meetingHandler.Update)
	meetings.Post("/:id/start", meetingHandler.Start)
	meetings.Post("/:id/end", meetingHandler.End)

	// Analytics routes
	analytics := protected.Group("/analytics")
	analytics.Get("/meetings/:id/metrics", analyticsHandler.GetMeetingMetrics)
	analytics.Get("/meetings/:id/participants", analyticsHandler.GetParticipantSummary)
	analytics.Get("/meetings/:id/alerts", analyticsHandler.GetMeetingAlerts)
	analytics.Get("/meetings/:id/summary", analyticsHandler.GetMeetingSummary)

	// Recording routes
	recordingHandler := handlers.NewRecordingHandler(db)
	recordings := protected.Group("/recordings")
	recordings.Post("/", recordingHandler.UploadRecording)
	recordings.Post("/start", recordingHandler.StartRecording)
	recordings.Post("/:id/chunk", recordingHandler.AppendChunk)
	recordings.Post("/:id/complete", recordingHandler.CompleteRecording)
	recordings.Get("/", recordingHandler.ListRecordings)
	recordings.Get("/:id", recordingHandler.GetRecording)
	recordings.Get("/:id/stream", recordingHandler.StreamVideo)
	recordings.Get("/:id/timeline", recordingHandler.GetTimeline)
	recordings.Get("/:id/alerts", recordingHandler.GetAlerts)
	recordings.Delete("/:id", recordingHandler.DeleteRecording)

	// Video Analysis routes
	videoAnalysisHandler := handlers.NewVideoAnalysisHandler(db)
	videoAnalysis := protected.Group("/video-analysis")
	videoAnalysis.Post("/upload", videoAnalysisHandler.Upload)
	videoAnalysis.Get("/", videoAnalysisHandler.List)
	videoAnalysis.Get("/:id", videoAnalysisHandler.GetByID)
	videoAnalysis.Delete("/:id", videoAnalysisHandler.Delete)
	// Internal endpoint for AI processor to update progress
	api.Put("/video-analysis/:id/progress", videoAnalysisHandler.UpdateProgress)

	// WebSocket routes
	app.Use("/ws", ws.UpgradeMiddleware())
	app.Get("/ws/meetings/:id", websocket.New(wsHandler.HandleConnection))

	// Start server
	addr := fmt.Sprintf(":%s", cfg.Server.Port)
	log.Printf("🚀 API Gateway starting on %s", addr)
	log.Fatal(app.Listen(addr))
}

// saveAttentionMetrics saves attention data to database
func saveAttentionMetrics(db *gorm.DB, meetingID uuid.UUID, data map[string]interface{}) {
	// Handle "faces" key (from Redis broadcast) or "participants" key
	var participants []interface{}
	var ok bool
	if participants, ok = data["faces"].([]interface{}); !ok {
		if participants, ok = data["participants"].([]interface{}); !ok {
			return
		}
	}

	now := time.Now()
	for _, p := range participants {
		participant, ok := p.(map[string]interface{})
		if !ok {
			continue
		}

		trackID, _ := participant["track_id"].(string)
		attentionScore, _ := participant["attention_score"].(float64)

		// Get gaze info
		var isLookingAway bool
		if gaze, ok := participant["gaze"].(map[string]interface{}); ok {
			if looking, ok := gaze["is_looking_at_camera"].(bool); ok {
				isLookingAway = !looking
			}
		}

		// Get blink info
		var isDrowsy bool
		var eyeOpenness float64 = 1.0
		if blink, ok := participant["blink"].(map[string]interface{}); ok {
			if drowsy, ok := blink["is_drowsy"].(bool); ok {
				isDrowsy = drowsy
			}
			if ear, ok := blink["avg_ear"].(float64); ok {
				eyeOpenness = ear
			}
		}

		// Get head pose score
		var headPoseScore float64 = 100
		if headPose, ok := participant["head_pose"].(map[string]interface{}); ok {
			yaw, _ := headPose["yaw"].(float64)
			pitch, _ := headPose["pitch"].(float64)
			// Simple head pose score based on yaw and pitch
			if yaw < 0 {
				yaw = -yaw
			}
			if pitch < 0 {
				pitch = -pitch
			}
			headPoseScore = 100 - (yaw+pitch)/2
			if headPoseScore < 0 {
				headPoseScore = 0
			}
		}

		// Generate a valid UUID from track_id
		participantUUID := uuid.NewSHA1(uuid.NameSpaceOID, []byte(meetingID.String()+trackID))

		metric := models.AttentionMetric{
			Time:           now,
			MeetingID:      meetingID,
			ParticipantID:  participantUUID,
			AttentionScore: attentionScore,
			GazeScore: func() float64 {
				if isLookingAway {
					return 50
				} else {
					return 100
				}
			}(),
			HeadPoseScore:    headPoseScore,
			EyeOpennessScore: eyeOpenness,
			IsLookingAway:    isLookingAway,
			IsDrowsy:         isDrowsy,
		}

		if err := db.Create(&metric).Error; err != nil {
			log.Printf("Failed to save attention metric: %v", err)
		}
	}
}
