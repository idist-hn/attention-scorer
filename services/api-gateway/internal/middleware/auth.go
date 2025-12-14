package middleware

import (
	"strings"

	"github.com/attention-detection/api-gateway/pkg/auth"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

const (
	AuthHeader     = "Authorization"
	BearerPrefix   = "Bearer "
	UserIDKey      = "userID"
	UserEmailKey   = "userEmail"
)

// AuthMiddleware creates JWT authentication middleware
func AuthMiddleware(jwtManager *auth.JWTManager) fiber.Handler {
	return func(c *fiber.Ctx) error {
		authHeader := c.Get(AuthHeader)
		
		if authHeader == "" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "missing authorization header",
			})
		}

		if !strings.HasPrefix(authHeader, BearerPrefix) {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "invalid authorization header format",
			})
		}

		tokenString := strings.TrimPrefix(authHeader, BearerPrefix)
		
		claims, err := jwtManager.ValidateToken(tokenString)
		if err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "invalid or expired token",
			})
		}

		// Store user info in context
		c.Locals(UserIDKey, claims.UserID)
		c.Locals(UserEmailKey, claims.Email)

		return c.Next()
	}
}

// OptionalAuth allows requests without auth but adds user info if present
func OptionalAuth(jwtManager *auth.JWTManager) fiber.Handler {
	return func(c *fiber.Ctx) error {
		authHeader := c.Get(AuthHeader)
		
		if authHeader != "" && strings.HasPrefix(authHeader, BearerPrefix) {
			tokenString := strings.TrimPrefix(authHeader, BearerPrefix)
			if claims, err := jwtManager.ValidateToken(tokenString); err == nil {
				c.Locals(UserIDKey, claims.UserID)
				c.Locals(UserEmailKey, claims.Email)
			}
		}

		return c.Next()
	}
}

// GetUserID retrieves user ID from context
func GetUserID(c *fiber.Ctx) (uuid.UUID, bool) {
	userID, ok := c.Locals(UserIDKey).(uuid.UUID)
	return userID, ok
}

// GetUserEmail retrieves user email from context
func GetUserEmail(c *fiber.Ctx) (string, bool) {
	email, ok := c.Locals(UserEmailKey).(string)
	return email, ok
}

