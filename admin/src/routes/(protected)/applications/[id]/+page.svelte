<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getApplication, updateApplicationStatus, downloadApplicationCv } from '$lib/api/applications';
	import { getFormFields } from '$lib/api/formFields';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { ApplicationRead, ApplicationStatus } from '$lib/api/types';

	const log = createLogger('ApplicationDetailPage');

	const STATUS_LABELS: Record<ApplicationStatus, string> = {
		new: 'New',
		reviewed: 'Reviewed',
		rejected: 'Rejected',
		hired: 'Hired',
	};

	const STATUS_OPTIONS: ApplicationStatus[] = ['new', 'reviewed', 'rejected', 'hired'];

	let application: ApplicationRead | null = null;
	let fieldLabels: Record<string, string> = {};
	let errorMessage = '';
	let isLoading = true;
	let isUpdatingStatus = false;
	let statusSuccess = false;
	let isDownloadingCv = false;
	let cvDownloadError = '';

	$: publicId = $page.params.id;

	async function load() {
		isLoading = true;
		errorMessage = '';
		try {
			application = await getApplication(publicId);
			const formFields = await getFormFields(application.job_public_id);
			fieldLabels = Object.fromEntries(formFields.map((f) => [String(f.id), f.label]));
			log.info('application.detail_loaded', { public_id: publicId });
		} catch (err) {
			if (err instanceof ApiError && err.status === 404) {
				errorMessage = 'Application not found.';
			} else {
				errorMessage = 'Failed to load application. Please try again.';
			}
			log.error('application.load_failed', { public_id: publicId, error: String(err) });
		} finally {
			isLoading = false;
		}
	}

	async function handleCvDownload() {
		if (!application?.cv_filename) return;
		isDownloadingCv = true;
		cvDownloadError = '';
		try {
			await downloadApplicationCv(publicId, application.cv_filename);
		} catch (err) {
			cvDownloadError = 'Failed to download CV. Please try again.';
			log.error('application.cv_download_failed', { public_id: publicId, error: String(err) });
		} finally {
			isDownloadingCv = false;
		}
	}

	async function handleStatusChange(newStatus: ApplicationStatus) {
		if (!application || newStatus === application.status) return;
		isUpdatingStatus = true;
		statusSuccess = false;
		try {
			application = await updateApplicationStatus(publicId, newStatus);
			statusSuccess = true;
			setTimeout(() => (statusSuccess = false), 2500);
			log.info('application.status_updated', { public_id: publicId, status: newStatus });
		} catch (err) {
			errorMessage = 'Failed to update status. Please try again.';
			log.error('application.status_update_failed', { public_id: publicId, error: String(err) });
		} finally {
			isUpdatingStatus = false;
		}
	}

	function formatResponseValue(value: string | string[]): string {
		if (Array.isArray(value)) return value.join(', ') || '—';
		return value || '—';
	}

	onMount(() => load());
</script>

<svelte:head>
	<title>Application Detail — Admin</title>
</svelte:head>

