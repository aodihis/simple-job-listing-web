import { api } from './client';
import type { JobCreate, JobRead, PaginatedJobs } from './types';

export async function listAdminJobs(params?: {
	page?: number;
	per_page?: number;
	include_deleted?: boolean;
}): Promise<PaginatedJobs> {
	const qs = new URLSearchParams();
	if (params?.page) qs.set('page', String(params.page));
	if (params?.per_page) qs.set('per_page', String(params.per_page));
	if (params?.include_deleted) qs.set('include_deleted', 'true');
	const query = qs.toString() ? `?${qs}` : '';
	return api.get<PaginatedJobs>(`/api/v1/admin/jobs${query}`);
}

export async function getAdminJob(publicId: string): Promise<JobRead> {
	return api.get<JobRead>(`/api/v1/admin/jobs/${publicId}`);
}

export async function createJob(data: JobCreate): Promise<JobRead> {
	return api.post<JobRead>('/api/v1/admin/jobs', data);
}

export async function toggleJob(publicId: string): Promise<JobRead> {
	return api.patch<JobRead>(`/api/v1/admin/jobs/${publicId}/toggle`, {});
}

export async function deleteJob(publicId: string): Promise<JobRead> {
	return api.delete<JobRead>(`/api/v1/admin/jobs/${publicId}`);
}
