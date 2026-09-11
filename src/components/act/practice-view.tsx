"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageFrame } from "@/components/act/page-frame";
import { readSession, writeSession } from "@/lib/act/prototype-state";
import type { ChoiceId, PublicQuestion, Subject } from "@/lib/act/types";

interface Feedback {
  correct: boolean;
  correctChoiceId: ChoiceId;
  explanation: string;
  failureMode?: string;
}

export function PracticeView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const [questions, setQuestions] = useState<PublicQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, ChoiceId>>({});
  const [feedback, setFeedback] = useState<Record<string, Feedback>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(() => Boolean(readSession(subject, subject).practiceComplete[skillId]));

  useEffect(() => {
    fetch(`/api/prototype/questions?subject=${subject}&purpose=practice`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Practice could not be loaded.");
        return response.json() as Promise<{ questions: PublicQuestion[] }>;
      })
      .then(({ questions: loadedQuestions }) => setQuestions(loadedQuestions.filter((question) => question.skillId === skillId)))
      .catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : "Practice could not be loaded."))
      .finally(() => setLoading(false));
  }, [skillId, subject]);

  if (loading) return <PracticeMessage>Loading targeted practice…</PracticeMessage>;
  if (error || questions.length === 0) return <PracticeMessage>{error || "There is no approved practice inventory for this skill yet."}</PracticeMessage>;

  const question = questions[currentIndex];
  const currentFeedback = feedback[question.id];

  async function choose(choiceId: ChoiceId) {
    setAnswers((current) => ({ ...current, [question.id]: choiceId }));
    setError("");
    try {
      const response = await fetch("/api/prototype/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ questionId: question.id, choiceId }),
      });
      if (!response.ok) throw new Error("Feedback could not be loaded. Try that answer again.");
      const result = (await response.json()) as Feedback;
      setFeedback((current) => ({ ...current, [question.id]: result }));
    } catch (answerError: unknown) {
      setError(answerError instanceof Error ? answerError.message : "Feedback could not be loaded.");
    }
  }

  function finish() {
    if (Object.keys(answers).length < questions.length) {
      setError("Answer each practice question before continuing to reassessment.");
      return;
    }
    const session = readSession(subject, subject);
    writeSession({ ...session, practiceComplete: { ...session.practiceComplete, [skillId]: true } });
    setComplete(true);
  }

  if (complete) {
    return (
      <PageFrame>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Practice complete</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Ready for new questions?</h1>
        <p className="mt-4 max-w-xl text-sm leading-6 text-slate-600">Your practice responses are kept separate from the reassessment. The next questions will be unseen for this cycle.</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href={`/reassess/${subject}/${skillId}`} className="inline-flex h-10 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Start reassessment</Link>
          <Link href={`/learn/${subject}/${skillId}`} className="inline-flex h-10 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-100">Back to learning</Link>
        </div>
      </PageFrame>
    );
  }

  return (
    <PageFrame>
      <Link href={`/learn/${subject}/${skillId}`} className="text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline">← Back to learning</Link>
      <div className="mt-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Targeted practice</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Try the idea without help.</h1>
        </div>
        <p className="text-sm text-slate-500">Question {currentIndex + 1} of {questions.length}</p>
      </div>

      <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        {question.context ? <p className="rounded-md bg-slate-50 p-4 text-base leading-7 text-slate-800">{question.context}</p> : null}
        <h2 className="mt-5 text-xl font-semibold leading-8 text-slate-950">{question.prompt}</h2>
        <div className="mt-6 space-y-3">
          {question.choices.map((choice) => {
            const selected = answers[question.id] === choice.id;
            const isCorrect = currentFeedback?.correctChoiceId === choice.id;
            const isWrong = selected && currentFeedback && !currentFeedback.correct;
            return (
              <button key={choice.id} type="button" onClick={() => choose(choice.id)} className={`flex w-full items-start gap-3 rounded-lg border p-4 text-left text-sm leading-6 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 ${isCorrect ? "border-emerald-700 bg-emerald-50" : isWrong ? "border-amber-400 bg-amber-50" : selected ? "border-slate-500 bg-slate-50" : "border-slate-200 hover:border-slate-400 hover:bg-slate-50"}`}>
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-slate-300 text-xs font-semibold">{choice.id}</span>
                <span>{choice.text}</span>
              </button>
            );
          })}
        </div>
        {currentFeedback ? <div className={`mt-6 rounded-md p-4 text-sm leading-6 ${currentFeedback.correct ? "bg-emerald-50 text-emerald-950" : "bg-amber-50 text-amber-950"}`} role="status"><strong>{currentFeedback.correct ? "Correct. " : "Not quite. "}</strong>{currentFeedback.explanation}{currentFeedback.failureMode ? <span className="block mt-2 text-xs">This response suggests: {currentFeedback.failureMode.replaceAll("_", " ")}.</span> : null}</div> : <p className="mt-5 text-xs text-slate-500">Choose an answer to see an explanation.</p>}
      </section>

      {error ? <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900" role="alert">{error}</p> : null}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <button type="button" disabled={currentIndex === 0} onClick={() => setCurrentIndex((index) => index - 1)} className="h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 disabled:opacity-40 hover:bg-slate-100">Previous</button>
        {currentIndex < questions.length - 1 ? <button type="button" onClick={() => setCurrentIndex((index) => index + 1)} className="h-10 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800">Next question</button> : <button type="button" onClick={finish} className="h-10 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Continue to reassessment</button>}
      </div>
    </PageFrame>
  );
}

function PracticeMessage({ children }: { children: import("react").ReactNode }) {
  return <PageFrame><div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm" role="status">{children}</div></PageFrame>;
}
