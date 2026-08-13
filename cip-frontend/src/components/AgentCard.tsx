/**
 * AgentCard.tsx
 * Modular card component for displaying individual agent results
 * Implements progressive disclosure: title + confidence visible by default,
 * detailed insights hidden until expanded
 */

import React, { useState } from 'react';
import { ChevronDown, BookOpen, FileText } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@radix-ui/react-collapsible';
import { AgentResult } from '../types';

interface AgentCardProps {
  /**
   * Unique identifier for the agent (e.g., 'financial', 'litigation')
   */
  id: string;

  /**
   * Agent data containing title, confidence, insights, and evidence
   */
  data: AgentResult;

  /**
   * Optional callback when card is expanded/collapsed
   */
  onToggle?: (isOpen: boolean) => void;

  /**
   * Optional custom styling class
   */
  className?: string;
}

/**
 * AgentCard Component
 * Enterprise-grade card with progressive disclosure pattern
 * - Always visible: Title, Confidence Score, Metadata
 * - Expandable: Detailed Insight, System Evidence
 *
 * Rationale:
 * Progressive disclosure reduces cognitive load for initial scan while
 * maintaining access to detailed evidence for stakeholders who need it.
 * Confidence score provides at-a-glance data quality indicator.
 */
export const AgentCard: React.FC<AgentCardProps> = ({
  id,
  data,
  onToggle,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleToggle = (open: boolean) => {
    setIsOpen(open);
    onToggle?.(open);
  };

  // Format confidence as percentage with visual indicator
  const getConfidenceColor = (score: number): string => {
    if (score >= 80) return 'text-emerald-700';
    if (score >= 60) return 'text-amber-700';
    return 'text-red-700';
  };

  const getConfidenceBgColor = (score: number): string => {
    if (score >= 80) return 'bg-emerald-50';
    if (score >= 60) return 'bg-amber-50';
    return 'bg-red-50';
  };

  return (
    <Collapsible open={isOpen} onOpenChange={handleToggle}>
      <div
        className={`
          border border-slate-200 rounded-lg 
          transition-all duration-200
          ${isOpen ? 'shadow-md' : 'shadow-sm hover:shadow-md'}
          bg-white
          ${className}
        `}
      >
        {/* Header Section - Always Visible */}
        <CollapsibleTrigger asChild>
          <button
            className="
              w-full px-6 py-4
              flex items-center justify-between
              hover:bg-slate-50
              transition-colors duration-150
              group
            "
          >
            {/* Title and Agent ID */}
            <div className="flex items-start gap-4 flex-1 text-left">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-slate-900">
                  {data.title}
                </h3>
                <p className="text-xs text-slate-500 mt-1 uppercase tracking-wide">
                  {id} agent
                </p>
              </div>
            </div>

            {/* Confidence Badge */}
            <div className="flex items-center gap-3">
              <div
                className={`
                  px-3 py-2 rounded-md
                  ${getConfidenceBgColor(data.confidence_score)}
                `}
              >
                <span
                  className={`text-sm font-semibold ${getConfidenceColor(data.confidence_score)}`}
                >
                  {data.confidence_score}%
                </span>
                <p className="text-xs text-slate-600">
                  {data.confidence_score >= 80
                    ? 'High confidence'
                    : data.confidence_score >= 60
                      ? 'Moderate confidence'
                      : 'Lower confidence'}
                </p>
              </div>

              {/* Expand/Collapse Chevron */}
              <ChevronDown
                className={`
                  w-5 h-5 text-slate-400
                  transition-transform duration-200
                  group-hover:text-slate-600
                  ${isOpen ? 'rotate-180' : ''}
                `}
                strokeWidth={2}
              />
            </div>
          </button>
        </CollapsibleTrigger>

        {/* Expandable Content */}
        <CollapsibleContent>
          <div className="border-t border-slate-200 bg-slate-50">
            {/* Detailed Insight Section */}
            <div className="px-6 py-4 border-b border-slate-200">
              <div className="flex items-start gap-3">
                <BookOpen className="w-4 h-4 text-slate-600 mt-1 flex-shrink-0" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-slate-900 mb-2">
                    Detailed Insight
                  </h4>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {data.detailed_insight}
                  </p>
                </div>
              </div>
            </div>

            {/* System Evidence Section */}
            <div className="px-6 py-4">
              <div className="flex items-start gap-3">
                <FileText className="w-4 h-4 text-slate-600 mt-1 flex-shrink-0" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-slate-900 mb-3">
                    System Evidence
                  </h4>

                  {/* Evidence List */}
                  {data.system_evidence && data.system_evidence.length > 0 ? (
                    <ul className="space-y-2">
                      {data.system_evidence.map((evidence, idx) => (
                        <li
                          key={idx}
                          className="flex gap-2 text-sm text-slate-700"
                        >
                          <span className="text-slate-400 flex-shrink-0">
                            •
                          </span>
                          <span>{evidence}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-500 italic">
                      No evidence available
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Metadata Footer (if available) */}
            {data.metadata && (
              <div className="px-6 py-3 border-t border-slate-200 bg-white">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-slate-600">
                  {data.metadata.sources && (
                    <div>
                      <span className="font-semibold text-slate-700">
                        {data.metadata.sources.length}
                      </span>
                      <p className="text-slate-500">Sources</p>
                    </div>
                  )}
                  {data.metadata.data_points && (
                    <div>
                      <span className="font-semibold text-slate-700">
                        {data.metadata.data_points}
                      </span>
                      <p className="text-slate-500">Data Points</p>
                    </div>
                  )}
                  {data.metadata.last_updated && (
                    <div className="col-span-2">
                      <p className="text-slate-500">
                        Updated:{' '}
                        {new Date(
                          data.metadata.last_updated
                        ).toLocaleDateString()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
};

export default AgentCard;
