<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { scaleCanvas } from '../utils/helpers.js';
  import * as d3 from 'd3';
  import {
    Animator,
    Attribute,
    easeInOut,
    interpolateTo,
  } from '../models/data_items.js';
  import SpinnerPointer from './SpinnerPointer.svelte';

  const dispatch = createEventDispatcher();

  let canvas;
  let hiddenCanvas;
  let needsDraw = false;

  export let width = 300;
  export let height = 300;
  export let borderColor = '#eee';

  $: {
    // Makes sure to scale the canvas when the width/height change
    if (!!canvas) {
      scaleCanvas(d3.select(canvas), width, height);
    }
    if (!!hiddenCanvas) {
      scaleCanvas(d3.select(hiddenCanvas), width, height);
    }
  }

  let colors = [];

  function makeColor(h, s, l, f, index) {
    let hue = new Attribute({ value: h });
    let saturation = new Attribute({ value: s });
    let lightness = new Attribute({ value: l });
    let fraction = new Attribute({ value: f });

    let hiddenColor = _indexToColor(index);
    colorIndexMapping[hiddenColor] = index;
    return {
      hue,
      saturation,
      lightness,
      fraction,
      rawHue: h,
      rawSaturation: s,
      rawLightness: l,
      hiddenColor,
      advance(dt) {
        let uh = hue.advance(dt);
        let us = saturation.advance(dt);
        let ul = lightness.advance(dt);
        let uf = fraction.advance(dt);
        return uh || us || ul || uf;
      },
    };
  }

  function setColorAnimating(index) {
    animatingColors.add(index);
  }

  function animateColor(
    index,
    toValues,
    save = true,
    duration = 1000,
    curve = null
  ) {
    let animate = false;
    let color = colors[index];
    if (toValues.hue != undefined) {
      animate = true;
      color.hue.animate(
        new Animator(interpolateTo(toValues.hue), duration, curve)
      );
      if (save) color.rawHue = toValues.hue;
    }
    if (toValues.saturation != undefined) {
      animate = true;
      color.saturation.animate(
        new Animator(interpolateTo(toValues.saturation), duration, curve)
      );
      if (save) color.rawSaturation = toValues.saturation;
    }
    if (toValues.lightness != undefined) {
      animate = true;
      color.lightness.animate(
        new Animator(interpolateTo(toValues.lightness), duration, curve)
      );
      if (save) color.rawLightness = toValues.lightness;
    }
    if (toValues.fraction != undefined) {
      animate = true;
      color.fraction.label = 'fraction';
      color.fraction.animate(
        new Animator(interpolateTo(toValues.fraction), duration, curve)
      );
    }
    if (animate) setColorAnimating(index);
  }

  const ColorTransition = 1000;

  // each color can contain the following attributes: hue, saturation, lightness, fraction
  export function setColors(newColors, animated = true) {
    if (animated) {
      // Update existing colors
      let commonLimit = Math.min(newColors.length, colors.length);
      d3.range(commonLimit).map((index) => {
        animateColor(
          index,
          {
            hue: newColors[index].hue,
            saturation: newColors[index].saturation,
            lightness: newColors[index].lightness,
          },
          true,
          ColorTransition,
          easeInOut
        );
      });
      let destFractions = d3
        .range(commonLimit)
        .map((index) => newColors[index].fraction || 0.0);

      if (newColors.length > colors.length) {
        // Add new colors
        d3.range(commonLimit, newColors.length).forEach((index) => {
          let color = newColors[index];
          colors = [
            ...colors,
            makeColor(
              color.hue || 0.0,
              color.saturation || 0.0,
              color.lightness || 0.0,
              0.0,
              index
            ),
          ];
          destFractions.push(color.fraction || 0.0);
        });
      } else if (newColors.length < colors.length) {
        // Remove old colors
        d3.range(commonLimit, colors.length).forEach((index) =>
          destFractions.push(0.0)
        );
        setTimeout(() => {
          colors = colors.slice(0, newColors.length);
        }, ColorTransition);
      }

      // Animate fractions
      let colorsWithFraction = destFractions
        .slice(0, newColors.length)
        .filter((f) => f > 0.0);
      let occupiedFractionAmount = colorsWithFraction.reduce(
        (curr, frac) => curr + frac,
        0.0
      );
      let defaultFraction =
        (1.0 - occupiedFractionAmount) /
        (newColors.length - colorsWithFraction.length);
      destFractions.forEach((f, i) =>
        animateColor(
          i,
          { fraction: f > 0.0 || i >= newColors.length ? f : defaultFraction },
          true,
          ColorTransition,
          easeInOut
        )
      );
    } else {
      // Calculate the amount not distributed among colors with a fraction
      let colorsWithFraction = newColors.filter((c) =>
        c.hasOwnProperty('fraction')
      );
      let occupiedFractionAmount = colorsWithFraction.reduce(
        (curr, color) => curr + color.fraction,
        0.0
      );
      let defaultFraction =
        (1.0 - occupiedFractionAmount) /
        (newColors.length - colorsWithFraction.length);
      colors = newColors.map((color, i) =>
        makeColor(
          color.hue || 0.0,
          color.saturation || 0.0,
          color.lightness || 0.0,
          color.fraction || defaultFraction,
          i
        )
      );
      needsDraw = true;
    }

    if (selectedIndex != null)
      updateInteractionColors(
        hoveredIndex,
        hoveredIndex,
        selectedIndex,
        selectedIndex
      );
  }

  $: if (!!canvas && !!colors) {
    draw(canvas);
  }

  function _createSector(context, startAngle, endAngle, radiusX, radiusY) {
    context.beginPath();
    context.moveTo(width / 2, height / 2);
    context.ellipse(
      width / 2,
      height / 2,
      radiusX,
      radiusY,
      0,
      startAngle,
      endAngle
    );
    context.lineTo(width / 2, height / 2);
  }

  export function draw(cvs, hidden = false) {
    if (!cvs) {
      return;
    }

    // Clear the canvas
    var context = cvs.getContext('2d');
    context.clearRect(0, 0, width, height);

    let margin = 3.0;

    // Draw
    let currentArcPosition = 0.0;

    colors.forEach((color, i) => {
      let arcAngle = color.fraction.get() * 2 * Math.PI;
      _createSector(
        context,
        currentArcPosition,
        currentArcPosition + arcAngle,
        width / 2 - margin,
        height / 2 - margin
      );
      if (hidden) {
        context.fillStyle = _indexToColor(i);
        context.fill();
      } else {
        let h = color.hue.get();
        let s = color.saturation.get();
        let l = color.lightness.get();

        context.fillStyle = `hsl(${h}, ${s}%, ${l}%)`;
        context.fill();

        context.strokeStyle = borderColor;
        context.lineWidth = 3.0;
        context.stroke();
      }
      currentArcPosition += arcAngle;
    });

    if (!hidden) {
      currentArcPosition = 0.0;
      colors.forEach((color, i) => {
        let arcAngle = color.fraction.get() * 2 * Math.PI;
        _createSector(
          context,
          currentArcPosition,
          currentArcPosition + arcAngle,
          width / 2 - margin,
          height / 2 - margin
        );
        currentArcPosition += arcAngle;

        if (selectedIndex == i) {
          context.strokeStyle = '#999';
          context.lineWidth = 2.0;
        } else if (hoveredIndex == i) {
          context.strokeStyle = '#ddd';
          context.lineWidth = 2.0;
        } else {
          return;
        }
        context.stroke();
      });
    }
  }

  let colorIndexMapping = {};

  const COLOR_INDEX_FACTOR = 90;
  function _indexToColor(index) {
    return (
      '#' +
      ('000000' + (index * COLOR_INDEX_FACTOR).toString(16)).slice(-6) +
      'ff'
    );
  }

  function _colorToHex(color) {
    let num =
      color[0] * 0x01000000 +
      color[1] * 0x010000 +
      color[2] * 0x0100 +
      color[3];
    return '#' + ('00000000' + num.toString(16)).slice(-8);
  }

  const HoverTransitionDuration = 200;

  function getIDAtPoint(x, y) {
    draw(hiddenCanvas, true);
    var context = hiddenCanvas.getContext('2d');
    let color = context.getImageData(
      x * window.devicePixelRatio,
      y * window.devicePixelRatio,
      1,
      1
    ).data;

    let idx = colorIndexMapping[_colorToHex(color)];
    if (idx == undefined) idx = null;
    return idx;
  }

  // Interaction

  let hoveredIndex = null;
  let oldHoveredIndex = null;
  export let selectedIndex = null;
  let oldSelectedIndex = null;
  let pointerAngle = 0.0;

  $: if (
    (hoveredIndex != oldHoveredIndex || selectedIndex != oldSelectedIndex) &&
    colors.length > 0
  ) {
    updateInteractionColors(
      oldHoveredIndex,
      hoveredIndex,
      oldSelectedIndex,
      selectedIndex
    );
    if (selectedIndex != null) {
      updatePointerAngle();
    }
    oldHoveredIndex = hoveredIndex;
    oldSelectedIndex = selectedIndex;
  }

  function updatePointerAngle() {
    pointerAngle =
      (colors
        .slice(0, selectedIndex)
        .reduce((total, curr) => total + curr.fraction.get(), 0.0) +
        colors[selectedIndex].fraction.get() / 2.0) *
      2.0 *
      Math.PI;
  }

  function updateInteractionColors(oldHover, newHover, oldClick, newClick) {
    /*let updates = {};
    if (oldHover != null) {
      updates[oldHover] = { lightness: colors[oldHover].rawLightness };
    }
    if (oldClick != null) {
      updates[oldClick] = { lightness: colors[oldClick].rawLightness };
    }
    if (newHover != null) {
      updates[newHover] = { lightness: colors[newHover].rawLightness * 0.8 };
    }
    if (newClick != null) {
      updates[newClick] = {
        lightness: colors[newClick].rawLightness * 0.6,
      };
    }
    Object.keys(updates).forEach((index) =>
      animateColor(
        index,
        updates[index],
        false,
        HoverTransitionDuration,
        easeInOut
      )
    );*/
    needsDraw = true;
  }

  function onMousemove(e) {
    var rect = e.target.getBoundingClientRect();
    var x = e.clientX - rect.left; //x position within the element.
    var y = e.clientY - rect.top; //y position within the element.
    hoveredIndex = getIDAtPoint(x, y);
    dispatch('hover', hoveredIndex);
  }

  function onMouseout(e) {
    hoveredIndex = null;
    dispatch('hover', hoveredIndex);
  }

  function onClick(e) {
    var rect = e.target.getBoundingClientRect();
    var x = e.clientX - rect.left; //x position within the element.
    var y = e.clientY - rect.top; //y position within the element.
    selectedIndex = getIDAtPoint(x, y);
    if (selectedIndex != null) dispatch('select', selectedIndex);
  }

  // Run loop

  let timer;
  let currentTime = 0;
  let animatingColors = new Set();

  onMount(() => {
    colors = [
      makeColor(0, 60, 70, 0.33333, 0),
      makeColor(160, 60, 70, 0.33333, 1),
      makeColor(180, 50, 60, 0.33333, 2),
    ];

    timer = d3.timer((elapsed) => {
      let dt = elapsed - currentTime;
      currentTime = elapsed;
      for (let colorIdx of animatingColors) {
        if (colorIdx >= colors.length || !colors[colorIdx].advance(dt)) {
          animatingColors.delete(colorIdx);
        }
      }
      if (animatingColors.size > 0 || needsDraw) {
        draw(canvas);
        updatePointerAngle();
        needsDraw = false;
      }
    });
  });

  onDestroy(() => {
    if (!!timer) {
      timer.stop();
      timer = null;
    }
  });
</script>

<div style="width: {width}px; height: {height}px;">
  <div class="spinner-container">
    <canvas
      bind:this={canvas}
      on:mousemove={onMousemove}
      on:mouseout={onMouseout}
      on:click={onClick}
      class="spinner-canvas"
    />
    <canvas
      bind:this={hiddenCanvas}
      style="display: none;"
      class="spinner-canvas"
    />
    <SpinnerPointer length={width * 0.4} angle={pointerAngle} />
  </div>
</div>

<style>
  .spinner-container {
    position: relative;
    width: 100%;
    height: 100%;
  }

  .spinner-canvas {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
  }
</style>
