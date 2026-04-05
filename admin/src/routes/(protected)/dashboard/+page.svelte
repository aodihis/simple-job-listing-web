<script lang="ts">
	import { getMe } from '$lib/api/auth';
	import { onMount } from 'svelte';
	import type { AdminUserRead } from '$lib/api/types';

	let user: AdminUserRead | null = null;

	onMount(async () => {
		try {
			user = await getMe();
		} catch {
			// Token invalid — the API client will redirect to /login
		}
	});
</script>

<svelte:head>
	<title>Dashboard — Admin</title>
</svelte:head>

<div class="dashboard">
	<h1>Dashboard</h1>
	{#if user}
		<p>Welcome, <strong>{user.display_name}</strong>.</p>
	{:else}
		<p>Loading…</p>
	{/if}

	<div class="coming-soon">
		<p>More dashboard content will appear here as features are added.</p>
	</div>
</div>

<style>
	.dashboard {
		max-width: 900px;
	}

	h1 {
		margin: 0 0 0.5rem;
	}

	.coming-soon {
		margin-top: 2rem;
		padding: 1.5rem;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		color: var(--color-text-muted);
	}
</style>
