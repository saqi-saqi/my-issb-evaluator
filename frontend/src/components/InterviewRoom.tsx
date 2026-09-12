import React, { useState } from 'react';
import {
  Play,
  Send,
  Sparkles,
  User,
  Shield,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  ChevronRight,
  RefreshCw,
  Award,
} from 'lucide-react';
import {
  AnswerResponse,
  LearningPhaseResult,
  StartInterviewResponse,
} from '../types';
import { getLearningFeedback, startInterview, submitAnswer, submitFollowUp } from '../api';
import { LearningPhaseCard } from './LearningPhaseCard';

interface InterviewRoomProps {
  onSessionComplete: (sessionId: string) => void;
}

export const InterviewRoom: React.FC<InterviewRoomProps> = ({ onSessionComplete }) => {
  // Setup State
  const [candidateName, setCandidateName] = useState('Cadet Muhammad Ali');
  const [targetBranch, setTargetBranch] = useState('Pakistan Army (PMA Long Course)');
  const [persona, setPersona] = useState<'deputy_president' | 'psychologist'>('deputy_president');
  const [numQuestions, setNumQuestions] = useState(4);

  // Active Session State
  const [session, setSession] = useState<StartInterviewResponse | null>(null);
  const [currentQuestionData, setCurrentQuestionData] = useState<any>(null);
  const [answerInput, setAnswerInput] = useState('');
  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null);
  const [followUpInput, setFollowUpInput] = useState('');
  const [conversationHistory, setConversationHistory] = useState<Array<{
    qId: string;
    category: string;
    question: string;
    answer: string;
    followUp?: string;
    followUpAnswer?: string;
  }>>([]);

  // Learning Phase State
  const [activeLearning, setActiveLearning] = useState<{
    questionId: string;
    questionText: string;
    data: LearningPhaseResult;
  } | null>(null);
  const [pendingNextQuestion, setPendingNextQuestion] = useState<any>(null);
  const [pendingIsCompleted, setPendingIsCompleted] = useState<boolean>(false);

  // UI state
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isCompleted, setIsCompleted] = useState(false);

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidateName.trim()) {
      setErrorMsg('Please enter a candidate name.');
      return;
    }
    setErrorMsg(null);
    setLoading(true);
    try {
      const data = await startInterview(candidateName.trim(), persona, numQuestions);
      setSession(data);
      setCurrentQuestionData(data.current_question);
      setConversationHistory([]);
      setFollowUpQuestion(null);
      setAnswerInput('');
      setFollowUpInput('');
      setActiveLearning(null);
      setPendingNextQuestion(null);
      setPendingIsCompleted(false);
      setIsCompleted(false);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start interview.');
    } finally {
      setLoading(false);
    }
  };

  const handlePrimarySubmit = async () => {
    if (!answerInput.trim() || !session) return;
    setErrorMsg(null);
    setLoading(true);

    try {
      const res: AnswerResponse = await submitAnswer(session.session_id, answerInput.trim());

      if (res.has_follow_up && res.follow_up_question) {
        // Trigger follow-up probe mode
        setFollowUpQuestion(res.follow_up_question);
      } else {
        // Record into local conversation history
        const currentQId = currentQuestionData.id;
        const currentQText = currentQuestionData.natural_prompt || currentQuestionData.raw_question;
        setConversationHistory((prev) => [
          ...prev,
          {
            qId: currentQId,
            category: currentQuestionData.category,
            question: currentQText,
            answer: answerInput.trim(),
          },
        ]);
        setAnswerInput('');
        setPendingNextQuestion(res.next_question || null);
        setPendingIsCompleted(!!res.is_completed);

        // Fetch coaching learning phase
        try {
          const learning = await getLearningFeedback(session.session_id, currentQId);
          setActiveLearning({
            questionId: currentQId,
            questionText: currentQText,
            data: learning,
          });
        } catch (learnErr) {
          if (res.is_completed) {
            setIsCompleted(true);
            onSessionComplete(session.session_id);
          } else if (res.next_question) {
            setCurrentQuestionData(res.next_question);
          }
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit answer.');
    } finally {
      setLoading(false);
    }
  };

  const handleFollowUpSubmit = async () => {
    if (!followUpInput.trim() || !session) return;
    setErrorMsg(null);
    setLoading(true);

    try {
      const res: AnswerResponse = await submitFollowUp(session.session_id, followUpInput.trim());

      const currentQId = currentQuestionData.id;
      const currentQText = currentQuestionData.natural_prompt || currentQuestionData.raw_question;
      setConversationHistory((prev) => [
        ...prev,
        {
          qId: currentQId,
          category: currentQuestionData.category,
          question: currentQText,
          answer: answerInput.trim(),
          followUp: followUpQuestion || undefined,
          followUpAnswer: followUpInput.trim(),
        },
      ]);

      setFollowUpQuestion(null);
      setFollowUpInput('');
      setAnswerInput('');
      setPendingNextQuestion(res.next_question || null);
      setPendingIsCompleted(!!res.is_completed);

      // Fetch coaching learning phase
      try {
        const learning = await getLearningFeedback(session.session_id, currentQId);
        setActiveLearning({
          questionId: currentQId,
          questionText: currentQText,
          data: learning,
        });
      } catch (learnErr) {
        if (res.is_completed) {
          setIsCompleted(true);
          onSessionComplete(session.session_id);
        } else if (res.next_question) {
          setCurrentQuestionData(res.next_question);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit follow-up response.');
    } finally {
      setLoading(false);
    }
  };

  const handleProceedAfterLearning = () => {
    setActiveLearning(null);
    if (pendingIsCompleted) {
      setIsCompleted(true);
      if (session) {
        onSessionComplete(session.session_id);
      }
    } else if (pendingNextQuestion) {
      setCurrentQuestionData(pendingNextQuestion);
      setPendingNextQuestion(null);
    }
  };

  const wordCount = answerInput.trim() ? answerInput.trim().split(/\s+/).length : 0;

  // 1. SETUP VIEW (when no active session)
  if (!session) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Hero Banner */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-4">
            <Shield className="w-3.5 h-3.5" />
            <span>Official ISSB Practice Suite</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-3">
            Simulate Your ISSB Interview With Precision
          </h1>
          <p className="text-slate-400 max-w-2xl mx-auto text-sm sm:text-base">
            Structured questions drawn strictly from verified board pools. Evidence-accumulating behavioral evaluation benchmarked against official guidelines.
          </p>
        </div>

        {/* Configuration Card */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl shadow-xl max-w-2xl mx-auto border border-slate-700/60">
          <form onSubmit={handleStart} className="space-y-6">
            {errorMsg && (
              <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Candidate Name */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Candidate Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={candidateName}
                  onChange={(e) => setCandidateName(e.target.value)}
                  placeholder="e.g. Cadet Tariq Mahmood"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900/90 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                  required
                />
              </div>
            </div>

            {/* Target Branch */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Target Commission Branch
              </label>
              <select
                value={targetBranch}
                onChange={(e) => setTargetBranch(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-900/90 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
              >
                <option value="Pakistan Army (PMA Long Course)">Pakistan Army (PMA Long Course)</option>
                <option value="Pakistan Navy (Cadet Entry)">Pakistan Navy (Cadet Entry)</option>
                <option value="Pakistan Air Force (GD Pilot / CAE)">Pakistan Air Force (GD Pilot / CAE)</option>
              </select>
            </div>

            {/* Interview Dimension */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
                Select Interview Evaluator Dimension
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setPersona('deputy_president')}
                  className={`p-4 rounded-xl text-left border transition-all ${
                    persona === 'deputy_president'
                      ? 'bg-emerald-950/40 border-emerald-500 text-white ring-1 ring-emerald-500/50'
                      : 'bg-slate-900/60 border-slate-700/80 text-slate-300 hover:border-slate-600'
                  }`}
                >
                  <div className="font-semibold text-sm mb-1 flex items-center justify-between">
                    <span>Deputy President</span>
                    {persona === 'deputy_president' && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    )}
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Evaluates intellect, emotional pattern, social behavior, and general awareness through structured confrontation.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setPersona('psychologist')}
                  className={`p-4 rounded-xl text-left border transition-all ${
                    persona === 'psychologist'
                      ? 'bg-emerald-950/40 border-emerald-500 text-white ring-1 ring-emerald-500/50'
                      : 'bg-slate-900/60 border-slate-700/80 text-slate-300 hover:border-slate-600'
                  }`}
                >
                  <div className="font-semibold text-sm mb-1 flex items-center justify-between">
                    <span>Psychologist</span>
                    {persona === 'psychologist' && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    )}
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Probes subconscious motivations, self-perception, emotional stability, and psychological defense mechanisms.
                  </p>
                </button>
              </div>
            </div>

            {/* Question Count Slider */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Question Count per Session
                </label>
                <span className="text-xs font-bold text-emerald-400 font-mono bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                  {numQuestions} Questions
                </span>
              </div>
              <input
                type="range"
                min="2"
                max="8"
                value={numQuestions}
                onChange={(e) => setNumQuestions(parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <div className="flex justify-between text-[11px] text-slate-500 mt-1 font-mono">
                <span>2 (Quick)</span>
                <span>5 (Standard)</span>
                <span>8 (Thorough)</span>
              </div>
            </div>

            {/* Start Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl shadow-lg shadow-emerald-900/40 transition-all duration-200 flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Preparing Question Sequence...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Commence Practice Interview</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // 2. ACTIVE INTERVIEW OR COMPLETED VIEW
  const currentStep = conversationHistory.length + 1;
  const progressPct = Math.min(100, Math.round(((currentStep - 1) / session.total_questions) * 100));

  return (
    <div className="max-w-4xl mx-auto py-6 px-4">
      {/* Top Header & Progress */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              {session.persona_title}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Candidate: {session.candidate_name}
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right">
            <span className="text-xs text-slate-400 font-mono">
              Question {Math.min(currentStep, session.total_questions)} of {session.total_questions}
            </span>
            <div className="w-32 bg-slate-800 h-2 rounded-full mt-1 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${progressPct}%` }}
              ></div>
            </div>
          </div>

          <button
            onClick={() => setSession(null)}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
            title="Exit Session"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="mb-4 p-3.5 rounded-xl bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Finished State Banner */}
      {isCompleted ? (
        <div className="glass-panel p-8 rounded-2xl text-center space-y-4 border border-emerald-500/30 shadow-2xl">
          <div className="w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center border border-emerald-500/40 animate-bounce">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-white">Interview Session Concluded!</h2>
          <p className="text-slate-300 text-sm max-w-lg mx-auto leading-relaxed">
            All questions and probing follow-ups have been completed. Your responses have been processed through the multi-pass psychometric evaluation engine.
          </p>
          <div className="pt-4">
            <button
              onClick={() => onSessionComplete(session.session_id)}
              className="px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-semibold rounded-xl shadow-lg shadow-emerald-950/50 transition-all flex items-center space-x-2 mx-auto"
            >
              <Award className="w-5 h-5" />
              <span>Inspect Comprehensive 15-Section Evaluation Report</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Previous Conversation History (collapsible/faded) */}
          {conversationHistory.length > 0 && (
            <div className="space-y-4 mb-6">
              {conversationHistory.map((item, idx) => (
                <div key={idx} className="space-y-2 opacity-70 hover:opacity-100 transition-opacity">
                  {/* Q */}
                  <div className="flex items-start space-x-3">
                    <div className="w-7 h-7 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center text-xs font-mono font-bold flex-shrink-0 mt-0.5">
                      Q{idx + 1}
                    </div>
                    <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800 text-sm text-slate-300 flex-1">
                      {item.question}
                    </div>
                  </div>
                  {/* A */}
                  <div className="flex items-start space-x-3 pl-10">
                    <div className="bg-emerald-950/20 p-3 rounded-xl border border-emerald-500/20 text-sm text-emerald-200/90 flex-1">
                      {item.answer}
                    </div>
                  </div>
                  {item.followUp && (
                    <>
                      <div className="flex items-start space-x-3 pl-6">
                        <div className="bg-amber-950/30 p-2.5 rounded-xl border border-amber-500/30 text-xs text-amber-300 flex-1">
                          <strong>Probe:</strong> {item.followUp}
                        </div>
                      </div>
                      <div className="flex items-start space-x-3 pl-12">
                        <div className="bg-emerald-950/30 p-2.5 rounded-xl border border-emerald-500/20 text-xs text-slate-300 flex-1">
                          {item.followUpAnswer}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* LEARNING COACHING PHASE (When active for current answer) */}
          {activeLearning ? (
            <LearningPhaseCard
              sessionId={session.session_id}
              questionId={activeLearning.questionId}
              questionText={activeLearning.questionText}
              learningData={activeLearning.data}
              onProceed={handleProceedAfterLearning}
            />
          ) : (
            <>
              {/* ACTIVE QUESTION CARD */}
              <div className="glass-panel-glow p-6 rounded-2xl space-y-4 border border-emerald-500/30">
                {/* Meta bar */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold uppercase tracking-wider border border-emerald-500/20 font-mono">
                      {currentQuestionData?.category_label || currentQuestionData?.category}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      Diff: {'⭐'.repeat(currentQuestionData?.difficulty || 1)}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    Assessing: {currentQuestionData?.evaluation_dimension?.replace('_', ' ')}
                  </span>
                </div>

                {/* Prompt text */}
                <div className="flex items-start space-x-3 pt-2">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center text-white font-bold text-xs flex-shrink-0 shadow-md shadow-emerald-950/50">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div className="space-y-1">
                    <div className="text-xs text-emerald-400 font-semibold uppercase tracking-wide">
                      {session.persona_title}
                    </div>
                    <p className="text-base sm:text-lg text-white font-medium leading-relaxed">
                      {currentQuestionData?.natural_prompt || currentQuestionData?.raw_question}
                    </p>
                  </div>
                </div>
              </div>

              {/* FOLLOW-UP PROBE MODAL/ALERT */}
              {followUpQuestion ? (
                <div className="p-5 rounded-2xl bg-amber-950/30 border border-amber-500/40 space-y-4 shadow-xl">
                  <div className="flex items-start space-x-3">
                    <div className="w-7 h-7 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center flex-shrink-0 mt-0.5 border border-amber-500/30">
                      <AlertCircle className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider text-amber-400 mb-1">
                        Interviewer Probing Follow-Up
                      </div>
                      <p className="text-sm sm:text-base text-amber-100 font-medium">
                        {followUpQuestion}
                      </p>
                    </div>
                  </div>

                  {/* Your previous answer quote */}
                  <div className="pl-10 text-xs text-slate-400 italic">
                    Candidate's initial reply: "{answerInput}"
                  </div>

                  <div className="pl-10 space-y-2">
                    <textarea
                      value={followUpInput}
                      onChange={(e) => setFollowUpInput(e.target.value)}
                      placeholder="Address the probing follow-up directly with concrete reasons and personal accountability..."
                      rows={3}
                      className="w-full p-3 bg-slate-900/90 border border-amber-500/40 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 transition-all placeholder-slate-500"
                    ></textarea>

                    <button
                      onClick={handleFollowUpSubmit}
                      disabled={loading || !followUpInput.trim()}
                      className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-sm transition-all flex items-center space-x-2 disabled:opacity-50"
                    >
                      {loading ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                      <span>Submit Follow-Up Response</span>
                    </button>
                  </div>
                </div>
              ) : (
                /* PRIMARY ANSWER INPUT */
                <div className="glass-panel p-5 rounded-2xl space-y-3 border border-slate-700/60">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Your Answer:</span>
                    <span className="font-mono">{wordCount} words (aim for 30–60 words with concrete examples)</span>
                  </div>

                  <textarea
                    value={answerInput}
                    onChange={(e) => setAnswerInput(e.target.value)}
                    placeholder="State your answer clearly, ground your assertions in concrete personal examples, and remain honest..."
                    rows={4}
                    className="w-full p-3.5 bg-slate-900/90 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all placeholder-slate-500 leading-relaxed"
                  ></textarea>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-slate-500 hidden sm:inline">
                      Avoid rote-learned clichés or blame externalization.
                    </span>
                    <button
                      onClick={handlePrimarySubmit}
                      disabled={loading || !answerInput.trim()}
                      className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-sm transition-all flex items-center space-x-2 shadow-md shadow-emerald-950/40 disabled:opacity-50 ml-auto"
                    >
                      {loading ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                      <span>Submit Answer</span>
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
