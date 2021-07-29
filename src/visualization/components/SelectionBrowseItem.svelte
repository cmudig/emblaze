<script>
  import { slide } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  export let entry;
  let isOpen = false;
  const toggle = () => (isOpen = !isOpen);
  const dispatch = createEventDispatcher();
  let activeSelection = false;
</script>

<button on:click={toggle} aria-expanded={isOpen} class="accordion">
  <b>{entry['selectionName']}</b>
  {#if isOpen}
    <p class="detail">{entry['selectionDescription']}</p>
    <p class="detail summary-text">
      Frame {entry.currentFrame}, {entry.selectedIDs.length} selected, {entry
        .alignedIDs.length} aligned, {entry.filterIDs.length > 0
        ? `${entry.filterIDs.length} filtered`
        : 'no filter'}
    </p>
    <button
      class="load-selection-btn btn btn-primary btn-sm jp-Dialog-button jp-mod-accept jp-mod-styled"
      on:click={() => dispatch('loadSelection', entry)}
    >
      Load Selection
    </button>
  {/if}
</button>

<style>
  .accordion {
    border: none;
    border-bottom: 1px solid #bbb;
    background: none;
    display: block;
    color: inherit;
    font-size: 14px;
    cursor: pointer;
    margin: 0;
    padding: 12px;
    width: 100%;
    text-align: left;
  }

  .accordion:focus {
    background: #bbb;
  }

  .accordion:hover {
    background: #eee;
  }

  .load-selection-btn {
    margin-top: 8px;
  }

  .summary-text {
    color: #666;
  }

  .detail {
    font-size: 0.85em;
  }
</style>
