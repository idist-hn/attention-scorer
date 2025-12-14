'use client';

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { Circle, Square, Download, Play, Pause, Video, X, Loader2, Cloud, CloudOff, AlertTriangle } from 'lucide-react';
import { recordings as recordingsApi, ServerRecording } from '@/lib/api';

interface DetectionEntry {
  timestamp_ms: number;
  faces: any[];
  avg_attention: number;
}

interface AlertEntry {
  timestamp_ms: number;
  video_time_formatted: string;
  alert: {
    id: string;
    participant_name: string;
    alert_type: string;
    severity: string;
    message: string;
    created_at: string;
  };
}

interface Recording {
  id: string;
  blob?: Blob;
  url: string;
  duration: number;
  timestamp: number;
  timeline: DetectionEntry[];
  alerts: AlertEntry[];
  isLocal: boolean;  // true if not yet uploaded to server
  isUploading?: boolean;
  serverRecording?: ServerRecording;
}

interface Alert {
  id: string;
  participant_name: string;
  alert_type: string;
  severity: string;
  message: string;
  created_at: string;
}

interface VideoRecorderProps {
  stream: MediaStream | null;
  meetingId: string;
  currentDetection?: { faces: any[]; avgAttention: number } | null;
  compositeCanvas?: HTMLCanvasElement | null;
  autoRecord?: boolean;
  alerts?: Alert[];
}

