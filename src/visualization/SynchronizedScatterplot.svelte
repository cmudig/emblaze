<svelte:options accessors />

<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import * as d3 from 'd3';
  import { fade } from 'svelte/transition';
  import Icon from 'fa-svelte';
  import { faExclamationTriangle } from '@fortawesome/free-solid-svg-icons/faExclamationTriangle';
  import Scatterplot from './pixi/Scatterplot.svelte';
  import PreviewSlider from './components/PreviewSlider.svelte';
  import PixiScatterplot from './pixi/PixiScatterplot';
  const dispatch = createEventDispatcher();

  let container;

  // Props for this element
  export let backgroundColor = 'white';
  export let width = null;
  export let height = null;

  // Props passed directly to scatterplot
  export let padding = 0.3;
  export let pointRadius = 3.0;
  export let colorScheme = { value: d3.interpolateTurbo };
  export let animateTransitions = false;

  // when number of points is greater than this, performance mode will be used
  export let performanceModeThreshold = 2000;

  // Enable/disable interaction
  export let hoverable = false;
  export let thumbnail = false;

  // Frames and previews
  export let frame = 0;
  export let previewFrame = -1; // the frame to preview with translucent lines
  export let showPreviewControls = false;
  export let previewProgress = 0.0;

  // Scatterplot state
  let scalesNeutral = true;
  export let hoveredID = null;
  export let clickedIDs = [];
  export let alignedIDs = [];
  export let tentativeSelectedIDs = [];
  export let filterIDs = [];

  let followingIDs = [];

  const minSelection = 3;

  // Data control
  export let data = null;

  // Thumbnails
  export let thumbnailsURL = null;

  // Number of neighbors to display
  export let numNeighbors = 10;

  let scatterplot;
  let warningMessage = '';
  let colorScale = (c) => c;

  // Initialization

  $: if (!!data) {
    colorScale = data.colorScale(colorScheme);
  }

  // Display

  let performanceMode = false;

  $: if (!!data) {
    performanceMode =
      (filterIDs == null ||
        filterIDs.length == 0 ||
        filterIDs.length > performanceModeThreshold) &&
      data.frame(0).length > performanceModeThreshold;
  }

  // Returns the current viewport as [min x, max x, min y, max y] in data space
  export function getViewport() {
    return scatterplot.getViewport();
  }

  // Selection

  var prevClickedIDs = null;
  $: if (prevClickedIDs != clickedIDs && !!data) {
    updateSelection();
    prevClickedIDs = clickedIDs;
    dispatch('dataclick', clickedIDs);
  }

  function updateSelection() {
    if (clickedIDs.length > 0) {
      if (clickedIDs.length == 1) showVicinityOfClickedPoint();
      if (filterIDs.length > 0) filterToSelection(true);
    } else {
      followingIDs = [];
    }
  }

  export function selectPoint(pointID, multi = false) {
    if (!scatterplot) return;
    scatterplot.selectPoint(pointID, multi);
  }

  var prevAlignedIDs = null;
  $: if (prevAlignedIDs != alignedIDs && !!data) {
    dispatch('align', { alignedIDs, baseFrame: frame });
    prevAlignedIDs = alignedIDs;
  }

  // Filter button

  let showFilterButton = false;
  $: showFilterButton = clickedIDs.length > 0 || filterIDs.length > 0;

  function filterToSelection(append = false) {
    let newFilter = getFilterPoints(clickedIDs);
    if (append) {
      filterIDs.forEach((id) => newFilter.add(id));
    }
    filterIDs = Array.from(newFilter);
  }

  function getFilterPoints(selection) {
    let filteredPoints = new Set();
    selection.forEach((clickedID) => {
      filteredPoints.add(clickedID);
      data.frames.forEach((frame) => {
        let neighbors = frame.neighbors(clickedID, 10);
        neighbors.forEach((n) => filteredPoints.add(n));
        let highlight = frame
          .get(clickedID, 'highlightIndexes')
          .slice(0, numNeighbors);
        if (!!highlight) {
          highlight.forEach((n) => filteredPoints.add(n));
        }
      });
    });
    return filteredPoints;
  }

  function clearFilter() {
    filterIDs = [];
  }

  // Radius select button
  let showRadiusselectButton = false;
  $: showRadiusselectButton = clickedIDs.length == 1 && filterIDs.length == 0;

  export let inRadiusselect = false;
  const DefaultSelectionRadius = 30;
  export let selectionRadius = DefaultSelectionRadius;
  let selectionOrder = [];
  // Async function that takes a point ID and distance metric,
  // and returns a list of [id, distance] pairs in sorted order
  export let selectionOrderFn = null;
  export let selectionUnit = 'pixels';
  export let selectionUnits = ['pixels', 'cosine'];
  let selectionMin = 0;
  let selectionMax = 0;
  let selectionStep = 1;
  let selectionOrderLoading = false;

  // Reset button
  let showResetButton = false;
  $: showResetButton =
    !scalesNeutral || clickedIDs.length > 0 || alignedIDs.length > 0;

  // Align button
  export let allowAlignment = true;
  let showAlignmentButton = false;
  $: showAlignmentButton =
    allowAlignment && (clickedIDs.length > 0 || alignedIDs.length > 0);

  let alignedToSelection = false;
  $: alignedToSelection =
    alignedIDs.length > 0 &&
    JSON.stringify(alignedIDs) ==
      JSON.stringify(getVicinityOfPoints(clickedIDs));

  let alignmentText = '';
  $: alignmentText = getAlignmentText(
    alignedIDs,
    clickedIDs,
    tentativeSelectedIDs,
    alignedToSelection
  );

  function _describePoint(pointID) {
    let datapt = data.byID(pointID);
    if (!datapt) return '';
    let detailMessage = null;
    let labels = datapt.label;
    if (!!labels) {
      if (!!labels[frame]) detailMessage = labels[frame].text || null;
      else if (
        Object.keys(labels).length > 0 &&
        !!labels[Object.keys(labels)[0]]
      )
        detailMessage = labels[Object.keys(labels)[0]].text || null;
      else detailMessage = null;
    }
    if (!!detailMessage) detailMessage = ' - ' + detailMessage;
    else detailMessage = '';
    return `${pointID}${detailMessage}`;
  }

  function _othersMessage(pointIDs) {
    return pointIDs.length > 1 ? ` and ${pointIDs.length - 1} others` : '';
  }

  function getAlignmentText(
    alignPoints,
    clickPoints,
    tentativePoints,
    alignedToSelectedPoints
  ) {
    if (
      (alignPoints.length == 0 &&
        clickPoints.length == 0 &&
        tentativePoints.length == 0) ||
      thumbnail
    ) {
      return '';
    }

    if (tentativePoints.length > 0) {
      return `Selecting ${tentativePoints.length} points`;
    }

    if (clickPoints.length == 0 && alignPoints.length > 0) {
      return `Aligned to <strong>${_describePoint(
        alignPoints[0]
      )}</strong>${_othersMessage(alignPoints)}`;
    } else if (clickPoints.length > 0 && alignPoints.length == 0) {
      return `<strong>${_describePoint(
        clickPoints[0]
      )}</strong>${_othersMessage(clickPoints)} selected`;
    }

    let selectionBase =
      `<strong>${_describePoint(clickPoints[0])}</strong>` +
      `${_othersMessage(clickPoints)} selected`;
    if (alignedToSelectedPoints) return selectionBase + ' (aligned)';

    return (
      selectionBase +
      `, aligned to ${alignPoints.length} ` +
      `point${alignPoints.length > 1 ? 's' : ''}`
    );
  }

  export function animateDatasetUpdate() {
    scatterplot.animateDatasetUpdate();
  }

  export function updateThumbnails() {
    if (!!scatterplot.updateThumbnails) scatterplot.updateThumbnails();
  }

  export function reset() {
    clickedIDs = [];
    alignedIDs = [];
    followingIDs = [];
    filterIDs = [];
    scatterplot.reset();
  }

  function getVicinityOfPoints(pointIDs) {
    let vicinity;
    if (pointIDs.length >= 3) {
      // There are enough points to use them as-is
      vicinity = pointIDs;
    } else {
      // Use the neighbors to help with the alignment
      let filteredPoints = new Set(pointIDs);
      pointIDs.forEach((id) => {
        let highlightIndexes = data.byID(id).highlightIndexes;
        let allNeighbors = new Set(
          Object.values(highlightIndexes)
            .map((v) => v.slice(0, numNeighbors))
            .flat()
        );
        allNeighbors.forEach((n) => filteredPoints.add(n));
      });
      vicinity = Array.from(filteredPoints);
    }
    return vicinity;
  }

  export function showVicinityOfClickedPoint() {
    followingIDs = getVicinityOfPoints(clickedIDs);
    console.log('showing vicinity:', clickedIDs, followingIDs);
  }
