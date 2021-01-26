<svelte:options accessors />

<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import * as d3 from 'd3';
  import D3Canvas from './D3Canvas.svelte';
  import { DatasetManager } from './data_manager.js';
  import { Scales } from './scales';
  import { fade } from 'svelte/transition';
  import Icon from 'fa-svelte';
  import { faExclamationTriangle } from '@fortawesome/free-solid-svg-icons/faExclamationTriangle';

  const dispatch = createEventDispatcher();

  let container;

  export let padding = 1.0;

  export let width = null;
  export let height = null;
  let actualWidth = null;
  let actualHeight = null;
  $: if (!!width) actualWidth = width;
  else if (!!container) actualWidth = container.clientWidth;
  $: if (!!height) actualHeight = height;
  else if (!!container) actualHeight = container.clientHeight;

  export let useHalos = false;
  export let hoverable = false;
  export let thumbnail = false;

  export let rFactor = 1.0;
  export let colorScheme = { value: d3.interpolateTurbo };
  let oldColorScheme;

  let colorScale = (c) => c;

  export let frame = 0;
  export let previewFrame = -1; // the frame to preview with translucent lines
  var prevFrame = -1;
  var prevPreviewFrame = -1;

  export let hoveredID = null;
  export let clickedID = null;

  export let data = null;
  let oldData = null;
  export let animateTransitions = false;
  var marks = null;
  let dataManager;

  let timer;
  let currentTime = 0;

  let warningMessage = '';
  $: {
    if (!data) warningMessage = '';
    else if (
      !!clickedID &&
      previewFrame >= 0 &&
      previewFrame != frame &&
      !data.atFrame(clickedID, previewFrame)
    ) {
      warningMessage =
        'The selected entity is not present in the destination frame';
    } else if (
      !!clickedID &&
      (previewFrame < 0 || previewFrame == frame) &&
      !data.atFrame(clickedID, frame)
    ) {
      warningMessage = 'The selected entity is not present in this plot';
    } else {
      warningMessage = '';
    }
  }

  // Animate point positions on different frames
  $: {
    if (!!dataManager) {
      if (prevFrame != frame) {
        updateFrame(frame);
        prevFrame = frame;
      }
    }
  }

  export function updateFrame(newFrame) {
    dataManager.setFrame(newFrame, animateTransitions);
    if (!!hoveredID && !data.atFrame(hoveredID, newFrame)) {
      hideStarGraph(hoveredID);
      hoveredID = null;
    } else if (!!hoveredID) {
      updateStarGraph(hoveredID);
    }
    if (!!clickedID && !data.atFrame(clickedID, newFrame)) {
      hideStarGraph(clickedID);
      if (isCenteredOnPoint) {
        showVicinityOfClickedPoint();
      }
    } else if (!!clickedID) {
      updateStarGraph(clickedID);
      // if (!isCenteredOnPoint) {
      //   // Re-zoom to show where points have moved
      //   showVicinityOfClickedPoint();
      // }
    }

    if (!!canvas && !animateTransitions) {
      canvas.draw();
    }
  }

  // Animate shadow lines when previewing a frame
  $: {
    if (!!dataManager) {
      if (previewFrame != prevPreviewFrame) {
        prevPreviewFrame = previewFrame;
        dataManager.previewFrame(previewFrame, animateTransitions, useHalos);
        if (!!canvas && !animateTransitions) {
          canvas.draw();
        }
      }
    }
  }

  $: if (!!canvas && (oldData != data || oldColorScheme != colorScheme)) {
    oldData = data;
    oldColorScheme = colorScheme;

    initializeDataBinding(data);
  }

  onMount(() => {
    if (animateTransitions) {
      timer = d3.timer((elapsed) => {
        let dt = elapsed - currentTime;
        if (dt >= 100) {
          console.log('Elapsed time:', dt);
        }
        currentTime = elapsed;
        let update = scales.advance(dt);
        update = (!!marks && marks.advance(dt)) || update;
        if (update) {
          canvas.draw();
        }
      });
    }

    window.addEventListener('resize', handleResize);
  });

  // Temporary initial value
  let scales = new Scales([0, 1], [0, 1], [0, 1], [0, 1]);

  var canvas;
  var hiddenCanvas; // for getting IDs

  var mouseMoveTimeout;

  function onMouseover() {
    dispatch('mouseover');
  }

  function onMousedown() {
    dispatch('mousedown');
  }

  function onMouseup() {
    dispatch('mouseup');
  }

  function onMouseout() {
    if (thumbnail) {
      dispatch('mouseout');
    } else if (hoveredID != null) {
      hoveredID = null;
      dispatch('datahover', hoveredID);
    }
  }

  function getIDAtPoint(x, y) {
    if (!dataManager) return null;

    hiddenCanvas.draw();
    var color = hiddenCanvas.getColorAtPoint(x, y);

    var colKey = 'rgb(' + color[0] + ',' + color[1] + ',' + color[2] + ')';
    return dataManager.getPointByColorID(colKey);
  }

  var prevHoverID = null;
  var prevClickedID = null;

  let starGraphs = {};

  function showStarGraph(id) {
    if (!!starGraphs[id]) {
      dataManager.highlightStarGraph(starGraphs[id]).then(
        () => {},
        () => {}
      );
    } else if (!!data.byID(id)) {
      let item = data.atFrame(id, frame);
      if (!item) return;
      let neighbors = (item.highlightIndexes || []).map((i) => '' + i);
      starGraphs[id] = dataManager.createStarGraph(id, neighbors);
      dataManager.highlightStarGraph(starGraphs[id]).then(
        () => {},
        () => {}
      );
    }
  }

  function hideStarGraph(id) {
    if (!!starGraphs[id]) {
      dataManager.unhighlightStarGraph(starGraphs[id]).then(
        () => (starGraphs[id] = undefined),
        () => {}
      );
    }
  }

  function updateStarGraph(id) {
    if (!!starGraphs[id]) {
      let item = data.atFrame(id, frame);
      if (item) {
        let neighbors = (item.highlightIndexes || []).map((i) => '' + i);
        dataManager.updateStarGraph(starGraphs[id], neighbors);
      } else {
        hideStarGraph(id);
      }
    } else {
      showStarGraph(id);
    }
  }

  $: if (prevHoverID != hoveredID && !!marks && !!data) {
    if (prevHoverID != null && prevHoverID != clickedID) {
      hideStarGraph(prevHoverID);
    }
    if (hoveredID != null) {
      showStarGraph(hoveredID);
    }
    prevHoverID = hoveredID;
  }

  $: if (prevClickedID != clickedID && !!marks && !!data) {
    if (prevClickedID != null) {
      hideStarGraph(prevClickedID);
    }
    if (clickedID != null) {
      showStarGraph(clickedID);
    }

    prevClickedID = clickedID;
  }

  export function selectPoint(pointID) {
    clickedID = pointID;
    dispatch('dataclick', clickedID);

    if (!!clickedID) {
      // Find the nearest neighbors in all frames and highlight those
      let filteredPoints = new Set([clickedID]);
      let highlightIndexes = data.byID(clickedID).highlightIndexes;
      let allNeighbors = new Set(Object.values(highlightIndexes).flat());
      // Add another round of neighbors
      allNeighbors.forEach((n) => {
        filteredPoints.add(n);
        let highlightIndexes = data.byID(n).highlightIndexes;
        Object.values(highlightIndexes)
          .flat()
          .forEach((id) => filteredPoints.add(id));
      });
      dataManager.filter(filteredPoints);

      if (isCenteredOnPoint) {
        centerOnClickedPoint();
      } else {
        showVicinityOfClickedPoint();
      }

      /*d3.range(data.frameCount).forEach((f) => {
        let neighbors = data.neighborsInFrame(clickedID, f, 25);
        neighbors.forEach((n) => filteredPoints.add(n));
        let framePt = data.atFrame(clickedID, f);
        if (!!framePt && !!framePt.highlightIndexes) {
          framePt.highlightIndexes.forEach((n) => filteredPoints.add(n));
        }
      });*/
    } else {
      dataManager.clearFilter();
      isCenteredOnPoint = false;
    }
  }

  function onMousemove(info) {
    if (!hoverable) return;

    // Get mouse positions from the main canvas.
    var e = info.detail;
    var rect = e.target.getBoundingClientRect();
    var mouseX = e.clientX - rect.left; //x position within the element.
    var mouseY = e.clientY - rect.top; //y position within the element.
    var newHoveredID = getIDAtPoint(mouseX, mouseY);

    if (newHoveredID != hoveredID) {
      hoveredID = newHoveredID;

      dispatch('datahover', hoveredID);
    }
  }

  function onClick(info) {
    if (!hoverable) return;

    // Get mouse positions from the main canvas.
    var e = info.detail;
    var rect = e.target.getBoundingClientRect();
    var mouseX = e.clientX - rect.left; //x position within the element.
    var mouseY = e.clientY - rect.top; //y position within the element.
    var idx = getIDAtPoint(mouseX, mouseY);

    selectPoint(idx);
  }

  let showResetButton = false;

  let showCenterButton = false;
  let isCenteredOnPoint = false;
  $: showCenterButton = clickedID != null;
  let centeredText = '';
  $: centeredText = getCenteredText(isCenteredOnPoint, clickedID);

  function getCenteredText(isCentered, pointID) {
    if (pointID == null || thumbnail) {
      return '';
    }
    let datapt = data.byID(pointID);
    if (!datapt) return '';
    let detailMessage = datapt.hoverText;
    if (!!detailMessage) detailMessage = ' - ' + detailMessage;
    else detailMessage = '';

    if (isCentered) {
      return `Centered on <strong>${pointID}${detailMessage}</strong>`;
    }
    return `Showing vicinity of <strong>${pointID}${detailMessage}</strong>`;
  }

  function rescale() {
    isCenteredOnPoint = false;
    if (!!dataManager && !!canvas) {
      dataManager.rescale();
      canvas.draw();
    }
  }

  function resetAxisScales() {
    selectPoint(null);
    scales.resetZoom();
    isCenteredOnPoint = false;
    if (!!dataManager && !!canvas) {
      dataManager.rescale();
      canvas.draw();
    }
  }

  function centerOnClickedPoint() {
    let datapt = data.atFrame(clickedID, frame);

    let neighbors = datapt.highlightIndexes;
    scales.centerOn(
      dataManager.marks.getMarkByID(clickedID),
      [clickedID, ...neighbors].map((pt) => dataManager.marks.getMarkByID(pt))
    );
    isCenteredOnPoint = true;
  }

  function showVicinityOfClickedPoint() {
    isCenteredOnPoint = false;

    scales.zoomTo(
      Array.from(dataManager.filterVisiblePoints).map((pt) =>
        dataManager.marks.getMarkByID(pt)
      )
    );
  }

  // Updating the data bindings
  function initializeDataBinding(data) {
    if (!data) {
      dataManager = null;
      return;
    }
    dataManager = new DatasetManager(
      data,
      // These preserve the reference to this object's scales, so the functions' behavior
      // will automatically change as the scales change
      (c) => colorScale(c),
      (x) => scales.scaleX(x),
      (y) => scales.scaleY(y),
      frame
    );
    marks = dataManager.marks;

    let colorType = colorScheme.type || 'continuous';
    if (colorType == 'categorical') {
      colorScale = d3
        .scaleOrdinal(colorScheme.value)
        .domain(data.getColorExtent(true));
    } else {
      colorScale = d3
        .scaleSequential(colorScheme.value)
        .domain(data.getColorExtent());
    }

    dispatch('colorScale', colorScale);
  }

  $: if (!!data && !!dataManager && !!canvas) initializeScales(padding);

  function initializeScales(plotPadding) {
    scales = new Scales(
      data.getXExtent(),
      data.getYExtent(),
      [canvas.margin.left, actualWidth - canvas.margin.right],
      [canvas.margin.top, actualHeight - canvas.margin.bottom],
      plotPadding
    );

    scales.onUpdate(() => {
      showResetButton = !scales.isNeutral() || clickedID != null;
    });
    canvas.draw();
  }

  function handleResize() {
    console.log('resizing');
    actualWidth = container.clientWidth;
    actualHeight = container.clientHeight;
  }
