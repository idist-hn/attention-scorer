'use client';

import React, { useState, useEffect } from 'react';
import { ArrowLeft, FileVideo, Clock, Users, AlertTriangle, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { videoAnalysis, VideoAnalysis } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface AnalysisResults {
  duration: number;
  total_frames: number;
  analyzed_frames: number;
  avg_attention: number;
  min_attention: number;
  max_attention: number;
  total_alerts: number;
  timeline: Array<{ timestamp_ms: number; avg_attention: number; faces: any[] }>;
  alerts: Array<{ type: string; severity: string; timestamp_ms: number }>;
}

export default function AnalysisDetailPage({ params }: { params: { id: string } }) {
  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const res = await videoAnalysis.get(params.id);
        setAnalysis(res.data);
        if (res.data.results) {
          setResults(JSON.parse(res.data.results));
        }
      } catch (err) {
        console.error('Failed to fetch analysis:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalysis();
  }, [params.id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!analysis || !results) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-gray-500">Analysis not found or not completed</div>
      </div>
    );
  }

  const formatTime = (ms: number) => {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    return `${m}:${(s % 60).toString().padStart(2, '0')}`;
  };

  const chartData = results.timeline.map((t) => ({
    time: formatTime(t.timestamp_ms),
    attention: Math.round(t.avg_attention),
  }));

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/analyze" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <FileVideo className="w-6 h-6 text-blue-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Analysis Results</h1>
            <p className="text-sm text-gray-500">{analysis.filename}</p>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={<Clock />} label="Duration" value={formatTime(results.duration * 1000)} />
          <StatCard icon={<TrendingUp />} label="Avg Attention" value={`${Math.round(results.avg_attention)}%`} color="blue" />
          <StatCard icon={<Users />} label="Frames Analyzed" value={results.analyzed_frames.toString()} />
          <StatCard icon={<AlertTriangle />} label="Alerts" value={results.total_alerts.toString()} color="red" />
        </div>

        {/* Attention Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Attention Timeline</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
                <YAxis domain={[0, 100]} stroke="#9CA3AF" fontSize={12} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                  labelStyle={{ color: '#9CA3AF' }}
                />
                <Line type="monotone" dataKey="attention" stroke="#3B82F6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Summary */}
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Attention Summary</h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-500">Average</span>
                <span className="font-medium text-gray-900 dark:text-white">{Math.round(results.avg_attention)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Minimum</span>
                <span className="font-medium text-red-500">{Math.round(results.min_attention)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Maximum</span>
                <span className="font-medium text-green-500">{Math.round(results.max_attention)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Alerts ({results.total_alerts})</h2>
            {results.alerts.length === 0 ? (
              <p className="text-gray-500">No alerts detected</p>
            ) : (
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {results.alerts.slice(0, 10).map((alert, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${
                      alert.severity === 'critical' ? 'bg-red-500' : 'bg-yellow-500'
                    }`} />
                    <span className="text-gray-500">{formatTime(alert.timestamp_ms)}</span>
                    <span className="text-gray-900 dark:text-white">{alert.type}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color = 'gray'
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color?: string;
}) {
  const colorClasses = {
    gray: 'text-gray-500',
    blue: 'text-blue-500',
    red: 'text-red-500',
    green: 'text-green-500',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className={`w-8 h-8 ${colorClasses[color as keyof typeof colorClasses]} mb-2`}>
        {icon}
      </div>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

