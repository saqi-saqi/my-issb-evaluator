import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  TrendingUp,
  Target,
  Lightbulb,
  Award,
  ChevronRight,
  ShieldAlert,
  Layers,
  FileCheck,
} from 'lucide-react';
import {
  BeforeAfterComparison,
  ImprovementArea,
  LearningPhaseResult,
  StrengthItem,
} from '../types';
import { submitRetryAnswer } from '../api';

interface LearningPhaseCardProps {
  sessionId: string;
  questionId: string;
  questionText: string;
  learningData: LearningPhaseResult;
  onProceed: () => void;
  onRetryComplete?: (comparison: BeforeAfterComparison) => void;
}

export const LearningPhaseCard: React.FC<LearningPhaseCardProps> = ({
  sessionId,
  questionId,
  questionText,
  learningData,
  onProceed,
  onRetryComplete,
}) => {
  const [retryInput, setRetryInput] = useState('');
  const [submittingRetry, setSubmittingRetry] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<BeforeAfterComparison | null>(null);
  const [currentLearning, setCurrentLearning] = useState<LearningPhaseResult>(learningData);

  const handleRetrySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!retryInput.trim() || submittingRetry) return;

    setSubmittingRetry(true);
    setRetryError(null);

    try {
      const res = await submitRetryAnswer(sessionId, questionId, retryInput.trim());
      if (res?.before_after) {
        setComparisonResult(res.before_after);
      }
      if (res?.new_learning) {
        setCurrentLearning(res.new_learning);
      }
      if (onRetryComplete && res?.before_after) {
        onRetryComplete(res.before_after);
      }
    } catch (err: any) {
      setRetryError(err.message || 'Failed to evaluate retry answer.');
    } finally {
      setSubmittingRetry(false);
    }
  };

  const getPriorityBadge = (priority: string = 'MEDIUM') => {
    switch (priority?.toUpperCase()) {
      case 'HIGH':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center space-x-1">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse"></span>
            <span>High Priority</span>
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30">
            Medium Priority
          </span>
        );
      case 'LOW':
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-sky-500/10 text-sky-400 border border-sky-500/30">
            Low Priority
          </span>
        );
    }
  };

  const strengths = currentLearning?.strengths || [];
  const improvementAreas = currentLearning?.improvement_areas || [];

  return (
    <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-emerald-500/30 bg-slate-900/90 shadow-2xl space-y-6 my-6 relative overflow-hidden">
      {/* Decorative gradient glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono text-xs font-bold border border-emerald-500/40 flex items-center space-x-1">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400 mr-1 inline" />
              AI ISSB Coach
            </span>
            <span className="text-xs text-slate-400">Interactive Learning & Improvement</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Personalized Coaching & Practice Loop
          </h2>
        </div>

        <button
          onClick={onProceed}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-semibold rounded-xl border border-slate-700 transition-all flex items-center space-x-2 self-start sm:self-auto"
        >
          <span>Continue Question Flow</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Overall Assessment Banner */}
      <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/80 text-sm text-slate-300 leading-relaxed">
        <div className="flex items-start space-x-3">
          <Lightbulb className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-slate-100 mb-1">Coach Observation</p>
            <p>{currentLearning?.overall_assessment || 'Response evaluated. Follow the coaching guidance below to strengthen your expression.'}</p>
          </div>
        </div>
      </div>

      {/* Strengths Section */}
      {strengths.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center space-x-1.5">
            <CheckCircle className="w-4 h-4" />
            <span>What You Did Well (Strengths Observed)</span>
          </h3>

          <div className="grid grid-cols-1 gap-3">
            {strengths.map((str, idx) => {
              const area = typeof str === 'string' ? 'Observed Trait' : (str?.area || 'Observed Trait');
              const obs = typeof str === 'string' ? str : (str?.observation || '');
              const reinf = typeof str === 'object' ? str?.reinforcement : '';
              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/20 text-sm space-y-1.5"
                >
                  <div className="flex items-center space-x-2 font-semibold text-emerald-300">
                    <Award className="w-4 h-4 text-emerald-400" />
                    <span>{area}</span>
                  </div>
                  <p className="text-slate-300 text-xs">{obs}</p>
                  {reinf && (
                    <p className="text-xs text-slate-400 italic pt-1 border-t border-emerald-900/40">
                      {reinf}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Improvement Areas Section */}
      {improvementAreas.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-rose-400 flex items-center space-x-1.5">
            <Target className="w-4 h-4" />
            <span>Targeted Improvement Areas</span>
          </h3>

          <div className="space-y-4">
            {improvementAreas.map((ia, idx) => (
              <div
                key={idx}
                className="p-5 rounded-xl bg-slate-800/40 border border-slate-700 space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-bold text-white">{ia?.area || 'Improvement Area'}</span>
                    {getPriorityBadge(ia?.priority)}
                  </div>
                  {ia?.evidence_ids && ia.evidence_ids.length > 0 && (
                    <span className="text-xs font-mono text-slate-500">
                      Grounded: {ia.evidence_ids.join(', ')}
                    </span>
                  )}
                </div>

                <div className="text-xs space-y-2 text-slate-300">
                  {ia?.problem && (
                    <p>
                      <strong className="text-slate-400">The Problem:</strong> {ia.problem}
                    </p>
                  )}
                  {ia?.why_it_matters && (
                    <p>
                      <strong className="text-slate-400">Why It Matters:</strong> {ia.why_it_matters}
                    </p>
                  )}
                  {ia?.how_to_improve && (
                    <p className="text-emerald-300">
                      <strong className="text-emerald-400">How to Improve:</strong> {ia.how_to_improve}
                    </p>
                  )}
                </div>

                {ia?.technique && (
                  <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-700/60 text-xs font-mono text-teal-300">
                    <span className="text-slate-500 block mb-0.5 uppercase tracking-wider text-[10px]">
                      Practical Technique Formula:
                    </span>
                    {ia.technique}
                  </div>
                )}

                {ia?.example_structure && (
                  <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-400 font-mono">
                    <span className="text-slate-500 block mb-1 uppercase tracking-wider text-[10px]">
                      Recommended Structure (Template Only):
                    </span>
                    <pre className="whitespace-pre-wrap font-sans text-xs text-slate-300">
                      {ia.example_structure}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Live Before vs After Comparison Card (if candidate retried) */}
      {comparisonResult && (
        <div className="p-5 rounded-xl bg-gradient-to-br from-emerald-950/40 to-slate-900 border border-emerald-500/40 space-y-4">
          <div className="flex items-center justify-between border-b border-emerald-800/40 pb-3">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              <h4 className="text-sm font-bold text-white">Before vs After Comparison</h4>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold font-mono ${
                (comparisonResult?.change || 0) > 0
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : (comparisonResult?.change || 0) === 0
                  ? 'bg-slate-700 text-slate-300'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
              }`}
            >
              {(comparisonResult?.change || 0) > 0 ? `+${comparisonResult.change}` : (comparisonResult?.change ?? 0)} Points
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {comparisonResult?.explanation || 'Attempt evaluated against observable indicators.'}
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase font-mono">Initial Score</span>
              <span className="text-sm font-bold text-slate-300 font-mono">
                {comparisonResult?.previous_score ?? '-'}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase font-mono">Revised Score</span>
              <span className="text-sm font-bold text-emerald-400 font-mono">
                {comparisonResult?.new_score ?? '-'}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase font-mono">Words (Before / After)</span>
              <span className="text-sm font-bold text-slate-300 font-mono">
                {comparisonResult?.metrics?.before?.word_count ?? '-'} / {comparisonResult?.metrics?.after?.word_count ?? '-'}
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase font-mono">Improved Areas</span>
              <span className="text-sm font-bold text-emerald-400 font-mono">
                {comparisonResult?.improved_areas?.length ?? 0}
              </span>
            </div>
          </div>

          {comparisonResult?.improved_areas && comparisonResult.improved_areas.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-xs text-slate-400 mr-1">Verified Improvements:</span>
              {comparisonResult.improved_areas.map((area, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-medium border border-emerald-500/30 flex items-center space-x-1"
                >
                  <CheckCircle className="w-3 h-3 text-emerald-400 mr-1 inline" />
                  <span>{area}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Practice / Retry Input Box */}
      <div className="p-5 rounded-xl bg-slate-800/50 border border-emerald-500/20 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <RefreshCw className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-white">
              Practice Task: Refine Your Answer
            </h4>
          </div>
          <span className="text-xs text-emerald-400 font-medium">
            Target: {currentLearning?.retry?.target_area || 'Clarity & Ownership'}
          </span>
        </div>

        <p className="text-xs text-slate-300">
          {currentLearning?.retry?.instruction || 'Revise your response applying the suggested technique.'}
        </p>

        <form onSubmit={handleRetrySubmit} className="space-y-3 pt-1">
          <textarea
            rows={3}
            value={retryInput}
            onChange={(e) => setRetryInput(e.target.value)}
            placeholder="Type your improved response here using first-person ownership and specific concrete examples..."
            className="w-full rounded-xl bg-slate-950/80 border border-slate-700/80 p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-all resize-none font-sans"
          />

          {retryError && (
            <div className="text-xs text-rose-400 flex items-center space-x-1">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>{retryError}</span>
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-mono">
              {retryInput.trim().split(/\s+/).filter(Boolean).length} words
            </span>

            <div className="flex items-center space-x-3">
              <button
                type="submit"
                disabled={!retryInput.trim() || submittingRetry}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-semibold rounded-xl text-xs transition-all flex items-center space-x-1.5 shadow-md shadow-emerald-950/30"
              >
                {submittingRetry ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Evaluating Retry...</span>
                  </>
                ) : (
                  <>
                    <FileCheck className="w-3.5 h-3.5" />
                    <span>Evaluate Revised Answer</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={onProceed}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-all flex items-center space-x-1"
              >
                <span>Proceed</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Disclaimer */}
      <p className="text-[11px] text-slate-500 italic text-center pt-2">
        {currentLearning?.disclaimer || 'Formative practice guidance generated from observable indicators. Not an official board evaluation.'}
      </p>
    </div>
  );
};
