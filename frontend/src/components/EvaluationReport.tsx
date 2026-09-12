import React, { useEffect, useState } from 'react';
import { Award, RefreshCw, Shield, CheckCircle2, BookOpen, FileText } from 'lucide-react';
import { EvaluationReportData, SessionLearningReport } from '../types';
import { getLearningProfile } from '../api';
import { RadarChart } from './RadarChart';

interface EvaluationReportProps {
  report: EvaluationReportData | null;
  isLoading?: boolean;
  onRetake: () => void;
}

interface ActionPlanItem {
  id: string;
  title: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  blueprint: string;
  drills: string[];
}

const cleanFeedbackText = (text?: string): string => {
  if (!text) return '';
  return text
    .replace(/\*\*According to official ISSB guidelines\*\*,?\s*/gi, '')
    .replace(/\*\*Based on the project's behavioral evaluation rubric\*\*,?\s*/gi, '')
    .replace(/According to official ISSB guidelines,?\s*/gi, '')
    .replace(/Based on the project's behavioral evaluation rubric,?\s*/gi, '')
    .trim();
};

const parseIndicators = (indicatorsStr?: string): string[] => {
  if (!indicatorsStr) return ['SCORED', 'STANDARD'];
  const items = indicatorsStr
    .split(',')
    .map((s) => s.trim().replace(/^[-*]\s*/, ''))
    .filter(Boolean);

  if (items.length === 0) return ['SCORED'];

  return items.slice(0, 2).map((item) => {
    const words = item.split(/\s+/);
    if (words.length > 2) {
      return words.slice(0, 2).join(' ').toUpperCase();
    }
    return item.toUpperCase();
  });
};

const mapDimensionShortName = (name: string): string => {
  if (name.includes('Intellect')) return 'Intellect';
  if (name.includes('Emotional')) return 'Emotional Composure';
  if (name.includes('Social')) return 'Social Adaptability';
  if (name.includes('Communication') || name.includes('Expression')) return 'Expression';
  if (name.includes('Motivation')) return 'Motivation';
  return name;
};

export const EvaluationReport: React.FC<EvaluationReportProps> = ({
  report,
  isLoading = false,
  onRetake,
}) => {
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

  // 1. TACTICAL LOADING STATE
  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4">
        <div className="military-card p-8 sm:p-12 rounded-2xl text-center space-y-6 shadow-2xl border border-[#162536] bg-[#0a121d] relative overflow-hidden">
          {/* Animated radar rings and glowing shield badge */}
          <div className="relative w-24 h-24 mx-auto flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-[#00e599]/30 animate-ping opacity-70" />
            <div className="absolute inset-2 rounded-full border border-[#00e599]/50 animate-pulse" />
            <div className="w-16 h-16 rounded-full bg-[#00e599]/15 border border-[#00e599] flex items-center justify-center shadow-[0_0_25px_rgba(0,229,153,0.35)]">
              <Shield className="w-8 h-8 text-[#00e599] animate-pulse" />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-center space-x-2 text-xs font-mono tracking-widest text-[#00e599] uppercase">
              <span className="w-2 h-2 rounded-full bg-[#00e599] animate-ping" />
              <span>PROCESSING SELECTION BOARD DOSSIER</span>
            </div>
            <h2 className="text-2xl font-bold font-mono text-white tracking-wide">
              Synthesizing Psychometric Performance Report...
            </h2>
            <p className="text-slate-400 text-xs font-mono max-w-md mx-auto leading-relaxed">
              Evaluating candidate responses across 14 Officer-Like Qualities, verifying RAG citations, and deriving structured developmental feedback.
            </p>
          </div>

          {/* Sequential step progress indicators */}
          <div className="space-y-2.5 pt-4 text-left max-w-sm mx-auto border-t border-[#162536]">
            <div className="flex items-center space-x-2.5 text-xs font-mono text-[#00e599]">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>Extracting per-answer evidence & indicators</span>
            </div>
            <div className="flex items-center space-x-2.5 text-xs font-mono text-[#00e599]">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>Computing 14-OLQ psychometric scores</span>
            </div>
            <div className="flex items-center space-x-2.5 text-xs font-mono text-amber-400 animate-pulse">
              <RefreshCw className="w-4 h-4 animate-spin flex-shrink-0" />
              <span>Grounding claims with official ISSB criteria...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 2. EMPTY STATE
  if (!report) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="w-16 h-16 rounded-xl bg-[#0a121d] text-slate-400 mx-auto flex items-center justify-center mb-4 border border-[#162536]">
          <Award className="w-8 h-8 text-[#00e599]" />
        </div>
        <h2 className="text-xl font-bold font-mono tracking-wider text-white uppercase mb-2">
          No Active Evaluation Report
        </h2>
        <p className="text-slate-400 text-xs font-mono max-w-md mx-auto mb-6">
          Complete an interview session in the chamber to generate your comprehensive 5-dimension scorecard.
        </p>
        <button
          onClick={onRetake}
          className="military-btn-emerald px-6 py-3 rounded text-xs font-mono font-bold tracking-wider uppercase transition-all"
        >
          Enter Interview Chamber
        </button>
      </div>
    );
  }

  const {
    candidate_name,
    persona,
    overall_practice_score,
    performance_band,
    dimension_scores,
    dimension_evaluations,
    formatted_evidence_table,
    radar_chart_data,
    session_metadata,
    growth_areas,
    key_strengths,
    methodological_disclaimer,
  } = report;

  const evaluatorTitle =
    persona === 'deputy_president' ? 'Deputy President' : 'Senior Psychologist';
  const totalQuestions = formatted_evidence_table?.length || session_metadata?.question_count || 5;
  const sessionId = session_metadata?.session_id || 'demo-zflyotub';

  // Build the 4 Priority Action Plan Cards
  const defaultActionPlans: ActionPlanItem[] = [
    {
      id: '01',
      title: 'Power of Expression',
      priority: 'HIGH',
      blueprint:
        growth_areas?.[0] ||
        'Speak in complete, deliberate paragraphs. Open with the answer, then justify it.',
      drills: [
        'Record 90-second answers to 5 board questions daily',
        'Read one editorial aloud and summarise it in 3 sentences',
      ],
    },
    {
      id: '02',
      title: 'Structured Reasoning (STAR)',
      priority: 'MEDIUM',
      blueprint:
        growth_areas?.[1] ||
        'Every experiential answer must trace Situation → Task → Action → Result.',
      drills: [
        'Write 10 STAR stories from your own life',
        'Practise compressing each story to 60 seconds',
      ],
    },
    {
      id: '03',
      title: 'First-Person Ownership',
      priority: 'MEDIUM',
      blueprint:
        growth_areas?.[2] ||
        "Own decisions explicitly: 'I decided', 'I accepted responsibility'.",
      drills: [
        "Rewrite past answers replacing 'we' with 'I' where true",
        "Articulate your 'why' for service in under 45 seconds",
      ],
    },
    {
      id: '04',
      title: 'Social Awareness',
      priority: 'LOW',
      blueprint:
        growth_areas?.[3] ||
        'Show how you read and adjust to others without surrendering your position.',
      drills: [
        "Describe 3 conflicts you resolved and the other party's view",
        'Group discussion practice, twice weekly',
      ],
    },
  ];

  // Radar data points mapped to clean 5 dimensions
  const formattedRadarData = (radar_chart_data || []).map((pt) => ({
    ...pt,
    subject: mapDimensionShortName(pt.subject || pt.dimension),
  }));

  // Standard 5 Dimensions list for the right panel
  const standardDimensionKeys = [
    { key: 'Intellect & Reasoning', label: 'Intellect' },
    { key: 'Emotional Composure', label: 'Emotional Composure' },
    { key: 'Social Adaptability & Teamwork', label: 'Social Adaptability' },
    { key: 'Communication & Expression', label: 'Expression' },
    { key: 'Motivation & Integrity', label: 'Motivation' },
  ];

  // Aggregate all unique citations from dimension evaluations
  const allCitations = Object.values(dimension_evaluations || {})
    .flatMap((item) => [...(item.official_citations || []), ...(item.academic_citations || [])])
    .filter((v, i, a) => a.indexOf(v) === i && v.trim().length > 0);

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6">
      {/* Top Header line */}
      <div className="flex items-center space-x-2 text-xs font-mono tracking-widest uppercase text-slate-400 mb-4">
        <div className="w-5 h-[2px] bg-[#00e599]" />
        <span>PERFORMANCE DASHBOARD</span>
      </div>

      {/* Hero Score Card */}
      <div className="military-card p-6 md:p-8 rounded-lg mb-6 border border-[#162536] bg-[#0a121d] relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-center justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-center gap-6 text-center sm:text-left">
            {/* SVG Circular Progress Ring */}
            <div className="relative w-28 h-28 flex-shrink-0 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                <circle
                  cx="60"
                  cy="60"
                  r="48"
                  className="stroke-[#152335]"
                  strokeWidth="8"
                  fill="transparent"
                />
                <circle
                  cx="60"
                  cy="60"
                  r="48"
                  className="stroke-[#00e599] transition-all duration-1000 ease-out"
                  strokeWidth="8"
                  strokeDasharray={2 * Math.PI * 48}
                  strokeDashoffset={
                    2 * Math.PI * 48 * (1 - Math.min(100, Math.max(0, overall_practice_score || 0)) / 100)
                  }
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-3xl font-extrabold font-mono text-white leading-none">
                  {Math.round(overall_practice_score || 0)}
                </span>
                <span className="text-[11px] font-mono tracking-widest text-slate-500 mt-1">
                  / 100
                </span>
              </div>
            </div>

            {/* Narrative Info */}
            <div className="space-y-2">
              <div className="text-[11px] font-mono tracking-widest uppercase text-slate-400">
                OVERALL PRACTICE SCORE · CSAC
              </div>
              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded border border-amber-500/50 bg-amber-500/10 text-amber-400 text-xs font-mono font-semibold">
                  <span>🎖</span>
                  <span>{performance_band?.tier || 'Foundational — Intensive Coaching'}</span>
                </span>
              </div>
              <p className="text-xs text-slate-400 max-w-xl leading-relaxed">
                Candidate <span className="text-white font-medium">{candidate_name}</span> assessed by the {evaluatorTitle} across {totalQuestions} questions and five officer-like-quality dimensions. Session {sessionId}.
              </p>
            </div>
          </div>

          {/* Right Action Button */}
          <div className="flex-shrink-0">
            <button
              onClick={onRetake}
              className="military-btn-emerald px-6 py-3 rounded text-xs font-mono font-bold tracking-wider uppercase flex items-center space-x-2 transition-all"
            >
              <span>⟳</span>
              <span>PRACTICE AGAIN</span>
            </button>
          </div>
        </div>
      </div>

      {/* Segmented Navigation Tabs */}
      <div className="inline-flex p-1 rounded-md bg-[#060b11] border border-[#162536] mb-6">
        <button
          onClick={() => setActiveSection('action_plan')}
          className={`px-4 py-2 text-xs font-mono tracking-wider font-semibold rounded uppercase transition-all ${
            activeSection === 'action_plan'
              ? 'bg-[#00e599] text-black font-bold shadow-[0_0_15px_rgba(0,229,153,0.3)]'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          PRIORITY ACTION PLAN
        </button>
        <button
          onClick={() => setActiveSection('competencies')}
          className={`px-4 py-2 text-xs font-mono tracking-wider font-semibold rounded uppercase transition-all ${
            activeSection === 'competencies'
              ? 'bg-[#00e599] text-black font-bold shadow-[0_0_15px_rgba(0,229,153,0.3)]'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          COMPETENCY BALANCE
        </button>
        <button
          onClick={() => setActiveSection('transcript')}
          className={`px-4 py-2 text-xs font-mono tracking-wider font-semibold rounded uppercase transition-all ${
            activeSection === 'transcript'
              ? 'bg-[#00e599] text-black font-bold shadow-[0_0_15px_rgba(0,229,153,0.3)]'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          QUESTION SCORECARD
        </button>
      </div>

      {/* TAB 1: PRIORITY ACTION PLAN */}
      {activeSection === 'action_plan' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Coach Strategic Directive (if available from learning profile) */}
          {learningReport?.suggested_next_practice_session && (
            <div className="military-card p-5 rounded-lg border border-teal-500/30 bg-teal-950/20 space-y-1.5">
              <div className="flex items-center space-x-2 text-xs font-mono text-teal-400 font-bold uppercase tracking-wider">
                <FileText className="w-3.5 h-3.5" />
                <span>Coach Strategic Directive for Next Session</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {learningReport.suggested_next_practice_session}
              </p>
            </div>
          )}

          {/* 2x2 Grid of Priority Action Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {defaultActionPlans.map((item) => {
              const isHigh = item.priority === 'HIGH';
              const isMed = item.priority === 'MEDIUM';
              const badgeClass = isHigh
                ? 'border-red-500/40 text-red-400 bg-red-500/10'
                : isMed
                ? 'border-amber-500/40 text-amber-400 bg-amber-500/10'
                : 'border-cyan-500/40 text-cyan-400 bg-cyan-500/10';

              return (
                <div
                  key={item.id}
                  className="military-card p-6 rounded-lg border border-[#162536] bg-[#0a121d] flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-slate-500 font-mono text-xs">{item.id}</span>
                      <span
                        className={`font-mono text-[10px] px-2 py-0.5 rounded tracking-wider uppercase font-bold border ${badgeClass}`}
                      >
                        {item.priority}
                      </span>
                    </div>

                    <h3 className="text-white font-bold text-base mb-3">{item.title}</h3>

                    <div className="mb-4">
                      <div className="text-teal-400 font-mono uppercase tracking-widest text-[10px] font-bold mb-1.5">
                        COACH BLUEPRINT
                      </div>
                      <p className="text-slate-300 text-xs leading-relaxed">{item.blueprint}</p>
                    </div>
                  </div>

                  <div>
                    <div className="text-amber-400 font-mono uppercase tracking-widest text-[10px] font-bold mb-2">
                      PRACTICE DRILLS
                    </div>
                    <ul className="space-y-1.5 text-xs text-slate-300">
                      {item.drills.map((drill, dIdx) => (
                        <li key={dIdx} className="flex items-start space-x-2">
                          <span className="text-amber-400 font-bold leading-none mt-1">▪</span>
                          <span className="leading-relaxed">{drill}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: COMPETENCY BALANCE (Radar + Dimension Scores & Comments) */}
      {activeSection === 'competencies' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left Column: 5-Dimension Radar */}
            <div className="military-card p-6 rounded-lg border border-[#162536] bg-[#0a121d]">
              <div className="flex items-center space-x-2 text-xs font-mono tracking-widest uppercase text-slate-400 mb-4">
                <div className="w-4 h-[1px] bg-[#00e599]" />
                <span>5-DIMENSION RADAR</span>
              </div>
              <div className="py-4">
                <RadarChart data={formattedRadarData} size={300} />
              </div>
            </div>

            {/* Right Column: Dimension Scores with Evaluator Comments */}
            <div className="military-card p-6 rounded-lg border border-[#162536] bg-[#0a121d] space-y-4">
              <div className="flex items-center space-x-2 text-xs font-mono tracking-widest uppercase text-slate-400 mb-2">
                <div className="w-4 h-[1px] bg-[#00e599]" />
                <span>DIMENSION SCORES & OBSERVATIONS</span>
              </div>

              <div className="space-y-4">
                {standardDimensionKeys.map(({ key, label }) => {
                  const evalItem = dimension_evaluations?.[key];
                  const score = Math.round(
                    dimension_scores?.[key] ??
                      dimension_scores?.[label] ??
                      (evalItem?.dimension_score || 35)
                  );
                  const isPass = score >= 60;
                  const feedbackText = cleanFeedbackText(evalItem?.detailed_feedback);

                  return (
                    <div key={key} className="space-y-2 p-3.5 rounded-lg bg-[#070e17] border border-[#162536]">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-white font-medium">{label}</span>
                        <span className="font-mono font-bold text-[#00e599]">{score}%</span>
                      </div>

                      {/* Score Bar */}
                      <div className="w-full bg-[#152335] h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            isPass ? 'bg-[#00e599]' : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.max(5, Math.min(100, score))}%` }}
                        />
                      </div>

                      {/* Evaluator Qualitative Comments */}
                      {feedbackText && (
                        <div className="pt-2 border-t border-[#132030] mt-2 space-y-1">
                          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
                            Evaluator Comment:
                          </span>
                          <p className="text-[11px] text-slate-300 leading-relaxed">
                            {feedbackText}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Demonstrated Strengths / Proven Competencies */}
          {key_strengths && key_strengths.length > 0 && (
            <div className="military-card p-6 rounded-lg border border-[#162536] bg-[#0a121d] space-y-3">
              <div className="flex items-center space-x-2 text-xs font-mono tracking-widest uppercase text-slate-400">
                <div className="w-4 h-[1px] bg-[#00e599]" />
                <span>OBSERVED STRENGTHS & NOTABLE INDICATORS</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {key_strengths.map((str, i) => (
                  <div
                    key={i}
                    className="text-xs text-slate-200 flex items-start space-x-2.5 bg-[#0c1624] p-3 rounded-lg border border-[#1e2d42]"
                  >
                    <span className="text-[#00e599] font-bold">✓</span>
                    <span className="leading-relaxed">{str}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: QUESTION SCORECARD & CITATIONS */}
      {activeSection === 'transcript' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Question Evidence Table */}
          <div className="military-card rounded-lg border border-[#162536] bg-[#0a121d] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-[#070e17] border-b border-[#162536]">
                  <tr className="text-[11px] font-mono tracking-widest text-slate-500 uppercase">
                    <th className="py-3 px-4 w-12">#</th>
                    <th className="py-3 px-4 w-44">DOMAIN</th>
                    <th className="py-3 px-4">QUESTION & OBSERVATION</th>
                    <th className="py-3 px-4 w-44">INDICATORS</th>
                    <th className="py-3 px-4 text-right w-20">SCORE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#132030] text-xs">
                  {formatted_evidence_table && formatted_evidence_table.length > 0 ? (
                    formatted_evidence_table.map((row, idx) => {
                      const numStr = String(row.No || idx + 1).padStart(2, '0');
                      const domain =
                        mapDimensionShortName(row['Assessed Dimension'] || '') ||
                        row.Category ||
                        'Emotional Stability';
                      const scoreVal =
                        parseInt(String(row.Score || '0').replace('%', ''), 10) || 36;
                      const indicators = parseIndicators(row.Indicators);
                      const hasWeaknessNote =
                        row.Weaknesses &&
                        row.Weaknesses !== 'None observed' &&
                        row.Weaknesses.trim().length > 0;

                      return (
                        <tr key={idx} className="hover:bg-[#0d1826]/50 transition-colors">
                          <td className="py-4 px-4 font-mono text-slate-400 align-top">{numStr}</td>
                          <td className="py-4 px-4 text-amber-400 font-medium align-top">{domain}</td>
                          <td className="py-4 px-4 text-slate-300 pr-4 leading-relaxed align-top">
                            <div>{row.Question || 'Situational interview question.'}</div>
                            {/* Question Observation / Weakness Feedback */}
                            {hasWeaknessNote && (
                              <div className="text-[11px] text-amber-300/80 font-mono mt-1.5 flex items-start space-x-1.5">
                                <span className="text-amber-400">⚠</span>
                                <span>Note: {row.Weaknesses}</span>
                              </div>
                            )}
                          </td>
                          <td className="py-4 px-4 align-top">
                            <div className="flex flex-wrap gap-1.5">
                              {indicators.map((ind, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 rounded bg-[#0c1624] border border-[#1e2d42] text-[10px] font-mono font-bold tracking-wider text-slate-400 uppercase"
                                >
                                  {ind}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-4 px-4 text-right font-mono font-bold text-base align-top">
                            <span className={scoreVal >= 60 ? 'text-[#00e599]' : 'text-red-500'}>
                              {scoreVal}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500 font-mono text-xs">
                        No question evidence logged for this session.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Citations & Evaluator Standards Dossier */}
          <div className="military-card p-6 rounded-lg border border-[#162536] bg-[#0a121d] space-y-4">
            <div className="flex items-center justify-between border-b border-[#162536] pb-3">
              <div className="flex items-center space-x-2 text-xs font-mono tracking-widest uppercase text-slate-400">
                <div className="w-4 h-[1px] bg-[#00e599]" />
                <span>REFERENCED ISSB STANDARDS & CITATIONS</span>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">
                RAG Standard Grounding
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block mb-2">
                  Official Guidelines & Evaluation Rubrics:
                </span>
                <div className="flex flex-wrap gap-2">
                  {allCitations.length > 0 ? (
                    allCitations.map((citation, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded bg-[#0b1420] border border-[#1e2d42] text-slate-300 font-mono text-[11px] flex items-center space-x-1.5"
                      >
                        <span className="text-[#00e599]">📜</span>
                        <span>{citation}</span>
                      </span>
                    ))
                  ) : (
                    <>
                      <span className="px-2.5 py-1 rounded bg-[#0b1420] border border-[#1e2d42] text-slate-300 font-mono text-[11px] flex items-center space-x-1.5">
                        <span className="text-[#00e599]">📜</span>
                        <span>Official ISSB Candidate Guidelines (GHQ Rawalpindi)</span>
                      </span>
                      <span className="px-2.5 py-1 rounded bg-[#0b1420] border border-[#1e2d42] text-slate-300 font-mono text-[11px] flex items-center space-x-1.5">
                        <span className="text-[#00e599]">📜</span>
                        <span>Project Behavioral Evaluation Rubric (14-OLQ Ground Truth)</span>
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Methodological Disclaimer */}
              <div className="text-[11px] text-slate-400 font-mono leading-relaxed border-t border-[#162536] pt-3">
                <span className="text-[#00e599] font-bold mr-1">🛡️ METHODOLOGICAL DISCLAIMER:</span>
                {methodological_disclaimer ||
                  'Defensible assessment based on observable behavioral indicators across standardized ISSB dimensions. Evaluates practice readiness without false passing guarantees.'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
