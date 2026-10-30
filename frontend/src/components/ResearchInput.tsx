import React, { useState } from 'react';
import { ArrowRight, Search, SlidersHorizontal } from 'lucide-react';
import type { ResearchDepth } from '../types/research';

interface ResearchInputProps {
  query: string;
  onChangeQuery: (value: string) => void;
  onSubmit: (depth: ResearchDepth, maxSources: number) => void;
  isLoading: boolean;
}

export function ResearchInput({
  query,
  onChangeQuery,
  onSubmit,
  isLoading,
}: ResearchInputProps) {
  const [depth, setDepth] = useState<ResearchDepth>('standard');
  const [maxSources, setMaxSources] = useState<number>(5);
  const [showOptions, setShowOptions] = useState<boolean>(false);

  const trimmed = query.trim();
  const isValidLength = trimmed.length >= 3 && trimmed.length <= 1000;
  const isTooShort = query.length > 0 && trimmed.length < 3;
  const isTooLong = trimmed.length > 1000;

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isValidLength && !isLoading) {
      onSubmit(depth, maxSources);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full bg-white rounded-xl border border-slate-200 shadow-sm transition-all focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-100">
      <div className="p-4 sm:p-5">
        <label htmlFor="research-query-input" className="sr-only">
          Research Question
        </label>
        <textarea
          id="research-query-input"
          rows={3}
          value={query}
          onChange={(e) => onChangeQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder="What would you like to research today?"
          className="w-full resize-none text-slate-900 placeholder:text-slate-400 text-sm sm:text-base border-0 focus:outline-hidden focus:ring-0 leading-relaxed disabled:opacity-60"
        />

        {/* Validation Warning */}
        {isTooShort && (
          <p className="text-xs text-amber-600 mt-1">
            Question must be at least 3 characters.
          </p>
        )}
        {isTooLong && (
          <p className="text-xs text-rose-600 mt-1">
            Question exceeds maximum length of 1000 characters ({trimmed.length}/1000).
          </p>
        )}
      </div>

      {/* Control Bar */}
      <div className="px-4 py-3 bg-slate-50/80 border-t border-slate-100 rounded-b-xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowOptions(!showOptions)}
            disabled={isLoading}
            className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg border transition-colors ${
              showOptions
                ? 'bg-sky-50 text-sky-700 border-sky-200'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
            <span>Options</span>
          </button>

          <span className="text-xs text-slate-400 font-mono">
            {trimmed.length}/1000
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-block text-[11px] text-slate-400">
            Press <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-500 text-[10px]">Ctrl</kbd> + <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-500 text-[10px]">Enter</kbd>
          </span>

          <button
            type="submit"
            disabled={!isValidLength || isLoading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 active:bg-sky-800 text-white text-sm font-medium transition-colors shadow-xs disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isLoading ? (
              <>
                <Search className="w-4 h-4 animate-spin" />
                <span>Researching...</span>
              </>
            ) : (
              <>
                <span>Research</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Expandable Options Drawer */}
      {showOptions && (
        <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block font-medium text-slate-700 mb-1">Research Depth</label>
            <div className="flex rounded-lg border border-slate-200 bg-white p-0.5">
              {(['quick', 'standard', 'deep'] as ResearchDepth[]).map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDepth(d)}
                  className={`flex-1 py-1 px-2 rounded-md font-medium capitalize text-center transition-colors ${
                    depth === d
                      ? 'bg-sky-600 text-white shadow-2xs'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              {depth === 'quick' && '1-2 search queries for fast verification'}
              {depth === 'standard' && '2-3 targeted search queries'}
              {depth === 'deep' && 'Up to 5 in-depth queries across sources'}
            </p>
          </div>

          <div>
            <label className="block font-medium text-slate-700 mb-1">Max Sources to Explore</label>
            <div className="flex rounded-lg border border-slate-200 bg-white p-0.5">
              {[3, 5, 10].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => setMaxSources(num)}
                  className={`flex-1 py-1 px-2 rounded-md font-medium text-center transition-colors ${
                    maxSources === num
                      ? 'bg-sky-600 text-white shadow-2xs'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {num} Sources
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Limits the number of external web documents scraped and analyzed.
            </p>
          </div>
        </div>
      )}
    </form>
  );
}
