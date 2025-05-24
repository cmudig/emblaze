<!-- A scatterplot implementation using PIXI.js. Has the same props and methods
  as pixi/Scatterplot.svelte. -->
<svelte:options accessors />

<script>
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import * as d3 from 'd3';
  import D3Canvas from './D3Canvas.svelte';
  import LabelCanvas from './LabelCanvas.svelte';
  import ScatterplotState from '../state/ScatterplotState.svelte';
  import { ColorIDMap } from '../utils/helpers';
  import ScatterplotViewportState from '../state/ScatterplotViewportState.svelte';

  // Props

  export let padding = 0.3;

  export let width = null;
  export let height = null;

  export let hoverable = false;
  export let thumbnail = false;

  export let rFactor = 1.0;
  export let colorScale = (c) => c;

  export let frame = null;
  export let previewFrame = null; // the frame to preview with translucent lines
  export let previewInfo = null;
  export let previewProgress = 0.0;

  export let hoveredID = null;
  export let clickedIDs = [];
  export let alignedIDs = [];
  export let filter = new Set();
  export let followingIDs = [];

  export let data = null;

  export let animateTransitions = false;
  export let scalesNeutral = true;

  export let thumbnailsURL = null;

  const dispatch = createEventDispatcher();

  let container;

  let actualWidth = null;
  let actualHeight = null;
  $: if (!!width) actualWidth = width;
  else if (!!container) actualWidth = container.clientWidth;
  $: if (!!height) actualHeight = height;
  else if (!!container) actualHeight = container.clientHeight;

  // For ID mapping
  let colorMap = new ColorIDMap();

  let followingMarks = [];

  var marks = null;

  let stateManager;
  let viewportManager;

  let timer;
  let currentTime = 0;

  let oldData = null;
  let oldColorScale = null;

  $: if (!!canvas && (oldData != data || oldColorScale != colorScale)) {
    oldData = data;
    oldColorScale = colorScale;
    canvas.setFrozen(false);
  }

  onMount(() => {
    if (animateTransitions) {
      timer = d3.timer((elapsed) => {
        let dt = elapsed - currentTime;
        currentTime = elapsed;
        let update = !!viewportManager ? viewportManager.advance(dt) : false;
        update = (!!marks && marks.advance(dt)) || update;
        if (update) {
          canvas.draw();
          if (!!labelCanvas) labelCanvas.draw();
        }
      });
    }

    window.addEventListener('resize', handleResize);
  });

  onDestroy(() => {
    if (!!timer) {
      timer.stop();
      timer = null;
    }
  });

  // Draw and then destroy marks to save memory
  $: if (thumbnail && !!marks && !canvas.frozen) {
    canvas.draw(() => {
      stateManager.destroyMarks();
      canvas.setFrozen(true);
    });
  }

  var canvas;
  var hiddenCanvas; // for getting IDs
  var labelCanvas;

  // Previews

  $: if (
    previewFrame != null &&
    previewFrame !== frame &&
    previewProgress != null
  ) {
    if (!!canvas) canvas.draw();
    if (!!labelCanvas) labelCanvas.draw();
  }

  // Interaction

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

  function getElementAtPoint(x, y) {
    if (!colorMap) return null;

    var color = hiddenCanvas.getColorAtPoint(x, y);

    var colKey = 'rgb(' + color[0] + ',' + color[1] + ',' + color[2] + ')';
    return colorMap.obj(colKey);
  }

  export function selectPoint(pointID, multi = false) {
    if (!stateManager) return;

    // This is currently redundant
    stateManager.selectElement({ type: 'mark', id: pointID }, multi);
  }

  function onMousemove(info) {
    if (!hoverable) return;

    hiddenCanvas.draw();

    // Get mouse positions from the main canvas.
    var e = info.detail;
    var rect = e.target.getBoundingClientRect();
    var mouseX = e.clientX - rect.left; //x position within the element.
    var mouseY = e.clientY - rect.top; //y position within the element.
    var hoveredElement = getElementAtPoint(mouseX, mouseY);
    let newHoveredID =
      !!hoveredElement && hoveredElement.type == 'mark'
        ? hoveredElement.id
        : null;

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
    var el = getElementAtPoint(mouseX, mouseY);

    stateManager.selectElement(el, e.shiftKey);
  }

  function onMultiselect(info) {
    if (!hoverable) return;

    // Draw multiselect onto hidden canvas
    var points = info.detail;
    hiddenCanvas.isMultiselecting = true;
    hiddenCanvas.multiselectPath = points;
    hiddenCanvas.draw();

    // Find points that are in the multiselect
    clickedIDs = marks
      .filter((mark) => {
        if (mark.attr('alpha') < 0.01) return false;
        let x = Math.round(mark.attr('x'));
        let y = Math.round(mark.attr('y'));
        return hiddenCanvas.pointIsInMultiselect(x, y);
      })
      .map((mark) => mark.id);
    dispatch('dataclick', clickedIDs);

    hiddenCanvas.isMultiselecting = false;
    hiddenCanvas.multiselectPath = [];
    hiddenCanvas.draw();
  }

  export function animateDatasetUpdate() {
    stateManager.animateDatasetUpdate();
  }

  function rescale() {
    scalesNeutral = viewportManager.scalesNeutral;
    if (!!canvas) canvas.draw();
    if (!!hiddenCanvas) hiddenCanvas.draw();
  }

  export function reset() {
    viewportManager.resetAxisScales();
  }

  $: {
    followingMarks = followingIDs.map((id) => marks.getMarkByID(id));
  }

  function handleResize() {
    if (!container) return;
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
  <ScatterplotState
    bind:this={stateManager}
    {thumbnail}
    {data}
    {colorMap}
    {frame}
    {previewFrame}
    {previewInfo}
    bind:marks
    colorScale={(c) => colorScale(c)}
    xScale={(x) => viewportManager.scaleX(x)}
    yScale={(y) => viewportManager.scaleY(y)}
    bind:hoveredID
    bind:selectedIDs={clickedIDs}
    bind:alignedIDs
    bind:previewProgress
  />
  <ScatterplotViewportState
    bind:this={viewportManager}
    width={actualWidth}
    height={actualHeight}
    xExtent={!!data ? data.getXExtent() : null}
    yExtent={!!data ? data.getYExtent() : null}
    {padding}
    {followingMarks}
    {thumbnail}
    on:update={rescale}
  />
  <D3Canvas
    {thumbnail}
    width={actualWidth}
    height={actualHeight}
    data={marks}
    pan={!thumbnail}
    zoom={!thumbnail}
    {rFactor}
    backgroundColor="transparent"
    on:click
    on:mousemove={onMousemove}
    on:mouseover={onMouseover}
    on:mousedown={onMousedown}
    on:mouseup={onMouseup}
    on:mouseout={onMouseout}
    on:click={onClick}
    on:multiselect={onMultiselect}
    on:scale={(e) => {
      viewportManager.scaleBy(e.detail.ds, e.detail.centerPoint);
    }}
    on:translate={(e) => {
      viewportManager.translateBy(e.detail.x, e.detail.y);
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
    <LabelCanvas
      width={actualWidth}
      height={actualHeight}
      data={marks}
      bind:this={labelCanvas}
    />
  {/if}
</div>

<style>
  #container {
    position: relative;
    overflow: hidden;
  }
</style>
