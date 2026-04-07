<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getJob } from '$lib/api/jobs';
	import { submitApplication } from '$lib/api/applications';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { JobRead } from '$lib/api/types';

	const log = createLogger('ApplyPage');

	$: publicId = $page.params.id;

	// ── Page state ────────────────────────────────────────────────────────────
	let job: JobRead | null = null;
	let isLoading = true;
	let notFound = false;
	let loadError = '';

	// ── Form state ────────────────────────────────────────────────────────────
	let applicantName = '';
	let applicantEmail = '';
	// responses keyed by string(field.id)
	let responses: Record<string, string | string[]> = {};
	let cvFile: File | null = null;

	let isSubmitting = false;
	let submitError = '';
	let submitted = false;
	let confirmationId = '';

	let fieldErrors: Record<string, string> = {};

	// ── Education / Experience state ──────────────────────────────────────────
	interface EduDraft {
		institution: string;
		degree: string;
		field_of_study: string;
		gpa: string;
		start_year: string;
		end_year: string; // empty string = present
	}
	interface ExpDraft {
		title: string;
		company: string;
		summary: string;
		start_year: string;
		end_year: string; // empty string = present
	}

	const currentYear = new Date().getFullYear();
	let education: EduDraft[] = [];
	let experience: ExpDraft[] = [];

	function addEducation() {
		education = [
			...education,
			{ institution: '', degree: '', field_of_study: '', gpa: '', start_year: '', end_year: '' },
		];
	}
	function removeEducation(i: number) {
		education = education.filter((_, idx) => idx !== i);
	}

	function addExperience() {
		experience = [
			...experience,
			{ title: '', company: '', summary: '', start_year: '', end_year: '' },
		];
	}
	function removeExperience(i: number) {
		experience = experience.filter((_, idx) => idx !== i);
	}

	function serializeEducation() {
		return education.map((e) => ({
			institution: e.institution,
			degree: e.degree,
			field_of_study: e.field_of_study || null,
			gpa: e.gpa || null,
			start_year: e.start_year ? parseInt(e.start_year) : null,
			end_year: e.end_year ? parseInt(e.end_year) : null,
		}));
	}

	function serializeExperience() {
		return experience.map((e) => ({
			title: e.title,
			company: e.company,
			summary: e.summary || null,
			start_year: e.start_year ? parseInt(e.start_year) : null,
			end_year: e.end_year ? parseInt(e.end_year) : null,
		}));
	}

	// ── Load job ──────────────────────────────────────────────────────────────
	onMount(async () => {
		try {
			job = await getJob(publicId);

			if (job.application_mode === 'external_url' && job.external_apply_url) {
				// Redirect immediately for external applications
				window.location.href = job.external_apply_url;
				return;
			}

			// Initialise response map with empty values
			for (const f of job.form_fields) {
				responses[String(f.id)] = f.field_type === 'checkbox' ? [] : '';
			}

			log.info('apply.page_loaded', { public_id: publicId, field_count: job.form_fields.length });
		} catch (err) {
			if (err instanceof ApiError && err.status === 404) {
				notFound = true;
			} else {
				loadError = 'Failed to load job details. Please try again.';
				log.error('apply.load_failed', { public_id: publicId, error: String(err) });
			}
		} finally {
			isLoading = false;
		}
	});

	// ── Checkbox helpers ──────────────────────────────────────────────────────
	function toggleCheckbox(fieldId: string, option: string, checked: boolean) {
		const current = (responses[fieldId] as string[]) ?? [];
		responses[fieldId] = checked
			? [...current, option]
			: current.filter((v) => v !== option);
	}

	function isChecked(fieldId: string, option: string): boolean {
		const val = responses[fieldId];
		return Array.isArray(val) && val.includes(option);
	}

	// ── Validation ────────────────────────────────────────────────────────────
	function validate(): boolean {
		fieldErrors = {};
		let valid = true;

		if (!applicantName.trim()) {
			fieldErrors['_name'] = 'Your name is required.';
			valid = false;
		}
		if (!applicantEmail.trim()) {
			fieldErrors['_email'] = 'Your email is required.';
			valid = false;
		} else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(applicantEmail)) {
			fieldErrors['_email'] = 'Please enter a valid email address.';
			valid = false;
		}
		if (!cvFile) {
			fieldErrors['_cv'] = 'Please attach your CV (PDF, DOC, or DOCX).';
			valid = false;
		}

		if (!job) return false;

		for (const f of job.form_fields) {
			if (!f.is_required) continue;
			const key = String(f.id);
			const val = responses[key];
			const empty =
				val === undefined ||
				val === null ||
				(typeof val === 'string' && !val.trim()) ||
				(Array.isArray(val) && val.length === 0);
			if (empty) {
				fieldErrors[key] = `"${f.label}" is required.`;
				valid = false;
			}
		}

		return valid;
	}

	// ── Submit ────────────────────────────────────────────────────────────────
	async function handleSubmit() {
		submitError = '';
		if (!validate() || !job || !cvFile) return;

		isSubmitting = true;
		try {
			const result = await submitApplication(
				publicId,
				{
					applicant_name: applicantName.trim(),
					applicant_email: applicantEmail.trim(),
					responses,
					education: serializeEducation(),
					experience: serializeExperience(),
				},
				cvFile,
			);
			confirmationId = result.public_id;
			submitted = true;
			log.info('application.submitted', { job_id: publicId, confirmation: result.public_id });
		} catch (err) {
			if (err instanceof ApiError) {
				if (err.status === 409) {
					submitError = 'You have already applied for this position.';
				} else if (err.status === 400) {
					submitError = err.detail;
				} else {
					submitError = 'Something went wrong. Please try again.';
				}
			} else {
				submitError = 'Something went wrong. Please try again.';
			}
			log.error('application.submit_failed', { job_id: publicId, error: String(err) });
		} finally {
			isSubmitting = false;
		}
	}
