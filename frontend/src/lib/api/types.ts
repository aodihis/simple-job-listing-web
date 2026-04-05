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
	tags: TagRead[];
	created_at: string;
	expires_at: string | null;
}

export interface JobRead {
	public_id: string;
	title: string;
	description: string;
	employment_type: EmploymentType;
	location: string | null;
	is_remote: boolean;
	application_mode: ApplicationMode;
	external_apply_url: string | null;
	tags: TagRead[];
	created_at: string;
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
