/**
 * utils/formatting.ts
 * Data transformation and formatting utilities
 * Handles display-layer data preparation without modifying types
 */

import { AgentResult, StatusResponse } from '../types';

/**
 * Format a confidence score with human-readable label
 */
export function formatConfidence(score: number): string {
  if (score >= 90) return 'Very High';
  if (score >= 75) return 'High';
  if (score >= 60) return 'Moderate';
  if (score >= 40) return 'Low';
  return 'Very Low';
}

/**
 * Get semantic color class for confidence score
 * For use in Tailwind CSS classes
 */
export function getConfidenceClass(score: number): {
  bg: string;
  text: string;
  badge: string;
} {
  if (score >= 80) {
    return {
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      badge: 'bg-emerald-200 text-emerald-900',
    };
  }
  if (score >= 60) {
    return {
      bg: 'bg-amber-50',
      text: 'text-amber-700',
      badge: 'bg-amber-200 text-amber-900',
    };
  }
  return {
    bg: 'bg-red-50',
    text: 'text-red-700',
    badge: 'bg-red-200 text-red-900',
  };
}

/**
 * Format a date string to human-readable format
 * Handles ISO 8601 strings from backend
 */
export function formatDate(dateString: string, includeTime = true): string {
  try {
    const date = new Date(dateString);
    const options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    };

    if (includeTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }

    return date.toLocaleDateString('en-US', options);
  } catch {
    return dateString;
  }
}

/**
 * Calculate time elapsed since a date
 * "2 hours ago", "3 days ago", etc.
 */
export function formatTimeAgo(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
    if (seconds < 2592000) return `${Math.floor(seconds / 604800)} weeks ago`;

    return formatDate(dateString, false);
  } catch {
    return dateString;
  }
}

/**
 * Truncate long text with ellipsis
 */
export function truncateText(text: string, maxLength = 100): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Extract main domain from evidence URLs
 */
export function extractDomain(url: string): string {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.replace('www.', '');
  } catch {
    return url;
  }
}

/**
 * Count total evidence items across all agents
 */
export function countTotalEvidence(statusResponse: StatusResponse): number {
  if (!statusResponse.agent_results) return 0;

  return Object.values(statusResponse.agent_results).reduce((total, agent) => {
    return total + (agent.system_evidence?.length || 0);
  }, 0);
}

/**
 * Count agents with high confidence (>= 80%
 */
export function countHighConfidenceAgents(
  statusResponse: StatusResponse
): number {
  if (!statusResponse.agent_results) return 0;

  return Object.values(statusResponse.agent_results).filter(
    (agent) => agent.confidence_score >= 80
  ).length;
}

/**
 * Get average confidence across all agents
 */
export function getAverageConfidence(statusResponse: StatusResponse): number {
  if (!statusResponse.agent_results) return 0;

  const agents = Object.values(statusResponse.agent_results);
  if (agents.length === 0) return 0;

  const total = agents.reduce((sum, agent) => sum + agent.confidence_score, 0);
  return Math.round(total / agents.length);
}

/**
 * Sort agents by confidence score (descending)
 */
export function sortAgentsByConfidence(agents: AgentResult[]): AgentResult[] {
  return [...agents].sort((a, b) => b.confidence_score - a.confidence_score);
}

/**
 * Filter agents by minimum confidence threshold
 */
export function filterAgentsByConfidence(
  agents: AgentResult[],
  minConfidence = 60
): AgentResult[] {
  return agents.filter((agent) => agent.confidence_score >= minConfidence);
}

/**
 * Generate a summary statistics object from status response
 * Useful for dashboard overview cards
 */
export interface SummaryStats {
  totalAgents: number;
  highConfidenceCount: number;
  averageConfidence: number;
  totalEvidence: number;
  processingTime?: number; // milliseconds
}

export function generateSummaryStats(
  statusResponse: StatusResponse
): SummaryStats {
  const agents = Object.values(statusResponse.agent_results || {});
  let processingTime: number | undefined;

  if (statusResponse.created_at && statusResponse.completed_at) {
    const start = new Date(statusResponse.created_at).getTime();
    const end = new Date(statusResponse.completed_at).getTime();
    processingTime = end - start;
  }

  return {
    totalAgents: agents.length,
    highConfidenceCount: countHighConfidenceAgents(statusResponse),
    averageConfidence: getAverageConfidence(statusResponse),
    totalEvidence: countTotalEvidence(statusResponse),
    processingTime,
  };
}
