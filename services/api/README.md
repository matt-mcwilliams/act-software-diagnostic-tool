# ACT Adaptive API

This is the FastAPI domain boundary. It provides operational/authentication
contracts, reviewer-only canonical content import, PostgreSQL-backed
diagnostics, and the first durable remediation-cycle, practice, and
reassessment contracts. The Next.js browser uses these flows when
`ACT_API_BASE_URL` is configured and falls back to the local prototype without
it.

## Local development

From the repository root:

```bash
pnpm api:install
pnpm api:dev
```

The API runs at `http://127.0.0.1:8000`. The local test-user path is opt-in:

```bash
ACT_API_ALLOW_TEST_USER=true curl \
  -H 'Authorization: Bearer prototype-test-token' \
  http://127.0.0.1:8000/v1/me
```

Production authentication requires `ACT_API_AUTH_JWT_SECRET` and verifies
the token signature, expiry, audience, and optional issuer. The test token
must never be enabled in a production environment.

## Content import preview

Reviewer/admin users can preview the canonical exports without writing rows or
receiving question text:

```bash
curl -X POST http://127.0.0.1:8000/v1/internal/imports/preview \
  -H 'Authorization: Bearer <reviewer-token>' \
  -H 'Content-Type: application/json' \
  -d '{"subject":"english"}'
```

The response includes source hashes, normalized row counts, and blocking
warnings such as missing primary-skill mappings or unresolved rights review.

Once `ACT_API_DATABASE_URL` is configured, the same reviewer/admin boundary
can import a selected export:

```bash
curl -X POST http://127.0.0.1:8000/v1/internal/imports \
  -H 'Authorization: Bearer <reviewer-token>' \
  -H 'Content-Type: application/json' \
  -d '{"subject":"english"}'
```

Imports are source-hash idempotent and create draft/pending-review content plus
draft diagnostic, practice, and reassessment blueprints. They do not make raw
canonical content assignable or expose it in the result; a reviewer must still
complete the rights/content review and approve the inventory and blueprints.

Student assessment endpoints are enabled only when PostgreSQL contains an
approved blueprint and approved, rights-cleared question inventory:

```text
GET  /v1/diagnostics
POST /v1/assessment-sessions
GET  /v1/assessment-sessions/{session_id}
PUT  /v1/assessment-sessions/{session_id}/responses/{session_item_id}
POST /v1/assessment-sessions/{session_id}/submit
GET  /v1/assessment-sessions/{session_id}/results
POST /v1/issue-reports
```

Remediation and durable learning endpoints:

```text
POST /v1/remediation-cycles
GET  /v1/remediation-cycles/{cycle_id}
POST /v1/remediation-cycles/{cycle_id}/resource-events
POST /v1/remediation-cycles/{cycle_id}/practice-sets
POST /v1/remediation-cycles/{cycle_id}/reassessments
GET  /v1/remediation-cycles/{cycle_id}/reassessments
GET  /v1/practice-sets/{practice_set_id}
POST /v1/practice-sets/{practice_set_id}/complete
```

Practice and reassessment sets reuse the public assessment-session response
protocol. They require approved purpose-specific blueprints, approved
rights-cleared inventory, and exclude every question already exposed to the
student.

## Reviewer operations

After importing, a reviewer can explicitly publish or reject a draft
blueprint and selected source slice. Publishing requires confirmation of the
content review, rights clearance, and answer-key review; the response contains
only lifecycle and count metadata:

```text
POST  /v1/internal/content/{blueprint_id}/reviews
GET   /v1/internal/issues?status=open
PATCH /v1/internal/issues/{issue_id}
GET   /v1/internal/experiments/{experiment_key}/export
```

The export requires `ACT_API_EXPORT_PSEUDONYM_SECRET`. It returns keyed pilot
pseudonyms and cohort-level skill/completion facts, never names, emails,
question text, response text, or answer keys. Keep the secret in `.env.local`
or the deployment secret store; do not put it in a committed environment file.

Protected and bulk `/v1` paths use the configured process-local rate limit
(`ACT_API_RATE_LIMIT_REQUESTS` per
`ACT_API_RATE_LIMIT_WINDOW_SECONDS`) and return `429` with `Retry-After` when
the limit is exceeded. This is a first-prototype guard; enforce the same
policy at the deployment edge or with a shared store before running multiple
API workers or regions.

Session items contain prompts and choices only. Response saves require an
`Idempotency-Key` header and a monotonic `client_revision`; stale revisions
return a conflict instead of overwriting newer work. New diagnostic sessions
exclude questions already exposed to that student. Submission finalizes
omissions, persists a reproducible raw score, and requires its own
`Idempotency-Key`.

## Domain migrations

The FastAPI service owns the domain migration history. Preview the migration
manifest without a database connection, or apply unapplied migrations using
the server-only `ACT_API_DATABASE_URL`:

```bash
pnpm api:migrate --dry-run
pnpm api:migrate
```

Applied migrations are recorded with a SHA-256 checksum. Re-running is a
no-op; changing an already-applied file stops with an error.

For backup, restore rehearsal, and migration rollback steps, see
[`docs/runbooks/api-backup-restore.md`](../../docs/runbooks/api-backup-restore.md).
