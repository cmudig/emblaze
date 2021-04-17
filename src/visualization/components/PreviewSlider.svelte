<!--An interactive custom slider that controls the progress from one frame to another-->
<script>
  import { onDestroy, onMount } from "svelte";
  import * as d3 from "d3";
  import {
    Animator,
    Attribute,
    easeInOut,
    interpolateTo,
  } from "../models/data_items";

  export let width = 200;
  export let height = 28;

  export let progress = 0.0;
  export let snapToEndpoints = false;

  export let progressAttr = new Attribute(0.0);
  export let knobColor = new Attribute({
    value: 1.0,
    transform: (val) => {
      let intVal = Math.round(val * 255);
      return `rgb(${intVal},${intVal},${intVal})`;
    },
    cache: true,
  });
  const AnimDuration = 2000;
  let timer;

  let canvas;
  let margin = 3.0;
  let radius = 0.0;
  $: radius = (height - margin * 2) / 2;

  $: if (!!canvas) draw(width, height);

  let isHovering = false;
  let oldHovering = false;
  let isClicking = false;
  let oldClicking = false;
  $: if (oldHovering != isHovering || oldClicking != isClicking) {
    let newColor = isClicking ? 0.5 : isHovering ? 0.8 : 1.0;
    knobColor.animate(new Animator(interpolateTo(newColor), 200));
    oldHovering = isHovering;
    oldClicking = isClicking;
  }

  export function draw(w, h) {
    if (!canvas) return;

    // Clear the canvas
    var context = canvas.getContext("2d");
    context.clearRect(0, 0, canvas.width, canvas.height);

    context.strokeStyle = "darkgray";
    context.lineWidth = 2.0;

    context.save();
    context.fillStyle = "lightgray";
    context.beginPath();
    context.moveTo(margin + radius, margin);
    context.lineTo(width - (margin + radius), margin);
    context.arc(
      width - (margin + radius),
      height / 2,
      radius,
      -Math.PI * 0.5,
      Math.PI * 0.5
    );
    context.lineTo(margin + radius, height - margin);
    context.arc(
      margin + radius,
      height / 2,
      radius,
      Math.PI * 0.5,
      Math.PI * 1.5
    );
    context.closePath();
    context.fill();
    context.stroke();
    context.restore();

    context.save();
    context.fillStyle = knobColor.get();
    context.beginPath();
    context.ellipse(
      margin + radius + (width - margin * 2 - radius * 2) * progressAttr.get(),
      height / 2,
      radius,
      radius,
      0,
      0,
      2 * Math.PI
    );
    context.closePath();
    context.fill();
    context.stroke();
    context.restore();
  }

  // Interaction

  let mouseDown = false;
  let clickX = 0;

  function locationWithinKnob(x, y) {
    let knobX =
      margin + radius + (width - margin * 2 - radius * 2) * progressAttr.get();
    return x >= knobX - radius && x <= knobX + radius;
  }

  function onMousedown(e) {
    mouseDown = true;
    var rect = e.target.getBoundingClientRect();
    var mouseX = e.clientX - rect.left; //x position within the element.
    var mouseY = e.clientY - rect.top; //y position within the element.
    isClicking = locationWithinKnob(mouseX, mouseY);
    if (isClicking) clickX = mouseX;
  }

  function onMouseover(e) {
    var rect = e.target.getBoundingClientRect();
    var mouseX = e.clientX - rect.left; //x position within the element.
    var mouseY = e.clientY - rect.top; //y position within the element.
    isHovering = locationWithinKnob(mouseX, mouseY);
  }

  function onMousemove(e) {
    var rect = canvas.getBoundingClientRect(); //e.target.getBoundingClientRect();
    var mouseX = e.clientX - rect.left; //x position within the element.
    var mouseY = e.clientY - rect.top; //y position within the element.
    if (mouseDown && isClicking) {
      let newProgress =
        progressAttr.get() +
        (mouseX - clickX) / (width - margin * 2 - radius * 2);
      progressAttr.set(Math.max(0.0, Math.min(1.0, newProgress)));
      clickX = mouseX;
    }

    isHovering = locationWithinKnob(mouseX, mouseY);
  }

  let isSnapping = false;

  function onMouseup() {
    if (isClicking && snapToEndpoints) {
      isSnapping = true;
      let newProgress = Math.round(progress);
      newProgress = Math.max(0.0, Math.min(1.0, newProgress));
      let duration = Math.abs(newProgress - progress) * AnimDuration;
      progressAttr.animate(
        new Animator(interpolateTo(newProgress), duration, easeInOut)
      );
    }
    mouseDown = false;
    isClicking = false;
  }

  function onMouseout() {
    isHovering = false;
  }

  // Timer and initialization

  let currentTime = 0;

  function setupTimer() {
    timer = d3.timer((elapsed) => {
      let dt = elapsed - currentTime;
      currentTime = elapsed;
      let a = progressAttr.advance(dt);
      let b = knobColor.advance(dt);
      if (a || b) {
        draw(width, height);
      }
      if (!a && isSnapping) {
        isSnapping = false;
      }
      if (Math.abs(progressAttr.get() - progress) >= 0.005) {
        progress = progressAttr.get();
      }
    });
  }

  $: if (progress != progressAttr.data() && !isSnapping) {
    let duration = Math.abs(progress - progressAttr.data()) * AnimDuration;
    progressAttr.animate(
      new Animator(interpolateTo(progress), duration, easeInOut)
    );
  }

  onMount(() => {
    var context = canvas.getContext("2d");
    context.scale(window.devicePixelRatio, window.devicePixelRatio);
    setupTimer();
  });

  onDestroy(() => {
    timer.stop();
    timer = null;
  });
</script>

<svelte:window
  on:mouseup={onMouseup}
  on:mousemove={(e) => {
    if (isClicking) {
      onMousemove(e);
    }
  }}
/>

<canvas
  bind:this={canvas}
  width={width * window.devicePixelRatio}
  height={height * window.devicePixelRatio}
  style="width: {width}px; height: {height}px;"
  on:mousedown={onMousedown}
  on:mousemove={onMousemove}
  on:mouseup={onMouseup}
  on:mouseover={onMouseover}
  on:mouseout={onMouseout}
/>
