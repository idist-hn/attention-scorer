package services

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// RedisService handles Redis operations
type RedisService struct {
	client *redis.Client
	ctx    context.Context
}

// NewRedisService creates a new Redis service
func NewRedisService(host string, port int, password string, db int) (*RedisService, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%d", host, port),
		Password: password,
		DB:       db,
	})

	ctx := context.Background()

	// Test connection
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return &RedisService{
		client: client,
		ctx:    ctx,
	}, nil
}

// Set stores a value with expiration
func (r *RedisService) Set(key string, value interface{}, expiration time.Duration) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return r.client.Set(r.ctx, key, data, expiration).Err()
}

// Get retrieves a value
func (r *RedisService) Get(key string, dest interface{}) error {
	data, err := r.client.Get(r.ctx, key).Bytes()
	if err != nil {
		return err
	}
	return json.Unmarshal(data, dest)
}

// Delete removes a key
func (r *RedisService) Delete(key string) error {
	return r.client.Del(r.ctx, key).Err()
}

// Exists checks if key exists
func (r *RedisService) Exists(key string) bool {
	result, _ := r.client.Exists(r.ctx, key).Result()
	return result > 0
}

// Publish publishes a message to a channel
func (r *RedisService) Publish(channel string, message interface{}) error {
	data, err := json.Marshal(message)
	if err != nil {
		return err
	}
	return r.client.Publish(r.ctx, channel, data).Err()
}

// Subscribe subscribes to a channel
func (r *RedisService) Subscribe(channel string) *redis.PubSub {
	return r.client.Subscribe(r.ctx, channel)
}

// --- Cache helpers ---

// CacheAttentionMetrics caches attention metrics
func (r *RedisService) CacheAttentionMetrics(meetingID, participantID string, metrics interface{}) error {
	key := fmt.Sprintf("attention:%s:%s", meetingID, participantID)
	return r.Set(key, metrics, 5*time.Minute)
}

// GetCachedAttentionMetrics gets cached metrics
func (r *RedisService) GetCachedAttentionMetrics(meetingID, participantID string, dest interface{}) error {
	key := fmt.Sprintf("attention:%s:%s", meetingID, participantID)
	return r.Get(key, dest)
}

// CacheMeetingState caches meeting state
func (r *RedisService) CacheMeetingState(meetingID string, state interface{}) error {
	key := fmt.Sprintf("meeting:state:%s", meetingID)
	return r.Set(key, state, 1*time.Hour)
}

// --- Pub/Sub helpers ---

// PublishAttentionUpdate publishes attention update
func (r *RedisService) PublishAttentionUpdate(meetingID string, update interface{}) error {
	channel := fmt.Sprintf("meeting:%s:attention", meetingID)
	return r.Publish(channel, update)
}

// PublishAlert publishes an alert
func (r *RedisService) PublishAlert(meetingID string, alert interface{}) error {
	channel := fmt.Sprintf("meeting:%s:alerts", meetingID)
	return r.Publish(channel, alert)
}

// --- Queue helpers ---

// PushToQueue pushes a frame to processing queue
func (r *RedisService) PushToQueue(queueName string, data interface{}) error {
	jsonData, err := json.Marshal(data)
	if err != nil {
		return err
	}
	return r.client.RPush(r.ctx, queueName, jsonData).Err()
}

// PopFromQueue pops from processing queue
func (r *RedisService) PopFromQueue(queueName string, timeout time.Duration) (string, error) {
	result, err := r.client.BLPop(r.ctx, timeout, queueName).Result()
	if err != nil {
		return "", err
	}
	if len(result) > 1 {
		return result[1], nil
	}
	return "", nil
}

// Close closes the Redis connection
func (r *RedisService) Close() error {
	return r.client.Close()
}

// SubscribeToPattern subscribes to channels matching a pattern
func (r *RedisService) SubscribeToPattern(pattern string) *redis.PubSub {
	return r.client.PSubscribe(r.ctx, pattern)
}

// AttentionResultHandler is called when attention results are received
type AttentionResultHandler func(meetingID string, result []byte)

// StartAttentionSubscriber starts listening for attention results
func (r *RedisService) StartAttentionSubscriber(handler AttentionResultHandler) {
	pubsub := r.SubscribeToPattern("meeting:*:attention")
	ch := pubsub.Channel()

	go func() {
		for msg := range ch {
			// Extract meeting ID from channel name: meeting:{meetingID}:attention
			// Pattern: meeting:UUID:attention
			parts := splitChannel(msg.Channel)
			if len(parts) >= 2 {
				meetingID := parts[1]
				handler(meetingID, []byte(msg.Payload))
			}
		}
	}()
}

// splitChannel splits a Redis channel name
func splitChannel(channel string) []string {
	var parts []string
	var current string
	for _, c := range channel {
		if c == ':' {
			parts = append(parts, current)
			current = ""
		} else {
			current += string(c)
		}
	}
	if current != "" {
		parts = append(parts, current)
	}
	return parts
}
