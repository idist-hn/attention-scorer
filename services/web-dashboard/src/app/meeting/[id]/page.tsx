'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ArrowLeft, Users, Activity, Bell, Video } from 'lucide-react';
import Link from 'next/link';
import { VideoFeed, VideoFeedRef } from '@/components/VideoFeed';
import { AttentionScore } from '@/components/AttentionScore';
import { AttentionChart } from '@/components/AttentionChart';
import { ParticipantGrid } from '@/components/ParticipantGrid';
import { AlertPanel } from '@/components/AlertPanel';
import { VideoRecorder } from '@/components/VideoRecorder';
import websocket from '@/lib/websocket';

// Participant type
interface Participant {
  id: string;
  name: string;
  attention_score: number;
  is_looking_away: boolean;
  is_drowsy: boolean;
  is_active: boolean;
}

// Alert type
interface Alert {
  id: string;
  participant_name: string;
  alert_type: 'not_attentive' | 'looking_away' | 'drowsy';
  severity: 'info' | 'warning' | 'critical';
  message: string;
  created_at: string;
}

// Generate empty chart data
const generateEmptyChartData = () => {
  const data = [];
  const now = new Date();
  for (let i = 60; i >= 0; i--) {
    data.push({
      time: new Date(now.getTime() - i * 1000).toISOString(),
      attention: 0,
      gaze: 0,
      headPose: 0,
      eyeOpenness: 0,
    });
  }
  return data;
};

// Detection result type matching VideoFeed component
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

