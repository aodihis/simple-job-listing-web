/**
 * Logger wrapper around loglevel.
 *
 * This is the ONLY file to change when swapping log sinks or adding plugins
 * (e.g., forwarding errors to Sentry, sending to a remote analytics endpoint).
 *
 * Never import 'loglevel' directly in application code — always use createLogger().
 *
 * Usage:
 *   import { createLogger } from '$lib/logger';
 *   const log = createLogger('MyComponent');
 *   log.info('jobs.loaded', { count });
 *   log.error('jobs.load_failed', { error: String(err) });
 */

import loglevel from 'loglevel';
import type { Logger } from './types';

const envLevel =
	(typeof import.meta !== 'undefined' && (import.meta.env?.PUBLIC_LOG_LEVEL as string)) || 'warn';

/**
 * Create a named logger.
 *
 * @param name - Module or component name. Use PascalCase for components,
 *               module path for utilities (e.g. 'api/client').
 */
export function createLogger(name: string): Logger {
	const inner = loglevel.getLogger(name);
	inner.setLevel(envLevel as loglevel.LogLevelDesc);

	// To add a remote sink (Sentry, Datadog, etc.), wrap methodFactory here:
	//
	//   const originalFactory = inner.methodFactory;
	//   inner.methodFactory = (methodName, level, loggerName) => {
	//     const rawMethod = originalFactory(methodName, level, loggerName);
	//     return (...args) => {
	//       rawMethod(...args);
	//       if (methodName === 'error') Sentry.captureMessage(String(args[0]));
	//     };
	//   };
	//   inner.setLevel(inner.getLevel()); // re-apply to activate factory

	return {
		trace: (event, ctx) => inner.trace({ event, ...ctx }),
		debug: (event, ctx) => inner.debug({ event, ...ctx }),
		info: (event, ctx) => inner.info({ event, ...ctx }),
		warn: (event, ctx) => inner.warn({ event, ...ctx }),
		error: (event, ctx) => inner.error({ event, ...ctx }),
	};
}
