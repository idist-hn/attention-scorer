'use client';

import React from 'react';
import { AlertTriangle, Eye, Moon, X, Bell, CheckCircle2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface Alert {
  id: string;
  participant_name: string;
  alert_type: 'not_attentive' | 'looking_away' | 'drowsy';
  severity: 'info' | 'warning' | 'critical';
  message: string;
  created_at: string;
  resolved_at?: string;
}

interface AlertPanelProps {
  alerts: Alert[];
  onDismiss?: (alertId: string) => void;
}

export function AlertPanel({ alerts, onDismiss }: AlertPanelProps) {
  const getIcon = (type: string, severity: string) => {
    const iconClass = severity === 'critical' ? 'text-red-500' : severity === 'warning' ? 'text-amber-500' : 'text-blue-500';
    switch (type) {
      case 'drowsy':
        return <Moon className={`w-4 h-4 ${iconClass}`} />;
      case 'looking_away':
        return <Eye className={`w-4 h-4 ${iconClass}`} />;
      default:
        return <AlertTriangle className={`w-4 h-4 ${iconClass}`} />;
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase bg-red-500 text-white rounded">Critical</span>;
      case 'warning':
        return <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase bg-amber-500 text-white rounded">Warning</span>;
      default:
        return <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase bg-blue-500 text-white rounded">Info</span>;
    }
  };

  const criticalCount = alerts.filter(a => a.severity === 'critical').length;
  const warningCount = alerts.filter(a => a.severity === 'warning').length;

  if (alerts.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center gap-2">
          <Bell className="w-4 h-4 text-gray-400" />
          <h3 className="font-semibold text-gray-900 dark:text-white">Alerts</h3>
        </div>
        <div className="p-6 text-center">
          <CheckCircle2 className="w-10 h-10 text-green-500 mx-auto mb-2" />
          <p className="text-sm font-medium text-gray-900 dark:text-white">All Clear!</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">No active alerts at the moment</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-gray-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Alerts</h3>
            <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
              {alerts.length}
            </span>
          </div>
          {/* Summary badges */}
          <div className="flex items-center gap-1.5">
            {criticalCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full">
                {criticalCount} critical
              </span>
            )}
            {warningCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-full">
                {warningCount} warning
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Alert list */}
      <div className="divide-y divide-gray-100 dark:divide-gray-700 max-h-72 overflow-y-auto">
        {alerts.map((alert, index) => (
          <div
            key={alert.id}
            className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors animate-in slide-in-from-top-2 duration-200"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5 p-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg">
                {getIcon(alert.alert_type, alert.severity)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-sm text-gray-900 dark:text-white truncate">
                    {alert.participant_name}
                  </span>
                  {getSeverityBadge(alert.severity)}
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                  {alert.message}
                </p>
                <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1">
                  {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                </p>
              </div>
              {onDismiss && (
                <button
                  onClick={() => onDismiss(alert.id)}
                  className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 rounded transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AlertPanel;

