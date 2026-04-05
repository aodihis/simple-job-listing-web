import { redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { token } from '$lib/stores/auth';
import { isTokenExpired } from '$lib/utils/auth';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = () => {
	const currentToken = get(token);

	if (!currentToken || isTokenExpired(currentToken)) {
		// Clear stale token if it exists but is expired
		if (currentToken) {
			token.set(null);
		}
		throw redirect(302, '/login');
	}
};
