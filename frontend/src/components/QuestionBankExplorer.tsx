import React, { useState, useEffect } from 'react';
import { Database, Filter, ChevronDown, ChevronUp, Star, Shield, HelpCircle } from 'lucide-react';
import { CategoryItem, QuestionItem } from '../types';
import { fetchCategories, fetchQuestions } from '../api';

export const QuestionBankExplorer: React.FC = () => {
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [selectedCat, setSelectedCat] = useState<string>('all');
  const [selectedPersona, setSelectedPersona] = useState<string>('all');
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [expandedQId, setExpandedQId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCategories().then(setCategories).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchQuestions(selectedCat, selectedPersona)
      .then((data) => {
        setQuestions(data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedCat, selectedPersona]);

  const toggleExpand = (id: string) => {
    setExpandedQId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div>
        <div className="flex items-center space-x-2 mb-1">
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20 font-mono">
            47 Curated Items
          </span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
          Curated ISSB Question Bank Browser
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Examine calibrated interview prompts across 13 core psychological and leadership categories.
        </p>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-1.5 pb-2">
        <button
          onClick={() => setSelectedCat('all')}
          className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
            selectedCat === 'all'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/40'
              : 'bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          All Categories ({categories.reduce((acc, c) => acc + c.count, 0)})
        </button>
        {categories.map((c) => (
          <button
            key={c.category}
            onClick={() => setSelectedCat(c.category)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              selectedCat === c.category
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/40'
                : 'bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            {c.label} ({c.count})
          </button>
        ))}
      </div>

      {/* Secondary Persona Filter & Counter */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1 border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <span>Persona Target:</span>
          <select
            value={selectedPersona}
            onChange={(e) => setSelectedPersona(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none"
          >
            <option value="all">All Personas</option>
            <option value="deputy_president">Deputy President</option>
            <option value="psychologist">Psychologist</option>
          </select>
        </div>

        <span className="font-mono">Displaying {questions.length} questions</span>
      </div>

      {/* Questions List */}
      <div className="space-y-3">
        {questions.map((q) => {
          const isExpanded = expandedQId === q.id;
          return (
            <div
              key={q.id}
              className="glass-panel rounded-2xl border border-slate-800 hover:border-slate-700 transition-all overflow-hidden"
            >
              <div
                onClick={() => toggleExpand(q.id)}
                className="p-4 sm:p-5 flex items-start justify-between gap-4 cursor-pointer select-none"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-bold text-xs text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                      {q.id}
                    </span>
                    <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                      {q.category.replace('_', ' ')}
                    </span>
                    <span className="text-slate-600">•</span>
                    <span className="text-[11px] text-amber-400 font-mono">
                      {'⭐'.repeat(q.difficulty)}
                    </span>
                    <span className="text-slate-600">•</span>
                    <span className="text-[11px] text-slate-400">
                      {q.persona === 'both' ? 'Both Personas' : q.persona.replace('_', ' ')}
                    </span>
                  </div>

                  <p className="text-sm sm:text-base font-medium text-white leading-relaxed">
                    {q.question}
                  </p>
                </div>

                <button className="text-slate-400 hover:text-white p-1 flex-shrink-0 mt-1">
                  {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>

              {/* Collapsible Details */}
              {isExpanded && (
                <div className="p-4 sm:p-5 pt-0 border-t border-slate-800/80 bg-slate-900/40 space-y-3 text-xs">
                  <div>
                    <span className="font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Psychometric Assessment Intent:
                    </span>
                    <p className="text-slate-300 italic">{q.intent}</p>
                  </div>

                  {q.follow_up_pool && q.follow_up_pool.length > 0 && (
                    <div>
                      <span className="font-bold text-amber-400 uppercase tracking-wider block mb-1">
                        Calibrated Follow-Up Probes ({q.follow_up_pool.length}):
                      </span>
                      <ul className="space-y-1.5 pl-2">
                        {q.follow_up_pool.map((fu, idx) => (
                          <li key={idx} className="text-slate-300 flex items-start space-x-2">
                            <span className="text-amber-400 font-bold">•</span>
                            <span>{fu}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="pt-2 text-[11px] text-slate-500 font-mono">
                    Evaluation Dimension: <strong className="text-slate-400">{q.evaluation_dimension}</strong>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
