# Backend Coding Standards

## Stack

- Python 3.12+
- FastAPI with Pydantic v2
- SQLAlchemy 2.x ORM (sync sessions)
- Alembic for migrations
- structlog for structured logging
- python-jose[cryptography] for JWT
- passlib[bcrypt] for password hashing
- pydantic-settings for configuration
- ruff for linting and formatting

## Code Style

- Follow PEP 8. Line length: 100 characters.
- Use `ruff` for both linting and formatting — run `ruff check . --fix && ruff format .` before committing.
- All functions and methods must have type annotations. No bare `Any` without an inline comment justifying it.
- Use `X | None` union syntax (Python 3.10+), not `Optional[X]`.
- Prefer Pydantic models or dataclasses over plain dicts for structured data.
- No `print()` calls anywhere — use the logger.

## File Naming

- All Python files: `snake_case.py`
- Model files are **singular** nouns: `user.py`, `job.py` — not `users.py`
- Schema files mirror model files: `app/schemas/job.py` mirrors `app/models/job.py`
- Router files are **plural** nouns matching the resource: `jobs.py`, `users.py`, `auth.py`

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `routers/` | HTTP layer only — validate input shape, call one service function, return response. Zero business logic. |
| `services/` | All business logic. Accept Pydantic schemas or plain types. Return Pydantic schemas. Raise `AppException` subclasses on errors. |
| `models/` | SQLAlchemy ORM definitions only. No queries, no business logic. |
| `schemas/` | Pydantic I/O contracts. Separate `Create`, `Update`, `Read` classes per resource. Include `Field(description=...)` for Swagger docs. |
| `dependencies.py` | All reusable `Depends()` functions: `get_db`, `get_current_user`, `require_active_admin`. |

## Logging Standard

### Setup (every module that logs)

```python
from app.logging.config import get_logger

log = get_logger(__name__)
```

### Usage rules

Always pass context as **keyword arguments**, never in the message string:

```python
# Correct
log.info("job.created", job_id=job.public_id, posted_by=user.email)
log.warning("auth.login_failed", email=email, reason="invalid_password")
log.error("email.send_failed", error=str(e), recipient=recipient)

# Wrong — don't interpolate values into the message
log.info(f"Job {job.public_id} created by {user.email}")
```

### Event naming

Use **dot-notation** to namespace events: `"resource.action"` or `"resource.action_qualifier"`.

Examples: `"auth.register_success"`, `"auth.login_failed"`, `"job.created"`, `"job.deleted"`, `"email.send_failed"`, `"application.submitted"`

### Log levels

| Level | When to use |
|-------|-------------|
| `debug` | Verbose traces, query counts, timing. Off in production. |
| `info` | Normal application flow — entity created, action completed. |
| `warning` | Expected failures that don't need a page — wrong password, duplicate email, not found. |
| `error` | Unexpected failures — SMTP down, DB unavailable, unhandled exception in a service. |

### Where to log

- **Log in services**, not in routers. Routers have request-level middleware that logs method/path/status automatically.
- External call wrappers (`email_service.py`, file upload) log at their own layer.

### What never to log

- Raw JWT tokens
- Password hashes or plaintext passwords
- Full request/response bodies (may contain PII) — log IDs and counts only

### Swapping log sinks

The structlog processor chain is defined entirely in `app/logging/config.py`.

- **Dev** uses `ConsoleRenderer` (human-readable, colorized)
- **Prod** switch to `JSONRenderer` for structured log ingestion
- To add a file sink, remote sink (Loki, Datadog, etc.), or sampling: **only edit `app/logging/config.py`**. No other file changes required.

```python
# app/logging/config.py — the only file to change when swapping sinks
def configure_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer(),
    ]
    structlog.configure(processors=processors, ...)
```

## Database Rules

- Always inject the session via `Depends(get_db)` in router functions.
- Pass `db: Session` as the **first argument** to service functions.
- **Never `db.commit()` inside a service function.** Commit happens in the router (or a transaction helper) so the router controls transaction scope.
- Never modify the database schema manually. All changes go through Alembic:
  ```bash
  alembic revision --autogenerate -m "describe_the_change"
  alembic upgrade head
  ```
- Use `public_id` (UUID v4) as the external-facing identifier in API URLs — never expose internal integer PKs.

## Error Handling

- Define `AppException(Exception)` in `app/utils/exceptions.py` with `status_code: int` and `detail: str`.
- Subclass it for domain errors: `NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`.
- Register a **single** `@app.exception_handler(AppException)` in `main.py` — do not use `try/except` in routers for expected errors.
- Use `try/except` in services only for external calls (SMTP, file I/O). Always re-raise as an `AppException` subclass.
- Let unexpected exceptions bubble up to FastAPI's default 500 handler (augmented by request logging middleware).

## Authentication

- `require_active_admin` dependency (in `dependencies.py`) decodes JWT, fetches user from DB, asserts `is_active=True`.
- Token secrets come from `settings.SECRET_KEY` (env var, never hardcoded).
- Never log the raw JWT or any password hash.

## API Documentation

All endpoints must include a `summary=` string. Pydantic schema fields must include `Field(description=...)` for non-obvious fields. These populate the Swagger UI at `/docs` automatically.
