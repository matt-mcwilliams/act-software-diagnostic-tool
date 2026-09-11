import { PageFrame } from "@/components/act/page-frame";
import { SignInForm } from "@/components/act/sign-in-form";

export default function SignInPage() {
  return (
    <PageFrame>
      <div className="mx-auto max-w-md">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Pilot access</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">Sign in to continue.</h1>
        <p className="mt-4 text-sm leading-6 text-slate-600">Use the email address from your invite. We will send a one-time link; no password is needed.</p>
        <div className="mt-8"><SignInForm /></div>
      </div>
    </PageFrame>
  );
}
