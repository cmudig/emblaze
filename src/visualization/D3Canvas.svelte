<svelte:options accessors />

<script>
  import { onMount, createEventDispatcher } from 'svelte';
  import { normalizeVector, scaleCanvas } from './helpers.js';
  import * as d3 from 'd3';

  const dispatch = createEventDispatcher();

  let container;

  export let data = null;
  export let width = 300;
  export let height = 300;
  export let hidden = false;
  export let thumbnail = false;
  export let pan = false;
  export let zoom = false;
  export let rFactor = 1.0;
  export let hiddenDim = 16.0; // The size of the target on the hidden canvas

  export let halosEnabled = true;

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

  export const margin = {
    // top: 30,
    // bottom: 50,
    // left: 50,
    // right: 30,
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
  };

  const renderMargin = 50.0;

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

  export function draw() {
    if (!data || !canvas) {
      return;
    }

    // Clear the canvas
    var context = canvas.node().getContext('2d');
    context.clearRect(0, 0, width, height);

    if (hidden) {
      context.imageSmoothingEnabled = false;
    }

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

          if (showDelta) {
            context.globalAlpha = 0.1;
            context.translate(x, y);
            let haloAngle = Math.atan2(x2 - x, y - y2);
            context.rotate(-haloAngle);
            context.beginPath();
            // Draw a semicircle and then an angular side
            let extent =
              Math.sqrt((x2 - x) * (x2 - x) + (y2 - y) * (y2 - y)) /
              (width * 0.7);
            drawOblongHalo(context, halo, extent);
            context.fill();
            context.rotate(haloAngle);
            context.translate(-x, -y);
          } else if (halo > 1.0) {
            context.beginPath();
            context.ellipse(x, y, halo, halo, 0, 0, 2 * Math.PI);
            context.fill();
          }
        } else if (!thumbnail && showDelta) {
          let lineAlpha = d.attr('lineAlpha');
          if (lineAlpha >= 0.001) {
            context.globalAlpha = lineAlpha || 0.1;
            context.beginPath();
            /*context.moveTo(x, y);
            context.lineTo(x2, y2);
            context.lineCap = "round";
            context.lineWidth = d.attr("lineWidth") || 2.0;*/
            let lineWidth = d.attr('lineWidth') * 0.3 || 2.0;
            drawWideningLine(context, x, y, x2, y2, r * 0.3, lineWidth);
            context.fillStyle = fillStyle;
            context.fill();
            // context.strokeStyle = d.attr("haloStyle");
            // context.stroke();
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
      });

      data.forEach((d) => {
        let hoverText = d.attr('hoverText');
        let x = d.attr('x');
        let y = d.attr('y');

        if (!!hoverText) {
          // Draw a background below it
          context.globalAlpha = 0.9;
          context.fillStyle = 'white';
          let textWidth = context.measureText(hoverText).width;
          let fontSize = 9;
          let padding = 3;
          context.fillRect(
            x - textWidth / 2 - padding,
            y - (10 + fontSize + padding),
            textWidth + padding * 2,
            fontSize + padding * 2
          );
          context.globalAlpha = 1.0;
          context.font = `${fontSize}pt Arial`;
          context.textAlign = 'center';
          context.fillStyle = 'black';
          context.fillText(hoverText, x, y - 10);
        }
      });
    }

    context.globalAlpha = 1.0;
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

  // Zooming and panning code from https://www.cs.colostate.edu/~anderson/newsite/javascript-zoom.html

  function handleDblClick(event) {
    /*var X = event.clientX - this.offsetLeft - this.clientLeft + this.scrollLeft; //Canvas coordinates
    var Y = event.clientY - this.offsetTop - this.clientTop + this.scrollTop;
    var x = (X / width) * widthView + xleftView; // View coordinates
    var y = (Y / height) * heightView + ytopView;

    scaleFactor *= event.shiftKey == 1 ? 1.5 : 0.5; // shrink (1.5) if shift key pressed
    

    xleftView = x - widthView / 2;
    ytopView = y - heightView / 2;

    dispatch("transform", {scale: })*/
  }

  var mouseDown = false;
  var mouseMoved = true;

  var lastX = 0;
  var lastY = 0;

  function handleMouseMove(event) {
    mouseMoved = true;
    var rect = event.target.getBoundingClientRect();
    var mouseX = event.clientX - rect.left; //x position within the element.
    var mouseY = event.clientY - rect.top; //y position within the element.

    if (mouseDown && !!lastX && !!lastY) {
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
      .on('dblclick', (e) => {
        if (zoom) {
          handleDblClick(e);
        } else {
          dispatch('dblclick', e);
        }
      })
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
          dispatch('click', e);
        }
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

  onMount(() => {
    initializeCanvas(container, []);
  });
</script>

<div bind:this={container} />
