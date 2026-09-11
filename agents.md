# Repository instructions

- Use pnpm for all package management and project scripts.
- After every completed change, create a focused git commit before starting the next change.
- Each commit must include only the files changed for that specific change. Never stage the whole repository by default; stage explicit paths.
- Keep secrets out of git. Use `.env.local` for local credentials and update `.env.example` with variable names and safe placeholders only.
- Run the smallest relevant verification command after each change and record any follow-up work in the next focused commit.
