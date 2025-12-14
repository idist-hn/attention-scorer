.PHONY: install dev test lint format clean demo

# Python environment
PYTHON := python3
PIP := pip3
VENV := .venv

# Install production dependencies
install:
	$(PIP) install -r requirements.txt

# Install development dependencies
dev:
	$(PIP) install -r requirements.txt
	$(PIP) install black isort mypy pytest pytest-cov

# Create virtual environment
venv:
	$(PYTHON) -m venv $(VENV)
	@echo "Run 'source $(VENV)/bin/activate' to activate"

# Run tests
test:
	pytest tests/ -v --cov=src --cov-report=term-missing

# Run linter
lint:
	mypy src/ --ignore-missing-imports
	black --check src/
	isort --check-only src/

# Format code
format:
	black src/ tests/
	isort src/ tests/

# Run demo
demo:
	$(PYTHON) demo.py

# Run demo with video
demo-video:
	$(PYTHON) demo.py --video $(VIDEO)

# Download YOLOv8 face model
download-model:
	@echo "Downloading YOLOv8 face model..."
	@mkdir -p models
	@if [ ! -f models/yolov8n-face.pt ]; then \
		wget -O models/yolov8n-face.pt https://github.com/akanametov/yolov8-face/releases/download/v0.0.0/yolov8n-face.pt; \
	fi
	@echo "Model downloaded to models/"

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/

# Docker
docker-build:
	docker build -t attention-ai-processor .

docker-run:
	docker run --gpus all -it --rm attention-ai-processor

