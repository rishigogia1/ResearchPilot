import { Compass, CheckCircle2, AlertTriangle, XCircle, RefreshCw } from 'lucide-react';
import type { HealthResponse } from '../types/research';

interface HeaderProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
}

export function Header({ health, healthLoading, onRefreshHealth }: HeaderProps) {
  const isOnline = Boolean(health);
  const llmConfigured = health?.services?.llm_configured;
  const tavilyConfigured = health?.services?.tavily_configured;

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shadow-xs">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 tracking-tight text-lg">ResearchPilot</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase bg-slate-100 text-slate-600 border border-slate-200">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-slate-500 font-normal">
              Autonomous AI research workspace grounded in verifiable sources
            </p>
          </div>
        </div>

        {/* Backend Connectivity Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            {healthLoading ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 text-[11px] font-medium border border-slate-200">
                <RefreshCw className="w-3 h-3 animate-spin text-slate-400" />
                Connecting...
              </span>
            ) : isOnline ? (
              <div className="flex items-center gap-2">
                {llmConfigured && tavilyConfigured ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 text-[11px] font-medium border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    Backend Connected
                  </span>
                ) : (
                  <span
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 text-[11px] font-medium border border-amber-200"
                    title={
                      !llmConfigured
                        ? 'LLM API key missing in backend/.env'
                        : 'Tavily API key missing in backend/.env'
                    }
                  >
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    Keys Unconfigured
                  </span>
                )}
              </div>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 text-[11px] font-medium border border-rose-200">
                <XCircle className="w-3.5 h-3.5 text-rose-500" />
                Backend Offline
              </span>
            )}

            <button
              onClick={onRefreshHealth}
              disabled={healthLoading}
              title="Refresh connection status"
              className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              aria-label="Refresh connection"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${healthLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
