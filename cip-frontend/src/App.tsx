import { BrowserRouter as Router, Routes, Route, useSearchParams } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnalysisForm } from './components/AnalysisForm';
import Dashboard from './components/Dashboard';

// 1. Re-initialize the TanStack Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000, 
      gcTime: 5 * 60 * 1000, 
      retry: 3,
      retryDelay: (attemptIndex) => Math.pow(2, attemptIndex) * 1000, 
    },
  },
});

// 2. Wrapper component to handle URL params for the Dashboard
function DashboardWrapper() {
  const [searchParams] = useSearchParams();
  
  const runId = searchParams.get('runId') || 'run-123'; 
  const companyName = searchParams.get('company') || 'Acme Corporation';

  return (
    <main className="bg-white">
      <Dashboard
        runId={runId}
        companyName={companyName}
        pollingConfig={{
          polling_interval: 2000,
          max_retries: 5,
        }}
      />
    </main>
  );
}

// 3. Your main App component wrapping everything cleanly
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          {/* Home page: User enters company and country */}
          <Route path="/" element={<AnalysisForm />} />

          {/* Dashboard page */}
          <Route path="/dashboard" element={<DashboardWrapper />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}