/**
 * Auth-aware fetch wrapper.
 *
 * - Attaches Authorization: Bearer <token> on every request
 * - On 401: clears auth store and redirects to /login
 * - On non-OK: throws ApiError with status and message
 *
 * Never call fetch() directly — use this client or the resource modules in $lib/api/.
 */

import { goto } from '$app/navigation';
import { get } from 'svelte/store';
import { createLogger } from '$lib/logger';
import { token } from '$lib/stores/auth';
import { clearAuth } from '$lib/utils/auth';
import { ApiError } from './types';

const log = createLogger('api/client');

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
	const currentToken = get(token);

	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string>),
	};

	if (currentToken) {
		headers['Authorization'] = `Bearer ${currentToken}`;
	}

	log.debug('api.request', { method: options.method ?? 'GET', path });

	const response = await fetch(path, { ...options, headers });

	if (response.status === 401) {
		log.warn('api.unauthorized', { path });
		clearAuth();
		goto('/login');
		throw new ApiError(401, 'Session expired. Please log in again.');
	}

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

	// 204 No Content — return empty object cast to T
	if (response.status === 204) {
		return {} as T;
	}

	return response.json() as Promise<T>;
}

export const api = {
	get: <T>(path: string) => apiFetch<T>(path),

	post: <T>(path: string, body: unknown) =>
		apiFetch<T>(path, { method: 'POST', body: JSON.stringify(body) }),

	put: <T>(path: string, body: unknown) =>
		apiFetch<T>(path, { method: 'PUT', body: JSON.stringify(body) }),

	patch: <T>(path: string, body?: unknown) =>
		apiFetch<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }),

	delete: <T>(path: string) => apiFetch<T>(path, { method: 'DELETE' }),
};

/**
 * Unauthenticated fetch — for login and register endpoints.
 * Same error handling as api, but no Authorization header.
 */
export async function publicFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string>),
	};

	const response = await fetch(path, { ...options, headers });

	if (!response.ok) {
		let detail = `Request failed with status ${response.status}`;
		try {
			const body = (await response.json()) as { detail?: string };
			if (body.detail) detail = body.detail;
		} catch {
			// ignore parse errors
		}
		throw new ApiError(response.status, detail);
	}

	return response.json() as Promise<T>;
}
