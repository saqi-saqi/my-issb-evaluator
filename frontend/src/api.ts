import {
  AnswerResponse,
  BeforeAfterComparison,
  CandidateLearningProfile,
  CategoryItem,
  EvaluationReportData,
  LearningPhaseResult,
  QuestionItem,
  RagChunk,
  SessionLearningReport,
  StartInterviewResponse,
  SystemStatus,
} from './types';

const BASE_URL = '/api';

export async function fetchStatus(): Promise<SystemStatus> {
  const res = await fetch(`${BASE_URL}/status`);
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function fetchCategories(): Promise<CategoryItem[]> {
  const res = await fetch(`${BASE_URL}/categories`);
  if (!res.ok) throw new Error('Failed to fetch categories');
  return res.json();
}

export async function fetchQuestions(
  category?: string,
  persona?: string,
  maxDifficulty?: number
): Promise<QuestionItem[]> {
  const params = new URLSearchParams();
  if (category && category !== 'all') params.append('category', category);
  if (persona && persona !== 'all') params.append('persona', persona);
  if (maxDifficulty) params.append('max_difficulty', maxDifficulty.toString());

  const res = await fetch(`${BASE_URL}/questions?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch questions');
  return res.json();
}

export async function searchRag(
  query: string,
  sourceType?: string,
  preferOfficial: boolean = true,
  topK: number = 5
): Promise<RagChunk[]> {
  const payload: any = { query, prefer_official: preferOfficial, top_k: topK };
  if (sourceType && sourceType !== 'all') payload.source_type = sourceType;

  const res = await fetch(`${BASE_URL}/rag/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to search knowledge base');
  return res.json();
}

export async function startInterview(
  candidateName: string,
  persona: string,
  numQuestions: number
): Promise<StartInterviewResponse> {
  const res = await fetch(`${BASE_URL}/interview/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      candidate_name: candidateName,
      persona: persona,
      num_questions: numQuestions,
    }),
  });
  if (!res.ok) throw new Error('Failed to initialize interview');
  return res.json();
}

export async function submitAnswer(
  sessionId: string,
  answer: string
): Promise<AnswerResponse> {
  const res = await fetch(`${BASE_URL}/interview/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, answer }),
  });
  if (!res.ok) throw new Error('Failed to submit answer');
  return res.json();
}

export async function submitFollowUp(
  sessionId: string,
  followUpAnswer: string
): Promise<AnswerResponse> {
  const res = await fetch(`${BASE_URL}/interview/follow-up`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, follow_up_answer: followUpAnswer }),
  });
  if (!res.ok) throw new Error('Failed to submit follow-up response');
  return res.json();
}

export async function fetchReport(sessionId: string): Promise<EvaluationReportData> {
  const res = await fetch(`${BASE_URL}/interview/report/${sessionId}`);
  if (!res.ok) throw new Error('Failed to load evaluation report');
  return res.json();
}

export async function updateLLMSettings(
  provider: string,
  apiKey?: string,
  modelName?: string,
  baseUrl?: string
): Promise<{ success: boolean; message: string; status_info: any }> {
  const res = await fetch(`${BASE_URL}/settings/llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider,
      api_key: apiKey,
      model_name: modelName,
      base_url: baseUrl,
    }),
  });
  if (!res.ok) throw new Error('Failed to update LLM configuration');
  return res.json();
}

export async function getLearningFeedback(
  sessionId: string,
  questionId?: string
): Promise<LearningPhaseResult> {
  const res = await fetch(`${BASE_URL}/learning/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question_id: questionId }),
  });
  if (!res.ok) throw new Error('Failed to fetch learning feedback');
  const data = await res.json();
  return data.learning_phase;
}

export async function submitRetryAnswer(
  sessionId: string,
  questionId: string,
  retryAnswer: string
): Promise<{
  before_after: BeforeAfterComparison;
  new_evidence: any;
  new_learning: LearningPhaseResult;
  learning_profile: CandidateLearningProfile;
}> {
  const res = await fetch(`${BASE_URL}/learning/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      question_id: questionId,
      retry_answer: retryAnswer,
    }),
  });
  if (!res.ok) throw new Error('Failed to submit retry answer');
  return res.json();
}

export async function getLearningProfile(
  sessionId: string
): Promise<{
  session_id: string;
  learning_profile: CandidateLearningProfile;
  session_learning_report: SessionLearningReport;
}> {
  const res = await fetch(`${BASE_URL}/learning/profile/${sessionId}`);
  if (!res.ok) throw new Error('Failed to load learning profile');
  return res.json();
}
