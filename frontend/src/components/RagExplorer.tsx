import React, { useState, useEffect } from 'react';
import { Search, BookOpen, Shield, GraduationCap, FileText, Globe, Filter, RefreshCw } from 'lucide-react';
import { RagChunk } from '../types';
import { searchRag } from '../api';

export const RagExplorer: React.FC = () => {
  const [query, setQuery] = useState('leadership clear thinking under stress');
  const [sourceType, setSourceType] = useState('all');
  const [preferOfficial, setPreferOfficial] = useState(true);
  const [results, setResults] = useState<RagChunk[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const data = await searchRag(query.trim(), sourceType, preferOfficial, 8);
      setResults(data);
    } catch (err) {
      console.error('RAG Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleSearch();
  }, [sourceType, preferOfficial]);

  const getSourceBadge = (type: string, level: number) => {
    switch (type) {
      case 'official':
        return (
          <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[10px] font-semibold tracking-wider uppercase font-mono flex items-center space-x-1">
            <Shield className="w-3 h-3" />
            <span>Official ISSB (Level {level})</span>
          </span>
        );
      case 'academic':
        return (
          <span className="px-2.5 py-0.5 rounded-full bg-purple-500/15 text-purple-400 border border-purple-500/30 text-[10px] font-semibold tracking-wider uppercase font-mono flex items-center space-x-1">
            <GraduationCap className="w-3 h-3" />
            <span>Academic Theory (Level {level})</span>
          </span>
        );
      case 'evaluation':
        return (
          <span className="px-2.5 py-0.5 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/30 text-[10px] font-semibold tracking-wider uppercase font-mono flex items-center space-x-1">
            <FileText className="w-3 h-3" />
            <span>Rubric Anchor (Level {level})</span>
          </span>
        );
      case 'current_affairs':
        return (
          <span className="px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 text-[10px] font-semibold tracking-wider uppercase font-mono flex items-center space-x-1">
            <Globe className="w-3 h-3" />
            <span>Current Affairs (Level {level})</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-mono">
            Prep Guide (Level {level})
          </span>
        );
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div>
        <div className="flex items-center space-x-2 mb-1">
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20 font-mono">
            Multi-Tier Grounding
          </span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
          RAG Knowledge Base & Provenance Explorer
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Verify factual knowledge grounding, authority tiers, and observable psychometric indicators.
        </p>
      </div>

      {/* Search & Filter Controls */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search doctrine (e.g. 'OLQ guidelines', 'stress regulation', 'economy')..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-900/90 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all placeholder-slate-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-xl transition-all flex items-center space-x-2 shadow-md shadow-emerald-950/30 disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Search</span>
          </button>
        </form>

        {/* Source Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-slate-400 font-medium mr-1 flex items-center space-x-1">
              <Filter className="w-3 h-3" />
              <span>Filter:</span>
            </span>
            {[
              { id: 'all', label: 'All Sources' },
              { id: 'official', label: 'Official ISSB' },
              { id: 'academic', label: 'Academic' },
              { id: 'evaluation', label: 'Rubrics' },
              { id: 'preparation', label: 'Preparation' },
              { id: 'current_affairs', label: 'Current Affairs' },
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setSourceType(f.id)}
                className={`px-3 py-1 rounded-lg transition-all ${
                  sourceType === f.id
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-semibold'
                    : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:text-white'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <label className="flex items-center space-x-2 cursor-pointer text-slate-300">
            <input
              type="checkbox"
              checked={preferOfficial}
              onChange={(e) => setPreferOfficial(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-emerald-500 accent-emerald-500"
            />
            <span className="text-xs">Prioritize Official ISSB</span>
          </label>
        </div>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-400 px-1 font-mono">
          <span>Retrieved Chunks: {results.length}</span>
          <span>Deduplicated & Threshold Filtered</span>
        </div>

        {loading ? (
          <div className="text-center py-12 text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
            <p className="text-xs">Querying knowledge indices...</p>
          </div>
        ) : results.length === 0 ? (
          <div className="glass-panel p-8 rounded-2xl text-center text-slate-400 border border-slate-800">
            <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No knowledge chunks matched this query.</p>
          </div>
        ) : (
          results.map((chunk, i) => (
            <div
              key={i}
              className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3 hover:border-slate-700 transition-colors"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  {getSourceBadge(chunk.source_type, chunk.authority_level)}
                  <h3 className="text-sm font-bold text-white">{chunk.title}</h3>
                </div>
                <div className="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
                  <span>Score: {chunk.score.toFixed(3)}</span>
                  <span>•</span>
                  <span>{chunk.source_file}</span>
                </div>
              </div>

              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans whitespace-pre-line bg-slate-900/40 p-3.5 rounded-xl border border-slate-800/60">
                {chunk.text}
              </p>

              <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                <span>
                  <strong>Topic:</strong> {chunk.topic}
                </span>
                <span className="font-mono text-emerald-400">
                  {chunk.citation}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
