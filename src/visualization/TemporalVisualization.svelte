<script>
  import * as d3 from 'd3';
  import Legend from './components/Legend.svelte';
  import DefaultThumbnailViewer from './components/DefaultThumbnailViewer.svelte';
  import Autocomplete from './components/Autocomplete.svelte';
  import ScatterplotThumbnail from './components/ScatterplotThumbnail.svelte';
  import SynchronizedScatterplot from './SynchronizedScatterplot.svelte';
  import { createEventDispatcher } from 'svelte';

  export let colorScheme = { name: 'turbo', value: d3.interpolateTurbo };

  const dispatch = createEventDispatcher();

  let colorScale;

  export let useHalos = false;

  export let thumbnailsURL = null;
  export let thumbnailData = null;
  let thumbnailViewer;

  export let data = null;

  export let showLegend = true;

  let selectedIDs = [];

  let alignedIDs = [];
  let alignedFrame = 0;
  // alignedFrame should match currentFrame as long as there is no current alignment
  $: if (alignedIDs.length == 0) alignedFrame = currentFrame;

  let oldAlignedIDs = [];
  $: if (alignedIDs !== oldAlignedIDs) {
    dispatch('align', { baseFrame: alignedFrame, alignedIDs });
    oldAlignedIDs = alignedIDs;
  }

  let filterIDs = [];

  let thumbnailIDs = [];
  let thumbnailHover = false;
  let thumbnailNeighbors = [];
  let previewThumbnailID = null;
  let previewThumbnailMessage = '';
  let previewThumbnailNeighbors = [];

  let currentFrame = 0;
  let previewFrame = -1;

  let canvas;

  $: if (!!data) {
    currentFrame = 0;
    previewFrame = -1;
  }

  // Thumbnails

  $: {
    thumbnailIDs = selectedIDs;
    thumbnailHover = false;
  }

  function onScatterplotHover(e) {
    if (e.detail != null) {
      thumbnailIDs = [e.detail];
      thumbnailHover = true;
    } else {
      thumbnailIDs = selectedIDs;
      thumbnailHover = false;
    }
  }

  export function updateThumbnails() {
    if (!!thumbnailViewer) thumbnailViewer.updateImageThumbnails();
  }

  // Autocomplete

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

{#if !!data}
  <div class="vis-container">
    <div class="thumbnail-container">
      {#each [...d3.range(data.frameCount)] as i}
        <div class="thumbnail-item">
          <ScatterplotThumbnail
            on:click={() => {
              if (previewFrame == i) {
                currentFrame = i;
                previewFrame = -1;
              } else if (currentFrame != i) previewFrame = i;
              else if (currentFrame == i) previewFrame = -1;
            }}
            isSelected={currentFrame == i}
            isPreviewing={previewFrame == i && previewFrame != currentFrame}
            colorScale={!!data ? data.colorScale(colorScheme) : null}
            {data}
            frame={!!data ? data.frame(i) : null}
          />
        </div>
      {/each}
    </div>

    <div class="scatterplot">
      <div class="scatterplot-parent">
        <SynchronizedScatterplot
          bind:this={canvas}
          {data}
          frame={currentFrame}
          {previewFrame}
          hoverable
          showPreviewControls
          animateTransitions
          backgroundColor={previewFrame != currentFrame && previewFrame != -1
            ? '#f8f8ff'
            : 'white'}
          bind:clickedIDs={selectedIDs}
          bind:alignedIDs
          bind:filterIDs
          on:datahover={onScatterplotHover}
          {colorScheme}
          selectionUnits={['pixels']}
        />
        {#if showLegend}
          <div class="legend-container">
            <Legend
              colorScale={!!data ? data.colorScale(colorScheme) : null}
              type={colorScheme.type || 'continuous'}
            />
          </div>
        {/if}
      </div>
    </div>
    <div class="sidebar">
      <div class="search-bar">
        <Autocomplete
          placeholder="Search for a point..."
          options={pointSelectorOptions}
          maxOptions={10}
          fillWidth={true}
          on:change={(e) => (selectedIDs = [e.detail])}
        />
      </div>
      <div class="sidebar-content">
        <DefaultThumbnailViewer
          bind:this={thumbnailViewer}
          dataset={data}
          primaryTitle={thumbnailHover ? 'Hovered Point' : 'Selection'}
          frame={currentFrame}
          {previewFrame}
          {thumbnailIDs}
        />
      </div>
    </div>
  </div>
{/if}

<style>
  .scatterplot {
    height: 100%;
    flex: 1 1;
    min-width: 0;
  }

  .scatterplot-parent {
    position: relative;
    width: 100%;
    height: 100%;
    /*border: 1px solid #bbb;*/
  }

  .vis-container {
    width: 100%;
    height: 100%;
    display: flex;
    justify-items: stretch;
    /*border: 2px solid #bbb;*/
  }

  .thumbnail-item {
    border-bottom: 1px solid #bbb;
  }

  .thumbnail-container {
    flex-shrink: 0;
    overflow-y: scroll;
    border: 1px solid #bbb;
  }

  .legend-container {
    position: absolute;
    top: 12px;
    left: 12px;
    border-radius: 4px;
    background-color: rgba(255, 255, 255, 0.8);
    pointer-events: none;
  }

  .sidebar {
    width: 300px;
    height: 100%;
    display: flex;
    flex-direction: column;
    margin-right: 8px;
    box-sizing: border-box;
  }

  .sidebar-content {
    border: 1px solid #bbb;
    flex-grow: 1;
    overflow-y: scroll;
    box-sizing: border-box;
  }
  .search-bar {
    display: flex;
    align-items: center;
    height: 44px;
    margin: 4px;
    flex: 0 0 auto;
  }
</style>
