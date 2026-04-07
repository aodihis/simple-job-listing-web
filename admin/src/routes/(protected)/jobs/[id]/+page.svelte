<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getAdminJob, updateJob } from '$lib/api/jobs';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { ApplicationMode, EmploymentType } from '$lib/api/types';
	import RichTextEditor from '$lib/components/RichTextEditor.svelte';

	const log = createLogger('EditJobPage');

	$: jobId = $page.params.id;

	let isLoading = true;
	let isSaving = false;
	let loadError = '';
	let errorMessage = '';
	let fieldErrors: Record<string, string> = {};

	// Form state
	let title = '';
	let description = '';
	let employmentType: EmploymentType = 'full_time';
	let location = '';
	let isRemote = false;
	let salaryMin = '';
	let salaryMax = '';
	let applicationMode: ApplicationMode = 'form';
	let externalApplyUrl = '';
	let tagsInput = '';
	let expiresAt = '';

	onMount(async () => {
		try {
			const job = await getAdminJob(jobId);
			title = job.title;
			description = job.description;
			employmentType = job.employment_type as EmploymentType;
			location = job.location ?? '';
			isRemote = job.is_remote;
			applicationMode = job.application_mode as ApplicationMode;
			externalApplyUrl = job.external_apply_url ?? '';
			tagsInput = job.tags.map((t) => t.name).join(', ');
			expiresAt = job.expires_at ? job.expires_at.slice(0, 10) : '';
			salaryMin = job.salary_min != null ? String(job.salary_min) : '';
			salaryMax = job.salary_max != null ? String(job.salary_max) : '';
			log.info('job.loaded_for_edit', { public_id: jobId });
		} catch (err) {
			loadError =
				err instanceof ApiError && err.status === 404
					? 'Job not found.'
					: 'Failed to load job. Please refresh.';
			log.error('job.load_failed', { public_id: jobId, error: String(err) });
		} finally {
			isLoading = false;
		}
	});

	function validate(): boolean {
		fieldErrors = {};
		let valid = true;
		if (!title.trim()) { fieldErrors['title'] = 'Title is required.'; valid = false; }
		if (!description || description === '<p></p>') {
			fieldErrors['description'] = 'Description is required.'; valid = false;
		}
		if (applicationMode === 'external_url' && !externalApplyUrl.trim()) {
			fieldErrors['externalApplyUrl'] = 'An external URL is required.'; valid = false;
		}
		if (externalApplyUrl && !/^https?:\/\/.+/.test(externalApplyUrl)) {
			fieldErrors['externalApplyUrl'] = 'Must start with http:// or https://'; valid = false;
		}
		const minVal = salaryMin !== '' ? parseInt(salaryMin, 10) : null;
		const maxVal = salaryMax !== '' ? parseInt(salaryMax, 10) : null;
		if (minVal !== null && minVal < 0) { fieldErrors['salaryMin'] = 'Salary cannot be negative.'; valid = false; }
		if (maxVal !== null && maxVal < 0) { fieldErrors['salaryMax'] = 'Salary cannot be negative.'; valid = false; }
		if (minVal !== null && maxVal !== null && maxVal < minVal) {
			fieldErrors['salaryMax'] = 'Maximum must be greater than or equal to minimum.'; valid = false;
		}
		return valid;
	}

	async function handleSubmit() {
		errorMessage = '';
		if (!validate()) return;

		const tags = tagsInput.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);

		isSaving = true;
		try {
			await updateJob(jobId, {
				title: title.trim(),
				description: description.trim(),
				employment_type: employmentType,
				location: location.trim() || null,
				is_remote: isRemote,
				salary_min: salaryMin !== '' ? parseInt(salaryMin, 10) : null,
				salary_max: salaryMax !== '' ? parseInt(salaryMax, 10) : null,
				application_mode: applicationMode,
				external_apply_url: applicationMode === 'external_url' ? externalApplyUrl.trim() : null,
				tags,
				expires_at: expiresAt || null,
			});
			log.info('job.updated', { public_id: jobId });
			goto('/jobs');
		} catch (err) {
			if (err instanceof ApiError) {
				errorMessage = err.status === 422
					? 'Please check your inputs — ' + err.detail
					: 'Failed to save job. Please try again.';
				log.error('job.update_failed', { status: err.status, detail: err.detail });
			} else {
				errorMessage = 'An unexpected error occurred.';
				log.error('job.update_error', { error: String(err) });
			}
		} finally {
			isSaving = false;
		}
	}
