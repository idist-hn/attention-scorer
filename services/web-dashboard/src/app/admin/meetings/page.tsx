'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, meetings as meetingsApi } from '@/lib/api';
import AdminLayout from '@/components/AdminLayout';
import { Video, Plus, Search, Play, Square, Eye, Trash2, Users, Clock } from 'lucide-react';

interface Meeting {
  id: string;
  title: string;
  description: string;
  status: 'scheduled' | 'active' | 'ended';
  host: { name: string; email: string };
  start_time: string;
  end_time: string;
  created_at: string;
  participant_count?: number;
}

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'scheduled' | 'ended'>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newMeeting, setNewMeeting] = useState({ title: '', description: '' });
  const [message, setMessage] = useState({ type: '', text: '' });

  const fetchMeetings = async () => {
    try {
      const response = await meetingsApi.list();
      setMeetings(response.data || []);
    } catch (error) {
      console.error('Failed to fetch meetings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMeetings(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await meetingsApi.create(newMeeting);
      setMessage({ type: 'success', text: 'Meeting created successfully' });
      setShowCreateModal(false);
      setNewMeeting({ title: '', description: '' });
      fetchMeetings();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.error || 'Failed to create meeting' });
    }
  };

  const handleStart = async (id: string) => {
    try {
      await meetingsApi.start(id);
      fetchMeetings();
    } catch (error) {
      console.error('Failed to start meeting:', error);
    }
  };

  const handleEnd = async (id: string) => {
    try {
      await meetingsApi.end(id);
      fetchMeetings();
    } catch (error) {
      console.error('Failed to end meeting:', error);
    }
  };

  const filteredMeetings = meetings.filter(m => {
    const matchesSearch = m.title.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'all' || m.status === filter;
    return matchesSearch && matchesFilter;
  });

  const getStatusBadge = (status: string) => {
    const styles = {
      active: 'bg-green-100 text-green-700',
      scheduled: 'bg-blue-100 text-blue-700',
      ended: 'bg-gray-100 text-gray-700'
    };
    return styles[status as keyof typeof styles] || styles.scheduled;
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Video className="w-7 h-7" /> Meetings Management
          </h1>
          <button onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">
            <Plus className="w-4 h-4" /> New Meeting
          </button>
        </div>

        {message.text && (
          <div className={`p-3 rounded-lg ${message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {message.text}
          </div>
        )}

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="p-4 border-b dark:border-gray-700 flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input type="text" placeholder="Search meetings..." value={search} onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" />
            </div>
            <select value={filter} onChange={(e) => setFilter(e.target.value as any)}
              className="px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white">
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="scheduled">Scheduled</option>
              <option value="ended">Ended</option>
            </select>
          </div>

          <div className="divide-y dark:divide-gray-700">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading meetings...</div>
            ) : filteredMeetings.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No meetings found</div>
            ) : filteredMeetings.map((meeting) => (
              <div key={meeting.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium text-gray-900 dark:text-white">{meeting.title}</h3>
                    <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadge(meeting.status)}`}>{meeting.status}</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{meeting.description || 'No description'}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                    <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {meeting.host?.name || 'Unknown'}</span>
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(meeting.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {meeting.status === 'scheduled' && (
                    <button onClick={() => handleStart(meeting.id)} className="p-2 text-green-600 hover:bg-green-50 rounded-lg" title="Start">
                      <Play className="w-5 h-5" />
                    </button>
                  )}
                  {meeting.status === 'active' && (
                    <button onClick={() => handleEnd(meeting.id)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg" title="End">
                      <Square className="w-5 h-5" />
                    </button>
                  )}
                  <Link href={`/meeting/${meeting.id}`} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg" title="View">
                    <Eye className="w-5 h-5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Create New Meeting</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Title</label>
                <input type="text" value={newMeeting.title} onChange={(e) => setNewMeeting({...newMeeting, title: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                <textarea value={newMeeting.description} onChange={(e) => setNewMeeting({...newMeeting, description: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white" rows={3} />
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button type="button" onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AdminLayout>
  );
}

