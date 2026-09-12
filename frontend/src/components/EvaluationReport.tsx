import React, { useEffect, useState } from 'react';
import {
  Award,
  CheckCircle,
  AlertTriangle,
  BookOpen,
  Printer,
  ChevronDown,
  ChevronUp,
  Shield,
  Compass,
  Sparkles,
  Target,
  Lightbulb,
} from 'lucide-react';
import { EvaluationReportData, SessionLearningReport } from '../types';
import { getLearningProfile } from '../api';
import { RadarChart } from './RadarChart';

interface EvaluationReportProps {
  report: EvaluationReportData | null;
  onRetake: () => void;
}

const cleanFeedbackText = (text: string): string => {
  if (!text) return '';
  return text
    .replace(/\*\*According to official ISSB guidelines\*\*,?\s*/gi, '')
    .replace(/\*\*Based on the project's behavioral evaluation rubric\*\*,?\s*/gi, '')
    .replace(/According to official ISSB guidelines,?\s*/gi, '')
    .replace(/Based on the project's behavioral evaluation rubric,?\s*/gi, '')
    .trim();
};

export const EvaluationReport: React.FC<EvaluationReportProps> = ({ report, onRetake }) => {
  const [learningReport, setLearningReport] = useState<SessionLearningReport | null>(null);
  const [activeSection, setActiveSection] = useState<'action_plan' | 'competencies' | 'transcript'>('action_plan');

  useEffect(() => {
    if (report?.session_metadata?.session_id) {
      getLearningProfile(report.session_metadata.session_id)
        .then((res) => {
          if (res?.session_learning_report) {
            setLearningReport(res.session_learning_report);
          }
        })
        .catch(() => {});
    }
  }, [report?.session_metadata?.session_id]);

  if (!report) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="w-16 h-16 rounded-2xl bg-slate-800/80 text-slate-400 mx-auto flex items-center justify-center mb-4 border border-slate-700">
          <Award className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">No Active Evaluation Report</h2>
        <p className="text-slate-400 text-sm max-w-md mx-auto mb-6">
          Complete a mock interview in the 'Interview' tab to generate your performance report.
        </p>
        <button
          onClick={onRetake}
          className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-emerald-950/40"
        >
          Begin Mock Interview
        </button>
      </div>
    );
  }

  const {
    candidate_name,
    persona,
    overall_practice_score,
    performance_band,
    dimension_evaluations,
    key_strengths,
    growth_areas,
    formatted_evidence_table,
    radar_chart_data,
    session_metadata,
    preparation_recommendations,
    methodological_disclaimer,
  } = report;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="max-w-4xl mx-auto py-6 px-4 space-y-5">
      {/* Top Header / Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20 font-mono">
              Feedback Report
            </span>
            <span className="text-xs text-slate-500 font-mono">
              Session: {session_metadata?.session_id?.slice(0, 8) || 'Active'}
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-white">
            {candidate_name}
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Evaluator: <span className="text-emerald-400 font-medium">{persona === 'deputy_president' ? 'Deputy President (Board)' : 'Senior Psychologist'}</span> • {session_metadata?.session_date || 'Today'}
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={handlePrint}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-all flex items-center space-x-1.5"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print</span>
          </button>
          <button
            onClick={onRetake}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-emerald-950/30"
          >
            New Interview
          </button>
        </div>
      </div>

      {/* Hero Score Card */}
      <div className="glass-panel p-5 rounded-2xl border border-emerald-500/20 bg-slate-900/80 relative overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-center">
          {/* Main Score Box */}
          <div className="text-center md:text-left md:border-r border-slate-800 md:pr-5">
            <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">
              Practice Score
            </span>
            <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-200 my-1 font-mono">
              {overall_practice_score}%
            </div>
            <div className="inline-block px-3 py-0.5 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              {performance_band?.tier || 'Demonstrated Readiness'}
            </div>
          </div>

          {/* Narrative Summary */}
          <div className="md:col-span-2 space-y-1.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>Assessment Summary</span>
            </h3>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {performance_band?.summary}
            </p>
          </div>
        </div>
      </div>

      {/* Segmented Tab Switcher */}
      <div className="flex items-center justify-between p-1 bg-slate-900/90 rounded-xl border border-slate-800 shadow-sm gap-1">
        <button
          onClick={() => setActiveSection('action_plan')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-2 ${
            activeSection === 'action_plan'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Target className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Priority Action Plan</span>
        </button>

        <button
          onClick={() => setActiveSection('competencies')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-2 ${
            activeSection === 'competencies'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Compass className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Competency Balance</span>
        </button>

        <button
          onClick={() => setActiveSection('transcript')}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-2 ${
            activeSection === 'transcript'
              ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Question Scorecard</span>
        </button>
      </div>

      {/* TAB 1: PRIORITY ACTION PLAN (DEFAULT) */}
      {activeSection === 'action_plan' && (
        <div className="space-y-5 animate-in fade-in duration-150">
          {/* Areas to Improve */}
          <div className="glass-panel p-5 rounded-2xl border border-rose-500/25 bg-slate-900/80 space-y-3.5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
              <div className="flex items-center space-x-2">
                <div className="w-6 h-6 rounded-lg bg-rose-500/20 text-rose-400 flex items-center justify-center border border-rose-500/30">
                  <Target className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    Primary Areas to Improve
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Targeted developmental feedback for your next attempt
                  </p>
                </div>
              </div>
              {learningReport?.recurring_weaknesses && learningReport.recurring_weaknesses.length > 0 && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold">
                  ⚠ {learningReport.recurring_weaknesses.length} Recurring Patterns
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {growth_areas?.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-slate-950/70 border border-rose-500/20 space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-rose-400 flex items-center space-x-1">
                      <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                      <span>Focus #{idx + 1}</span>
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300 font-mono font-bold">
                      Priority
                    </span>
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed pt-0.5">
                    {item}
                  </p>
                </div>
              ))}
            </div>

            {/* Coach Blueprint */}
            {learningReport?.suggested_next_practice_session && (
              <div className="p-3 rounded-xl bg-teal-950/20 border border-teal-500/30 space-y-1">
                <div className="flex items-center space-x-1.5 text-teal-400 text-xs font-bold uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Coach Guidance:</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {learningReport.suggested_next_practice_session}
                </p>
              </div>
            )}
          </div>

          {/* Recommended Practice Steps */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center space-x-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
              <span>Recommended Drills Before Next Mock</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {(preparation_recommendations || []).slice(0, 4).map((rec, idx) => (
                <div key={idx} className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 text-xs text-slate-300 flex items-start space-x-2">
                  <span className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-[10px] flex-shrink-0 font-mono mt-0.5">
                    {idx + 1}
                  </span>
                  <span className="leading-relaxed">{rec}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Action Footer CTA */}
          <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-2xl bg-slate-800/40 border border-slate-700/60 gap-3">
            <span className="text-xs text-slate-300 text-center sm:text-left">
              Ready to implement this feedback in a fresh practice session?
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setActiveSection('competencies')}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-all"
              >
                View Competency Breakdown
              </button>
              <button
                onClick={onRetake}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-emerald-950/30"
              >
                Practice Again Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: COMPETENCIES & RADAR */}
      {activeSection === 'competencies' && (
        <div className="space-y-5 animate-in fade-in duration-150">
          {/* Demonstrated Strengths */}
          <div className="glass-panel p-5 rounded-2xl border border-emerald-500/20 bg-slate-900/70 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Demonstrated Strengths</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {key_strengths?.map((str, i) => (
                <div
                  key={i}
                  className="text-xs text-slate-200 flex items-start space-x-2 bg-emerald-950/20 p-2.5 rounded-xl border border-emerald-500/15"
                >
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{str}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Competency Balance (Radar + Dimension Bars) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Radar Plot */}
            <div className="lg:col-span-5 glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col items-center justify-center">
              <div className="w-full flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                  <Compass className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Competency Balance</span>
                </h3>
                <span className="text-[10px] text-slate-500 font-mono">5 Dimensions</span>
              </div>
              <RadarChart data={radar_chart_data} size={270} />
            </div>

            {/* Dimensions Summary */}
            <div className="lg:col-span-7 glass-panel p-5 rounded-2xl border border-slate-800 space-y-2.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Dimension Scores & Observations
              </h3>
              <div className="space-y-2.5">
                {Object.entries(dimension_evaluations || {}).map(([dimName, item], idx) => {
                  const score = item.dimension_score || 0;
                  const barColor = score >= 75 ? 'bg-emerald-500' : score >= 60 ? 'bg-teal-500' : 'bg-amber-500';
                  return (
                    <div key={idx} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">{dimName}</span>
                        <span className="text-xs font-bold font-mono text-emerald-400">{score}%</span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${barColor} rounded-full transition-all duration-500`}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed pt-0.5">
                        {cleanFeedbackText(item.detailed_feedback)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: QUESTION OBSERVATION SCORECARD */}
      {activeSection === 'transcript' && (
        <div className="space-y-5 animate-in fade-in duration-150">
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 bg-slate-900/70 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
                <span>Per-Question Evaluation Log</span>
              </h3>
              <span className="text-[10px] text-slate-500 font-mono">
                {formatted_evidence_table?.length || 0} Questions Evaluated
              </span>
            </div>

            {/* Table */}
            {formatted_evidence_table && formatted_evidence_table.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500 uppercase font-mono text-[10px]">
                      <th className="py-2 px-2.5">#</th>
                      <th className="py-2 px-2.5">Question ID</th>
                      <th className="py-2 px-2.5">Category</th>
                      <th className="py-2 px-2.5">Dimension</th>
                      <th className="py-2 px-2.5 text-center">Score</th>
                      <th className="py-2 px-2.5">Observed Indicators</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300 text-[11px]">
                    {formatted_evidence_table.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-2 px-2.5 font-mono text-slate-500">{row.No}</td>
                        <td className="py-2 px-2.5 font-mono font-bold text-emerald-400">{row["Question ID"]}</td>
                        <td className="py-2 px-2.5 text-white">{row.Category}</td>
                        <td className="py-2 px-2.5 text-slate-400">{row["Assessed Dimension"]}</td>
                        <td className="py-2 px-2.5 text-center font-mono font-bold text-emerald-400">{row.Score}</td>
                        <td className="py-2 px-2.5 text-slate-300">{row.Indicators}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-slate-400 py-4 text-center">No question evidence records found.</p>
            )}

            {/* Citations Log */}
            <div className="space-y-1.5 pt-2 border-t border-slate-800">
              <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Referenced ISSB Evaluation Standards
              </h4>
              <div className="flex flex-wrap gap-1.5 text-[10px]">
                {Object.values(dimension_evaluations || {}).flatMap((item) => [
                  ...(item.official_citations || []),
                  ...(item.academic_citations || []),
                ]).filter((v, i, a) => a.indexOf(v) === i).map((citation, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400">
                    📜 {citation}
                  </span>
                ))}
              </div>
            </div>

            {/* Methodological Disclaimer */}
            <div className="text-[10px] text-slate-500 leading-relaxed border-t border-slate-800/80 pt-2.5">
              🛡️ {methodological_disclaimer}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

