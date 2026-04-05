<script lang="ts">
	import { goto } from '$app/navigation';
	import { clearAuth } from '$lib/utils/auth';
	import { isAuthenticated } from '$lib/stores/auth';

	function handleLogout() {
		clearAuth();
		goto('/login');
	}
</script>

<div class="admin-shell">
	<aside class="sidebar">
		<div class="sidebar-header">
			<span class="brand">Admin</span>
		</div>

		<nav class="nav">
			<a href="/dashboard" class="nav-link">Dashboard</a>
			<a href="/jobs" class="nav-link">Jobs</a>
			<a href="/applications" class="nav-link">Applications</a>
			<a href="/admins" class="nav-link">Admins</a>
			<a href="/settings" class="nav-link">Settings</a>
		</nav>

		<div class="sidebar-footer">
			<button class="logout-btn" on:click={handleLogout}>Log out</button>
		</div>
	</aside>

	<main class="content">
		<slot />
	</main>
</div>

<style>
	.admin-shell {
		display: flex;
		min-height: 100vh;
	}

	.sidebar {
		width: 220px;
		background: var(--color-surface);
		border-right: 1px solid var(--color-border);
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
	}

	.sidebar-header {
		padding: 1.25rem 1rem;
		border-bottom: 1px solid var(--color-border);
	}

	.brand {
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--color-primary);
	}

	.nav {
		display: flex;
		flex-direction: column;
		padding: 0.75rem 0;
		flex: 1;
	}

	.nav-link {
		padding: 0.6rem 1rem;
		color: var(--color-text);
		text-decoration: none;
		font-size: 0.9rem;
		transition: background 0.1s;
	}

	.nav-link:hover {
		background: var(--color-bg);
	}

	.sidebar-footer {
		padding: 1rem;
		border-top: 1px solid var(--color-border);
	}

	.logout-btn {
		width: 100%;
		padding: 0.5rem;
		background: none;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		font-size: 0.875rem;
		color: var(--color-text-muted);
		transition: all 0.15s;
	}

	.logout-btn:hover {
		border-color: var(--color-danger);
		color: var(--color-danger);
	}

	.content {
		flex: 1;
		padding: 2rem;
		overflow-y: auto;
	}
</style>
