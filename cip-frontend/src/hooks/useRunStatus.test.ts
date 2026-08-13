/**
 * hooks/useRunStatus.test.ts
 * Example tests for useRunStatus custom hook
 * Shows patterns for testing React Query hooks with Vitest
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRunStatus } from './useRunStatus';
import { StatusResponse } from '../types';
import React from 'react';

describe('useRunStatus', () => {
  let mockFetch: ReturnType<typeof vi.fn>;
  let queryClient: QueryClient;

  beforeEach(() => {
    mockFetch = vi.fn();
    // Vitest's native global stubbing utility—fixes the TypeScript red line
    vi.stubGlobal('fetch', mockFetch);

    // Disable retries entirely in tests so network/404 tests fail instantly
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  const mockStatusResponse: StatusResponse = {
    run_id: 'run-123',
    status: 'COMPLETED',
    executive_summary: 'Strong financial performance',
    agent_results: {
      financial: {
        title: 'Financial Analysis',
        confidence_score: 92,
        detailed_insight: 'Revenue growth of 15%',
        system_evidence: ['Q4 earnings up'],
      },
    },
    created_at: '2024-01-15T10:00:00Z',
    completed_at: '2024-01-15T10:05:00Z',
  };

  const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);

  it('fetches run status on mount', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatusResponse,
    });

    const { result } = renderHook(() => useRunStatus({ runId: 'run-123' }), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.data).toBeDefined();
    });

    expect(mockFetch).toHaveBeenCalledWith(
      '/status/run-123',
      expect.any(Object)
    );
  });

  it('returns loading state initially', () => {
    mockFetch.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() =>
            resolve({
              ok: true,
              json: async () => mockStatusResponse,
            })
          )
        )
    );

    const { result } = renderHook(() => useRunStatus({ runId: 'run-123' }), {
      wrapper,
    });

    expect(result.current.isLoading).toBe(true);
  });

  it('handles completed status', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatusResponse,
    });

    const { result } = renderHook(() => useRunStatus({ runId: 'run-123' }), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.data?.status).toBe('COMPLETED');
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it('handles failed status', async () => {
    const failedResponse: StatusResponse = {
      run_id: 'run-123',
      status: 'FAILED',
      error_message: 'Analysis failed',
      created_at: '2024-01-15T10:00:00Z',
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => failedResponse,
    });

    const { result } = renderHook(() => useRunStatus({ runId: 'run-123' }), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.data?.status).toBe('FAILED');
    });
  });

  it('handles network errors', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(
      () => useRunStatus({ runId: 'run-123', max_retries: 0 }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it('handles API 404 errors', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ error: 'Run not found' }),
    });

    const { result } = renderHook(
      () => useRunStatus({ runId: 'nonexistent', max_retries: 0 }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it('respects enabled flag', () => {
    const { result } = renderHook(
      () => useRunStatus({ runId: 'run-123', enabled: false }),
      { wrapper }
    );

    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.status).toBe('idle');
  });

  it('caches results for same runId', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockStatusResponse,
    });

    const { result: result1 } = renderHook(
      () => useRunStatus({ runId: 'run-123' }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result1.current.data).toBeDefined();
    });

    const initialFetchCount = mockFetch.mock.calls.length;

    const { result: result2 } = renderHook(
      () => useRunStatus({ runId: 'run-123' }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result2.current.data).toBeDefined();
    });

    expect(mockFetch.mock.calls.length).toBe(initialFetchCount);
  });

  it('makes separate requests for different runIds', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockStatusResponse,
    });

    renderHook(() => useRunStatus({ runId: 'run-123' }), { wrapper });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/status/run-123',
        expect.any(Object)
      );
    });

    renderHook(() => useRunStatus({ runId: 'run-456' }), { wrapper });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/status/run-456',
        expect.any(Object)
      );
    });

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('uses custom polling interval', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        ...mockStatusResponse,
        status: 'PROCESSING',
      }),
    });

    renderHook(
      () =>
        useRunStatus({
          runId: 'run-123',
          polling_interval: 5000,
        }),
      { wrapper }
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
  });
});
