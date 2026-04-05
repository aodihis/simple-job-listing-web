<script lang="ts">
	import { goto } from '$app/navigation';
	import { registerFirstAdmin } from '$lib/api/auth';
	import { ApiError } from '$lib/api/types';
	import { createLogger } from '$lib/logger';
	import { token } from '$lib/stores/auth';

	const log = createLogger('RegisterPage');

	let email = '';
	let displayName = '';
	let password = '';
	let confirmPassword = '';

	let isLoading = false;
	let errorMessage = '';

	const fieldErrors: Record<string, string> = {};

	function validate(): boolean {
		Object.keys(fieldErrors).forEach((k) => delete fieldErrors[k]);
		let valid = true;

		if (!email) {
			fieldErrors['email'] = 'Email is required.';
			valid = false;
		}
		if (!displayName) {
			fieldErrors['displayName'] = 'Display name is required.';
			valid = false;
		}
		if (password.length < 8) {
			fieldErrors['password'] = 'Password must be at least 8 characters.';
			valid = false;
		}
		if (password !== confirmPassword) {
			fieldErrors['confirmPassword'] = 'Passwords do not match.';
			valid = false;
		}

		return valid;
	}

	async function handleSubmit() {
		errorMessage = '';
		if (!validate()) return;

		isLoading = true;
		try {
			const response = await registerFirstAdmin(email, displayName, password);
			token.set(response.access_token);
			log.info('auth.register_success', { email });
			goto('/dashboard', { replaceState: true });
		} catch (err) {
			if (err instanceof ApiError) {
				if (err.status === 409) {
					errorMessage = 'An admin account already exists. Please log in instead.';
				} else if (err.status === 422) {
					errorMessage = 'Please check your inputs and try again.';
				} else {
					errorMessage = 'Registration failed. Please try again.';
				}
				log.warn('auth.register_failed', { email, status: err.status });
			} else {
				errorMessage = 'An unexpected error occurred. Please try again.';
				log.error('auth.register_error', { error: String(err) });
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Register — Admin</title>
</svelte:head>

<div class="auth-page">
	<div class="auth-card">
		<h1>Create Admin Account</h1>
		<p class="subtitle">Set up the first administrator account.</p>

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
					class:invalid={fieldErrors['email']}
				/>
				{#if fieldErrors['email']}
					<span class="field-error">{fieldErrors['email']}</span>
				{/if}
			</div>

			<div class="field">
				<label for="displayName">Display Name</label>
				<input
					id="displayName"
					type="text"
					bind:value={displayName}
					autocomplete="name"
					disabled={isLoading}
					class:invalid={fieldErrors['displayName']}
				/>
				{#if fieldErrors['displayName']}
					<span class="field-error">{fieldErrors['displayName']}</span>
				{/if}
			</div>

			<div class="field">
				<label for="password">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					autocomplete="new-password"
					disabled={isLoading}
					class:invalid={fieldErrors['password']}
				/>
				{#if fieldErrors['password']}
					<span class="field-error">{fieldErrors['password']}</span>
				{/if}
			</div>

			<div class="field">
				<label for="confirmPassword">Confirm Password</label>
				<input
					id="confirmPassword"
					type="password"
					bind:value={confirmPassword}
					autocomplete="new-password"
					disabled={isLoading}
					class:invalid={fieldErrors['confirmPassword']}
				/>
				{#if fieldErrors['confirmPassword']}
					<span class="field-error">{fieldErrors['confirmPassword']}</span>
				{/if}
			</div>

			<button type="submit" class="btn-primary" disabled={isLoading}>
				{#if isLoading}Creating account…{:else}Create Account{/if}
			</button>
		</form>

		<p class="footer-link">Already have an account? <a href="/login">Log in</a></p>
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
		max-width: 420px;
		box-shadow: var(--shadow);
	}

	h1 {
		margin: 0 0 0.25rem;
		font-size: 1.5rem;
	}

	.subtitle {
		color: var(--color-text-muted);
		margin: 0 0 1.5rem;
		font-size: 0.9rem;
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

	input.invalid {
		border-color: var(--color-danger);
	}

	input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.field-error {
		font-size: 0.8rem;
		color: var(--color-danger);
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

	.footer-link {
		text-align: center;
		margin: 1.25rem 0 0;
		font-size: 0.875rem;
		color: var(--color-text-muted);
	}
</style>
