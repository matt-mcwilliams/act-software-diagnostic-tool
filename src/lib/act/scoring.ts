import { buildRecommendations, calculateMastery, evidenceForResponse } from "./engine";
import { getQuestions, getSkills } from "./server-content";
import type {
  AssessmentPurpose,
  EvidenceRecord,
  MasterySnapshot,
  Recommendation,
  ResponseInput,
  Subject,
} from "./types";

export interface ScoredItem {
  questionId: string;
  choiceId: ResponseInput["choiceId"];
  correct: boolean | null;
  explanation?: string;
}

export interface AssessmentScore {
  subject: Subject;
  purpose: AssessmentPurpose;
  correct: number;
  answered: number;
  total: number;
  items: ScoredItem[];
  evidence: EvidenceRecord[];
  snapshots: MasterySnapshot[];
  recommendations: Recommendation[];
}

export function scoreAssessment(
  subject: Subject,
  purpose: AssessmentPurpose,
  responses: ResponseInput[],
): AssessmentScore {
  const questions = new Map(getQuestions(subject, purpose).map((item) => [item.id, item] as const));

  const relevantResponses = responses.filter((response) => questions.has(response.questionId));
  const evidence = relevantResponses.map((response) =>
    evidenceForResponse(questions.get(response.questionId)!, response),
  );
  const skills = getSkills(subject);
  const snapshots = skills.map((skill) => calculateMastery(skill.id, evidence));
  const inventory = new Set(
    skills
      .filter((skill) => skill.resources.length > 0)
      .map((skill) => skill.id),
  );
  const scoredItems = relevantResponses.map((response) => {
    const item = questions.get(response.questionId)!;
    const correct = response.choiceId === null ? null : response.choiceId === item.correctChoiceId;
    return {
      questionId: response.questionId,
      choiceId: response.choiceId,
      correct,
      ...(purpose !== "diagnostic" && response.choiceId !== null ? { explanation: item.explanation } : {}),
    };
  });

  return {
    subject,
    purpose,
    correct: scoredItems.filter((item) => item.correct === true).length,
    answered: scoredItems.filter((item) => item.choiceId !== null).length,
    total: questions.size,
    items: scoredItems,
    evidence,
    snapshots,
    recommendations: buildRecommendations(skills, snapshots, inventory),
  };
}
