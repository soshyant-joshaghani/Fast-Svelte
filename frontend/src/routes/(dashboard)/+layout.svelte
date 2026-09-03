<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/modules/global/stores/auth';
	import AppSidebar from '$lib/components/layout/AppSidebar.svelte';
	import Header from '$lib/components/layout/Header.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';

	let { children } = $props();

	onMount(() => {
		if (!$authStore.isLoading && !$authStore.isAuthenticated) {
			goto('/login');
		}
	});

	$effect(() => {
		if (!$authStore.isLoading && !$authStore.isAuthenticated) {
			goto('/login');
		}
	});
</script>

{#if $authStore.isLoading}
	<div class="flex min-h-screen items-center justify-center text-muted-foreground">
		Restoring session…
	</div>
{:else if $authStore.isAuthenticated}
	<Sidebar.Provider>
		<AppSidebar />
		<Sidebar.Inset>
			<Header />
			<main class="flex-1 p-6">{@render children()}</main>
		</Sidebar.Inset>
	</Sidebar.Provider>
{/if}
