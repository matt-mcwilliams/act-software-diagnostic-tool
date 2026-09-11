# Domain migrations

The FastAPI service owns domain-schema migrations. The existing Drizzle
migration is retained for the original starter `diagnostic_runs` table until
the shared environment is checked for data and a deliberate retirement
migration is scheduled.

Apply these migrations in filename order with the service's migration runner
once it is connected to the pilot database. They are intentionally separate
from the Next.js web schema so there is one owner for assessment, content,
mastery, remediation, and analytics writes.

The first domain migration also creates the retry primitives used by future
session mutations: one open assessment per student/blueprint and scoped
`idempotency_keys` containing a request hash plus the completed response. A
mutation must return the stored response for the same owner/scope/key, and
must reject a reused key whose request hash differs.

Migration `0002` records each canonical-content import batch by source hash,
taxonomy/schema version, row counts, warnings, and lifecycle status. Imported
canonical exports remain non-assignable until their review and rights gates
are cleared.

Migration `0003` gives each source artifact a stable `(source_type, name,
version)` identity so the importer can use conflict-safe upserts.
