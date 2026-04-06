import { api } from './client';
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
