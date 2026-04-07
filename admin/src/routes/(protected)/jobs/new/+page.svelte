<script lang="ts">
	import { goto } from '$app/navigation';
	import { createJob } from '$lib/api/jobs';
	import { saveFormFields } from '$lib/api/formFields';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { ApplicationMode, EmploymentType, FieldType } from '$lib/api/types';
	import { OPTION_FIELD_TYPES } from '$lib/api/types';
	import RichTextEditor from '$lib/components/RichTextEditor.svelte';

	const log = createLogger('NewJobPage');

	// ── Tab state ──────────────────────────────────────────────────────────────
	let activeTab: 'details' | 'form' = 'details';

	// ── Job details state ──────────────────────────────────────────────────────
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

	// ── Form builder state ─────────────────────────────────────────────────────
	interface DraftField {
		_key: number;
		label: string;
		field_type: FieldType;
		is_required: boolean;
		options: string[];
		optionsRaw: string;
	}

	let fields: DraftField[] = [];
	let nextKey = 0;

	const FIELD_TYPES: { value: FieldType; label: string }[] = [
		{ value: 'text', label: 'Short text' },
		{ value: 'textarea', label: 'Long text' },
		{ value: 'email', label: 'Email address' },
		{ value: 'url', label: 'URL / Link' },
		{ value: 'number', label: 'Number' },
		{ value: 'radio', label: 'Radio (single choice)' },
		{ value: 'select', label: 'Dropdown (single choice)' },
		{ value: 'checkbox', label: 'Checkboxes (multi-choice)' },
	];

	// ── Submit state ───────────────────────────────────────────────────────────
	let isLoading = false;
	let apiError = '';
	let detailsErrors: Record<string, string> = {};
	let formFieldErrors: { label?: string; options?: string }[] = [];
	let formTabError = '';

	// ── Form builder helpers ───────────────────────────────────────────────────
	function blankField(): DraftField {
		return { _key: nextKey++, label: '', field_type: 'text', is_required: false, options: [], optionsRaw: '' };
	}

	function needsOptions(type: FieldType): boolean {
		return OPTION_FIELD_TYPES.includes(type);
	}

	function syncOptions(f: DraftField): void {
		f.options = [...new Set(f.optionsRaw.split(',').map((s) => s.trim()).filter(Boolean))];
	}

	function addField() { fields = [...fields, blankField()]; }
	function removeField(key: number) { fields = fields.filter((f) => f._key !== key); }

	function moveUp(index: number) {
		if (index === 0) return;
		const copy = [...fields];
		[copy[index - 1], copy[index]] = [copy[index], copy[index - 1]];
		fields = copy;
	}

	function moveDown(index: number) {
		if (index === fields.length - 1) return;
		const copy = [...fields];
		[copy[index], copy[index + 1]] = [copy[index + 1], copy[index]];
		fields = copy;
	}

	function onTypeChange(f: DraftField) {
		if (!needsOptions(f.field_type)) { f.optionsRaw = ''; f.options = []; }
		fields = fields;
	}

	// Switch to form tab when built-in form is selected
	function onApplicationModeChange() {
		if (applicationMode === 'form') activeTab = 'form';
	}

	// ── Validation ─────────────────────────────────────────────────────────────
	function validateDetails(): boolean {
		detailsErrors = {};
		let valid = true;
		if (!title.trim()) {
			detailsErrors['title'] = 'Title is required.';
			valid = false;
		}
		if (!description || description === '<p></p>') {
			detailsErrors['description'] = 'Description is required.';
			valid = false;
		}
		const minVal = salaryMin !== '' ? parseInt(salaryMin, 10) : null;
		const maxVal = salaryMax !== '' ? parseInt(salaryMax, 10) : null;
		if (minVal !== null && minVal < 0) {
			detailsErrors['salaryMin'] = 'Salary cannot be negative.';
			valid = false;
		}
		if (maxVal !== null && maxVal < 0) {
			detailsErrors['salaryMax'] = 'Salary cannot be negative.';
			valid = false;
		}
		if (minVal !== null && maxVal !== null && maxVal < minVal) {
			detailsErrors['salaryMax'] = 'Maximum salary must be greater than or equal to minimum.';
			valid = false;
		}
		if (applicationMode === 'external_url' && !externalApplyUrl.trim()) {
			detailsErrors['externalApplyUrl'] = 'An external URL is required when using external application.';
			valid = false;
		}
		if (externalApplyUrl && !/^https?:\/\/.+/.test(externalApplyUrl)) {
			detailsErrors['externalApplyUrl'] = 'Must be a valid URL starting with http:// or https://';
			valid = false;
		}
		return valid;
	}

	function validateFormFields(): boolean {
		formTabError = '';
		fields.forEach((f) => { if (needsOptions(f.field_type)) syncOptions(f); });

		if (fields.length === 0) {
			formTabError = 'Add at least one field to the application form before publishing.';
			return false;
		}
		if (fields.length > 20) {
			formTabError = 'Maximum 20 fields allowed.';
			return false;
		}

		formFieldErrors = fields.map((f) => {
			const e: { label?: string; options?: string } = {};
			if (!f.label.trim()) e.label = 'Label is required.';
			if (needsOptions(f.field_type)) {
				if (f.options.length === 0) e.options = 'At least one option is required.';
				else if (f.options.length > 20) e.options = 'Maximum 20 options.';
				else if (f.options.some((o) => o.length > 100)) e.options = 'Each option must be 100 characters or fewer.';
			}
			return e;
		});

		return formFieldErrors.every((e) => Object.keys(e).length === 0);
	}

	$: detailsHasErrors = Object.keys(detailsErrors).length > 0;
	$: formHasErrors = formTabError !== '' || formFieldErrors.some((e) => Object.keys(e).length > 0);

	// ── Submit ─────────────────────────────────────────────────────────────────
	async function handleSubmit() {
		apiError = '';

		const detailsOk = validateDetails();
		const formOk = applicationMode === 'form' ? validateFormFields() : true;

		if (!detailsOk) {
			activeTab = 'details';
			return;
		}
		if (!formOk) {
			activeTab = 'form';
			return;
		}

		const tags = tagsInput.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);

		isLoading = true;
		try {
			const job = await createJob({
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

			if (applicationMode === 'form') {
				await saveFormFields(job.public_id, {
					fields: fields.map((f) => ({
						label: f.label.trim(),
						field_type: f.field_type,
						is_required: f.is_required,
						options: f.options,
					})),
				});
				log.info('form_fields.saved', { job_id: job.public_id, count: fields.length });
			}

			log.info('job.created', { title: job.title, public_id: job.public_id });
			goto('/jobs');
		} catch (err) {
			if (err instanceof ApiError) {
				apiError = err.status === 422
					? 'Please check your inputs — ' + err.detail
					: 'Failed to create job. Please try again.';
				log.error('job.create_failed', { status: err.status, detail: err.detail });
			} else {
				apiError = 'An unexpected error occurred. Please try again.';
				log.error('job.create_error', { error: String(err) });
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>New Job — Admin</title>
</svelte:head>

<div class="page">
	<a href="/jobs" class="back-link">← Back to Jobs</a>
	<div class="page-header">
		<h1>Post a New Job</h1>
		<button type="button" class="btn-primary" on:click={handleSubmit} disabled={isLoading}>
			{isLoading ? 'Publishing…' : 'Publish Job'}
		</button>
	</div>

	{#if apiError}
		<div class="alert alert-error" role="alert">{apiError}</div>
	{/if}

	<!-- Tab bar -->
	<div class="tab-bar">
		<button
			type="button"
			class="tab"
			class:active={activeTab === 'details'}
			on:click={() => (activeTab = 'details')}
		>
			Job Details
			{#if detailsHasErrors}
				<span class="error-dot" title="This tab has errors"></span>
			{/if}
		</button>
		<button
			type="button"
			class="tab"
			class:active={activeTab === 'form'}
			disabled={applicationMode !== 'form'}
			on:click={() => (activeTab = 'form')}
		>
			Application Form
			{#if applicationMode !== 'form'}
				<span class="tab-note">N/A</span>
			{:else}
				<span class="tab-note">{fields.length} field{fields.length !== 1 ? 's' : ''}</span>
				{#if formHasErrors}
					<span class="error-dot" title="This tab has errors"></span>
				{/if}
			{/if}
		</button>
	</div>

	<!-- ── Tab: Job Details ─────────────────────────────────────────────────── -->
	{#if activeTab === 'details'}
		<form on:submit|preventDefault={handleSubmit} novalidate>
			<div class="form-section">
				<h2>Basic Info</h2>

				<div class="field">
					<label for="title">Job Title <span class="required">*</span></label>
					<input
						id="title"
						type="text"
						bind:value={title}
						placeholder="e.g. Senior Backend Engineer"
						disabled={isLoading}
						class:invalid={detailsErrors['title']}
					/>
					{#if detailsErrors['title']}
						<span class="field-error">{detailsErrors['title']}</span>
					{/if}
				</div>

				<div class="field-row">
					<div class="field">
						<label for="employmentType">Employment Type <span class="required">*</span></label>
						<select id="employmentType" bind:value={employmentType} disabled={isLoading}>
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
							disabled={isLoading}
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
							disabled={isLoading}
							class:invalid={detailsErrors['salaryMin']}
						/>
						{#if detailsErrors['salaryMin']}
							<span class="field-error">{detailsErrors['salaryMin']}</span>
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
							disabled={isLoading}
							class:invalid={detailsErrors['salaryMax']}
						/>
						{#if detailsErrors['salaryMax']}
							<span class="field-error">{detailsErrors['salaryMax']}</span>
						{/if}
					</div>
				</div>
				<span class="field-hint salary-hint">Annual salary in whole currency units. Leave both blank to not disclose.</span>

				<div class="field field-checkbox">
					<label>
						<input type="checkbox" bind:checked={isRemote} disabled={isLoading} />
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
							disabled={isLoading}
						/>
						<span class="field-hint">Separate tags with commas. New tags are created automatically.</span>
					</div>

					<div class="field">
						<label for="expiresAt">Expiry Date</label>
						<input
							id="expiresAt"
							type="date"
							bind:value={expiresAt}
							disabled={isLoading}
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
						disabled={isLoading}
						invalid={!!detailsErrors['description']}
					/>
					{#if detailsErrors['description']}
						<span class="field-error">{detailsErrors['description']}</span>
					{/if}
				</div>
			</div>

			<div class="form-section">
				<h2>Application Settings</h2>

				<div class="field">
					<span class="field-label">How should candidates apply?</span>
					<div class="radio-group">
						<label class="radio-label">
							<input
								type="radio"
								bind:group={applicationMode}
								value="form"
								disabled={isLoading}
								on:change={onApplicationModeChange}
							/>
							<div>
								<strong>Built-in form</strong>
								<p>Candidates apply directly on this site. Configure the form fields in the "Application Form" tab.</p>
							</div>
						</label>
						<label class="radio-label">
							<input
								type="radio"
								bind:group={applicationMode}
								value="external_url"
								disabled={isLoading}
								on:change={onApplicationModeChange}
							/>
							<div>
								<strong>External URL</strong>
								<p>Redirect candidates to an external application page (e.g. Greenhouse, Lever, your own site).</p>
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
							disabled={isLoading}
							class:invalid={detailsErrors['externalApplyUrl']}
						/>
						{#if detailsErrors['externalApplyUrl']}
							<span class="field-error">{detailsErrors['externalApplyUrl']}</span>
						{/if}
					</div>
				{/if}

				{#if applicationMode === 'form'}
					<p class="form-tab-cta">
						Set up the questions candidates will answer in the
						<button type="button" class="link-btn" on:click={() => (activeTab = 'form')}>
							Application Form tab →
						</button>
					</p>
				{/if}
			</div>
		</form>
	{/if}

	<!-- ── Tab: Application Form ────────────────────────────────────────────── -->
	{#if activeTab === 'form'}
		<div class="form-section">
			<div class="form-builder-header">
				<div>
					<h2>Application Form Fields</h2>
					<p class="section-desc">These are the questions candidates will fill out when applying. At least one field is required.</p>
				</div>
				<span class="field-count">{fields.length} / 20 fields</span>
			</div>

			{#if formTabError}
				<div class="alert alert-error" role="alert">{formTabError}</div>
			{/if}

			<!-- Matrix table -->
			<div class="matrix-wrap">
				<table class="matrix">
					<thead>
						<tr>
							<th class="col-order">Order</th>
							<th class="col-label">Question label <span class="required">*</span></th>
							<th class="col-type">Input type <span class="required">*</span></th>
							<th class="col-req">Required</th>
							<th class="col-options">Options <span class="hint">(for radio / dropdown / checkboxes)</span></th>
							<th class="col-actions">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each fields as f, i (f._key)}
							<tr class:has-error={formFieldErrors[i] && Object.keys(formFieldErrors[i]).length > 0}>
								<td class="col-order">
									<div class="order-btns">
										<button
											type="button"
											class="icon-btn"
											disabled={i === 0}
											on:click={() => moveUp(i)}
											title="Move up"
										>↑</button>
										<span class="order-num">{i + 1}</span>
										<button
											type="button"
											class="icon-btn"
											disabled={i === fields.length - 1}
											on:click={() => moveDown(i)}
											title="Move down"
										>↓</button>
									</div>
								</td>

								<td class="col-label">
									<input
										type="text"
										bind:value={f.label}
										placeholder="e.g. Years of experience"
										maxlength="200"
										class:invalid={formFieldErrors[i]?.label}
									/>
									{#if formFieldErrors[i]?.label}
										<span class="field-error">{formFieldErrors[i].label}</span>
									{/if}
								</td>

								<td class="col-type">
									<select bind:value={f.field_type} on:change={() => onTypeChange(f)}>
										{#each FIELD_TYPES as ft}
											<option value={ft.value}>{ft.label}</option>
										{/each}
									</select>
								</td>

								<td class="col-req">
									<label class="checkbox-label">
										<input type="checkbox" bind:checked={f.is_required} />
										<span class="sr-only">Required</span>
									</label>
								</td>

								<td class="col-options">
									{#if needsOptions(f.field_type)}
										<textarea
											bind:value={f.optionsRaw}
											on:blur={() => syncOptions(f)}
											placeholder="Option A, Option B, Option C"
											rows="2"
											class:invalid={formFieldErrors[i]?.options}
										></textarea>
										<span class="field-hint">Comma-separated. Max 20, each ≤ 100 chars.</span>
										{#if formFieldErrors[i]?.options}
											<span class="field-error">{formFieldErrors[i].options}</span>
										{/if}
									{:else}
										<span class="na">—</span>
									{/if}
								</td>

								<td class="col-actions">
									<button
										type="button"
										class="remove-btn"
										on:click={() => removeField(f._key)}
										title="Remove field"
									>Remove</button>
								</td>
							</tr>
						{/each}

						{#if fields.length === 0}
							<tr>
								<td colspan="6" class="empty-row">
									No fields yet. Click "Add field" to start building the form.
								</td>
							</tr>
						{/if}
					</tbody>
				</table>
			</div>

			<div class="toolbar">
				<button
					type="button"
					class="btn-secondary"
					on:click={addField}
					disabled={fields.length >= 20}
				>
					+ Add field
					{#if fields.length >= 20}
						<span class="limit-note">(max 20)</span>
					{/if}
				</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.page {
		width: 100%;
	}

	.back-link {
		font-size: 0.875rem;
		color: var(--color-text-muted);
		text-decoration: none;
		display: block;
		margin-bottom: 0.25rem;
	}

	.back-link:hover {
		color: var(--color-primary);
	}

	h1 {
		margin: 0;
	}

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

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

	/* ── Tab bar ── */
	.tab-bar {
		display: flex;
		gap: 0;
		border-bottom: 2px solid var(--color-border);
		margin-bottom: 1.25rem;
	}

	.tab {
		position: relative;
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.6rem 1.25rem;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
		font-size: 0.9rem;
		font-weight: 500;
		color: var(--color-text-muted);
		cursor: pointer;
		transition: color 0.15s, border-color 0.15s;
		white-space: nowrap;
	}

	.tab:hover:not(:disabled) {
		color: var(--color-text);
	}

	.tab.active {
		color: var(--color-primary);
		border-bottom-color: var(--color-primary);
	}

	.tab:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}

	.tab-note {
		font-size: 0.75rem;
		font-weight: 400;
		color: var(--color-text-muted);
	}

	.error-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--color-danger);
		flex-shrink: 0;
	}

	/* ── Form sections ── */
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

	.field:last-child {
		margin-bottom: 0;
	}

	.field-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.field-row .field {
		margin-bottom: 0;
	}

	.field-checkbox {
		flex-direction: row;
		align-items: center;
	}

	.field-checkbox label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		font-weight: normal;
	}

	label, .field-label {
		font-size: 0.875rem;
		font-weight: 500;
	}

	.required {
		color: var(--color-danger);
	}

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

	input:focus,
	select:focus {
		border-color: var(--color-primary);
	}

	input.invalid {
		border-color: var(--color-danger);
	}

	input:disabled,
	select:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.field-error {
		font-size: 0.8rem;
		color: var(--color-danger);
	}

	.field-hint {
		font-size: 0.8rem;
		color: var(--color-text-muted);
	}

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

	.radio-label input {
		margin-top: 0.2rem;
		flex-shrink: 0;
	}

	.radio-label strong {
		display: block;
		font-size: 0.9rem;
	}

	.radio-label p {
		margin: 0.15rem 0 0;
		font-size: 0.8rem;
		color: var(--color-text-muted);
	}

	.form-tab-cta {
		margin: 0.75rem 0 0;
		font-size: 0.875rem;
		color: var(--color-text-muted);
	}

	.link-btn {
		background: none;
		border: none;
		padding: 0;
		color: var(--color-primary);
		font-size: inherit;
		cursor: pointer;
		text-decoration: underline;
	}

	.link-btn:hover {
		color: var(--color-primary-hover);
	}

	/* ── Form builder ── */
	.form-builder-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 1.25rem;
	}

	.form-builder-header h2 {
		margin: 0 0 0.25rem;
	}

	.section-desc {
		margin: 0;
		font-size: 0.85rem;
		color: var(--color-text-muted);
	}

	.field-count {
		font-size: 0.8rem;
		color: var(--color-text-muted);
		white-space: nowrap;
		padding-top: 0.2rem;
	}

	.matrix-wrap {
		overflow-x: auto;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		margin-bottom: 1rem;
	}

	.matrix {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	.matrix thead th {
		background: var(--color-surface);
		padding: 0.6rem 0.75rem;
		text-align: left;
		font-weight: 600;
		font-size: 0.8rem;
		border-bottom: 1px solid var(--color-border);
		white-space: nowrap;
	}

	.matrix tbody tr {
		border-bottom: 1px solid var(--color-border);
	}

	.matrix tbody tr:last-child {
		border-bottom: none;
	}

	.matrix tbody tr.has-error {
		background: #fff8f8;
	}

	.matrix td {
		padding: 0.5rem 0.75rem;
		vertical-align: top;
	}

	.col-order   { width: 70px; }
	.col-label   { width: 26%; }
	.col-type    { width: 18%; }
	.col-req     { width: 70px; text-align: center; }
	.col-options { width: 30%; }
	.col-actions { width: 90px; }

	.order-btns {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.15rem;
	}

	.order-num {
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	.icon-btn {
		background: none;
		border: 1px solid var(--color-border);
		border-radius: 4px;
		padding: 0.1rem 0.35rem;
		font-size: 0.75rem;
		cursor: pointer;
		color: var(--color-text);
		line-height: 1.4;
	}

	.icon-btn:hover:not(:disabled) {
		background: var(--color-bg);
	}

	.icon-btn:disabled {
		opacity: 0.3;
		cursor: default;
	}

	.matrix input[type='text'],
	.matrix select,
	.matrix textarea {
		width: 100%;
		padding: 0.4rem 0.5rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		font-size: 0.875rem;
		font-family: inherit;
		outline: none;
		background: white;
		transition: border-color 0.15s;
	}

	.matrix input[type='text']:focus,
	.matrix select:focus,
	.matrix textarea:focus {
		border-color: var(--color-primary);
	}

	.matrix input[type='text'].invalid,
	.matrix textarea.invalid {
		border-color: var(--color-danger);
	}

	.matrix textarea {
		resize: vertical;
		min-height: 54px;
		line-height: 1.4;
	}

	.checkbox-label {
		display: flex;
		justify-content: center;
		align-items: center;
		padding-top: 0.3rem;
		cursor: pointer;
	}

	.checkbox-label input {
		width: 16px;
		height: 16px;
		cursor: pointer;
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
	}

	.na {
		color: var(--color-text-muted);
		font-size: 0.8rem;
	}

	.remove-btn {
		padding: 0.3rem 0.6rem;
		background: none;
		border: 1px solid var(--color-danger);
		border-radius: var(--radius);
		color: var(--color-danger);
		font-size: 0.8rem;
		cursor: pointer;
		white-space: nowrap;
		transition: background 0.15s;
	}

	.remove-btn:hover {
		background: #fff5f5;
	}

	.empty-row {
		text-align: center;
		padding: 2rem;
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}

	.toolbar {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.limit-note {
		font-size: 0.75rem;
		opacity: 0.7;
	}

	.hint {
		font-weight: normal;
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	/* ── Buttons ── */
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

	.btn-primary:hover:not(:disabled) {
		background: var(--color-primary-hover);
	}

	.btn-primary:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.btn-secondary {
		padding: 0.5rem 1rem;
		background: var(--color-surface);
		color: var(--color-text);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		font-size: 0.9rem;
		cursor: pointer;
		transition: border-color 0.15s;
	}

	.btn-secondary:hover:not(:disabled) {
		border-color: var(--color-text-muted);
	}

	.btn-secondary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	@media (max-width: 600px) {
		.field-row {
			grid-template-columns: 1fr;
		}
	}
</style>
