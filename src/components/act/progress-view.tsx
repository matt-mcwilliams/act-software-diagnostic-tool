"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageFrame } from "@/components/act/page-frame";
import { StatusLabel } from "@/components/act/status-label";
import { readSession, type PrototypeSession } from "@/lib/act/prototype-state";
import type { Skill, Subject } from "@/lib/act/types";

const subjects: Subject[] = ["english", "math"];

export function ProgressView() {
  const [sessions] = useState<PrototypeSession[]>(() => subjects.map((subject) => readSession(subject, subject)));
  const [skills, setSkills] = useState<Skill[]>([]);

  useEffect(() => {
    fetch("/api/prototype/catalog")
      .then((response) => response.json() as Promise<{ skills: Skill[] }>)
      .then(({ skills: loadedSkills }) => setSkills(loadedSkills));
  }, []);

  const startedSessions = sessions.filter((session) => session.score || Object.keys(session.answers).length > 0);

  return (
    <PageFrame>
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Progress</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Keep the next step visible.</h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">This view stays intentionally small: current targets, completed cycles, and a clear way back into the loop.</p>

      {startedSessions.length === 0 ? (
        <div className="mt-8 rounded-xl border border-slate-200 bg-white p-7 shadow-sm">
          <p className="text-sm text-slate-600">No diagnostic history in this browser yet.</p>
          <Link href="/start" className="mt-5 inline-flex h-10 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Start a diagnostic</Link>
        </div>
      ) : (
        <div className="mt-8 grid gap-6">
          {startedSessions.map((session) => {
            const subjectSkills = skills.filter((skill) => skill.subject === session.subject);
            const latestScore = Object.values(session.cycleScores).at(-1) ?? session.score;
            const targets = latestScore?.recommendations.filter((recommendation) => recommendation.readiness).slice(0, 3) ?? [];
            return (
              <section key={session.subject} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">{session.subject === "english" ? "English" : "Math"}</p>
                    <h2 className="mt-2 text-xl font-semibold">{session.score ? "Current priorities" : "Diagnostic in progress"}</h2>
                  </div>
                  <Link href={session.score ? `/results/${session.subject}` : `/diagnostic/${session.subject}`} className="text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline">{session.score ? "Review results" : "Resume diagnostic"}</Link>
                </div>
                {session.score ? <div className="mt-5 space-y-3">{targets.map((recommendation) => { const skill = subjectSkills.find((candidate) => candidate.id === recommendation.skillId); const snapshot = latestScore?.snapshots.find((candidate) => candidate.skillId === recommendation.skillId); if (!skill || !snapshot) return null; return <div key={skill.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-3"><div><p className="font-medium text-slate-900">{skill.name}</p><p className="mt-1 text-xs text-slate-500">{session.cycleScores[skill.id] ? "Cycle complete" : "Next target"}</p></div><StatusLabel classification={snapshot.classification} /></div>; })}</div> : <p className="mt-4 text-sm leading-6 text-slate-600">{Object.keys(session.answers).length} answer{Object.keys(session.answers).length === 1 ? "" : "s"} saved locally. You can continue where you left off.</p>}
                {session.score && Object.keys(session.cycleScores).length > 0 ? <p className="mt-5 border-t border-slate-200 pt-4 text-xs text-slate-500">Completed cycles: {Object.keys(session.cycleScores).length}</p> : null}
              </section>
            );
          })}
        </div>
      )}
    </PageFrame>
  );
}
