<script>
  import * as d3 from 'd3';
  import SynchronizedScatterplot from './SynchronizedScatterplot.svelte';
  import DefaultThumbnailViewer from './components/DefaultThumbnailViewer.svelte';
  import Legend from './components/Legend.svelte';
  import Autocomplete from './components/Autocomplete.svelte';

  export let colorScheme = { name: 'turbo', value: d3.interpolateTurbo };

  let colorScale;

  export let useHalos = false;

  export let thumbnailsURL = null;
  export let thumbnailData = null;
  let thumbnailViewer;
  let thumbnailID = null;
  let thumbnailNeighbors = [];

  let previousClickedID = null;
  let previousClickedFrame = null;

  export let data = null;

  let selectedIDs = [];
  let hoveredID = null;

  let canvases = [];

  export function updateThumbnails() {
    canvases.forEach((c) => c.updateThumbnails());
    if (!!thumbnailViewer) thumbnailViewer.updateImageThumbnails();
  }

  function updateThumbnailID(id, frame) {
    thumbnailID = id;
    if (thumbnailID != null && data.atFrame(thumbnailID, frame) != null) {
      thumbnailNeighbors = data.atFrame(thumbnailID, frame).highlightIndexes;
    } else {
      thumbnailNeighbors = [];
    }
  }

  function onScatterplotHover(e, frame) {
    if (e.detail != null) updateThumbnailID(e.detail, frame);
    else if (!!previousClickedID)
      updateThumbnailID(previousClickedID, previousClickedFrame);
    else updateThumbnailID(null, null);
  }

  function onScatterplotClick(e, frame) {
    if (e.detail.length == 1) {
      previousClickedID = e.detail;
      previousClickedFrame = frame;
    } else {
      previousClickedID = null;
      previousClickedFrame = null;
    }
    updateThumbnailID(previousClickedID, previousClickedFrame);
  }

  let pointSelectorOptions = [];

  function updatePointSelectorOptions() {
    if (data == null) return;
    pointSelectorOptions = Object.keys(data.frame(0)).map((itemID) => {
      if (
        !!thumbnailData &&
        thumbnailData.format == 'text_descriptions' &&
        !!thumbnailData.items[itemID]
      ) {
        return {
          value: itemID,
          text: `${itemID} - ${thumbnailData.items[itemID].name}`,
        };
      }
      return { value: itemID, text: itemID };
    });
  }

  $: if (data != null) {
    updatePointSelectorOptions();
  }

  function selectPoint(pointID) {
    selectedIDs = [pointID];
  }

  function resetAll() {
    canvases.forEach((c) => c.resetAxisScales());
  }

  function centerAll() {
    canvases.forEach((c) => c.centerOnClickedPoint());
  }

  function vicinityAll() {
    canvases.forEach((c) => c.showVicinityOfClickedPoint());
  }

  export function animateDatasetUpdate() {
    canvases.forEach((c) => c.animateDatasetUpdate());
  }
</script>

<div>
  <Autocomplete
    options={pointSelectorOptions}
    on:change={(e) => selectPoint(e.detail)}
  />
  <div style="display: flex">
    <div style="display: flex; flex-grow: 1; flex-wrap: wrap;">
      {#if !!data}
        {#each d3.range(data.frameCount) as frame}
          <div class="scatterplot">
            <SynchronizedScatterplot
              bind:this={canvases[frame]}
              {data}
              width={400}
              height={400}
              hoverable
              {colorScheme}
              {frame}
              animateTransitions
              bind:clickedIDs={selectedIDs}
              on:colorScale={(e) => (colorScale = e.detail)}
              on:datahover={(e) => onScatterplotHover(e, frame)}
              on:dataclick={(e) => onScatterplotClick(e, frame)}
              on:reset={resetAll}
              on:center={centerAll}
              on:vicinity={vicinityAll}
              on:align
            />
          </div>
        {/each}
      {/if}
    </div>
    {#if !!thumbnailData}
      <div style="flex: 0 0 auto;">
        <DefaultThumbnailViewer
          bind:this={thumbnailViewer}
          dataset={data}
          width={200}
          height={600}
          frame={0}
          thumbnailIDs={[thumbnailID]}
        />
      </div>
    {/if}
  </div>

  <Legend {colorScale} type={colorScheme.type || 'continuous'} />
</div>

<style>
  .scatterplot {
    margin: 8px;
  }
</style>
