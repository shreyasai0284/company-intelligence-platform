/**
 * HeroSection.tsx
 * Prominent display area for executive summary
 * Establishes visual hierarchy and scanning pattern for enterprise users
 */

import React from 'react';
import { Sparkles } from 'lucide-react';

interface HeroSectionProps {
  /**
   * The executive summary text
   */
  summary: string;

  /**
   * Company or entity name for context
   */
  title?: string;

  /**
   * Date of the report
   */
  generatedAt?: string;

  /**
   * Custom className for styling
   */
  className?: string;
}

/**
 * HeroSection Component
 * Enterprise-grade hero section following "clean dashboard" aesthetic
 * - Ample whitespace around content
 * - Clear visual separation from cards below
 * - Subtle visual interest (icon, soft gradient) without distraction
 * - Large, readable typography
 *
 * Design rationale:
 * The executive summary is the entry point for stakeholders.
 * It needs visual dominance without being loud or distracting.
 * Soft gradient background and icon provide visual interest while
 * maintaining professional appearance.
 */
export const HeroSection: React.FC<HeroSectionProps> = ({
  summary,
  title,
  generatedAt,
  className = '',
}) => {
  return (
    <div
      className={`
        relative mb-12
        ${className}
      `}
    >
      {/* Background decoration: subtle gradient */}
      <div
        className="
          absolute inset-0 -z-10
          bg-gradient-to-br from-blue-50 via-white to-slate-50
          rounded-lg
        "
      />

      <div className="px-8 py-10">
        {/* Header with icon */}
        <div className="flex items-start gap-4 mb-6">
          <div
            className="
              p-3 bg-blue-100 rounded-lg
              flex-shrink-0
            "
          >
            <Sparkles className="w-5 h-5 text-blue-700" strokeWidth={2} />
          </div>

          <div className="flex-1">
            {title && (
              <h1 className="text-2xl font-bold text-slate-900 mb-1">
                {title}
              </h1>
            )}
            <p className="text-xs uppercase tracking-widest text-slate-500 font-semibold">
              Executive Summary
            </p>
          </div>
        </div>

        {/* Summary text with enterprise typography */}
        <p
          className="
            text-lg leading-relaxed text-slate-700
            font-normal
            max-w-3xl
            mb-6
          "
        >
          {summary}
        </p>

        {/* Metadata footer */}
        {generatedAt && (
          <div className="pt-4 border-t border-slate-200">
            <p className="text-xs text-slate-500">
              Generated on{' '}
              {new Date(generatedAt).toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Empty state hero for when summary is not yet available
 */
export const HeroSectionSkeleton: React.FC = () => {
  return (
    <div className="mb-12 px-8 py-10">
      {/* Header skeleton */}
      <div className="flex items-start gap-4 mb-6">
        <div className="w-12 h-12 bg-slate-200 rounded-lg animate-pulse flex-shrink-0" />
        <div className="flex-1">
          <div className="h-7 bg-slate-200 rounded-md w-48 mb-2 animate-pulse" />
          <div className="h-4 bg-slate-100 rounded w-32 animate-pulse" />
        </div>
      </div>

      {/* Text skeleton */}
      <div className="space-y-3 max-w-3xl mb-6">
        <div className="h-6 bg-slate-200 rounded-md animate-pulse" />
        <div className="h-6 bg-slate-200 rounded-md animate-pulse w-5/6" />
        <div className="h-6 bg-slate-200 rounded-md animate-pulse w-4/5" />
      </div>

      {/* Footer skeleton */}
      <div className="pt-4 border-t border-slate-200">
        <div className="h-4 bg-slate-100 rounded w-48 animate-pulse" />
      </div>
    </div>
  );
};
