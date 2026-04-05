<script lang="ts">
	import { onMount } from 'svelte';
	import { listAdminJobs, toggleJob, deleteJob } from '$lib/api/jobs';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { JobListItem, PaginatedJobs } from '$lib/api/types';

	const log = createLogger('JobsPage');

	const EMPLOYMENT_LABELS: Record<string, string> = {
		full_time: 'Full-time',
		part_time: 'Part-time',
		contract: 'Contract',
		internship: 'Internship',
	};

	let data: PaginatedJobs | null = null;
	let errorMessage = '';
	let isLoading = true;
	let currentPage = 1;
	let actionLoadingId: string | null = null; // tracks which job has an in-progress action
	let confirmDeleteId: string | null = null;  // job pending delete confirmation

	async function load(page = 1) {
		isLoading = true;
		errorMessage = '';
		try {
			data = await listAdminJobs({ page, per_page: 20 });
			currentPage = page;
			log.info('jobs.loaded', { page, total: data.total });
		} catch (err) {
			if (err instanceof ApiError) {
				errorMessage = 'Failed to load jobs. Please try again.';
			} else {
				errorMessage = 'An unexpected error occurred.';
			}
			log.error('jobs.load_failed', { error: String(err) });
		} finally {
			isLoading = false;
		}
	}

	async function handleToggle(job: JobListItem) {
		actionLoadingId = job.public_id;
		try {
			const updated = await toggleJob(job.public_id);
			if (data) {
				data = {
					...data,
					items: data.items.map((j) =>
						j.public_id === job.public_id ? { ...j, is_active: updated.is_active } : j,
					),
				};
			}
			log.info('job.toggled', { public_id: job.public_id, is_active: updated.is_active });
		} catch (err) {
			errorMessage = 'Failed to update job status. Please try again.';
			log.error('job.toggle_failed', { public_id: job.public_id, error: String(err) });
		} finally {
			actionLoadingId = null;
		}
	}

	async function handleDelete(publicId: string) {
		confirmDeleteId = null;
		actionLoadingId = publicId;
		try {
			await deleteJob(publicId);
			if (data) {
				data = {
					...data,
					items: data.items.map((j) =>
						j.public_id === publicId ? { ...j, is_deleted: true, is_active: false } : j,
					),
					total: data.total,
				};
			}
			log.info('job.deleted', { public_id: publicId });
		} catch (err) {
			errorMessage = 'Failed to delete job. Please try again.';
			log.error('job.delete_failed', { public_id: publicId, error: String(err) });
		} finally {
			actionLoadingId = null;
		}
	}

	onMount(() => load());
</script>

<svelte:head>
	<title>Jobs — Admin</title>
</svelte:head>

