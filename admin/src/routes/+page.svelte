<script lang="ts">
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth';
	import { onMount } from 'svelte';

	onMount(() => {
		if ($isAuthenticated) {
			goto('/dashboard', { replaceState: true });
		} else {
			goto('/login', { replaceState: true });
		}
	});
</script>

<p>Redirecting...</p>
