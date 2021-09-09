<script>
  import { createEventDispatcher } from 'svelte';

  import SelectionBrowseItem from './SelectionBrowseItem';

  const dispatch = createEventDispatcher();
  export let data = [];
  export let thumbnailProvider = null;
  export let loading = false;

  export let emptyMessage = 'No items yet';
  export let loadingMessage = 'Loading...';
</script>

{#if loading}
  <div class="placeholder-text">
    {loadingMessage}
    <i class="fa fa-spinner fa-spin" />
  </div>
{:else if data.length == 0}
  <div class="placeholder-text">
    {emptyMessage}
  </div>
{:else}
  <div class="selection-browser-container">
    {#each data as entry}
      <SelectionBrowseItem {entry} {thumbnailProvider} on:loadSelection />
    {/each}
  </div>
{/if}

<style>
  .selection-browser-container {
    background: white;
  }

  .placeholder-text {
    max-width: 100%;
    text-align: center;
    color: #999;
    padding: 80px 24px 0 24px;
  }
</style>