<div class="page">
	<div class="page-header">
		<h1>Jobs</h1>
		<a href="/jobs/new" class="btn-primary">+ New Job</a>
	</div>

	{#if errorMessage}
		<div class="alert alert-error" role="alert">{errorMessage}</div>
	{/if}

	{#if isLoading}
		<p class="loading">Loading…</p>
	{:else if data && data.items.length === 0}
		<div class="empty">
			<p>No jobs yet.</p>
			<a href="/jobs/new" class="btn-primary">Post your first job</a>
		</div>
	{:else if data}
		<div class="table-meta">
			Showing {data.items.length} of {data.total} jobs
		</div>

		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						<th>Title</th>
						<th>Type</th>
						<th>Location</th>
						<th>Tags</th>
						<th>Status</th>
						<th>Posted</th>
						<th>Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each data.items as job (job.public_id)}
						<tr class:row-deleted={job.is_deleted}>
							<td>
								<a href="/jobs/{job.public_id}" class="job-title">{job.title}</a>
							</td>
							<td>{EMPLOYMENT_LABELS[job.employment_type] ?? job.employment_type}</td>
							<td>
								{#if job.is_remote && !job.location}
									<span class="badge badge-remote">Remote</span>
								{:else if job.is_remote}
									{job.location} · <span class="badge badge-remote">Remote</span>
								{:else}
									{job.location ?? '—'}
								{/if}
							</td>
							<td>
								<div class="tags">
									{#each job.tags.slice(0, 3) as tag}
										<span class="badge">{tag.name}</span>
									{/each}
									{#if job.tags.length > 3}
										<span class="badge">+{job.tags.length - 3}</span>
									{/if}
								</div>
							</td>
							<td>
								{#if job.is_deleted}
									<span class="badge badge-deleted">Deleted</span>
								{:else if !job.is_active}
									<span class="badge badge-inactive">Inactive</span>
								{:else}
									<span class="badge badge-active">Active</span>
								{/if}
							</td>
							<td class="date">{new Date(job.created_at).toLocaleDateString()}</td>
							<td class="actions-cell">
								{#if !job.is_deleted}
									<button
										class="action-btn"
										disabled={actionLoadingId === job.public_id}
										on:click={() => handleToggle(job)}
										title={job.is_active ? 'Deactivate job' : 'Activate job'}
									>
										{job.is_active ? 'Deactivate' : 'Activate'}
									</button>

									{#if confirmDeleteId === job.public_id}
										<span class="confirm-row">
											<span class="confirm-text">Sure?</span>
											<button
												class="action-btn action-btn-danger"
												disabled={actionLoadingId === job.public_id}
												on:click={() => handleDelete(job.public_id)}
											>
												Yes, delete
											</button>
											<button
												class="action-btn"
												on:click={() => (confirmDeleteId = null)}
											>
												Cancel
											</button>
										</span>
									{:else}
										<button
											class="action-btn action-btn-danger"
											disabled={actionLoadingId === job.public_id}
											on:click={() => (confirmDeleteId = job.public_id)}
											title="Delete job"
										>
											Delete
										</button>
									{/if}
								{/if}
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
		max-width: 1100px;
	}

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1.5rem;
	}

	h1 {
		margin: 0;
	}

	.btn-primary {
		display: inline-block;
		padding: 0.5rem 1rem;
		background: var(--color-primary);
		color: white;
		border-radius: var(--radius);
		text-decoration: none;
		font-size: 0.9rem;
		font-weight: 500;
		transition: background 0.15s;
	}

	.btn-primary:hover {
		background: var(--color-primary-hover);
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
		text-align: center;
		padding: 3rem 1rem;
		color: var(--color-text-muted);
	}

	.empty p {
		margin-bottom: 1rem;
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

	.row-deleted td {
		opacity: 0.5;
	}

	.job-title {
		color: var(--color-text);
		font-weight: 500;
		text-decoration: none;
	}

	.job-title:hover {
		color: var(--color-primary);
	}

	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
	}

	.badge {
		display: inline-block;
		padding: 0.15rem 0.5rem;
		background: var(--color-bg);
		border: 1px solid var(--color-border);
		border-radius: 999px;
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	.badge-active {
		background: #f0fff4;
		border-color: #9ae6b4;
		color: var(--color-success);
	}

	.badge-inactive {
		background: #fffff0;
		border-color: #faf089;
		color: #b7791f;
	}

	.badge-deleted {
		background: #fff5f5;
		border-color: #feb2b2;
		color: var(--color-danger);
	}

	.badge-remote {
		background: #ebf8ff;
		border-color: #90cdf4;
		color: #2b6cb0;
	}

	.date {
		white-space: nowrap;
		color: var(--color-text-muted);
	}

	.actions-cell {
		white-space: nowrap;
	}

	.action-btn {
		padding: 0.3rem 0.6rem;
		font-size: 0.8rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		background: var(--color-surface);
		color: var(--color-text);
		cursor: pointer;
		transition: border-color 0.15s;
		margin-right: 0.35rem;
	}

	.action-btn:hover:not(:disabled) {
		border-color: var(--color-text-muted);
	}

	.action-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.action-btn-danger {
		color: var(--color-danger);
		border-color: #feb2b2;
	}

	.action-btn-danger:hover:not(:disabled) {
		background: #fff5f5;
		border-color: var(--color-danger);
	}

	.confirm-row {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
	}

	.confirm-text {
		font-size: 0.8rem;
		color: var(--color-danger);
		font-weight: 500;
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
