<script>
  import { scaleCanvas } from '../utils/helpers';
  import * as d3 from 'd3';
  import { onMount } from 'svelte';

  let canvas;
  export let length = 40;
  export let fillColor = '#333';
  export let strokeColor = '#eee';
  let width = 4;

  export let angle = 0;

  function drawPointer(context) {
    let h = length;
    let j = 0.05 * Math.sqrt(h * h - width * width);
    let theta = Math.asin(width / h);
    let s = j * Math.tan(theta);
    let sinTheta = Math.sin(theta);
    let cosTheta = Math.cos(theta);

    context.beginPath();
    context.arc(0, 0, width, theta, Math.PI - theta, 2 * Math.PI);
    context.lineTo(0, h);
    context.lineTo(width * cosTheta, width * sinTheta);
    context.fillStyle = fillColor;
    context.fill();
    context.strokeStyle = strokeColor;
    context.lineWidth = 2.0;
    context.stroke();
  }

  onMount(() => {
    scaleCanvas(d3.select(canvas), length * 2, width * 2 + 2);

    var context = canvas.getContext('2d');
    context.clearRect(0, 0, length * 2, 2 * width + 2);
    context.translate(length, width + 1);
    context.rotate(-Math.PI / 2.0);
    drawPointer(context);
  });
</script>

<div class="pointer-container">
  <canvas
    bind:this={canvas}
    style="transform: rotate({angle}rad);"
    class="pointer"
  />
</div>

<style>
  .pointer-container {
    /* position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0; */
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }

  .pointer {
    transition: transform 0.8s ease-in-out;
  }
</style>
