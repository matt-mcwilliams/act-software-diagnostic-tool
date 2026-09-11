import Link from "next/link";

import { PageFrame } from "@/components/act/page-frame";

export default function Home() {
  return (
    <PageFrame>
      <section className="grid gap-12 py-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center lg:py-16">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">ACT adaptive learning pilot</p>
          <h1 className="mt-5 max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-6xl">
            Find the skill to work on next.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
            Take a short English or Math diagnostic, see an honest picture of your current evidence, and follow one focused path from learn to practice to reassessment.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/start"
              className="inline-flex h-11 items-center justify-center rounded-md bg-emerald-700 px-5 text-sm font-semibold text-white hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
            >
              Start a diagnostic
            </Link>
            <Link
              href="/progress"
              className="inline-flex h-11 items-center justify-center rounded-md border border-slate-300 bg-white px-5 text-sm font-semibold text-slate-700 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
            >
              View progress
            </Link>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">The loop</p>
          <ol className="mt-5 space-y-5">
            {[
              ["01", "Diagnose", "Answer a small set of questions without answer feedback."],
              ["02", "Learn + practice", "Use one curated resource, then try targeted items."],
              ["03", "Reassess", "Answer new questions and see whether the evidence changed."],
            ].map(([number, title, description]) => (
              <li key={number} className="flex gap-4">
                <span className="font-mono text-sm text-emerald-700">{number}</span>
                <div>
                  <h2 className="font-semibold text-slate-900">{title}</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-6 border-t border-slate-200 pt-4 text-xs leading-5 text-slate-500">
            Prototype mode stores progress in this browser. The question bank is authored demo content mapped to the current ACT taxonomy exports.
          </p>
        </div>
      </section>

      <section className="border-t border-slate-200 py-10">
        <div className="grid gap-5 sm:grid-cols-3">
          <div>
            <p className="text-sm font-semibold text-slate-900">Traceable</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">Every recommendation points back to scored skill evidence.</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Honest</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">Sparse evidence is shown as uncertainty, not false precision.</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Focused</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">The first version keeps the student experience small and readable.</p>
          </div>
        </div>
      </section>
    </PageFrame>
  );
}
