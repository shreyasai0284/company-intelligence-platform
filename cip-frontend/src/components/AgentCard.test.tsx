/**
 * components/AgentCard.test.tsx
 * Example unit tests for AgentCard component
 * Shows patterns for testing React components with Vitest
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AgentCard } from './AgentCard';
import { AgentResult } from '../types';

describe('AgentCard', () => {
  const mockData: AgentResult = {
    title: 'Financial Analysis',
    confidence_score: 92,
    detailed_insight: 'Strong revenue growth driven by enterprise customers.',
    system_evidence: ['Q4 2023 earnings: $250M', 'YoY growth: +15%'],
    metadata: {
      sources: ['SEC EDGAR', 'Financial News'],
      data_points: 15,
      last_updated: '2024-01-15T10:30:00Z',
    },
  };

  it('renders card with title and confidence score', () => {
    render(<AgentCard id="financial" data={mockData} />);

    expect(screen.getByText('Financial Analysis')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('financial agent')).toBeInTheDocument();
  });

  it('does not show detailed insight initially', () => {
    render(<AgentCard id="financial" data={mockData} />);

    expect(screen.queryByText('Detailed Insight')).not.toBeInTheDocument();
    expect(screen.queryByText(/Strong revenue growth/)).not.toBeInTheDocument();
  });

  it('expands to show detailed insight on click', async () => {
    const user = userEvent.setup();
    render(<AgentCard id="financial" data={mockData} />);

    const trigger = screen.getByRole('button');

    // Wrapped in act to handle async animation/state updates
    await act(async () => {
      await user.click(trigger);
    });

    expect(screen.getByText('Detailed Insight')).toBeInTheDocument();
    expect(screen.getByText(/Strong revenue growth/)).toBeInTheDocument();
  });

  it('shows system evidence when expanded', async () => {
    const user = userEvent.setup();
    render(<AgentCard id="financial" data={mockData} />);

    const trigger = screen.getByRole('button');

    await act(async () => {
      await user.click(trigger);
    });

    expect(screen.getByText('System Evidence')).toBeInTheDocument();
    expect(screen.getByText(/Q4 2023 earnings/)).toBeInTheDocument();
    expect(screen.getByText(/YoY growth/)).toBeInTheDocument();
  });

  it('shows metadata footer when data available', async () => {
    const user = userEvent.setup();
    render(<AgentCard id="financial" data={mockData} />);

    const trigger = screen.getByRole('button');

    await act(async () => {
      await user.click(trigger);
    });

    expect(screen.getByText('2')).toBeInTheDocument(); // 2 sources
    expect(screen.getByText('15')).toBeInTheDocument(); // 15 data points
  });

  it('applies correct confidence color classes', () => {
    const { container } = render(<AgentCard id="financial" data={mockData} />);

    const badge = container.querySelector('.bg-emerald-50');
    expect(badge).toBeInTheDocument();
  });

  it('applies warning color for moderate confidence', () => {
    const moderateData: AgentResult = {
      ...mockData,
      confidence_score: 65,
    };

    const { container } = render(
      <AgentCard id="financial" data={moderateData} />
    );

    const badge = container.querySelector('.bg-amber-50');
    expect(badge).toBeInTheDocument();
  });

  it('applies error color for low confidence', () => {
    const lowData: AgentResult = {
      ...mockData,
      confidence_score: 45,
    };

    const { container } = render(<AgentCard id="financial" data={lowData} />);

    const badge = container.querySelector('.bg-red-50');
    expect(badge).toBeInTheDocument();
  });

  it('calls onToggle callback when expanded/collapsed', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<AgentCard id="financial" data={mockData} onToggle={onToggle} />);

    const trigger = screen.getByRole('button');

    // Expand
    await act(async () => {
      await user.click(trigger);
    });
    expect(onToggle).toHaveBeenCalledWith(true);

    // Collapse
    await act(async () => {
      await user.click(trigger);
    });
    expect(onToggle).toHaveBeenCalledWith(false);
  });

  it('handles empty system evidence gracefully', () => {
    const noEvidenceData: AgentResult = {
      ...mockData,
      system_evidence: [],
    };

    render(<AgentCard id="financial" data={noEvidenceData} />);

    expect(screen.getByText('Financial Analysis')).toBeInTheDocument();
  });

  it('displays chevron icon and rotates on expand', async () => {
    const user = userEvent.setup();
    const { container } = render(<AgentCard id="financial" data={mockData} />);

    const chevron = container.querySelector('svg');
    expect(chevron).toHaveClass('text-slate-400');

    const trigger = screen.getByRole('button');

    await act(async () => {
      await user.click(trigger);
    });

    expect(chevron).toHaveClass('rotate-180');
  });

  it('applies custom className prop', () => {
    const { container } = render(
      <AgentCard id="financial" data={mockData} className="custom-class" />
    );

    const cardDiv = container.querySelector('.custom-class');
    expect(cardDiv).toBeInTheDocument();
  });
});
