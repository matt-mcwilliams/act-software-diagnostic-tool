"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageFrame } from "@/components/act/page-frame";
import { StatusLabel } from "@/components/act/status-label";
import { readSession, saveIssue } from "@/lib/act/prototype-state";
import type { Skill, Subject } from "@/lib/act/types";

export function LearnView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const [skill, setSkill] = useState<Skill | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch(`/api/prototype/catalog?subject=${subject}`)
      .then((response) => response.json() as Promise<{ skills: Skill[] }>)
      .then(({ skills }) => setSkill(skills.find((candidate) => candidate.id === skillId) ?? null));
  }, [skillId, subject]);

  if (!skill) return <PageFrame><div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm" role="status">Loading the learning path…</div></PageFrame>;

  const currentSkill = skill;
  const session = readSession(subject, subject);
  const snapshot = session.score?.snapshots.find((candidate) => candidate.skillId === currentSkill.id);
  const recommendation = session.score?.recommendations.find((candidate) => candidate.skillId === currentSkill.id);

  function reportProblem() {
    saveIssue(session, `Resource or diagnosis issue for ${currentSkill.id}`);
    setMessage("Thanks — this issue is recorded for pilot review.");
  }

  return (
    <PageFrame>
      <Link href={`/results/${subject}`} className="text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline">← Back to results</Link>
      <div className="mt-8 max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Focused learning</p>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{currentSkill.name}</h1>
            <p className="mt-2 text-sm text-slate-500">{currentSkill.category}</p>
          </div>
          {snapshot ? <StatusLabel classification={snapshot.classification} /> : null}
        </div>

        <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-lg font-semibold text-slate-950">What this skill means</h2>
          <p className="mt-3 text-base leading-7 text-slate-700">{currentSkill.definition}</p>
          <p className="mt-4 text-sm leading-6 text-slate-600">{currentSkill.whyItMatters}</p>
          {recommendation ? <p className="mt-5 rounded-md bg-emerald-50 p-4 text-sm leading-6 text-emerald-950">{recommendation.explanation}</p> : null}
        </div>

        <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Start with this resource</p>
          <h2 className="mt-3 text-xl font-semibold text-slate-950">{currentSkill.resources[0].title}</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">{currentSkill.resources[0].note}</p>
          <a href={currentSkill.resources[0].url} target="_blank" rel="noreferrer" className="mt-5 inline-flex h-10 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-100">Open resource ↗</a>
          <p className="mt-4 text-xs leading-5 text-slate-500">Opening a resource is recorded as engagement only; it does not count as proof of mastery.</p>
        </section>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
          <button type="button" onClick={reportProblem} className="text-sm font-semibold text-slate-600 underline-offset-4 hover:text-slate-950 hover:underline">Report a problem</button>
          <Link href={`/practice/${subject}/${skill.id}`} className="inline-flex h-11 items-center rounded-md bg-emerald-700 px-5 text-sm font-semibold text-white hover:bg-emerald-800">Continue to practice</Link>
        </div>
        {message ? <p className="mt-4 text-sm text-emerald-800" role="status">{message}</p> : null}
      </div>
    </PageFrame>
  );
}
