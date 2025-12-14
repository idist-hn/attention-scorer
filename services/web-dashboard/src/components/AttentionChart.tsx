'use client';

import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { format } from 'date-fns';
import { Activity, TrendingUp } from 'lucide-react';

interface DataPoint {
  time: string;
  attention: number;
  gaze?: number;
  headPose?: number;
  eyeOpenness?: number;
}

interface AttentionChartProps {
  data: DataPoint[];
  showDetails?: boolean;
  height?: number;
}

export function AttentionChart({ data, showDetails = false, height = 250 }: AttentionChartProps) {
  const formatTime = (time: string) => {
    try {
      return format(new Date(time), 'HH:mm:ss');
    } catch {
      return time;
    }
  };

  // Calculate stats
  const avgAttention = data.length > 0
    ? Math.round(data.reduce((sum, d) => sum + d.attention, 0) / data.length)
    : 0;
  const maxAttention = data.length > 0 ? Math.round(Math.max(...data.map(d => d.attention))) : 0;
  const minAttention = data.length > 0 ? Math.round(Math.min(...data.map(d => d.attention))) : 0;

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-900 text-white px-3 py-2 rounded-lg shadow-lg border border-gray-700">
          <p className="text-xs text-gray-400 mb-1">{formatTime(label)}</p>
          <div className="space-y-1">
            {payload.map((entry: any, index: number) => (
              <div key={index} className="flex items-center gap-2">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-xs">{entry.name}:</span>
                <span className="text-xs font-semibold">{entry.value?.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  };

  if (data.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
          <Activity className="w-4 h-4 text-gray-400" />
          <h3 className="font-semibold text-gray-900 dark:text-white">Attention Timeline</h3>
        </div>
        <div className="p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center mx-auto mb-3">
            <TrendingUp className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">No data yet</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Start your camera to see attention metrics
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
      {/* Header with stats */}
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-gray-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Attention Timeline</h3>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <p className="text-[10px] uppercase text-gray-500 dark:text-gray-400">Avg</p>
              <p className={`text-sm font-bold ${avgAttention >= 70 ? 'text-green-500' : avgAttention >= 40 ? 'text-amber-500' : 'text-red-500'}`}>
                {avgAttention}%
              </p>
            </div>
            <div className="text-center">
              <p className="text-[10px] uppercase text-gray-500 dark:text-gray-400">High</p>
              <p className="text-sm font-bold text-green-500">{maxAttention}%</p>
            </div>
            <div className="text-center">
              <p className="text-[10px] uppercase text-gray-500 dark:text-gray-400">Low</p>
              <p className="text-sm font-bold text-red-500">{minAttention}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="p-4">
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="attentionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22C55E" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#22C55E" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gazeGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" strokeOpacity={0.5} vertical={false} />
            <XAxis
              dataKey="time"
              tickFormatter={formatTime}
              stroke="#9CA3AF"
              fontSize={10}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
              stroke="#9CA3AF"
              fontSize={10}
              tickFormatter={(v) => `${v}%`}
              tickLine={false}
              axisLine={false}
              ticks={[0, 25, 50, 75, 100]}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Reference lines for thresholds */}
            <ReferenceLine y={70} stroke="#22C55E" strokeDasharray="3 3" strokeOpacity={0.5} />
            <ReferenceLine y={40} stroke="#F59E0B" strokeDasharray="3 3" strokeOpacity={0.5} />

            {showDetails && (
              <>
                <Area
                  type="monotone"
                  dataKey="gaze"
                  name="Gaze"
                  stroke="#3B82F6"
                  strokeWidth={1}
                  fill="url(#gazeGradient)"
                  strokeDasharray="3 3"
                />
                <Area
                  type="monotone"
                  dataKey="headPose"
                  name="Head Pose"
                  stroke="#F59E0B"
                  strokeWidth={1}
                  fill="transparent"
                  strokeDasharray="3 3"
                />
              </>
            )}

            <Area
              type="monotone"
              dataKey="attention"
              name="Attention"
              stroke="#22C55E"
              strokeWidth={2}
              fill="url(#attentionGradient)"
              activeDot={{ r: 4, strokeWidth: 2, fill: '#fff', stroke: '#22C55E' }}
            />
          </AreaChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="flex items-center justify-center gap-6 mt-2">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-green-500 rounded" />
            <span className="text-xs text-gray-500 dark:text-gray-400">Attention</span>
          </div>
          {showDetails && (
            <>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-0.5 bg-blue-500 rounded" style={{ opacity: 0.7 }} />
                <span className="text-xs text-gray-500 dark:text-gray-400">Gaze</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-0.5 bg-amber-500 rounded" style={{ opacity: 0.7 }} />
                <span className="text-xs text-gray-500 dark:text-gray-400">Head Pose</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AttentionChart;

