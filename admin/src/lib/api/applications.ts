import { get } from 'svelte/store';
import { api } from './client';
import { token } from '$lib/stores/auth';
import { ApiError } from './types';
import type { ApplicationRead, ApplicationStatus, PaginatedApplications } from './types';

export interface ListApplicationsParams {
	job_id?: string;
	status?: ApplicationStatus;
	page?: number;
	per_page?: number;
}

export async function listApplications(
	params: ListApplicationsParams = {},
): Promise<PaginatedApplications> {
	const query = new URLSearchParams();
	if (params.job_id) query.set('job_id', params.job_id);
	if (params.status) query.set('status', params.status);
	if (params.page) query.set('page', String(params.page));
	if (params.per_page) query.set('per_page', String(params.per_page));
	const qs = query.toString();
	return api.get<PaginatedApplications>(`/api/v1/admin/applications${qs ? `?${qs}` : ''}`);
}

export async function getApplication(publicId: string): Promise<ApplicationRead> {
	return api.get<ApplicationRead>(`/api/v1/admin/applications/${publicId}`);
}

export async function updateApplicationStatus(
	publicId: string,
	status: ApplicationStatus,
): Promise<ApplicationRead> {
	return api.patch<ApplicationRead>(`/api/v1/admin/applications/${publicId}/status`, { status });
}

/**
 * Fetch the CV file for an application and trigger a browser download.
 * Uses the auth token in the Authorization header.
 */
export async function downloadApplicationCv(publicId: string, filename: string): Promise<void> {
	const currentToken = get(token);
	const headers: Record<string, string> = {};
	if (currentToken) headers['Authorization'] = `Bearer ${currentToken}`;

	const response = await fetch(`/api/v1/admin/applications/${publicId}/cv`, { headers });

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

	const blob = await response.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}