export default function MeetingPage({ params }: { params: { id: string } }) {
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [chartData, setChartData] = useState(generateEmptyChartData());
  const [avgAttention, setAvgAttention] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [detections, setDetections] = useState<DetectionResult[]>([]);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [currentDetectionData, setCurrentDetectionData] = useState<{ faces: any[]; avgAttention: number } | null>(null);
  const [compositeCanvas, setCompositeCanvas] = useState<HTMLCanvasElement | null>(null);

  const videoFeedRef = useRef<VideoFeedRef>(null);

  // Track alert cooldowns to avoid spamming
  const alertCooldowns = useRef<Record<string, number>>({});

  // Calculate average attention
  useEffect(() => {
    if (participants.length === 0) {
      setAvgAttention(0);
      return;
    }
    const avg = participants.reduce((sum, p) => sum + p.attention_score, 0) / participants.length;
    setAvgAttention(avg);
  }, [participants]);

  // WebSocket connection
  useEffect(() => {
    websocket.connect(params.id)
      .then(() => setIsConnected(true))
      .catch(() => setIsConnected(false));

    const unsubAttention = websocket.on('attention', (rawData) => {
      console.log('Received attention data:', rawData);

      // Handle both {faces: [...]} and direct array format
      const data = rawData?.faces || (Array.isArray(rawData) ? rawData : []);

      // Data is an array of participant results from pipeline
      if (Array.isArray(data) && data.length > 0) {
        const now = Date.now();
        const newAlerts: Alert[] = [];

        // Update participants from detection data
        setParticipants((prev) => {
          const updated: Participant[] = [];

          data.forEach((result: any, index: number) => {
            const trackId = result.track_id || String(index);
            const attentionScore = result.attention_score || 0;

            // Determine states from metrics
            const isLookingAway = result.gaze?.is_looking_at_camera === false ||
              (result.head_pose?.yaw && Math.abs(result.head_pose.yaw) > 30);
            const isDrowsy = result.blink?.is_drowsy === true;

            // Find existing participant to preserve name
            const existing = prev.find(p => p.id === trackId);
            const participantName = existing?.name || `Person ${index + 1}`;

            updated.push({
              id: trackId,
              name: participantName,
              attention_score: Math.round(attentionScore),
              is_looking_away: isLookingAway,
              is_drowsy: isDrowsy,
              is_active: true
            });

            // Generate alerts with cooldown (5 seconds between same alert type)
            const cooldownKey = `${trackId}-`;

            // Drowsy alert (critical)
            if (isDrowsy) {
              const key = cooldownKey + 'drowsy';
              if (!alertCooldowns.current[key] || now - alertCooldowns.current[key] > 5000) {
                alertCooldowns.current[key] = now;
                newAlerts.push({
                  id: `alert-${now}-${trackId}-drowsy`,
                  participant_name: participantName,
                  alert_type: 'drowsy',
                  severity: 'critical',
                  message: 'Appears drowsy - eyes closing frequently',
                  created_at: new Date().toISOString()
                });
              }
            }

            // Looking away alert (warning)
            if (isLookingAway) {
              const key = cooldownKey + 'looking_away';
              if (!alertCooldowns.current[key] || now - alertCooldowns.current[key] > 5000) {
                alertCooldowns.current[key] = now;
                newAlerts.push({
                  id: `alert-${now}-${trackId}-looking_away`,
                  participant_name: participantName,
                  alert_type: 'looking_away',
                  severity: 'warning',
                  message: 'Looking away from screen',
                  created_at: new Date().toISOString()
                });
              }
            }

            // Low attention alert (info)
            if (attentionScore < 40 && !isDrowsy && !isLookingAway) {
              const key = cooldownKey + 'low_attention';
              if (!alertCooldowns.current[key] || now - alertCooldowns.current[key] > 10000) {
                alertCooldowns.current[key] = now;
                newAlerts.push({
                  id: `alert-${now}-${trackId}-low_attention`,
                  participant_name: participantName,
                  alert_type: 'not_attentive',
                  severity: 'info',
                  message: `Low attention score: ${Math.round(attentionScore)}%`,
                  created_at: new Date().toISOString()
                });
              }
            }
          });

          return updated;
        });

        // Add new alerts (keep last 10)
        if (newAlerts.length > 0) {
          setAlerts((prev) => [...newAlerts, ...prev].slice(0, 10));
        }

        // Update chart with real attention data
        const avgScore = data.reduce((sum: number, r: any) => sum + (r.attention_score || 0), 0) / data.length;
        const gazeScore = data[0]?.gaze?.is_looking_at_camera ? 100 : 50;
        const headPoseScore = data[0]?.head_pose ? Math.max(0, 100 - Math.abs(data[0].head_pose.yaw) * 2) : 0;
        const eyeOpenness = data[0]?.blink?.avg_ear ? Math.min(100, data[0].blink.avg_ear * 300) : 0;

        setChartData((prev) => {
          const newData = [...prev.slice(1), {
            time: new Date().toISOString(),
            attention: avgScore,
            gaze: gazeScore,
            headPose: headPoseScore,
            eyeOpenness: eyeOpenness,
          }];
          return newData;
        });

        // Update detections for video overlay
        setDetections(data as DetectionResult[]);

        // Update current detection data for video recording timeline
        setCurrentDetectionData({ faces: data, avgAttention: avgScore });
      }
    });

    const unsubAlert = websocket.on('alert', (data) => {
      setAlerts((prev) => [data, ...prev].slice(0, 10));
    });

    return () => {
      unsubAttention();
      unsubAlert();
      websocket.disconnect();
    };
  }, [params.id]);



  const handleFrame = useCallback((frameData: string) => {
    if (websocket.isConnected) {
      websocket.sendFrame(frameData);
    }
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">Meeting Room</h1>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                {isConnected ? 'Connected' : 'Disconnected'}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
              <Users className="w-5 h-5" />
              <span>{participants.length}</span>
            </div>
            <AttentionScore score={avgAttention} size="sm" showLabel={false} />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Video, Recorder and Chart */}
          <div className="lg:col-span-2 space-y-4">
            <VideoFeed
              ref={videoFeedRef}
              onFrame={handleFrame}
              frameInterval={100}
              detections={detections}
              meetingId={params.id}
              onStreamReady={setVideoStream}
              autoStart={true}
              onCompositeCanvasReady={setCompositeCanvas}
            />

            {/* Video Recorder */}
            <VideoRecorder
              stream={videoStream}
              meetingId={params.id}
              currentDetection={currentDetectionData}
              compositeCanvas={compositeCanvas}
              autoRecord={true}
              alerts={alerts}
            />

            <AttentionChart data={chartData} showDetails height={250} />
          </div>

          {/* Right column - Participants and Alerts */}
          <div className="space-y-4">
            <AlertPanel alerts={alerts} onDismiss={(id) => setAlerts((prev) => prev.filter((a) => a.id !== id))} />
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-gray-400" />
                  <h3 className="font-semibold text-gray-900 dark:text-white">Participants</h3>
                  <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
                    {participants.length}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs text-gray-500">Live</span>
                </div>
              </div>
              <div className="p-3 max-h-96 overflow-y-auto">
                <ParticipantGrid participants={participants} />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

