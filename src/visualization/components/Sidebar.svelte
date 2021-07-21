{#if show}
  <nav transition:fly={{x: 250, opacity: 1}}>
		<button on:click|preventDefault={() => show = false}>
            Close Sidebar
        </button>
        {#each data as entry, i}
		    <Collapsible entry={entry} idx={i} on:loadSelection />
		{/each}
  </nav>
{/if}



<script>
import { fly } from 'svelte/transition';
import Collapsible from './Collapsible';

export let data = [];
export let show = false;

</script>
		
<style>
nav {
    position: absolute;
    background: white;
	top: 0;
    right: 0;
	margin-left: 24px; 
	height: 600px; 
	flex-wrap: wrap; 
	flex-direction: column; 
	align-content: flex-start;
	border-left: 1px solid #aaa;
	padding: 2rem 1rem 0.6rem;
	width: 240px;
}
</style>