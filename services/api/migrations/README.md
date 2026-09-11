# Domain migrations

The FastAPI service owns domain-schema migrations. The existing Drizzle
migration is retained for the original starter `diagnostic_runs` table until
the shared environment is checked for data and a deliberate retirement
migration is scheduled.

Apply these migrations in filename order with the service's migration runner
once it is connected to the pilot database. They are intentionally separate
from the Next.js web schema so there is one owner for assessment, content,
mastery, remediation, and analytics writes.
