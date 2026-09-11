# FastAPI database backup and restore runbook

This runbook is for the PostgreSQL database configured by
`ACT_API_DATABASE_URL`. The connection string is a secret and must stay in
`.env.local` or the deployment secret store.

## Before a migration

1. Confirm the target environment and announce a short write window.
2. Create an encrypted, access-controlled custom-format dump outside this
   repository:

   ```bash
   pg_dump --dbname="$ACT_API_DATABASE_URL" \
     --format=custom \
     --file="/secure/backups/act-api-$(date -u +%Y%m%dT%H%M%SZ).dump"
   ```

3. Record the dump filename, database environment, migration commit, and
   operator in the pilot change log.
4. Verify the migration manifest before applying it:

   ```bash
   pnpm api:migrate --dry-run
   ```

5. Apply migrations only from the reviewed commit:

   ```bash
   pnpm api:migrate
   ```

The migration runner stores a checksum for every applied file and stops if an
already-applied migration was modified.

## Restore rehearsal

Restore into a fresh, isolated PostgreSQL database. Never use `--clean` against
the pilot database for a rehearsal.

```bash
createdb act_api_restore_rehearsal
pg_restore --dbname=act_api_restore_rehearsal \
  --no-owner --exit-on-error \
  "/secure/backups/act-api-YYYYMMDDTHHMMSSZ.dump"
```

Then verify, using a connection string for the rehearsal database:

```bash
ACT_API_DATABASE_URL=postgresql://.../act_api_restore_rehearsal pnpm api:migrate --dry-run
ACT_API_DATABASE_URL=postgresql://.../act_api_restore_rehearsal pnpm api:dev
```

Check `/healthz`, `/readyz`, one authenticated `/v1/me` request, and a
read-only progress/export query. Confirm that no student identity appears in
the export response. Record restore duration and the oldest recoverable point.

## Rollback decision

Prefer a forward migration or content retirement when data is valid. Restore
the pilot database only for corruption, unrecoverable migration failure, or
confirmed data loss:

1. Pause student assignments and write traffic.
2. Preserve current logs and take a final dump for forensics.
3. Restore the last verified dump into a replacement database, or use the
   provider's point-in-time restore.
4. Run the migration dry-run and health/auth checks against the replacement.
5. Re-enable traffic only after response ownership and no-answer-key checks
   pass.
6. Record the incident, restore point, validation evidence, and follow-up
   migration.

The repository does not contain production credentials or backup files, and a
restore rehearsal must be performed by the deployment operator against the
actual managed PostgreSQL environment before pilot launch.
