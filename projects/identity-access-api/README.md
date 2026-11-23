# Identity Access API

A backend identity and access-management service built with FastAPI, SQLAlchemy 2 and PostgreSQL. It demonstrates secure password storage, JWT access and refresh tokens, refresh-token rotation, role-based access control and audit events.

> Portfolio learning project; not a managed identity provider and not independently security-audited.

## Features

- Registration with email validation and a 12-character minimum password length.
- Argon2 password hashing using `pwdlib`.
- OAuth2 password-form login issuing signed JWT access and refresh tokens.
- Validation of token signature, algorithm, expiry, not-before, issuer, audience, token type and required claims.
- Short-lived access tokens and refresh-token rotation.
- Server-side refresh-session tracking by SHA-256 hash of the JWT ID (JTI); raw refresh tokens are not stored.
- Refresh-token reuse detection with revocation of the remaining token family.
- Logout and persisted refresh-session revocation.
- Role-based access control with `user` and `admin` roles.
- Admin-only user listing, role changes, account deactivation and audit-event review.
- Guardrails against self-demotion and self-deactivation of the last administrator.
- SQLAlchemy 2 models, PostgreSQL, Alembic migrations, Docker Compose and automated tests.

## Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 · PostgreSQL · Alembic · PyJWT · Argon2 / pwdlib · Docker Compose · pytest

## Local setup (SQLite)

Install dependencies:

```bash
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements.txt
```

Set a signing key of at least 32 characters:

**PowerShell**
```powershell
$env:JWT_SECRET_KEY = "replace-with-a-random-secret-at-least-32-characters"
```

**macOS / Linux**
```bash
export JWT_SECRET_KEY="replace-with-a-random-secret-at-least-32-characters"
```

Run migrations and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs.

## PostgreSQL with Docker Compose

Copy `.env.example` to `.env`, set a unique strong `JWT_SECRET_KEY` and `POSTGRES_PASSWORD`, then run:

```bash
docker compose up --build
```

The API is published only on the local loopback interface at http://127.0.0.1:8000. Compose waits for PostgreSQL health; the API container runs Alembic migrations on startup.

## Bootstrap the first administrator

There is no public self-service endpoint to grant administrator privileges. First register the intended account, then run the local administrative command:

```bash
python -m app.cli promote-admin your-email@example.com
```

Run this command only from a trusted environment with access to the configured database.

## Authentication flow

1. Register: `POST /auth/register`.
2. Login: `POST /auth/token` using form fields `username` (email) and `password`.
3. Send the access token as `Authorization: Bearer <access_token>`.
4. Rotate the refresh token: `POST /auth/refresh`.
5. Revoke a refresh session: `POST /auth/logout` (requires a valid access token too).

Defaults: access token 15 minutes; refresh token 7 days. Values are configurable with environment variables.

## API

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/health` | Public | Health check |
| POST | `/auth/register` | Public | Create a standard user |
| POST | `/auth/token` | Public | Login and issue token pair |
| POST | `/auth/refresh` | Refresh token | Rotate refresh token |
| POST | `/auth/logout` | Access token | Revoke refresh session |
| GET | `/users/me` | Access token | Read current profile |
| GET | `/admin/users` | Admin | List users |
| PATCH | `/admin/users/{id}/role` | Admin | Change role |
| PATCH | `/admin/users/{id}/status` | Admin | Activate / deactivate account |
| GET | `/admin/audit` | Admin | Review audit events |

Interactive docs: `/docs`.

## Data model

- `users`: email, full name, Argon2 password hash, role and active status.
- `refresh_sessions`: hashed token JTI, family ID, expiry and revocation timestamp.
- `audit_events`: authentication and administrator actions.

## Security notes and limitations

Passwords are not stored in plaintext. The JWT decoder pins the allowed algorithm and validates issuer, audience and required claims. Authorisation reads the current user and role from the database rather than trusting a role claim in the token. Public registration always assigns the `user` role.

This example uses bearer tokens for clarity. A browser production deployment also needs a deliberate token-storage design (often Secure, HttpOnly, SameSite cookies), CSRF protection where applicable, HTTPS, rate limiting, email verification, password reset, secrets management, structured logging and monitoring. Concurrent refresh attempts should be handled with database row locking or conditional updates before production use. This project has not undergone an independent security audit.

## Tests

```bash
pytest -q
```

Tests use isolated in-memory SQLite databases and cover registration, password hashing, login, protected routes, refresh rotation and reuse, logout, RBAC, administrator guardrails and audit logging.
