# Admin Dashboard — SvelteKit

Admin interface for the Job Listing application. Allows administrators to post jobs, manage applications, invite other admins, and configure notification emails.

## Tech Stack

- **SvelteKit** with TypeScript
- **Vite** — build tool with dev proxy to backend
- **loglevel** — logging (wrapped behind `$lib/logger`, never imported directly)
- JWT auth stored in `localStorage`

---

## Setup

### 1. Install dependencies

```bash
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Available variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PUBLIC_LOG_LEVEL` | `warn` | Client-side log level: `trace`, `debug`, `info`, `warn`, `error` |

### 3. Start the dev server

```bash
npm run dev
```

Opens at http://localhost:5173

> **Note:** The Vite dev server proxies all `/api` requests to `http://localhost:8000` (the backend). Make sure the backend is running first.

---

## First Run

On first visit, the app redirects to `/login`. If no admin account exists yet, go to `/register` to create the first admin account.

After the first admin is created, `/register` returns a 409 error — subsequent admins must be invited by an existing admin (coming in a later step).

---

## Auth Flow

```
/register  →  POST /api/v1/auth/register  →  store JWT  →  /dashboard
/login     →  POST /api/v1/auth/login     →  store JWT  →  /dashboard

Any protected route:
  +layout.ts checks token presence and expiry
  → expired/missing token → redirect /login
  → 401 from API → clearAuth() → redirect /login
```

The JWT token is stored in `localStorage` under the key `admin_token`.

---

## Available Scripts

```bash
npm run dev          # Start dev server (port 5173)
npm run build        # Production build
npm run preview      # Preview production build locally
npm run check        # TypeScript type-check
npm run format       # Format with Prettier
npm run lint         # Lint check
```

---

## Project Structure

```
admin/
├── src/
│   ├── app.html               # HTML shell
│   ├── app.css                # Global CSS custom properties
│   ├── lib/
│   │   ├── logger/
│   │   │   ├── index.ts       # Logger wrapper — change sinks here only
│   │   │   └── types.ts       # Logger interface
│   │   ├── api/
│   │   │   ├── client.ts      # Auth-aware fetch wrapper
│   │   │   ├── auth.ts        # login, register, getMe
│   │   │   └── types.ts       # Shared API types, ApiError
│   │   ├── stores/
│   │   │   └── auth.ts        # JWT token store (localStorage-backed)
│   │   └── utils/
│   │       └── auth.ts        # decodeTokenPayload, isTokenExpired, clearAuth
│   └── routes/
│       ├── +layout.svelte     # Root layout (no auth check)
│       ├── +page.svelte       # Redirects to /dashboard or /login
│       ├── login/             # Login page
│       ├── register/          # First-admin registration page
│       └── (protected)/       # Auth-gated route group
│           ├── +layout.ts     # Auth guard → redirect /login if no valid token
│           ├── +layout.svelte # Nav sidebar + main content slot
│           └── dashboard/     # Welcome page
├── vite.config.ts             # Vite config (API proxy)
├── svelte.config.js
├── tsconfig.json
└── .env.example
```

See [CLAUDE.md](CLAUDE.md) for coding standards and conventions.
