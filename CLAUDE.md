# Job Listing Web — Monorepo

## Structure

```
job-listing-web/
├── backend/    FastAPI REST API (Python 3.12+)
├── frontend/   SvelteKit public-facing site
└── admin/      SvelteKit admin dashboard
```

## Starting Each Service

```bash
# Backend
cd backend
pip install -e ".[dev]"
cp .env.example .env   # fill in SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Admin dashboard
cd admin
npm install
cp .env.example .env
npm run dev            # default port 5173

# Frontend
cd frontend
npm install
cp .env.example .env
npm run dev            # default port 5174
```

## Environment Files

- Never commit `.env` files — they contain secrets
- Each app has a `.env.example` documenting required variables
- Copy `.env.example` to `.env` and fill in values before running

## API Documentation (when backend is running)

- Swagger UI: http://localhost:8000/docs
- ReDoc:       http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Stack Boundaries

| Layer    | Stack                     | Port |
|----------|---------------------------|------|
| backend  | FastAPI + SQLAlchemy      | 8000 |
| admin    | SvelteKit (TypeScript)    | 5173 |
| frontend | SvelteKit (TypeScript)    | 5174 |

The admin and frontend apps talk to the backend via REST API only.
They share no code, no database connection, and no direct imports.

## General Rules

- Each app has its own `CLAUDE.md` with stack-specific coding standards — read it before modifying that app
- All schema changes go through Alembic migrations, never manual DB edits
- CORS origins are configured via the `CORS_ORIGINS` env var in the backend — no code changes needed per environment
