import type { AssessmentScore } from "./scoring";
import type { ChoiceId, Subject } from "./types";

export interface PrototypeSession {
  sessionId: string;
  subject: Subject;
  answers: Record<string, ChoiceId>;
  status: "in_progress" | "submitted";
  score?: AssessmentScore;
  practiceComplete: Record<string, boolean>;
  reassessmentAnswers: Record<string, ChoiceId>;
  cycleScores: Record<string, AssessmentScore>;
  issueReports: string[];
}

const storageKey = (sessionId: string) => `act-prototype-session:${sessionId}`;
const subjects: Subject[] = ["english", "math"];

export function emptySession(sessionId: string, subject: Subject): PrototypeSession {
  return {
    sessionId,
    subject,
    answers: {},
    status: "in_progress",
    practiceComplete: {},
    reassessmentAnswers: {},
    cycleScores: {},
    issueReports: [],
  };
}

export function readSession(sessionId: string, subject: Subject): PrototypeSession {
  if (typeof window === "undefined") return emptySession(sessionId, subject);

  try {
    const stored = window.localStorage.getItem(storageKey(sessionId));
    if (!stored) return emptySession(sessionId, subject);
    const parsed = JSON.parse(stored) as Partial<PrototypeSession>;
    return {
      ...emptySession(sessionId, subject),
      ...parsed,
      subject,
      sessionId,
    };
  } catch {
    return emptySession(sessionId, subject);
  }
}

export function writeSession(session: PrototypeSession) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(storageKey(session.sessionId), JSON.stringify(session));
  window.dispatchEvent(new Event("act-prototype-storage"));
}

export function subscribeToPrototypeChanges(callback: () => void) {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener("storage", callback);
  window.addEventListener("act-prototype-storage", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("act-prototype-storage", callback);
  };
}

export function getStartStatusSnapshot() {
  return JSON.stringify(
    subjects.map((subject) => {
      const session = readSession(subject, subject);
      return session.status === "submitted"
        ? "results"
        : Object.keys(session.answers).length > 0
          ? "resume"
          : "new";
    }),
  );
}

export function getServerStartStatusSnapshot() {
  return JSON.stringify(["new", "new"]);
}

export function saveIssue(session: PrototypeSession, issue: string): PrototypeSession {
  const next = {
    ...session,
    issueReports: [...session.issueReports, issue],
  };
  writeSession(next);
  return next;
}

export function responseEntries(answers: Record<string, ChoiceId>) {
  return Object.entries(answers).map(([questionId, choiceId]) => ({ questionId, choiceId }));
}

export function sessionHasCycle(session: PrototypeSession, skillId: string) {
  return Boolean(session.cycleScores[skillId]);
}
