# ACT Adaptive API

This is the planned FastAPI domain boundary. It currently provides the
operational endpoints and authenticated current-user contract needed before
assessment and content writes move out of the Next.js prototype.

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

Imports are source-hash idempotent and create draft/pending-review content.
They do not make raw canonical content assignable or expose it in the result.

Student assessment endpoints are enabled only when PostgreSQL contains an
approved blueprint and approved, rights-cleared question inventory:

```text
GET  /v1/diagnostics
POST /v1/assessment-sessions
PUT  /v1/assessment-sessions/{session_id}/responses/{session_item_id}
```

Session items contain prompts and choices only. Response saves require an
`Idempotency-Key` header and a monotonic `client_revision`; stale revisions
return a conflict instead of overwriting newer work. New diagnostic sessions
exclude questions already exposed to that student.

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
