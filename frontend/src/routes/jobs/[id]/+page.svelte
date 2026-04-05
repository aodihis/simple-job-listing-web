<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getJob } from '$lib/api/jobs';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import type { JobRead } from '$lib/api/types';

	const log = createLogger('JobDetailPage');

	const EMPLOYMENT_LABELS: Record<string, string> = {
		full_time: 'Full-time',
		part_time: 'Part-time',
		contract: 'Contract',
		internship: 'Internship',
	};

	let job: JobRead | null = null;
	let isLoading = true;
	let notFound = false;
	let errorMessage = '';

	$: publicId = $page.params.id;
	$: renderedDescription = job?.description ?? '';

	function formatDate(iso: string) {
		return new Date(iso).toLocaleDateString(undefined, {
			month: 'long',
			day: 'numeric',
			year: 'numeric',
		});
	}

	onMount(async () => {
		try {
			job = await getJob(publicId);
			log.info('job.loaded', { public_id: publicId, title: job.title });
		} catch (err) {
			if (err instanceof ApiError && err.status === 404) {
				notFound = true;
			} else {
				errorMessage = 'Failed to load job. Please try again.';
				log.error('job.load_failed', { public_id: publicId, error: String(err) });
			}
		} finally {
			isLoading = false;
		}
	});
</script>

