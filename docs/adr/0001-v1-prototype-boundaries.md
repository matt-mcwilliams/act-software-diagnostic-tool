# ADR 0001: V1 prototype boundaries

- Status: accepted for the first prototype
- Date: 2026-09-11

## Context

The repository contains a Next.js app, Supabase helpers, a Drizzle starter
schema, and two large taxonomy/content exports. The product plan calls for a
student loop that can be inspected from response through recommendation and
later move domain writes behind a FastAPI service.

## Decisions

1. The two `content/exports/master-output-*.json` files are treated as source
   artifacts for import and validation. They are not imported into Client
   Components or bundled into student-facing pages.
2. The current student experience uses a deliberately small, authored demo
   question bank mapped to taxonomy IDs from those exports. The UI labels this
   mode as prototype content; it does not imply official ACT score equivalence.
3. Correct answers remain in the server-only content module. Diagnostic and
   reassessment question endpoints return prompts and choices only. Practice
   feedback is released only through a practice-answer endpoint after a choice
   is submitted.
4. The first UI prototype stores session state in browser local storage so the
   loop can be exercised without a configured database or auth account. This is
   a development boundary, not the pilot persistence contract.
5. The future domain owner is a FastAPI service with PostgreSQL persistence.
   Next.js will call that service through an authenticated API boundary; it
   will not become a second owner of assessment, mastery, or recommendation
   writes.
6. Mastery uses the transparent weighted Beta-Binomial model and the
   recommendation ranking uses the version labels in `src/lib/act/engine.ts`.
   Both are replaceable, and stored evidence—not a mutable percentage—is the
   intended long-term source of truth.

## Consequences

- The prototype can demonstrate the full learning loop without pretending the
  current starter database is production-ready.
- The API contract can be tested now for answer-key separation and later point
  at FastAPI without changing student-facing question semantics.
- A real pilot still requires auth, durable domain tables, imports, exposure
  tracking, issue/report operations, and de-identified exports before release.
