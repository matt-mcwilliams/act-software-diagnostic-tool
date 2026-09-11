# Repository instructions

- Use pnpm for all package management and project scripts.
- After every completed change, create a focused git commit before starting the next change.
- Each commit must include only the files changed for that specific change. Never stage the whole repository by default; stage explicit paths.
- You may always use subagents to speed up the work. Unless the user says otherwise, use Luna at xhigh effort for subagent tasks.
- Keep secrets out of git. Use `.env.local` for local credentials and update `.env.example` with variable names and safe placeholders only.
- Run the smallest relevant verification command after each change and record any follow-up work in the next focused commit.

## Next.js project rules

This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from older versions. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repository root) before writing code, and heed deprecation notices.

This guidance is maintained by the installed Next.js version. Verify the source in `node_modules/next/dist/server/lib/generate-agent-files.js` if framework behavior is unclear.
