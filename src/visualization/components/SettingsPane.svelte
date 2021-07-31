<script>
  import { createEventDispatcher } from 'svelte';

  export let previewMode = '';
  export let previewModes = [];

  export let numNeighbors = 10;

  // Delay the setting of numNeighbors since it might alter the UI
  let numNeighborsValue = 10;
  let oldNumNeighbors = 10;
  let numNeighborsTimeout = null;
  $: numNeighborsValue = numNeighbors;
  $: if (oldNumNeighbors != numNeighborsValue) {
    updateNumNeighbors();
    oldNumNeighbors = numNeighborsValue;
  }

  function updateNumNeighbors() {
    if (!!numNeighborsTimeout) clearTimeout(numNeighborsTimeout);
    numNeighborsTimeout = setTimeout(() => {
      numNeighbors = numNeighborsValue;
    }, 100);
  }

  export let previewK = 10;
  export let similarityThreshold = 0.5;

  export let colorScheme = '';
  export let colorSchemes = [];

  export let showLegend = true;

  const dispatch = createEventDispatcher();
</script>

<div class="dialog-body">
  <form>
    <div class="form-row">
      <label for="color-scheme" class="col-form-label">Color Scheme</label>
      <select
        bind:value={colorScheme}
        id="color-scheme"
        class="col-form-element"
      >
        {#each colorSchemes as scheme}
          <option value={scheme}>{scheme}</option>
        {/each}
      </select>
    </div>
    <div class="form-row">
      <label for="neighbor-k" class="col-form-label"
        >Neighbor Count: {numNeighborsValue}</label
      >
      <input
        class="col-form-element"
        type="range"
        min="5"
        max="100"
        step="5"
        bind:value={numNeighborsValue}
        id="neighbor-k"
      />
    </div>
    <p class="help-text">
      The number of neighbors displayed in the scatterplot and sidebar.
    </p>
    <div class="form-row">
      <input type="checkbox" id="show-legend" bind:checked={showLegend} />
      <label for="show-legend" style="padding-left: 12px;">Show Legend</label>
    </div>
    <div class="form-row">
      <label for="preview-mode" class="col-form-label">Preview Mode</label>
      <select
        bind:value={previewMode}
        id="preview-mode"
        class="col-form-element"
      >
        {#each previewModes as mode}
          <option value={mode}>{mode}</option>
        {/each}
      </select>
    </div>
    <div class="form-row">
      <label for="preview-k" class="col-form-label"
        >Preview Neighbor Count: {previewK}</label
      >
      <input
        class="col-form-element"
        type="range"
        min="5"
        max="100"
        step="5"
        bind:value={previewK}
        id="preview-k"
      />
    </div>
    <p class="help-text">
      The number of neighbors used to calculate pointwise similarity between
      frames.
    </p>
    <div class="form-row">
      <label for="similarity-threshold" class="col-form-label"
        >Similarity Threshold: {similarityThreshold.toFixed(2)}</label
      >
      <input
        type="range"
        min="0"
        max="1"
        step="0.05"
        class="col-form-element"
        bind:value={similarityThreshold}
        id="similarity-threshold"
      />
    </div>
    <p class="help-text">
      If the fraction of neighbors that stay constant between frames is above
      this threshold, a preview line will not be shown.
    </p>
  </form>
</div>
<div class="dialog-footer">
  <button
    type="button"
    class="dialog-footer-button btn btn-secondary jp-Dialog-button jp-mod-reject jp-mod-styled"
    on:click={() => dispatch('close')}>Close</button
  >
</div>

<style>
  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    padding-top: 12px;
  }

  .dialog-footer-button {
    margin-left: 12px;
    margin-right: 0 !important;
  }

  .form-row {
    display: flex;
  }

  .col-form-label {
    flex: 0 0 auto;
    padding-right: 12px;
  }

  .col-form-element {
    flex-grow: 1;
  }

  .help-text {
    color: #666;
    font-size: 0.85em;
    margin-bottom: 12px;
  }
</style>