export function VideoRecorder({ stream, meetingId, currentDetection, compositeCanvas, autoRecord = false, alerts = [] }: VideoRecorderProps) {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timelineRef = useRef<DetectionEntry[]>([]);
  const alertsRef = useRef<AlertEntry[]>([]);
  const processedAlertIds = useRef<Set<string>>(new Set());
  const startTimeRef = useRef<number>(0);
  const autoStartedRef = useRef(false);
  const currentRecordingIdRef = useRef<string | null>(null);

  const [isRecording, setIsRecording] = useState(false);
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [duration, setDuration] = useState(0);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const loadedRef = useRef(false);

  // Load recordings from server on mount
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    const loadRecordings = async () => {
      try {
        setIsLoading(true);
        const response = await recordingsApi.list(meetingId);
        const serverRecordings: Recording[] = response.data.map((sr) => {
          let alertsData: AlertEntry[] = [];
          if (sr.alerts_data) {
            try {
              alertsData = JSON.parse(sr.alerts_data);
            } catch {}
          }
          return {
            id: sr.id,
            url: recordingsApi.getStreamUrl(sr.id),
            duration: sr.duration_seconds,
            timestamp: new Date(sr.created_at).getTime(),
            timeline: [],
            alerts: alertsData,
            isLocal: false,
            serverRecording: sr,
          };
        });
        setRecordings(serverRecordings);
      } catch (error) {
        console.error('Failed to load recordings:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadRecordings();
  }, [meetingId]);

  // Update duration while recording
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setDuration(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  // Collect detection data during recording
  useEffect(() => {
    if (isRecording && currentDetection) {
      timelineRef.current.push({
        timestamp_ms: Date.now() - startTimeRef.current,
        faces: currentDetection.faces,
        avg_attention: currentDetection.avgAttention,
      });
    }
  }, [isRecording, currentDetection]);

  // Collect alerts during recording
  useEffect(() => {
    if (isRecording && alerts.length > 0) {
      alerts.forEach((alert) => {
        // Only add new alerts that haven't been processed
        if (!processedAlertIds.current.has(alert.id)) {
          processedAlertIds.current.add(alert.id);
          const timestamp_ms = Date.now() - startTimeRef.current;
          const seconds = Math.floor(timestamp_ms / 1000);
          const minutes = Math.floor(seconds / 60);
          const secs = seconds % 60;
          alertsRef.current.push({
            timestamp_ms,
            video_time_formatted: `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`,
            alert: {
              id: alert.id,
              participant_name: alert.participant_name,
              alert_type: alert.alert_type,
              severity: alert.severity,
              message: alert.message,
              created_at: alert.created_at,
            },
          });
        }
      });
    }
  }, [isRecording, alerts]);

  // Auto-start recording when stream is ready
  useEffect(() => {
    if (autoRecord && stream && !isRecording && !autoStartedRef.current) {
      autoStartedRef.current = true;
      // Small delay to ensure everything is initialized
      const timer = setTimeout(() => {
        startRecording();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [autoRecord, stream, isRecording]);

  const startRecording = useCallback(async () => {
    // Prefer composite canvas (video + overlay) if available
    let recordStream: MediaStream | null = null;

    if (compositeCanvas) {
      try {
        recordStream = compositeCanvas.captureStream(30); // 30 fps
      } catch (e) {
        console.warn('Failed to capture from composite canvas:', e);
      }
    }

    // Fallback to raw stream if composite not available
    if (!recordStream && stream) {
      recordStream = stream;
    }

    if (!recordStream) return;

    chunksRef.current = [];
    timelineRef.current = [];
    alertsRef.current = [];
    processedAlertIds.current = new Set();
    startTimeRef.current = Date.now();

    // Start recording session on server
    let serverRecordingId: string | null = null;
    try {
      const response = await recordingsApi.start(meetingId);
      serverRecordingId = response.data.id;
      currentRecordingIdRef.current = serverRecordingId;
      console.log('Started server recording:', serverRecordingId);
    } catch (error) {
      console.error('Failed to start server recording:', error);
      // Continue with local-only recording
    }

    const options = { mimeType: 'video/webm;codecs=vp9' };
    try {
      mediaRecorderRef.current = new MediaRecorder(recordStream, options);
    } catch {
      try {
        mediaRecorderRef.current = new MediaRecorder(recordStream, { mimeType: 'video/webm' });
      } catch {
        mediaRecorderRef.current = new MediaRecorder(recordStream);
      }
    }

    mediaRecorderRef.current.ondataavailable = async (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
        // Stream chunk to server if we have a server recording
        if (currentRecordingIdRef.current) {
          try {
            await recordingsApi.appendChunk(currentRecordingIdRef.current, e.data);
          } catch (error) {
            console.warn('Failed to upload chunk:', error);
          }
        }
      }
    };

    mediaRecorderRef.current.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: 'video/webm' });
      const url = URL.createObjectURL(blob);
      const recordingAlerts = [...alertsRef.current];
      const recordingTimeline = [...timelineRef.current];
      const actualDuration = Math.floor((Date.now() - startTimeRef.current) / 1000);
      const recordingId = currentRecordingIdRef.current || `local-${Date.now()}`;

      // Complete recording on server
      if (currentRecordingIdRef.current) {
        try {
          const response = await recordingsApi.complete(currentRecordingIdRef.current, {
            duration: actualDuration,
            alerts: recordingAlerts,
            timeline: recordingTimeline,
          });
          console.log('Completed server recording:', response.data.id);

          // Add to recordings list
          setRecordings(prev => [{
            id: response.data.id,
            blob,
            url,
            duration: actualDuration,
            timestamp: Date.now(),
            timeline: recordingTimeline,
            alerts: recordingAlerts,
            isLocal: false,
            serverRecording: response.data,
          }, ...prev]);
        } catch (error) {
          console.error('Failed to complete server recording:', error);
          // Save as local recording
          setRecordings(prev => [{
            id: recordingId,
            blob,
            url,
            duration: actualDuration,
            timestamp: Date.now(),
            timeline: recordingTimeline,
            alerts: recordingAlerts,
            isLocal: true,
          }, ...prev]);
        }
      } else {
        // Local-only recording
        setRecordings(prev => [{
          id: recordingId,
          blob,
          url,
          duration: actualDuration,
          timestamp: Date.now(),
          timeline: recordingTimeline,
          alerts: recordingAlerts,
          isLocal: true,
        }, ...prev]);
      }

      currentRecordingIdRef.current = null;
    };

    mediaRecorderRef.current.start(1000); // Capture every second
    setIsRecording(true);
    setDuration(0);
  }, [stream, compositeCanvas, meetingId]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  const downloadRecording = useCallback(async (recording: Recording) => {
    const date = new Date(recording.timestamp);
    const dateStr = date.toISOString().slice(0, 19).replace(/[T:]/g, '-');
    const baseFilename = `attention-${meetingId}-${dateStr}`;

    // Download video - for server recordings, need to fetch with auth
    if (recording.isLocal && recording.blob) {
      // Local recording - use blob URL
      const videoLink = document.createElement('a');
      videoLink.href = recording.url;
      videoLink.download = `${baseFilename}.webm`;
      videoLink.click();
    } else {
      // Server recording - fetch with auth token
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(recording.url, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const videoLink = document.createElement('a');
        videoLink.href = url;
        videoLink.download = `${baseFilename}.webm`;
        videoLink.click();
        URL.revokeObjectURL(url);
      } catch (error) {
        console.error('Failed to download video:', error);
      }
    }

    // Download metadata JSON with alerts if any alerts exist
    if (recording.alerts.length > 0) {
      const metadata = {
        meeting_id: meetingId,
        recording_id: recording.id,
        recorded_at: new Date(recording.timestamp).toISOString(),
        duration_seconds: recording.duration,
        alerts_summary: {
          total: recording.alerts.length,
          critical: recording.alerts.filter(a => a.alert?.severity === 'critical').length,
          warning: recording.alerts.filter(a => a.alert?.severity === 'warning').length,
          info: recording.alerts.filter(a => a.alert?.severity === 'info').length,
        },
        alerts: recording.alerts.map(a => ({
          video_time: a.video_time_formatted,
          timestamp_ms: a.timestamp_ms,
          participant: a.alert?.participant_name,
          type: a.alert?.alert_type,
          severity: a.alert?.severity,
          message: a.alert?.message,
        })),
      };

      const jsonBlob = new Blob([JSON.stringify(metadata, null, 2)], { type: 'application/json' });
      const jsonUrl = URL.createObjectURL(jsonBlob);
      const jsonLink = document.createElement('a');
      jsonLink.href = jsonUrl;
      jsonLink.download = `${baseFilename}-alerts.json`;

      // Delay to avoid browser blocking multiple downloads
      setTimeout(() => {
        jsonLink.click();
        URL.revokeObjectURL(jsonUrl);
      }, 500);
    }
  }, [meetingId]);

  const deleteRecording = useCallback(async (id: string) => {
    const recording = recordings.find(r => r.id === id);
    if (!recording) return;

    // Delete from server if not local
    if (!recording.isLocal) {
      try {
        await recordingsApi.delete(id);
      } catch (error) {
        console.error('Failed to delete recording from server:', error);
      }
    }

    // Revoke local URL if exists
    if (recording.blob) {
      URL.revokeObjectURL(recording.url);
    }

    setRecordings(prev => prev.filter(r => r.id !== id));
    if (playingId === id) {
      setPlayingId(null);
    }
  }, [recordings, playingId]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const formatTimestamp = (ts: number) => {
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      recordings.forEach(r => URL.revokeObjectURL(r.url));
    };
  }, []);

  return (
    <div className="space-y-3">
      {/* Recording controls */}
      <div className="flex items-center gap-2 bg-gray-800/80 backdrop-blur rounded-lg px-3 py-2">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={!stream && !compositeCanvas}
            className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white text-sm transition-colors"
          >
            <Circle className="w-3.5 h-3.5 fill-current" />
            Record
          </button>
        ) : (
          <>
            <div className="flex items-center gap-2 px-2 py-1 bg-red-500/20 rounded-lg">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              <span className="text-red-400 text-xs font-semibold">REC</span>
              <span className="text-white text-sm font-mono">{formatTime(duration)}</span>
            </div>
            <button
              onClick={stopRecording}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-600 hover:bg-gray-500 rounded-lg text-white text-sm transition-colors"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              Stop
            </button>
          </>
        )}

        {recordings.length > 0 && (
          <div className="flex items-center gap-1.5 ml-auto text-gray-400 text-xs">
            <Video className="w-3.5 h-3.5" />
            <span>{recordings.length} saved</span>
          </div>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="bg-gray-800/80 backdrop-blur rounded-lg p-4 flex items-center justify-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
          <span className="text-gray-400 text-sm">Loading recordings...</span>
        </div>
      )}

      {/* Recordings list */}
      {!isLoading && recordings.length > 0 && (
        <div className="bg-gray-800/80 backdrop-blur rounded-lg overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-700 flex items-center justify-between">
            <span className="text-white text-sm font-medium">Recordings</span>
            <span className="text-gray-400 text-xs">{recordings.length} videos</span>
          </div>
          <div className="max-h-48 overflow-y-auto divide-y divide-gray-700">
            {recordings.map((recording) => (
              <div key={recording.id} className="px-3 py-2 hover:bg-gray-700/50 transition-colors">
                <div className="flex items-center gap-3">
                  {/* Preview thumbnail or play button */}
                  <div className="relative w-16 h-10 bg-gray-900 rounded overflow-hidden flex-shrink-0">
                    {playingId === recording.id ? (
                      <video
                        src={recording.url}
                        className="w-full h-full object-cover"
                        autoPlay
                        loop
                        muted
                        onEnded={() => setPlayingId(null)}
                      />
                    ) : (
                      <button
                        onClick={() => setPlayingId(recording.id)}
                        className="absolute inset-0 flex items-center justify-center bg-black/50 hover:bg-black/30 transition-colors"
                      >
                        <Play className="w-4 h-4 text-white fill-current" />
                      </button>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-white text-sm font-medium truncate">
                        {formatTimestamp(recording.timestamp)}
                      </p>
                      {/* Upload status indicator */}
                      {recording.isUploading && (
                        <span className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold rounded bg-blue-500/20 text-blue-400">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Uploading
                        </span>
                      )}
                      {!recording.isLocal && !recording.isUploading && (
                        <span className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold rounded bg-green-500/20 text-green-400" title="Saved to server">
                          <Cloud className="w-3 h-3" />
                        </span>
                      )}
                      {recording.isLocal && !recording.isUploading && (
                        <span className="flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold rounded bg-amber-500/20 text-amber-400" title="Local only">
                          <CloudOff className="w-3 h-3" />
                        </span>
                      )}
                      {recording.alerts.length > 0 && (
                        <span className={`px-1.5 py-0.5 text-[10px] font-semibold rounded ${
                          recording.alerts.some(a => a.alert?.severity === 'critical')
                            ? 'bg-red-500 text-white'
                            : recording.alerts.some(a => a.alert?.severity === 'warning')
                            ? 'bg-amber-500 text-white'
                            : 'bg-blue-500 text-white'
                        }`}>
                          {recording.alerts.length} alert{recording.alerts.length > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    <p className="text-gray-400 text-xs">
                      {formatTime(recording.duration)}
                      {recording.blob && ` • ${(recording.blob.size / 1024 / 1024).toFixed(1)} MB`}
                      {recording.serverRecording && ` • ${(recording.serverRecording.file_size / 1024 / 1024).toFixed(1)} MB`}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5">
                    {playingId === recording.id && (
                      <button
                        onClick={() => setPlayingId(null)}
                        className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-600 rounded transition-colors"
                        title="Stop"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => downloadRecording(recording)}
                      className="p-1.5 text-blue-400 hover:text-blue-300 hover:bg-blue-500/20 rounded transition-colors"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => deleteRecording(recording.id)}
                      className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/20 rounded transition-colors"
                      title="Delete"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

