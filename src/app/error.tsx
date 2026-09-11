"use client";

import Link from "next/link";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5 text-slate-950">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-7 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-amber-700">Something went wrong</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">This page could not finish loading.</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">Your locally saved answers are unchanged. Try the page again or return to the start.</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" onClick={reset} className="inline-flex h-10 items-center rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800">Try again</button>
          <Link href="/start" className="inline-flex h-10 items-center rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-100">Return to start</Link>
        </div>
      </div>
    </main>
  );
}
