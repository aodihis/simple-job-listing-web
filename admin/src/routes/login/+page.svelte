<script lang="ts">
	import { goto } from '$app/navigation';
	import { loginAdmin } from '$lib/api/auth';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import { setAuth } from '$lib/utils/auth';

	const log = createLogger('LoginPage');

	let email = '';
	let password = '';
	let isLoading = false;
	let errorMessage = '';

	async function handleSubmit() {
		errorMessage = '';
		isLoading = true;

		try {
			const response = await loginAdmin(email, password);
			setAuth(response);
			log.info('auth.login_success', { email });
			goto('/dashboard', { replaceState: true });
		} catch (err) {
			if (err instanceof ApiError) {
				if (err.status === 401) {
					errorMessage = 'Invalid email or password.';
				} else {
					errorMessage = 'Login failed. Please try again.';
				}
				log.warn('auth.login_failed', { email, status: err.status });
			} else {
				errorMessage = 'An unexpected error occurred. Please try again.';
				log.error('auth.login_error', { error: String(err) });
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Login — Admin</title>
</svelte:head>

<div class="auth-page">
	<div class="auth-card">
		<h1>Admin Login</h1>

		{#if errorMessage}
			<div class="alert alert-error" role="alert">{errorMessage}</div>
		{/if}

		<form on:submit|preventDefault={handleSubmit} novalidate>
			<div class="field">
				<label for="email">Email</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					autocomplete="email"
					disabled={isLoading}
				/>
			</div>

			<div class="field">
				<label for="password">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					autocomplete="current-password"
					disabled={isLoading}
				/>
			</div>

			<button type="submit" class="btn-primary" disabled={isLoading}>
				{#if isLoading}Signing in…{:else}Sign In{/if}
			</button>
		</form>
	</div>
</div>

<style>
	.auth-page {
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
	}

	.auth-card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		padding: 2rem;
		width: 100%;
		max-width: 400px;
		box-shadow: var(--shadow);
	}

	h1 {
		margin: 0 0 1.5rem;
		font-size: 1.5rem;
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

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		margin-bottom: 1rem;
	}

	label {
		font-size: 0.875rem;
		font-weight: 500;
	}

	input {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		font-size: 1rem;
		outline: none;
		transition: border-color 0.15s;
	}

	input:focus {
		border-color: var(--color-primary);
	}

	input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-primary {
		width: 100%;
		padding: 0.6rem 1rem;
		background: var(--color-primary);
		color: white;
		border: none;
		border-radius: var(--radius);
		font-size: 1rem;
		font-weight: 500;
		margin-top: 0.5rem;
		transition: background 0.15s;
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--color-primary-hover);
	}

	.btn-primary:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}
</style>