</script>

<div
  style="width: {width != null ? `${width}px` : '100%'}; height: {height != null
    ? `${height}px`
    : '100%'};"
  id="container"
  bind:this={container}
>
  <D3Canvas
    {thumbnail}
    width={actualWidth}
    height={actualHeight}
    data={marks}
    halosEnabled={useHalos}
    pan={!thumbnail}
    zoom={!thumbnail}
    {rFactor}
    on:click
    on:mousemove={onMousemove}
    on:mouseover={onMouseover}
    on:mousedown={onMousedown}
    on:mouseup={onMouseup}
    on:mouseout={onMouseout}
    on:click={onClick}
    on:scale={(e) => {
      scales.scaleBy(e.detail.ds, e.detail.centerPoint);
      rescale();
    }}
    on:translate={(e) => {
      scales.translateBy(e.detail.x, e.detail.y);
      rescale();
    }}
    bind:this={canvas}
  />
  {#if hoverable}
    <D3Canvas
      width={actualWidth}
      height={actualHeight}
      data={marks}
      bind:this={hiddenCanvas}
      {rFactor}
      hidden
    />
  {/if}
  {#if !thumbnail}
    <div id="button-panel">
      {#if showCenterButton}
        <button
          disabled={!data.atFrame(clickedID, frame)}
          type="button"
          class="btn btn-primary btn-sm"
          on:click|preventDefault={!isCenteredOnPoint
            ? centerOnClickedPoint
            : showVicinityOfClickedPoint}>
          {#if !isCenteredOnPoint}Center{:else}Vicinity{/if}</button
        >
      {/if}
      {#if showResetButton}
        <button
          type="button"
          class="btn btn-dark btn-sm"
          on:click|preventDefault={resetAxisScales}>Reset</button
        >
      {/if}
    </div>
    <div id="message-panel">
      {#if !!centeredText}
        {@html centeredText}
      {/if}
    </div>
    {#if warningMessage.length > 0}
      <div id="warning-panel">
        <Icon icon={faExclamationTriangle} />
        {warningMessage}
      </div>
    {/if}
  {/if}
</div>

<style>
  #container {
    position: relative;
    overflow: hidden;
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
</style>
