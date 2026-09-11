export type Subject = "english" | "math";
export type AssessmentPurpose = "diagnostic" | "practice" | "reassessment";
export type ChoiceId = "A" | "B" | "C" | "D";
export type EvidenceDirection = "positive" | "negative" | "omitted";

export type MasteryClassification =
  | "strong_evidence_of_mastery"
  | "likely_mastered"
  | "developing"
  | "likely_weak"
  | "strong_evidence_of_weakness"
  | "insufficient_evidence";

export interface SkillResource {
  title: string;
  url: string;
  type: "lesson" | "practice";
  note: string;
}

export interface Skill {
  id: string;
  subject: Subject;
  name: string;
  category: string;
  definition: string;
  whyItMatters: string;
  importance: number;
  resources: SkillResource[];
}

export interface Choice {
  id: ChoiceId;
  text: string;
}

export interface PublicQuestion {
  id: string;
  subject: Subject;
  purpose: AssessmentPurpose;
  skillId: string;
  context?: string;
  prompt: string;
  choices: Choice[];
}

export interface PrivateQuestion extends PublicQuestion {
  correctChoiceId: ChoiceId;
  explanation: string;
  failureModeByChoice?: Partial<Record<ChoiceId, string>>;
}

export interface ResponseInput {
  questionId: string;
  choiceId: ChoiceId | null;
}

export interface EvidenceRecord {
  questionId: string;
  skillId: string;
  direction: EvidenceDirection;
  weight: number;
  purpose: AssessmentPurpose;
  failureMode?: string;
}

export interface MasterySnapshot {
  skillId: string;
  mean: number;
  lowerBound: number;
  upperBound: number;
  effectiveEvidence: number;
  correctCount: number;
  incorrectCount: number;
  omittedCount: number;
  classification: MasteryClassification;
  reason: string;
}

export interface Recommendation {
  skillId: string;
  rank: number;
  priorityScore: number;
  weaknessScore: number;
  importanceScore: number;
  confidenceScore: number;
  readiness: boolean;
  explanation: string;
}
