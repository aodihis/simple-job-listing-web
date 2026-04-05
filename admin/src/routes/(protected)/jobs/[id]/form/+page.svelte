<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getAdminJob } from '$lib/api/jobs';
	import { getFormFields, saveFormFields } from '$lib/api/formFields';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { FormFieldRead, FieldType } from '$lib/api/types';
	import { OPTION_FIELD_TYPES } from '$lib/api/types';

	const log = createLogger('FormBuilderPage');

	// ── State ─────────────────────────────────────────────────────────────────

	$: jobId = $page.params.id;

	let jobTitle = '';
	let isLoading = true;
	let isSaving = false;
	let loadError = '';
	let saveError = '';
	let saveSuccess = false;

	// Working copy — each entry mirrors FormFieldCreate + a local key for Svelte keyed lists
	interface DraftField {
		_key: number;
		label: string;
		field_type: FieldType;
		is_required: boolean;
		options: string[]; // only for radio/select/checkbox
		optionsRaw: string; // textarea-bound comma-separated string
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

	// ── Load ──────────────────────────────────────────────────────────────────

	onMount(async () => {
		try {
			const [job, existing] = await Promise.all([
				getAdminJob(jobId),
				getFormFields(jobId),
			]);
			jobTitle = job.title;
			fields = existing.map(serverToDraft);
			log.info('form_fields.loaded', { job_id: jobId, count: existing.length });
		} catch (err) {
			loadError = 'Failed to load form fields. Please refresh.';
			log.error('form_fields.load_failed', { job_id: jobId, error: String(err) });
		} finally {
			isLoading = false;
		}
	});

	// ── Helpers ───────────────────────────────────────────────────────────────

	function serverToDraft(f: FormFieldRead): DraftField {
		return {
			_key: nextKey++,
			label: f.label,
			field_type: f.field_type as FieldType,
			is_required: f.is_required,
			options: f.options,
			optionsRaw: f.options.join(', '),
		};
	}

	function blankField(): DraftField {
		return {
			_key: nextKey++,
			label: '',
			field_type: 'text',
			is_required: false,
			options: [],
			optionsRaw: '',
		};
	}

	function needsOptions(type: FieldType): boolean {
		return OPTION_FIELD_TYPES.includes(type);
	}

	/** Parse optionsRaw into the options array, trimming and deduplicating. */
	function syncOptions(f: DraftField): void {
		f.options = [...new Set(
			f.optionsRaw.split(',').map((s) => s.trim()).filter(Boolean)
		)];
	}

	// ── Field manipulation ────────────────────────────────────────────────────

	function addField() {
		fields = [...fields, blankField()];
	}

	function removeField(key: number) {
		fields = fields.filter((f) => f._key !== key);
	}

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
		if (!needsOptions(f.field_type)) {
			f.optionsRaw = '';
			f.options = [];
		}
		fields = fields; // trigger reactivity
	}

	// ── Validation ────────────────────────────────────────────────────────────

	interface FieldError {
		label?: string;
		options?: string;
	}

	let fieldErrors: FieldError[] = [];

	function validate(): boolean {
		fieldErrors = fields.map((f) => {
			const e: FieldError = {};
			if (!f.label.trim()) e.label = 'Label is required.';
			if (needsOptions(f.field_type)) {
				syncOptions(f);
				if (f.options.length === 0) e.options = 'At least one option is required.';
				else if (f.options.length > 20) e.options = 'Maximum 20 options.';
				else if (f.options.some((o) => o.length > 100))
					e.options = 'Each option must be 100 characters or fewer.';
			}
			return e;
		});
		return fieldErrors.every((e) => Object.keys(e).length === 0);
	}

	// ── Save ──────────────────────────────────────────────────────────────────

	async function handleSave() {
		saveError = '';
		saveSuccess = false;

		// Sync all options before validating
		fields.forEach((f) => {
			if (needsOptions(f.field_type)) syncOptions(f);
		});

		if (!validate()) return;

		if (fields.length > 20) {
			saveError = 'Maximum 20 fields allowed.';
			return;
		}

		isSaving = true;
		try {
			const saved = await saveFormFields(jobId, {
				fields: fields.map((f) => ({
					label: f.label.trim(),
					field_type: f.field_type,
					is_required: f.is_required,
					options: f.options,
				})),
			});
			// Re-sync from server response to get IDs
			fields = saved.map(serverToDraft);
			saveSuccess = true;
			log.info('form_fields.saved', { job_id: jobId, count: saved.length });
		} catch (err) {
			if (err instanceof ApiError) {
				saveError = err.detail ?? 'Failed to save. Please try again.';
			} else {
				saveError = 'An unexpected error occurred.';
			}
			log.error('form_fields.save_failed', { job_id: jobId, error: String(err) });
		} finally {
			isSaving = false;
		}
	}
