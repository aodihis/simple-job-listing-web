/**
 * Auth-aware fetch wrapper.
 *
 * - Attaches Authorization: Bearer <token> on every request
 * - On 401: attempts a silent token refresh; if successful, retries the original request once
 * - On refresh failure (or no refresh token): clears auth and redirects to /login
 * - On non-OK: throws ApiError with status and message
 *
 * Never call fetch() directly — use this client or the resource modules in $lib/api/.
 */

import { goto } from '$app/navigation';
import { get } from 'svelte/store';
import { createLogger } from '$lib/logger';
import { token, refreshToken } from '$lib/stores/auth';
import { clearAuth, setAuth } from '$lib/utils/auth';
import { ApiError } from './types';
import type { TokenResponse } from './types';

const log = createLogger('api/client');

// Shared refresh promise — ensures only one refresh call happens at a time even if
// multiple requests 401 simultaneously.
let activeRefresh: Promise<string | null> | null = null;

async function attemptRefresh(): Promise<string | null> {
	if (activeRefresh) return activeRefresh;

	activeRefresh = (async (): Promise<string | null> => {
		const rt = get(refreshToken);
		if (!rt) return null;
		try {
			const response = await publicFetch<TokenResponse>('/api/v1/auth/refresh', {
				method: 'POST',
				body: JSON.stringify({ refresh_token: rt }),
			});
			setAuth(response);
			log.info('auth.token_refreshed', {});
			return response.access_token;
		} catch {
			log.warn('auth.refresh_failed', {});
			clearAuth();
			return null;
		}
	})();

	try {
		return await activeRefresh;
	} finally {
		activeRefresh = null;
	}
}

async function apiFetch<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
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

	if (response.status === 401 && !isRetry) {
		log.warn('api.unauthorized', { path });
		const newToken = await attemptRefresh();
		if (newToken) {
			// Retry once with the new access token
			return apiFetch<T>(path, options, true);
		}
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
 * Unauthenticated fetch — for login, register, and refresh endpoints.
 * Same error handling as api, but no Authorization header and no retry logic.
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
