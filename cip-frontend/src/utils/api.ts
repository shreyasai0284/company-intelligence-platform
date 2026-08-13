/**
 * utils/api.ts
 * Centralized API client and request utilities
 * Handles base URLs, headers, error handling, and caching strategies
 */

import { StatusResponse } from '../types';

/**
 * API configuration
 * Can be overridden per environment via .env files
 */
const API_BASE_URL = import.meta.env.DEV
  ? '/api'
  : import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_TIMEOUT = 30000; // 30 seconds

/**
 * Error class for API-specific errors
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public details?: any
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = 'ApiError';
  }
}

/**
 * Generic API request function with timeout and error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const headers = {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new ApiError(response.status, response.statusText, errorBody);
    }

    const data = await response.json();
    return data as T;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new ApiError(0, 'Network Error', {
        message: 'Unable to reach API',
      });
    }

    throw error;
  }
}

function normalizeTimestamp(value: unknown): string | undefined {
  if (typeof value === 'number') {
    return new Date(value * 1000).toISOString();
  }

  if (typeof value === 'string') {
    const numeric = Number(value);
    if (!Number.isNaN(numeric) && /^\\d{10}$/.test(value.trim())) {
      return new Date(numeric * 1000).toISOString();
    }

    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toISOString();
    }
  }

  return undefined;
}

function normalizeStatusResponse(response: any, runId: string): StatusResponse {
  const createdAt = normalizeTimestamp(response.created_at) ?? new Date().toISOString();
  const completedAt = normalizeTimestamp(response.completed_at);

  return {
    ...response,
    run_id: response.run_id || runId,
    created_at: createdAt,
    completed_at: completedAt,
  } as StatusResponse;
}

/**
 * Fetch status for a specific run
 * Used by useRunStatus hook
 */
export async function getRunStatus(runId: string): Promise<StatusResponse> {
  const response = await apiRequest<any>(`/status/${runId}`);

  if (response && typeof response === 'object' && !response.status) {
    return normalizeStatusResponse({
      run_id: runId,
      status: 'COMPLETED',
      executive_summary: typeof response.report === 'string' ? response.report : response.message || 'Report available.',
      agent_results: {},
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    }, runId);
  }

  return normalizeStatusResponse(response, runId);
}

/**
 * Optional: Cancel a running analysis
 */
export async function cancelRun(runId: string): Promise<void> {
  await apiRequest(`/cancel/${runId}`, { method: 'POST' });
}

/**
 * Optional: Retry a failed run
 */
export async function retryRun(runId: string): Promise<StatusResponse> {
  return apiRequest<StatusResponse>(`/retry/${runId}`, { method: 'POST' });
}

/**
 * Optional: Get historical runs
 */
export interface HistoricalRun {
  run_id: string;
  company_name: string;
  country: string;
  status: StatusResponse['status'];
  created_at: string;
  completed_at?: string;
}

export async function getHistoricalRuns(limit = 50): Promise<HistoricalRun[]> {
  return apiRequest<HistoricalRun[]>(`/runs?limit=${limit}`);
}

/**
 * Retry logic with exponential backoff
 * Used by useRunStatus hook
 */
export function getRetryDelay(attemptCount: number, maxDelay = 30000): number {
  const delay = Math.pow(2, attemptCount) * 1000; // 1s, 2s, 4s, 8s, 16s, 32s...
  return Math.min(delay, maxDelay);
}
// src/utils/api.ts

// NEW: Submit analysis request to backend
export interface SubmitAnalysisResponse {
  run_id?: string;
  report?: string;
  markdown?: string;
  [key: string]: any;
}

export async function submitAnalysis(params: {
  company_name: string;
  country: string;
  tier?: 'Standard' | 'Premium';
}): Promise<SubmitAnalysisResponse> {
  const apiUrl = import.meta.env.DEV
    ? '/api'
    : import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  const response = await fetch(`${apiUrl}/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      company: params.company_name,
      country: params.country,
      tier: params.tier ?? 'Standard',
    }),
  });

  const responseText = await response.text();

  if (!response.ok) {
    throw new Error(`Failed to submit analysis: ${response.statusText}${responseText ? ` - ${responseText}` : ''}`);
  }

  if (!responseText) {
    throw new Error('Failed to submit analysis: empty response from backend.');
  }

  try {
    return JSON.parse(responseText);
  } catch {
    throw new Error(`Failed to submit analysis: backend returned non-JSON content: ${responseText}`);
  }
}

// EXISTING: Fetch results once you have the runId
export async function fetchRunStatus(runId: string): Promise<StatusResponse> {
  const apiUrl = import.meta.env.DEV
    ? '/api'
    : import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
  const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true';

  // For now, still use mock data
  if (USE_MOCK_DATA) {
    const mockData = await import('./mockData');
    return (
      (mockData as any).mock_Status_Response ??
      (mockData as any).mockStatusResponse ??
      (mockData as any).default
    );
  }

  // When backend ready, fetch real data
  const response = await fetch(`${apiUrl}/status/${runId}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch run status: ${response.statusText}`);
  }

  return response.json();
}