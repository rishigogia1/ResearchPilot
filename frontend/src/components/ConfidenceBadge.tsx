import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react';
import type { ConfidenceScore } from '../types/research';

interface ConfidenceBadgeProps {
  confidence: ConfidenceScore;
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const level = confidence.level.toLowerCase();

  let badgeColor = 'bg-slate-100 text-slate-700 border-slate-200';
  let Icon = Shield;

  if (level === 'high') {
    badgeColor = 'bg-emerald-50 text-emerald-800 border-emerald-200';
    Icon = ShieldCheck;
  } else if (level === 'medium') {
    badgeColor = 'bg-amber-50 text-amber-800 border-amber-200';
    Icon = Shield;
  } else if (level === 'low') {
    badgeColor = 'bg-rose-50 text-rose-800 border-rose-200';
    Icon = ShieldAlert;
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Source Confidence Assessment
        </span>
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold capitalize border ${badgeColor}`}
        >
          <Icon className="w-3.5 h-3.5" />
          <span>{confidence.level} Confidence</span>
        </span>
      </div>

      <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
        {confidence.explanation}
      </p>
    </div>
  );
}
