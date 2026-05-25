# API conventions

Authoritative rules for the FastAPI backend. Every endpoint follows these.

## Base URL and versioning

- Local: `http://localhost:8000`
- Production: `https://api.<domain>`
- All routes mounted under `/v1/`. When breaking changes are needed, mount `/v2/` alongside; do not silently break v1.

## Auth

- Apple Sign-In and Google Sign-In on the client. Client sends the ID token to `POST /v1/auth/exchange`.
- Server verifies the token, upserts the user, returns:
  - `access_token`: short-lived JWT (15 min), HS256, contains `sub` (user id), `exp`, `iat`
  - `refresh_token`: opaque random string stored hashed in `refresh_tokens` table
- Refresh via `POST /v1/auth/refresh`. Rotate refresh token on every refresh.
- All authenticated routes require `Authorization: Bearer <access_token>`.

## Request and response format

- JSON only. `Content-Type: application/json`.
- Snake case in JSON. Clients (Next.js and Swift) map to their own conventions.
- All timestamps are ISO 8601 UTC with `Z` suffix.
- Pagination uses cursor style: `?limit=50&cursor=<opaque>`. Response includes `next_cursor` (null when done). Do not use offset pagination anywhere.

## Errors

Single shape across the API:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human-readable summary.",
    "details": { "field": "weight_kg", "reason": "must be positive" }
  }
}
```

Codes: `validation_error`, `not_found`, `unauthorized`, `forbidden`, `conflict`, `rate_limited`, `internal_error`, `integration_error`.

## Resource patterns

- Collections: `GET /v1/<resource>`
- Item: `GET /v1/<resource>/{id}`
- Create: `POST /v1/<resource>`
- Update: `PATCH /v1/<resource>/{id}` (partial), `PUT` not used.
- Delete: `DELETE /v1/<resource>/{id}`. Soft-deletes return 204 and exclude from default lists.
- Nested when ownership is strict: `POST /v1/workout-sessions/{id}/sets`. Two levels of nesting maximum.

## Idempotency

Mutations that the client might retry (start workout, log set, sync from Fitbit) accept an `Idempotency-Key` header. Server stores key + response for 24 hours and replays the same response.

## Rate limits

- Global default: 600 req/min per user via Redis token bucket.
- Auth endpoints: 30 req/min per IP.
- AI endpoints (recommendations, photo recognition): 60 req/hour per user.
- 429 with `Retry-After` header on limit.

## OpenAPI

FastAPI auto-generates `/openapi.json`. Both clients generate their typed SDKs from this file:
- Web: `openapi-typescript` -> `apps/web/src/lib/api/types.ts`
- iOS: `swift-openapi-generator` -> `App/Generated/API.swift`

Both SDKs are regenerated in CI; mismatches between spec and clients fail the build.

## Validation

- Pydantic v2 models for every request and response.
- Constraints declared on the model (positive numbers, max lengths, etc.), not in route bodies.
- Return 422 with the validation error code on Pydantic failures.

## Logging and tracing

- structlog JSON logs with `user_id`, `request_id`, `route`, `latency_ms`.
- OpenTelemetry traces exported to a self-hosted Tempo or Honeycomb (decide at deployment task).
- No PII in logs beyond `user_id`. No tokens, no emails.

## Background jobs

- Use ARQ (Redis-backed) for async work: nightly analytics rollups, Fitbit syncs, LLM rationale generation.
- Jobs are idempotent and re-runnable. Use `Idempotency-Key`-style dedup where applicable.
