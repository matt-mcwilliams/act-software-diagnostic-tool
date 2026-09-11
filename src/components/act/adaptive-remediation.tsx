"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { FastApiSessionPlayer } from "@/components/act/fastapi-session-player";
import { PageFrame } from "@/components/act/page-frame";
import type {
  FastApiAssessmentResult,
  FastApiAssessmentSession,
  FastApiMasteryResponse,
  FastApiPracticeSet,
  FastApiRemediationCycle,
  FastApiRemediationCycleSummary,
} from "@/lib/api/contracts";
import type { Subject } from "@/lib/act/types";
import { LearnView } from "@/components/act/learn-view";
import { PracticeView } from "@/components/act/practice-view";
import { ProgressView } from "@/components/act/progress-view";
import { ReassessmentView } from "@/components/act/reassessment-view";

type AssessmentMode = "local" | "fastapi";

const cycleKey = (subject: Subject, skillId: string) => `act-fastapi-cycle:${subject}:${skillId}`;

function requestId() {
  return crypto.randomUUID();
}

async function responseError(response: Response, fallback: string) {
  const body = await response.json().catch(() => null) as { error?: { message?: string } } | null;
  return body?.error?.message || fallback;
}

function useAssessmentMode() {
  const [mode, setMode] = useState<AssessmentMode | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/api/assessment/mode", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("The assessment service could not be reached.");
        return response.json() as Promise<{ mode?: AssessmentMode }>;
      })
      .then((body) => {
        if (!active) return;
        if (body.mode !== "local" && body.mode !== "fastapi") throw new Error("The assessment service returned an invalid mode.");
        setMode(body.mode);
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "The assessment service could not be reached.");
      });
    return () => {
      active = false;
    };
  }, []);

  return { mode, error };
}

export function AdaptiveLearnView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const { mode, error } = useAssessmentMode();
  if (error) return <ModeMessage message={error} />;
  if (!mode) return <ModeMessage message="Preparing your learning path…" status />;
  return mode === "fastapi" ? <FastApiLearnView subject={subject} skillId={skillId} /> : <LearnView subject={subject} skillId={skillId} />;
}

export function AdaptivePracticeView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const { mode, error } = useAssessmentMode();
  if (error) return <ModeMessage message={error} />;
  if (!mode) return <ModeMessage message="Preparing targeted practice…" status />;
  return mode === "fastapi" ? <FastApiPracticeView subject={subject} skillId={skillId} /> : <PracticeView subject={subject} skillId={skillId} />;
}

export function AdaptiveReassessmentView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const { mode, error } = useAssessmentMode();
  if (error) return <ModeMessage message={error} />;
  if (!mode) return <ModeMessage message="Preparing your reassessment…" status />;
  return mode === "fastapi" ? <FastApiReassessmentView subject={subject} skillId={skillId} /> : <ReassessmentView subject={subject} skillId={skillId} />;
}

export function AdaptiveProgressView() {
  const { mode, error } = useAssessmentMode();
  if (error) return <ModeMessage message={error} />;
  if (!mode) return <ModeMessage message="Loading your progress…" status />;
  return mode === "fastapi" ? <FastApiProgressView /> : <ProgressView />;
}

