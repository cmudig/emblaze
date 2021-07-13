<script>
  import SynchronizedScatterplot from './visualization/SynchronizedScatterplot.svelte';
  import ScatterplotThumbnail from './visualization/components/ScatterplotThumbnail.svelte';
  import SpinnerButton from './visualization/components/SpinnerButton.svelte';
  import * as d3 from 'd3';
  import ColorSchemes from './colorschemes';

  export let model;

  // Creates a Svelte store (https://svelte.dev/tutorial/writable-stores) that syncs with the named Traitlet in widget.ts and example.py.
  import { syncValue } from './stores';
  import { Dataset } from './visualization/models/dataset.js';
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  import { fade } from 'svelte/transition';
  import ImageThumbnailViewer from './visualization/components/ImageThumbnailViewer.svelte';
  import TextThumbnailViewer from './visualization/components/TextThumbnailViewer.svelte';
  import Legend from './visualization/components/Legend.svelte';
  import Autocomplete from './visualization/components/Autocomplete.svelte';

  let data = syncValue(model, 'data', {});
  let isLoading = syncValue(model, 'isLoading', true);
  let loadingMessage = syncValue(model, 'loadingMessage', '');

  let plotPadding = syncValue(model, 'plotPadding', 10.0);
  let height = 600; // can make this reactive later

  let dataset = null;
  let frameTransformations = syncValue(model, 'frameTransformations', []);
  let frameColors = syncValue(model, 'frameColors', []);
  let thumbnailData = syncValue(model, 'thumbnailData', {});

  let colorScheme = syncValue(model, 'colorScheme', 'tableau');
  let colorSchemeObject = ColorSchemes.getColorScheme($colorScheme);
  $: {
    let newScheme = ColorSchemes.getColorScheme($colorScheme);
    console.log('New color scheme:', newScheme, colorSchemeObject);
    if (!!newScheme) colorSchemeObject = newScheme;
  }

  $: if (
    !!$frameTransformations &&
    $frameTransformations.length > 0 &&
    !!dataset
  ) {
    console.log('Transforming', $frameTransformations);
    updateTransformations();
  }

  $: updateDataset($data);

  function updateDataset(rawData) {
    if (!!rawData && !!rawData['data']) {
      dataset = new Dataset(rawData, 'color', 3);
      if (!!$frameTransformations && $frameTransformations.length > 0)
        updateTransformations(false);
    } else {
      dataset = null;
    }
  }

  function updateTransformations(animate = true) {
    dataset.transform($frameTransformations);
    if (!!canvas && animate) {
      console.log('Updating frame', $currentFrame);
      canvas.animateDatasetUpdate();
    }
  }

  $: onMount(() => {
    // This logs if the widget is initialized successfully
    console.log('Mounted DR widget successfully');
  });

  let canvas;

  let selectedIDs = syncValue(model, 'selectedIDs', []);
  $: console.log($selectedIDs);

  let alignedIDs = syncValue(model, 'alignedIDs', []);

  let thumbnailIDs = [];
  let thumbnailHover = false;
  let thumbnailNeighbors = [];
  let previewThumbnailID = null;
  let previewThumbnailMessage = '';
  let previewThumbnailNeighbors = [];

  let currentFrame = syncValue(model, 'currentFrame', 0);
  let previewFrame = -1;

  function updatePreviewThumbnailID() {
    if (previewFrame == -1) {
      previewThumbnailID = null;
      previewThumbnailMessage = '';
      previewThumbnailNeighbors = [];
    } else if (
      thumbnailID != null &&
      dataset.frame(previewFrame).has(thumbnailID)
    ) {
      previewThumbnailID = thumbnailID;
      previewThumbnailNeighbors = dataset
        .frame(previewFrame)
        .get(thumbnailID, 'highlightIndexes');
    } else {
      previewThumbnailID = null;
      if (thumbnailID != null)
        previewThumbnailMessage =
          'The selected point is not present in the preview';
      previewThumbnailNeighbors = [];
    }
  }

  function onScatterplotHover(e) {
    if (e.detail != null) {
      thumbnailIDs = [e.detail];
      thumbnailHover = true;
    } else {
      thumbnailIDs = $selectedIDs;
      thumbnailHover = false;
    }
  }

  $: {
    thumbnailIDs = $selectedIDs;
    thumbnailHover = false;
  }

  let oldPreviewFrame = -1;

  $: if (oldPreviewFrame != previewFrame) {
    updatePreviewThumbnailID();
    oldPreviewFrame = previewFrame;
  }

  let spinner;
  $: if (!!spinner && !!$frameColors && $frameColors.length > 0) {
    console.log('Spinner!');
    setTimeout(() => {
      spinner.setColors(
        $frameColors.map((f) => ({
          hue: f[0],
          saturation: f[1],
          lightness: f[2],
        })),
        true
      );
    }, 0);
  }

  let showLegend = false;

  // Thumbnails

  $: if (!!dataset && !!canvas) {
    if (!!$thumbnailData && !!$thumbnailData.format)
      dataset.addThumbnails($thumbnailData);
    else dataset.removeThumbnails();
    canvas.updateThumbnails();
  }

  // Autocomplete

  let pointSelectorOptions = [];

  function updatePointSelectorOptions() {
    if (dataset == null || $currentFrame < 0) return;
    let frame = dataset.frame($currentFrame);
    pointSelectorOptions = frame.getIDs().map((itemID) => {
      if (!!frame.get(itemID, 'label')) {
        return {
          value: itemID,
          text: `${itemID} - ${frame.get(itemID, 'label').text}`,
        };
      }
      return { value: itemID, text: itemID.toString() };
    });
  }

  $: if (dataset != null && $currentFrame >= 0) {
    updatePointSelectorOptions();
  }
