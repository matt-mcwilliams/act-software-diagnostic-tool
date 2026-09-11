import type {
  AssessmentPurpose,
  EvidenceRecord,
  MasterySnapshot,
  PrivateQuestion,
  Recommendation,
  ResponseInput,
  Skill,
} from "./types";

export const MASTERY_MODEL_VERSION = "beta-binomial-v1";
export const PRIORITY_FORMULA_VERSION = "priority-v1";

const PRIOR_ALPHA = 2;
const PRIOR_BETA = 2;
const TARGET_MASTERY = 0.75;

const EVIDENCE_WEIGHTS: Record<AssessmentPurpose, { correct: number; incorrect: number }> = {
  diagnostic: { correct: 1, incorrect: 1 },
  practice: { correct: 0.45, incorrect: 0.65 },
  reassessment: { correct: 1.25, incorrect: 1.25 },
};

export function evidenceForResponse(
  question: PrivateQuestion,
  response: ResponseInput,
): EvidenceRecord {
  if (response.choiceId === null) {
    return {
      questionId: question.id,
      skillId: question.skillId,
      direction: "omitted",
      weight: 0,
      purpose: question.purpose,
    };
  }

  const correct = response.choiceId === question.correctChoiceId;
  const purpose = question.purpose;
  const failureMode = question.failureModeByChoice?.[response.choiceId];

  return {
    questionId: question.id,
    skillId: question.skillId,
    direction: correct ? "positive" : "negative",
    weight: correct
      ? EVIDENCE_WEIGHTS[purpose].correct
      : failureMode
        ? EVIDENCE_WEIGHTS[purpose].incorrect * 1.15
        : EVIDENCE_WEIGHTS[purpose].incorrect,
    purpose,
    ...(failureMode ? { failureMode } : {}),
  };
}

export function calculateMastery(
  skillId: string,
  evidence: EvidenceRecord[],
): MasterySnapshot {
  const skillEvidence = evidence.filter((record) => record.skillId === skillId);
  const positive = skillEvidence
    .filter((record) => record.direction === "positive")
    .reduce((sum, record) => sum + record.weight, 0);
  const negative = skillEvidence
    .filter((record) => record.direction === "negative")
    .reduce((sum, record) => sum + record.weight, 0);
  const effectiveEvidence = positive + negative;
  const alpha = PRIOR_ALPHA + positive;
  const beta = PRIOR_BETA + negative;
  const mean = alpha / (alpha + beta);
  const confidence = effectiveEvidence / (effectiveEvidence + 2);
  const intervalRadius = Math.min(0.32, 0.42 / Math.sqrt(effectiveEvidence + 1));
  const lowerBound = Math.max(0, mean - intervalRadius);
  const upperBound = Math.min(1, mean + intervalRadius);
  const correctCount = skillEvidence.filter((record) => record.direction === "positive").length;
  const incorrectCount = skillEvidence.filter((record) => record.direction === "negative").length;
  const omittedCount = skillEvidence.filter((record) => record.direction === "omitted").length;

  let classification: MasterySnapshot["classification"];
  if (effectiveEvidence < 2) {
    classification = "insufficient_evidence";
  } else if (mean >= 0.78 && lowerBound >= 0.62 && confidence >= 0.7) {
    classification = "strong_evidence_of_mastery";
  } else if (mean >= 0.68 && confidence >= 0.55) {
    classification = "likely_mastered";
  } else if (mean <= 0.34 && upperBound <= 0.5 && confidence >= 0.7) {
    classification = "strong_evidence_of_weakness";
  } else if (mean <= 0.52 && confidence >= 0.55) {
    classification = "likely_weak";
  } else {
    classification = "developing";
  }

  const reason =
    classification === "insufficient_evidence"
      ? "There are not yet enough scored responses to make a dependable call."
      : `Based on ${correctCount} correct and ${incorrectCount} incorrect scored response${correctCount + incorrectCount === 1 ? "" : "s"}.`;

  return {
    skillId,
    mean,
    lowerBound,
    upperBound,
    effectiveEvidence,
    correctCount,
    incorrectCount,
    omittedCount,
    classification,
    reason,
  };
}

export function buildRecommendations(
  skills: Skill[],
  snapshots: MasterySnapshot[],
  inventory: Set<string>,
): Recommendation[] {
  return snapshots
    .map((snapshot) => {
      const skill = skills.find((candidate) => candidate.id === snapshot.skillId);
      if (!skill) return null;

      const readiness = inventory.has(skill.id) && skill.resources.length > 0;
      const weaknessScore = Math.max(0, (TARGET_MASTERY - snapshot.mean) / TARGET_MASTERY);
      const confidenceScore = Math.min(
        1,
        snapshot.effectiveEvidence / (snapshot.effectiveEvidence + 2),
      );
      const importanceScore = skill.importance;
      const priorityScore = weaknessScore * importanceScore * confidenceScore * (readiness ? 1 : 0);
      const explanation = readiness
        ? snapshot.classification === "insufficient_evidence"
          ? `${skill.name} is worth checking, but the diagnostic needs more evidence before focused remediation.`
          : `${skill.name} is prioritized from the observed response pattern, its ACT coverage, and an available learning path.`
        : `${skill.name} is visible for review, but the current prototype does not have a complete learning path.`;

      return {
        skillId: skill.id,
        rank: 0,
        priorityScore,
        weaknessScore,
        importanceScore,
        confidenceScore,
        readiness,
        explanation,
      };
    })
    .filter((recommendation): recommendation is Recommendation => recommendation !== null)
    .sort((a, b) => b.priorityScore - a.priorityScore || a.skillId.localeCompare(b.skillId))
    .map((recommendation, index) => ({ ...recommendation, rank: index + 1 }));
}