function FastApiProgressView() {
  const [records, setRecords] = useState<Array<{ subject: Subject; mastery: FastApiMasteryResponse; cycles: FastApiRemediationCycleSummary[] }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all(["english", "math"].map(async (subject) => {
      const [masteryResponse, cyclesResponse] = await Promise.all([
        fetch(`/api/assessment/mastery?subject=${subject}`, { cache: "no-store" }),
        fetch(`/api/assessment/cycles?subject=${subject}`, { cache: "no-store" }),
      ]);
      if (!masteryResponse.ok || !cyclesResponse.ok) throw new Error("Your durable progress could not be loaded.");
      return {
        subject: subject as Subject,
        mastery: await masteryResponse.json() as FastApiMasteryResponse,
        cycles: await cyclesResponse.json() as FastApiRemediationCycleSummary[],
      };
    }))
      .then((loadedRecords) => {
        if (!active) return;
        setRecords(loadedRecords);
        setLoading(false);
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "Your durable progress could not be loaded.");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) return <ModeMessage message="Loading your progress…" status />;
  if (error) return <ModeMessage message={error} />;

  return (
    <PageFrame>
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Progress</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Keep the next step visible.</h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">This view stays intentionally small: current durable targets, active cycles, and a clear way back into the loop.</p>

      <div className="mt-8 grid gap-6">
        {records.map(({ subject, mastery, cycles }) => {
          const snapshotBySkill = new Map(mastery.snapshots.map((snapshot) => [snapshot.skill_id, snapshot]));
          const targets = mastery.recommendations.filter((recommendation) => (snapshotBySkill.get(recommendation.skill_id)?.effective_evidence ?? 0) > 0).slice(0, 3);
          const activeCycles = cycles.filter((cycle) => !["mastered", "abandoned"].includes(cycle.status)).slice(0, 3);
          return (
            <section key={subject} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">{subject === "english" ? "English" : "Math"}</p>
                  <h2 className="mt-2 text-xl font-semibold">{targets.length > 0 ? "Current priorities" : "No active targets yet"}</h2>
                </div>
                <Link href={`/results/${subject}`} className="text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline">Review results</Link>
              </div>
              {targets.length > 0 ? <div className="mt-5 space-y-3">{targets.map((recommendation) => { const snapshot = snapshotBySkill.get(recommendation.skill_id); return <div key={recommendation.skill_id} className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-3"><div><Link href={`/learn/${subject}/${recommendation.skill_id}`} className="font-medium text-slate-900 hover:underline">{recommendation.skill_name}</Link><p className="mt-1 text-xs text-slate-500">{snapshot ? `${snapshot.correct_count} correct · ${snapshot.incorrect_count} incorrect` : "Evidence recorded"}</p></div><span className="text-xs font-semibold text-slate-600">{formatStatus(snapshot?.classification ?? "developing")}</span></div>; })}</div> : <p className="mt-4 text-sm leading-6 text-slate-600">Complete a durable diagnostic to create a traceable skill profile.</p>}
              {activeCycles.length > 0 ? <div className="mt-5 border-t border-slate-200 pt-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Active cycles</p><div className="mt-3 space-y-2">{activeCycles.map((cycle) => <p key={cycle.id} className="text-sm text-slate-700">{cycle.skill_name} <span className="text-xs text-slate-500">· {formatStatus(cycle.status)}</span></p>)}</div></div> : null}
            </section>
          );
        })}
      </div>
    </PageFrame>
  );
}

function FastApiLearnView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const router = useRouter();
  const [cycle, setCycle] = useState<FastApiRemediationCycle | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadCycle() {
      const storedId = window.localStorage.getItem(cycleKey(subject, skillId));
      let response = storedId
        ? await fetch(`/api/assessment/cycles/${storedId}`, { cache: "no-store" })
        : null;
      if (!response?.ok) {
        response = await fetch("/api/assessment/cycles", {
          method: "POST",
          headers: { "content-type": "application/json", "idempotency-key": requestId() },
          body: JSON.stringify({ skill_id: skillId }),
          cache: "no-store",
        });
      }
      if (!response.ok) throw new Error(await responseError(response, "The learning path could not be loaded."));
      const loaded = await response.json() as FastApiRemediationCycle;
      if (!active) return;
      window.localStorage.setItem(cycleKey(subject, skillId), loaded.id);
      setCycle(loaded);
      setLoading(false);
    }
    loadCycle().catch((loadError: unknown) => {
      if (!active) return;
      setError(loadError instanceof Error ? loadError.message : "The learning path could not be loaded.");
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [skillId, subject]);

  async function startPractice() {
    if (!cycle) return;
    setBusy(true);
    setError("");
    try {
      let nextCycle = cycle;
      if (!cycle.practice_set_id) {
        const response = await fetch(`/api/assessment/cycles/${cycle.id}/practice-sets`, {
          method: "POST",
          headers: { "idempotency-key": requestId() },
          cache: "no-store",
        });
        if (!response.ok) throw new Error(await responseError(response, "Targeted practice is not ready yet."));
        const practiceSet = await response.json() as FastApiPracticeSet;
        const cycleResponse = await fetch(`/api/assessment/cycles/${cycle.id}`, { cache: "no-store" });
        nextCycle = cycleResponse.ok ? await cycleResponse.json() as FastApiRemediationCycle : { ...cycle, practice_set_id: practiceSet.id, practice_session_id: practiceSet.assessment_session_id };
        setCycle(nextCycle);
        window.localStorage.setItem(cycleKey(subject, skillId), nextCycle.id);
      }
      router.push(`/practice/${subject}/${skillId}`);
    } catch (startError: unknown) {
      setError(startError instanceof Error ? startError.message : "Targeted practice is not ready yet.");
    } finally {
      setBusy(false);
    }
  }

  function recordResource(resourceId: string) {
    if (!cycle) return;
    void fetch(`/api/assessment/cycles/${cycle.id}/resource-events`, {
      method: "POST",
      headers: { "content-type": "application/json", "idempotency-key": requestId() },
      body: JSON.stringify({ resource_id: resourceId, event_type: "resource_opened" }),
    });
  }

  if (loading) return <ModeMessage message="Loading the learning path…" status />;
  if (error && !cycle) return <ModeMessage message={error} />;
  if (!cycle) return <ModeMessage message="No learning path was found." />;

  return (
    <div>
      <Link href={`/results/${subject}`} className="text-sm font-semibold text-emerald-800 underline-offset-4 hover:underline">← Back to results</Link>
      <div className="mt-8 max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Focused learning</p>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{cycle.skill_name}</h1>
            <p className="mt-2 text-sm text-slate-500">{cycle.skill_key}</p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{formatStatus(cycle.status)}</span>
        </div>

        <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-lg font-semibold text-slate-950">Why this is a target</h2>
          <p className="mt-3 text-base leading-7 text-slate-700">Work through one focused resource, then answer new practice questions before reassessing this skill.</p>
        </section>

        <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Instruction</p>
          {cycle.resources.length === 0 ? (
            <p className="mt-4 rounded-md bg-slate-100 p-4 text-sm leading-6 text-slate-700">An approved learning resource is not available for this skill yet.</p>
          ) : (
            <div className="mt-4 space-y-4">
              {cycle.resources.map((resource) => (
                <div key={resource.id} className="rounded-lg border border-slate-200 p-4">
                  <h2 className="font-semibold text-slate-950">{resource.title}</h2>
                  <p className="mt-1 text-xs text-slate-500">{resource.provider}</p>
                  {resource.focus_note ? <p className="mt-3 text-sm leading-6 text-slate-600">{resource.focus_note}</p> : null}
                  <a href={resource.url} target="_blank" rel="noreferrer" onClick={() => recordResource(resource.id)} className="mt-4 inline-flex h-9 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-100">Open resource ↗</a>
                </div>
              ))}
            </div>
          )}
        </section>

        {error ? <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900" role="alert">{error}</p> : null}
        <button type="button" onClick={startPractice} disabled={busy} className="mt-6 inline-flex h-11 items-center rounded-md bg-emerald-700 px-5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{busy ? "Preparing practice…" : cycle.practice_set_id ? "Continue to practice" : "Start targeted practice"}</button>
      </div>
    </div>
  );
}

function FastApiPracticeView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const [cycle, setCycle] = useState<FastApiRemediationCycle | null>(null);
  const [practiceSet, setPracticeSet] = useState<FastApiPracticeSet | null>(null);
  const [result, setResult] = useState<FastApiAssessmentResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadPractice() {
      const storedId = window.localStorage.getItem(cycleKey(subject, skillId));
      let cycleResponse = storedId ? await fetch(`/api/assessment/cycles/${storedId}`, { cache: "no-store" }) : null;
      if (!cycleResponse?.ok) {
        cycleResponse = await fetch("/api/assessment/cycles", {
          method: "POST",
          headers: { "content-type": "application/json", "idempotency-key": requestId() },
          body: JSON.stringify({ skill_id: skillId }),
          cache: "no-store",
        });
      }
      if (!cycleResponse.ok) throw new Error(await responseError(cycleResponse, "The practice cycle could not be loaded."));
      const loadedCycle = await cycleResponse.json() as FastApiRemediationCycle;
      if (!loadedCycle.practice_set_id) throw new Error("Start the learning path before opening practice.");
      const setResponse = await fetch(`/api/assessment/practice-sets/${loadedCycle.practice_set_id}`, { cache: "no-store" });
      if (!setResponse.ok) throw new Error(await responseError(setResponse, "Targeted practice could not be loaded."));
      if (!active) return;
      window.localStorage.setItem(cycleKey(subject, skillId), loadedCycle.id);
      setCycle(loadedCycle);
      setPracticeSet(await setResponse.json() as FastApiPracticeSet);
      setLoading(false);
    }
    loadPractice().catch((loadError: unknown) => {
      if (!active) return;
      setError(loadError instanceof Error ? loadError.message : "Targeted practice could not be loaded.");
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [skillId, subject]);

  async function finishPractice(nextResult: FastApiAssessmentResult) {
    if (!cycle || !practiceSet) return;
    const response = await fetch(`/api/assessment/practice-sets/${practiceSet.id}/complete`, {
      method: "POST",
      headers: { "idempotency-key": requestId() },
      cache: "no-store",
    });
    if (!response.ok) throw new Error(await responseError(response, "Practice was scored but could not be marked complete."));
    const completedSet = await response.json() as FastApiPracticeSet;
    const cycleResponse = await fetch(`/api/assessment/cycles/${cycle.id}`, { cache: "no-store" });
    if (cycleResponse.ok) setCycle(await cycleResponse.json() as FastApiRemediationCycle);
    setPracticeSet(completedSet);
    setResult(nextResult);
  }

  if (loading) return <ModeMessage message="Loading targeted practice…" status />;
  if (error || !cycle || !practiceSet) return <ModeMessage message={error || "Targeted practice could not be loaded."} />;
  if (result || practiceSet.status === "completed") {
    return (
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Practice complete</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Ready for new questions?</h1>
        {result ? <p className="mt-4 text-base text-slate-700">You answered {result.correct} of {result.total} correctly.</p> : <p className="mt-4 text-sm leading-6 text-slate-600">This practice set is already complete. Your next questions will be unseen for this cycle.</p>}
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href={`/reassess/${subject}/${skillId}`} className="inline-flex h-10 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Start reassessment</Link>
          <Link href={`/learn/${subject}/${skillId}`} className="inline-flex h-10 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-100">Back to learning</Link>
        </div>
      </div>
    );
  }

  return <FastApiSessionPlayer session={practiceSet.assessment_session} eyebrow="Targeted practice" heading="Try the idea without help." description="Practice responses are scored after you submit the set. Feedback stays separate from the unseen reassessment." submitLabel="Submit practice" submittingLabel="Scoring…" onSubmitted={finishPractice} />;
}

function FastApiReassessmentView({ subject, skillId }: { subject: Subject; skillId: string }) {
  const [cycle, setCycle] = useState<FastApiRemediationCycle | null>(null);
  const [session, setSession] = useState<FastApiAssessmentSession | null>(null);
  const [result, setResult] = useState<FastApiAssessmentResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadReassessment() {
      const storedId = window.localStorage.getItem(cycleKey(subject, skillId));
      let cycleResponse = storedId ? await fetch(`/api/assessment/cycles/${storedId}`, { cache: "no-store" }) : null;
      if (!cycleResponse?.ok) {
        cycleResponse = await fetch("/api/assessment/cycles", {
          method: "POST",
          headers: { "content-type": "application/json", "idempotency-key": requestId() },
          body: JSON.stringify({ skill_id: skillId }),
          cache: "no-store",
        });
      }
      if (!cycleResponse.ok) throw new Error(await responseError(cycleResponse, "The reassessment cycle could not be loaded."));
      const loadedCycle = await cycleResponse.json() as FastApiRemediationCycle;
      let sessionResponse = loadedCycle.reassessment_session_id
        ? await fetch(`/api/assessment/sessions/${loadedCycle.reassessment_session_id}`, { cache: "no-store" })
        : null;
      if (!sessionResponse?.ok) {
        sessionResponse = await fetch(`/api/assessment/cycles/${loadedCycle.id}/reassessments`, {
          method: "POST",
          headers: { "idempotency-key": requestId() },
          cache: "no-store",
        });
      }
      if (!sessionResponse.ok) throw new Error(await responseError(sessionResponse, "Unseen reassessment is not ready yet."));
      const loadedSession = await sessionResponse.json() as FastApiAssessmentSession;
      if (!active) return;
      window.localStorage.setItem(cycleKey(subject, skillId), loadedCycle.id);
      setCycle(loadedCycle);
      if (["submitted", "scoring", "scored"].includes(loadedSession.status)) {
        const resultResponse = await fetch(`/api/assessment/sessions/${loadedSession.id}/results`, { cache: "no-store" });
        if (resultResponse.ok) setResult(await resultResponse.json() as FastApiAssessmentResult);
        else setSession(loadedSession);
      } else {
        setSession(loadedSession);
      }
      setLoading(false);
    }
    loadReassessment().catch((loadError: unknown) => {
      if (!active) return;
      setError(loadError instanceof Error ? loadError.message : "Unseen reassessment is not ready yet.");
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [skillId, subject]);

  function finishReassessment(nextResult: FastApiAssessmentResult) {
    setResult(nextResult);
  }

  if (loading) return <ModeMessage message="Loading unseen reassessment…" status />;
  if (error || !cycle) return <ModeMessage message={error || "Unseen reassessment is not ready yet."} />;
  if (result) {
    const snapshot = result.snapshots.find((candidate) => candidate.skill_id === skillId);
    return (
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Cycle complete</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Your evidence has been updated.</h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">This reassessment used new questions and was combined with your diagnostic evidence. It does not produce an official ACT score.</p>
        <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-600">Reassessment summary</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{result.correct} of {result.total} correct</p>
          {snapshot ? <p className="mt-4 text-sm leading-6 text-slate-600">Current estimate: {formatStatus(snapshot.classification)}. {snapshot.reason}</p> : null}
        </div>
        <div className="mt-6 flex flex-wrap gap-3"><Link href={`/results/${subject}`} className="inline-flex h-10 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Review priorities</Link><Link href="/progress" className="inline-flex h-10 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-100">View progress</Link></div>
      </div>
    );
  }
  if (!session) return <ModeMessage message="Unseen reassessment is not ready yet." />;

  return <FastApiSessionPlayer session={{ ...session, purpose: "reassessment" }} eyebrow="Unseen reassessment" heading="What transferred?" description="These questions are separate from practice. Feedback will appear after you submit the set." submitLabel="Submit reassessment" submittingLabel="Scoring…" onSubmitted={finishReassessment} />;
}

function formatStatus(value: string) {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function ModeMessage({ message, status = false }: { message: string; status?: boolean }) {
  return <div className={`rounded-xl border p-8 text-sm shadow-sm ${status ? "border-slate-200 bg-white text-slate-600" : "border-amber-200 bg-amber-50 text-amber-950"}`} role={status ? "status" : "alert"}>{message}</div>;
}
