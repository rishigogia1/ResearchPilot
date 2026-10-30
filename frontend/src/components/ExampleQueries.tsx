import { Sparkles } from 'lucide-react';

interface ExampleQueriesProps {
  onSelectQuery: (query: string) => void;
  disabled?: boolean;
}

const EXAMPLE_QUERIES = [
  'Compare the top three open-source vector databases for RAG applications.',
  'Research five Indian B2B SaaS startups in HR technology.',
  'Evaluate single-agent versus multi-agent architectures.',
  'Compare approaches to adding memory to AI support agents.',
];

export function ExampleQueries({ onSelectQuery, disabled = false }: ExampleQueriesProps) {
  return (
    <div className="w-full">
      <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 mb-2">
        <Sparkles className="w-3.5 h-3.5 text-sky-600" />
        <span>Example research questions:</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((example, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectQuery(example)}
            className="text-left text-xs bg-white text-slate-700 hover:text-sky-700 hover:bg-sky-50/70 hover:border-sky-300 border border-slate-200 rounded-lg px-3 py-1.5 transition-all shadow-2xs disabled:opacity-50 disabled:pointer-events-none"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
