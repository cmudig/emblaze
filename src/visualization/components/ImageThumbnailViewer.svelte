<script>
  import { onMount } from "svelte";
  import * as d3 from "d3";

  export let width = 200;
  export let height = 600;

  export let baseURL = "";
  export let thumbnailData = null;
  export let primaryTitle = "Selected item";
  export let secondaryTitle = "Neighbors";
  export let primaryThumbnail = null;
  export let secondaryThumbnails = [];
  export let message = "";

  let container;
  let primaryContainer;
  let primaryImage;
  let secondaryContainer;

  let thumbnailUpdateTimer = null;

  function getThumbnailInfo(id) {
    if (!!thumbnailData) {
      return thumbnailData.items[id];
    }
    return null;
  }

  function updateSecondaryThumbnails(u) {
    secondaryContainer.selectAll("div").style("opacity", 0.0);
    if (!!thumbnailUpdateTimer) {
      clearTimeout(thumbnailUpdateTimer);
    }

    thumbnailUpdateTimer = setTimeout(() => {
      secondaryContainer
        .selectAll("div")
        .transition()
        .duration(100)
        .style("opacity", 1.0);
      thumbnailUpdateTimer = null;
    }, 200);

    let enterSel = u
      .enter()
      .append("div")
      .style("margin", "4px")
      .style("overflow", "hidden")
      .style("position", "relative");
    enterSel.append("img");
    enterSel
      .merge(u)
      .style("width", (d) => (!!d ? d.width : 0) + "px")
      .style("height", (d) => (!!d ? d.height : 0) + "px")
      .select("img")
      .style("position", "relative")
      .style("left", (d) => -d.col + "px")
      .style("top", (d) => -d.row + "px")
      .style("width", (!!thumbnailData ? thumbnailData.macroWidth : 0) + "px")
      .style("height", (!!thumbnailData ? thumbnailData.macroHeight : 0) + "px")
      .attr("src", (d) => (d ? baseURL + "/" + d.filename : ""));

    u.exit().remove();
  }

  $: {
    if (!!secondaryContainer && !!thumbnailData) {
      let newData = secondaryThumbnails.map(getThumbnailInfo);
      updateSecondaryThumbnails(
        secondaryContainer.selectAll("div").data(newData)
      );
    }
  }

  $: {
    if (!!primaryContainer && !!thumbnailData) {
      let d = primaryThumbnail >= 0 ? getThumbnailInfo(primaryThumbnail) : null;
      if (!!d) {
        primaryContainer
          .style("width", d.width + "px")
          .style("height", d.height + "px");
        primaryImage
          .style("visibility", "visible")
          .style("left", -d.col + "px")
          .style("top", -d.row + "px")
          .style("width", thumbnailData.macroWidth + "px")
          .style("height", thumbnailData.macroHeight + "px")
          .attr("src", baseURL + "/" + d.filename);
      } else {
        primaryImage.style("visibility", "hidden");
      }
    }
  }

  let _pc;
  let _sc;

  onMount(() => {
    primaryContainer = d3.select(_pc);
    primaryImage = primaryContainer.append("img").style("position", "relative");
    secondaryContainer = d3.select(_sc);

    let u = secondaryContainer.selectAll("svg");
    if (!!thumbnailData) {
      u.data(secondaryThumbnails.map(getThumbnailInfo));
    }
    updateSecondaryThumbnails(u);
  });
</script>

<style>
  .primary-container {
    margin-bottom: 8px;
    margin-left: 4px;
    overflow: hidden;
    position: relative;
  }

  .secondary-container {
    display: flex;
    flex-wrap: wrap;
  }
</style>

<div bind:this={container} style="width: {width}px; height: {height}px;">
  <h4>{primaryTitle}</h4>
  {#if !!message}
    <p>{message}</p>
  {/if}
  <div bind:this={_pc} class="primary-container" />
  <h4>{secondaryTitle}</h4>
  <div bind:this={_sc} class="secondary-container" />
</div>