<svelte:head>
	<title>{job ? `${job.title} — JobBoard` : 'Job — JobBoard'}</title>
	{#if job}
		<meta name="description" content="Apply for {job.title}{job.location ? ` in ${job.location}` : ''}." />
	{/if}
</svelte:head>

<div class="detail-page">
	<a href="/" class="back-link">← All Jobs</a>

	{#if isLoading}
		<div class="skeleton-wrap">
			<div class="skeleton sk-title"></div>
			<div class="skeleton sk-meta"></div>
			<div class="skeleton sk-body"></div>
		</div>
	{:else if notFound}
		<div class="not-found">
			<h1>Job Not Found</h1>
			<p>This job posting may have been removed or is no longer active.</p>
			<a href="/" class="btn-primary">Browse All Jobs</a>
		</div>
	{:else if errorMessage}
		<div class="alert-error" role="alert">{errorMessage}</div>
	{:else if job}
		<div class="job-detail">
			<div class="detail-header">
				<h1 class="job-title">{job.title}</h1>

				<div class="meta-row">
					<span class="meta-badge type-badge">
						{EMPLOYMENT_LABELS[job.employment_type] ?? job.employment_type}
					</span>

					{#if job.is_remote && !job.location}
						<span class="meta-badge remote-badge">Remote</span>
					{:else if job.is_remote && job.location}
						<span class="meta-location">📍 {job.location}</span>
						<span class="meta-badge remote-badge">Remote</span>
					{:else if job.location}
						<span class="meta-location">📍 {job.location}</span>
					{/if}

					<span class="meta-date">Posted {formatDate(job.created_at)}</span>
				</div>

				{#if job.tags.length > 0}
					<div class="tag-row">
						{#each job.tags as tag}
							<span class="tag">{tag.name}</span>
						{/each}
					</div>
				{/if}
			</div>

			<div class="detail-body">
				<div class="description prose">
					{@html renderedDescription}
				</div>
			</div>

			<div class="apply-section">
				{#if job.application_mode === 'external_url' && job.external_apply_url}
					<a
						href={job.external_apply_url}
						target="_blank"
						rel="noopener noreferrer"
						class="btn-apply"
					>
						Apply Now →
					</a>
					<p class="apply-note">You'll be redirected to an external application page.</p>
				{:else}
					<a href="/jobs/{job.public_id}/apply" class="btn-apply">Apply Now →</a>
					<p class="apply-note">Apply directly on this site.</p>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.detail-page {
		max-width: 780px;
		margin: 0 auto;
	}

	.back-link {
		display: inline-block;
		font-size: 0.875rem;
		color: #718096;
		text-decoration: none;
		margin-bottom: 1.5rem;
	}

	.back-link:hover {
		color: #3b82f6;
	}

	/* Skeletons */
	.skeleton-wrap {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.skeleton {
		border-radius: 8px;
		background: #e2e8f0;
		animation: pulse 1.4s ease-in-out infinite;
	}

	.sk-title { height: 2.5rem; width: 60%; }
	.sk-meta  { height: 1.25rem; width: 40%; }
	.sk-body  { height: 300px; }

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	/* Not found */
	.not-found {
		text-align: center;
		padding: 4rem 1rem;
		color: #4a5568;
	}

	.not-found h1 {
		font-size: 1.5rem;
		margin-bottom: 0.5rem;
	}

	.not-found p {
		margin-bottom: 1.5rem;
	}

	.btn-primary {
		display: inline-block;
		padding: 0.55rem 1.25rem;
		background: #3b82f6;
		color: white;
		border-radius: 8px;
		text-decoration: none;
		font-size: 0.95rem;
		font-weight: 500;
	}

	.btn-primary:hover {
		background: #2563eb;
		color: white;
	}

	/* Error */
	.alert-error {
		background: #fff5f5;
		border: 1px solid #feb2b2;
		color: #c53030;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		font-size: 0.9rem;
	}

	/* Detail layout */
	.job-detail {
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 16px;
		overflow: hidden;
	}

	.detail-header {
		padding: 2rem;
		border-bottom: 1px solid #f0f4f8;
	}

	.job-title {
		font-size: 1.6rem;
		font-weight: 700;
		color: #1a202c;
		margin: 0 0 1rem;
		line-height: 1.3;
	}

	.meta-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		align-items: center;
		margin-bottom: 0.75rem;
	}

	.meta-badge {
		display: inline-block;
		padding: 0.2rem 0.65rem;
		border-radius: 999px;
		font-size: 0.8rem;
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
		font-size: 0.875rem;
		color: #4a5568;
	}

	.meta-date {
		font-size: 0.8rem;
		color: #a0aec0;
		margin-left: auto;
	}

	.tag-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}

	.tag {
		padding: 0.15rem 0.55rem;
		background: #f7fafc;
		border: 1px solid #e2e8f0;
		border-radius: 999px;
		font-size: 0.78rem;
		color: #4a5568;
	}

	/* Description */
	.detail-body {
		padding: 2rem;
	}

	.description :global(h1),
	.description :global(h2),
	.description :global(h3) {
		font-weight: 600;
		line-height: 1.4;
		margin: 1.5rem 0 0.5rem;
		color: #1a202c;
	}

	.description :global(h1) { font-size: 1.3rem; }
	.description :global(h2) { font-size: 1.1rem; }
	.description :global(h3) { font-size: 1rem; }

	.description :global(p) {
		margin: 0 0 1rem;
		color: #2d3748;
		line-height: 1.7;
	}

	.description :global(ul),
	.description :global(ol) {
		margin: 0 0 1rem 1.5rem;
		color: #2d3748;
		line-height: 1.7;
	}

	.description :global(li) {
		margin-bottom: 0.3rem;
	}

	.description :global(strong) {
		font-weight: 600;
		color: #1a202c;
	}

	.description :global(code) {
		font-family: 'SFMono-Regular', Consolas, monospace;
		background: #f7fafc;
		padding: 0.1em 0.4em;
		border-radius: 4px;
		font-size: 0.88em;
		color: #2d3748;
	}

	.description :global(pre) {
		background: #f7fafc;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		padding: 1rem;
		overflow-x: auto;
		margin: 0 0 1rem;
	}

	.description :global(pre code) {
		background: none;
		padding: 0;
	}

	.description :global(blockquote) {
		border-left: 3px solid #e2e8f0;
		padding-left: 1rem;
		color: #718096;
		margin: 0 0 1rem;
	}

	.description :global(hr) {
		border: none;
		border-top: 1px solid #e2e8f0;
		margin: 1.5rem 0;
	}

	/* Apply section */
	.apply-section {
		padding: 1.5rem 2rem;
		background: #f8fafc;
		border-top: 1px solid #f0f4f8;
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.btn-apply {
		display: inline-block;
		padding: 0.7rem 1.75rem;
		background: #3b82f6;
		color: white;
		border-radius: 8px;
		text-decoration: none;
		font-size: 1rem;
		font-weight: 600;
		transition: background 0.15s;
		white-space: nowrap;
	}

	.btn-apply:hover {
		background: #2563eb;
		color: white;
	}

	.apply-note {
		margin: 0;
		font-size: 0.85rem;
		color: #718096;
	}

	@media (max-width: 600px) {
		.detail-header,
		.detail-body {
			padding: 1.25rem;
		}

		.apply-section {
			flex-direction: column;
			align-items: flex-start;
			padding: 1.25rem;
		}

		.job-title {
			font-size: 1.3rem;
		}

		.meta-date {
			margin-left: 0;
		}
	}
</style>
