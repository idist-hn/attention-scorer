'use client';

import React from 'react';
import { User, AlertTriangle, Eye, EyeOff, Users, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface Participant {
  id: string;
  name: string;
  avatar?: string;
  attention_score: number;
  is_looking_away: boolean;
  is_drowsy: boolean;
  is_active: boolean;
}

interface ParticipantGridProps {
  participants: Participant[];
}

export function ParticipantGrid({ participants }: ParticipantGridProps) {
  // Sort participants: active first, then by attention score
  const sortedParticipants = [...participants].sort((a, b) => {
    if (a.is_active !== b.is_active) return a.is_active ? -1 : 1;
    return b.attention_score - a.attention_score;
  });

  if (participants.length === 0) {
    return (
      <div className="text-center py-6">
        <Users className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No participants detected</p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Start your camera to begin</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {sortedParticipants.map((participant, index) => (
        <ParticipantRow key={participant.id} participant={participant} index={index} />
      ))}
    </div>
  );
}

function ParticipantRow({ participant, index }: { participant: Participant; index: number }) {
  const score = participant.attention_score;

  // Determine status color and icon
  const getScoreColor = () => {
    if (participant.is_drowsy) return 'text-red-500';
    if (participant.is_looking_away) return 'text-amber-500';
    if (score >= 70) return 'text-green-500';
    if (score >= 40) return 'text-amber-500';
    return 'text-red-500';
  };

  const getScoreBg = () => {
    if (participant.is_drowsy) return 'bg-red-500';
    if (participant.is_looking_away) return 'bg-amber-500';
    if (score >= 70) return 'bg-green-500';
    if (score >= 40) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const getTrendIcon = () => {
    if (score >= 70) return <TrendingUp className="w-3 h-3 text-green-500" />;
    if (score >= 40) return <Minus className="w-3 h-3 text-amber-500" />;
    return <TrendingDown className="w-3 h-3 text-red-500" />;
  };

  const getStatusIndicator = () => {
    if (participant.is_drowsy) {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-[10px] font-medium rounded">
          <AlertTriangle className="w-3 h-3" />
          Drowsy
        </span>
      );
    }
    if (participant.is_looking_away) {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 text-[10px] font-medium rounded">
          <EyeOff className="w-3 h-3" />
          Away
        </span>
      );
    }
    if (score >= 70) {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-[10px] font-medium rounded">
          <Eye className="w-3 h-3" />
          Focused
        </span>
      );
    }
    return null;
  };

  return (
    <div
      className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all animate-in slide-in-from-left-2 duration-200"
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {/* Avatar with status ring */}
      <div className="relative flex-shrink-0">
        {participant.avatar ? (
          <img
            src={participant.avatar}
            alt={participant.name}
            className={`w-9 h-9 rounded-full ring-2 ${participant.is_active ? 'ring-green-500' : 'ring-gray-300 dark:ring-gray-600'}`}
          />
        ) : (
          <div className={`w-9 h-9 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center ring-2 ${participant.is_active ? 'ring-green-500' : 'ring-gray-300 dark:ring-gray-600'}`}>
            <span className="text-white text-sm font-medium">
              {participant.name.charAt(0).toUpperCase()}
            </span>
          </div>
        )}
        {/* Active indicator */}
        {participant.is_active && (
          <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 border-2 border-white dark:border-gray-800 rounded-full" />
        )}
      </div>

      {/* Name and status */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {participant.name}
          </p>
          {getStatusIndicator()}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          {getTrendIcon()}
          <span className={`text-xs font-medium ${getScoreColor()}`}>
            {Math.round(score)}% attention
          </span>
        </div>
      </div>

      {/* Score circle */}
      <div className="flex-shrink-0">
        <div className="relative w-10 h-10">
          <svg className="w-10 h-10 transform -rotate-90">
            <circle
              cx="20"
              cy="20"
              r="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              className="text-gray-200 dark:text-gray-600"
            />
            <circle
              cx="20"
              cy="20"
              r="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeDasharray={`${score * 1.005} 100.5`}
              strokeLinecap="round"
              className={getScoreColor()}
              style={{ transition: 'stroke-dasharray 0.5s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-xs font-bold ${getScoreColor()}`}>
              {Math.round(score)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ParticipantGrid;

