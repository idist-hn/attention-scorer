package middleware

import (
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
)

// RateLimiter configuration
type RateLimiterConfig struct {
	Max        int           // Maximum requests per window
	Window     time.Duration // Time window
	KeyFunc    func(*fiber.Ctx) string
	SkipFunc   func(*fiber.Ctx) bool
}

// RateLimiter middleware
type RateLimiter struct {
	config   RateLimiterConfig
	visitors map[string]*visitor
	mu       sync.RWMutex
}

type visitor struct {
	count    int
	lastSeen time.Time
}

// NewRateLimiter creates a new rate limiter
func NewRateLimiter(config RateLimiterConfig) *RateLimiter {
	if config.Max == 0 {
		config.Max = 100
	}
	if config.Window == 0 {
		config.Window = time.Minute
	}
	if config.KeyFunc == nil {
		config.KeyFunc = func(c *fiber.Ctx) string {
			return c.IP()
		}
	}

	rl := &RateLimiter{
		config:   config,
		visitors: make(map[string]*visitor),
	}

	// Cleanup goroutine
	go rl.cleanup()

	return rl
}

// Handler returns the fiber middleware handler
func (rl *RateLimiter) Handler() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Skip if configured
		if rl.config.SkipFunc != nil && rl.config.SkipFunc(c) {
			return c.Next()
		}

		key := rl.config.KeyFunc(c)

		rl.mu.Lock()
		v, exists := rl.visitors[key]
		if !exists || time.Since(v.lastSeen) > rl.config.Window {
			rl.visitors[key] = &visitor{count: 1, lastSeen: time.Now()}
			rl.mu.Unlock()
			return c.Next()
		}

		v.count++
		v.lastSeen = time.Now()
		count := v.count
		rl.mu.Unlock()

		if count > rl.config.Max {
			c.Set("X-RateLimit-Limit", string(rune(rl.config.Max)))
			c.Set("X-RateLimit-Remaining", "0")
			c.Set("Retry-After", string(rune(int(rl.config.Window.Seconds()))))
			
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error": "Too many requests",
				"retry_after_seconds": int(rl.config.Window.Seconds()),
			})
		}

		remaining := rl.config.Max - count
		c.Set("X-RateLimit-Limit", string(rune(rl.config.Max)))
		c.Set("X-RateLimit-Remaining", string(rune(remaining)))

		return c.Next()
	}
}

// cleanup removes old visitors
func (rl *RateLimiter) cleanup() {
	ticker := time.NewTicker(rl.config.Window)
	defer ticker.Stop()

	for range ticker.C {
		rl.mu.Lock()
		for key, v := range rl.visitors {
			if time.Since(v.lastSeen) > rl.config.Window*2 {
				delete(rl.visitors, key)
			}
		}
		rl.mu.Unlock()
	}
}

// DefaultRateLimiter returns a rate limiter with default config
func DefaultRateLimiter() fiber.Handler {
	return NewRateLimiter(RateLimiterConfig{
		Max:    100,
		Window: time.Minute,
	}).Handler()
}

// StrictRateLimiter returns a rate limiter for sensitive endpoints
func StrictRateLimiter() fiber.Handler {
	return NewRateLimiter(RateLimiterConfig{
		Max:    10,
		Window: time.Minute,
	}).Handler()
}

