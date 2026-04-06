import { api } from './client';
import type { ApplicationConfirmation, ApplicationCreate } from './types';

export async function submitApplication(
	jobPublicId: string,
	data: ApplicationCreate,
): Promise<ApplicationConfirmation> {
	return api.post<ApplicationConfirmation>(`/api/v1/jobs/${jobPublicId}/apply`, data);
}
