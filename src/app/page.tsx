import {
  ArrowUpRight,
  Check,
  CircleDot,
  GitBranch,
  LockKeyhole,
  ShieldCheck,
  Terminal,
  Wrench,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

const readiness = [
  { label: "Auth boundary", detail: "Supabase SSR", icon: ShieldCheck },
  { label: "Data layer", detail: "Drizzle + Postgres", icon: GitBranch },
  { label: "AI extension", detail: "Reserved, not connected", icon: Zap },
];

const workflow = [
  {
    number: "01",
    title: "Capture the signal",
    description: "Start with the symptom, the context, and the constraints around it.",
  },
  {
    number: "02",
    title: "Map the system",
    description: "Keep observations, dependencies, and decisions in one shared record.",
  },
  {
    number: "03",
    title: "Resolve with confidence",
    description: "Turn a vague failure into a clear next action and a durable trail.",
  },
];

const stack = [
  "Next.js App Router",
  "Supabase Auth + SSR",
  "Drizzle ORM + PostgreSQL",
  "Playwright + Vercel",
];

export default function Home() {
  return (
    <main className="grid-lines min-h-screen overflow-hidden">
      <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-5 py-5 sm:px-8 lg:px-12">
        <header className="flex items-center justify-between border-b border-white/10 pb-5">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-full bg-signal text-signal-foreground">
              <CircleDot className="size-5" strokeWidth={2.5} />
            </div>
            <div>
              <p className="font-mono text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-signal">
                ACT / 01
              </p>
              <p className="text-sm font-medium tracking-tight text-foreground">
                Software Diagnostic Tool
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge
              variant="outline"
              className="hidden border-white/15 bg-white/5 text-muted-foreground sm:inline-flex"
            >
              Private workspace
            </Badge>
            <div className="flex items-center gap-2 font-mono text-[0.65rem] uppercase tracking-[0.15em] text-muted-foreground">
              <span className="signal-pulse size-2 rounded-full bg-signal" />
              Ready
            </div>
          </div>
        </header>

        <section className="grid flex-1 items-center gap-12 py-14 lg:grid-cols-[1.1fr_0.9fr] lg:gap-20 lg:py-20">
          <div>
            <div className="mb-7 flex items-center gap-3 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <span className="h-px w-8 bg-signal" />
              Diagnosis starts with a better question
            </div>
            <h1 className="max-w-3xl text-5xl font-semibold leading-[0.98] tracking-[-0.06em] text-foreground sm:text-7xl lg:text-[5.5rem]">
              Find the fault
              <span className="block text-signal">before it finds you.</span>
            </h1>
            <p className="mt-8 max-w-xl text-lg leading-8 text-muted-foreground">
              A calm, structured workspace for turning software symptoms into clear next actions — with the context intact.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Button
                size="lg"
                className="h-11 gap-2 bg-signal px-5 text-signal-foreground hover:bg-signal/90"
              >
                Start a diagnostic
                <ArrowUpRight className="size-4" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="h-11 border-white/15 bg-transparent px-5 hover:bg-white/5"
              >
                Read the setup notes
              </Button>
            </div>

            <div className="mt-14 grid max-w-2xl gap-3 border-t border-white/10 pt-5 sm:grid-cols-3">
              {readiness.map(({ label, detail, icon: Icon }) => (
                <div key={label} className="flex gap-3">
                  <Icon className="mt-0.5 size-4 text-signal" />
                  <div>
                    <p className="text-sm font-medium text-foreground">{label}</p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Card className="relative overflow-hidden border-white/15 bg-card/80 shadow-2xl shadow-black/20">
            <div className="absolute right-0 top-0 size-32 translate-x-1/3 -translate-y-1/3 rounded-full bg-signal/10 blur-2xl" />
            <CardHeader className="relative gap-4 border-b border-white/10 pb-6">
              <div className="flex items-center justify-between">
                <Badge className="bg-signal/15 text-signal hover:bg-signal/15">New run</Badge>
                <span className="font-mono text-xs text-muted-foreground">DRAFT / 0001</span>
              </div>
              <div>
                <CardTitle className="text-2xl tracking-tight">What are you seeing?</CardTitle>
                <CardDescription className="mt-2 max-w-sm leading-6 text-muted-foreground">
                  Start a record with just enough detail to make the next conversation useful.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="relative space-y-5 pt-6">
              <div className="space-y-2">
                <Label htmlFor="diagnostic-name" className="text-xs font-medium text-muted-foreground">
                  Diagnostic name
                </Label>
                <Input
                  id="diagnostic-name"
                  placeholder="e.g. Checkout latency"
                  className="h-11 border-white/15 bg-white/[0.04] placeholder:text-muted-foreground/60"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="diagnostic-symptom" className="text-xs font-medium text-muted-foreground">
                  First signal
                </Label>
                <Textarea
                  id="diagnostic-symptom"
                  placeholder="Describe the symptom in plain language..."
                  className="min-h-28 resize-none border-white/15 bg-white/[0.04] placeholder:text-muted-foreground/60"
                />
              </div>
              <Button
                type="button"
                className="h-11 w-full gap-2 bg-foreground text-background hover:bg-foreground/90"
              >
                Create draft record
                <ArrowUpRight className="size-4" />
              </Button>
              <p className="flex items-center justify-center gap-2 text-center font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
                <LockKeyhole className="size-3" />
                Nothing leaves this workspace yet
              </p>
            </CardContent>
          </Card>
        </section>

        <section className="border-t border-white/10 py-12 lg:py-16">
          <div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr] lg:gap-20">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-signal">The working loop</p>
              <h2 className="mt-4 max-w-sm text-3xl font-semibold leading-tight tracking-[-0.04em] text-foreground">
                Less hunting. More signal.
              </h2>
              <p className="mt-4 max-w-sm leading-7 text-muted-foreground">
                The foundation is intentionally small so your team can shape the diagnostic workflow around the work.
              </p>
            </div>
            <div className="grid gap-0 sm:grid-cols-3">
              {workflow.map((item, index) => (
                <div
                  key={item.number}
                  className="relative border-t border-white/10 py-5 sm:border-l sm:border-t-0 sm:px-6 sm:first:border-l-0 sm:first:pl-0"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-signal">{item.number}</span>
                    {index === 0 ? <Wrench className="size-4 text-muted-foreground" /> : null}
                    {index === 1 ? <Terminal className="size-4 text-muted-foreground" /> : null}
                    {index === 2 ? <Check className="size-4 text-muted-foreground" /> : null}
                  </div>
                  <h3 className="mt-6 text-base font-medium text-foreground">{item.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-5 border-t border-white/10 py-12 sm:grid-cols-2 lg:py-16">
          <Card className="border-white/10 bg-white/[0.035]">
            <CardHeader>
              <CardTitle className="text-lg">Foundation online</CardTitle>
              <CardDescription className="leading-6 text-muted-foreground">
                The repository is wired for a production path from local diagnosis to authenticated, persisted runs.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              {stack.map((item) => (
                <div key={item} className="flex items-center gap-2 text-sm text-foreground">
                  <Check className="size-4 text-signal" />
                  {item}
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="border-signal/25 bg-signal/[0.07]">
            <CardHeader>
              <div className="flex items-center gap-2 text-signal">
                <CircleDot className="size-4" />
                <span className="font-mono text-xs uppercase tracking-[0.18em]">Deliberately quiet</span>
              </div>
              <CardTitle className="mt-2 text-lg">AI is an extension point, not a dependency.</CardTitle>
              <CardDescription className="leading-6 text-muted-foreground">
                Add an AI-assisted workflow when the product earns one. Until then, the core diagnostic loop stays explicit and inspectable.
              </CardDescription>
            </CardHeader>
          </Card>
        </section>

        <footer className="flex flex-col gap-3 border-t border-white/10 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono uppercase tracking-[0.15em]">ACT Diagnostic Tool / v0.1</p>
          <div className="flex items-center gap-4">
            <span>Built for clarity</span>
            <Separator orientation="vertical" className="h-3 bg-white/15" />
            <span>AI not connected</span>
          </div>
        </footer>
      </div>
    </main>
  );
}
