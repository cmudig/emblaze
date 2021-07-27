<script>
  import { createEventDispatcher } from 'svelte';

  import SelectionBrowseItem from './SelectionBrowseItem';

  const dispatch = createEventDispatcher();
  export let data = [];
</script>

<div class="selection-browser-container">
  <button on:click|preventDefault={() => dispatch('close')}>
    Close Sidebar
  </button>
  {#each data as entry}
    <SelectionBrowseItem {entry} on:loadSelection />
  {/each}
</div>

<style>
  .selection-browser-container {
    background: white;
    margin-left: 24px;
    flex-wrap: wrap;
    flex-direction: column;
    align-content: flex-start;
    padding: 2rem 1rem 0.6rem;
  }
</style>
