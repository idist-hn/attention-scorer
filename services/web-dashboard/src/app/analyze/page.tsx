'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Upload, FileVideo, Loader2, CheckCircle, XCircle, ArrowLeft, Play, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { videoAnalysis, VideoAnalysis } from '@/lib/api';

export default function AnalyzePage() {
  const [analyses, setAnalyses] = useState<VideoAnalysis[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState('');

  const fetchAnalyses = useCallback(async () => {
    try {
      const res = await videoAnalysis.list();
      setAnalyses(res.data || []);
    } catch (err) {
      console.error('Failed to fetch analyses:', err);
    }
  }, []);

  useEffect(() => {
    fetchAnalyses();
    const interval = setInterval(fetchAnalyses, 5000);
    return () => clearInterval(interval);
  }, [fetchAnalyses]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file);
      setError('');
    } else {
      setError('Please select a valid video file');
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError('');
    try {
      await videoAnalysis.upload(selectedFile);
      setSelectedFile(null);
      fetchAnalyses();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this analysis?')) return;
    try {
      await videoAnalysis.delete(id);
      fetchAnalyses();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <FileVideo className="w-6 h-6 text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Video Analysis</h1>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Upload Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Upload Video for Analysis
          </h2>
          
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragOver ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-600'
            }`}
          >
            <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600 dark:text-gray-300 mb-2">
              Drag and drop a video file here, or
            </p>
            <label className="cursor-pointer text-blue-600 hover:text-blue-700">
              browse files
              <input type="file" accept="video/*" onChange={handleFileSelect} className="hidden" />
            </label>
            <p className="text-sm text-gray-400 mt-2">Supports MP4, WebM, AVI, MOV, MKV</p>
          </div>

          {selectedFile && (
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileVideo className="w-8 h-8 text-blue-500" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">{formatSize(selectedFile.size)}</p>
                </div>
              </div>
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                {uploading ? 'Uploading...' : 'Analyze'}
              </button>
            </div>
          )}

          {error && <p className="mt-2 text-red-500 text-sm">{error}</p>}
        </div>

        {/* Analyses List */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Your Analyses</h2>
          </div>

          {analyses.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <FileVideo className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No analyses yet. Upload a video to get started.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {analyses.map((analysis) => (
                <AnalysisItem
                  key={analysis.id}
                  analysis={analysis}
                  onDelete={handleDelete}
                  formatSize={formatSize}
                  formatDuration={formatDuration}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function AnalysisItem({
  analysis,
  onDelete,
  formatSize,
  formatDuration
}: {
  analysis: VideoAnalysis;
  onDelete: (id: string) => void;
  formatSize: (bytes: number) => string;
  formatDuration: (seconds: number) => string;
}) {
  const statusIcon = {
    pending: <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />,
    processing: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
    completed: <CheckCircle className="w-5 h-5 text-green-500" />,
    failed: <XCircle className="w-5 h-5 text-red-500" />,
  };

  const statusText = {
    pending: 'Pending',
    processing: `Processing ${analysis.progress}%`,
    completed: 'Completed',
    failed: 'Failed',
  };

  return (
    <div className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {statusIcon[analysis.status]}
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{analysis.filename}</p>
            <p className="text-sm text-gray-500">
              {formatSize(analysis.file_size)}
              {analysis.duration > 0 && ` • ${formatDuration(analysis.duration)}`}
              {' • '}{new Date(analysis.created_at).toLocaleString()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-sm px-2 py-1 rounded ${
            analysis.status === 'completed' ? 'bg-green-100 text-green-700' :
            analysis.status === 'failed' ? 'bg-red-100 text-red-700' :
            'bg-blue-100 text-blue-700'
          }`}>
            {statusText[analysis.status]}
          </span>
          {analysis.status === 'completed' && (
            <Link
              href={`/analyze/${analysis.id}`}
              className="p-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
            >
              <Play className="w-4 h-4" />
            </Link>
          )}
          <button
            onClick={() => onDelete(analysis.id)}
            className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-red-500"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {analysis.status === 'processing' && (
        <div className="mt-3">
          <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${analysis.progress}%` }}
            />
          </div>
        </div>
      )}

      {analysis.status === 'failed' && analysis.error_message && (
        <p className="mt-2 text-sm text-red-500">{analysis.error_message}</p>
      )}
    </div>
  );
}

