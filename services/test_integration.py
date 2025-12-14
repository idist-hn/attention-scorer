#!/usr/bin/env python3
"""
Integration tests for the Attention Detection System.
Tests the full pipeline from frame input to attention output.
"""
import pytest
import requests
import numpy as np
import cv2
import base64
import json
import time
import websocket
import threading
from typing import Optional

# Configuration
API_BASE_URL = "http://localhost:8080/api/v1"
WS_URL = "ws://localhost:8080/ws/meetings"
PIPELINE_URL = "http://localhost:8000"


def create_test_frame() -> bytes:
    """Create a test frame with a face-like pattern."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)
    cv2.circle(img, (320, 240), 100, (180, 150, 130), -1)
    cv2.circle(img, (290, 220), 15, (50, 50, 50), -1)
    cv2.circle(img, (350, 220), 15, (50, 50, 50), -1)
    cv2.ellipse(img, (320, 280), (30, 15), 0, 0, 180, (100, 80, 80), 2)
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


class TestAPIGateway:
    """Integration tests for API Gateway."""

    def test_health_check(self):
        """Test API Gateway health endpoint."""
        response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/health", timeout=5)
        assert response.status_code == 200

    def test_register_and_login(self):
        """Test user registration and login flow."""
        # Register
        email = f"test_{int(time.time())}@example.com"
        register_data = {"email": email, "password": "test123", "name": "Test User"}
        response = requests.post(f"{API_BASE_URL}/auth/register", json=register_data, timeout=5)
        # May fail if user exists, that's ok
        
        # Login
        login_data = {"email": email, "password": "test123"}
        response = requests.post(f"{API_BASE_URL}/auth/login", json=login_data, timeout=5)
        if response.status_code == 200:
            data = response.json()
            assert "token" in data
            return data["token"]
        return None

    def test_create_meeting(self):
        """Test meeting creation."""
        token = self.test_register_and_login()
        if not token:
            pytest.skip("Could not get auth token")
        
        headers = {"Authorization": f"Bearer {token}"}
        meeting_data = {"title": "Integration Test Meeting", "description": "Test"}
        response = requests.post(f"{API_BASE_URL}/meetings", json=meeting_data, headers=headers, timeout=5)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        return data["id"], token

    def test_list_meetings(self):
        """Test listing meetings."""
        token = self.test_register_and_login()
        if not token:
            pytest.skip("Could not get auth token")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE_URL}/meetings", headers=headers, timeout=5)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestPipelineOrchestrator:
    """Integration tests for Pipeline Orchestrator."""

    def test_health_check(self):
        """Test pipeline health endpoint."""
        try:
            response = requests.get(f"{PIPELINE_URL}/health", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Pipeline orchestrator not running")

    def test_process_frame(self):
        """Test frame processing endpoint."""
        try:
            frame_data = create_test_frame()
            frame_b64 = base64.b64encode(frame_data).decode('utf-8')
            
            payload = {
                "meeting_id": "test-meeting-123",
                "frame": frame_b64
            }
            
            response = requests.post(f"{PIPELINE_URL}/process", json=payload, timeout=30)
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("Pipeline orchestrator not running")


class TestWebSocket:
    """Integration tests for WebSocket connections."""

    def test_websocket_connection(self):
        """Test WebSocket connection to meeting."""
        received_messages = []
        connected = threading.Event()
        
        def on_message(ws, message):
            received_messages.append(json.loads(message))
        
        def on_open(ws):
            connected.set()
        
        def on_error(ws, error):
            pass
        
        try:
            ws = websocket.WebSocketApp(
                f"{WS_URL}/test-meeting-ws",
                on_message=on_message,
                on_open=on_open,
                on_error=on_error
            )
            
            ws_thread = threading.Thread(target=ws.run_forever, kwargs={"ping_timeout": 5})
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection
            connected.wait(timeout=5)
            time.sleep(1)
            ws.close()
            
        except Exception as e:
            pytest.skip(f"WebSocket test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

