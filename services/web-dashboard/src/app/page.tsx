'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Video, Users, Activity, AlertTriangle, Plus, Play, Square, X, Film } from 'lucide-react';
import AdminLayout from '@/components/AdminLayout';
import { meetings as meetingsApi } from '@/lib/api';

export default function Home() {
  const [meetings, setMeetings] = useState<any[]>([]);
  const [stats, setStats] = useState({ activeMeetings: 0, participants: 0, avgAttention: 0, alerts: 0 });
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newMeetingTitle, setNewMeetingTitle] = useState('');
  const [newMeetingDesc, setNewMeetingDesc] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const fetchData = async () => {
    try {
      const response = await meetingsApi.list();
      const data = response.data || [];
      setMeetings(data);

      const active = data.filter((m: any) => m.status === 'active').length;
      const totalParticipants = data.reduce((sum: number, m: any) =>
        sum + (m.Participants?.length || 0), 0);
      setStats({
        activeMeetings: active,
        participants: totalParticipants,
        avgAttention: 0,
        alerts: 0
      });
    } catch (error) {
      console.error('Failed to fetch meetings:', error);
      setMeetings([]);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateMeeting = async () => {
    if (!newMeetingTitle.trim()) return;
    setIsCreating(true);
    try {
      await meetingsApi.create({ title: newMeetingTitle, description: newMeetingDesc });
      setShowCreateModal(false);
      setNewMeetingTitle('');
      setNewMeetingDesc('');
      fetchData();
    } catch (error) {
      console.error('Failed to create meeting:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleStartMeeting = async (id: string) => {
    try {
      await meetingsApi.start(id);
      fetchData();
    } catch (error) {
      console.error('Failed to start meeting:', error);
    }
  };

  const handleEndMeeting = async (id: string) => {
    try {
      await meetingsApi.end(id);
      fetchData();
    } catch (error) {
      console.error('Failed to end meeting:', error);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Dashboard
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Monitor and analyze meeting attention in real-time
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/recordings"
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              <Film size={20} />
              Recordings
            </Link>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              <Plus size={20} />
              New Meeting
            </button>
          </div>
        </header>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard icon={<Video />} title="Active Meetings" value={String(stats.activeMeetings)} color="blue" />
          <StatCard icon={<Users />} title="Participants" value={String(stats.participants)} color="green" />
          <StatCard icon={<Activity />} title="Avg Attention" value={`${stats.avgAttention}%`} color="yellow" />
          <StatCard icon={<AlertTriangle />} title="Alerts Today" value={String(stats.alerts)} color="red" />
        </div>

        {/* Meetings List */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Recent Meetings</h2>
          <div className="space-y-4">
            {meetings.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No meetings yet. Create your first meeting!</p>
            ) : meetings.slice(0, 10).map((meeting) => (
              <MeetingCard
                key={meeting.ID || meeting.id}
                meeting={meeting}
                onStart={handleStartMeeting}
                onEnd={handleEndMeeting}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Create Meeting Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Create New Meeting</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-gray-500 hover:text-gray-700">
                <X size={20} />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Meeting Title *
                </label>
                <input
                  type="text"
                  value={newMeetingTitle}
                  onChange={(e) => setNewMeetingTitle(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  placeholder="e.g., Team Standup"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={newMeetingDesc}
                  onChange={(e) => setNewMeetingDesc(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  rows={3}
                  placeholder="Optional description..."
                />
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateMeeting}
                  disabled={isCreating || !newMeetingTitle.trim()}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                >
                  {isCreating ? 'Creating...' : 'Create Meeting'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  );
}

function StatCard({ icon, title, value, color }: { icon: React.ReactNode; title: string; value: string; color: string }) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300',
    green: 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-300',
    yellow: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900 dark:text-yellow-300',
    red: 'bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-300',
  }[color];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses}`}>{icon}</div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        </div>
      </div>
    </div>
  );
}

interface MeetingCardProps {
  meeting: any;
  onStart: (id: string) => void;
  onEnd: (id: string) => void;
}

function MeetingCard({ meeting, onStart, onEnd }: MeetingCardProps) {
  const id = meeting.ID || meeting.id;
  const title = meeting.Title || meeting.title;
  const status = meeting.Status || meeting.status || 'scheduled';
  const participants = meeting.Participants?.length || meeting.participants || 0;

  const statusColors: Record<string, string> = {
    active: 'bg-green-100 text-green-700',
    scheduled: 'bg-blue-100 text-blue-700',
    ended: 'bg-gray-100 text-gray-700',
  };

  return (
    <div className="flex items-center justify-between p-4 border rounded-lg dark:border-gray-700">
      <div>
        <h3 className="font-medium text-gray-900 dark:text-white">{title}</h3>
        <p className="text-sm text-gray-500">{participants} participants</p>
      </div>
      <div className="flex items-center gap-3">
        <span className={`px-2 py-1 text-xs rounded-full ${statusColors[status] || statusColors.scheduled}`}>
          {status}
        </span>
        {status === 'scheduled' && (
          <button
            onClick={() => onStart(id)}
            className="flex items-center gap-1 px-3 py-1.5 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm"
          >
            <Play size={14} />
            Start
          </button>
        )}
        {status === 'active' && (
          <button
            onClick={() => onEnd(id)}
            className="flex items-center gap-1 px-3 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm"
          >
            <Square size={14} />
            End
          </button>
        )}
        <a
          href={`/meeting/${id}`}
          className="px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm"
        >
          View
        </a>
      </div>
    </div>
  );
}

