<script>
  import * as d3 from 'd3';
  import ImageThumbnailViewer from './components/ImageThumbnailViewer.svelte';
  import Legend from './components/Legend.svelte';
  import TextThumbnailViewer from './components/TextThumbnailViewer.svelte';
  import Autocomplete from './components/Autocomplete.svelte';
  import ScatterplotThumbnail from './components/ScatterplotThumbnail.svelte';
  import SynchronizedScatterplot from './SynchronizedScatterplot.svelte';

  export let colorScheme = { name: 'turbo', value: d3.interpolateTurbo };

  let colorScale;

  export let useHalos = false;

  export let thumbnailsURL = null;
  export let thumbnailData = null;
  let thumbnailViewer;
  let thumbnailID = null;
  let thumbnailNeighbors = [];

  let previewThumbnailID = null;
  let previewThumbnailMessage = '';
  let previewThumbnailNeighbors = [];

  export let data = null;

  let currentFrame = 0;
  let previewFrame = -1;

  let canvas;

  $: if (!!data) {
    currentFrame = 0;
    previewFrame = -1;
  }

  function updateThumbnailID(id) {
    thumbnailID = id;
    if (
      thumbnailID != null &&
      data.atFrame(thumbnailID, currentFrame) != null
    ) {
      thumbnailNeighbors = data.atFrame(thumbnailID, currentFrame)
        .highlightIndexes;
    } else {
      thumbnailNeighbors = [];
    }

    updatePreviewThumbnailID();
  }

  function updatePreviewThumbnailID() {
    if (previewFrame == -1) {
      previewThumbnailID = null;
      previewThumbnailMessage = '';
      previewThumbnailNeighbors = [];
    } else if (
      thumbnailID != null &&
      data.atFrame(thumbnailID, previewFrame) != null
    ) {
      previewThumbnailID = thumbnailID;
      previewThumbnailNeighbors = data.atFrame(thumbnailID, previewFrame)
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
    if (e.detail != null) updateThumbnailID(e.detail);
    else if (canvas.clickedIDs.length == 1)
      updateThumbnailID(canvas.clickedIDs[0]);
    else updateThumbnailID(null);
  }

  function onScatterplotClick(e) {
    if (e.detail.length == 1) updateThumbnailID(e.detail);
    else updateThumbnailID(null);
  }

  let oldFrame = 0;
  $: if (oldFrame != currentFrame) {
    updateThumbnailID(thumbnailID);
    oldFrame = currentFrame;
  }

  let oldPreviewFrame = -1;

  $: if (oldPreviewFrame != previewFrame) {
    updatePreviewThumbnailID();
    oldPreviewFrame = previewFrame;
  }

  let pointSelectorOptions = [];

  function updatePointSelectorOptions() {
    if (data == null || currentFrame < 0) return;
    pointSelectorOptions = data
      .frame(currentFrame)
      .getIDs()
      .map((itemID) => {
        if (!!data.thumbnailData && !!data.thumbnailData.get(itemID, 'text')) {
          return {
            value: itemID,
            text: `${itemID} - ${data.thumbnailData.get(itemID, 'text')}`,
          };
        }
        return { value: itemID, text: itemID.toString() };
      });
  }

  $: if (data != null && currentFrame >= 0) {
    updatePointSelectorOptions();
  }

  function selectPoint(pointID) {
    canvas.selectPoint(pointID);
  }

  export function animateDatasetUpdate() {
    canvas.animateDatasetUpdate();
  }
</script>

<div>
  <Autocomplete
    options={pointSelectorOptions}
    on:change={(e) => selectPoint(e.detail)}
  />
  <div style="display: flex;">
    <div class="scatterplot">
      <SynchronizedScatterplot
        {data}
        width={700}
        height={700}
        hoverable
        {colorScheme}
        frame={currentFrame}
        {previewFrame}
        {thumbnailsURL}
        animateTransitions
        showPreviewControls
        backgroundColor={previewFrame != currentFrame && previewFrame != -1
          ? '#f8f8ff'
          : 'white'}
        bind:this={canvas}
        on:colorScale={(e) => (colorScale = e.detail)}
        on:datahover={onScatterplotHover}
        on:dataclick={onScatterplotClick}
        on:cancelPreview={() => (previewFrame = -1)}
        on:advancePreview={() => (currentFrame = previewFrame)}
        on:align
      />
    </div>

    {#if data != null}
      <div
        style="height: 700px; display: flex; flex-wrap: wrap; flex-direction: column; width: 240px;"
      >
        {#each [...d3.range(data.frameCount)] as i}
          <ScatterplotThumbnail
            on:click={() => {
              if (previewFrame == i) {
                currentFrame = i;
              } else if (currentFrame != i) previewFrame = i;
              else if (currentFrame == i) previewFrame = -1;
            }}
            isSelected={currentFrame == i}
            isPreviewing={previewFrame == i && previewFrame != currentFrame}
            colorScale={!!data ? data.colorScale(colorScheme) : null}
            {data}
            frame={!!data ? data.frame(i) : null}
          />
        {/each}
      </div>
    {/if}

    {#if !!thumbnailData}
      {#if thumbnailData.format == 'imagegrid'}
        <ImageThumbnailViewer
          bind:this={thumbnailViewer}
          {thumbnailData}
          width={200}
          height={600}
          baseURL={thumbnailsURL}
          primaryThumbnail={thumbnailID}
          secondaryThumbnails={thumbnailNeighbors}
        />
        {#if previewFrame != -1 && previewFrame != currentFrame}
          <ImageThumbnailViewer
            {thumbnailData}
            width={200}
            height={600}
            baseURL={thumbnailsURL}
            primaryTitle="Preview"
            message={previewThumbnailMessage}
            primaryThumbnail={previewThumbnailID}
            secondaryThumbnails={previewThumbnailNeighbors}
          />
        {/if}
      {:else if thumbnailData.format == 'text_descriptions'}
        <TextThumbnailViewer
          bind:this={thumbnailViewer}
          {thumbnailData}
          width={200}
          height={600}
          frame={currentFrame}
          diffColor="red"
          primaryThumbnail={thumbnailID}
          secondaryThumbnails={thumbnailNeighbors}
          secondaryDiff={previewThumbnailNeighbors}
        />
        {#if previewFrame != -1 && previewFrame != currentFrame}
          <TextThumbnailViewer
            {thumbnailData}
            width={200}
            height={600}
            primaryTitle="Preview"
            frame={previewFrame}
            diffColor="green"
            message={previewThumbnailMessage}
            primaryThumbnail={previewThumbnailID}
            secondaryThumbnails={previewThumbnailNeighbors}
            secondaryDiff={thumbnailNeighbors}
          />
        {/if}
      {/if}
    {/if}
  </div>

  <Legend {colorScale} type={colorScheme.type || 'continuous'} />
</div>

<style>
  .scatterplot {
    margin-bottom: 16px;
    margin-right: 16px;
  }
</style>
