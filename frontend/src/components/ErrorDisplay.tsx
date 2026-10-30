import { AlertCircle, Key, Clock, ServerOff, RefreshCw, X } from 'lucide-react';
import { ApiClientError } from '../services/api';

interface ErrorDisplayProps {
  error: ApiClientError;
  onDismiss: () => void;
  onRetry?: () => void;
}

export function ErrorDisplay({ error, onDismiss, onRetry }: ErrorDisplayProps) {
  const isMissingCredentials =
    error.code === 'MISSING_CREDENTIALS' || error.status === 503;
  const isTimeout =
    error.code === 'WORKFLOW_TIMEOUT' || error.status === 504;
  const isOffline =
    error.code === 'NETWORK_ERROR' || error.code === 'BACKEND_OFFLINE' || error.status === 0;

  return (
    <div className="w-full bg-white border border-rose-200 rounded-xl p-5 shadow-xs transition-all">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-rose-50 border border-rose-200 text-rose-600 flex items-center justify-center shrink-0">
            {isMissingCredentials ? (
              <Key className="w-5 h-5 text-amber-600" />
            ) : isTimeout ? (
              <Clock className="w-5 h-5 text-amber-600" />
            ) : isOffline ? (
              <ServerOff className="w-5 h-5 text-rose-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-rose-600" />
            )}
          </div>

          <div>
            <div className="flex items-center gap-2 mb-1">
              <h4 className="text-sm font-semibold text-slate-900">
                {isMissingCredentials
                  ? 'External API Credentials Required'
                  : isTimeout
                  ? 'Research Execution Timed Out'
                  : isOffline
                  ? 'Backend Server Unreachable'
                  : 'Research Execution Failed'}
              </h4>
              <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                {error.code}
              </span>
            </div>

            <p className="text-sm text-slate-600 leading-relaxed mb-3">
              {error.message}
            </p>

            {/* Practical remediation instructions for missing keys */}
            {isMissingCredentials && (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-700 font-mono mb-3">
                <p className="font-sans font-semibold text-slate-800 mb-1.5">
                  How to configure external keys:
                </p>
                <p className="text-slate-600 font-sans mb-1">
                  Create or edit <code className="text-sky-700 font-bold">backend/.env</code> with:
                </p>
                <div className="bg-white p-2 rounded border border-slate-200 text-[11px]">
                  <div>OPENAI_API_KEY=your_openai_key</div>
                  <div>TAVILY_API_KEY=your_tavily_key</div>
                </div>
              </div>
            )}

            {isOffline && (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-700 mb-3">
                <p className="font-semibold text-slate-800 mb-1">FastAPI Start Command:</p>
                <code className="text-sky-700 block bg-white p-2 rounded border border-slate-200 font-mono text-[11px]">
                  cd backend && .venv\Scripts\uvicorn app.main:app --reload --port 8000
                </code>
              </div>
            )}

            {error.requestId && (
              <p className="text-[11px] text-slate-400 font-mono">
                Request ID: {error.requestId}
              </p>
            )}
          </div>
        </div>

        <button
          onClick={onDismiss}
          className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-100 transition-colors"
          aria-label="Dismiss error"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {onRetry && (
        <div className="mt-3 pt-3 border-t border-slate-100 flex justify-end">
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Query</span>
          </button>
        </div>
      )}
    </div>
  );
}
