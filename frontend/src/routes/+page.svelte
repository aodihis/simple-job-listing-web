<script lang="ts">
	import { onMount } from 'svelte';
	import { listJobs } from '$lib/api/jobs';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { PaginatedJobs } from '$lib/api/types';

	const log = createLogger('JobListingPage');

	const EMPLOYMENT_LABELS: Record<string, string> = {
		full_time: 'Full-time',
		part_time: 'Part-time',
		contract: 'Contract',
		internship: 'Internship',
	};

	const EMPLOYMENT_TYPES = [
		{ value: '', label: 'All types' },
		{ value: 'full_time', label: 'Full-time' },
		{ value: 'part_time', label: 'Part-time' },
		{ value: 'contract', label: 'Contract' },
		{ value: 'internship', label: 'Internship' },
	];

	// Filter + sort state
	let searchQuery = '';
	let pendingSearch = ''; // typed but not yet submitted
	let selectedType = '';
	let remoteOnly = false;
	let sort: 'newest' | 'oldest' = 'newest';
	let currentPage = 1;
	let selectedTags: string[] = [];
	let pendingTag = '';

	// Data state
	let data: PaginatedJobs | null = null;
	let isLoading = true;
	let errorMessage = '';

	// Debounce timer for search
	let searchTimer: ReturnType<typeof setTimeout>;

	async function load(page = 1) {
		isLoading = true;
		errorMessage = '';
		try {
			data = await listJobs({
				q: searchQuery || undefined,
				tags: selectedTags.length ? selectedTags : undefined,
				employment_type: selectedType || undefined,
				is_remote: remoteOnly || undefined,
				sort,
				page,
				per_page: 12,
			});
			currentPage = page;
			log.info('jobs.loaded', { page, total: data.total, q: searchQuery });
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

	function applyFilters() {
		searchQuery = pendingSearch;
		load(1);
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			clearTimeout(searchTimer);
			applyFilters();
		}
	}

	function handleSearchInput() {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			searchQuery = pendingSearch;
			load(1);
		}, 400);
	}

	function handleTypeChange() {
		load(1);
	}

	function handleRemoteChange() {
		load(1);
	}

	function handleSortChange() {
		load(1);
	}

	function addTag() {
		const tag = pendingTag.trim().toLowerCase();
		if (tag && !selectedTags.includes(tag)) {
			selectedTags = [...selectedTags, tag];
			load(1);
		}
		pendingTag = '';
	}

	function removeTag(tag: string) {
		selectedTags = selectedTags.filter((t) => t !== tag);
		load(1);
	}

	function handleTagKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ',') {
			e.preventDefault();
			addTag();
		}
	}

	function formatDate(iso: string) {
		return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function formatSalary(min: number | null, max: number | null): string | null {
		const fmt = (n: number) =>
			n >= 1000 ? `$${(n / 1000).toFixed(0)}k` : `$${n.toLocaleString()}`;
		if (min !== null && max !== null) return `${fmt(min)} – ${fmt(max)}`;
		if (min !== null) return `From ${fmt(min)}`;
		if (max !== null) return `Up to ${fmt(max)}`;
		return null;
	}

	onMount(() => load());
</script>

<svelte:head>
	<title>Browse Jobs</title>
	<meta name="description" content="Browse open job positions." />
</svelte:head>

<div class="listing-page">
	<!-- Filters bar -->
	<div class="filters">
		<div class="search-wrap">
			<input
				type="search"
				class="search-input"
				placeholder="Search jobs…"
				bind:value={pendingSearch}
				on:input={handleSearchInput}
				on:keydown={handleSearchKeydown}
			/>
		</div>

		<div class="filter-controls">
			<select bind:value={selectedType} on:change={handleTypeChange} class="filter-select">
				{#each EMPLOYMENT_TYPES as t}
					<option value={t.value}>{t.label}</option>
				{/each}
			</select>

			<label class="remote-label">
				<input type="checkbox" bind:checked={remoteOnly} on:change={handleRemoteChange} />
				Remote only
			</label>

			<select bind:value={sort} on:change={handleSortChange} class="filter-select">
				<option value="newest">Newest first</option>
				<option value="oldest">Oldest first</option>
			</select>
		</div>

		<div class="tag-filter">
			<div class="tag-input-wrap">
				<input
					type="text"
					class="tag-input"
					placeholder="Filter by tag…"
					bind:value={pendingTag}
					on:keydown={handleTagKeydown}
				/>
				<button class="tag-add-btn" on:click={addTag} disabled={!pendingTag.trim()}>Add</button>
			</div>
			{#if selectedTags.length > 0}
				<div class="tag-chips">
					{#each selectedTags as tag}
						<span class="tag-chip">
							{tag}
							<button class="tag-chip-remove" on:click={() => removeTag(tag)} aria-label="Remove {tag}">×</button>
						</span>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<!-- Results header -->
	{#if data && !isLoading}
		<p class="results-meta">
			{#if data.total === 0}
				No jobs found{searchQuery ? ` for "${searchQuery}"` : ''}.
			{:else}
				{data.total} job{data.total === 1 ? '' : 's'} found
				{#if searchQuery}<span class="meta-query"> for "<strong>{searchQuery}</strong>"</span>{/if}
			{/if}
		</p>
	{/if}

	{#if errorMessage}
		<div class="alert-error" role="alert">{errorMessage}</div>
	{/if}

	{#if isLoading}
		<div class="loading-grid">
			{#each { length: 6 } as _}
				<div class="skeleton-card"></div>
			{/each}
		</div>
	{:else if data && data.items.length > 0}
		<div class="job-grid">
			{#each data.items as job (job.public_id)}
				<a href="/jobs/{job.public_id}" class="job-card">
					<div class="card-top">
						<h2 class="card-title">{job.title}</h2>
						<div class="card-meta">
							<span class="meta-badge type-badge">{EMPLOYMENT_LABELS[job.employment_type] ?? job.employment_type}</span>
							{#if job.is_remote && !job.location}
								<span class="meta-badge remote-badge">Remote</span>
							{:else if job.is_remote && job.location}
								<span class="meta-location">{job.location}</span>
								<span class="meta-badge remote-badge">Remote</span>
							{:else if job.location}
								<span class="meta-location">{job.location}</span>
							{/if}
						</div>
					{#if formatSalary(job.salary_min, job.salary_max)}
						<div class="card-salary">{formatSalary(job.salary_min, job.salary_max)}</div>
					{/if}
					</div>

					{#if job.tags.length > 0}
						<div class="card-tags">
							{#each job.tags.slice(0, 4) as tag}
								<span class="tag">{tag.name}</span>
							{/each}
							{#if job.tags.length > 4}
								<span class="tag tag-more">+{job.tags.length - 4}</span>
							{/if}
						</div>
					{/if}

					<div class="card-footer">
						<span class="posted-date">Posted {formatDate(job.created_at)}</span>
						<span class="view-link">View →</span>
					</div>
				</a>
			{/each}
		</div>

		{#if data.pages > 1}
			<div class="pagination">
				<button
					class="page-btn"
					disabled={currentPage <= 1}
					on:click={() => load(currentPage - 1)}
				>
					← Previous
				</button>
				<span class="page-info">Page {currentPage} of {data.pages}</span>
				<button
					class="page-btn"
					disabled={currentPage >= data.pages}
					on:click={() => load(currentPage + 1)}
				>
					Next →
				</button>
			</div>
		{/if}
	{:else if data && data.items.length === 0}
		<div class="empty">
			<p>No jobs match your filters.</p>
			<button
				class="clear-btn"
				on:click={() => {
					pendingSearch = '';
					searchQuery = '';
					selectedType = '';
					remoteOnly = false;
					sort = 'newest';
					selectedTags = [];
					pendingTag = '';
					load(1);
				}}
			>
				Clear filters
			</button>
		</div>
	{/if}
</div>

<style>
	.listing-page {
		max-width: 960px;
		margin: 0 auto;
	}

	/* Filters */
	.filters {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
		align-items: center;
	}

	.search-wrap {
		flex: 1;
		min-width: 200px;
	}

	.search-input {
		width: 100%;
		padding: 0.55rem 0.9rem;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		font-size: 0.95rem;
		background: white;
		outline: none;
		transition: border-color 0.15s;
	}

	.search-input:focus {
		border-color: #3b82f6;
	}

	.filter-controls {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.filter-select {
		padding: 0.5rem 0.75rem;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		font-size: 0.9rem;
		background: white;
		outline: none;
		cursor: pointer;
	}

	.filter-select:focus {
		border-color: #3b82f6;
	}

	.remote-label {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.9rem;
		cursor: pointer;
		white-space: nowrap;
		color: #4a5568;
	}

	/* Results meta */
	.results-meta {
		font-size: 0.875rem;
		color: #718096;
		margin: 0 0 1rem;
	}

	.meta-query strong {
		color: #2d3748;
	}

	.alert-error {
		background: #fff5f5;
		border: 1px solid #feb2b2;
		color: #c53030;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1rem;
		font-size: 0.9rem;
	}

	/* Loading skeletons */
	.loading-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1rem;
	}

	.skeleton-card {
		height: 160px;
		border-radius: 12px;
		background: #e2e8f0;
		animation: pulse 1.4s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	/* Job grid */
	.job-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1rem;
	}

	.job-card {
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.25rem;
		text-decoration: none;
		color: inherit;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		transition: border-color 0.15s, box-shadow 0.15s, transform 0.1s;
	}

	.job-card:hover {
		border-color: #3b82f6;
		box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
		transform: translateY(-1px);
	}

	.card-top {
		flex: 1;
	}

	.card-title {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
		color: #1a202c;
		line-height: 1.4;
	}

	.card-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		align-items: center;
	}

	.meta-badge {
		display: inline-block;
		padding: 0.15rem 0.55rem;
		border-radius: 999px;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.type-badge {
		background: #eff6ff;
		color: #1d4ed8;
		border: 1px solid #bfdbfe;
	}

	.remote-badge {
		background: #f0fdf4;
		color: #15803d;
		border: 1px solid #bbf7d0;
	}

	.meta-location {
		font-size: 0.8rem;
		color: #718096;
	}

	.card-salary {
		font-size: 0.82rem;
		font-weight: 600;
		color: #15803d;
		margin-top: 0.25rem;
	}

	/* Tags */
	.card-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
	}

	.tag {
		padding: 0.1rem 0.45rem;
		background: #f7fafc;
		border: 1px solid #e2e8f0;
		border-radius: 999px;
		font-size: 0.72rem;
		color: #4a5568;
	}

	.tag-more {
		color: #718096;
	}

	/* Card footer */
	.card-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-top: 0.5rem;
		border-top: 1px solid #f0f4f8;
	}

	.posted-date {
		font-size: 0.78rem;
		color: #a0aec0;
	}

	.view-link {
		font-size: 0.82rem;
		font-weight: 600;
		color: #3b82f6;
	}

	/* Empty state */
	.empty {
		text-align: center;
		padding: 4rem 1rem;
		color: #718096;
	}

	.empty p {
		margin-bottom: 1rem;
	}

	.clear-btn {
		padding: 0.5rem 1.25rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 0.9rem;
		cursor: pointer;
		transition: background 0.15s;
	}

	.clear-btn:hover {
		background: #2563eb;
	}

	/* Pagination */
	.pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1.5rem;
		margin-top: 2rem;
		font-size: 0.9rem;
	}

	.page-btn {
		padding: 0.5rem 1rem;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		background: white;
		font-size: 0.9rem;
		cursor: pointer;
		transition: border-color 0.15s;
	}

	.page-btn:hover:not(:disabled) {
		border-color: #3b82f6;
		color: #3b82f6;
	}

	.page-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.page-info {
		color: #718096;
	}

	/* Tag filter */
	.tag-filter {
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.tag-input-wrap {
		display: flex;
		gap: 0.4rem;
	}

	.tag-input {
		flex: 1;
		padding: 0.55rem 0.9rem;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		font-size: 0.9rem;
		background: white;
		outline: none;
		transition: border-color 0.15s;
	}

	.tag-input:focus {
		border-color: #3b82f6;
	}

	.tag-add-btn {
		padding: 0.5rem 0.85rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 0.85rem;
		cursor: pointer;
		transition: background 0.15s;
	}

	.tag-add-btn:hover:not(:disabled) {
		background: #2563eb;
	}

	.tag-add-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.tag-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}

	.tag-chip {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.2rem 0.55rem;
		background: #eff6ff;
		border: 1px solid #bfdbfe;
		border-radius: 999px;
		font-size: 0.8rem;
		color: #1d4ed8;
	}

	.tag-chip-remove {
		background: none;
		border: none;
		padding: 0;
		line-height: 1;
		font-size: 1rem;
		color: #3b82f6;
		cursor: pointer;
		display: flex;
		align-items: center;
	}

	.tag-chip-remove:hover {
		color: #1d4ed8;
	}

	@media (max-width: 600px) {
		.filters {
			flex-direction: column;
			align-items: stretch;
		}

		.filter-controls {
			justify-content: space-between;
		}

		.job-grid,
		.loading-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
