/**
 * Auth store — single source of truth for JWT token state.
 *
 * Backed by localStorage so the token survives page refreshes.
 * The store syncs to/from localStorage automatically on every write.
 *
 * Import `token` to read/write the raw token.
 * Import `isAuthenticated` to reactively check auth state in components.
 */

import { derived, writable } from 'svelte/store';

const STORAGE_KEY = 'admin_token';

function readFromStorage(): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem(STORAGE_KEY);
}

function writeToStorage(value: string | null): void {
	if (typeof localStorage === 'undefined') return;
	if (value) {
		localStorage.setItem(STORAGE_KEY, value);
	} else {
		localStorage.removeItem(STORAGE_KEY);
	}
}

// Initialize from localStorage (null on SSR — localStorage is unavailable)
export const token = writable<string | null>(readFromStorage());

// Persist every change to localStorage
token.subscribe(writeToStorage);

// Derived boolean — use this in templates: {#if $isAuthenticated}
export const isAuthenticated = derived(token, ($token) => $token !== null);
