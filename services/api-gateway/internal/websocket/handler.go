package websocket

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

// Handler handles WebSocket connections
type Handler struct {
	hub                 *Hub
	pipelineURL         string
	httpClient          *http.Client
	frameProcessChannel chan FrameProcessRequest
}

// FrameProcessRequest for async processing
type FrameProcessRequest struct {
	Client    *Client
	FrameData string
	RequestID string
}

// NewHandler creates a new WebSocket handler
func NewHandler(hub *Hub) *Handler {
	pipelineURL := os.Getenv("PIPELINE_ORCHESTRATOR_URL")
	if pipelineURL == "" {
		pipelineURL = "http://pipeline-orchestrator:8051"
	}

	h := &Handler{
		hub:         hub,
		pipelineURL: pipelineURL,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		frameProcessChannel: make(chan FrameProcessRequest, 100),
	}

	// Start frame processing workers
	for i := 0; i < 5; i++ {
		go h.frameProcessWorker()
	}

	return h
}

// frameProcessWorker processes frames asynchronously
func (h *Handler) frameProcessWorker() {
	for req := range h.frameProcessChannel {
		h.processFrameAsync(req)
	}
}

// processFrameAsync sends frame to pipeline orchestrator
func (h *Handler) processFrameAsync(req FrameProcessRequest) {
	payload := map[string]string{
		"frame_data": req.FrameData,
		"meeting_id": req.Client.MeetingID.String(),
		"request_id": req.RequestID,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		log.Printf("Error marshaling frame request: %v", err)
		return
	}

	resp, err := h.httpClient.Post(
		h.pipelineURL+"/process",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		log.Printf("Error sending to pipeline: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("Pipeline returned status: %d", resp.StatusCode)
		return
	}

	// Results are published to Redis by pipeline, not returned here
	log.Printf("Frame processed for meeting %s", req.Client.MeetingID)
}

// UpgradeMiddleware checks if the request can be upgraded to WebSocket
func UpgradeMiddleware() fiber.Handler {
	return func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			c.Locals("allowed", true)
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	}
}

// HandleConnection handles a WebSocket connection
func (h *Handler) HandleConnection(c *websocket.Conn) {
	// Get meeting ID from params
	meetingIDStr := c.Params("id")
	meetingID, err := uuid.Parse(meetingIDStr)
	if err != nil {
		log.Printf("Invalid meeting ID: %s", meetingIDStr)
		c.Close()
		return
	}

	// Get user ID from query or locals
	userIDStr := c.Query("user_id")
	userID, _ := uuid.Parse(userIDStr)
	if userID == uuid.Nil {
		userID = uuid.New() // Generate anonymous ID
	}

	// Create client
	client := &Client{
		ID:        uuid.New(),
		UserID:    userID,
		MeetingID: meetingID,
		Conn:      c,
		Send:      make(chan []byte, 256),
	}

	// Register client
	h.hub.Register(client)

	// Notify room of new participant
	h.hub.BroadcastToMeeting(meetingID, Message{
		Type:      MessageTypeParticipant,
		MeetingID: meetingIDStr,
		Data: map[string]interface{}{
			"action":  "joined",
			"user_id": userID.String(),
		},
	})

	// Start goroutines for reading and writing
	go h.writePump(client)
	h.readPump(client)
}

// readPump handles incoming messages from the client
func (h *Handler) readPump(client *Client) {
	defer func() {
		h.hub.Unregister(client)

		// Notify room of participant leaving
		h.hub.BroadcastToMeeting(client.MeetingID, Message{
			Type:      MessageTypeParticipant,
			MeetingID: client.MeetingID.String(),
			Data: map[string]interface{}{
				"action":  "left",
				"user_id": client.UserID.String(),
			},
		})

		client.Conn.Close()
	}()

	for {
		_, message, err := client.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}

		// Parse incoming message
		var msg Message
		if err := json.Unmarshal(message, &msg); err != nil {
			continue
		}

		// Handle different message types
		switch msg.Type {
		case MessageTypeFrame:
			// Forward frame to AI processor (via Redis or gRPC)
			h.handleFrame(client, msg)
		default:
			// Broadcast to room
			h.hub.BroadcastToMeeting(client.MeetingID, msg)
		}
	}
}

// writePump sends messages to the client
func (h *Handler) writePump(client *Client) {
	defer client.Conn.Close()

	for message := range client.Send {
		if err := client.Conn.WriteMessage(websocket.TextMessage, message); err != nil {
			return
		}
	}
}

// handleFrame processes a video frame from a client
func (h *Handler) handleFrame(client *Client, msg Message) {
	// Extract frame data from message
	data, ok := msg.Data.(map[string]interface{})
	if !ok {
		log.Printf("Invalid frame data format")
		return
	}

	frameData, ok := data["frame"].(string)
	if !ok {
		log.Printf("Frame data not found in message")
		return
	}

	// Queue frame for async processing
	select {
	case h.frameProcessChannel <- FrameProcessRequest{
		Client:    client,
		FrameData: frameData,
		RequestID: uuid.New().String(),
	}:
		// Frame queued successfully
	default:
		log.Printf("Frame processing queue full, dropping frame")
	}
}

// BroadcastAttentionResult broadcasts attention results to a meeting
func (h *Handler) BroadcastAttentionResult(meetingID uuid.UUID, result interface{}) {
	h.hub.BroadcastToMeeting(meetingID, Message{
		Type:      MessageTypeAttention,
		MeetingID: meetingID.String(),
		Data:      result,
	})
}

// BroadcastAlert broadcasts an alert to a meeting
func (h *Handler) BroadcastAlert(meetingID uuid.UUID, alert interface{}) {
	h.hub.BroadcastToMeeting(meetingID, Message{
		Type:      MessageTypeAlert,
		MeetingID: meetingID.String(),
		Data:      alert,
	})
}
