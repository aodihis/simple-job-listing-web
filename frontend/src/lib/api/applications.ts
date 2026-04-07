import { api } from './client';
import type { ApplicationConfirmation, ApplicationCreate } from './types';

export async function submitApplication(
	jobPublicId: string,
	data: ApplicationCreate,
	cvFile: File,
): Promise<ApplicationConfirmation> {
	const form = new FormData();
	form.append('applicant_name', data.applicant_name);
	form.append('applicant_email', data.applicant_email);
	form.append('responses_json', JSON.stringify(data.responses));
	form.append('education_json', JSON.stringify(data.education ?? []));
	form.append('experience_json', JSON.stringify(data.experience ?? []));
	form.append('cv_file', cvFile);
	return api.postFormData<ApplicationConfirmation>(`/api/v1/jobs/${jobPublicId}/apply`, form);
}