</script>

<svelte:head>
	<title>Form Builder — {jobTitle || 'Job'} — Admin</title>
</svelte:head>

<div class="page">
	<div class="page-header">
		<div>
			<a href="/jobs" class="back-link">← Back to Jobs</a>
			<h1>Application Form</h1>
			{#if jobTitle}
				<p class="subtitle">Editing form for: <strong>{jobTitle}</strong></p>
			{/if}
		</div>
	</div>

	{#if isLoading}
		<p class="loading">Loading…</p>
	{:else if loadError}
		<div class="alert alert-error" role="alert">{loadError}</div>
	{:else}
		{#if saveError}
			<div class="alert alert-error" role="alert">{saveError}</div>
		{/if}
		{#if saveSuccess}
			<div class="alert alert-success" role="status">Form saved successfully.</div>
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
						<tr class:has-error={fieldErrors[i] && Object.keys(fieldErrors[i]).length > 0}>
							<!-- Order controls -->
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

							<!-- Label -->
							<td class="col-label">
								<input
									type="text"
									bind:value={f.label}
									placeholder="e.g. Years of experience"
									maxlength="200"
									class:invalid={fieldErrors[i]?.label}
								/>
								{#if fieldErrors[i]?.label}
									<span class="field-error">{fieldErrors[i].label}</span>
								{/if}
							</td>

							<!-- Type -->
							<td class="col-type">
								<select
									bind:value={f.field_type}
									on:change={() => onTypeChange(f)}
								>
									{#each FIELD_TYPES as ft}
										<option value={ft.value}>{ft.label}</option>
									{/each}
								</select>
							</td>

							<!-- Required -->
							<td class="col-req">
								<label class="checkbox-label">
									<input type="checkbox" bind:checked={f.is_required} />
									<span class="sr-only">Required</span>
								</label>
							</td>

							<!-- Options (only active for radio/select/checkbox) -->
							<td class="col-options">
								{#if needsOptions(f.field_type)}
									<textarea
										bind:value={f.optionsRaw}
										on:blur={() => syncOptions(f)}
										placeholder="Option A, Option B, Option C"
										rows="2"
										class:invalid={fieldErrors[i]?.options}
									></textarea>
									<span class="field-hint">Comma-separated. Max 20, each ≤ 100 chars.</span>
									{#if fieldErrors[i]?.options}
										<span class="field-error">{fieldErrors[i].options}</span>
									{/if}
								{:else}
									<span class="na">—</span>
								{/if}
							</td>

							<!-- Remove -->
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

			<span class="field-count">{fields.length} / 20 fields</span>

			<button
				type="button"
				class="btn-primary"
				on:click={handleSave}
				disabled={isSaving}
			>
				{isSaving ? 'Saving…' : 'Save form'}
			</button>
		</div>
	{/if}
</div>

<style>
	.page {
		max-width: 1000px;
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

	.subtitle {
		margin: 0.25rem 0 0;
		font-size: 0.9rem;
		color: var(--color-text-muted);
	}

	.page-header {
		margin-bottom: 1.5rem;
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

	.alert-success {
		background: #f0fff4;
		border: 1px solid #9ae6b4;
		color: #276749;
	}

	/* Matrix table */
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

	/* Column widths */
	.col-order { width: 70px; }
	.col-label { width: 26%; }
	.col-type  { width: 18%; }
	.col-req   { width: 70px; text-align: center; }
	.col-options { width: 30%; }
	.col-actions { width: 90px; }

	/* Order column */
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

	/* Inputs */
	input[type='text'],
	select,
	textarea {
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

	input[type='text']:focus,
	select:focus,
	textarea:focus {
		border-color: var(--color-primary);
	}

	input[type='text'].invalid,
	textarea.invalid {
		border-color: var(--color-danger);
	}

	textarea {
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

	.field-error {
		display: block;
		font-size: 0.75rem;
		color: var(--color-danger);
		margin-top: 0.2rem;
	}

	.field-hint {
		display: block;
		font-size: 0.75rem;
		color: var(--color-text-muted);
		margin-top: 0.2rem;
	}

	.na {
		color: var(--color-text-muted);
		font-size: 0.8rem;
	}

	/* Remove button */
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

	/* Empty state */
	.empty-row {
		text-align: center;
		padding: 2rem;
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}

	/* Toolbar */
	.toolbar {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.field-count {
		font-size: 0.8rem;
		color: var(--color-text-muted);
		margin-right: auto;
	}

	.limit-note {
		font-size: 0.75rem;
		opacity: 0.7;
	}

	.btn-primary {
		padding: 0.5rem 1.25rem;
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius);
		font-size: 0.9rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
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

	.required {
		color: var(--color-danger);
	}

	.hint {
		font-weight: normal;
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	.loading {
		color: var(--color-text-muted);
	}
</style>
