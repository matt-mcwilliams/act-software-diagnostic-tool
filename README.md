# ACT Adaptive

The first prototype of an adaptive ACT English and Math remediation loop:

```text
diagnose → see evidence-backed priorities → learn → practice → reassess
```

It is intentionally plain. The current goal is to make the learning loop
readable, testable, and inspectable before adding broader coverage or visual
complexity.

## Working now

- English and Math diagnostic entry points with resumable browser-local answers.
- Submit-time diagnostic scoring with no answer key in the question payload.
- Explainable weighted Beta-Binomial mastery bands and ranked skill targets.
- Curated resource links, targeted practice feedback, and unseen reassessment.
- Combined diagnostic + reassessment evidence with a minimal progress view.
- Supabase magic-link sign-in boundary that activates when public Supabase
  config is present; otherwise the app clearly runs in prototype mode.
- Optional server-to-server FastAPI `/v1/me` verification when
  `ACT_API_BASE_URL` is configured alongside Supabase.
- Reviewer-only canonical import preview and draft import endpoints with
  source-hash audit records.
- Authenticated FastAPI diagnostic catalog, session start/resume, and
  answer-key-free response-save contract with exposure and idempotency rules.
- FastAPI operational/authentication foundation at `services/api/`.
- PostgreSQL domain schema migration for versioned content, assessment facts,
  mastery evidence, remediation cycles, generated-content review, and pilot
  analytics.
- Canonical ACT exports organized under `content/exports/` and checked by a
  dry-run validator.

## Prototype boundary

The student flow currently stores session state in `localStorage`, and the
demo question bank is authored prototype content mapped to IDs from the
canonical taxonomy exports. It is not official ACT score-equivalent content.
The FastAPI service is not yet wired into the browser flow's persistence path;
the browser still uses local prototype routes. FastAPI now owns the planned
domain boundary for canonical imports and has the first PostgreSQL-backed
assessment session contract, which requires approved database content before
it can serve a student session.

## Local setup

```bash
pnpm install
cp .env.example .env.local
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Add Supabase variables to
`.env.local` to enable magic-link access. Set `ACT_API_BASE_URL` as well when
the configured pilot should verify the user with FastAPI. Without Supabase
variables, choose “Continue in prototype mode” on `/sign-in`.

## Commands

```bash
pnpm dev             # Start the Next.js app
pnpm lint            # Run ESLint
pnpm typecheck       # Check TypeScript
pnpm build           # Create a production build
pnpm test:e2e        # Run Playwright smoke tests
pnpm content:validate # Validate both canonical exports, without DB writes
pnpm api:install     # Install FastAPI service/test dependencies
pnpm api:dev         # Start FastAPI at 127.0.0.1:8000
pnpm api:test        # Run FastAPI tests
pnpm api:typecheck   # Compile-check FastAPI modules
pnpm db:generate     # Generate legacy Drizzle migrations
pnpm db:push         # Push the legacy Drizzle schema
```

## Project map

```text
src/app/                 Next.js App Router pages and prototype API routes
src/components/act/      Student loop UI and browser-local session behavior
src/lib/act/              Typed content contract and deterministic scoring
src/lib/supabase/         Browser/server clients and pilot route guard
services/api/             FastAPI identity/operations boundary and SQL schema
content/exports/          Canonical ACT taxonomy/content artifacts
tests/                    Playwright smoke coverage
docs/adr/                 Architecture decisions
```

## Pilot work still required

Before a real pilot, connect the student UI to the FastAPI session contract,
add submit/scoring/mastery/remediation writes, approve a reviewed blueprint
and inventory, add internal review/export tools, and complete the privacy,
rights, accessibility, and backup/restore gates in `plan.md`.
