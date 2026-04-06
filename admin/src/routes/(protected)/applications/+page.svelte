<script lang="ts">
	import { onMount } from 'svelte';
	import { listApplications } from '$lib/api/applications';
	import { listAdminJobs } from '$lib/api/jobs';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { ApplicationRead, ApplicationStatus, PaginatedApplications, JobListItem } from '$lib/api/types';

	const log = createLogger('ApplicationsPage');

	const STATUS_LABELS: Record<ApplicationStatus, string> = {
		new: 'New',
		reviewed: 'Reviewed',
		rejected: 'Rejected',
		hired: 'Hired',
	};

	const STATUS_OPTIONS: { value: string; label: string }[] = [
		{ value: '', label: 'All statuses' },
		{ value: 'new', label: 'New' },
		{ value: 'reviewed', label: 'Reviewed' },
		{ value: 'rejected', label: 'Rejected' },
		{ value: 'hired', label: 'Hired' },
	];

	let data: PaginatedApplications | null = null;
	let jobs: JobListItem[] = [];
	let errorMessage = '';
	let isLoading = true;
	let currentPage = 1;

	// Filters
	let filterJobId = '';
	let filterStatus = '';

	async function loadJobs() {
		try {
			const resp = await listAdminJobs({ page: 1, per_page: 100 });
			jobs = resp.items;
		} catch {
			// non-critical — just means the job filter dropdown will be empty
		}
	}

	async function load(page = 1) {
		isLoading = true;
		errorMessage = '';
		try {
			data = await listApplications({
				job_id: filterJobId || undefined,
				status: (filterStatus as ApplicationStatus) || undefined,
				page,
				per_page: 20,
			});
			currentPage = page;
			log.info('applications.loaded', { page, total: data.total });
		} catch (err) {
			if (err instanceof ApiError) {
				errorMessage = 'Failed to load applications. Please try again.';
			} else {
				errorMessage = 'An unexpected error occurred.';
			}
			log.error('applications.load_failed', { error: String(err) });
		} finally {
			isLoading = false;
		}
	}

	function applyFilters() {
		load(1);
	}

	function clearFilters() {
		filterJobId = '';
		filterStatus = '';
		load(1);
	}

	onMount(() => {
		loadJobs();
		load();
	});
</script>

<svelte:head>
	<title>Applications — Admin</title>
</svelte:head>

<div class="page">
	<div class="page-header">
		<h1>Applications</h1>
	</div>

	<!-- Filters -->
	<div class="filters">
		<div class="filter-group">
			<label for="filter-job" class="filter-label">Job</label>
			<select id="filter-job" class="filter-select" bind:value={filterJobId}>
				<option value="">All jobs</option>
				{#each jobs as job (job.public_id)}
					<option value={job.public_id}>{job.title}</option>
				{/each}
			</select>
		</div>

		<div class="filter-group">
			<label for="filter-status" class="filter-label">Status</label>
			<select id="filter-status" class="filter-select" bind:value={filterStatus}>
				{#each STATUS_OPTIONS as opt}
					<option value={opt.value}>{opt.label}</option>
				{/each}
			</select>
		</div>

		<div class="filter-actions">
			<button class="btn-filter" on:click={applyFilters}>Apply</button>
			{#if filterJobId || filterStatus}
				<button class="btn-clear" on:click={clearFilters}>Clear</button>
			{/if}
		</div>
	</div>

	{#if errorMessage}
		<div class="alert alert-error" role="alert">{errorMessage}</div>
	{/if}

	{#if isLoading}
		<p class="loading">Loading…</p>
	{:else if data && data.items.length === 0}
		<div class="empty">
			<p>No applications found.</p>
		</div>
	{:else if data}
		<div class="table-meta">
			Showing {data.items.length} of {data.total} applications
		</div>

		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						<th>Applicant</th>
						<th>Email</th>
						<th>Job</th>
						<th>Status</th>
						<th>Submitted</th>
						<th>Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each data.items as app (app.public_id)}
						<tr>
							<td class="name-cell">{app.applicant_name}</td>
							<td class="email-cell">{app.applicant_email}</td>
							<td class="job-cell">
								<a href="/jobs/{app.job_public_id}" class="job-link">{app.job_title}</a>
							</td>
							<td>
								<span class="badge badge-{app.status}">{STATUS_LABELS[app.status]}</span>
							</td>
							<td class="date">{new Date(app.created_at).toLocaleDateString()}</td>
							<td>
								<a href="/applications/{app.public_id}" class="action-btn">View</a>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		{#if data.pages > 1}
			<div class="pagination">
				<button disabled={currentPage <= 1} on:click={() => load(currentPage - 1)}>
					Previous
				</button>
				<span>Page {currentPage} of {data.pages}</span>
				<button disabled={currentPage >= data.pages} on:click={() => load(currentPage + 1)}>
					Next
				</button>
			</div>
		{/if}
	{/if}
</div>

<style>
	.page {
		max-width: 1000px;
	}

	.page-header {
		margin-bottom: 1.25rem;
	}

	h1 {
		margin: 0;
	}

	.filters {
		display: flex;
		align-items: flex-end;
		gap: 1rem;
		margin-bottom: 1.25rem;
		flex-wrap: wrap;
	}

	.filter-group {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.filter-label {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.filter-select {
		padding: 0.4rem 0.6rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		background: var(--color-surface);
		font-size: 0.875rem;
		color: var(--color-text);
		min-width: 160px;
	}

	.filter-actions {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		padding-top: 1.1rem;
	}

	.btn-filter {
		padding: 0.4rem 0.9rem;
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
	}

	.btn-filter:hover {
		background: var(--color-primary-hover);
	}

	.btn-clear {
		padding: 0.4rem 0.75rem;
		background: none;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		font-size: 0.875rem;
		color: var(--color-text-muted);
		cursor: pointer;
	}

	.btn-clear:hover {
		border-color: var(--color-text-muted);
		color: var(--color-text);
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

	.empty {
		padding: 3rem 1rem;
		text-align: center;
		color: var(--color-text-muted);
	}

	.table-meta {
		font-size: 0.875rem;
		color: var(--color-text-muted);
		margin-bottom: 0.75rem;
	}

	.table-wrap {
		overflow-x: auto;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.9rem;
	}

	th {
		background: var(--color-bg);
		padding: 0.6rem 0.75rem;
		text-align: left;
		font-weight: 600;
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		color: var(--color-text-muted);
		border-bottom: 1px solid var(--color-border);
	}

	td {
		padding: 0.6rem 0.75rem;
		border-bottom: 1px solid var(--color-border);
		vertical-align: middle;
	}

	tr:last-child td {
		border-bottom: none;
	}

	tr:hover td {
		background: var(--color-bg);
	}

	.name-cell {
		font-weight: 500;
	}

	.email-cell {
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}

	.job-link {
		color: var(--color-text);
		text-decoration: none;
		font-size: 0.875rem;
	}

	.job-link:hover {
		color: var(--color-primary);
	}

	.date {
		white-space: nowrap;
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}

	.badge {
		display: inline-block;
		padding: 0.2rem 0.55rem;
		border-radius: 999px;
		font-size: 0.75rem;
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

	.action-btn {
		padding: 0.3rem 0.6rem;
		font-size: 0.8rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		background: var(--color-surface);
		color: var(--color-text);
		text-decoration: none;
		display: inline-block;
		transition: border-color 0.15s;
	}

	.action-btn:hover {
		border-color: var(--color-text-muted);
	}

	.pagination {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-top: 1rem;
		font-size: 0.875rem;
	}

	.pagination button {
		padding: 0.4rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		background: var(--color-surface);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.pagination button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
