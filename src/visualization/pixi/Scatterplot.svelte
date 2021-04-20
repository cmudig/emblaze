<!-- A scatterplot implementation using PIXI.js. Has the same props and methods
  as canvas/Scatterplot.svelte. -->
<svelte:options accessors />

<script>
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import * as PIXI from 'pixi.js';
  import * as d3 from 'd3';
  import ScatterplotState from '../state/ScatterplotState.svelte';
  import { ColorIDMap } from '../utils/helpers';
  import ScatterplotViewportState from '../state/ScatterplotViewportState.svelte';
  import PixiScatterplot from './PixiScatterplot';
  import { PixiInMemoryLoader } from './PixiInMemoryLoader';

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

  let stateManager;
  let viewportManager;

  let colorMap = new ColorIDMap();

  let followingMarks = [];
  var marks = null;

  let pixiApp;
  let loader;
  let scatterplot;

  onMount(() => {
    PIXI.settings.FILTER_RESOLUTION = window.devicePixelRatio;
    pixiApp = new PIXI.Application({
      antialias: true,
      transparent: true,
      width: width,
      height: height,
      resolution: window.devicePixelRatio,
      sharedTicker: true,
    });
    pixiApp.renderer.gl.getExtension('OES_standard_derivatives');

    let view = pixiApp.view;
    container.appendChild(view);
    initializeMouseHandlers(view);

    window.addEventListener('resize', handleResize);
  });

  $: if (!!actualWidth && !!actualHeight && !!pixiApp && !!pixiApp.view) {
    d3.select(pixiApp.view)
      .attr('width', actualWidth * window.devicePixelRatio + 'px')
      .attr('height', actualHeight * window.devicePixelRatio + 'px')
      .style('width', actualWidth + 'px')
      .style('height', actualHeight + 'px');
    pixiApp.renderer.resize(actualWidth, actualHeight);
  }

  $: if (!!actualWidth && !!actualHeight && !!scatterplot) {
    scatterplot.setSize([actualWidth, actualHeight]);
  }

  onDestroy(() => {
    if (!!scatterplot) {
      scatterplot.destroy();
      scatterplot = null;
    }
    if (!!loader) {
      loader.destroy();
      loader = null;
    }
  });

  $: if (!!marks && !!pixiApp) {
    setupScatterplot();
  }

  $: if (!!viewportManager && !!pixiApp) {
    setupTicker();
  }

  function setupTicker() {
    pixiApp.ticker.add(() => {
      let dt = pixiApp.ticker.elapsedMS;
      if (!!viewportManager) {
        viewportAnimating = viewportManager.advance(dt);
        if (!!scatterplot)
          scatterplot.updateTransform(viewportManager.getTransformInfo());
      }
    });
  }

  function setupScatterplot() {
    if (!!scatterplot) {
      scatterplot.getElements().forEach((el) => pixiApp.stage.removeChild(el));
      scatterplot.destroy();
    }
    scatterplot = new PixiScatterplot(
      marks,
      viewportManager.getTransformInfo(),
      rFactor
    );
    scatterplot.addTo(pixiApp.stage, pixiApp.ticker, pixiApp.renderer);
    let renderMargin = 50.0;
    scatterplot.setRenderBox([
      -renderMargin,
      actualWidth + renderMargin,
      -renderMargin,
      actualHeight + renderMargin,
    ]);
    scatterplot.setSize([actualWidth, actualHeight]);
  }

  function handleResize() {
    if (!container) return;
    actualWidth = container.clientWidth;
    actualHeight = container.clientHeight;
  }

  // Texture loading (for image labels)

  export function updateThumbnails() {
    if (!scatterplot || !data) return;
    loadSpritesheets();
  }

  $: if (!!scatterplot) {
    loadSpritesheets();
  }

  function loadSpritesheets() {
    if (!!loader) {
      loader.destroy();
      scatterplot.setTextureLoader(null);
    }
    if (!data || !data.spritesheets) return;

    // All spritesheet data (JSON specs, images) are located in the
    // data.spritesheets object.
    loader = new PixiInMemoryLoader();
    let content = data.spritesheets;
    Promise.all(
      Object.keys(content).map((name) => {
        loader.add(
          name,
          content[name].spec,
          content[name].image,
          content[name].imageFormat || 'image/png'
        );
      })
    ).then(() => {
      if (!!loader)
        console.log(
          `Loaded ${Object.keys(content).length} spritesheets in-memory`
        );
      console.log(loader.resources['img_0.json'].textures);
    });
    scatterplot.setTextureLoader(loader);
  }

  // Previews

  // Interaction

  var mouseDown = false;
  var mouseMoved = true;

  var lastX = 0;
  var lastY = 0;

  function initializeMouseHandlers(view) {
    d3.select(view)
      .on('mousedown', (e) => {
        mouseDown = true;
        mouseMoved = false;
        dispatch('mousedown', e);
      })
      .on('mouseup', (e) => {
        mouseDown = false;
        lastX = 0;
        lastY = 0;
        if (!mouseMoved) {
          handleClick(e);
          dispatch('click', e);
        } else if (!!scatterplot.multiselect) {
          onMultiselect(e);
        }
        setTimeout(() => (mouseMoved = false));
        dispatch('mouseup', e);
      })
      .on('mousemove', (e) => {
        if (!thumbnail) {
          handleMouseMove(e);
        } else {
          dispatch('mousemove', e);
        }
      })
      .on('mouseout', () => {
        if (hoveredID != null) {
          hoveredID = null;
        }
      })
      .on('mousewheel', handleMouseWheel)
      .on('DOMMouseScroll', handleMouseWheel)
      .on('MozMousePixelScroll', (e) => e.preventDefault());
  }

  function getElementAtPoint(x, y) {
    if (!pixiApp) return null;

    let interactionMap = scatterplot.getInteractionMap(
      pixiApp.renderer,
      actualWidth,
      actualHeight,
      colorMap
    );
    if (!interactionMap) return null;

    return interactionMap.obj(x, y);
  }

  function handleMouseMove(event) {
    mouseMoved = true;
    var rect = event.target.getBoundingClientRect();
    var mouseX = event.clientX - rect.left; //x position within the element.
    var mouseY = event.clientY - rect.top; //y position within the element.

    if (mouseDown && !!lastX && !!lastY) {
      if (event.shiftKey || !!scatterplot.multiselect) {
        // Multiselect
        if (!scatterplot.multiselect) {
          scatterplot.startMultiselect([mouseX, mouseY]);
        } else {
          scatterplot.updateMultiselect([mouseX, mouseY]);
        }
      } else {
        var dx = mouseX - lastX; // * scaleFactor;
        var dy = mouseY - lastY; // * scaleFactor;

        viewportManager.translateBy(-dx, -dy);
      }
    } else if (!mouseDown) {
      let hoveredItem = getElementAtPoint(mouseX, mouseY);
      if (!!hoveredItem && hoveredItem.type == 'mark') {
        hoveredID = hoveredItem.id;
      } else {
        hoveredID = null;
      }
    }
    lastX = mouseX;
    lastY = mouseY;
  }

  function handleMouseWheel(event) {
    if (thumbnail) return;

    var ds;
    if (!!event.wheelDelta) {
      ds = 0.01 * event.wheelDelta;
    } else if (!!event.detail) {
      ds = -0.01 * event.detail; // untested
    }

    var rect = event.target.getBoundingClientRect();
    var mouseX = event.clientX - rect.left; //x position within the element.
    var mouseY = event.clientY - rect.top; //y position within the element.

    viewportManager.scaleBy(ds, [mouseX, mouseY]);

    event.preventDefault();
  }

  function handleClick(event) {
    if (thumbnail) return;

    scatterplot.clearInteractionMap();

    var rect = event.target.getBoundingClientRect();
    var mouseX = event.clientX - rect.left; //x position within the element.
    var mouseY = event.clientY - rect.top; //y position within the element.
    var el = getElementAtPoint(mouseX, mouseY);
    stateManager.selectElement(el, event.shiftKey);
  }

  // Selection

  var prevHoverID = null;

  $: if (prevHoverID != hoveredID) {
    dispatch('datahover', hoveredID);
    prevHoverID = hoveredID;
  }

  export function selectPoint(pointID, multi = false) {
    if (!stateManager) return;

    // This is currently redundant
    stateManager.selectElement({ type: 'mark', id: pointID }, multi);
  }

  function onMultiselect(event) {
    if (!hoverable) return;

    let map = scatterplot.makeMultiselectMap(
      pixiApp.renderer,
      actualWidth,
      actualHeight
    );

    // Find points that are in the multiselect
    clickedIDs = marks
      .filter((mark) => {
        if (mark.attr('alpha') < 0.01) return false;
        let x = Math.round(mark.attr('x'));
        let y = Math.round(mark.attr('y'));
        return map.contains(x, y);
      })
      .map((mark) => mark.id);
    dispatch('dataclick', clickedIDs);

    scatterplot.endMultiselect();
  }

  export function animateDatasetUpdate() {
    stateManager.animateDatasetUpdate();
  }

  let viewportAnimating = false;
  $: if (!!scatterplot) {
    scatterplot.setInteractionEnabled(
      !viewportAnimating && !(mouseDown && mouseMoved)
    );
  }

  // Clear interaction map when filter is changed
  let prevFilter = null;
  $: if (prevFilter !== filter) {
    if (!!scatterplot) scatterplot.clearInteractionMap();
    prevFilter = filter;
  }

  function rescale() {
    scalesNeutral = viewportManager.scalesNeutral;
  }

  export function reset() {
    viewportManager.resetAxisScales();
  }

  $: if (!!marks) {
    followingMarks = followingIDs.map((id) => marks.getMarkByID(id));
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
    colorScale={(c) => colorScale(c)}
    colorFormat="rgbArray"
    xScale={(x) => viewportManager.scaleX(x)}
    yScale={(y) => viewportManager.scaleY(y)}
    bind:marks
    bind:filter
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
    on:update={rescale}
  />
</div>

<style>
  #container {
    position: relative;
    overflow: hidden;
    transition: background-color 0.5s linear;
    border-radius: 8px;
  }
</style>
