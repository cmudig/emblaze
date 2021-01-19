<script>
  import SynchronizedScatterplot from "./SynchronizedScatterplot.svelte";
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  export let colorScheme;
  export let data;
  export let frame;
  export let isSelected = false;

  let canvasBG = "transparent";
  let isHovering = false;
  let isClicking = false;

  $: {
    if (isClicking) {
      canvasBG = "skyblue";
    } else if (isHovering) {
      canvasBG = isSelected ? "deepskyblue" : "skyblue";
    } else {
      canvasBG = isSelected ? "deepskyblue" : "transparent";
    }
  }

  function onMouseover(obj) {
    isHovering = true;
    dispatch("mouseover");
  }

  function onMousedown(obj) {
    isClicking = true;
  }

  function onMouseup(obj) {
    isClicking = false;
  }

  function onMouseout(obj) {
    isHovering = false;
    dispatch("mouseout");
  }
</script>

<style>
  .thumbnail-container {
    width: 60px;
    display: flex;
    flex-direction: column;
    align-items: center;
    border-radius: 8px;
  }
  .thumbnail-name {
    color: #555;
    font-size: small;
    text-align: center;
    margin-bottom: 4px !important;
  }
</style>

<div
  class="thumbnail-container"
  style="background-color: {canvasBG};"
  on:mouseover={onMouseover}
  on:mousedown={onMousedown}
  on:mouseup={onMouseup}
  on:mouseout={onMouseout}>
  <SynchronizedScatterplot
    thumbnail
    on:click
    {colorScheme}
    {data}
    width={40}
    height={40}
    {frame}
    rFactor="0.05" />
  <p class="thumbnail-name">{data.frameLabels[frame]}</p>
</div>
