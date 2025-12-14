#!/usr/bin/env python3
"""
Setup script for Attention Detection AI Processor.
"""

import os
import urllib.request
from pathlib import Path


def download_yolov8_face_model():
    """Download YOLOv8 face detection model."""
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / "yolov8n-face.pt"
    
    if model_path.exists():
        print(f"Model already exists: {model_path}")
        return
    
    # YOLOv8-face model URL
    url = "https://github.com/akanametov/yolov8-face/releases/download/v0.0.0/yolov8n-face.pt"
    
    print(f"Downloading YOLOv8-face model from {url}...")
    
    try:
        urllib.request.urlretrieve(url, model_path)
        print(f"Model downloaded successfully: {model_path}")
    except Exception as e:
        print(f"Failed to download model: {e}")
        print("Please download manually from:")
        print(f"  {url}")
        print(f"And save to: {model_path}")


def create_env_file():
    """Create .env file from example if it doesn't exist."""
    env_file = Path(".env")
    example_file = Path(".env.example")
    
    if env_file.exists():
        print(".env file already exists")
        return
    
    if example_file.exists():
        import shutil
        shutil.copy(example_file, env_file)
        print(".env file created from .env.example")
    else:
        print("Warning: .env.example not found")


def check_gpu():
    """Check if GPU is available."""
    print("\nChecking GPU availability...")
    
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✓ CUDA is available")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            print(f"  CUDA Version: {torch.version.cuda}")
        else:
            print("✗ CUDA is not available, will use CPU")
    except ImportError:
        print("PyTorch not installed yet, cannot check GPU")


def check_dependencies():
    """Check if required packages are installed."""
    print("\nChecking dependencies...")
    
    required = [
        "mediapipe",
        "ultralytics",
        "cv2",
        "numpy",
        "pydantic",
        "loguru"
    ]
    
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ {pkg}")
            missing.append(pkg)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
    else:
        print("\nAll dependencies installed!")


def main():
    print("=" * 50)
    print("Attention Detection AI Processor Setup")
    print("=" * 50)
    
    # Create .env file
    create_env_file()
    
    # Download model
    download_yolov8_face_model()
    
    # Check GPU
    check_gpu()
    
    # Check dependencies
    check_dependencies()
    
    print("\n" + "=" * 50)
    print("Setup complete!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Download model: make download-model (if not already done)")
    print("3. Run demo: python demo.py")


if __name__ == "__main__":
    main()

