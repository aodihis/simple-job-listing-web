export interface TokenResponse {
	access_token: string;
	token_type: string;
	expires_in: number;
}

export interface AdminUserRead {
	public_id: string;
	email: string;
	display_name: string;
	is_active: boolean;
}

export type EmploymentType = 'full_time' | 'part_time' | 'contract' | 'internship';
export type ApplicationMode = 'form' | 'external_url';

export interface TagRead {
	name: string;
}

export interface JobListItem {
	public_id: string;
	title: string;
	employment_type: EmploymentType;
	location: string | null;
	is_remote: boolean;
	is_active: boolean;
	is_deleted: boolean;
	tags: TagRead[];
	created_at: string;
	expires_at: string | null;
}

export interface JobRead extends JobListItem {
	description: string;
	application_mode: ApplicationMode;
	external_apply_url: string | null;
	updated_at: string;
	posted_by_email: string;
}

export interface JobCreate {
	title: string;
	description: string;
	employment_type: EmploymentType;
	location: string | null;
	is_remote: boolean;
	application_mode: ApplicationMode;
	external_apply_url: string | null;
	tags: string[];
	expires_at: string | null;
}

export interface PaginatedJobs {
	items: JobListItem[];
	total: number;
	page: number;
	per_page: number;
	pages: number;
}

export class ApiError extends Error {
	constructor(
		public readonly status: number,
		public readonly detail: string,
	) {
		super(detail);
		this.name = 'ApiError';
	}
}
