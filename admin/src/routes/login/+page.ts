import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { token } from '$lib/stores/auth';
import { isTokenExpired } from '$lib/utils/auth';
import type { PageLoad } from './$types';

export const load: PageLoad = () => {
	if (!browser) return;

	const currentToken = get(token);

	if (currentToken && !isTokenExpired(currentToken)) {
		throw redirect(302, '/dashboard');
	}
};
