export interface SystemStatus {
  status: string;
  knowledge_base_chunks: number;
  question_bank_total: number;
  categories_total: number;
  llm_status: {
    status: string;
    detail: string;
    badge: 'success' | 'warning' | 'error';
  };
}

export interface CategoryItem {
  category: string;
  label: string;
  count: number;
}

export interface QuestionItem {
  id: string;
  category: string;
  category_label?: string;
  question: string;
  raw_question?: string;
  natural_prompt?: string;
  difficulty: number;
  persona: string;
  intent: string;
  evaluation_dimension: string;
  follow_up_pool: string[];
}

export interface RagChunk {
  score: number;
  text: string;
  source_type: string;
  dimension: string;
  topic: string;
  title: string;
  source_file: string;
  authority_level: number;
  citation: string;
  _fallback?: boolean;
}

export interface StartInterviewResponse {
  session_id: string;
  candidate_name: string;
  persona: string;
  persona_title: string;
  current_index: number;
  total_questions: number;
  current_question: {
    id: string;
    category: string;
    category_label: string;
    difficulty: number;
    evaluation_dimension: string;
    intent: string;
    raw_question: string;
    natural_prompt: string;
  };
}

export interface AnswerResponse {
  session_id: string;
  has_follow_up: boolean;
  follow_up_question?: string;
  is_completed: boolean;
  current_index: number;
  total_questions: number;
  next_question?: {
    id: string;
    category: string;
    category_label: string;
    difficulty: number;
    evaluation_dimension: string;
    intent: string;
    raw_question: string;
    natural_prompt: string;
  };
}

export interface EvaluationItemData {
  dimension: string;
  positive_indicators_observed: string[];
  weaknesses_observed: string[];
  official_citations: string[];
  academic_citations: string[];
  detailed_feedback: string;
  dimension_score: number;
  confidence: number;
}

export interface PerQuestionEvidence {
  No: number;
  "Question ID": string;
  Question?: string;
  Category: string;
  "Assessed Dimension": string;
  Score: string;
  Confidence?: string;
  Indicators: string;
  Weaknesses?: string;
}

export interface RadarDataPoint {
  subject: string;
  dimension: string;
  score: number;
  fullMark: number;
}

export interface EvaluationReportData {
  candidate_name: string;
  persona: string;
  overall_practice_score: number;
  dimension_scores: Record<string, number>;
  dimension_evaluations: Record<string, EvaluationItemData>;
  key_strengths: string[];
  growth_areas: string[];
  per_question_evidence: any[];
  formatted_evidence_table: PerQuestionEvidence[];
  radar_chart_data: RadarDataPoint[];
  session_metadata: Record<string, any>;
  candidate_profile: Record<string, any>;
  communication_assessment: string;
  leadership_assessment: string;
  decision_making_assessment: string;
  teamwork_assessment: string;
  motivation_assessment: string;
  stress_response_assessment: string;
  preparation_recommendations: string[];
  methodological_disclaimer: string;
  performance_band: {
    tier: string;
    badge_color: string;
    summary: string;
  };
}

export interface StrengthItem {
  area: string;
  observation: string;
  evidence_ids: string[];
  reinforcement: string;
}

export interface ImprovementArea {
  area: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  problem: string;
  evidence_ids: string[];
  why_it_matters: string;
  how_to_improve: string;
  technique: string;
  practice_task: string;
  example_structure?: string;
}

export interface LearningSummary {
  top_priority: string;
  secondary_priority: string;
  strength_to_maintain: string;
}

export interface RetryPrompt {
  enabled: boolean;
  instruction: string;
  target_area: string;
}

export interface LearningPhaseResult {
  overall_assessment: string;
  strengths: StrengthItem[];
  improvement_areas: ImprovementArea[];
  learning_summary: LearningSummary;
  retry: RetryPrompt;
  disclaimer: string;
}

export interface BeforeAfterComparison {
  previous_score: number;
  new_score: number;
  change: number;
  improved_areas: string[];
  unchanged_areas: string[];
  new_weaknesses: string[];
  explanation: string;
  metrics: {
    before: Record<string, any>;
    after: Record<string, any>;
    improvement: Record<string, any>;
  };
}

export interface CandidateLearningProfile {
  strengths: string[];
  recurring_weaknesses: string[];
  improving_areas: string[];
  priority_areas: string[];
  practice_history: any[];
  weakness_counts: Record<string, number>;
}

export interface SessionLearningReport {
  candidate_name: string;
  session_id: string;
  strongest_areas: string[];
  weakest_areas: string[];
  recurring_weaknesses: string[];
  improvements_achieved: string[];
  areas_requiring_further_practice: string[];
  recommended_practice_exercises: string[];
  olqs_with_strong_evidence: string[];
  olqs_requiring_more_evidence: string[];
  communication_patterns: string;
  reasoning_patterns: string;
  answer_structuring_patterns: string;
  suggested_next_practice_session: string;
  methodological_disclaimer: string;
}
