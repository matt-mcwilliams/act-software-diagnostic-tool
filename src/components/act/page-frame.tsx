import type { ReactNode } from "react";

import { SiteHeader } from "./site-header";

export function PageFrame({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <SiteHeader />
      <main className="mx-auto w-full max-w-5xl px-5 py-10 sm:px-8 sm:py-14">{children}</main>
    </div>
  );
}
