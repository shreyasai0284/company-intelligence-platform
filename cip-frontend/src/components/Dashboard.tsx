/**
 * Dashboard.tsx
 * Main intelligence platform dashboard
 * Orchestrates hero section, status indicator, and modular agent cards
 *
 * Architecture principles:
 * - Data fetching is decoupled via custom hook
 * - Cards are rendered dynamically based on API response keys
 * - Responsive grid adapts to content and viewport
 * - Loading states are handled gracefully
 */

import React, { useEffect } from 'react';
import {
  useRunStatus,
  useIsResultReady,
  useAgentCardsData,
} from '../hooks/useRunStatus';
import { StatusIndicator, StatusProgressBar } from './StatusIndicator';
import { HeroSection, HeroSectionSkeleton } from './HeroSection';
import AgentCard from './AgentCard';
import { UseRunStatusOptions } from '../types';
import { AlertCircle, ArrowRight } from 'lucide-react';

interface DashboardProps {
  /**
   * The run ID to poll for status and results
   */
  runId: string;

  /**
   * Optional company name for context
   */
  companyName?: string;

  /**
   * Custom polling configuration
   */
  pollingConfig?: Partial<UseRunStatusOptions>;

  /**
   * Optional direct report payload to render immediately
   */
  initialReport?: string;

  /**
   * Callback when results are fully loaded
   */
  onResultsLoaded?: (runId: string) => void;

  /**
   * Custom className for styling
   */
  className?: string;
}

/**
 * Helper to capitalize the first letter of words for clean presentation
 */
const formatTitleCase = (str: string) => {
  return str
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

/**
 * Dashboard Component
 * Enterprise-grade intelligence dashboard for CIP
 */
export const Dashboard: React.FC<DashboardProps> = ({
  runId,
  companyName = 'Company',
  pollingConfig = {},
  onResultsLoaded,
  className = '',
  initialReport,
}) => {
  const initialData = initialReport
    ? {
        run_id: runId,
        status: 'COMPLETED' as const,
        executive_summary: initialReport,
        agent_results: {},
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      }
    : undefined;

  // Fetch status from backend with polling
  const { data, isLoading, isError, error, isFetching } = useRunStatus({
    runId,
    enabled: true,
    polling_interval: 2000,
    ...pollingConfig,
    initialData,
  });

  // Helper hooks to check state
  const isResultReady = useIsResultReady(data);
  const agentCards = useAgentCardsData(data);

  // Safely format the company name for titles
  const formattedCompanyName = formatTitleCase(companyName);

  // Notify parent when results are loaded
  useEffect(() => {
    if (isResultReady && onResultsLoaded) {
      onResultsLoaded(runId);
    }
  }, [isResultReady, runId, onResultsLoaded]);

  // Render: Loading State
  if (isLoading && !data) {
    return (
      <div className={`min-h-screen bg-white ${className}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header skeleton */}
          <div className="mb-8 flex items-center justify-between">
            <div className="space-y-2">
              <div className="h-6 bg-slate-200 rounded w-48 animate-pulse" />
              <div className="h-4 bg-slate-100 rounded w-32 animate-pulse" />
            </div>
          </div>

          {/* Hero skeleton */}
          <HeroSectionSkeleton />

          {/* Card skeletons */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-48 bg-slate-100 rounded-lg animate-pulse"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Render: Error State
  if (isError || data?.status === 'FAILED') {
    return (
      <div className={`min-h-screen bg-white ${className}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-slate-900">
              {formattedCompanyName} Intelligence Report
            </h1>
          </div>

          {/* Error message */}
          <div className="bg-red-50 border border-red-200 rounded-lg px-6 py-8 mb-8">
            <div className="flex items-start gap-4">
              <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h2 className="text-lg font-semibold text-red-900 mb-2">
                  Unable to Load Report
                </h2>
                <p className="text-red-800 mb-4">
                  {error?.message ||
                    data?.error_message ||
                    'An unexpected error occurred while processing your request.'}
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="
                    inline-flex items-center gap-2
                    px-4 py-2 bg-red-600 text-white rounded-md
                    hover:bg-red-700 transition-colors
                    font-medium text-sm
                  "
                >
                  Try Again
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render: Success State
  return (
    <div className={`min-h-screen bg-white ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header with Title and Status */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold text-slate-900 mb-2 capitalize">
                {formattedCompanyName} Intelligence Report
              </h1>
              <p className="text-slate-600">
                Comprehensive analysis across {agentCards.length} intelligence
                domains
              </p>
            </div>
          </div>

          {/* Status indicator row */}
          <div className="flex items-center justify-between">
            <StatusIndicator
              status={data?.status || 'PENDING'}
              progress={data?.progress}
              isFetching={isFetching}
            />
          </div>

          {/* Progress bar for in-progress states */}
          {data?.status === 'PROCESSING' && data.progress !== undefined && (
            <div className="mt-4">
              <StatusProgressBar
                progress={data.progress}
                status={data.status}
              />
            </div>
          )}
        </div>

        {/* Hero Section: Executive Summary */}
        {data?.executive_summary && (
          <HeroSection
            summary={data.executive_summary}
            title={formattedCompanyName}
            generatedAt={data.created_at}
          />
        )}

        {/* Agent Results Grid */}
        {isResultReady && agentCards.length > 0 ? (
          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-6">
              Detailed Analysis
            </h2>

            <div
              className="
                grid grid-cols-1 md:grid-cols-2 gap-6
                auto-rows-max
              "
            >
              {agentCards.map((card) => (
                <AgentCard
                  key={card.id}
                  id={card.id}
                  data={card}
                  onToggle={(isOpen) => {
                    console.debug(`Card ${card.id} toggled: ${isOpen}`);
                  }}
                />
              ))}
            </div>
          </div>
        ) : !isResultReady ? (
          <div className="text-center py-12">
            <div className="inline-block p-4 bg-blue-50 rounded-lg mb-4">
              <div className="w-10 h-10 bg-blue-100 rounded-full animate-pulse mx-auto" />
            </div>
            <p className="text-slate-600 mb-2">Processing your request...</p>
            <p className="text-sm text-slate-500">
              This may take a few moments. Your page will update automatically.
            </p>
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-slate-600">
              {data?.executive_summary
                ? 'Your report is ready above. Additional agent cards will appear once richer structured results are available.'
                : 'No agent results available. Please check the report or try again.'}
            </p>
          </div>
        )}

        {/* Footer metadata */}
        {data && (
          <footer className="mt-16 pt-8 border-t border-slate-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm text-slate-600">
              <div>
                <p className="text-slate-500 text-xs uppercase font-semibold mb-1">
                  Run ID
                </p>
                <p className="font-mono text-slate-700">{data.run_id}</p>
              </div>
              <div>
                <p className="text-slate-500 text-xs uppercase font-semibold mb-1">
                  Status
                </p>
                <p className="capitalize text-slate-700">{data.status}</p>
              </div>
              <div>
                <p className="text-slate-500 text-xs uppercase font-semibold mb-1">
                  Created
                </p>
                <p className="text-slate-700">
                  {new Date(data.created_at).toLocaleDateString()}
                </p>
              </div>
              {data.completed_at && (
                <div>
                  <p className="text-slate-500 text-xs uppercase font-semibold mb-1">
                    Completed
                  </p>
                  <p className="text-slate-700">
                    {new Date(data.completed_at).toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>
          </footer>
        )}
      </div>
    </div>
  );
};

export default Dashboard;