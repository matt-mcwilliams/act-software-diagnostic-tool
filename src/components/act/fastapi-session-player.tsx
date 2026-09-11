"use client";

import { useRef, useState } from "react";

import type {
  FastApiAssessmentResult,
  FastApiAssessmentSession,
  FastApiChoiceId,
} from "@/lib/api/contracts";

function requestId() {
  return crypto.randomUUID();
}

async function responseError(response: Response, fallback: string) {
  const body = await response.json().catch(() => null) as { error?: { message?: string } } | null;
  return body?.error?.message || fallback;
}

export function FastApiSessionPlayer({
  session,
  eyebrow,
  heading,
  description,
  submitLabel,
  submittingLabel,
  onSubmitted,
}: {
  session: FastApiAssessmentSession;
  eyebrow: string;
  heading: string;
  description?: string;
  submitLabel: string;
  submittingLabel: string;
  onSubmitted: (result: FastApiAssessmentResult) => Promise<void> | void;
}) {
  const [answers, setAnswers] = useState<Record<string, FastApiChoiceId>>(session.answers ?? {});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [saveState, setSaveState] = useState<"saving" | "saved" | "error">("saved");
  const [status, setStatus] = useState<"ready" | "submitting">("ready");
  const [error, setError] = useState("");
  const answersRef = useRef(answers);
  const revisionsRef = useRef(session.revisions ?? {});
  const saveQueues = useRef<Record<string, Promise<void>>>({});
  const saveFailures = useRef(new Set<string>());

  const question = session.items[currentIndex];
  const unansweredCount = session.items.length - Object.keys(answers).length;

  function choose(choiceId: FastApiChoiceId) {
    if (!question || status === "submitting") return;
    const revision = (revisionsRef.current[question.id] ?? 0) + 1;
    const nextAnswers = { ...answersRef.current, [question.id]: choiceId };
    answersRef.current = nextAnswers;
    revisionsRef.current = { ...revisionsRef.current, [question.id]: revision };
    setAnswers(nextAnswers);
    setSaveState("saving");
    setError("");

    const previous = saveQueues.current[question.id] ?? Promise.resolve();
    const save = previous
      .catch(() => undefined)
      .then(async () => {
        const response = await fetch(`/api/assessment/sessions/${session.id}/responses/${question.id}`, {
          method: "PUT",
          headers: {
            "content-type": "application/json",
            "idempotency-key": requestId(),
          },
          body: JSON.stringify({ choice_id: choiceId, client_revision: revision }),
          cache: "no-store",
        });
        if (!response.ok) throw new Error(await responseError(response, "Your answer could not be saved."));
        const saved = await response.json() as { client_revision: number };
        revisionsRef.current = { ...revisionsRef.current, [question.id]: saved.client_revision };
        saveFailures.current.delete(question.id);
        setSaveState("saved");
      })
      .catch((saveError: unknown) => {
        saveFailures.current.add(question.id);
        setSaveState("error");
        setError(saveError instanceof Error ? saveError.message : "Your answer could not be saved.");
      });
    saveQueues.current[question.id] = save;
  }

  async function submit() {
    if (unansweredCount > 0 && !window.confirm(`You have ${unansweredCount} unanswered question${unansweredCount === 1 ? "" : "s"}. Submit anyway?`)) return;
    setStatus("submitting");
    setError("");
    await Promise.all(Object.values(saveQueues.current));
    if (saveFailures.current.size > 0) {
      setSaveState("error");
      setError("Your answers could not be synchronized. Check your connection and try again.");
      setStatus("ready");
      return;
    }

    try {
      const response = await fetch(`/api/assessment/sessions/${session.id}/submit`, {
        method: "POST",
        headers: { "idempotency-key": requestId() },
        cache: "no-store",
      });
      if (!response.ok) throw new Error(await responseError(response, "Your answers could not be scored."));
      await onSubmitted(await response.json() as FastApiAssessmentResult);
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "Your answers could not be scored.");
      setStatus("ready");
    }
  }

  if (!question) return <Message message="This assessment has no questions yet." />;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">{eyebrow}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{heading}</h1>
          {description ? <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">{description}</p> : null}
        </div>
        <p className="text-sm text-slate-500" aria-live="polite">
          {saveState === "saving" ? "Saving…" : saveState === "error" ? "Needs attention" : "Saved"}
        </p>
      </div>

      <div className="mt-8 h-2 overflow-hidden rounded-full bg-slate-200" aria-label={`Question ${currentIndex + 1} of ${session.items.length}`}>
        <div className="h-full rounded-full bg-emerald-700 transition-all" style={{ width: `${((currentIndex + 1) / session.items.length) * 100}%` }} />
      </div>
      <div className="mt-3 flex justify-between text-xs text-slate-500">
        <span>Question {currentIndex + 1} of {session.items.length}</span>
        <span>{unansweredCount} unanswered</span>
      </div>

      <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        {question.context ? <p className="rounded-md bg-slate-50 p-4 text-base leading-7 text-slate-800">{question.context}</p> : null}
        <h2 className="mt-6 text-xl font-semibold leading-8 text-slate-950">{question.prompt}</h2>
        <fieldset className="mt-6">
          <legend className="sr-only">Answer choices</legend>
          <div className="space-y-3">
            {question.choices.map((choice) => {
              const selected = answers[question.id] === choice.id;
              return (
                <button
                  key={choice.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => choose(choice.id)}
                  className={`flex w-full items-start gap-3 rounded-lg border p-4 text-left text-sm leading-6 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 ${selected ? "border-emerald-700 bg-emerald-50 text-slate-950" : "border-slate-200 hover:border-slate-400 hover:bg-slate-50"}`}
                >
                  <span className={`flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${selected ? "border-emerald-700 bg-emerald-700 text-white" : "border-slate-300 text-slate-600"}`}>{choice.id}</span>
                  <span>{choice.text}</span>
                </button>
              );
            })}
          </div>
        </fieldset>
      </section>

      {error ? <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900" role="alert">{error}</p> : null}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <button type="button" disabled={currentIndex === 0 || status === "submitting"} onClick={() => setCurrentIndex((index) => index - 1)} className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40 hover:bg-slate-100">Previous</button>
        <div className="flex gap-3">
          {currentIndex < session.items.length - 1 ? (
            <button type="button" onClick={() => setCurrentIndex((index) => index + 1)} className="h-10 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800">Next question</button>
          ) : (
            <button type="button" onClick={submit} disabled={status === "submitting"} className="h-10 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">{status === "submitting" ? submittingLabel : submitLabel}</button>
          )}
        </div>
      </div>
    </div>
  );
}

function Message({ message }: { message: string }) {
  return <div className="rounded-xl border border-amber-200 bg-amber-50 p-8 text-sm text-amber-950" role="alert">{message}</div>;
}
