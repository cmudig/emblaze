<script>
  import { createEventDispatcher } from 'svelte';

  import SelectionBrowseItem from './SelectionBrowseItem';

  const dispatch = createEventDispatcher();
  export let data = [];
</script>

<div class="selection-browser-container">
  {#each data as entry}
    <SelectionBrowseItem {entry} on:loadSelection />
  {/each}
</div>

<style>
  .selection-browser-container {
    background: white;
  }
</style>
