/**
 * useRunStatus.ts
 * Custom TanStack Query hook for polling the /status/{runId} endpoint
 * Handles polling lifecycle, retry logic, and graceful error handling
 * Supports both real backend polling and local mock mode.
 */

import { useQuery } from '@tanstack/react-query';
import {
  StatusResponse,
  UseRunStatusOptions,
  UseRunStatusReturn,
} from '../types';

/**
 * Simulated mock data structure to safely run the frontend in isolation.
 * Includes multiple naming variations to guarantee fields map to your UI controls.
 */
import { MOCK_STATUS_RESPONSE } from '../utils/mockData';
import { getRunStatus } from '../utils/api';

async function fetchRunStatus(runId: string): Promise<StatusResponse> {
  const useMockData = import.meta.env.VITE_USE_MOCK_DATA === 'true';

  if (useMockData) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    return MOCK_STATUS_RESPONSE as any as StatusResponse;
  }

  return getRunStatus(runId);
}

/**
 * Custom hook for polling backend run status
 * Automatically stops polling when status === 'COMPLETED' or 'FAILED'
 */
export function useRunStatus(options: UseRunStatusOptions): UseRunStatusReturn {
  const {
    runId,
    enabled = true,
    polling_interval = 2000,
    max_retries = 5,
    initialData,
  } = options;

  const shouldContinuePolling = (data?: StatusResponse) => {
    if (!data) return true;
    return String(data.status).toUpperCase() !== 'COMPLETED' && String(data.status).toUpperCase() !== 'FAILED';
  };

  const query = useQuery<StatusResponse, Error>({
    queryKey: ['runStatus', runId],
    queryFn: () => fetchRunStatus(runId),
    initialData,
    refetchInterval: (query) => {
      return shouldContinuePolling(query.state.data) ? polling_interval : false;
    },
    refetchIntervalInBackground: false,
    enabled: enabled && !initialData,
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    retry: (failureCount) => {
      if (failureCount >= max_retries) {
        return false;
      }
      return true;
    },
    retryDelay: (attemptIndex) => Math.pow(2, attemptIndex) * 1000,
    staleTime: 1000,
    gcTime: 5 * 60 * 1000,
  });

  const derivedStatus = !enabled
    ? 'idle'
    : query.error
      ? 'error'
      : query.status;
  const derivedIsError = query.isError || !!query.error;

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: derivedIsError,
    error: query.error,
    status: derivedStatus as any,
    isFetching: query.isFetching,
  } as UseRunStatusReturn;
}

/**
 * Helper hook to check if data is complete and ready for display
 */
export function useIsResultReady(data: StatusResponse | undefined): boolean {
  return !!data && String(data.status).toUpperCase() === 'COMPLETED';
}

/**
 * Helper hook to extract normalized agent cards from results
 */
export function useAgentCardsData(data: StatusResponse | undefined) {
  const agentResults = data?.agent_results || {};
  return Object.entries(agentResults).map(([id, result]) => ({
    id,
    ...result,
  }));
}