<script>
  export let width = null;
  export let height = null;

  export let dataset = null;
  export let primaryTitle = 'Selection';
  export let secondaryTitle = 'Neighbors';
  export let thumbnailIDs = [];
  export let secondaryDiff = []; // list of IDs to use as references
  export let diffColor = 'green';
  export let frame = -1;
  export let message = '';

  let secondaryIDs = [];

  let _secondaryDiff = new Set();
  $: _secondaryDiff = new Set(secondaryDiff);

  function makeThumbnailInfo(id, secondary, diff) {
    if (!dataset || !id || frame < 0) return '';
    let item = dataset.frame(frame).get(id, 'label');
    if (!item) return '';

    let color = 'black';
    if (secondary && diff.size > 0 && !diff.has(id)) {
      color = diffColor;
    }
    let infoText = `<p style="color: ${color}">` + (item.text || '') + '</p>';
    if (!secondary && !!item.description) {
      infoText +=
        '<p style="color: grey;">' +
        item.description.replace('\n', '</p><p style="color: grey;">') +
        '</p>';
    }
    return infoText;
  }

  $: if (thumbnailIDs.length == 1 && frame >= 0) {
    secondaryIDs = dataset
      .frame(frame)
      .get(thumbnailIDs[0], 'highlightIndexes');
  } else {
    secondaryIDs = [];
  }
</script>

<div
  class="thumbnail-parent"
  style="width: {!!width ? `${width}px` : '100%'}; height: {!!height
    ? `${height}px`
    : '100%'};"
>
  {#if thumbnailIDs.length == 0}
    <div class="no-selection">
      Click to select points in the scatter plot, or Shift + drag to select a
      region.
    </div>
  {:else}
    <div class="header-bar">
      {primaryTitle}
    </div>
    <div class="thumbnails-container">
      {#if !!message}
        <p>{message}</p>
      {/if}
      {#each thumbnailIDs as id}
        <div class="thumbnail-row">
          {@html makeThumbnailInfo(id, false)}
        </div>
      {/each}
    </div>
  {/if}
  {#if secondaryIDs.length > 0}
    <div class="header-bar">
      {secondaryTitle}
    </div>
    <div class="thumbnails-container">
      {#each secondaryIDs as id}
        <div class="thumbnail-row">
          {@html makeThumbnailInfo(id, true, _secondaryDiff)}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .thumbnail-parent {
    overflow-y: scroll;
  }
  .no-selection {
    width: 100%;
    text-align: center;
    margin-top: 80px;
    color: #999;
    padding: 0 24px;
  }
  .thumbnail-row {
    padding: 4px 6px;
  }
  .thumbnails-container {
    padding: 12px;
  }
  .header-bar {
    background-color: #ddd;
    padding: 8px 12px;
    font-weight: 600;
    font-size: 10pt;
    text-transform: uppercase;
  }
</style>
