'use client';

import React from 'react';

interface AttentionScoreProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function AttentionScore({ score, size = 'md', showLabel = true }: AttentionScoreProps) {
  const getColor = (score: number) => {
    if (score >= 70) return { bg: 'bg-green-500', text: 'text-green-500', label: 'High' };
    if (score >= 40) return { bg: 'bg-yellow-500', text: 'text-yellow-500', label: 'Medium' };
    return { bg: 'bg-red-500', text: 'text-red-500', label: 'Low' };
  };

  const { bg, text, label } = getColor(score);

  const sizeClasses = {
    sm: { ring: 'w-12 h-12', text: 'text-sm', stroke: 3 },
    md: { ring: 'w-20 h-20', text: 'text-xl', stroke: 4 },
    lg: { ring: 'w-28 h-28', text: 'text-2xl', stroke: 5 },
  }[size];

  const radius = size === 'sm' ? 20 : size === 'md' ? 35 : 50;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`relative ${sizeClasses.ring}`}>
        <svg className="w-full h-full transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="50%"
            cy="50%"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={sizeClasses.stroke}
            className="text-gray-200 dark:text-gray-700"
          />
          {/* Progress circle */}
          <circle
            cx="50%"
            cy="50%"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={sizeClasses.stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={text}
            style={{ transition: 'stroke-dashoffset 0.3s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`font-bold ${sizeClasses.text} text-gray-900 dark:text-white`}>
            {Math.round(score)}%
          </span>
        </div>
      </div>
      {showLabel && (
        <span className={`text-xs font-medium ${text}`}>{label}</span>
      )}
    </div>
  );
}

interface AttentionBadgeProps {
  score: number;
  name: string;
}

export function AttentionBadge({ score, name }: AttentionBadgeProps) {
  const getColor = (score: number) => {
    if (score >= 70) return 'bg-green-100 text-green-700 border-green-300';
    if (score >= 40) return 'bg-yellow-100 text-yellow-700 border-yellow-300';
    return 'bg-red-100 text-red-700 border-red-300';
  };

  return (
    <div className={`flex items-center gap-2 px-3 py-1 rounded-full border ${getColor(score)}`}>
      <span className="text-sm font-medium">{name}</span>
      <span className="text-sm font-bold">{Math.round(score)}%</span>
    </div>
  );
}

export default AttentionScore;

