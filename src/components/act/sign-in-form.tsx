"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { createClient } from "@/lib/supabase/client";
import { getOptionalSupabaseConfig } from "@/lib/supabase/env";

export function SignInForm() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const configured = Boolean(getOptionalSupabaseConfig());

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setPending(true);

    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
      });
      if (error) throw error;
      setMessage("Check your email for a sign-in link.");
    } catch {
      setMessage("We could not send that link. Check the email address and Supabase configuration.");
    } finally {
      setPending(false);
    }
  }

  if (!configured) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-7 shadow-sm">
        <p className="text-sm leading-6 text-slate-600">Supabase is not configured in this local environment. You can still exercise the prototype loop with browser-local progress.</p>
        <Link href="/start" className="mt-6 inline-flex h-10 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">Continue in prototype mode</Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-slate-200 bg-white p-7 shadow-sm">
      <label htmlFor="email" className="text-sm font-semibold text-slate-900">Email address</label>
      <input id="email" name="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" className="mt-2 h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-700/20" />
      <button type="submit" disabled={pending} className="mt-5 inline-flex h-10 items-center rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{pending ? "Sending…" : "Send sign-in link"}</button>
      {message ? <p className="mt-4 text-sm leading-6 text-slate-700" role="status">{message}</p> : null}
    </form>
  );
}
