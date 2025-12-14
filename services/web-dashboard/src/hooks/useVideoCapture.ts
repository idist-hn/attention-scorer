'use client';

import { useRef, useState, useCallback, useEffect } from 'react';

interface UseVideoCaptureOptions {
  onFrame?: (frameData: string) => void;
  frameInterval?: number; // ms between frames
}

export function useVideoCapture(options: UseVideoCaptureOptions = {}) {
  const { onFrame, frameInterval = 100 } = options;
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);

  // Get available cameras
  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then((allDevices) => {
      setDevices(allDevices.filter((d) => d.kind === 'videoinput'));
    });
  }, []);

  const startCapture = useCallback(async (deviceId?: string) => {
    try {
      const constraints: MediaStreamConstraints = {
        video: deviceId
          ? { deviceId: { exact: deviceId }, width: 640, height: 480 }
          : { facingMode: 'user', width: 640, height: 480 },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setIsCapturing(true);
      setError(null);

      // Start frame capture interval
      if (onFrame && canvasRef.current && videoRef.current) {
        intervalRef.current = setInterval(() => {
          captureFrame();
        }, frameInterval);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to access camera');
      setIsCapturing(false);
    }
  }, [onFrame, frameInterval]);

  const captureFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !onFrame) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (!ctx) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    // Convert to base64 JPEG and strip data URL prefix
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
    const frameData = dataUrl.replace(/^data:image\/\w+;base64,/, '');
    onFrame(frameData);
  }, [onFrame]);

  const stopCapture = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsCapturing(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCapture();
    };
  }, [stopCapture]);

  return {
    videoRef,
    canvasRef,
    streamRef,
    isCapturing,
    error,
    devices,
    startCapture,
    stopCapture,
    captureFrame,
  };
}

export default useVideoCapture;

