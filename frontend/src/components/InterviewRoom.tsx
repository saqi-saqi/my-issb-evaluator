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
  ArrowRight,
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
      <div className="max-w-6xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          {/* Left Column: Hero & Stats */}
          <div className="lg:col-span-6 space-y-6 pt-2">
            <div className="flex items-center space-x-2 text-xs font-mono tracking-widest text-[#00e599] uppercase">
              <span className="w-5 h-[2px] bg-[#00e599]"></span>
              <span>CANDIDATE SETUP</span>
            </div>

            <h1 className="text-4xl sm:text-5xl font-black tracking-tight text-white leading-[1.15]">
              Report to the <span className="text-[#00e599] drop-shadow-[0_0_20px_rgba(0,229,153,0.3)]">Selection Board.</span>
            </h1>

            <p className="text-slate-400 text-sm leading-relaxed max-w-lg">
              A live simulation of the ISSB officer interview. Answer under pressure, absorb follow-up probes, receive coaching after every question, and leave with a psychometric readiness report.
            </p>

            {/* 3 Stat Counters */}
            <div className="grid grid-cols-3 gap-6 pt-6 border-t border-[#162536]">
              <div>
                <div className="text-3xl font-black font-mono text-white">05</div>
                <div className="text-[10px] font-mono tracking-wider text-slate-500 uppercase mt-1">
                  DIMENSIONS SCORED
                </div>
              </div>
              <div>
                <div className="text-3xl font-black font-mono text-white">02</div>
                <div className="text-[10px] font-mono tracking-wider text-slate-500 uppercase mt-1">
                  EVALUATOR PERSONAS
                </div>
              </div>
              <div>
                <div className="text-3xl font-black font-mono text-white">∞</div>
                <div className="text-[10px] font-mono tracking-wider text-slate-500 uppercase mt-1">
                  PRACTICE LOOPS
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Setup Form */}
          <div className="lg:col-span-6">
            <div className="military-card p-6 sm:p-8 rounded-2xl shadow-2xl">
              <form onSubmit={handleStart} className="space-y-6">
                {errorMsg && (
                  <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-center space-x-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                {/* 01 · CANDIDATE NAME */}
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
                    01 · CANDIDATE NAME
                  </label>
                  <input
                    type="text"
                    value={candidateName}
                    onChange={(e) => setCandidateName(e.target.value)}
                    placeholder="e.g. Ahmed Raza"
                    className="w-full px-4 py-3 bg-[#060b11] border border-[#1b2d42] rounded-xl text-white text-sm focus:outline-none focus:border-[#00e599] transition-all placeholder-slate-600 font-medium"
                    required
                  />
                </div>

                {/* 02 · EVALUATOR PERSONA */}
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
                    02 · EVALUATOR PERSONA
                  </label>
                  <div className="space-y-3">
                    {/* DP Option */}
                    <div
                      onClick={() => setPersona('deputy_president')}
                      className={`p-4 rounded-xl border transition-all cursor-pointer ${
                        persona === 'deputy_president'
                          ? 'military-card-active'
                          : 'bg-[#070d14] border-[#152335] hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start space-x-3.5">
                          <div className="w-10 h-10 rounded-lg border border-[#00e599]/40 bg-[#00e599]/10 text-[#00e599] font-mono font-bold text-sm flex items-center justify-center flex-shrink-0">
                            DP
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-bold text-white text-sm">Deputy President</span>
                              <span className="text-xs text-slate-400">Brigadier</span>
                            </div>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {['DEFENSE', 'LEADERSHIP', 'STRATEGIC GEOPOLITICS', 'CRISIS DILEMMAS'].map((tag) => (
                                <span key={tag} className="px-2 py-0.5 rounded bg-[#060b11] border border-[#1b2d42] text-[9px] font-mono text-slate-300">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <span className="text-[10px] font-mono text-amber-400 font-bold uppercase tracking-wider">
                          BOARD INTERVIEW
                        </span>
                      </div>
                    </div>

                    {/* SP Option */}
                    <div
                      onClick={() => setPersona('psychologist')}
                      className={`p-4 rounded-xl border transition-all cursor-pointer ${
                        persona === 'psychologist'
                          ? 'military-card-active'
                          : 'bg-[#070d14] border-[#152335] hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start space-x-3.5">
                          <div className="w-10 h-10 rounded-lg border border-[#00e599]/40 bg-[#00e599]/10 text-[#00e599] font-mono font-bold text-sm flex items-center justify-center flex-shrink-0">
                            SP
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-bold text-white text-sm">Senior Psychologist</span>
                              <span className="text-xs text-slate-400">Lt. Colonel</span>
                            </div>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {['UPBRINGING', 'FAMILY DYNAMICS', 'STRESS COPING', 'EMOTIONAL STABILITY'].map((tag) => (
                                <span key={tag} className="px-2 py-0.5 rounded bg-[#060b11] border border-[#1b2d42] text-[9px] font-mono text-slate-300">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <span className="text-[10px] font-mono text-amber-400 font-bold uppercase tracking-wider">
                          ASSESSMENT INTERVIEW
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 03 · NUMBER OF QUESTIONS */}
                <div>
                  <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
                    03 · NUMBER OF QUESTIONS
                  </label>
                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => setNumQuestions((prev) => Math.max(2, prev - 1))}
                      className="w-9 h-9 flex items-center justify-center bg-[#070d14] border border-[#1b2d42] rounded-lg text-slate-300 hover:text-white transition-colors"
                    >
                      -
                    </button>
                    <div className="w-14 h-9 flex items-center justify-center bg-[#060b11] border border-[#1b2d42] rounded-lg text-white font-mono font-bold text-sm">
                      {numQuestions}
                    </div>
                    <button
                      type="button"
                      onClick={() => setNumQuestions((prev) => Math.min(10, prev + 1))}
                      className="w-9 h-9 flex items-center justify-center bg-[#070d14] border border-[#1b2d42] rounded-lg text-slate-300 hover:text-white transition-colors"
                    >
                      +
                    </button>
                    <span className="text-xs font-mono text-slate-500 ml-2">
                      1 - 10 · default 5
                    </span>
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 rounded-xl military-btn-emerald flex items-center justify-center space-x-2 font-mono uppercase tracking-widest text-xs disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                      <span>Preparing Chamber...</span>
                    </>
                  ) : (
                    <>
                      <span>ENTER INTERVIEW CHAMBER</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 2. ACTIVE INTERVIEW OR COMPLETED VIEW
  const currentStep = conversationHistory.length + 1;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Top Header & Progress from Lovable */}
      <div className="flex items-center justify-between pb-4 mb-6 border-b border-[#162536]">
        <div className="flex items-center space-x-2 text-xs font-mono tracking-widest text-[#00e599] uppercase">
          <span className="w-5 h-[2px] bg-[#00e599]"></span>
          <span>INTERVIEW CHAMBER</span>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-xs font-mono text-slate-400">
            Question <span className="text-[#00e599] font-bold text-sm">{Math.min(currentStep, session.total_questions)}</span> of {session.total_questions}
          </div>
          <button
            onClick={() => setSession(null)}
            className="p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-[#0a121d] transition-colors"
            title="Exit Session"
          >
            <RefreshCw className="w-3.5 h-3.5" />
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
        <div className="military-card p-8 rounded-2xl text-center space-y-4 shadow-2xl">
          <div className="w-16 h-16 rounded-full bg-[#00e599]/20 text-[#00e599] mx-auto flex items-center justify-center border border-[#00e599]/40">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-white">Interview Session Concluded!</h2>
          <p className="text-slate-300 text-sm max-w-lg mx-auto leading-relaxed">
            All questions and probing follow-ups have been completed. Your responses have been processed through the psychometric evaluation engine.
          </p>
          <div className="pt-4">
            <button
              onClick={() => onSessionComplete(session.session_id)}
              className="px-6 py-3 military-btn-emerald rounded-xl transition-all flex items-center space-x-2 mx-auto font-mono text-xs uppercase tracking-wider"
            >
              <Award className="w-4 h-4" />
              <span>VIEW PERFORMANCE DASHBOARD</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
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
              {/* ACTIVE QUESTION CARD from Image 1 */}
              <div className="military-card p-6 sm:p-7 rounded-2xl space-y-4 shadow-2xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3.5">
                    <div className="w-12 h-12 rounded-lg border border-[#00e599]/40 bg-[#00e599]/10 text-[#00e599] font-mono font-bold text-base flex items-center justify-center flex-shrink-0">
                      {session.persona === 'deputy_president' ? 'DP' : 'SP'}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-white text-base">
                          {session.persona === 'deputy_president' ? 'Deputy President' : 'Senior Psychologist'}
                        </span>
                        <span className="text-[11px] font-mono uppercase text-slate-400">
                          {session.persona === 'deputy_president' ? 'BRIGADIER' : 'LT. COLONEL'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="px-2.5 py-1 rounded border border-amber-500/40 bg-amber-500/10 text-amber-400 text-[10px] font-mono font-bold uppercase tracking-wider">
                    {currentQuestionData?.evaluation_dimension?.toUpperCase() || 'EMOTIONAL STABILITY'}
                  </div>
                </div>

                {/* Question Text */}
                <div className="pt-2">
                  <p className="text-lg sm:text-xl text-white font-normal leading-relaxed">
                    {currentQuestionData?.natural_prompt || currentQuestionData?.raw_question}
                  </p>
                </div>
              </div>

              {/* FOLLOW-UP PROBE MODAL/ALERT */}
              {followUpQuestion ? (
                <div className="military-card p-6 rounded-2xl border-amber-500/40 bg-amber-950/20 space-y-4 shadow-2xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-amber-400 text-xs font-mono uppercase font-bold tracking-wider">
                      <AlertCircle className="w-4 h-4" />
                      <span>Interviewer Probing Follow-Up</span>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-[10px] font-bold">
                      PROBE
                    </span>
                  </div>

                  <p className="text-base sm:text-lg text-white font-medium">
                    {followUpQuestion}
                  </p>

                  <textarea
                    value={followUpInput}
                    onChange={(e) => setFollowUpInput(e.target.value)}
                    placeholder="Address the probe directly with concrete reasoning and personal ownership..."
                    rows={3}
                    className="w-full p-4 bg-[#060b11] border border-amber-500/40 rounded-xl text-white text-sm focus:outline-none placeholder-slate-600 leading-relaxed"
                  ></textarea>

                  <div className="flex justify-end">
                    <button
                      onClick={handleFollowUpSubmit}
                      disabled={loading || !followUpInput.trim()}
                      className="px-6 py-2.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-black font-extrabold text-xs font-mono uppercase tracking-wider transition-all disabled:opacity-50 flex items-center space-x-2"
                    >
                      {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                      <span>SUBMIT FOLLOW-UP RESPONSE</span>
                    </button>
                  </div>
                </div>
              ) : (
                /* YOUR RESPONSE CARD from Image 1 */
                <div className="military-card rounded-2xl overflow-hidden shadow-2xl space-y-0">
                  <div className="px-6 pt-5 pb-2 flex items-center justify-between border-b border-[#132235]">
                    <span className="text-xs font-mono tracking-widest text-slate-400 uppercase font-semibold">
                      YOUR RESPONSE
                    </span>
                    <span className="text-xs font-mono text-slate-500 font-bold">
                      {wordCount} WORDS
                    </span>
                  </div>

                  <textarea
                    value={answerInput}
                    onChange={(e) => setAnswerInput(e.target.value)}
                    placeholder="Speak as you would to the board. Own your decisions in the first person."
                    rows={5}
                    className="w-full p-6 bg-transparent text-white text-sm focus:outline-none placeholder-slate-600 leading-relaxed resize-none min-h-[140px]"
                  ></textarea>

                  <div className="px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-[#132235] bg-[#070e17]/60">
                    <span className="text-[11px] font-mono text-slate-400">
                      Target 80-150 words · Situation → Task → Action → Result
                    </span>

                    <button
                      onClick={handlePrimarySubmit}
                      disabled={loading || !answerInput.trim()}
                      className="px-6 py-2.5 rounded-xl military-btn-emerald flex items-center space-x-2 text-xs font-mono uppercase tracking-wider disabled:opacity-50 ml-auto"
                    >
                      {loading ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin mr-1" />
                          <span>Evaluating...</span>
                        </>
                      ) : (
                        <>
                          <Send className="w-3.5 h-3.5" />
                          <span>SUBMIT ANSWER</span>
                        </>
                      )}
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
