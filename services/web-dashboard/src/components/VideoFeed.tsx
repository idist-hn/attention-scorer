'use client';

import React, { useEffect, useRef, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Camera, CameraOff, Loader2 } from 'lucide-react';
import { useVideoCapture } from '@/hooks/useVideoCapture';

// Detection result type from pipeline
interface DetectionResult {
  track_id: string;
  face?: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    confidence: number;
  };
  head_pose?: {
    yaw: number;
    pitch: number;
    roll: number;
  };
  gaze?: {
    is_looking_at_camera: boolean;
    gaze_angle: number;
  };
  blink?: {
    is_drowsy: boolean;
    avg_ear: number;
  };
  attention_score: number;
  alerts?: string[];
}

interface VideoFeedProps {
  onFrame?: (frameData: string) => void;
  frameInterval?: number;
  detections?: DetectionResult[];
  meetingId?: string;
  onStreamReady?: (stream: MediaStream | null) => void;
  autoStart?: boolean;
  onCompositeCanvasReady?: (canvas: HTMLCanvasElement | null) => void;
}

export interface VideoFeedRef {
  getCompositeCanvas: () => HTMLCanvasElement | null;
  getVideoElement: () => HTMLVideoElement | null;
}

export const VideoFeed = forwardRef<VideoFeedRef, VideoFeedProps>(function VideoFeed(
  { onFrame, frameInterval = 100, detections = [], meetingId, onStreamReady, autoStart = false, onCompositeCanvasReady },
  ref
) {
  const {
    videoRef,
    canvasRef,
    streamRef,
    isCapturing,
    error,
    devices,
    startCapture,
    stopCapture
  } = useVideoCapture({ onFrame, frameInterval });

  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const compositeCanvasRef = useRef<HTMLCanvasElement>(null);
  const autoStartedRef = useRef(false);
  const [isStarting, setIsStarting] = React.useState(false);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getCompositeCanvas: () => compositeCanvasRef.current,
    getVideoElement: () => videoRef.current,
  }));

  // Auto-start camera when component mounts
  useEffect(() => {
    if (autoStart && !isCapturing && !autoStartedRef.current && !error) {
      autoStartedRef.current = true;
      setIsStarting(true);
      startCapture().finally(() => setIsStarting(false));
    }
  }, [autoStart, isCapturing, error, startCapture]);

  // Notify parent when stream is ready
  useEffect(() => {
    if (onStreamReady) {
      onStreamReady(streamRef.current);
    }
  }, [isCapturing, onStreamReady, streamRef]);

  // Notify parent when composite canvas is ready
  useEffect(() => {
    if (onCompositeCanvasReady && compositeCanvasRef.current) {
      onCompositeCanvasReady(compositeCanvasRef.current);
    }
  }, [isCapturing, onCompositeCanvasReady]);

  // Draw detection overlays
  const drawDetections = useCallback(() => {
    const video = videoRef.current;
    const canvas = overlayCanvasRef.current;
    if (!video || !canvas || !isCapturing) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Match canvas size to video display size
    const rect = video.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Get video intrinsic dimensions for coordinate mapping
    const videoWidth = video.videoWidth || 640;
    const videoHeight = video.videoHeight || 480;
    const scaleX = canvas.width / videoWidth;
    const scaleY = canvas.height / videoHeight;

    detections.forEach((detection) => {
      if (!detection.face) return;

      const { x1, y1, x2, y2 } = detection.face;
      const score = detection.attention_score || 0;

      // Scale coordinates to canvas
      const scaledX1 = x1 * scaleX;
      const scaledY1 = y1 * scaleY;
      const scaledX2 = x2 * scaleX;
      const scaledY2 = y2 * scaleY;
      const width = scaledX2 - scaledX1;
      const height = scaledY2 - scaledY1;

      // Determine color based on attention score
      let color = '#22c55e'; // Green for high attention
      if (score < 50) {
        color = '#ef4444'; // Red for low attention
      } else if (score < 70) {
        color = '#f59e0b'; // Orange for medium attention
      }

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(scaledX1, scaledY1, width, height);

      // Draw corner accents
      const cornerLength = Math.min(width, height) * 0.2;
      ctx.lineWidth = 4;

      // Top-left corner
      ctx.beginPath();
      ctx.moveTo(scaledX1, scaledY1 + cornerLength);
      ctx.lineTo(scaledX1, scaledY1);
      ctx.lineTo(scaledX1 + cornerLength, scaledY1);
      ctx.stroke();

      // Top-right corner
      ctx.beginPath();
      ctx.moveTo(scaledX2 - cornerLength, scaledY1);
      ctx.lineTo(scaledX2, scaledY1);
      ctx.lineTo(scaledX2, scaledY1 + cornerLength);
      ctx.stroke();

      // Bottom-left corner
      ctx.beginPath();
      ctx.moveTo(scaledX1, scaledY2 - cornerLength);
      ctx.lineTo(scaledX1, scaledY2);
      ctx.lineTo(scaledX1 + cornerLength, scaledY2);
      ctx.stroke();

      // Bottom-right corner
      ctx.beginPath();
      ctx.moveTo(scaledX2 - cornerLength, scaledY2);
      ctx.lineTo(scaledX2, scaledY2);
      ctx.lineTo(scaledX2, scaledY2 - cornerLength);
      ctx.stroke();

      // Draw attention score label
      const labelText = `${Math.round(score)}%`;
      ctx.font = 'bold 16px Arial';
      const textMetrics = ctx.measureText(labelText);
      const labelPadding = 6;
      const labelWidth = textMetrics.width + labelPadding * 2;
      const labelHeight = 24;

      // Label background
      ctx.fillStyle = color;
      ctx.fillRect(scaledX1, scaledY1 - labelHeight - 4, labelWidth, labelHeight);

      // Label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(labelText, scaledX1 + labelPadding, scaledY1 - 10);

      // Draw status indicators
      let statusY = scaledY1 + height + 20;

      // Looking away indicator
      if (detection.gaze && !detection.gaze.is_looking_at_camera) {
        ctx.fillStyle = '#f59e0b';
        ctx.font = '12px Arial';
        ctx.fillText('👀 Looking Away', scaledX1, statusY);
        statusY += 16;
      }

      // Drowsy indicator
      if (detection.blink?.is_drowsy) {
        ctx.fillStyle = '#ef4444';
        ctx.font = '12px Arial';
        ctx.fillText('😴 Drowsy', scaledX1, statusY);
        statusY += 16;
      }

      // Head pose indicator (if looking too far away)
      if (detection.head_pose && Math.abs(detection.head_pose.yaw) > 30) {
        ctx.fillStyle = '#f59e0b';
        ctx.font = '12px Arial';
        const direction = detection.head_pose.yaw > 0 ? 'Right' : 'Left';
        ctx.fillText(`↪ Turned ${direction}`, scaledX1, statusY);
      }
    });

    // Also draw to composite canvas for recording (video + overlay combined)
    updateCompositeCanvas();
  }, [detections, isCapturing, videoRef]);

  // Update composite canvas (video + detections combined) for recording
  const updateCompositeCanvas = useCallback(() => {
    const video = videoRef.current;
    const overlay = overlayCanvasRef.current;
    const composite = compositeCanvasRef.current;
    if (!video || !overlay || !composite || !isCapturing) return;

    const ctx = composite.getContext('2d');
    if (!ctx) return;

    // Use video's natural dimensions
    const videoWidth = video.videoWidth || 640;
    const videoHeight = video.videoHeight || 480;
    composite.width = videoWidth;
    composite.height = videoHeight;

    // Draw video frame
    ctx.drawImage(video, 0, 0, videoWidth, videoHeight);

    // Draw overlay on top (scaled from display size to video size)
    if (overlay.width > 0 && overlay.height > 0) {
      ctx.drawImage(overlay, 0, 0, videoWidth, videoHeight);
    }
  }, [isCapturing, videoRef]);

  // Redraw when detections change
  useEffect(() => {
    drawDetections();
  }, [drawDetections]);

  // Redraw on resize
  useEffect(() => {
    const handleResize = () => drawDetections();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [drawDetections]);

  // Continuously update composite canvas for recording at 30fps
  useEffect(() => {
    if (!isCapturing) return;

    let animationId: number;
    const updateLoop = () => {
      updateCompositeCanvas();
      animationId = requestAnimationFrame(updateLoop);
    };
    animationId = requestAnimationFrame(updateLoop);

    return () => cancelAnimationFrame(animationId);
  }, [isCapturing, updateCompositeCanvas]);

  return (
    <div className="relative bg-gray-900 rounded-xl overflow-hidden shadow-lg">
      {/* Video element */}
      <video
        ref={videoRef}
        className="w-full aspect-video object-cover"
        autoPlay
        playsInline
        muted
      />

      {/* Detection overlay canvas */}
      <canvas
        ref={overlayCanvasRef}
        className="absolute inset-0 pointer-events-none"
        style={{ width: '100%', height: '100%' }}
      />

      {/* Hidden canvas for frame capture */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Hidden composite canvas for recording (video + overlay) */}
      <canvas ref={compositeCanvasRef} className="hidden" />

      {/* Overlay when starting camera */}
      {isStarting && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-800/90 text-white">
          <Loader2 className="w-10 h-10 mb-3 text-blue-400 animate-spin" />
          <p className="text-gray-300 text-sm">Starting camera...</p>
        </div>
      )}

      {/* Overlay when not capturing */}
      {!isCapturing && !isStarting && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-800 text-white">
          <CameraOff className="w-12 h-12 mb-4 text-gray-400" />
          <p className="text-gray-400 mb-4">Camera is off</p>
          <button
            onClick={() => {
              setIsStarting(true);
              startCapture().finally(() => setIsStarting(false));
            }}
            className="px-4 py-2 bg-blue-500 rounded-lg hover:bg-blue-600 flex items-center gap-2 transition-colors"
          >
            <Camera className="w-5 h-5" />
            Start Camera
          </button>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="absolute bottom-4 left-4 right-4 bg-red-500/90 backdrop-blur text-white p-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Camera controls */}
      {isCapturing && (
        <div className="absolute bottom-4 left-4 right-4 flex justify-between items-center">
          <select
            className="px-3 py-1.5 bg-black/60 backdrop-blur text-white rounded-lg text-sm border border-white/20"
            onChange={(e) => {
              stopCapture();
              startCapture(e.target.value);
            }}
          >
            {devices.map((device) => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label || `Camera ${device.deviceId.slice(0, 8)}`}
              </option>
            ))}
          </select>

          <button
            onClick={stopCapture}
            className="px-3 py-1.5 bg-red-500/80 backdrop-blur text-white rounded-lg text-sm hover:bg-red-600 transition-colors"
          >
            Stop
          </button>
        </div>
      )}

      {/* Live indicator */}
      {isCapturing && (
        <div className="absolute top-4 left-4 flex items-center gap-2 px-2.5 py-1 bg-black/60 backdrop-blur rounded-full">
          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span className="text-white text-xs font-medium">LIVE</span>
        </div>
      )}
    </div>
  );
});

export default VideoFeed;

