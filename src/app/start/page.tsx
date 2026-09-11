import { PageFrame } from "@/components/act/page-frame";
import { StartChooser } from "@/components/act/start-chooser";

export default function StartPage() {
  return (
    <PageFrame>
      <div className="max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-emerald-700">Start here</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">Choose a diagnostic</h1>
        <p className="mt-4 text-base leading-7 text-slate-600">
          Each diagnostic takes about 5 minutes in this prototype. You can leave and come back; answers are saved in this browser.
        </p>
      </div>
      <StartChooser />
    </PageFrame>
  );
}
