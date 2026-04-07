import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { token, refreshToken } from '$lib/stores/auth';
import { isTokenExpired, setAuth, clearAuth } from '$lib/utils/auth';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async () => {
	if (!browser) return;

	const currentToken = get(token);

	if (currentToken && !isTokenExpired(currentToken)) {
		return; // Access token still valid — proceed normally
	}

	// Access token missing or expired — try a silent refresh
	const rt = get(refreshToken);
	if (rt) {
		try {
			const { refreshAccessToken } = await import('$lib/api/auth');
			const response = await refreshAccessToken(rt);
			setAuth(response);
			return; // Refresh succeeded — proceed
		} catch {
			// Refresh token invalid or expired — fall through to redirect
		}
	}

	clearAuth();
	throw redirect(302, '/login');
};
