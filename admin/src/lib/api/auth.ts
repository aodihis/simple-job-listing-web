import { publicFetch } from './client';
import type { AdminUserRead, TokenResponse } from './types';

export async function loginAdmin(email: string, password: string): Promise<TokenResponse> {
	return publicFetch<TokenResponse>('/api/v1/auth/login', {
		method: 'POST',
		body: JSON.stringify({ email, password }),
	});
}

export async function registerFirstAdmin(
	email: string,
	displayName: string,
	password: string,
): Promise<TokenResponse> {
	return publicFetch<TokenResponse>('/api/v1/auth/register', {
		method: 'POST',
		body: JSON.stringify({ email, display_name: displayName, password }),
	});
}

export async function refreshAccessToken(rawRefreshToken: string): Promise<TokenResponse> {
	return publicFetch<TokenResponse>('/api/v1/auth/refresh', {
		method: 'POST',
		body: JSON.stringify({ refresh_token: rawRefreshToken }),
	});
}

export async function getMe(): Promise<AdminUserRead> {
	const { api } = await import('./client');
	return api.get<AdminUserRead>('/api/v1/auth/me');
}
