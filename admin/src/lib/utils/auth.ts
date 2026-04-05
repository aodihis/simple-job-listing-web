/**
 * Auth utility functions for token inspection and lifecycle management.
 */

import { get } from 'svelte/store';
import { token } from '$lib/stores/auth';

/**
 * Decode the JWT payload (base64url → JSON).
 * Does NOT verify the signature — that's the server's job.
 */
export function decodeTokenPayload(jwt: string): Record<string, unknown> {
	try {
		const [, payloadB64] = jwt.split('.');
		const json = atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/'));
		return JSON.parse(json) as Record<string, unknown>;
	} catch {
		return {};
	}
}

/**
 * Returns true if the token's `exp` claim is in the past.
 * Returns true for malformed tokens (treated as expired).
 */
export function isTokenExpired(jwt: string): boolean {
	const payload = decodeTokenPayload(jwt);
	const exp = payload['exp'];
	if (typeof exp !== 'number') return true;
	// exp is in seconds; Date.now() is in ms
	return Date.now() >= exp * 1000;
}

/**
 * Clear the auth token from the store (and thereby from localStorage).
 * Call this on logout or when a 401 is received from the API.
 */
export function clearAuth(): void {
	token.set(null);
}

/**
 * Returns the current token string if it exists and is not expired.
 * Returns null otherwise.
 */
export function getValidToken(): string | null {
	const t = get(token);
	if (!t || isTokenExpired(t)) return null;
	return t;
}
