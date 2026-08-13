export const MOCK_STATUS_RESPONSE = {
  run_id: 'run-demo-001',
  status: 'COMPLETED' as const,
  progress: 100,
  executive_summary: `
    Strong financial performance driven by enterprise customer growth.
    Revenue increased 15% YoY with improved margins. Leadership team
    expansion supports international expansion plans.
  `,
  agent_results: {
    financial: {
      title: 'Financial Analysis',
      confidence_score: 92,
      detailed_insight:
        'Q4 2023 earnings exceeded expectations with $250M in revenue. Enterprise segment grew 18% YoY.',
      system_evidence: [
        'Q4 2023 earnings: $250M (↑15% YoY)',
        'Gross margin: 68% (↑2% YoY)',
        'Enterprise ARR: $180M (↑18% YoY)',
        'Customer retention: 98%',
      ],
      metadata: {
        sources: ['SEC EDGAR', 'Earnings Call Transcript'],
        data_points: 15,
        last_updated: new Date().toISOString(),
      },
    },
    litigation: {
      title: 'Litigation & Legal',
      confidence_score: 88,
      detailed_insight:
        'No material pending litigation. 3 minor regulatory inquiries, all routine. IP portfolio strong with 150+ patents.',
      system_evidence: [
        'No material lawsuits pending',
        '3 routine regulatory inquiries (FDA)',
        '150+ patents filed',
        'No recalled products',
      ],
      metadata: {
        sources: ['SEC Filings', 'Legal Database'],
        data_points: 8,
        last_updated: new Date().toISOString(),
      },
    },
    leadership: {
      title: 'Leadership & Management',
      confidence_score: 85,
      detailed_insight:
        'CEO in role for 8 years with strong track record. CFO hired 2 years ago from Fortune 500. Board has 60% independent directors.',
      system_evidence: [
        'CEO: John Smith (8 years tenure)',
        'CFO: Jane Doe (ex-Fortune 500)',
        'Board: 6 independent, 4 executive directors',
        'Executive comp: Within industry benchmarks',
      ],
      metadata: {
        sources: ['SEC Proxy', 'Company Website'],
        data_points: 12,
        last_updated: new Date().toISOString(),
      },
    },
    product: {
      title: 'Product & Technology',
      confidence_score: 90,
      detailed_insight:
        'Market-leading product with 40% feature lead over competitors. R&D investment at 18% of revenue. Strong security posture.',
      system_evidence: [
        'Product NPS: 72 (industry avg: 55)',
        'R&D: 18% of revenue',
        'SOC 2 Type II certified',
        '99.99% uptime SLA',
      ],
      metadata: {
        sources: ['Product Analysis', 'Security Audit'],
        data_points: 10,
        last_updated: new Date().toISOString(),
      },
    },
  },
  created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 min ago
  completed_at: new Date().toISOString(),
};
