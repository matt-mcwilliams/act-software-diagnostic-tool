import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5 text-slate-950">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-7 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">Not found</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">That learning path does not exist.</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">Choose a subject from the start page to begin a supported diagnostic.</p>
        <Link href="/start" className="mt-6 inline-flex h-10 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Choose a diagnostic</Link>
      </div>
    </main>
  );
}
