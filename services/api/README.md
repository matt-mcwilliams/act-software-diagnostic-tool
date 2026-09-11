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
