<!-- A scatterplot implementation using PIXI.js. Has the same props and methods
  as canvas/Scatterplot.svelte. -->
<svelte:options accessors />

<script>
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import * as PIXI from 'pixi.js';
  import * as d3 from 'd3';
  import ScatterplotState from '../state/ScatterplotState.svelte';
  import { ColorIDMap, euclideanDistance } from '../utils/helpers';
  import ScatterplotViewportState from '../state/ScatterplotViewportState.svelte';
  import PixiScatterplot from './PixiScatterplot';
  import { PixiInMemoryLoader } from './PixiInMemoryLoader';
  import Scatterplot from '../canvas/Scatterplot.svelte';

  export let padding = 0.3;

  export let width = null;
  export let height = null;

  export let hoverable = false;
  export let thumbnail = false;

  export let pointRadius = 3.0;
  let rFactor = 1.0;
  export let colorScale = (c) => c;

  export let frame = null;
  export let previewFrame = null; // the frame to preview with translucent lines
  export let previewInfo = null;
  export let previewProgress = 0.0;

  export let hoveredID = null;
  export let clickedIDs = [];
  export let alignedIDs = [];
  export let tentativeSelectedIDs = [];
  export let filterIDs = [];
  export let followingIDs = [];
  export let idsOfInterest = [];

  export let data = null;

  export let animateTransitions = false;
  export let scalesNeutral = true;

  export let performanceMode = true;
  let showPointBorders = true;

  export let thumbnailsURL = null;

  export let numNeighbors = 10;

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
  //export let showRadiusselect = false;
  export let inRadiusselect = false;
  export let selectionRadius = defaultRadius;
  export let selectionUnit = 'pixels'; // if not pixels, it will be passed to the selectionOrderFn
  export let selectionOrderFn = null;
  export let selectionMin = 0;
  export let selectionMax = 0;
  export let selectionStep = 1;
  let selectionOrder = null; // order of points to add to the selection, in the format [idx, distance]

  onMount(() => {
    PIXI.settings.FILTER_RESOLUTION = window.devicePixelRatio;
    console.log('on scatteprlot mount');
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

    // Read size of container when the view is fully laid out
    setTimeout(() => {
      actualWidth = container.clientWidth;
      actualHeight = container.clientHeight;
    }, 0);

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

  let oldMarks = null;
  $: if (!!marks && marks !== oldMarks) {
    oldMarks = marks;
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
    scatterplot.showPointBorders = showPointBorders;
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

  $: if (!!scatterplot) scatterplot.showPointBorders = showPointBorders;
  $: if (!!scatterplot) scatterplot.rFactor = rFactor;

  // Returns the current viewport as [min x, max x, min y, max y] in data space
  export function getViewport() {
    let transformInfo = viewportManager.getTransformInfo();
    // Invert this transform info to get the locations of the screen corners
    return [
      -transformInfo.x.b / transformInfo.x.a,
      (actualWidth - transformInfo.x.b) / transformInfo.x.a,
      -transformInfo.y.b / transformInfo.y.a,
      (actualHeight - transformInfo.y.b) / transformInfo.y.a,
    ];
  }

  // Texture loading (for image labels)

  export function updateThumbnails() {
    if (!scatterplot || !data) return;
    loadSpritesheets();
  }

  let oldScatterplot;
  $: if (!!scatterplot && scatterplot !== oldScatterplot) {
    console.log('scatterplot updating thumbnails');
    oldScatterplot = scatterplot;
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
    )
      .then(() => {
        if (!!loader)
          console.log(
            `Loaded ${Object.keys(content).length} spritesheets in-memory`
          );
      })
      .catch((e) => {
        console.error('error loading spritesheets:', e);
      });
    scatterplot.setTextureLoader(loader);
  }

  // Previews

  // Interaction

  var mouseDown = false;
  var mouseMoved = true;

  var hoveringDelayPassed = false;
  var hoveringDelayTimeout = null;
  const HoveringDelayInterval = 200;

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
          dispatch('datahover', hoveredID);
        }
      })
      .on('mouseenter', () => {
        hoveringDelayTimeout = setTimeout(
          () => (hoveringDelayPassed = true),
          HoveringDelayInterval
        );
      })
      .on('mouseleave', () => {
        hoveringDelayPassed = false;
        if (!!hoveringDelayTimeout) clearTimeout(hoveringDelayTimeout);
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
      if (event.metaKey || event.ctrlKey || !!scatterplot.multiselect) {
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
    } else if (!mouseDown && hoveringDelayPassed) {
      let hoveredItem = getElementAtPoint(mouseX, mouseY);
      if (!!hoveredItem && hoveredItem.type == 'mark') {
        // centerX = mouseX;
        // centerY = mouseY;
        hoveredID = hoveredItem.id;
        dispatch('datahover', hoveredID);
        //handleRadiusselect();
      } else {
        hoveredID = null;
        dispatch('datahover', hoveredID);
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

    if (inRadiusselect) {
      cancelRadiusSelect();
    }

    scatterplot.clearInteractionMap();

    var rect = event.target.getBoundingClientRect();
    var mouseX = event.clientX - rect.left; //x position within the element.
    var mouseY = event.clientY - rect.top; //y position within the element.

    var el = getElementAtPoint(mouseX, mouseY);
    let newSelection = stateManager.selectElement(
      el,
      event.metaKey || event.ctrlKey
    );
    if (newSelection.length > 0)
      dispatch('logEvent', { type: 'selection', source: 'click' });
    else dispatch('logEvent', { type: 'deselection', source: 'click' });
  }

  // Selection

  // var prevHoverID = null;

  // $: if (prevHoverID != hoveredID) {
  //   dispatch('datahover', hoveredID);
  //   prevHoverID = hoveredID;
  // }

  export function selectPoint(pointID, multi = false) {
    if (!stateManager) return;

    // This is currently redundant
    stateManager.selectElement({ type: 'mark', id: pointID }, multi);
  }

  function onMultiselect(event) {
    if (!hoverable) {
      return;
    }

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
    dispatch('logEvent', { type: 'selection', source: 'lasso' });

    scatterplot.endMultiselect();
  }

  export function animateDatasetUpdate() {
    stateManager.animateDatasetUpdate();
  }

  export function cancelRadiusSelect() {
    inRadiusselect = false;
    tentativeSelectedIDs = [];
    scatterplot.endRadiusSelect();
  }

  let viewportAnimating = false;
  $: if (!!scatterplot) {
    scatterplot.setInteractionEnabled(
      !viewportAnimating && !(mouseDown && mouseMoved)
    );
  }

  $: if (inRadiusselect) {
    console.log('updating selection order');
    updateSelectionOrder(selectionUnit);
  }

  $: if (!!scatterplot && !!scatterplot.radiusselect)
    scatterplot.radiusselect.visible = selectionUnit == 'pixels';

  const SelectionRadiusPadding = 10;

  async function updateSelectionOrder(unit) {
    if (unit == 'pixels') {
      if (
        !!selectionOrder &&
        selectionOrder.length > 0 &&
        tentativeSelectedIDs.length > 0
      ) {
        // size the circle to fit the last mark
        let centerMark = marks.getMarkByID(clickedIDs[0]);
        let centerLoc = { x: centerMark.attr('x'), y: centerMark.attr('y') };
        selectionRadius =
          tentativeSelectedIDs.reduce((curr, id) => {
            let mark = marks.getMarkByID(id);
            return Math.max(
              curr,
              euclideanDistance(centerLoc, {
                x: mark.attr('x'),
                y: mark.attr('y'),
              })
            );
          }, 0) + SelectionRadiusPadding;
      }
      selectionOrder = [];
    } else {
      selectionOrder = await selectionOrderFn(clickedIDs[0], selectionUnit);
      if (selectionOrder.length > 0 && tentativeSelectedIDs.length > 1) {
        // keep the circle roughly the same size
        let centerMark = marks.getMarkByID(clickedIDs[0]);
        for (let i = 0; i < selectionOrder.length; i++) {
          let mark = marks.getMarkByID(selectionOrder[i][0]);
          let dist = euclideanDistance(
            { x: centerMark.attr('x'), y: centerMark.attr('y') },
            { x: mark.attr('x'), y: mark.attr('y') }
          );
          if (dist > selectionRadius) {
            selectionRadius = selectionOrder[Math.max(i - 1, 1)][1];
            break;
          }
        }
      }
    }
    tentativeSelectedIDs = idsWithinSelectionRadius(selectionUnit);
  }

  $: if (selectionUnit != 'pixels' && selectionOrder.length > 0) {
    // set the slider to range from the closest distance that is not zero, to
    // the farthest distance
    selectionMin = selectionOrder[1][1];
    selectionMax = selectionOrder[selectionOrder.length - 1][1];
    let step = Math.min(1, (selectionMax - selectionMin) / 100);
    selectionMin = Math.floor(selectionMin / step) * step;
    selectionMax = Math.ceil(selectionMax / step) * step;
    selectionStep = Math.min(1, (selectionMax - selectionMin) / 100);
  } else {
    selectionMin = 10;
    selectionMax = 250;
    selectionStep = 1;
  }

  function idsWithinSelectionRadius(unit) {
    if (!scatterplot || !scatterplot.radiusselect) return [];
    if (unit == 'pixels') {
      return marks
        .filter((mark) => {
          if (mark.attr('alpha') < 0.01) return false;
          let x = Math.round(mark.attr('x'));
          let y = Math.round(mark.attr('y'));
          return scatterplot.radiusselect.circle.contains(x, y);
        })
        .map((mark) => mark.id);
    } else if (selectionOrder.length > 0) {
      let selection = [];
      for (let i = 0; i < selectionOrder.length; i++) {
        if (selectionOrder[i][1] > selectionRadius) break;
        selection.push(selectionOrder[i][0]);
      }
      return selection;
    }
    return [];
  }

  function endRadiusSelect() {
    clickedIDs = idsWithinSelectionRadius(selectionUnit);
    dispatch('dataclick', clickedIDs);
    dispatch('logEvent', { type: 'selection', source: 'radiusselect' });
    scatterplot.endRadiusSelect();
    tentativeSelectedIDs = [];
  }

  function autosizeRadiusSelect() {
    if (selectionUnit == 'pixels') return;

    // size the scatterplot's selection radius based on the locations of the selected points
    let centerMark = marks.getMarkByID(clickedIDs[0]);
    let centerLoc = { x: centerMark.attr('x'), y: centerMark.attr('y') };
    // max distance in pixels from the center point
    let maxDistance = tentativeSelectedIDs.reduce((curr, id) => {
      let mark = marks.getMarkByID(id);
      return Math.max(
        curr,
        euclideanDistance(centerLoc, { x: mark.attr('x'), y: mark.attr('y') })
      );
    }, 0);
    // add some padding
    scatterplot.updateRadiusSelect(maxDistance + SelectionRadiusPadding);
  }

  $: if (!!scatterplot) {
    if (inRadiusselect) {
      if (!scatterplot.radiusselect && clickedIDs.length == 1) {
        scatterplot.startRadiusSelect(clickedIDs[0], selectionRadius);
        tentativeSelectedIDs = idsWithinSelectionRadius(selectionUnit);
      }
    } else {
      if (!!scatterplot.radiusselect) {
        endRadiusSelect();
      }
    }
  }

  $: if (!!scatterplot) {
    if (inRadiusselect && !!scatterplot.radiusselect) {
      if (selectionUnit == 'pixels') {
        // we will use the scatterplot's rendering to test for point inclusion
        scatterplot.updateRadiusSelect(selectionRadius);
        tentativeSelectedIDs = idsWithinSelectionRadius(selectionUnit);
      } else if (selectionOrder.length > 0) {
        tentativeSelectedIDs = idsWithinSelectionRadius(selectionUnit);
        autosizeRadiusSelect();
      }
    }
  }

  // Clear interaction map when filter is changed
  let prevFilterIDs = null;
  $: if (prevFilterIDs !== filterIDs) {
    if (!!scatterplot) scatterplot.clearInteractionMap();
    prevFilterIDs = filterIDs;
  }

  let viewportUpdateTimeout = null;
  const ViewportUpdateInterval = 500;

  function rescale() {
    scalesNeutral = viewportManager.scalesNeutral;
    if (inRadiusselect && !!scatterplot.radiusselect) autosizeRadiusSelect();
    if (!!viewportUpdateTimeout) clearTimeout(viewportUpdateTimeout);
    viewportUpdateTimeout = setTimeout(() => {
      dispatch('viewportChanged', getViewport());
      viewportUpdateTimeout = null;
    }, ViewportUpdateInterval);
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
    {numNeighbors}
    {idsOfInterest}
    {pointRadius}
    colorScale={(c) => colorScale(c)}
    colorFormat="rgbArray"
    xScale={!!viewportManager ? (x) => viewportManager.scaleX(x) : null}
    yScale={!!viewportManager ? (y) => viewportManager.scaleY(y) : null}
    highlightFocusedPoints={!performanceMode}
    showPreviewLines={!performanceMode}
    bind:marks
    bind:filterIDs
    bind:hoveredID
    bind:selectedIDs={clickedIDs}
    bind:tentativeSelectedIDs
    bind:alignedIDs
    bind:previewProgress
    on:logEvent
  />
  <ScatterplotViewportState
    bind:this={viewportManager}
    {data}
    width={actualWidth}
    height={actualHeight}
    xExtent={!!data ? data.getXExtent() : null}
    yExtent={!!data ? data.getYExtent() : null}
    {padding}
    {thumbnail}
    {followingMarks}
    visibleIDs={filterIDs}
    {pointRadius}
    bind:rFactor
    bind:showPointBorders
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
