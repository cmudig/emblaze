<script>
  import { createEventDispatcher } from 'svelte';
  import { helpMessagesVisible } from '../utils/stores';
  import HelpMessage from './HelpMessage.svelte';

  import SelectionBrowseItem from './SelectionBrowseItem.svelte';

  const dispatch = createEventDispatcher();
  export let data = [];
  export let thumbnailProvider = null;
  export let loading = false;

  export let emptyMessage = 'No items yet';
  export let loadingMessage = 'Loading...';
  export let helpMessage = '';
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
    {#if $helpMessagesVisible && !!helpMessage}
      <HelpMessage width={240}>
        {@html helpMessage}
      </HelpMessage>
    {/if}
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
