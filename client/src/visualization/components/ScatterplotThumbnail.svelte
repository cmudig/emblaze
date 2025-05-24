<script>
  import { createEventDispatcher } from 'svelte';
  import Scatterplot from '../canvas/Scatterplot.svelte';

  const dispatch = createEventDispatcher();

  export let colorScale;
  export let data;
  export let frame;
  export let isSelected = false;
  export let isPreviewing = false;
  export let accentColor = null; // list of three values [h, s, l]

  let canvasBG = 'white';
  let isHovering = false;
  let isClicking = false;

  $: {
    if (!!accentColor) {
      let alpha = 0.4;
      if (isClicking) {
        alpha = 0.5;
      } else if (isHovering) {
        alpha = isSelected ? 0.7 : 0.4;
      } else {
        alpha = isSelected ? 0.7 : 0.0;
      }
      canvasBG = `hsla(${accentColor[0]}, ${accentColor[1]}%, ${accentColor[2]}%, ${alpha})`;
    } else {
      if (isClicking) {
        canvasBG = 'skyblue';
      } else if (isHovering) {
        canvasBG = isSelected ? 'deepskyblue' : 'skyblue';
      } else {
        canvasBG = isSelected ? 'deepskyblue' : 'white';
      }
    }
  }

  function onMouseover(obj) {
    isHovering = true;
    dispatch('mouseover');
  }

  function onMousedown(obj) {
    isClicking = true;
  }

  function onMouseup(obj) {
    isClicking = false;
  }

  function onMouseout(obj) {
    isHovering = false;
    dispatch('mouseout');
  }
</script>

<div
  class="thumbnail-container"
  class:preview-frame={isPreviewing}
  style="background-color: {canvasBG}; {!!accentColor
    ? `border-right: 6px solid hsl(${accentColor[0]}, ${accentColor[1]}%, ${accentColor[2]}%);`
    : 'border-right: 6px solid #bbb;'}"
  on:mouseover={onMouseover}
  on:mousedown={onMousedown}
  on:mouseup={onMouseup}
  on:mouseout={onMouseout}
  on:click
>
  <Scatterplot
    thumbnail
    {colorScale}
    {data}
    width={54}
    height={54}
    {frame}
    rFactor={0.1}
    padding={1.0}
  />
  <p class="thumbnail-name">{frame.title}</p>
</div>

<style>
  .thumbnail-container {
    width: 100px;
    height: 100px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  .thumbnail-name {
    color: #555;
    font-size: small;
    text-align: center;
    margin-bottom: 4px !important;
  }
  .preview-frame {
    border: 2px dashed steelblue;
  }
</style>
