# Frontend Coding Standards

## Stack

- SvelteKit (latest stable) with TypeScript
- Vite as build tool
- `loglevel` as underlying logging library (always wrapped — never imported directly in app code)
- CSS custom properties for theming; no CSS-in-JS
- No external UI component library — handroll small UI atoms in `src/lib/components/ui/`

## Code Style

- TypeScript strict mode (`"strict": true` in tsconfig.json).
- All exported functions and component props must be typed. No `any` — use `unknown` and narrow explicitly.
- File naming: SvelteKit routes follow the framework's file convention. All other files use `camelCase.ts` for utilities and `PascalCase.svelte` for components.
- Max line length: 100 characters.
- Use Prettier for formatting (configured in `package.json`).
- No `console.log()` anywhere in application code — use the logger.

## Component Patterns

- Components receive data via **props**. They do not fetch data themselves.
- Data fetching belongs in `+page.ts` load functions (or `+layout.ts` for shared data).
- Extract any logic beyond simple event handling into a `*.ts` utility or Svelte store.
- Prefer Svelte stores (`writable`, `derived`) over component-local state when data is shared across components.
- Component file structure (top to bottom): `<script>`, markup, `<style>`.
- Keep components under ~150 lines. If longer, decompose into smaller components.

## Logging Standard

### Setup

```typescript
import { createLogger } from '$lib/logger';
const log = createLogger('ComponentOrModuleName');
```

Never import `loglevel` directly anywhere in app code.

### Usage

Always pass context as an object (second argument), never interpolate values into the event string:

```typescript
// Correct
log.info('filters.applied', { tags, employmentType, query });
log.warn('api.slow_response', { url, durationMs });
log.error('application.submit_failed', { jobId, error: String(error) });

// Wrong
log.info(`Filters applied: ${tags.join(',')}`);
```

### Event naming

Use **dot-notation**: `"resource.action"` or `"resource.action_qualifier"`.

Examples: `"jobs.loaded"`, `"job.detail_loaded"`, `"filters.applied"`, `"application.submitted"`, `"api.request_failed"`

### Log levels

| Level | When to use |
|-------|-------------|
| `debug` | Verbose: store mutations, render counts. Off in production. |
| `info` | Normal flow: page loaded, form submitted successfully. |
| `warn` | Degraded but recoverable: slow API, fallback triggered. |
| `error` | Failures: API error, form submit failed, unhandled rejection. |

### Swapping log sinks

The logger wrapper is in `src/lib/logger/index.ts`. This is the **only** file to change when adding or swapping sinks.

- To forward errors to Sentry: add a `loglevel.methodFactory` plugin in `index.ts`
- To add a remote analytics sink: add it in `index.ts`
- Log level is controlled by the `PUBLIC_LOG_LEVEL` environment variable

## API Calls

- All API calls go through `$lib/api/client.ts` which handles base URL, error parsing, and response typing.
- Individual resource modules (`jobs.ts`) export typed async functions — route load functions call these.
- On error, the API client throws a typed `ApiError` with `status` and `message`. Catch this in load functions and return SvelteKit `error()` responses.
- Never call `fetch()` directly in components or stores.

## Error Handling

- In `+page.ts` load functions, use SvelteKit's `error()` helper for unrecoverable errors (404, 500).
- For form submissions and soft errors (validation, network), use local Svelte state to show inline messages — do not throw.
- Global unhandled errors: set `window.onerror` / `window.onunhandledrejection` in the root `+layout.svelte` and log via the logger.

## Routing and Filter State

- URL search params are the **source of truth** for filter/search/sort state. Do not store filter state only in memory.
- Use SvelteKit's `goto()` with `replaceState: true` when updating filters to avoid polluting browser history.
- Load functions read filters from `url.searchParams`, not from stores.