</script>

{#if $isLoading}
  <div class="text-center">
    Loading {#if $loadingMessage.length > 0} ({$loadingMessage}){/if}...
    <i class="text-primary fa fa-spinner fa-spin" />
  </div>
{:else}
  <div class="vis-container">
    <div class="thumbnail-container">
      {#each [...d3.range(dataset.frameCount)] as i}
        <div class="thumbnail-item">
          <ScatterplotThumbnail
            on:click={() => {
              if (previewFrame == i) {
                $currentFrame = i;
                previewFrame = -1;
              } else if ($currentFrame != i) previewFrame = i;
              else if ($currentFrame == i) previewFrame = -1;
            }}
            isSelected={$currentFrame == i}
            isPreviewing={previewFrame == i && previewFrame != $currentFrame}
            colorScale={!!dataset
              ? dataset.colorScale(colorSchemeObject)
              : null}
            data={dataset}
            frame={!!dataset ? dataset.frame(i) : null}
            accentColor={!!$frameColors && $frameColors.length > i
              ? $frameColors[i]
              : null}
          />
        </div>
      {/each}
    </div>

    <div class="scatterplot">
      <div class="scatterplot-parent">
        <SynchronizedScatterplot
          bind:this={canvas}
          data={dataset}
          padding={$plotPadding}
          frame={$currentFrame}
          {previewFrame}
          hoverable
          showPreviewControls
          animateTransitions
          backgroundColor={previewFrame != $currentFrame && previewFrame != -1
            ? '#f8f8ff'
            : 'white'}
          bind:clickedIDs={$selectedIDs}
          bind:alignedIDs={$alignedIDs}
          on:datahover={onScatterplotHover}
          colorScheme={colorSchemeObject}
        />
        {#if showLegend}
          <div
            class="legend-container"
            transition:fade
            on:mouseout={() => {
              showLegend = false;
            }}
          >
            <Legend
              colorScale={!!dataset
                ? dataset.colorScale(colorSchemeObject)
                : null}
              type={colorSchemeObject.type || 'continuous'}
            />
          </div>
        {:else}
          <button
            class="btn btn-light btn-sm legend-hoverable"
            on:mouseover={() => {
              showLegend = true;
            }}>Legend</button
          >
        {/if}
      </div>
    </div>
    <div class="sidebar">
      <div class="action-toolbar">
        <Autocomplete
          placeholder="Search for a point..."
          options={pointSelectorOptions}
          fillWidth={true}
          on:change={(e) => ($selectedIDs = [e.detail])}
        />
      </div>
      {#if !!$thumbnailData}
        <div class="thumbnail-sidebar">
          {#if $thumbnailData.format == 'text_descriptions'}
            <TextThumbnailViewer
              {dataset}
              primaryTitle={thumbnailHover ? 'Hovered Point' : 'Selection'}
              frame={$currentFrame}
              diffColor="red"
              {thumbnailIDs}
              secondaryDiff={previewThumbnailNeighbors}
            />
          {/if}
        </div>
      {/if}
    </div>
    <div class="toolbar" />
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
    height: 600px;
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

  .legend-hoverable {
    position: absolute;
    bottom: 12px;
    right: 12px;
    margin-bottom: 0 !important;
  }
  .legend-container {
    position: absolute;
    bottom: 12px;
    right: 12px;
    border-radius: 4px;
    background-color: rgba(225, 225, 225, 0.8);
  }

  .sidebar {
    width: 300px;
    height: 600px;
    display: flex;
    flex-direction: column;
    margin-right: 8px;
  }

  .thumbnail-sidebar {
    border: 1px solid #bbb;
    flex-grow: 1;
  }
  .action-toolbar {
    display: flex;
    align-items: center;
    height: 48px;
    padding: 4px;
  }
</style>
