# ACT Diagnostic Tool

An intentional starter for a software diagnostic workspace. The first pass keeps the diagnostic loop explicit and inspectable; AI is reserved as a future extension point and is not connected yet.

## Stack

- Next.js App Router, React, and TypeScript
- Tailwind CSS and shadcn/ui
- Supabase Auth with cookie-based SSR
- FastAPI domain-service foundation with authenticated `/v1/me`
- Supabase PostgreSQL with Drizzle ORM and `postgres.js`
- Playwright for end-to-end smoke tests
- pnpm, GitHub Actions, and Vercel-ready deployment config

## Local setup

```bash
pnpm install
cp .env.example .env.local
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

Add the Supabase project URL and publishable key to `.env.local` for browser/server auth. Add `DATABASE_URL` when you are ready to run Drizzle commands against the project database.

## Commands

```bash
pnpm dev          # Start the local app
pnpm lint         # Run ESLint
pnpm typecheck    # Check TypeScript
pnpm build        # Create a production build
pnpm test:e2e     # Run Playwright smoke tests
pnpm api:install  # Install the FastAPI service and its test dependencies
pnpm api:dev      # Start the FastAPI service
pnpm api:test     # Run FastAPI tests
pnpm api:typecheck # Compile-check FastAPI modules
pnpm db:generate  # Generate Drizzle migrations
pnpm db:push      # Push the schema to PostgreSQL
pnpm db:studio    # Open Drizzle Studio
```

## Project map

```text
src/app/              App Router pages and global styles
src/components/ui/    shadcn/ui primitives
src/db/               Drizzle schema and lazy database client
src/lib/supabase/     Browser, server, and Proxy auth clients
src/proxy.ts          Next.js 16 session refresh entry point
services/api/         FastAPI operational and identity boundary
content/exports/      Canonical ACT taxonomy/content export artifacts
tests/                Playwright tests
drizzle.config.ts     Drizzle Kit configuration
```

## Deployment

The project is ready to connect to GitHub and import into Vercel. Set the same Supabase variables and `DATABASE_URL` in the Vercel project environment settings before enabling authenticated or persisted flows.