</script>

<div
  style="width: {width != null ? `${width}px` : '100%'}; height: {height != null
    ? `${height}px`
    : '100%'}; background-color: {backgroundColor};"
  id="container"
  bind:this={container}
>
  <Scatterplot
    bind:this={scatterplot}
    {padding}
    {width}
    {height}
    {hoverable}
    {thumbnail}
    {pointRadius}
    {performanceMode}
    {colorScale}
    {animateTransitions}
    {thumbnailsURL}
    {numNeighbors}
    frame={!!data ? data.frame(frame) : null}
    previewFrame={!!data && previewFrame >= 0 && previewFrame != frame
      ? data.frame(previewFrame)
      : null}
    previewInfo={!!data && previewFrame >= 0 && previewFrame != frame
      ? data.previewInfo(frame, previewFrame)
      : null}
    idsOfInterest={alignedIDs.length > 0 ? getFilterPoints(alignedIDs) : []}
    bind:previewProgress
    bind:clickedIDs
    bind:hoveredID
    bind:alignedIDs
    bind:tentativeSelectedIDs
    bind:followingIDs
    bind:filterIDs
    bind:data
    bind:scalesNeutral
    bind:inRadiusselect
    bind:selectionRadius
    bind:selectionUnit
    bind:selectionMin
    bind:selectionMax
    bind:selectionStep
    selectionOrderFn={!!selectionOrderFn
      ? async (id, metric) => {
          selectionOrderLoading = true;
          let result = await selectionOrderFn(id, metric);
          selectionOrderLoading = false;
          return result;
        }
      : null}
    on:mouseover
    on:mouseout
    on:mousedown
    on:mouseup
    on:datahover
    on:dataclick
    on:click
    on:viewportChanged
    on:logEvent
  />
  {#if !thumbnail}
    <div id="button-panel">
      {#if showRadiusselectButton && !inRadiusselect}
        <button
          type="button"
          class="btn btn-primary btn-sm jp-Dialog-button jp-mod-reject jp-mod-styled"
          on:click|preventDefault={() => {
            inRadiusselect = true;
            selectionRadius = DefaultSelectionRadius;
          }}
        >
          Start Radius Select
        </button>
      {:else if showRadiusselectButton && inRadiusselect}
        {#if selectionOrderLoading}
          Loading selection metric...
        {:else}
          <input
            type="range"
            bind:value={selectionRadius}
            min={selectionMin}
            max={selectionMax}
            step={selectionStep}
          />
          {Math.round(selectionRadius * 100) / 100}
          <select bind:value={selectionUnit}>
            {#each selectionUnits as unit}
              <option value={unit}>{unit}</option>
            {/each}
          </select>
          <button
            type="button"
            class="btn btn-secondary btn-sm jp-Dialog-button jp-mod-reject jp-mod-styled"
            on:click|preventDefault={() => scatterplot.cancelRadiusSelect()}
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary btn-sm jp-Dialog-button jp-mod-accept jp-mod-styled"
            on:click|preventDefault={() => (inRadiusselect = false)}
          >
            Select
          </button>
        {/if}
      {/if}

      {#if showFilterButton && !inRadiusselect}
        <button
          type="button"
          class="btn btn-success btn-sm jp-Dialog-button jp-mod-reject jp-mod-styled"
          on:click|preventDefault={filterIDs.length > 0
            ? clearFilter
            : () => filterToSelection()}
        >
          {#if filterIDs.length > 0}
            Show All
          {:else}
            Isolate
          {/if}
        </button>
      {/if}
      {#if showAlignmentButton && !inRadiusselect}
        {#if clickedIDs.length == 0 || alignedToSelection}
          <button
            type="button"
            class="btn btn-primary btn-sm jp-Dialog-button jp-mod-reject jp-mod-styled"
            on:click|preventDefault={() => (alignedIDs = [])}
          >
            Unalign</button
          >
        {:else}
          <button
            type="button"
            class="btn btn-primary btn-sm jp-Dialog-button jp-mod-reject jp-mod-styled"
            on:click|preventDefault={clickedIDs.length >= minSelection
              ? () => (alignedIDs = getVicinityOfPoints(clickedIDs))
              : () =>
                  alert(
                    `You must select at least ${minSelection} points to align.`
                  )}
          >
            Align</button
          >
        {/if}
      {/if}
      {#if showResetButton && !inRadiusselect}
        <button
          type="button"
          class="btn btn-dark btn-sm jp-Dialog-button jp-mod-warn jp-mod-styled"
          on:click|preventDefault={(e) => {
            reset();
            dispatch('reset');
          }}>Reset</button
        >
      {/if}
    </div>
    <div id="message-panel">
      {#if !!alignmentText}
        {@html alignmentText}
        {#if alignedIDs.length > 0 && !alignedToSelection}
          - <a
            on:click|preventDefault={() => (clickedIDs = alignedIDs)}
            href="#">Select alignment anchors</a
          >
        {/if}
      {/if}
    </div>
    {#if warningMessage.length > 0}
      <div id="warning-panel">
        <Icon icon={faExclamationTriangle} />
        {warningMessage}
      </div>
    {/if}
    {#if showPreviewControls && previewFrame != frame && previewFrame != -1}
      <div id="preview-panel">
        <PreviewSlider width={240} bind:progress={previewProgress} />
      </div>
    {/if}
  {/if}
</div>

<style>
  #container {
    position: relative;
    overflow: hidden;
    transition: background-color 0.5s linear;
  }
  #button-panel {
    position: absolute;
    right: 12px;
    top: 12px;
  }
  #message-panel {
    position: absolute;
    bottom: 12px;
    left: 12px;
    font-size: small;
    color: #555;
    background-color: rgba(255, 255, 255, 0.8);
    border-radius: 4px;
  }
  #warning-panel {
    position: absolute;
    top: 12px;
    left: 12px;
    border-radius: 4px;
    padding: 6px;
    background-color: goldenrod;
    color: white;
    font-size: small;
  }
  #preview-panel {
    position: absolute;
    bottom: 0;
    right: 0;
    padding: 12px;
    font-size: small;
    color: #555;
    display: flex;
    align-items: center;
    background-color: rgba(255, 255, 255, 0.8);
    border-radius: 4px;
  }

  .jp-Dialog-button.jp-mod-styled {
    margin-right: 2px !important;
  }
</style>
