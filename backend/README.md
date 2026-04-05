# Backend — FastAPI

REST API for the Job Listing application.

## Tech Stack

- **Python 3.12+**
- **FastAPI** — web framework
- **SQLAlchemy 2.x** — ORM (works with SQLite and PostgreSQL)
- **Alembic** — database migrations
- **structlog** — structured logging
- **python-jose** — JWT auth
- **passlib[bcrypt]** — password hashing
- **pydantic-settings** — configuration via environment variables

---

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
# Development (includes pytest, ruff, httpx)
pip install -e ".[dev]"

# Production with PostgreSQL driver
pip install -e ".[postgres]"

# Both
pip install -e ".[dev,postgres]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

Generate a secure `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Edit `.env` and set at minimum:

```
SECRET_KEY=<your-generated-key>
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

---

## API Documentation

When the server is running:

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI — interactive, try endpoints live |
| http://localhost:8000/redoc | ReDoc — clean reference view |
| http://localhost:8000/openapi.json | OpenAPI JSON schema |

To authenticate in Swagger UI: click **Authorize** (top right) and enter `Bearer <your_token>`.

---

## Database

### Development — SQLite (default)

No configuration needed. The database file `dev.db` is created automatically when you run migrations.

```
DATABASE_URL=sqlite:///./dev.db
```

### Production — PostgreSQL

1. Install the PostgreSQL driver:
   ```bash
   pip install -e ".[postgres]"
   ```

2. Update `DATABASE_URL` in your `.env` (or production environment):
   ```
   DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
   ```

3. Run migrations exactly the same way:
   ```bash
   alembic upgrade head
   ```

No code changes are required — SQLAlchemy uses the connection URL to pick the right driver. The ORM models, queries, and migration scripts work identically across both databases.

> **Tip:** For production PostgreSQL, consider using a connection pool like `pgbouncer`, or switch to the async driver (`asyncpg`) if you migrate to async FastAPI in the future.

### Creating a migration

Whenever you change a model:

```bash
alembic revision --autogenerate -m "describe_what_changed"
alembic upgrade head
```

Never edit the database schema manually — always go through Alembic.

---

## Running Tests

```bash
pytest
```

Tests use an in-memory SQLite database and are fully isolated — they do not touch `dev.db`.

---

## Code Quality

```bash
# Lint and auto-fix
ruff check . --fix

# Format
ruff format .

# Both
ruff check . --fix && ruff format .
```

---

## Logging

Structured logging via `structlog`. Log output is controlled by two env vars:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Minimum log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `JSON_LOGS` | `false` | Set to `true` for JSON output (use in production for log ingestion) |

**Dev** (human-readable):
```
LOG_LEVEL=DEBUG
JSON_LOGS=false
```

**Production** (JSON for Loki/Datadog/CloudWatch):
```
LOG_LEVEL=INFO
JSON_LOGS=true
```

To swap log sinks entirely (e.g., add a file handler or forward to a remote service), only `app/logging/config.py` needs to change.

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # App factory, middleware, exception handlers
│   ├── config.py            # All settings (reads from .env)
│   ├── database.py          # SQLAlchemy engine, session, Base
│   ├── dependencies.py      # FastAPI Depends: get_db, get_current_user
│   ├── logging/
│   │   ├── config.py        # structlog setup — change sinks here only
│   │   └── middleware.py    # Request/response logging
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # HTTP layer (no business logic)
│   ├── services/            # Business logic
│   └── utils/
│       ├── exceptions.py    # AppException and subclasses
│       └── security.py      # JWT and password utilities
├── alembic/
│   └── versions/            # Migration files
├── tests/
│   ├── conftest.py          # Test DB setup, fixtures
│   └── test_auth.py         # Auth endpoint tests
├── pyproject.toml
├── alembic.ini
└── .env.example
```

See [CLAUDE.md](CLAUDE.md) for coding standards and conventions.
