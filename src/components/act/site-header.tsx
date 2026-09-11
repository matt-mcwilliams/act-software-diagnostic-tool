import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4 sm:px-8">
        <Link href="/" className="flex items-center gap-3" aria-label="ACT Adaptive home">
          <span className="flex size-9 items-center justify-center rounded-full bg-emerald-700 text-sm font-bold text-white">
            A
          </span>
          <span>
            <span className="block text-sm font-semibold tracking-tight text-slate-950">ACT Adaptive</span>
            <span className="block text-xs text-slate-500">English + Math pilot</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm" aria-label="Primary navigation">
          <Link className="rounded-md px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950" href="/start">
            Start
          </Link>
          <Link className="rounded-md px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950" href="/progress">
            Progress
          </Link>
        </nav>
      </div>
    </header>
  );
}
