"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";

import { getServerStartStatusSnapshot, getStartStatusSnapshot, subscribeToPrototypeChanges } from "@/lib/act/prototype-state";
import type { Subject } from "@/lib/act/types";

const options: Array<{ subject: Subject; title: string; description: string; count: string }> = [
  {
    subject: "english",
    title: "English",
    description: "Punctuation, sentence boundaries, concision, and transitions.",
    count: "8 diagnostic questions",
  },
  {
    subject: "math",
    title: "Math",
    description: "Rates and percentages, equations, functions, and statistics.",
    count: "8 diagnostic questions",
  },
];

export function StartChooser() {
  const status = useSyncExternalStore(subscribeToPrototypeChanges, getStartStatusSnapshot, getServerStartStatusSnapshot);
  const statusBySubject = JSON.parse(status) as Array<"new" | "resume" | "results">;

  return (
    <div className="mt-10 grid gap-5 md:grid-cols-2">
      {options.map((option, index) => {
        const state = statusBySubject[index];
        const href = state === "results" ? `/results/${option.subject}` : `/diagnostic/${option.subject}`;
        const action = state === "results" ? "View results" : state === "resume" ? "Resume diagnostic" : "Start diagnostic";
        return (
          <article key={option.subject} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <h2 className="text-xl font-semibold text-slate-950">{option.title}</h2>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">{option.count}</span>
            </div>
            <p className="mt-4 min-h-12 text-sm leading-6 text-slate-600">{option.description}</p>
            <Link
              href={href}
              className="mt-6 inline-flex h-10 items-center justify-center rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
            >
              {action}
            </Link>
          </article>
        );
      })}
    </div>
  );
}
