<svelte:options accessors />

<script>
  import { onMount, createEventDispatcher, onDestroy } from "svelte";
  import { normalizeVector, scaleCanvas } from "../utils/helpers.js";
  import * as d3 from "d3";

  const dispatch = createEventDispatcher();

  let container;

  export let data = null;
  export let width = 300;
  export let height = 300;
  export let backgroundColor = "transparent";

  $: {
    // Makes sure to scale the canvas when the width/height change
    if (!!canvas) {
      scaleCanvas(canvas, width, height);
      draw();
    }
  }

  $: {
    // Draws the canvas when the data is explicitly updated
    if (!!data) {
      draw();
    }
  }

  $: {
    if (!!backgroundColor) {
      draw();
    }
  }

  const renderMargin = 50.0;

  var canvas;
  let needsDraw = false;

  // Keys are mark IDs, values are priority values
  let cachedPriorities = {};
  // Map of mark IDs to decorations
  let decorationsMap = {};
  // Array of decorations
  let drawOrder = [];

  function recomputeDrawOrder() {
    // Computes an ordering based on priority
    if (!data || data.marks.length == 0) {
      drawOrder = [];
      return;
    }
    drawOrder = Object.keys(cachedPriorities).filter(
      (id) => cachedPriorities[id] != null
    );
    drawOrder.sort((id1, id2) => cachedPriorities[id2] - cachedPriorities[id1]);
    drawOrder = drawOrder.map((id) => decorationsMap[id]);
  }

  function hasTextAtPoint(x, y, debug = false) {
    var context = canvas.node().getContext("2d");
    let color = context.getImageData(
      Math.round(x) * window.devicePixelRatio,
      Math.round(y) * window.devicePixelRatio,
      1,
      1
    ).data;
    if (debug) {
      console.log(x, y, color);
    }
    return color[3] > 0;
  }

  function _draw() {
    needsDraw = false;
    if (!data || !canvas) {
      return;
    }

    // Clear the canvas
    var context = canvas.node().getContext("2d");
    context.clearRect(0, 0, width, height);

    // Set mark priorities
    let changed = false;
    decorationsMap = {};
    let seenIDs = new Set();
    let newPriorities = {};
    data.decorations.forEach((d) => {
      if (d.type != "text") return;
      let newValue = d.attr("priority");
      let mark = d.marks[0];
      decorationsMap[mark.id] = d;
      if (newValue != cachedPriorities[mark.id]) changed = true;
      newPriorities[mark.id] = newValue;
      seenIDs.add(mark.id);
    });

    Object.keys(cachedPriorities).forEach((id) => {
      if (!seenIDs.has(id)) changed = true;
    });
    cachedPriorities = newPriorities;

    // Recompute draw order only if the priorities have changed
    if (changed) recomputeDrawOrder();

    drawOrder.forEach((d) => {
      let hoverText = d.attr("text");
      let x = d.attr("x");
      let y = d.attr("y");

      if (
        x < -renderMargin ||
        x > width + renderMargin ||
        y < -renderMargin ||
        y > height + renderMargin
      )
        return;

      if (!hoverText) return;

      context.save();
      // Draw a background below it - this also shows the bounding box of the text
      context.globalAlpha = 0.9;
      context.fillStyle = "white";
      let textWidth = context.measureText(hoverText).width;
      let fontSize = 9;
      let padding = 3;
      // Check the corners to make sure there is no text there
      let startX = x - textWidth / 2 - padding;
      let startY = y - (10 + fontSize + padding);
      if (
        hasTextAtPoint(startX, startY) ||
        hasTextAtPoint(startX + textWidth / 2 + padding, startY) ||
        hasTextAtPoint(startX + textWidth + padding * 2, startY) ||
        hasTextAtPoint(startX, startY + fontSize + padding * 2) ||
        hasTextAtPoint(
          startX + textWidth / 2 + padding,
          startY + fontSize + padding * 2
        ) ||
        hasTextAtPoint(
          startX + textWidth + padding * 2,
          startY + fontSize + padding * 2
        )
      ) {
        return;
      }
      context.fillRect(
        startX,
        startY,
        textWidth + padding * 2,
        fontSize + padding * 2
      );

      // Draw text
      context.globalAlpha = 1.0;
      context.font = `${fontSize * (d.attr("textScale") || 1.0)}pt Arial`;
      context.textAlign = "center";
      context.fillStyle = d.attr("color") || "black";
      context.fillText(hoverText, x, y - 10);
      context.restore();
    });
  }

  export function draw() {
    needsDraw = true;
  }

  function initializeCanvas(selector) {
    canvas = d3
      .select(selector)
      .append("canvas")
      .style("pointer-events", "none");
    scaleCanvas(canvas, width, height);
  }

  let timer;

  onMount(() => {
    initializeCanvas(container);

    timer = d3.timer(() => {
      if (needsDraw) _draw();
    });
  });

  onDestroy(() => {
    if (!!timer) timer.stop();
  });
</script>

<div
  bind:this={container}
  style="background-color: {backgroundColor};"
  id="hover-text-canvas-container"
/>

<style>
  #hover-text-canvas-container {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
</style>
