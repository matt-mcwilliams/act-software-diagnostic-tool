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
- Optional FastAPI-backed diagnostic player with durable session resume,
  answer autosave, submission, and mastery-aware results when approved API
  content is available.
- Reviewer-only canonical import preview and draft import endpoints with
  source-hash audit records.
- Reviewer content review/publish and issue queue endpoints with explicit
  rights/answer-key confirmation gates.
- Authenticated learner issue reports and keyed, de-identified pilot exports.
- Authenticated FastAPI diagnostic catalog, session start/resume, and
  answer-key-free response-save contract with exposure and idempotency rules.
- FastAPI operational/authentication foundation at `services/api/`.
- PostgreSQL domain schema migration for versioned content, assessment facts,
  mastery evidence, remediation cycles, generated-content review, and pilot
  analytics.
- Canonical ACT exports organized under `content/exports/` and checked by a
  dry-run validator.

## Prototype boundary

Without `ACT_API_BASE_URL`, the student flow uses browser-local session state
and the authored demo question bank mapped to IDs from the canonical taxonomy
exports. It is not official ACT score-equivalent content. When the API base URL
and Supabase configuration are present, the diagnostic route switches to the
FastAPI session contract: PostgreSQL owns item assignment, answer revisions,
submission, scoring, mastery, and result state. That mode requires an approved
diagnostic blueprint and approved content in the API database.

## Local setup

```bash
pnpm install
cp .env.example .env.local
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Add Supabase variables to
`.env.local` to enable magic-link access. Set `ACT_API_BASE_URL` as well when
the configured pilot should verify the user with FastAPI and use durable
diagnostic sessions. Without Supabase variables, choose “Continue in prototype
mode” on `/sign-in`.

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

Before a real pilot, use the reviewer endpoints to approve the actual
purpose-specific blueprints and inventory; add tutor comparison and richer
analytics; and complete the privacy, rights, accessibility, rate-limit, and
backup/restore gates in `plan.md`.
