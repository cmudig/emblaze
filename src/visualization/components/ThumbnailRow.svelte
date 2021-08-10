<script>
  export let d;
  export let color = 'black';
  export let blobURLs;

  export let mini = false;
  export let detail = false;
</script>

<div class="thumbnail-row">
  {#if !!d.sheet}
    <div
      class="image-parent"
      class:diff-green={color == 'green'}
      class:diff-red={color == 'red'}
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
    </div>
  {/if}
  {#if !d.sheet || !mini}
    <div class="thumbnail-text-section">
      {#if d.text}
        <p class:text-red={color == 'red'} class:text-green={color == 'green'}>
          {d.text}
        </p>
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
  }

  .image-parent {
    margin: 4px 12px 4px 4px;
    overflow: hidden;
    position: relative;
  }

  .thumbnail-image {
    position: relative;
    max-width: none !important;
  }

  .diff-red {
    border: 3px solid #d81b60;
  }

  .diff-green {
    border: 3px solid #98fb98;
  }

  .text-red {
    color: #d81b60;
  }

  .text-green {
    color: #98fb98;
  }
</style>
