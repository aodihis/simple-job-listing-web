/**
 * Auth store — single source of truth for JWT token state.
 *
 * Backed by localStorage so tokens survive page refreshes.
 * The stores sync to/from localStorage automatically on every write.
 *
 * Import `token` to read/write the access token.
 * Import `refreshToken` to read/write the refresh token.
 * Import `isAuthenticated` to reactively check auth state in components.
 */

import { derived, writable } from 'svelte/store';

const ACCESS_TOKEN_KEY = 'admin_token';
const REFRESH_TOKEN_KEY = 'admin_refresh_token';

function readFromStorage(key: string): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem(key);
}

function writeToStorage(key: string, value: string | null): void {
	if (typeof localStorage === 'undefined') return;
	if (value) {
		localStorage.setItem(key, value);
	} else {
		localStorage.removeItem(key);
	}
}

// Initialize from localStorage (null on SSR — localStorage is unavailable)
export const token = writable<string | null>(readFromStorage(ACCESS_TOKEN_KEY));
export const refreshToken = writable<string | null>(readFromStorage(REFRESH_TOKEN_KEY));

// Persist every change to localStorage
token.subscribe((v) => writeToStorage(ACCESS_TOKEN_KEY, v));
refreshToken.subscribe((v) => writeToStorage(REFRESH_TOKEN_KEY, v));

// Derived boolean — use this in templates: {#if $isAuthenticated}
export const isAuthenticated = derived(token, ($token) => $token !== null);