</script>

<svelte:head>
	<title>Edit Job — Admin</title>
</svelte:head>

<div class="page">
	<a href="/jobs" class="back-link">← Back to Jobs</a>
	<div class="page-header">
		<h1>Edit Job</h1>
		{#if !isLoading && !loadError}
			<div class="header-actions">
				<a href="/jobs/{jobId}/form" class="btn-secondary">Edit Form</a>
				<button type="submit" form="edit-job-form" class="btn-primary" disabled={isSaving}>
					{isSaving ? 'Saving…' : 'Save Changes'}
				</button>
			</div>
		{/if}
	</div>

	{#if isLoading}
		<p class="loading">Loading…</p>
	{:else if loadError}
		<div class="alert alert-error" role="alert">{loadError}</div>
	{:else}
		{#if errorMessage}
			<div class="alert alert-error" role="alert">{errorMessage}</div>
		{/if}

		<form id="edit-job-form" on:submit|preventDefault={handleSubmit} novalidate>
			<div class="form-section">
				<h2>Basic Info</h2>

				<div class="field">
					<label for="title">Job Title <span class="required">*</span></label>
					<input
						id="title"
						type="text"
						bind:value={title}
						placeholder="e.g. Senior Backend Engineer"
						disabled={isSaving}
						class:invalid={fieldErrors['title']}
					/>
					{#if fieldErrors['title']}
						<span class="field-error">{fieldErrors['title']}</span>
					{/if}
				</div>

				<div class="field-row">
					<div class="field">
						<label for="employmentType">Employment Type <span class="required">*</span></label>
						<select id="employmentType" bind:value={employmentType} disabled={isSaving}>
							<option value="full_time">Full-time</option>
							<option value="part_time">Part-time</option>
							<option value="contract">Contract</option>
							<option value="internship">Internship</option>
						</select>
					</div>

					<div class="field">
						<label for="location">Location</label>
						<input
							id="location"
							type="text"
							bind:value={location}
							placeholder="e.g. New York, NY"
							disabled={isSaving}
						/>
					</div>
				</div>

				<div class="field-row">
					<div class="field">
						<label for="salaryMin">Minimum Salary</label>
						<input
							id="salaryMin"
							type="number"
							bind:value={salaryMin}
							placeholder="e.g. 60000"
							min="0"
							disabled={isSaving}
							class:invalid={fieldErrors['salaryMin']}
						/>
						{#if fieldErrors['salaryMin']}
							<span class="field-error">{fieldErrors['salaryMin']}</span>
						{/if}
					</div>
					<div class="field">
						<label for="salaryMax">Maximum Salary</label>
						<input
							id="salaryMax"
							type="number"
							bind:value={salaryMax}
							placeholder="e.g. 90000"
							min="0"
							disabled={isSaving}
							class:invalid={fieldErrors['salaryMax']}
						/>
						{#if fieldErrors['salaryMax']}
							<span class="field-error">{fieldErrors['salaryMax']}</span>
						{/if}
					</div>
				</div>
				<span class="field-hint salary-hint">Annual salary in whole currency units. Leave both blank to not disclose.</span>

				<div class="field field-checkbox">
					<label>
						<input type="checkbox" bind:checked={isRemote} disabled={isSaving} />
						Remote-friendly role
					</label>
				</div>

				<div class="field-row">
					<div class="field">
						<label for="tags">Tags</label>
						<input
							id="tags"
							type="text"
							bind:value={tagsInput}
							placeholder="python, remote, senior (comma-separated)"
							disabled={isSaving}
						/>
						<span class="field-hint">Separate tags with commas.</span>
					</div>

					<div class="field">
						<label for="expiresAt">Expiry Date</label>
						<input
							id="expiresAt"
							type="date"
							bind:value={expiresAt}
							disabled={isSaving}
						/>
						<span class="field-hint">Leave blank for no expiry.</span>
					</div>
				</div>
			</div>

			<div class="form-section">
				<h2>Description <span class="required">*</span></h2>
				<div class="field">
					<RichTextEditor
						bind:content={description}
						disabled={isSaving}
						invalid={!!fieldErrors['description']}
					/>
					{#if fieldErrors['description']}
						<span class="field-error">{fieldErrors['description']}</span>
					{/if}
				</div>
			</div>

			<div class="form-section">
				<h2>Application Settings</h2>

				<div class="field">
					<label>How should candidates apply?</label>
					<div class="radio-group">
						<label class="radio-label">
							<input type="radio" bind:group={applicationMode} value="form" disabled={isSaving} />
							<div>
								<strong>Built-in form</strong>
								<p>Candidates apply directly on this site.</p>
							</div>
						</label>
						<label class="radio-label">
							<input type="radio" bind:group={applicationMode} value="external_url" disabled={isSaving} />
							<div>
								<strong>External URL</strong>
								<p>Redirect candidates to an external application page.</p>
							</div>
						</label>
					</div>
				</div>

				{#if applicationMode === 'external_url'}
					<div class="field">
						<label for="externalApplyUrl">External Apply URL <span class="required">*</span></label>
						<input
							id="externalApplyUrl"
							type="url"
							bind:value={externalApplyUrl}
							placeholder="https://apply.example.com/jobs/123"
							disabled={isSaving}
							class:invalid={fieldErrors['externalApplyUrl']}
						/>
						{#if fieldErrors['externalApplyUrl']}
							<span class="field-error">{fieldErrors['externalApplyUrl']}</span>
						{/if}
					</div>
				{/if}
			</div>

			</form>
	{/if}
</div>

<style>
	.page { width: 100%; }

	.back-link {
		display: block;
		font-size: 0.875rem;
		color: var(--color-text-muted);
		text-decoration: none;
		margin-bottom: 0.25rem;
	}

	.back-link:hover { color: var(--color-primary); }

	h1 { margin: 0; }

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	.loading { color: var(--color-text-muted); }

	.alert {
		padding: 0.75rem 1rem;
		border-radius: var(--radius);
		margin-bottom: 1.25rem;
		font-size: 0.9rem;
	}

	.alert-error {
		background: #fff5f5;
		border: 1px solid #feb2b2;
		color: var(--color-danger);
	}

	.form-section {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		padding: 1.5rem;
		margin-bottom: 1.25rem;
	}

	.form-section h2 {
		margin: 0 0 1.25rem;
		font-size: 1rem;
		font-weight: 600;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		margin-bottom: 1rem;
	}

	.field:last-child { margin-bottom: 0; }

	.field-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.field-row .field { margin-bottom: 0; }

	.field-checkbox { flex-direction: row; align-items: center; }

	.field-checkbox label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		font-weight: normal;
	}

	label { font-size: 0.875rem; font-weight: 500; }

	.required { color: var(--color-danger); }

	.salary-hint {
		display: block;
		margin-top: -0.75rem;
		margin-bottom: 1rem;
	}

	input[type='text'],
	input[type='url'],
	input[type='date'],
	input[type='number'],
	select {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		font-size: 0.95rem;
		font-family: inherit;
		outline: none;
		transition: border-color 0.15s;
		width: 100%;
		background: white;
	}

	input:focus, select:focus { border-color: var(--color-primary); }
	input.invalid { border-color: var(--color-danger); }
	input:disabled, select:disabled { opacity: 0.6; cursor: not-allowed; }

	.field-error { font-size: 0.8rem; color: var(--color-danger); }
	.field-hint { font-size: 0.8rem; color: var(--color-text-muted); }

	.radio-group {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-top: 0.25rem;
	}

	.radio-label {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		cursor: pointer;
		transition: border-color 0.15s;
		font-weight: normal;
	}

	.radio-label:has(input:checked) {
		border-color: var(--color-primary);
		background: #f0f7ff;
	}

	.radio-label input { margin-top: 0.2rem; flex-shrink: 0; }
	.radio-label strong { display: block; font-size: 0.9rem; }
	.radio-label p { margin: 0.15rem 0 0; font-size: 0.8rem; color: var(--color-text-muted); }

	.btn-primary {
		padding: 0.55rem 1.25rem;
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius);
		font-size: 0.95rem;
		font-weight: 500;
		transition: background 0.15s;
		cursor: pointer;
	}

	.btn-primary:hover:not(:disabled) { background: var(--color-primary-hover); }
	.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

	.btn-secondary {
		padding: 0.55rem 1.25rem;
		background: var(--color-surface);
		color: var(--color-text);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		font-size: 0.95rem;
		text-decoration: none;
		transition: border-color 0.15s;
		display: inline-block;
	}

	.btn-secondary:hover { border-color: var(--color-text-muted); }

	@media (max-width: 600px) {
		.field-row { grid-template-columns: 1fr; }
	}
</style>
