import React, { useEffect, useState } from 'react';
import { Award } from 'lucide-react';
import { EvaluationReportData, SessionLearningReport } from '../types';
import { getLearningProfile } from '../api';
import { RadarChart } from './RadarChart';

interface EvaluationReportProps {
  report: EvaluationReportData | null;
  onRetake: () => void;
}

interface ActionPlanItem {
  id: string;
  title: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  blueprint: string;
  drills: string[];
}

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
    persona,
    overall_practice_score,
    performance_band,
    dimension_scores,
    formatted_evidence_table,
    radar_chart_data,
    session_metadata,
    growth_areas,
  } = report;

  const evaluatorTitle =
    persona === 'deputy_president' ? 'Deputy President' : 'Senior Psychologist';
  const totalQuestions = formatted_evidence_table?.length || session_metadata?.question_count || 5;
  const sessionId = session_metadata?.session_id || 'demo-zflyotub';

  // Build the 4 Priority Action Plan Cards (matches Lovable screenshot 5)
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
                {/* Background Ring */}
                <circle
                  cx="60"
                  cy="60"
                  r="48"
                  className="stroke-[#152335]"
                  strokeWidth="8"
                  fill="transparent"
                />
                {/* Active Neon Emerald Ring */}
                <circle
                  cx="60"
                  cy="60"
                  r="48"
                  className="stroke-[#00e599] transition-all duration-1000 ease-out"
                  strokeWidth="8"
                  strokeDasharray={2 * Math.PI * 48}
                  strokeDashoffset={2 * Math.PI * 48 * (1 - Math.min(100, Math.max(0, overall_practice_score || 0)) / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              {/* Inner Text */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-3xl font-extrabold font-mono text-white leading-none">
                  {Math.round(overall_practice_score || 0)}
                </span>
                <span className="text-[11px] font-mono tracking-widest text-slate-500 mt-1">
                  / 100
                </span>
              </div>
            </div>

            {/* Middle Narrative Info */}
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
                Assessed by the {evaluatorTitle} across {totalQuestions} questions and five officer-like-quality dimensions. Session {sessionId}.
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

      {/* TAB 1: PRIORITY ACTION PLAN (Image 5) */}
      {activeSection === 'action_plan' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in duration-200">
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
                  {/* Top Bar: 01, 02 ... & Priority Pill */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-500 font-mono text-xs">{item.id}</span>
                    <span
                      className={`font-mono text-[10px] px-2 py-0.5 rounded tracking-wider uppercase font-bold border ${badgeClass}`}
                    >
                      {item.priority}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="text-white font-bold text-base mb-3">{item.title}</h3>

                  {/* Coach Blueprint */}
                  <div className="mb-4">
                    <div className="text-teal-400 font-mono uppercase tracking-widest text-[10px] font-bold mb-1.5">
                      COACH BLUEPRINT
                    </div>
                    <p className="text-slate-300 text-xs leading-relaxed">{item.blueprint}</p>
                  </div>
                </div>

                {/* Practice Drills */}
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
      )}

      {/* TAB 2: COMPETENCY BALANCE (Image 4) */}
      {activeSection === 'competencies' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-in fade-in duration-200">
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

          {/* Right Column: Dimension Scores */}
          <div className="military-card p-6 rounded-lg border border-[#162536] bg-[#0a121d] flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-xs font-mono tracking-widest uppercase text-slate-400 mb-6">
                <div className="w-4 h-[1px] bg-[#00e599]" />
                <span>DIMENSION SCORES</span>
              </div>

              <div className="space-y-6">
                {standardDimensionKeys.map(({ key, label }) => {
                  const score = Math.round(
                    dimension_scores?.[key] ??
                      dimension_scores?.[label] ??
                      (report.dimension_evaluations?.[key]?.dimension_score || 35)
                  );
                  const isPass = score >= 60;

                  return (
                    <div key={key} className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-white font-medium">{label}</span>
                        <span className="font-mono font-bold text-[#00e599]">{score}</span>
                      </div>
                      <div className="w-full bg-[#152335] h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            isPass ? 'bg-[#00e599]' : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.max(5, Math.min(100, score))}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: QUESTION SCORECARD (Image 3) */}
      {activeSection === 'transcript' && (
        <div className="military-card rounded-lg border border-[#162536] bg-[#0a121d] overflow-hidden animate-in fade-in duration-200">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-[#070e17] border-b border-[#162536]">
                <tr className="text-[11px] font-mono tracking-widest text-slate-500 uppercase">
                  <th className="py-3 px-4 w-12">#</th>
                  <th className="py-3 px-4 w-44">DOMAIN</th>
                  <th className="py-3 px-4">QUESTION</th>
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

                    return (
                      <tr key={idx} className="hover:bg-[#0d1826]/50 transition-colors">
                        <td className="py-4 px-4 font-mono text-slate-400">{numStr}</td>
                        <td className="py-4 px-4 text-amber-400 font-medium">{domain}</td>
                        <td className="py-4 px-4 text-slate-300 pr-4 leading-relaxed">
                          {row.Question ||
                            'When was the last time you lost your temper? What triggered it and how did you recover?'}
                        </td>
                        <td className="py-4 px-4">
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
                        <td className="py-4 px-4 text-right font-mono font-bold text-base">
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
      )}
    </div>
  );
};
