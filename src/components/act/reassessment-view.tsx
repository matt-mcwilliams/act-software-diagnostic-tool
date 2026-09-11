"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageFrame } from "@/components/act/page-frame";
import { readSession, responseEntries, writeSession } from "@/lib/act/prototype-state";
import type { AssessmentScore } from "@/lib/act/scoring";
import type { ChoiceId, PublicQuestion, Subject } from "@/lib/act/types";
import { StatusLabel } from "./status-label";

export function ReassessmentView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const [questions, setQuestions] = useState<PublicQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, ChoiceId>>(() => readSession(subject, subject).reassessmentAnswers);
  const [result, setResult] = useState<AssessmentScore | null>(() => readSession(subject, subject).cycleScores[skillId] ?? null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`/api/prototype/questions?subject=${subject}&purpose=reassessment`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Reassessment could not be loaded.");
        return response.json() as Promise<{ questions: PublicQuestion[] }>;
      })
      .then(({ questions: loadedQuestions }) => setQuestions(loadedQuestions.filter((question) => question.skillId === skillId)))
      .catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : "Reassessment could not be loaded."))
      .finally(() => setLoading(false));
  }, [skillId, subject]);

  if (loading) return <ReassessmentMessage>Loading unseen reassessment…</ReassessmentMessage>;
  if (error && questions.length === 0) return <ReassessmentMessage>{error}</ReassessmentMessage>;
  if (questions.length === 0) return <ReassessmentMessage>There is no reassessment inventory for this skill yet.</ReassessmentMessage>;
  if (result) return <Outcome subject={subject} skillId={skillId} result={result} />;

  const question = questions[currentIndex];
  const unansweredCount = questions.length - Object.keys(answers).length;

  function choose(choiceId: ChoiceId) {
    const nextAnswers = { ...answers, [question.id]: choiceId };
    setAnswers(nextAnswers);
    const session = readSession(subject, subject);
    writeSession({ ...session, reassessmentAnswers: nextAnswers });
  }

  async function submit() {
    if (unansweredCount > 0 && !window.confirm(`You have ${unansweredCount} unanswered question${unansweredCount === 1 ? "" : "s"}. Submit anyway?`)) return;
    setSubmitting(true);
    setError("");
    const session = readSession(subject, subject);
    const response = await fetch("/api/prototype/cycle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject,
        diagnosticResponses: responseEntries(session.answers),
        reassessmentResponses: questions.map((item) => ({ questionId: item.id, choiceId: answers[item.id] ?? null })),
      }),
    }).catch(() => null);

    if (!response?.ok) {
      setError("Your answers are saved, but the reassessment could not be scored. Try again.");
      setSubmitting(false);
      return;
    }

    const nextResult = (await response.json()) as AssessmentScore;
    writeSession({ ...readSession(subject, subject), reassessmentAnswers: answers, cycleScores: { ...session.cycleScores, [skillId]: nextResult } });
    setResult(nextResult);
    setSubmitting(false);
  }

  return (
    <PageFrame>
      <Link href={`/practice/${subject}/${skillId}`} className="text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline">← Back to practice</Link>
      <div className="mt-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Unseen reassessment</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">What transferred?</h1>
        </div>
        <p className="text-sm text-slate-500">Question {currentIndex + 1} of {questions.length}</p>
      </div>
      <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">These questions are separate from practice. Feedback will appear after you submit the set.</p>

      <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        {question.context ? <p className="rounded-md bg-slate-50 p-4 text-base leading-7 text-slate-800">{question.context}</p> : null}
        <h2 className="mt-5 text-xl font-semibold leading-8 text-slate-950">{question.prompt}</h2>
        <div className="mt-6 space-y-3">
          {question.choices.map((choice) => {
            const selected = answers[question.id] === choice.id;
            return <button key={choice.id} type="button" role="radio" aria-checked={selected} onClick={() => choose(choice.id)} className={`flex w-full items-start gap-3 rounded-lg border p-4 text-left text-sm leading-6 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 ${selected ? "border-emerald-700 bg-emerald-50" : "border-slate-200 hover:border-slate-400 hover:bg-slate-50"}`}><span className={`flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${selected ? "border-emerald-700 bg-emerald-700 text-white" : "border-slate-300 text-slate-600"}`}>{choice.id}</span><span>{choice.text}</span></button>;
          })}
        </div>
      </section>
      {error ? <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900" role="alert">{error}</p> : null}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <button type="button" disabled={currentIndex === 0} onClick={() => setCurrentIndex((index) => index - 1)} className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 disabled:opacity-40 hover:bg-slate-100">Previous</button>
        {currentIndex < questions.length - 1 ? <button type="button" onClick={() => setCurrentIndex((index) => index + 1)} className="h-10 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800">Next question</button> : <button type="button" disabled={submitting} onClick={submit} className="h-10 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{submitting ? "Scoring…" : "Submit reassessment"}</button>}
      </div>
    </PageFrame>
  );
}

function Outcome({ subject, skillId, result }: { subject: Subject; skillId: string; result: AssessmentScore }) {
  const snapshot = result.snapshots.find((candidate) => candidate.skillId === skillId);
  return (
    <PageFrame>
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Cycle complete</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">Your evidence has been updated.</h1>
      <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">The reassessment used new items and was combined with your diagnostic evidence. It does not produce an official ACT score.</p>
      {snapshot ? <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-4"><h2 className="text-xl font-semibold">Current skill estimate</h2><StatusLabel classification={snapshot.classification} /></div><p className="mt-4 text-sm leading-6 text-slate-600">{snapshot.reason} {snapshot.omittedCount ? `${snapshot.omittedCount} item${snapshot.omittedCount === 1 ? " was" : "s were"} omitted and kept separate from correctness.` : ""}</p></div> : null}
      <div className="mt-6 flex flex-wrap gap-3"><Link href={`/results/${subject}`} className="inline-flex h-10 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Review priorities</Link><Link href="/progress" className="inline-flex h-10 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-100">View progress</Link></div>
    </PageFrame>
  );
}

function ReassessmentMessage({ children }: { children: import("react").ReactNode }) {
  return <PageFrame><div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm" role="status">{children}</div></PageFrame>;
}
