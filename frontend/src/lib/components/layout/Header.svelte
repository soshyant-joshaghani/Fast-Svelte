<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import ThemeToggle from '$lib/components/layout/ThemeToggle.svelte';
	import UserNav from '$lib/components/layout/UserNav.svelte';
</script>

<header class="flex h-14 shrink-0 items-center gap-2 border-b px-4">
	<Sidebar.Trigger class="-ml-1" />
	<Separator orientation="vertical" class="mr-2 h-4" />
	<div class="flex flex-1 items-center justify-end gap-2">
		<ThemeToggle />
		<UserNav />
	</div>
</header>
