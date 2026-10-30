import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { ResearchInput } from './components/ResearchInput';
import { ExampleQueries } from './components/ExampleQueries';
import { LoadingState } from './components/LoadingState';
import { ErrorDisplay } from './components/ErrorDisplay';
import { ResearchReport } from './components/ResearchReport';
import { ApiClientError, getHealth, submitResearch } from './services/api';
import type { HealthResponse, ResearchDepth, ResearchResponse } from './types/research';

export default function App() {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [report, setReport] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);

  // Health state
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  // Probe backend health once on initial load
  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const data = await getHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const handleSelectExample = (example: string) => {
    setQuery(example);
    setError(null);
  };

  const handleSubmit = async (depth: ResearchDepth = 'standard', maxSources = 5) => {
    const trimmed = query.trim();
    if (trimmed.length < 3 || trimmed.length > 1000 || isLoading) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setReport(null);

    try {
      const result = await submitResearch({
        query: trimmed,
        depth,
        max_sources: maxSources,
      });
      setReport(result);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err);
      } else {
        setError(
          new ApiClientError(
            0,
            err instanceof Error ? err.message : 'An unexpected error occurred during research.',
            'UNEXPECTED_ERROR'
          )
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setReport(null);
    setError(null);
    setQuery('');
  };

  const handleRetry = () => {
    if (query.trim().length >= 3) {
      handleSubmit();
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased selection:bg-sky-100 selection:text-sky-900">
      <Header
        health={health}
        healthLoading={healthLoading}
        onRefreshHealth={checkHealth}
      />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* State 1: Active Research Report */}
        {report && !isLoading && (
          <ResearchReport report={report} onReset={handleReset} />
        )}

        {/* State 2: Active Loading State */}
        {isLoading && (
          <div className="max-w-2xl mx-auto">
            <LoadingState query={query} />
          </div>
        )}

        {/* State 3: Idle Search & Input Screen */}
        {!report && !isLoading && (
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="text-center space-y-2 mb-8">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                Ground your research in verifiable web evidence.
              </h1>
              <p className="text-sm sm:text-base text-slate-500 max-w-xl mx-auto">
                ResearchPilot plans investigations, queries the live web, extracts full article content, and synthesizes source-attributed findings.
              </p>
            </div>

            {/* Error Banner (if retryable error occurred) */}
            {error && (
              <ErrorDisplay
                error={error}
                onDismiss={() => setError(null)}
                onRetry={handleRetry}
              />
            )}

            {/* Primary Research Input */}
            <ResearchInput
              query={query}
              onChangeQuery={setQuery}
              onSubmit={handleSubmit}
              isLoading={isLoading}
            />

            {/* Selectable Example Prompts */}
            <ExampleQueries
              onSelectQuery={handleSelectExample}
              disabled={isLoading}
            />
          </div>
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>ResearchPilot • Citation-Grounded Autonomous Web Research</span>
          <span>FastAPI • React 19 • Tailwind CSS • Vite</span>
        </div>
      </footer>
    </div>
  );
}
