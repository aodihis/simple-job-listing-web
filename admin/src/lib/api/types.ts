export interface TokenResponse {
	access_token: string;
	refresh_token: string;
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
	salary_min: number | null;
	salary_max: number | null;
	application_mode: ApplicationMode;
	external_apply_url: string | null;
	form_fields: FormFieldRead[];
	updated_at: string;
	posted_by_email: string;
}

export interface JobUpdate {
	title: string;
	description: string;
	employment_type: EmploymentType;
	location: string | null;
	is_remote: boolean;
	salary_min: number | null;
	salary_max: number | null;
	application_mode: ApplicationMode;
	external_apply_url: string | null;
	tags: string[];
	expires_at: string | null;
}

export interface JobCreate {
	title: string;
	description: string;
	employment_type: EmploymentType;
	location: string | null;
	is_remote: boolean;
	salary_min: number | null;
	salary_max: number | null;
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

// ── Form fields ───────────────────────────────────────────────────────────────

export type FieldType =
	| 'text'
	| 'textarea'
	| 'email'
	| 'url'
	| 'number'
	| 'radio'
	| 'select'
	| 'checkbox';

export const OPTION_FIELD_TYPES: FieldType[] = ['radio', 'select', 'checkbox'];

export interface FormFieldRead {
	id: number;
	label: string;
	field_type: FieldType;
	is_required: boolean;
	options: string[];
	order: number;
}

export interface FormFieldCreate {
	label: string;
	field_type: FieldType;
	is_required: boolean;
	options: string[];
}

export interface FormFieldsUpdate {
	fields: FormFieldCreate[];
}

// ── Applications ──────────────────────────────────────────────────────────────

export type ApplicationStatus = 'new' | 'reviewed' | 'rejected' | 'hired';

export interface EducationEntry {
	institution: string;
	degree: string;
	field_of_study: string | null;
	gpa: string | null;
	start_year: number | null;
	end_year: number | null; // null = currently enrolled / present
}

export interface ExperienceEntry {
	title: string;
	company: string;
	summary: string | null;
	start_year: number | null;
	end_year: number | null; // null = current position
}

export interface ApplicationRead {
	public_id: string;
	applicant_name: string;
	applicant_email: string;
	responses: Record<string, string | string[]>;
	status: ApplicationStatus;
	created_at: string;
	job_public_id: string;
	job_title: string;
	cv_filename: string | null;
	education: EducationEntry[];
	experience: ExperienceEntry[];
}

export interface PaginatedApplications {
	items: ApplicationRead[];
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
