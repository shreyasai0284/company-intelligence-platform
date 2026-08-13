import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { submitAnalysis } from '../utils/api';

export function AnalysisForm() {
  const navigate = useNavigate();
  const [company, setCompany] = useState('');
  const [country, setCountry] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const countries = [
    'United States',
    'United Kingdom',
    'India',
    'Canada',
    'Germany',
    'France',
    'Australia',
    'Japan',
    'China',
    'Brazil'
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!company.trim()) {
      setError('Please enter a company name');
      return;
    }

    if (!country) {
      setError('Please select a country');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      const result = await submitAnalysis({
        company_name: company.trim(),
        country,
      });

      const params = new URLSearchParams({
        runId: result.run_id || 'local-run',
        company: company.trim(),
        country,
      });

      // Redirect the user to the dashboard with the run details in the URL string.
      // The dashboard should rely on the backend response for the latest report text.
      navigate(`/dashboard?${params.toString()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong triggering the analysis.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            Company Intelligence Analysis
          </h1>
          <p className="text-slate-600">
            Enter a company and country to analyze
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* Company Input */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Company Name
            </label>
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g., Apple, Google, Microsoft"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            />
          </div>

          {/* Country Dropdown */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Country
            </label>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            >
              <option value="">Select a country...</option>
              {countries.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-3 px-4 rounded-lg font-semibold text-white transition ${
              isLoading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
            }`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                Analyzing...
              </span>
            ) : (
              'Start Analysis'
            )}
          </button>
        </form>

      </div>
    </div>
  );
}