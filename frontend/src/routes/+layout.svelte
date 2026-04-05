<script lang="ts">
</script>

<div class="site">
	<header class="site-header">
		<div class="header-inner">
			<a href="/" class="logo">JobBoard</a>
			<nav>
				<a href="/">Browse Jobs</a>
			</nav>
		</div>
	</header>

	<main class="site-main">
		<slot />
	</main>

	<footer class="site-footer">
		<p>© {new Date().getFullYear()} JobBoard</p>
	</footer>
</div>

<style>
	:global(*, *::before, *::after) {
		box-sizing: border-box;
	}

	:global(body) {
		margin: 0;
		font-family:
			-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
		font-size: 16px;
		color: #1a202c;
		background: #f7f8fa;
		line-height: 1.5;
	}

	:global(a) {
		color: #3b82f6;
	}

	:global(a:hover) {
		color: #2563eb;
	}

	.site {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	.site-header {
		background: white;
		border-bottom: 1px solid #e2e8f0;
		position: sticky;
		top: 0;
		z-index: 10;
	}

	.header-inner {
		max-width: 1100px;
		margin: 0 auto;
		padding: 0 1.5rem;
		height: 3.5rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.logo {
		font-size: 1.2rem;
		font-weight: 700;
		color: #3b82f6;
		text-decoration: none;
		letter-spacing: -0.02em;
	}

	nav a {
		font-size: 0.9rem;
		font-weight: 500;
		color: #4a5568;
		text-decoration: none;
	}

	nav a:hover {
		color: #3b82f6;
	}

	.site-main {
		flex: 1;
		max-width: 1100px;
		width: 100%;
		margin: 0 auto;
		padding: 2rem 1.5rem;
	}

	.site-footer {
		background: white;
		border-top: 1px solid #e2e8f0;
		text-align: center;
		padding: 1.25rem;
		font-size: 0.85rem;
		color: #718096;
	}

	.site-footer p {
		margin: 0;
	}
</style>
