import { api } from './client';
import type { FormFieldRead, FormFieldsUpdate } from './types';

export async function getFormFields(jobPublicId: string): Promise<FormFieldRead[]> {
	return api.get<FormFieldRead[]>(`/api/v1/admin/jobs/${jobPublicId}/form-fields`);
}

export async function saveFormFields(
	jobPublicId: string,
	payload: FormFieldsUpdate,
): Promise<FormFieldRead[]> {
	return api.put<FormFieldRead[]>(`/api/v1/admin/jobs/${jobPublicId}/form-fields`, payload);
}
