/**
 * StatusIndicator.tsx
 * Visual indicator for backend processing state
 * Shows pulse during PENDING/PROCESSING, success checkmark on COMPLETED, error on FAILED
 */

import React from 'react';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';

interface StatusIndicatorProps {
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress?: number; // 0-100, optional
  isFetching?: boolean;
}

/**
 * StatusIndicator Component
 * Provides visual feedback on backend processing state
 * Uses enterprise-appropriate visual language (minimal animation, clear states)
 */
export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  progress,
  isFetching = false,
}) => {
  const getStatusContent = () => {
    switch (status) {
      case 'PENDING':
      case 'PROCESSING':
        return (
          <div className="flex items-center gap-2">
            <div className="relative w-4 h-4">
              {/* Outer pulse ring */}
              <div
                className="absolute inset-0 rounded-full bg-blue-400 opacity-75"
                style={{
                  animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                }}
              />
              {/* Inner solid dot */}
              <div className="absolute inset-1 rounded-full bg-blue-600" />
            </div>
            <span className="text-sm font-medium text-slate-600">
              {status === 'PROCESSING' ? 'Processing' : 'Waiting'}
            </span>
            {progress !== undefined && progress > 0 && (
              <span className="text-xs text-slate-500">({progress}%)</span>
            )}
          </div>
        );

      case 'COMPLETED':
        return (
          <div className="flex items-center gap-2">
            <CheckCircle2
              className="w-4 h-4 text-emerald-600"
              strokeWidth={2.5}
            />
            <span className="text-sm font-medium text-emerald-700">
              Completed
            </span>
          </div>
        );

      case 'FAILED':
        return (
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600" strokeWidth={2.5} />
            <span className="text-sm font-medium text-red-700">Failed</span>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex items-center justify-between px-1 py-1">
      {getStatusContent()}
      {isFetching && status !== 'COMPLETED' && (
        <Clock className="w-4 h-4 text-slate-400 animate-spin" />
      )}
    </div>
  );
};

/**
 * Progress Bar variant for full-width progress indication
 */
interface ProgressBarProps {
  progress: number; // 0-100
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
}

export const StatusProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  status,
}) => {
  const getBarColor = () => {
    if (status === 'FAILED') return 'bg-red-500';
    if (status === 'COMPLETED') return 'bg-emerald-500';
    return 'bg-blue-500';
  };

  return (
    <div className="w-full h-1 bg-slate-200 rounded-full overflow-hidden">
      <div
        className={`h-full transition-all duration-500 ease-out ${getBarColor()}`}
        style={{ width: `${Math.min(progress, 100)}%` }}
      />
    </div>
  );
};
