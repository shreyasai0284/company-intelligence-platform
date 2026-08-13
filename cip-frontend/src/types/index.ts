/**
 * Type definitions for Company Intelligence Platform API responses
 * Central source of truth for all data structures across the application
 */

/**
 * Individual agent result containing extracted insights
 * Each agent contributes structured data from different sources
 */
export interface AgentResult {
  title: string;
  confidence_score: number; // 0-100
  detailed_insight: string;
  system_evidence: string[];
  metadata?: {
    sources?: string[];
    last_updated?: string;
    data_points?: number;
  };
}

/**
 * Aggregate of all agent results
 * Keys represent agent names (financial, litigation, leadership, etc.)
 * Values contain the structured insights from each agent
 */
export interface AgentResults {
  [key: string]: AgentResult;
}

/**
 * Complete status response from backend polling endpoint
 * Returned by GET /status/{runId}
 */
export interface StatusResponse {
  run_id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress?: number; // 0-100, optional for in-progress states
  error_message?: string; // Present if status === 'FAILED'
  executive_summary?: string;
  agent_results?: AgentResults;
  created_at: string;
  completed_at?: string;
}

/**
 * Processed data for display layer
 * Represents a single agent's normalized card data
 */
export interface AgentCardData {
  id: string; // The key from agent_results (e.g., 'financial', 'litigation')
  title: string;
  confidence_score: number;
  detailed_insight: string;
  system_evidence: string[];
  sources?: string[];
  last_updated?: string;
}

/**
 * Query options for useRunStatus hook
 */
export interface UseRunStatusOptions {
  runId: string;
  enabled?: boolean;
  polling_interval?: number; // milliseconds, default 2000
  max_retries?: number;
  initialData?: StatusResponse;
}

/**
 * Return type for useRunStatus hook
 */
export interface UseRunStatusReturn {
  data: StatusResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  status: 'idle' | 'pending' | 'error' | 'success';
  isFetching: boolean;
}
