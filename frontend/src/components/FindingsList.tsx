import { BookOpen, ExternalLink } from 'lucide-react';
import type { Citation, EvidenceSource, FindingItem } from '../types/research';

interface FindingsListProps {
  findings: FindingItem[];
  citations: Citation[];
  sources: EvidenceSource[];
  onSelectSource?: (sourceId: string) => void;
}

export function FindingsList({ findings, citations, sources, onSelectSource }: FindingsListProps) {
  if (!findings || findings.length === 0) {
    return null;
  }

  const sourceMap = new Map(sources.map((s) => [s.source_id, s]));
  const citationMap = new Map(citations.map((c) => [c.citation_id, c]));

  return (
    <div className="space-y-4 mb-6">
      <div className="flex items-center gap-2 mb-2">
        <BookOpen className="w-4 h-4 text-sky-600" />
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-700">
          Key Findings & Evidence
        </h3>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {findings.map((item, idx) => (
          <div
            key={idx}
            className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-slate-300 transition-all"
          >
            <h4 className="text-base font-semibold text-slate-900 mb-2">
              {item.heading}
            </h4>

            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line mb-3">
              {item.content}
            </p>

            {/* Citations footer */}
            {item.citations && item.citations.length > 0 && (
              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-medium text-slate-400">Sources:</span>
                {item.citations.map((citeId) => {
                  // citeId could be a source_id (src-1) or citation_id (cite-1)
                  const directSource = sourceMap.get(citeId);
                  const linkedCitation = citationMap.get(citeId);
                  const resolvedSource =
                    directSource || (linkedCitation ? sourceMap.get(linkedCitation.source_id) : null);

                  if (resolvedSource) {
                    return (
                      <button
                        key={citeId}
                        type="button"
                        onClick={() => onSelectSource && onSelectSource(resolvedSource.source_id)}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 transition-colors cursor-pointer"
                        title={resolvedSource.title}
                      >
                        <span>[{resolvedSource.source_id}]</span>
                        <span className="max-w-[120px] truncate">{resolvedSource.domain}</span>
                        <ExternalLink className="w-2.5 h-2.5 text-sky-500" />
                      </button>
                    );
                  }

                  // Clear unavailable reference state when citation cannot be resolved
                  return (
                    <span
                      key={citeId}
                      className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-500 border border-slate-200"
                      title="Citation source not found in returned evidence"
                    >
                      [{citeId}] (Unverified)
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
