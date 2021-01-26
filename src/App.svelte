<script>
  import { dummyData } from './dummy-data/data.js';
  import SynchronizedScatterplot from './visualization/SynchronizedScatterplot.svelte';
  import SpinnerButton from './visualization/SpinnerButton.svelte';
  import * as d3 from 'd3';

  export let model;

  // Creates a Svelte store (https://svelte.dev/tutorial/writable-stores) that syncs with the named Traitlet in widget.ts and example.py.
  import { syncValue } from './stores';
  import { Dataset } from './visualization/dataset.js';
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  let data = syncValue(model, 'data', {});
  let isLoading = syncValue(model, 'isLoading', true);
  let loadingMessage = syncValue(model, 'loadingMessage', '');

  let plotPadding = syncValue(model, 'plotPadding', 10.0);

  let dataset = null;
  let frameTransformations = syncValue(model, 'frameTransformations', []);

  $: if (
    !!$frameTransformations &&
    $frameTransformations.length > 0 &&
    !!dataset
  ) {
    console.log('Transforming');
    updateTransformations();
  } else if (!!$data && !!$data['data']) {
    console.log('Updating data');
    dataset = new Dataset($data, 'color', 3);
    if (!!$frameTransformations && $frameTransformations.length > 0)
      updateTransformations(false);
  } else {
    dataset = null;
  }

  function updateTransformations(animate = true) {
    dataset.transform($frameTransformations);
    if (!!canvas && animate) {
      console.log('Updating frame', $currentFrame);
      canvas.updateFrame($currentFrame);
    }
  }

  $: onMount(() => {
    // This logs if the widget is initialized successfully
    console.log('Mounted DR widget successfully');
  });

  let canvas;

  let alignedIDs = syncValue(model, 'alignedIDs', []);

  let thumbnailID = null;
  let thumbnailNeighbors = [];
  let previewThumbnailID = null;
  let previewThumbnailMessage = '';
  let previewThumbnailNeighbors = [];

  let currentFrame = syncValue(model, 'currentFrame', 0);
  let previewFrame = -1;

  function updateThumbnailID(id) {
    thumbnailID = id;
    if (
      thumbnailID != null &&
      dataset.atFrame(thumbnailID, $currentFrame) != null
    ) {
      thumbnailNeighbors = dataset.atFrame(thumbnailID, $currentFrame)
        .highlightIndexes;
    } else {
      thumbnailNeighbors = [];
    }
  }

  function updatePreviewThumbnailID() {
    if (previewFrame == -1) {
      previewThumbnailID = null;
      previewThumbnailMessage = '';
      previewThumbnailNeighbors = [];
    } else if (
      thumbnailID != null &&
      dataset.atFrame(thumbnailID, previewFrame) != null
    ) {
      previewThumbnailID = thumbnailID;
      previewThumbnailNeighbors = dataset.atFrame(thumbnailID, previewFrame)
        .highlightIndexes;
    } else {
      previewThumbnailID = null;
      if (thumbnailID != null)
        previewThumbnailMessage =
          'The selected point is not present in the preview';
      previewThumbnailNeighbors = [];
    }
  }

  function onScatterplotHover(e) {
    updateThumbnailID(e.detail != null ? e.detail : canvas.clickedID || null);
  }

  function onScatterplotClick(e) {
    if (e.detail.length > 0) {
      $alignedIDs = e.detail;
    }

    if (e.detail.length != 1) updateThumbnailID(null);
    else updateThumbnailID(e.detail);
  }

  function onScatterplotReset(e) {
    $alignedIDs = [];
  }

  let oldFrame = 0;
  $: if (oldFrame != $currentFrame) {
    updateThumbnailID(thumbnailID);
    oldFrame = $currentFrame;
  }

  let oldPreviewFrame = -1;

  $: if (oldPreviewFrame != previewFrame) {
    updatePreviewThumbnailID();
    oldPreviewFrame = previewFrame;
  }

  let spinner;
  $: if (!!spinner && dataset != null) {
    console.log('Updating spinner colors', dataset.frameColors);
    setTimeout(() => {
      spinner.setColors(
        d3.range(dataset.frameCount).map((f) => ({
          hue: dataset.frameColors[f][0],
          saturation: dataset.frameColors[f][1],
          lightness: dataset.frameColors[f][2],
        })),
        true
      );
    }, 0);
  }
</script>

{#if $isLoading}
  <div class="text-center">
    Loading {#if $loadingMessage.length > 0} ({$loadingMessage}){/if}...
    <i class="text-primary fa fa-spinner fa-spin" />
  </div>
{:else}
  <div style="display: flex; align-items: flex-end;">
    <div class="scatterplot-container">
      <SynchronizedScatterplot
        bind:this={canvas}
        data={dataset}
        padding={$plotPadding}
        frame={$currentFrame}
        {previewFrame}
        hoverable
        animateTransitions
        width={600}
        height={600}
        on:datahover={onScatterplotHover}
        on:dataclick={onScatterplotClick}
        on:reset={onScatterplotReset}
        colorScheme={{
          name: 'tableau',
          value: d3.schemeTableau10,
          type: 'categorical',
        }}
      />
    </div>
    <div class="spinner-container">
      <SpinnerButton
        bind:this={spinner}
        width={120}
        height={120}
        selectedIndex={$currentFrame}
        on:hover={(e) => (previewFrame = e.detail != null ? e.detail : -1)}
        on:select={(e) => ($currentFrame = e.detail)}
      />
    </div>
  </div>
{/if}

<style>
  .scatterplot-container {
    width: 600px;
    height: 600px;
    border: 1px solid #444;
  }
  .spinner-container {
    padding-left: 16px;
  }
</style>
