<script>
  import { slide } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import Thumbnail from './Thumbnail.svelte';
  export let entry;
  export let thumbnailProvider = null;

  let selectionPreviewItems = '';
  $: if (
    !!thumbnailProvider &&
    !thumbnailProvider.hasImages &&
    !!entry &&
    !!entry.selectedIDs &&
    entry.selectedIDs.length > 0
  ) {
    let items = entry.selectedIDs.map((id) =>
      thumbnailProvider.get(id, entry.currentFrame)
    );
    selectionPreviewItems = items
      .map((item) => item.text)
      .slice(0, isOpen ? 10 : 3);
  }

  let selectionComponents = [];
  $: {
    selectionComponents = [];
    if (!!entry.selectedIDs && entry.selectedIDs.length > 0)
      selectionComponents.push(`${entry.selectedIDs.length} selected`);
    if (!!entry.alignedIDs && entry.alignedIDs.length > 0)
      selectionComponents.push(`${entry.alignedIDs.length} aligned`);
    if (!!entry.filterIDs && entry.filterIDs.length > 0)
      selectionComponents.push(`${entry.filterIDs.length} filtered`);
  }

  let isOpen = false;
  const toggle = () => (isOpen = !isOpen);
  const dispatch = createEventDispatcher();
  let activeSelection = false;
</script>

<button on:click={toggle} aria-expanded={isOpen} class="accordion">
  {#if !!entry.selectionName}
    <b>{entry.selectionName}</b>
  {/if}
  {#if !!thumbnailProvider && !!entry.selectedIDs && entry.selectedIDs.length > 0}
    {#if thumbnailProvider.hasImages}
      <div class="wrap-container">
        {#each entry.selectedIDs.slice(0, isOpen ? 6 : 3) as id}
          <Thumbnail
            {thumbnailProvider}
            {id}
            frame={entry.currentFrame}
            mini
            detail={false}
          />
        {/each}
        <p class="accordion-subtitle">
          and {entry.selectedIDs.length - (isOpen ? 6 : 3)} others
        </p>
      </div>
    {:else}
      <p class="accordion-subtitle">
        {#each selectionPreviewItems as item, i}
          <strong>{item}</strong>{i == entry.selectedIDs.length - 1 ? '' : ', '}
        {/each}
        {#if entry.selectedIDs.length > selectionPreviewItems.length}
          and {entry.selectedIDs.length - selectionPreviewItems.length} others
        {/if}
      </p>
    {/if}
  {/if}
  {#if !!entry.selectionDescription}
    <p class="detail">{@html entry.selectionDescription}</p>
  {/if}
  {#if !!entry.frameColors}
    <div class="frame-color-bar">
      {#each entry.frameColors as color}
        <div
          class="frame-color-bar-item"
          style={`background-color: hsla(${color[0]}, ${color[1]}%, ${color[2]}%, 1.0);`}
        />
      {/each}
    </div>
  {/if}
  {#if isOpen}
    <p class="detail summary-text">
      Frame {entry.currentFrame}, {selectionComponents.join(', ')}
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

  .accordion-subtitle {
    font-size: 13px;
    flex: 0 0 auto;
  }

  .detail {
    font-size: 0.85em;
  }

  .frame-color-bar {
    width: 100%;
    height: 6px;
    display: flex;
    justify-content: stretch;
    margin: 4px 0;
  }

  .frame-color-bar-item {
    flex: 1;
  }

  .wrap-container {
    display: flex;
    flex-wrap: wrap;
    flex: 1;
    align-items: center;
  }
</style>
