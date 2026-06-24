# 01.03 Auth: Apple + Google Sign-In

## Context

Users sign in with Apple or Google. No email/password. The mobile clients run the native sign-in flows and ship the ID token to our API; the web does the same via Apple JS and Google Identity Services.

Reference: `00-overview/api-conventions.md` (auth section).

## Goal

Working sign-in for both providers on the API side, JWT issuance, refresh rotation, and a `users` table populated correctly.

## Schema

Per `00-overview/data-model.md`:

```python
class User(Base):
    id: UUID
    email: str  # unique, nullable for Apple private relay edge cases
    display_name: str | None
    apple_sub: str | None  # unique
    google_sub: str | None  # unique
    unit_system: UnitSystem  # default 'imperial' (user base is US-leaning)
    birthdate: date | None
    sex_at_birth: SexAtBirth | None
    timezone: str  # default 'America/New_York'
```

Also create:

```python
class RefreshToken(Base):
    id: UUID
    user_id: UUID
    token_hash: str  # SHA-256 of the opaque token
    issued_at: datetime
    expires_at: datetime  # 60 days
    revoked_at: datetime | None
    rotated_to: UUID | None  # points to the next token if this was rotated
    user_agent: str | None
    ip: str | None
```

## Endpoints

- `POST /v1/auth/apple` body `{ "id_token": "..." }`
  - Verify the JWT against Apple's JWKS, validate `aud` matches our bundle id / service id, validate `exp`.
  - Extract `sub`, `email` (when present).
  - Upsert user by `apple_sub`.
  - Issue access + refresh tokens.
- `POST /v1/auth/google` body `{ "id_token": "..." }`
  - Same flow against Google JWKS.
- `POST /v1/auth/refresh` body `{ "refresh_token": "..." }`
  - Look up by hash. If found and not revoked or expired, rotate (issue new pair, mark old as revoked with `rotated_to`).
  - If found but already revoked, this is a replay: revoke the entire chain and return 401.
- `POST /v1/auth/logout` (authenticated)
  - Revoke the current refresh token chain.
- `GET /v1/me`
  - Returns the current user.
- `PATCH /v1/me`
  - Update `display_name`, `unit_system`, `timezone`, `birthdate`, `sex_at_birth`.

## Security

- Access token: HS256 JWT, 15 min expiry, secret loaded from env. Plan for asymmetric (RS256) later but not now.
- Refresh token: 32 random bytes, base64url, hashed with SHA-256 server-side. Never store plaintext.
- Refresh rotation is mandatory. Replay detection per above.
- Verify Apple ID tokens with the official Apple JWKS endpoint, cached for 1 hour.
- Verify Google ID tokens with the `google-auth` library.

## Deliverables

1. Alembic migration for `users` and `refresh_tokens` tables.
2. SQLAlchemy models.
3. Pydantic schemas for all request and response shapes.
4. Service layer in `app/services/auth.py` with `verify_apple_token`, `verify_google_token`, `issue_token_pair`, `rotate_refresh_token`.
5. `app/deps.py::get_current_user` dependency that validates the access token and loads the user.
6. Router `app/routers/auth.py`.
7. Tests:
   - Unit tests for token verification with mocked JWKS.
   - Integration tests for the full sign-in -> refresh -> logout flow.
   - Replay attack test: using a revoked refresh token revokes the chain.

## Acceptance criteria

- Sign-in with a real Apple test token from the iOS app succeeds.
- Sign-in with a real Google test token from the web succeeds.
- Refresh rotation works and replays are detected.
- `/v1/me` returns 401 without a token, 200 with one.

## Dependencies

- `01.02 FastAPI skeleton`

## Out of scope

- Email/password auth.
- Multi-device session listing UI (later).
