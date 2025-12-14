'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, Calendar, TrendingUp, Users, AlertTriangle, Download } from 'lucide-react';
import { meetings as meetingsApi } from '@/lib/api';

interface MeetingSummary {
  id: string;
  title: string;
  date: string;
  duration_minutes: number;
  participant_count: number;
  avg_attention: number;
  total_alerts: number;
  status: string;
}

export default function AnalyticsPage() {
  const [meetings, setMeetings] = useState<MeetingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState('week');

  useEffect(() => {
    const fetchMeetings = async () => {
      setLoading(true);
      try {
        const response = await meetingsApi.list();
        const data = response.data || [];

        // Filter by period
        const now = new Date();
        const periodDays = selectedPeriod === 'week' ? 7 : selectedPeriod === 'month' ? 30 : 90;
        const cutoff = new Date(now.getTime() - periodDays * 24 * 60 * 60 * 1000);

        const filtered = data
          .filter((m: any) => new Date(m.CreatedAt || m.created_at) >= cutoff)
          .map((m: any) => ({
            id: m.ID || m.id,
            title: m.Title || m.title,
            date: new Date(m.CreatedAt || m.created_at).toLocaleDateString(),
            duration_minutes: m.StartTime && m.EndTime
              ? Math.round((new Date(m.EndTime).getTime() - new Date(m.StartTime).getTime()) / 60000)
              : 0,
            participant_count: m.Participants?.length || 0,
            avg_attention: 0, // Would come from analytics API
            total_alerts: 0,
            status: m.Status || m.status || 'scheduled'
          }));

        setMeetings(filtered);
      } catch (error) {
        console.error('Failed to fetch meetings:', error);
        setMeetings([]);
      } finally {
        setLoading(false);
      }
    };

    fetchMeetings();
  }, [selectedPeriod]);

  const handleExport = () => {
    const csv = [
      ['Meeting', 'Date', 'Duration (min)', 'Participants', 'Attention %', 'Alerts', 'Status'].join(','),
      ...meetings.map(m => [m.title, m.date, m.duration_minutes, m.participant_count, m.avg_attention, m.total_alerts, m.status].join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `meetings-${selectedPeriod}-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const stats = {
    totalMeetings: meetings.length,
    avgAttention: meetings.length ? Math.round(meetings.reduce((sum, m) => sum + m.avg_attention, 0) / meetings.length) : 0,
    totalParticipants: meetings.reduce((sum, m) => sum + m.participant_count, 0),
    totalAlerts: meetings.reduce((sum, m) => sum + m.total_alerts, 0),
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Analytics</h1>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600"
            >
              <option value="week">Last 7 days</option>
              <option value="month">Last 30 days</option>
              <option value="quarter">Last 90 days</option>
            </select>
            <button
              onClick={handleExport}
              disabled={meetings.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
            >
              <Download size={18} />
              Export CSV
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard icon={<Calendar />} label="Meetings" value={stats.totalMeetings} color="blue" />
          <StatCard icon={<TrendingUp />} label="Avg Attention" value={`${stats.avgAttention}%`} color="green" />
          <StatCard icon={<Users />} label="Participants" value={stats.totalParticipants} color="purple" />
          <StatCard icon={<AlertTriangle />} label="Alerts" value={stats.totalAlerts} color="red" />
        </div>

        {/* Meetings Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <div className="p-4 border-b dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Meeting History</h2>
          </div>
          
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-300">Meeting</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-300">Date</th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-300">Status</th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-300">Duration</th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-300">Participants</th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-500 dark:text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y dark:divide-gray-700">
                  {meetings.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        No meetings found in this period
                      </td>
                    </tr>
                  ) : meetings.map((meeting) => (
                    <tr key={meeting.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="px-4 py-3 text-gray-900 dark:text-white font-medium">{meeting.title}</td>
                      <td className="px-4 py-3 text-gray-500">{meeting.date}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          meeting.status === 'active' ? 'bg-green-100 text-green-700' :
                          meeting.status === 'ended' ? 'bg-gray-100 text-gray-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {meeting.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center text-gray-500">
                        {meeting.duration_minutes > 0 ? `${meeting.duration_minutes}m` : '-'}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-500">{meeting.participant_count}</td>
                      <td className="px-4 py-3 text-center">
                        <Link
                          href={`/meeting/${meeting.id}`}
                          className="text-blue-500 hover:text-blue-700 text-sm"
                        >
                          View Details
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string | number; color: string }) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    red: 'bg-red-100 text-red-600',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses[color as keyof typeof colorClasses]}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

