import { Globe, ExternalLink, ShieldCheck } from 'lucide-react';
import type { EvidenceSource } from '../types/research';

interface SourcesListProps {
  sources: EvidenceSource[];
  highlightedSourceId?: string | null;
}

export function SourcesList({ sources, highlightedSourceId }: SourcesListProps) {
  if (!sources || sources.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-5 text-center text-sm text-slate-500 mb-6">
        No external web sources were discovered for this query.
      </div>
    );
  }

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-sky-600" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
            Retrieved Sources ({sources.length})
          </h3>
        </div>
        <span className="text-xs text-slate-400">
          Click links to verify claims at original publisher
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sources.map((source) => {
          const isHighlighted = highlightedSourceId === source.source_id;

          return (
            <div
              key={source.source_id}
              id={`source-${source.source_id}`}
              className={`bg-white border rounded-xl p-4 shadow-2xs transition-all flex flex-col justify-between ${
                isHighlighted
                  ? 'border-sky-500 ring-2 ring-sky-200 bg-sky-50/20'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                    [{source.source_id}]
                  </span>
                  <span className="text-xs font-medium text-slate-400 truncate max-w-[180px]">
                    {source.domain}
                  </span>
                </div>

                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group text-sm font-semibold text-slate-900 hover:text-sky-600 transition-colors flex items-start justify-between gap-1.5 mb-2"
                >
                  <span className="line-clamp-2">{source.title || source.domain}</span>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-sky-600 shrink-0 mt-1" />
                </a>

                {source.snippet && (
                  <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed mb-3">
                    "{source.snippet}"
                  </p>
                )}
              </div>

              {source.credibility_note && (
                <div className="pt-2 border-t border-slate-100 flex items-center gap-1.5 text-[11px] text-slate-500">
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="truncate">{source.credibility_note}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
