import { Table } from 'lucide-react';
import type { FindingItem } from '../types/research';

interface ComparisonTableProps {
  findings: FindingItem[];
  query: string;
}

interface ParsedTable {
  headers: string[];
  rows: string[][];
}

/**
 * Extracts Markdown-style tables from findings text if present.
 */
function extractMarkdownTable(text: string): ParsedTable | null {
  const lines = text.split('\n').map((l) => l.trim());
  const tableLines = lines.filter((l) => l.startsWith('|') && l.endsWith('|'));

  if (tableLines.length >= 3) {
    // Header
    const headers = tableLines[0]
      .slice(1, -1)
      .split('|')
      .map((h) => h.trim());

    // Skip separator line (line 1 with dashes)
    const rows = tableLines.slice(2).map((rowLine) =>
      rowLine
        .slice(1, -1)
        .split('|')
        .map((cell) => cell.trim())
    );

    if (headers.length >= 2 && rows.length > 0) {
      return { headers, rows };
    }
  }
  return null;
}

export function ComparisonTable({ findings, query }: ComparisonTableProps) {
  // Check if query or findings contain comparison intent
  const isComparisonQuery = /\b(compare|versus|vs|comparison|differences|benchmark)\b/i.test(query);

  // Look for markdown tables in findings
  for (const finding of findings) {
    const parsed = extractMarkdownTable(finding.content);
    if (parsed) {
      return (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Table className="w-4 h-4 text-sky-600" />
            <h4 className="text-sm font-semibold text-slate-900">
              {finding.heading || 'Comparative Analysis Matrix'}
            </h4>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left text-slate-700 border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  {parsed.headers.map((h, i) => (
                    <th key={i} className="py-2.5 px-3 font-semibold text-slate-800">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {parsed.rows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50/70 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="py-2.5 px-3">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }
  }

  // If query is comparative and we have 2+ findings with distinct headings, render structured comparison grid
  if (isComparisonQuery && findings.length >= 2) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Table className="w-4 h-4 text-sky-600" />
          <h4 className="text-sm font-semibold text-slate-900">Comparative Breakdown</h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left text-slate-700 border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="py-2.5 px-3 font-semibold text-slate-800 w-1/4">Aspect / Entity</th>
                <th className="py-2.5 px-3 font-semibold text-slate-800 w-3/4">Key Observed Characteristics</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {findings.map((f, idx) => (
                <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3 px-3 font-medium text-slate-900 align-top">{f.heading}</td>
                  <td className="py-3 px-3 text-slate-600 leading-relaxed align-top">{f.content}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // Do not render empty table when research question does not require comparison
  return null;
}