</script>

<svelte:head>
	<title>{job ? `Apply — ${job.title}` : 'Apply — JobBoard'}</title>
</svelte:head>

<div class="apply-page">
	<a href="/jobs/{publicId}" class="back-link">← Back to job</a>

	{#if isLoading}
		<div class="skeleton-wrap">
			<div class="skeleton sk-title"></div>
			<div class="skeleton sk-body"></div>
		</div>

	{:else if notFound}
		<div class="state-box">
			<h1>Position Not Found</h1>
			<p>This job may have been removed or is no longer accepting applications.</p>
			<a href="/" class="btn-primary">Browse all jobs</a>
		</div>

	{:else if loadError}
		<div class="alert-error" role="alert">{loadError}</div>

	{:else if submitted}
		<div class="success-box">
			<div class="success-icon">✓</div>
			<h1>Application submitted!</h1>
			<p>Thanks for applying for <strong>{job?.title}</strong>. We'll be in touch soon.</p>
			<p class="confirmation-id">Reference: <code>{confirmationId}</code></p>
			<a href="/" class="btn-primary">Browse more jobs</a>
		</div>

	{:else if job}
		<div class="apply-header">
			<h1>Apply for <span class="job-name">{job.title}</span></h1>
			{#if job.location || job.is_remote}
				<p class="job-meta">
					{#if job.location}{job.location}{/if}
					{#if job.location && job.is_remote} · {/if}
					{#if job.is_remote}Remote{/if}
				</p>
			{/if}
		</div>

		{#if submitError}
			<div class="alert-error" role="alert">{submitError}</div>
		{/if}

		<form on:submit|preventDefault={handleSubmit} novalidate>
			<!-- Always-present fields -->
			<div class="form-section">
				<h2>Your details</h2>

				<div class="field">
					<label for="applicant-name">Full name <span class="required">*</span></label>
					<input
						id="applicant-name"
						type="text"
						bind:value={applicantName}
						placeholder="Jane Smith"
						disabled={isSubmitting}
						class:invalid={fieldErrors['_name']}
					/>
					{#if fieldErrors['_name']}
						<span class="field-error">{fieldErrors['_name']}</span>
					{/if}
				</div>

				<div class="field">
					<label for="applicant-email">Email address <span class="required">*</span></label>
					<input
						id="applicant-email"
						type="email"
						bind:value={applicantEmail}
						placeholder="jane@example.com"
						disabled={isSubmitting}
						class:invalid={fieldErrors['_email']}
					/>
					{#if fieldErrors['_email']}
						<span class="field-error">{fieldErrors['_email']}</span>
					{/if}
				</div>

				<div class="field">
					<label for="cv-upload">CV / Resume <span class="required">*</span></label>
					<div class="file-input-wrap" class:invalid={fieldErrors['_cv']}>
						<label for="cv-upload" class="file-label" class:disabled={isSubmitting}>
							{#if cvFile}
								<span class="file-icon">📄</span>
								<span class="file-name">{cvFile.name}</span>
								<span class="file-change">Change</span>
							{:else}
								<span class="file-icon">📎</span>
								<span class="file-placeholder">Choose file…</span>
							{/if}
						</label>
						<input
							id="cv-upload"
							type="file"
							accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
							disabled={isSubmitting}
							on:change={(e) => {
								const files = e.currentTarget.files;
								cvFile = files && files.length > 0 ? files[0] : null;
							}}
						/>
					</div>
					<span class="field-hint">PDF, DOC, or DOCX · Max 10 MB</span>
					{#if fieldErrors['_cv']}
						<span class="field-error">{fieldErrors['_cv']}</span>
					{/if}
				</div>
			</div>

			<!-- Education -->
			<div class="form-section">
				<div class="section-header">
					<h2>Education</h2>
					<button type="button" class="btn-add" on:click={addEducation}>+ Add</button>
				</div>

				{#if education.length === 0}
					<p class="section-empty">No education added yet.</p>
				{/if}

				{#each education as edu, i}
					<div class="entry-card">
						<div class="entry-header">
							<span class="entry-label">Education #{i + 1}</span>
							<button
								type="button"
								class="btn-remove"
								on:click={() => removeEducation(i)}
								disabled={isSubmitting}
							>Remove</button>
						</div>

						<div class="field-row">
							<div class="field">
								<label for="edu-institution-{i}">Institution</label>
								<input id="edu-institution-{i}" type="text" bind:value={edu.institution} placeholder="e.g. MIT" disabled={isSubmitting} />
							</div>
							<div class="field">
								<label for="edu-degree-{i}">Degree</label>
								<select id="edu-degree-{i}" bind:value={edu.degree} disabled={isSubmitting}>
									<option value="">Select degree…</option>
									<option>High School Diploma</option>
									<option>Associate's</option>
									<option>Bachelor's</option>
									<option>Master's</option>
									<option>PhD / Doctorate</option>
									<option>Professional (MD, JD, etc.)</option>
									<option>Other</option>
								</select>
							</div>
						</div>

						<div class="field-row">
							<div class="field">
								<label for="edu-field-{i}">Field of study</label>
								<input id="edu-field-{i}" type="text" bind:value={edu.field_of_study} placeholder="e.g. Computer Science" disabled={isSubmitting} />
							</div>
							<div class="field">
								<label for="edu-gpa-{i}">GPA</label>
								<input id="edu-gpa-{i}" type="text" bind:value={edu.gpa} placeholder="e.g. 3.8 / 4.0" disabled={isSubmitting} />
							</div>
						</div>

						<div class="field-row">
							<div class="field">
								<label for="edu-start-{i}">Start year</label>
								<input id="edu-start-{i}" type="number" bind:value={edu.start_year} placeholder="2018" min="1950" max={currentYear} disabled={isSubmitting} />
							</div>
							<div class="field">
								<label for="edu-end-{i}">End year <span class="hint-inline">(blank = present)</span></label>
								<input id="edu-end-{i}" type="number" bind:value={edu.end_year} placeholder="Present" min="1950" max={currentYear + 10} disabled={isSubmitting} />
							</div>
						</div>
					</div>
				{/each}
			</div>

			<!-- Work Experience -->
			<div class="form-section">
				<div class="section-header">
					<h2>Work experience</h2>
					<button type="button" class="btn-add" on:click={addExperience}>+ Add</button>
				</div>

				{#if experience.length === 0}
					<p class="section-empty">No experience added yet.</p>
				{/if}

				{#each experience as exp, i}
					<div class="entry-card">
						<div class="entry-header">
							<span class="entry-label">Experience #{i + 1}</span>
							<button
								type="button"
								class="btn-remove"
								on:click={() => removeExperience(i)}
								disabled={isSubmitting}
							>Remove</button>
						</div>

						<div class="field-row">
							<div class="field">
								<label for="exp-title-{i}">Job title</label>
								<input id="exp-title-{i}" type="text" bind:value={exp.title} placeholder="e.g. Software Engineer" disabled={isSubmitting} />
							</div>
							<div class="field">
								<label for="exp-company-{i}">Company</label>
								<input id="exp-company-{i}" type="text" bind:value={exp.company} placeholder="e.g. Acme Corp" disabled={isSubmitting} />
							</div>
						</div>

						<div class="field-row">
							<div class="field">
								<label for="exp-start-{i}">Start year</label>
								<input id="exp-start-{i}" type="number" bind:value={exp.start_year} placeholder="2020" min="1950" max={currentYear} disabled={isSubmitting} />
							</div>
							<div class="field">
								<label for="exp-end-{i}">End year <span class="hint-inline">(blank = present)</span></label>
								<input id="exp-end-{i}" type="number" bind:value={exp.end_year} placeholder="Present" min="1950" max={currentYear + 10} disabled={isSubmitting} />
							</div>
						</div>

						<div class="field">
							<label for="exp-summary-{i}">Summary</label>
							<textarea id="exp-summary-{i}" bind:value={exp.summary} rows="3" placeholder="Briefly describe your responsibilities and achievements…" disabled={isSubmitting}></textarea>
						</div>
					</div>
				{/each}
			</div>

			<!-- Dynamic fields -->
			{#if job.form_fields.length > 0}
				<div class="form-section">
					<h2>Application questions</h2>

					{#each job.form_fields as field (field.id)}
						{@const key = String(field.id)}
						<div class="field">
							<label for="field-{field.id}">
								{field.label}
								{#if field.is_required}<span class="required">*</span>{/if}
							</label>

							{#if field.field_type === 'textarea'}
								<textarea
									id="field-{field.id}"
									bind:value={responses[key]}
									rows="5"
									disabled={isSubmitting}
									class:invalid={fieldErrors[key]}
								></textarea>

							{:else if field.field_type === 'radio'}
								<div class="radio-group" role="radiogroup" aria-labelledby="label-{field.id}">
									{#each field.options as option}
										<label class="radio-option">
											<input
												type="radio"
												name="field-{field.id}"
												value={option}
												bind:group={responses[key]}
												disabled={isSubmitting}
											/>
											{option}
										</label>
									{/each}
								</div>

							{:else if field.field_type === 'select'}
								<select
									id="field-{field.id}"
									bind:value={responses[key]}
									disabled={isSubmitting}
									class:invalid={fieldErrors[key]}
								>
									<option value="">— Select an option —</option>
									{#each field.options as option}
										<option value={option}>{option}</option>
									{/each}
								</select>

							{:else if field.field_type === 'checkbox'}
								<div class="checkbox-group" role="group" aria-labelledby="label-{field.id}">
									{#each field.options as option}
										<label class="checkbox-option">
											<input
												type="checkbox"
												checked={isChecked(key, option)}
												on:change={(e) => toggleCheckbox(key, option, e.currentTarget.checked)}
												disabled={isSubmitting}
											/>
											{option}
										</label>
									{/each}
								</div>

							{:else if field.field_type === 'email'}
								<input
									id="field-{field.id}"
									type="email"
									bind:value={responses[key]}
									disabled={isSubmitting}
									class:invalid={fieldErrors[key]}
								/>
							{:else if field.field_type === 'url'}
								<input
									id="field-{field.id}"
									type="url"
									bind:value={responses[key]}
									disabled={isSubmitting}
									class:invalid={fieldErrors[key]}
								/>
							{:else if field.field_type === 'number'}
								<input
									id="field-{field.id}"
									type="text"
									inputmode="numeric"
									bind:value={responses[key]}
									disabled={isSubmitting}
									class:invalid={fieldErrors[key]}
								/>
							{:else}
								<!-- text (default) -->
								<input
									id="field-{field.id}"
									type="text"
									bind:value={responses[key]}
									disabled={isSubmitting}
									class:invalid={fieldErrors[key]}
								/>
							{/if}

							{#if fieldErrors[key]}
								<span class="field-error">{fieldErrors[key]}</span>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			<div class="form-actions">
				<a href="/jobs/{publicId}" class="btn-secondary">Cancel</a>
				<button type="submit" class="btn-primary" disabled={isSubmitting}>
					{isSubmitting ? 'Submitting…' : 'Submit application'}
				</button>
			</div>
		</form>
	{/if}
</div>

<style>
	.apply-page {
		max-width: 680px;
		margin: 0 auto;
	}

	.back-link {
		display: inline-block;
		font-size: 0.875rem;
		color: #718096;
		text-decoration: none;
		margin-bottom: 1.5rem;
	}

	.back-link:hover { color: #3b82f6; }

	/* Skeleton */
	.skeleton-wrap { display: flex; flex-direction: column; gap: 0.75rem; }
	.skeleton { border-radius: 8px; background: #e2e8f0; animation: pulse 1.4s ease-in-out infinite; }
	.sk-title { height: 2rem; width: 55%; }
	.sk-body  { height: 280px; }
	@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

	/* State boxes */
	.state-box {
		text-align: center;
		padding: 3rem 1rem;
		color: #4a5568;
	}
	.state-box h1 { font-size: 1.4rem; margin-bottom: 0.5rem; color: #1a202c; }
	.state-box p  { margin-bottom: 1.5rem; }

	.success-box {
		text-align: center;
		padding: 3rem 1rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 16px;
	}
	.success-icon {
		width: 3rem;
		height: 3rem;
		background: #48bb78;
		color: white;
		border-radius: 50%;
		font-size: 1.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0 auto 1rem;
	}
	.success-box h1  { font-size: 1.4rem; margin-bottom: 0.5rem; color: #1a202c; }
	.success-box p   { margin-bottom: 0.75rem; color: #4a5568; }
	.confirmation-id { font-size: 0.85rem; color: #718096; }
	.confirmation-id code {
		background: #f7fafc;
		padding: 0.15em 0.4em;
		border-radius: 4px;
		font-family: monospace;
	}

	/* Header */
	.apply-header { margin-bottom: 1.5rem; }
	.apply-header h1 { font-size: 1.5rem; font-weight: 700; color: #1a202c; margin: 0 0 0.3rem; }
	.job-name { color: #3b82f6; }
	.job-meta { font-size: 0.9rem; color: #718096; margin: 0; }

	/* Alert */
	.alert-error {
		background: #fff5f5;
		border: 1px solid #feb2b2;
		color: #c53030;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		font-size: 0.9rem;
		margin-bottom: 1rem;
	}

	/* Form */
	.form-section {
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.5rem;
		margin-bottom: 1rem;
	}
	.form-section h2 {
		margin: 0 0 1.25rem;
		font-size: 1rem;
		font-weight: 600;
		color: #1a202c;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		margin-bottom: 1rem;
	}
	.field:last-child { margin-bottom: 0; }

	label {
		font-size: 0.875rem;
		font-weight: 500;
		color: #2d3748;
	}
	.required { color: #e53e3e; }

	input[type='text'],
	input[type='email'],
	input[type='url'],
	select,
	textarea {
		padding: 0.5rem 0.75rem;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		font-size: 0.95rem;
		font-family: inherit;
		outline: none;
		transition: border-color 0.15s;
		width: 100%;
		background: white;
	}
	input:focus, select:focus, textarea:focus { border-color: #3b82f6; }
	input.invalid, select.invalid, textarea.invalid { border-color: #e53e3e; }
	input:disabled, select:disabled, textarea:disabled { opacity: 0.6; cursor: not-allowed; }

	textarea { resize: vertical; min-height: 120px; line-height: 1.6; }

	/* File upload */
	.file-input-wrap {
		position: relative;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		overflow: hidden;
	}
	.file-input-wrap.invalid { border-color: #e53e3e; }

	.file-input-wrap input[type='file'] {
		position: absolute;
		inset: 0;
		opacity: 0;
		cursor: pointer;
		width: 100%;
		height: 100%;
	}
	.file-input-wrap input[type='file']:disabled { cursor: not-allowed; }

	.file-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		background: white;
		cursor: pointer;
		font-size: 0.95rem;
		min-height: 2.5rem;
		user-select: none;
	}
	.file-label.disabled { opacity: 0.6; cursor: not-allowed; }

	.file-icon { font-style: normal; flex-shrink: 0; }
	.file-placeholder { color: #a0aec0; }
	.file-name { flex: 1; color: #2d3748; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.file-change { margin-left: auto; font-size: 0.8rem; color: #3b82f6; flex-shrink: 0; }

	.field-hint {
		font-size: 0.78rem;
		color: #a0aec0;
	}

	/* Radio / Checkbox groups */
	.radio-group,
	.checkbox-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 0.15rem;
	}

	.radio-option,
	.checkbox-option {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.9rem;
		font-weight: normal;
		color: #2d3748;
		cursor: pointer;
	}

	.radio-option input,
	.checkbox-option input {
		width: auto;
		flex-shrink: 0;
		cursor: pointer;
	}

	.field-error {
		font-size: 0.8rem;
		color: #e53e3e;
	}

	/* Actions */
	.form-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 0.5rem;
	}

	.btn-primary {
		padding: 0.6rem 1.5rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 0.95rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
	}
	.btn-primary:hover:not(:disabled) { background: #2563eb; }
	.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

	.btn-secondary {
		padding: 0.6rem 1.25rem;
		background: white;
		color: #4a5568;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		font-size: 0.95rem;
		text-decoration: none;
		transition: border-color 0.15s;
		display: inline-flex;
		align-items: center;
	}
	.btn-secondary:hover { border-color: #a0aec0; }

	/* Section header with add button */
	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
	}
	.section-header h2 { margin: 0; }

	.section-empty {
		font-size: 0.875rem;
		color: #a0aec0;
		margin: 0;
	}

	/* Entry cards */
	.entry-card {
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		padding: 1rem;
		margin-bottom: 0.75rem;
	}
	.entry-card:last-of-type { margin-bottom: 0; }

	.entry-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}
	.entry-label {
		font-size: 0.8rem;
		font-weight: 600;
		color: #718096;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	/* Two-column row */
	.field-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem;
	}

	/* Add / remove buttons */
	.btn-add {
		padding: 0.3rem 0.75rem;
		background: white;
		color: #3b82f6;
		border: 1px dashed #93c5fd;
		border-radius: 6px;
		font-size: 0.825rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s, border-color 0.15s;
	}
	.btn-add:hover { background: #eff6ff; border-color: #3b82f6; }

	.btn-remove {
		padding: 0.2rem 0.5rem;
		background: none;
		color: #e53e3e;
		border: none;
		font-size: 0.8rem;
		cursor: pointer;
		opacity: 0.7;
		transition: opacity 0.15s;
	}
	.btn-remove:hover:not(:disabled) { opacity: 1; }
	.btn-remove:disabled { cursor: not-allowed; opacity: 0.4; }

	.hint-inline {
		font-size: 0.75rem;
		color: #a0aec0;
		font-weight: 400;
	}

	@media (max-width: 600px) {
		.form-section { padding: 1.25rem; }
		.form-actions { flex-direction: column-reverse; }
		.btn-primary, .btn-secondary { width: 100%; justify-content: center; }
		.field-row { grid-template-columns: 1fr; }
	}
</style>