<div class="page">
	<div class="page-header">
		<a href="/applications" class="back-link">← Applications</a>
		<h1>Application Detail</h1>
	</div>

	{#if errorMessage}
		<div class="alert alert-error" role="alert">{errorMessage}</div>
	{/if}

	{#if isLoading}
		<p class="loading">Loading…</p>
	{:else if application}
		<div class="layout">
			<!-- Left: applicant info + responses -->
			<div class="main-col">
				<section class="card">
					<h2 class="card-title">Applicant</h2>
					<dl class="info-grid">
						<dt>Name</dt>
						<dd>{application.applicant_name}</dd>
						<dt>Email</dt>
						<dd>
							<a href="mailto:{application.applicant_email}" class="email-link">
								{application.applicant_email}
							</a>
						</dd>
						<dt>Submitted</dt>
						<dd>{new Date(application.created_at).toLocaleString()}</dd>
						<dt>Job</dt>
						<dd>
							<a href="/jobs/{application.job_public_id}" class="job-link">
								{application.job_title}
							</a>
						</dd>
					</dl>
				</section>

				{#if application.education.length > 0}
					<section class="card">
						<h2 class="card-title">Education</h2>
						<div class="entry-list">
							{#each application.education as edu, i}
								<div class="entry-block" class:entry-divider={i > 0}>
									<p class="entry-title">
										{edu.degree ?? ''}
										{#if edu.field_of_study} — {edu.field_of_study}{/if}
									</p>
									<p class="entry-sub">{edu.institution}</p>
									<p class="entry-meta">
										{edu.start_year ?? '?'} – {edu.end_year ?? 'Present'}
										{#if edu.gpa} · GPA: {edu.gpa}{/if}
									</p>
								</div>
							{/each}
						</div>
					</section>
				{/if}

				{#if application.experience.length > 0}
					<section class="card">
						<h2 class="card-title">Work Experience</h2>
						<div class="entry-list">
							{#each application.experience as exp, i}
								<div class="entry-block" class:entry-divider={i > 0}>
									<p class="entry-title">{exp.title} — {exp.company}</p>
									<p class="entry-meta">
										{exp.start_year ?? '?'} – {exp.end_year ?? 'Present'}
									</p>
									{#if exp.summary}
										<p class="entry-summary">{exp.summary}</p>
									{/if}
								</div>
							{/each}
						</div>
					</section>
				{/if}

				{#if Object.keys(application.responses).length > 0}
					<section class="card">
						<h2 class="card-title">Form Responses</h2>
						<dl class="responses-list">
							{#each Object.entries(application.responses) as [fieldId, value]}
								<div class="response-item">
									<dt class="field-id">{fieldLabels[fieldId] ?? `Field #${fieldId}`}</dt>
									<dd class="field-value">{formatResponseValue(value)}</dd>
								</div>
							{/each}
						</dl>
					</section>
				{:else}
					<section class="card">
						<h2 class="card-title">Form Responses</h2>
						<p class="muted">No form responses — this job had no custom fields.</p>
					</section>
				{/if}
			</div>

			<!-- Right: status panel -->
			<aside class="sidebar-col">
				<section class="card">
					<h2 class="card-title">Status</h2>

					<div class="current-status">
						<span class="badge badge-{application.status}">
							{STATUS_LABELS[application.status]}
						</span>
					</div>

					{#if statusSuccess}
						<p class="status-success">Status updated.</p>
					{/if}

					<div class="status-actions">
						{#each STATUS_OPTIONS as status}
							<button
								class="status-btn"
								class:status-btn-active={application.status === status}
								disabled={isUpdatingStatus || application.status === status}
								on:click={() => handleStatusChange(status)}
							>
								{STATUS_LABELS[status]}
							</button>
						{/each}
					</div>
				</section>

				<section class="card">
					<h2 class="card-title">CV / Resume</h2>
					{#if application.cv_filename}
						{#if cvDownloadError}
							<p class="cv-error">{cvDownloadError}</p>
						{/if}
						<button
							class="cv-download-btn"
							disabled={isDownloadingCv}
							on:click={handleCvDownload}
						>
							{isDownloadingCv ? 'Downloading…' : '⬇ ' + application.cv_filename}
						</button>
					{:else}
						<p class="muted">No CV attached.</p>
					{/if}
				</section>

				<section class="card meta-card">
					<h2 class="card-title">Reference</h2>
					<p class="reference-id">{application.public_id}</p>
				</section>
			</aside>
		</div>
	{/if}
</div>

<style>
	.page {
		max-width: 900px;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	.back-link {
		display: inline-block;
		font-size: 0.875rem;
		color: var(--color-text-muted);
		text-decoration: none;
		margin-bottom: 0.5rem;
		transition: color 0.15s;
	}

	.back-link:hover {
		color: var(--color-text);
	}

	h1 {
		margin: 0;
	}

	.alert {
		padding: 0.75rem 1rem;
		border-radius: var(--radius);
		margin-bottom: 1rem;
		font-size: 0.9rem;
	}

	.alert-error {
		background: #fff5f5;
		border: 1px solid #feb2b2;
		color: var(--color-danger);
	}

	.loading {
		color: var(--color-text-muted);
	}

	.layout {
		display: grid;
		grid-template-columns: 1fr 260px;
		gap: 1.25rem;
		align-items: start;
	}

	.main-col {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.sidebar-col {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		padding: 1.25rem;
	}

	.card-title {
		margin: 0 0 1rem;
		font-size: 0.95rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.info-grid {
		display: grid;
		grid-template-columns: 110px 1fr;
		gap: 0.5rem 1rem;
		margin: 0;
	}

	dt {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.03em;
		padding-top: 0.1rem;
	}

	dd {
		margin: 0;
		font-size: 0.9rem;
		word-break: break-word;
	}

	.email-link,
	.job-link {
		color: var(--color-primary);
		text-decoration: none;
	}

	.email-link:hover,
	.job-link:hover {
		text-decoration: underline;
	}

	.responses-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin: 0;
	}

	.response-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.field-id {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.field-value {
		margin: 0;
		font-size: 0.9rem;
		word-break: break-word;
		white-space: pre-wrap;
	}

	.muted {
		color: var(--color-text-muted);
		font-size: 0.9rem;
		margin: 0;
	}

	.current-status {
		margin-bottom: 0.75rem;
	}

	.badge {
		display: inline-block;
		padding: 0.25rem 0.65rem;
		border-radius: 999px;
		font-size: 0.8rem;
		font-weight: 500;
		border: 1px solid var(--color-border);
		background: var(--color-bg);
		color: var(--color-text-muted);
	}

	.badge-new {
		background: #ebf8ff;
		border-color: #90cdf4;
		color: #2b6cb0;
	}

	.badge-reviewed {
		background: #fffff0;
		border-color: #faf089;
		color: #b7791f;
	}

	.badge-rejected {
		background: #fff5f5;
		border-color: #feb2b2;
		color: var(--color-danger);
	}

	.badge-hired {
		background: #f0fff4;
		border-color: #9ae6b4;
		color: var(--color-success);
	}

	.status-success {
		font-size: 0.825rem;
		color: var(--color-success);
		margin: 0 0 0.75rem;
	}

	.status-actions {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.status-btn {
		width: 100%;
		padding: 0.45rem 0.75rem;
		font-size: 0.875rem;
		text-align: left;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		background: var(--color-surface);
		color: var(--color-text);
		cursor: pointer;
		transition: border-color 0.15s, background 0.15s;
	}

	.status-btn:hover:not(:disabled) {
		background: var(--color-bg);
		border-color: var(--color-text-muted);
	}

	.status-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.status-btn-active {
		border-color: var(--color-primary);
		color: var(--color-primary);
		background: #eff6ff;
		font-weight: 500;
	}

	.meta-card {
		padding: 1rem 1.25rem;
	}

	.reference-id {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		font-family: monospace;
		word-break: break-all;
		margin: 0;
	}

	/* Education / Experience entries */
	.entry-list {
		display: flex;
		flex-direction: column;
	}

	.entry-block {
		padding: 0.75rem 0;
	}

	.entry-divider {
		border-top: 1px solid var(--color-border);
	}

	.entry-block:first-child {
		padding-top: 0;
	}

	.entry-title {
		margin: 0 0 0.15rem;
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.entry-sub {
		margin: 0 0 0.15rem;
		font-size: 0.875rem;
		color: var(--color-text-muted);
	}

	.entry-meta {
		margin: 0;
		font-size: 0.8rem;
		color: var(--color-text-muted);
	}

	.entry-summary {
		margin: 0.4rem 0 0;
		font-size: 0.875rem;
		color: var(--color-text);
		white-space: pre-wrap;
	}
</style>
