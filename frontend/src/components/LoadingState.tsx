import { Compass, Globe, Sparkles } from 'lucide-react';

interface LoadingStateProps {
  query: string;
}

export function LoadingState({ query }: LoadingStateProps) {
  return (
    <div className="w-full bg-white border border-slate-200 rounded-xl p-8 sm:p-12 text-center shadow-xs">
      <div className="w-14 h-14 rounded-2xl bg-sky-50 border border-sky-200 text-sky-600 flex items-center justify-center mx-auto mb-5 shadow-xs">
        <Compass className="w-7 h-7 animate-spin" style={{ animationDuration: '3s' }} />
      </div>

      <h3 className="text-lg font-semibold text-slate-900 mb-2">
        Researching your question...
      </h3>

      <div className="max-w-xl mx-auto px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 italic mb-6">
        "{query}"
      </div>

      <p className="text-sm text-slate-500 max-w-md mx-auto mb-6 leading-relaxed">
        ResearchPilot is actively generating targeted search queries, retrieving web articles, extracting text evidence, and cross-referencing citations.
      </p>

      <div className="inline-flex items-center justify-center gap-6 text-xs text-slate-500 border-t border-slate-100 pt-5">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-sky-500" />
          <span>Live Web Search</span>
        </div>
        <div className="w-1 h-1 rounded-full bg-slate-300" />
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-sky-500" />
          <span>Grounded Synthesis</span>
        </div>
      </div>
    </div>
  );
}
