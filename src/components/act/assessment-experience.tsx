"use client";

import { useEffect, useState } from "react";

import { DiagnosticPlayer } from "@/components/act/diagnostic-player";
import { FastApiDiagnosticPlayer } from "@/components/act/fastapi-diagnostic-player";
import type { Subject } from "@/lib/act/types";

type AssessmentMode = "local" | "fastapi";

export function AssessmentExperience({ subject }: { subject: Subject }) {
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
        if (body.mode !== "local" && body.mode !== "fastapi") {
          throw new Error("The assessment service returned an invalid mode.");
        }
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

  if (error) return <ErrorMessage message={error} />;
  if (mode === "fastapi") return <FastApiDiagnosticPlayer subject={subject} />;
  if (mode === "local") return <DiagnosticPlayer subject={subject} />;
  return <LoadingMessage />;
}

function LoadingMessage() {
  return <div className="rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-600 shadow-sm" role="status">Preparing your diagnostic…</div>;
}

function ErrorMessage({ message }: { message: string }) {
  return <div className="rounded-xl border border-amber-200 bg-amber-50 p-8 text-sm text-amber-950" role="alert">{message}</div>;
}
