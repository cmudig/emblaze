<script>
  import { createEventDispatcher } from 'svelte';
  export let d;
  export let color = 'black';
  export let blobURLs;
  const dispatch = createEventDispatcher();
  export let mini = false;
  export let detail = false;
</script>

<div
  class="thumbnail-row"
  on:click={(e) =>
    dispatch('thumbnailClick', {
      id: d.id,
      keyPressed: e.metaKey || e.ctrlKey,
    })}
  on:mouseover={() => dispatch('thumbnailHover', { id: d.id })}
  on:mouseout={() => dispatch('thumbnailHover', { id: null })}
>
  {#if !!d.sheet}
    <div
      class="image-parent"
      style={`width: ${d.spec.frame.w}px; height: ${d.spec.frame.h}px;`}
    >
      <img
        class="thumbnail-image"
        src={blobURLs.get(d.sheet)}
        width={`${d.macroSize.w}px`}
        height={`${d.macroSize.h}px`}
        style={`left: ${-d.spec.frame.x}px; top: ${-d.spec.frame.y}px; width: ${
          d.macroSize.w
        }px; height: ${d.macroSize.h}px;`}
        alt="Image preview for point {d.id}"
      />
      <div
        class="image-overlay"
        class:diff-green={color == 'green'}
        class:diff-red={color == 'red'}
        style={`width: ${d.spec.frame.w}px; height: ${d.spec.frame.h}px;`}
      />
    </div>
  {/if}
  {#if !d.sheet || !mini || !!d.rate || !!d.change}
    <div
      class="thumbnail-text-section"
      class:text-section-with-change={!!d.change}
    >
      {#if d.text && (!d.sheet || !mini)}
        <p
          class:text-red={color == 'red'}
          class:text-green={color == 'green'}
          class:label-with-change={!!d.change}
        >
          {d.text}
        </p>
      {/if}
      {#if !!d.rate}
        <div class="count-bar-parent">
          <div class="count-bar">
            <div
              class="count-bar-filled"
              style="width: {((d.rate.count / d.rate.total) * 100).toFixed(
                0
              )}%;"
            />
          </div>
          <div class="count-text">{d.rate.count}</div>
        </div>
      {:else if !!d.change}
        <div class="count-bar-parent">
          <div class="change-text text-red" style="text-align: right;">
            {#if d.change.lost > 0}&ndash;{d.change.lost}{/if}
          </div>
          <div class="count-bar">
            <div
              class="count-bar-lost"
              style="left: {(
                (0.5 - d.change.lost / (d.change.total * 2)) *
                100
              ).toFixed(0)}%; right: 50%;"
            />
            <div
              class="count-bar-gained"
              style="left: 50%; width: {(
                (d.change.gained / (d.change.total * 2)) *
                100
              ).toFixed(0)}%;"
            />
          </div>
          <div class="change-text text-green" style="text-align: left;">
            {#if d.change.gained > 0}+{d.change.gained}{/if}
          </div>
        </div>
      {/if}
      {#if detail && !!d.description}
        {#each d.description.split('\n') as line}
          <p style="color: grey;">{line}</p>
        {/each}
      {/if}
    </div>
  {/if}
</div>

<style>
  .thumbnail-row {
    padding: 4px 6px;
    display: flex;
    align-items: center;
    box-sizing: content-box;
    border-radius: 4px;
  }

  .thumbnail-text-section {
    width: 100%;
  }

  .text-section-with-change {
    display: flex;
    align-items: center;
  }

  .label-with-change {
    flex: 0 0 auto;
    width: 40%;
  }

  .thumbnail-row:hover {
    background-color: #eee;
  }

  .thumbnail-row:focus {
    background-color: #bbb;
  }

  .image-parent {
    margin: 4px 12px 4px 4px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
  }

  .thumbnail-image {
    position: relative;
    max-width: none !important;
  }

  .image-overlay {
    position: absolute;
    top: 0;
    left: 0;
  }

  .diff-red {
    background-color: rgba(216, 27, 96, 0.3);
  }

  .diff-green {
    background-color: rgba(73, 199, 56, 0.3);
  }

  .text-red {
    color: #d81b60;
  }

  .text-green {
    color: #49c738;
  }

  .count-bar-parent {
    display: flex;
    align-items: center;
    flex: 1 1 auto;
  }

  .count-text {
    color: #999;
    font-size: 9pt;
    width: 24px;
    flex: 0 0 auto;
    margin-left: 8px;
  }

  .change-text {
    font-size: 9pt;
    width: 24px;
    flex: 0 0 auto;
    margin: 0 8px;
  }

  .count-bar {
    flex: 1 1 auto;
    height: 6px;
    background-color: #ddd;
    border-radius: 2px;
    position: relative;
  }

  .count-bar-filled {
    border-radius: 2px;
    background-color: #666;
    height: 100%;
    position: absolute;
    top: 0;
    left: 0;
  }

  .count-bar-lost {
    height: 100%;
    position: absolute;
    top: 0;
    border-radius: 2px 0 0 2px;
    background-color: #d81b60;
  }

  .count-bar-gained {
    height: 100%;
    position: absolute;
    top: 0;
    border-radius: 0 2px 2px 0;
    background-color: #49c738;
  }
</style>
