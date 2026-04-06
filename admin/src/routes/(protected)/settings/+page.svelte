<script lang="ts">
	import { sendTestEmail } from '$lib/api/settings';
	import { createLogger } from '$lib/logger';

	const log = createLogger('SettingsPage');

	let to = '';
	let errors: { to?: string } = {};
	let resultMessage = '';
	let resultSuccess: boolean | null = null;
	let isSending = false;

	function validate(): boolean {
		errors = {};
		if (!to.trim()) {
			errors.to = 'Recipient email is required.';
		} else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(to.trim())) {
			errors.to = 'Enter a valid email address.';
		}
		return Object.keys(errors).length === 0;
	}

	async function handleSend() {
		if (!validate()) return;

		isSending = true;
		resultMessage = '';
		resultSuccess = null;

		try {
			const result = await sendTestEmail(to.trim());
			resultSuccess = result.success;
			resultMessage = result.message;
			log.info('settings.test_email_result', { success: result.success, to: to.trim() });
		} catch (error) {
			resultSuccess = false;
			resultMessage = 'Something went wrong. Please try again.';
			log.error('settings.test_email_failed', { error: String(error) });
		} finally {
			isSending = false;
		}
	}
</script>

<svelte:head>
	<title>Settings — Admin</title>
</svelte:head>

<div class="settings">
	<h1>Settings</h1>

	<section class="card">
		<h2>Email Configuration</h2>
		<p class="section-desc">
			Send a test email to verify your SMTP configuration is working correctly.
		</p>

		<form on:submit|preventDefault={handleSend} class="form">
			<div class="field">
				<label for="to">Send test email to</label>
				<input
					id="to"
					type="email"
					bind:value={to}
					placeholder="you@example.com"
					disabled={isSending}
					class:input-error={errors.to}
				/>
				{#if errors.to}
					<span class="error">{errors.to}</span>
				{/if}
			</div>

			<button type="submit" class="btn-primary" disabled={isSending}>
				{isSending ? 'Sending…' : 'Send Test Email'}
			</button>
		</form>

		{#if resultMessage}
			<div class="result" class:success={resultSuccess} class:failure={!resultSuccess}>
				{resultMessage}
			</div>
		{/if}
	</section>
</div>

<style>
	.settings {
		max-width: 600px;
	}

	h1 {
		margin: 0 0 1.5rem;
	}

	.card {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		padding: 1.5rem;
	}

	h2 {
		margin: 0 0 0.25rem;
		font-size: 1rem;
		font-weight: 600;
	}

	.section-desc {
		margin: 0 0 1.25rem;
		font-size: 0.875rem;
		color: var(--color-text-muted);
	}

	.form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	label {
		font-size: 0.875rem;
		font-weight: 500;
	}

	input {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		font-size: 0.875rem;
		background: var(--color-bg);
		color: var(--color-text);
	}

	input.input-error {
		border-color: var(--color-danger);
	}

	.error {
		font-size: 0.8rem;
		color: var(--color-danger);
	}

	.btn-primary {
		align-self: flex-start;
		padding: 0.5rem 1.25rem;
		background: var(--color-primary);
		color: #fff;
		border: none;
		border-radius: var(--radius);
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.15s;
	}

	.btn-primary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.result {
		margin-top: 1rem;
		padding: 0.75rem 1rem;
		border-radius: var(--radius);
		font-size: 0.875rem;
	}

	.result.success {
		background: color-mix(in srgb, var(--color-success, #22c55e) 12%, transparent);
		border: 1px solid var(--color-success, #22c55e);
		color: var(--color-success, #16a34a);
	}

	.result.failure {
		background: color-mix(in srgb, var(--color-danger) 12%, transparent);
		border: 1px solid var(--color-danger);
		color: var(--color-danger);
	}
</style>
