import { api } from './client';

export interface TestEmailResponse {
	success: boolean;
	message: string;
}

export async function sendTestEmail(to: string): Promise<TestEmailResponse> {
	return api.post<TestEmailResponse>('/api/v1/admin/settings/test-email', { to });
}
