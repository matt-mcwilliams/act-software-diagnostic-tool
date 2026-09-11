"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { PageFrame } from "@/components/act/page-frame";
import { StatusLabel } from "@/components/act/status-label";
import type { FastApiAssessmentResult } from "@/lib/api/contracts";
import { readSession } from "@/lib/act/prototype-state";
import type { Skill, Subject } from "@/lib/act/types";

export function ResultsView({ subject }: { subject: Subject }) {
  const [session] = useState(() => readSession(subject, subject));
  const [skills, setSkills] = useState<Skill[]>([]);
  const [mode, setMode] = useState<"loading" | "local" | "fastapi" | "error">("loading");
  const [backendResult, setBackendResult] = useState<FastApiAssessmentResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadResults() {
      const modeResponse = await fetch("/api/assessment/mode", { cache: "no-store" });
      if (!modeResponse.ok) throw new Error("The results service could not be reached.");
      const modeBody = await modeResponse.json() as { mode?: "local" | "fastapi" };

      if (modeBody.mode === "fastapi") {
        const sessionId = window.localStorage.getItem(`act-fastapi-session:${subject}`);
        if (!sessionId) throw new Error("No durable diagnostic session was found in this browser.");
        const response = await fetch(`/api/assessment/sessions/${sessionId}/results`, { cache: "no-store" });
        if (!response.ok) {
          const body = await response.json().catch(() => null) as { error?: { message?: string } } | null;
          throw new Error(body?.error?.message || "Your durable results are not ready yet.");
        }
        if (!active) return;
        setBackendResult(await response.json() as FastApiAssessmentResult);
        setMode("fastapi");
        return;
      }

      if (modeBody.mode !== "local") throw new Error("The results service returned an invalid mode.");
      const catalogResponse = await fetch(`/api/prototype/catalog?subject=${subject}`, { cache: "no-store" });
      if (!catalogResponse.ok) throw new Error("The skill catalog could not be loaded.");
      const { skills: loadedSkills } = await catalogResponse.json() as { skills: Skill[] };
      if (!active) return;
      setSkills(loadedSkills);
      setMode("local");
    }

    loadResults().catch((loadError: unknown) => {
      if (!active) return;
      setError(loadError instanceof Error ? loadError.message : "Your results could not be loaded.");
      setMode("error");
    });

    return () => {
      active = false;
    };
  }, [subject]);

  const latestCycleScore = Object.values(session.cycleScores).at(-1);
  const score = latestCycleScore ?? session.score ?? null;

  if (mode === "loading") return <Message>Loading your results…</Message>;
  if (mode === "error") {
    return (
      <Message>
        <p>{error}</p>
        <Link href={`/diagnostic/${subject}`} className="mt-5 inline-flex h-10 items-center rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800">Go to diagnostic</Link>
      </Message>
    );
  }
  if (mode === "fastapi" && backendResult) return <BackendResultsView result={backendResult} />;
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
        <p className="mt-2 text-2xl font-semibold text-slate-950">{session.score?.correct ?? score.correct} of {session.score?.total ?? score.total} correct</p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">These results describe the evidence from this short diagnostic. They are a starting point for choosing what to study, not an official ACT score.</p>
        {latestCycleScore ? <p className="mt-3 text-xs font-medium text-emerald-800">Targets below include your latest completed reassessment.</p> : null}
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

function BackendResultsView({ result }: { result: FastApiAssessmentResult }) {
  const targets = result.recommendations.slice(0, 4);

  return (
    <PageFrame>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">{result.subject === "english" ? "English" : "Math"} results</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Here is what to work on next.</h1>
        </div>
        <Link href="/progress" className="text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline">View progress</Link>
      </div>

      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-600">Diagnostic summary</p>
        <p className="mt-2 text-2xl font-semibold text-slate-950">{result.correct} of {result.total} correct</p>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">These results describe the evidence from this short diagnostic. They are a starting point for choosing what to study, not an official ACT score.</p>
        <p className="mt-3 text-xs font-medium text-emerald-800">Durable scoring: {result.scoring_version} · Mastery model: {result.mastery_model_version}</p>
      </div>

      <section className="mt-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Recommended targets</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Start with one of these.</h2>
          </div>
          <span className="text-sm text-slate-500">Ranked by durable evidence</span>
        </div>

        {targets.length === 0 ? (
          <div className="mt-5 rounded-xl border border-slate-200 bg-slate-100 p-5 text-sm leading-6 text-slate-700">
            Your durable result is saved. Target recommendations will appear when the learning inventory has been approved for this subject.
          </div>
        ) : (
          <div className="mt-5 grid gap-4">
            {targets.map((recommendation) => {
              const snapshot = result.snapshots.find((candidate) => candidate.skill_id === recommendation.skill_id);
              return (
                <article key={recommendation.skill_id} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-emerald-700">Priority {recommendation.rank}</p>
                      <h3 className="mt-2 text-xl font-semibold text-slate-950">{recommendation.skill_name}</h3>
                      <p className="mt-1 text-sm text-slate-500">{recommendation.skill_key}</p>
                    </div>
                    {snapshot ? <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{formatClassification(snapshot.classification)}</span> : null}
                  </div>
                  <p className="mt-5 max-w-2xl text-sm leading-6 text-slate-600">{recommendation.explanation}</p>
                  <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-4">
                    <p className="text-xs text-slate-500">{snapshot ? `Evidence: ${snapshot.correct_count} correct · ${snapshot.incorrect_count} incorrect` : "Evidence recorded in the durable profile"}</p>
                    <span className={`text-xs font-semibold ${recommendation.readiness ? "text-emerald-800" : "text-slate-500"}`}>
                      {recommendation.readiness ? "Learning path ready" : "Learning path pending review"}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <div className="mt-8 rounded-lg border border-slate-200 bg-slate-100 p-4 text-sm leading-6 text-slate-700">
        <strong>How to read this:</strong> Mastery estimates become more dependable as you complete targeted practice and reassessment cycles.
      </div>
    </PageFrame>
  );
}

function formatClassification(classification: string) {
  return classification
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function Message({ children }: { children: ReactNode }) {
  return <PageFrame><div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm">{children}</div></PageFrame>;
}
