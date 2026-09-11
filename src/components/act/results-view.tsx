"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { PageFrame } from "@/components/act/page-frame";
import { StatusLabel } from "@/components/act/status-label";
import { readSession } from "@/lib/act/prototype-state";
import type { AssessmentScore } from "@/lib/act/scoring";
import type { Skill, Subject } from "@/lib/act/types";

export function ResultsView({ subject }: { subject: Subject }) {
  const [score] = useState<AssessmentScore | null>(() => readSession(subject, subject).score ?? null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/prototype/catalog?subject=${subject}`)
      .then((response) => response.json() as Promise<{ skills: Skill[] }>)
      .then(({ skills: loadedSkills }) => setSkills(loadedSkills))
      .finally(() => setLoading(false));
  }, [subject]);

  if (loading) return <Message>Loading your results…</Message>;
  if (!score) {
    return (
      <Message>
        <p>You have not submitted this diagnostic yet.</p>
        <Link href={`/diagnostic/${subject}`} className="mt-5 inline-flex h-10 items-center rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800">Go to diagnostic</Link>
      </Message>
    );
  }

  const targets = score.recommendations.filter((recommendation) => recommendation.readiness).slice(0, 4);

  return (
    <PageFrame>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">{subject === "english" ? "English" : "Math"} results</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Here is what to work on next.</h1>
        </div>
        <Link href="/progress" className="text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline">View progress</Link>
      </div>

      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-600">Diagnostic summary</p>
        <p className="mt-2 text-2xl font-semibold text-slate-950">{score.correct} of {score.total} correct</p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">These results describe the evidence from this short diagnostic. They are a starting point for choosing what to study, not an official ACT score.</p>
      </div>

      <section className="mt-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Recommended targets</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Start with one of these.</h2>
          </div>
          <span className="text-sm text-slate-500">Ranked by evidence and readiness</span>
        </div>

        <div className="mt-5 grid gap-4">
          {targets.map((recommendation) => {
            const skill = skills.find((candidate) => candidate.id === recommendation.skillId);
            const snapshot = score.snapshots.find((candidate) => candidate.skillId === recommendation.skillId);
            if (!skill || !snapshot) return null;
            return (
              <article key={skill.id} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700">Priority {recommendation.rank}</p>
                    <h3 className="mt-2 text-xl font-semibold text-slate-950">{skill.name}</h3>
                    <p className="mt-1 text-sm text-slate-500">{skill.category}</p>
                  </div>
                  <StatusLabel classification={snapshot.classification} />
                </div>
                <p className="mt-5 max-w-2xl text-sm leading-6 text-slate-600">{recommendation.explanation}</p>
                <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-4">
                  <p className="text-xs text-slate-500">Evidence: {snapshot.correctCount} correct · {snapshot.incorrectCount} incorrect</p>
                  <Link href={`/learn/${subject}/${skill.id}`} className="inline-flex h-9 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Learn this skill</Link>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <div className="mt-8 rounded-lg border border-slate-200 bg-slate-100 p-4 text-sm leading-6 text-slate-700">
        <strong>How to read this:</strong> “More evidence needed” means the response pattern is not yet dependable enough to call a weakness or strength. The next targeted cycle can make that estimate clearer.
      </div>
    </PageFrame>
  );
}

function Message({ children }: { children: ReactNode }) {
  return <PageFrame><div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm">{children}</div></PageFrame>;
}
