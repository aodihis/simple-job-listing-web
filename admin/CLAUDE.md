# Admin Dashboard Coding Standards

## Stack

- SvelteKit (latest stable) with TypeScript
- Vite as build tool
- `loglevel` (always wrapped — never imported directly in app code)
- Auth via JWT stored in `localStorage` (acceptable for admin-only internal tool)
- No external UI library — handroll components in `src/lib/components/ui/`

## Code Style

- Identical to frontend: TypeScript strict mode, Prettier, 100 char lines, no `any`, no `console.log`.
- File naming: `camelCase.ts` for utilities, `PascalCase.svelte` for components, SvelteKit convention for routes.

## Auth Pattern

- JWT is stored in and read from `localStorage` via `$lib/utils/auth.ts`.
- The `$lib/stores/auth.ts` Svelte store is initialized from `localStorage` on app load.
- The `(protected)/+layout.ts` load function reads the auth store. If no valid, non-expired token → `redirect(302, '/login')`.
- Token expiry is checked client-side on every protected layout load — do not rely solely on 401 responses from the API.
- On receiving a 401 from the API, the client calls `clearAuth()` and redirects to `/login`.

## Component Patterns

- Same rules as frontend — components receive data via props, no fetch calls inside components.
- Forms use Svelte's reactive `bind:value` with a local `formData` object and a separate `errors` object. No form library.
- Table components receive data as props and emit events for actions (delete, toggle, view). They contain no fetch logic.
- Modals are controlled by a boolean `open` prop; they emit `close` events. The parent manages open/close state.
- Keep components under ~150 lines. Decompose if longer.

## Logging Standard

### Setup

```typescript
import { createLogger } from '$lib/logger';
const log = createLogger('ComponentOrModuleName');
```

Never import `loglevel` directly anywhere in app code.

### Usage

Always pass context as an object, never interpolate values into the event string:

```typescript
// Correct
log.info('auth.login_success', { email });
log.warn('auth.token_expired', { email });
log.error('job.create_failed', { error: String(error) });

// Wrong
log.info(`Login success for ${email}`);
```

### Event naming

Use **dot-notation**: `"resource.action"`.

Authentication events must always be logged: `"auth.login_success"`, `"auth.login_failed"`, `"auth.token_expired"`, `"auth.logout"`.

### Log levels

| Level | When to use |
|-------|-------------|
| `debug` | Verbose traces. Off in production. |
| `info` | Normal flow: login, job created, application status updated. |
| `warn` | Degraded but recoverable: token near expiry, slow API. |
| `error` | Failures: API errors, form submit failures, unhandled rejections. |

### Swapping log sinks

The logger wrapper is in `src/lib/logger/index.ts` — the **only** file to change when adding or swapping sinks. Log level is set via `PUBLIC_LOG_LEVEL` env var.

## API Calls

- All API calls go through `$lib/api/client.ts` — the auth-aware fetch wrapper.
- The client automatically:
  - Attaches `Authorization: Bearer <token>` from the auth store
  - On 401: calls `clearAuth()` then `goto('/login')`
  - Throws typed `ApiError({ status, message })` on non-OK responses
- Never call `fetch()` directly in components or load functions.
- Individual resource modules in `$lib/api/` export typed async functions.

## Error Handling

- Protected routes use `(protected)/+layout.ts` as the auth gate — no auth check needed in individual pages.
- Form errors: validate client-side first (required fields, email format), show inline. Surface server errors in a toast notification via the `Toast.svelte` component.
- Unexpected errors: log with the logger, show a generic "Something went wrong. Please try again." toast.
- Never expose raw API error messages to the UI (they may leak internal details). Map to user-friendly messages.

## Protected Route Structure

```
src/routes/
├── login/            # Public — no auth required
├── register/         # Public — only works when no admin exists yet
└── (protected)/      # SvelteKit route group
    ├── +layout.ts    # Auth guard: checks token validity, redirects to /login
    ├── +layout.svelte
    ├── dashboard/
    ├── jobs/
    ├── applications/
    ├── admins/
    └── settings/
```

The `(protected)` group name is stripped from URLs — `/dashboard`, `/jobs`, etc. are the actual paths.
