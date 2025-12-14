.PHONY: all build run test clean docker-build docker-up docker-down

# Variables
PROJECT_NAME=attention-detection

# Default target
all: build

# Build all services
build:
	@echo "Building all services..."
	cd services/ai-processor && pip install -e .
	cd services/api-gateway && go build -o bin/api-gateway ./cmd/main.go
	cd services/web-dashboard && npm run build

# Run all services (development)
run-ai:
	@echo "Starting AI Processor..."
	cd services/ai-processor && python demo.py

run-api:
	@echo "Starting API Gateway..."
	cd services/api-gateway && go run ./cmd/main.go

run-web:
	@echo "Starting Web Dashboard..."
	cd services/web-dashboard && npm run dev

# Run tests
test:
	@echo "Running all tests..."
	cd services/ai-processor && python -m pytest tests/ -v
	cd services/api-gateway && go test -v ./...
	cd services/web-dashboard && npm run lint

test-ai:
	cd services/ai-processor && python -m pytest tests/ -v

test-api:
	cd services/api-gateway && go test -v ./...

# Docker commands
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-up:
	@echo "Starting all services..."
	docker-compose up -d

docker-down:
	@echo "Stopping all services..."
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-ps:
	docker-compose ps

# Database
db-migrate:
	@echo "Running database migrations..."
	docker-compose exec postgres psql -U postgres -d attention_db -f /docker-entrypoint-initdb.d/001_init.sql

db-shell:
	docker-compose exec postgres psql -U postgres -d attention_db

# Clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf services/api-gateway/bin
	rm -rf services/web-dashboard/.next
	rm -rf services/web-dashboard/node_modules
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

# Install dependencies
deps:
	@echo "Installing dependencies..."
	cd services/ai-processor && pip install -r requirements.txt
	cd services/api-gateway && go mod download
	cd services/web-dashboard && npm install

# Demo
demo:
	@echo "Running AI demo..."
	cd services/ai-processor && python run_demo.py

# Help
help:
	@echo "Available commands:"
	@echo "  make build        - Build all services"
	@echo "  make run-ai       - Run AI Processor demo"
	@echo "  make run-api      - Run API Gateway"
	@echo "  make run-web      - Run Web Dashboard (dev)"
	@echo "  make test         - Run all tests"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start all services (Docker)"
	@echo "  make docker-down  - Stop all services (Docker)"
	@echo "  make demo         - Run AI processor demo"
	@echo "  make deps         - Install all dependencies"
	@echo "  make clean        - Clean build artifacts"

