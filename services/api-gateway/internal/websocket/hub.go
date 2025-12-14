package websocket

import (
	"encoding/json"
	"log"
	"sync"

	"github.com/gofiber/contrib/websocket"
	"github.com/google/uuid"
)

// Message types
const (
	MessageTypeFrame         = "frame"
	MessageTypeAttention     = "attention"
	MessageTypeAlert         = "alert"
	MessageTypeParticipant   = "participant"
	MessageTypeMeetingStatus = "meeting_status"
)

// Message represents a WebSocket message
type Message struct {
	Type      string      `json:"type"`
	MeetingID string      `json:"meeting_id,omitempty"`
	Data      interface{} `json:"data"`
}

// Client represents a WebSocket client
type Client struct {
	ID        uuid.UUID
	UserID    uuid.UUID
	MeetingID uuid.UUID
	Conn      *websocket.Conn
	Send      chan []byte
}

// Room represents a meeting room with multiple clients
type Room struct {
	ID      uuid.UUID
	Clients map[uuid.UUID]*Client
	mu      sync.RWMutex
}

// Hub manages WebSocket connections
type Hub struct {
	rooms      map[uuid.UUID]*Room
	register   chan *Client
	unregister chan *Client
	broadcast  chan *RoomMessage
	mu         sync.RWMutex
}

type RoomMessage struct {
	RoomID  uuid.UUID
	Message []byte
}

// NewHub creates a new WebSocket hub
func NewHub() *Hub {
	return &Hub{
		rooms:      make(map[uuid.UUID]*Room),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		broadcast:  make(chan *RoomMessage, 256),
	}
}

// Run starts the hub's main loop
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.addClient(client)
		case client := <-h.unregister:
			h.removeClient(client)
		case msg := <-h.broadcast:
			h.broadcastToRoom(msg)
		}
	}
}

func (h *Hub) addClient(client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()

	room, exists := h.rooms[client.MeetingID]
	if !exists {
		room = &Room{
			ID:      client.MeetingID,
			Clients: make(map[uuid.UUID]*Client),
		}
		h.rooms[client.MeetingID] = room
	}

	room.mu.Lock()
	room.Clients[client.ID] = client
	room.mu.Unlock()
}

func (h *Hub) removeClient(client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if room, exists := h.rooms[client.MeetingID]; exists {
		room.mu.Lock()
		delete(room.Clients, client.ID)
		close(client.Send)
		room.mu.Unlock()

		if len(room.Clients) == 0 {
			delete(h.rooms, client.MeetingID)
		}
	}
}

func (h *Hub) broadcastToRoom(msg *RoomMessage) {
	h.mu.RLock()
	room, exists := h.rooms[msg.RoomID]
	h.mu.RUnlock()

	if !exists {
		log.Printf("⚠️ Room %s does not exist, cannot broadcast", msg.RoomID)
		return
	}

	room.mu.RLock()
	defer room.mu.RUnlock()

	clientCount := len(room.Clients)
	log.Printf("📤 Broadcasting to room %s with %d clients", msg.RoomID, clientCount)

	for _, client := range room.Clients {
		select {
		case client.Send <- msg.Message:
			log.Printf("✅ Sent message to client %s", client.ID)
		default:
			log.Printf("⚠️ Client %s buffer full, skipping", client.ID)
		}
	}
}

// Register adds a client to the hub
func (h *Hub) Register(client *Client) {
	h.register <- client
}

// Unregister removes a client from the hub
func (h *Hub) Unregister(client *Client) {
	h.unregister <- client
}

// BroadcastToMeeting sends a message to all clients in a meeting
func (h *Hub) BroadcastToMeeting(meetingID uuid.UUID, msg Message) {
	data, err := json.Marshal(msg)
	if err != nil {
		return
	}

	h.broadcast <- &RoomMessage{
		RoomID:  meetingID,
		Message: data,
	}
}

// GetRoomClientCount returns the number of clients in a room
func (h *Hub) GetRoomClientCount(meetingID uuid.UUID) int {
	h.mu.RLock()
	defer h.mu.RUnlock()

	if room, exists := h.rooms[meetingID]; exists {
		room.mu.RLock()
		defer room.mu.RUnlock()
		return len(room.Clients)
	}
	return 0
}
