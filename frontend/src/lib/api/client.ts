/**
 * Unauthenticated fetch wrapper for the public frontend.
 *
 * - Throws ApiError on non-OK responses
 * - Never call fetch() directly — use this client or the resource modules in $lib/api/
 */

import { createLogger } from '$lib/logger';
import { ApiError } from './types';

const log = createLogger('api/client');

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string>),
	};

	log.debug('api.request', { method: options.method ?? 'GET', path });

	const response = await fetch(path, { ...options, headers });

	if (!response.ok) {
		let detail = `Request failed with status ${response.status}`;
		try {
			const body = (await response.json()) as { detail?: string };
			if (body.detail) detail = body.detail;
		} catch {
			// response body wasn't JSON — keep default message
		}
		log.error('api.request_failed', { path, status: response.status, detail });
		throw new ApiError(response.status, detail);
	}

	return response.json() as Promise<T>;
}

export const api = {
	get: <T>(path: string) => apiFetch<T>(path),
};
