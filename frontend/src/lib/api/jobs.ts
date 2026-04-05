import { api } from './client';
import type { JobRead, PaginatedJobs } from './types';

export interface ListJobsParams {
	q?: string;
	tags?: string[];
	employment_type?: string;
	is_remote?: boolean;
	sort?: 'newest' | 'oldest';
	page?: number;
	per_page?: number;
}

export async function listJobs(params: ListJobsParams = {}): Promise<PaginatedJobs> {
	const qs = new URLSearchParams();
	if (params.q) qs.set('q', params.q);
	if (params.employment_type) qs.set('employment_type', params.employment_type);
	if (params.is_remote !== undefined) qs.set('is_remote', String(params.is_remote));
	if (params.sort) qs.set('sort', params.sort);
	if (params.page) qs.set('page', String(params.page));
	if (params.per_page) qs.set('per_page', String(params.per_page));
	if (params.tags?.length) {
		params.tags.forEach((tag) => qs.append('tags', tag));
	}
	const query = qs.toString() ? `?${qs}` : '';
	return api.get<PaginatedJobs>(`/api/v1/jobs${query}`);
}

export async function getJob(publicId: string): Promise<JobRead> {
	return api.get<JobRead>(`/api/v1/jobs/${publicId}`);
}
