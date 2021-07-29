<script>
  import { createEventDispatcher } from 'svelte';

  import SelectionBrowseItem from './SelectionBrowseItem';

  const dispatch = createEventDispatcher();
  export let data = [];
</script>

{#if data.length == 0}
  <div class="no-history">
    No saved selections yet! To create one, first select, align, or isolate some
    points, then click Save Selection.
  </div>
{:else}
  <div class="selection-browser-container">
    {#each data as entry}
      <SelectionBrowseItem {entry} on:loadSelection />
    {/each}
  </div>
{/if}

<style>
  .selection-browser-container {
    background: white;
  }

  .no-history {
    max-width: 100%;
    text-align: center;
    color: #999;
    padding: 80px 24px 0 24px;
  }
</style>
