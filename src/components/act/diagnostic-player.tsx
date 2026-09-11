"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { readSession, writeSession } from "@/lib/act/prototype-state";
import type { ChoiceId, PublicQuestion, Subject } from "@/lib/act/types";

interface DiagnosticPlayerProps {
  subject: Subject;
}

export function DiagnosticPlayer({ subject }: DiagnosticPlayerProps) {
  const router = useRouter();
  const [questions, setQuestions] = useState<PublicQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, ChoiceId>>(() => readSession(subject, subject).answers);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [saveState, setSaveState] = useState<"saving" | "saved" | "offline">("saved");
  const [status, setStatus] = useState<"loading" | "ready" | "error" | "submitting">("loading");
  const [error, setError] = useState("");
  const session = useMemo(() => readSession(subject, subject), [subject]);

  useEffect(() => {
    fetch(`/api/prototype/questions?subject=${subject}&purpose=diagnostic`)
      .then(async (response) => {
        if (!response.ok) throw new Error("The diagnostic could not be loaded.");
        return response.json() as Promise<{ questions: PublicQuestion[] }>;
      })
      .then(({ questions: loadedQuestions }) => {
        setQuestions(loadedQuestions);
        setStatus("ready");
      })
      .catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : "The diagnostic could not be loaded.");
        setStatus("error");
      });
  }, [session.answers, session.status, subject]);

  const question = questions[currentIndex];
  const unansweredCount = questions.length - Object.keys(answers).length;

  function choose(choiceId: ChoiceId) {
    if (!question || session.status === "submitted") return;
    setSaveState("saving");
    const nextAnswers = { ...answers, [question.id]: choiceId };
    setAnswers(nextAnswers);
    writeSession({ ...readSession(subject, subject), answers: nextAnswers, status: "in_progress" });
    setSaveState("saved");
  }

  async function submit() {
    if (unansweredCount > 0 && !window.confirm(`You have ${unansweredCount} unanswered question${unansweredCount === 1 ? "" : "s"}. Submit anyway?`)) return;
    setStatus("submitting");
    setError("");
    const responses = questions.map((item) => ({ questionId: item.id, choiceId: answers[item.id] ?? null }));
    try {
      const response = await fetch("/api/prototype/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, purpose: "diagnostic", responses }),
      });
      if (!response.ok) throw new Error("Your answers are saved, but scoring failed. Try submitting again.");
      const score = await response.json();
      writeSession({
        ...readSession(subject, subject),
        answers,
        status: "submitted",
        score,
      });
      router.push(`/results/${subject}`);
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "Scoring failed. Your answers are still saved locally.");
      setSaveState("offline");
      setStatus("ready");
    }
  }

  if (status === "loading") return <LoadingMessage label="Loading your diagnostic…" />;
  if (status === "error") return <ErrorMessage message={error} />;
  if (!question) return <ErrorMessage message="This diagnostic has no questions yet." />;

  if (session.status === "submitted") {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-7 shadow-sm">
        <p className="text-sm font-semibold text-emerald-700">Diagnostic complete</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">Your results are ready.</h1>
        <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">You can review the skill profile and choose one focused learning path.</p>
        <Link href={`/results/${subject}`} className="mt-6 inline-flex h-10 items-center rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800">View results</Link>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">{subject === "english" ? "English" : "Math"} diagnostic</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Answer at your own pace.</h1>
        </div>
        <p className="text-sm text-slate-500" aria-live="polite">
          {saveState === "saving" ? "Saving…" : saveState === "offline" ? "Saved locally" : "Saved"}
        </p>
      </div>

      <div className="mt-8 h-2 overflow-hidden rounded-full bg-slate-200" aria-label={`Question ${currentIndex + 1} of ${questions.length}`}>
        <div className="h-full rounded-full bg-emerald-700 transition-all" style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }} />
      </div>
      <div className="mt-3 flex justify-between text-xs text-slate-500">
        <span>Question {currentIndex + 1} of {questions.length}</span>
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
        <button type="button" disabled={currentIndex === 0} onClick={() => setCurrentIndex((index) => index - 1)} className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40 hover:bg-slate-100">Previous</button>
        <div className="flex gap-3">
          {currentIndex < questions.length - 1 ? (
            <button type="button" onClick={() => setCurrentIndex((index) => index + 1)} className="h-10 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800">Next question</button>
          ) : (
            <button type="button" onClick={submit} disabled={status === "submitting"} className="h-10 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{status === "submitting" ? "Scoring…" : "Submit diagnostic"}</button>
          )}
        </div>
      </div>
    </div>
  );
}

function LoadingMessage({ label }: { label: string }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm" role="status">{label}</div>;
}

function ErrorMessage({ message }: { message: string }) {
  return <div className="rounded-xl border border-amber-200 bg-amber-50 p-8 text-sm text-amber-950" role="alert">{message}</div>;
}
