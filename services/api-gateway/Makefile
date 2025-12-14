.PHONY: build run test clean deps docker

# Variables
APP_NAME=api-gateway
MAIN_PATH=./cmd/main.go
DOCKER_IMAGE=attention-detection/api-gateway

# Go commands
build:
	@echo "Building $(APP_NAME)..."
	go build -o bin/$(APP_NAME) $(MAIN_PATH)

run:
	@echo "Running $(APP_NAME)..."
	go run $(MAIN_PATH)

test:
	@echo "Running tests..."
	go test -v ./...

test-coverage:
	@echo "Running tests with coverage..."
	go test -v -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html

clean:
	@echo "Cleaning..."
	rm -rf bin/
	rm -f coverage.out coverage.html

deps:
	@echo "Installing dependencies..."
	go mod download
	go mod tidy

# Database
migrate:
	@echo "Running migrations..."
	go run $(MAIN_PATH) migrate

# Docker
docker-build:
	@echo "Building Docker image..."
	docker build -t $(DOCKER_IMAGE):latest .

docker-run:
	@echo "Running Docker container..."
	docker run -p 8080:8080 --env-file .env $(DOCKER_IMAGE):latest

# Development
dev:
	@echo "Starting development server with hot reload..."
	which air > /dev/null || go install github.com/air-verse/air@latest
	air

# Linting
lint:
	@echo "Running linter..."
	which golangci-lint > /dev/null || go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	golangci-lint run

# Generate
generate:
	@echo "Generating code..."
	go generate ./...

# Help
help:
	@echo "Available commands:"
	@echo "  make build          - Build the application"
	@echo "  make run            - Run the application"
	@echo "  make test           - Run tests"
	@echo "  make test-coverage  - Run tests with coverage"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make deps           - Install dependencies"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run Docker container"
	@echo "  make dev            - Start development server with hot reload"
	@echo "  make lint           - Run linter"

