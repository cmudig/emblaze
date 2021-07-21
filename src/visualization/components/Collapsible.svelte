<script>
	import { slide } from "svelte/transition";
    import { createEventDispatcher } from 'svelte';
	export let entry;
	let isOpen = false;
	const toggle = () => isOpen = !isOpen;
    const dispatch = createEventDispatcher();
	let activeSelection = false;
</script>
<style>
	
	.accordion {border: none; 
				background: none;
		        display:block; 
		        color: inherit; 
		        font-size: 18px; 
		        cursor: pointer;
		        margin: 0; 
		        padding-bottom: 0.5em; 
		        padding-top: 0.5em;
                width: 200px;
		        text-align: left; }

	.accordion:focus {color:white; 
                      background: blue}
	
	svg { transition: transform 0.2s ease-in; }
	
	[aria-expanded=true] svg { transform: rotate(0.25turn); }
</style>
<button on:click={toggle} aria-expanded={isOpen} class="accordion">
    <svg style="tran"  width="20" height="20" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 24 24" stroke="currentColor">
        <path d="M9 5l7 7-7 7"></path>
    </svg> 
    <b>{entry["selectionName"]}</b>
{#if isOpen}
<p style="font-size:14px">{entry["selectionDescription"]}</p>
	<button
       style="font-size:12px"
       on:click={() => dispatch('loadSelection', {selectedIDs: entry["selectedIDs"],
                                                  alignedIDs: entry["alignedIDs"],
                                                  currentFrame: entry["currentFrame"]})}>
	   Load Selection
	</button>
{/if}
</button>

