export type FastApiChoiceId = "A" | "B" | "C" | "D";

export interface FastApiChoice {
  id: FastApiChoiceId;
  text: string;
}

export interface FastApiAssessmentItem {
  id: string;
  question_id: string;
  position: number;
  prompt: string;
  context: string | null;
  choices: FastApiChoice[];
}

export interface FastApiAssessmentSession {
  id: string;
  subject: "english" | "math";
  purpose: "diagnostic";
  status: "created" | "in_progress" | "submitted" | "scoring" | "scored" | "expired" | "abandoned" | "failed";
  items: FastApiAssessmentItem[];
  answers: Record<string, FastApiChoiceId>;
  revisions: Record<string, number>;
}

export interface FastApiScoredItem {
  session_item_id: string;
  question_id: string;
  choice_id: FastApiChoiceId | null;
  correct: boolean | null;
}

export interface FastApiMasterySnapshot {
  skill_id: string;
  skill_key: string;
  skill_name: string;
  mean: number;
  lower_bound: number;
  upper_bound: number;
  effective_evidence: number;
  correct_count: number;
  incorrect_count: number;
  omitted_count: number;
  classification: string;
  reason: string;
  model_version: string;
}

export interface FastApiRecommendation {
  skill_id: string;
  skill_key: string;
  skill_name: string;
  rank: number;
  priority_score: number;
  weakness_score: number;
  importance_score: number;
  confidence_score: number;
  readiness: boolean;
  explanation: string;
  formula_version: string;
}

export interface FastApiAssessmentResult {
  session_id: string;
  subject: "english" | "math";
  purpose: "diagnostic";
  correct: number;
  answered: number;
  total: number;
  items: FastApiScoredItem[];
  scoring_version: string;
  mastery_model_version: string;
  snapshots: FastApiMasterySnapshot[];
  recommendations: FastApiRecommendation[];
}
