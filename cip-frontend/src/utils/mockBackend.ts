// src/utils/mockBackend.ts

export async function mockAnalyze(params: {
  company_name: string;
  country: string;
}): Promise<{ run_id: string }> {
  
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 500));

  // Generate a unique runId based on company and country
  const runId = `run-${params.company_name.toLowerCase().replace(/\s+/g, '-')}-${params.country.toLowerCase()}-${Date.now()}`;

  // In real scenario, this would be stored in database
  // For now, we return a runId
  return { run_id: runId };
}