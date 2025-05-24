<svelte:options accessors />

<script>
  import { onMount, createEventDispatcher, onDestroy } from 'svelte';
  import { normalizeVector, scaleCanvas } from '../utils/helpers.js';
  import * as d3 from 'd3';

  const dispatch = createEventDispatcher();

  let container;

  export let data = null;
  export let width = 300;
  export let height = 300;
  export let hidden = false;
  export let thumbnail = false;
  export let backgroundColor = 'white';
  export let pan = false;
  export let zoom = false;
  export let rFactor = 1.0;
  export let hiddenDim = 16.0; // The size of the target on the hidden canvas

  export let halosEnabled = true;

  export let needsDraw = false;
  export let frozen = false;

  let drawCompletionHandlers = [];

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
  const HiddenMultiselectColor = 'rgb(200,200,200)';

  var canvas;

  // let lastFillStyle = null;
  // let fillIndex = Math.floor(Math.random() * 100);

  // Draws vertically
  function drawOblongHalo(context, halo, normDistance) {
    normDistance = Math.min(normDistance, 0.95);
    let h = halo * (1.0 + normDistance); // The height of the pointer
    let j = (1 - normDistance) * Math.sqrt(h * h - halo * halo);
    let theta = Math.asin(halo / h);
    let s = j * Math.tan(theta);
    let sinTheta = Math.sin(theta);
    let cosTheta = Math.cos(theta);

    if (normDistance < 0.001) {
      context.ellipse(0, 0, halo, halo, 0, 2.0 * Math.PI, false);
    } else {
      context.arc(0, 0, halo, theta, Math.PI - theta, 2 * Math.PI);
      context.lineTo(-j * sinTheta, h - j * cosTheta);
      context.arc(
        0,
        h - j * cosTheta - s * sinTheta,
        s,
        Math.PI - theta,
        theta,
        true
      );
      context.lineTo(halo * cosTheta, halo * sinTheta);
    }
  }

  // Draws a line with width startWidth at (x, y) and width endWidth at (x2, y2)
  function drawWideningLine(context, x, y, x2, y2, startWidth, endWidth) {
    let start = [x, y];
    let end = [x2, y2];
    let path = [end[0] - start[0], end[1] - start[1]];
    let normal;
    if (path[1] > 0.0) normal = normalizeVector([path[1], -path[0]]);
    else normal = normalizeVector([-path[1], path[0]]);
    context.moveTo(
      start[0] - (normal[0] * startWidth) / 2,
      start[1] - (normal[1] * startWidth) / 2
    );
    context.lineTo(
      start[0] + (normal[0] * startWidth) / 2,
      start[1] + (normal[1] * startWidth) / 2
    );
    context.lineTo(
      end[0] + (normal[0] * endWidth) / 2,
      end[1] + (normal[1] * endWidth) / 2
    );
    context.lineTo(
      end[0] - (normal[0] * endWidth) / 2,
      end[1] - (normal[1] * endWidth) / 2
    );
  }

  function _draw() {
    needsDraw = false;

    if (!data || !canvas || frozen) {
      return;
    }

    // Clear the canvas
    var context = canvas.node().getContext('2d');
    context.clearRect(0, 0, width, height);

    if (hidden) {
      context.imageSmoothingEnabled = false;
    }

    // Background decorations
    let haloDecorations = data.decorations.filter((d) => d.type == 'halo');
    haloDecorations.sort((d1, d2) => d2.attr('r') - d1.attr('r'));
    haloDecorations.forEach((d, i) => {
      context.save();
      if (!hidden) {
        let alpha = d.attr('alpha');
        context.globalAlpha = alpha;
      }

      let x = d.attr('x');
      let y = d.attr('y');

      let r = d.attr('r');
      let lineWidth = d.attr('lineWidth') || 0.0;

      context.beginPath();
      context.ellipse(x, y, r, r, 0, 0, 2 * Math.PI);
      context.fillStyle = hidden ? d.attr('colorID') : d.attr('color');
      context.fill();
      if (!hidden && lineWidth > 0.001) {
        context.globalAlpha = 1.0;
        context.lineWidth = lineWidth;
        context.strokeStyle = context.fillStyle;
        context.stroke();
      }
      context.restore();
    });

    data.forEach(function (d, i) {
      let x = d.attr('x');
      let y = d.attr('y');
      let halo = d.attr('halo');
      let r = d.attr('r') * rFactor;
      let alpha = d.attr('alpha');
      let x2, y2;
      let fillStyle;

      if (alpha <= 0.001) return;

      if (
        x < -renderMargin ||
        x > width + renderMargin ||
        y < -renderMargin ||
        y > height + renderMargin
      ) {
        if (hidden) return;
        x2 = d.attr('x2');
        y2 = d.attr('y2');
        if (
          Math.max(x, x2) < -renderMargin ||
          Math.min(x, x2) > width + renderMargin ||
          Math.max(y, y2) < -renderMargin ||
          Math.min(y, y2) > height + renderMargin
        )
          return;
      } else if (!hidden) {
        x2 = d.attr('x2');
        y2 = d.attr('y2');
      }

      /*if (i == fillIndex) {
        //  && d.attr("fillStyle") != lastFillStyle) {
        console.log(d.attr("fillStyle"), d.data.fillStyle);
        lastFillStyle = d.attr("fillStyle");
      }*/

      if (!hidden) {
        context.globalAlpha = alpha;
        fillStyle = d.attr('fillStyle');
      } else {
        fillStyle = d.attr('colorID');
      }

      if (!hidden) {
        let showDelta = Math.abs(x - x2) >= 0.1 && Math.abs(y - y2) >= 0.1;
        context.fillStyle = fillStyle;
        let oldAlpha = context.globalAlpha;

        if (!thumbnail && !!halo && halosEnabled) {
          // Draw a semitransparent halo around the point

          context.globalAlpha = 0.1;
          if (showDelta) {
            context.translate(x, y);
            let haloAngle = Math.atan2(x - x2, y2 - y);
            context.rotate(haloAngle);
            context.beginPath();
            // Draw a semicircle and then an angular side
            let extent =
              Math.sqrt((x2 - x) * (x2 - x) + (y2 - y) * (y2 - y)) /
              (width * 0.7);
            drawOblongHalo(context, halo, extent);
            context.fill();
            context.rotate(-haloAngle);
            context.translate(-x, -y);
          } else if (halo > 1.0) {
            context.beginPath();
            context.ellipse(x, y, halo, halo, 0, 0, 2 * Math.PI);
            context.fill();
          }
        } else if (!thumbnail && showDelta) {
          let lineAlpha = d.attr('lineAlpha');
          if (lineAlpha >= 0.001) {
            context.save();
            context.globalAlpha = lineAlpha || 0.1;

            let previewPath = d.attr('previewPath');
            if (!!previewPath && previewPath.length > 0) {
              let previewStartIdx = Math.floor(
                d.attr('previewPathStart') * previewPath.length
              );
              let previewEndIdx = Math.floor(
                d.attr('previewPathEnd') * previewPath.length
              );

              context.beginPath();
              let lineWidth = d.attr('lineWidth') * 0.3 || 2.0;
              context.moveTo(
                previewPath[previewStartIdx][0],
                previewPath[previewStartIdx][1]
              );
              previewPath
                .slice(previewStartIdx, previewEndIdx)
                .forEach((point) => context.lineTo(point[0], point[1]));
              context.strokeStyle = fillStyle;
              context.lineWidth = lineWidth;
              context.stroke();
            } else {
              context.beginPath();
              let lineWidth = d.attr('lineWidth') * 0.3 || 2.0;
              drawWideningLine(context, x, y, x2, y2, r * 0.3, lineWidth);
              context.fillStyle = fillStyle;
              context.fill();
            }

            context.restore();
          }
        }
        context.globalAlpha = oldAlpha;
      }

      // This is really the main performance bottleneck!
      context.beginPath();
      if (hidden) {
        // Squares on integer pixel values work better to avoid color blending
        context.rect(
          Math.round(x - hiddenDim / 2.0),
          Math.round(y - hiddenDim / 2.0),
          Math.round(hiddenDim),
          Math.round(hiddenDim)
        );
        context.fillStyle = fillStyle;
        context.fill();
      } else {
        context.ellipse(x, y, r, r, 0, 0, 2 * Math.PI);
        context.globalAlpha *= 0.5;
        context.fillStyle = fillStyle;
        context.fill();
        context.globalAlpha /= 0.5;
        context.strokeStyle = fillStyle;
        context.stroke();
      }
    });

    context.globalAlpha = 1.0;

    if (!hidden) {
      data.decorations.forEach((d, i) => {
        context.save();
        let alpha = d.attr('alpha');
        context.globalAlpha = alpha;

        let x = d.attr('x');
        let y = d.attr('y');

        if (d.type == 'outline') {
          let r = d.attr('r');

          context.beginPath();
          context.ellipse(x, y, r, r, 0, 0, 2 * Math.PI);
          context.strokeStyle = d.attr('color');
          context.lineWidth = d.attr('lineWidth');
          context.stroke();
        } else if (d.type == 'line') {
          let x2 = d.attr('x2');
          let y2 = d.attr('y2');

          context.beginPath();
          context.moveTo(x, y);
          context.lineTo(x2, y2);
          context.strokeStyle = d.attr('color');
          context.lineWidth = d.attr('lineWidth');
          context.lineCap = 'round';
          context.stroke();
        }
        context.restore();
      });
    }

    if (isMultiselecting) {
      context.save();
      if (hidden) {
        // Fully opaque
        context.fillStyle = HiddenMultiselectColor;
      } else {
        context.fillStyle = '#30cdfc44';
        context.strokeStyle = '#30cdfc99';
      }

      context.beginPath();
      context.moveTo(
        multiselectPath[multiselectPath.length - 1][0],
        multiselectPath[multiselectPath.length - 1][1]
      );
      multiselectPath
        .slice()
        .reverse()
        .forEach((point) => context.lineTo(point[0], point[1]));
      context.fill();
      if (!hidden) {
        context.lineWidth = 2;
        context.setLineDash([3, 3]);
        context.stroke();
      }
      context.restore();
    }

    context.globalAlpha = 1.0;

    drawCompletionHandlers.forEach((d) => d());
    drawCompletionHandlers = [];
  }

  export function draw(oncomplete = null) {
    if (!!oncomplete) drawCompletionHandlers.push(oncomplete);

    if (hidden) _draw();
    else needsDraw = true;
  }

  export function setFrozen(val) {
    frozen = val;
    if (frozen && !!timer) timer.stop();
    else if (!frozen) setupTimer();
  }

  export function getColorAtPoint(x, y) {
    var context = canvas.node().getContext('2d');
    return context.getImageData(
      x * window.devicePixelRatio,
      y * window.devicePixelRatio,
      1,
      1
    ).data;
  }

  export function pointIsInMultiselect(x, y) {
    if (!hidden) {
      console.error('pointIsInMultiselect only works for hidden canvases');
      return false;
    }
    if (!isMultiselecting) return false;
    let color = getColorAtPoint(x, y);
    let colKey = 'rgb(' + color[0] + ',' + color[1] + ',' + color[2] + ')';
    return colKey == HiddenMultiselectColor;
  }

  var mouseDown = false;
  var mouseMoved = true;

  var lastX = 0;
  var lastY = 0;

  export var isMultiselecting = false;
  export var multiselectPath = [];

  function handleMouseMove(event) {
    mouseMoved = true;
    var rect = event.target.getBoundingClientRect();
    var mouseX = event.clientX - rect.left; //x position within the element.
    var mouseY = event.clientY - rect.top; //y position within the element.

    if (mouseDown && (event.shiftKey || isMultiselecting)) {
      isMultiselecting = true;
      multiselectPath.push([mouseX, mouseY]);
      draw();
    } else if (mouseDown && !!lastX && !!lastY) {
      var dx = mouseX - lastX; // * scaleFactor;
      var dy = mouseY - lastY; // * scaleFactor;

      dispatch('translate', {
        x: -dx,
        y: -dy,
      });
    }
    lastX = mouseX;
    lastY = mouseY;
  }

  function handleMouseWheel(event) {
    if (!zoom) return;

    var ds;
    if (!!event.wheelDelta) {
      ds = 0.01 * event.wheelDelta;
    } else if (!!event.detail) {
      ds = -0.01 * event.detail; // untested
    }

    var rect = event.target.getBoundingClientRect();
    var mouseX = event.clientX - rect.left; //x position within the element.
    var mouseY = event.clientY - rect.top; //y position within the element.

    dispatch('scale', { ds: ds, centerPoint: [mouseX, mouseY] });

    event.preventDefault();
  }

  function initializeCanvas(selector) {
    canvas = d3
      .select(selector)
      .append('canvas')
      .style('background-color', 'transparent')
      .on('mousedown', (e) => {
        mouseDown = true;
        mouseMoved = false;
        dispatch('mousedown', e);
      })
      .on('mouseup', (e) => {
        lastX = 0;
        lastY = 0;
        if (isMultiselecting) {
          dispatch('multiselect', multiselectPath);
          isMultiselecting = false;
          multiselectPath = [];
          draw();
        } else if (!mouseMoved && mouseDown) {
          dispatch('click', e);
        }
        mouseDown = false;
        setTimeout(() => (mouseMoved = false));
        dispatch('mouseup', e);
      })
      .on('mouseover', (e) => {
        dispatch('mouseover', e);
      })
      .on('mouseout', (e) => {
        dispatch('mouseout', e);
      })
      .on('mousemove', (e) => {
        if ((pan || zoom) && mouseDown) {
          handleMouseMove(e);
        } else {
          dispatch('mousemove', e);
        }
      })
      .on('mousewheel', handleMouseWheel)
      .on('DOMMouseScroll', handleMouseWheel)
      .on('MozMousePixelScroll', (e) => e.preventDefault());
    scaleCanvas(canvas, width, height);
    if (hidden) {
      canvas.style('display', 'none');
    }

    //custom = d3.select(document.createElement("custom"));

    /*initializeDataBinding(allData);
    bindData(allData);
    
    // Start draw loop
    togglePlay(null);*/
  }

  let timer;

  function setupTimer() {
    if (hidden) return;
    timer = d3.timer(() => {
      if (needsDraw) _draw();
    });
  }

  onMount(() => {
    initializeCanvas(container, []);
    setupTimer();
  });

  onDestroy(() => {
    if (!!timer) timer.stop();
  });
</script>

<div
  bind:this={container}
  style="background-color: {backgroundColor}; width: 100%; height: 100%;"
/>

<style>
  .debug {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    z-index: 10;
    pointer-events: none;
  }
</style>
