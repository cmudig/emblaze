<script>
  import { onMount, onDestroy } from 'svelte';
  import { base64ToBlob } from '../utils/helpers';

  export let width = null;
  export let height = null;

  export let dataset = null;
  export let primaryTitle = 'Selection';
  export let secondaryTitle = 'Neighbors';
  export let thumbnailIDs = [];
  export let frame = -1;
  export let previewFrame = -1;
  export let message = '';

  let secondaryIDs = [];
  let previewSecondaryIDs = [];

  // For image thumbnails

  let blobURLs = new Map();

  export function updateImageThumbnails() {
    if (blobURLs.size > 0) destroyImageThumbnails();
    if (!!dataset.spritesheets) {
      Object.keys(dataset.spritesheets).forEach((sheet) => {
        // Make a blob containing this spritesheet image
        let sheetInfo = dataset.spritesheets[sheet];
        let blob = base64ToBlob(sheetInfo.image, sheetInfo.imageFormat);
        blobURLs.set(sheet, URL.createObjectURL(blob));
      });
    }
  }

  export function destroyImageThumbnails() {
    // Remove all blobs used for this thumbnail viewer
    for (var sheet of blobURLs.keys()) {
      URL.revokeObjectURL(blobURLs.get(sheet));
    }
    blobURLs.clear();
  }

  // Retrieving and displaying info

  function getThumbnailInfo(id, inFrame = -1) {
    inFrame = inFrame >= 0 ? inFrame : frame;
    if (!dataset || id === null || inFrame < 0) return null;

    let info = dataset.frame(inFrame).get(id, 'label');
    if (!info) return null;

    let result = {
      id,
      text: info.text,
      description: info.description,
    };
    if (
      !!info.sheet &&
      !!dataset.spritesheets &&
      !!dataset.spritesheets[info.sheet]
    ) {
      // Add properties to indicate where to retrieve the image thumbnail from
      // the spritesheet
      result.sheet = info.sheet;
      result.spec = dataset.spritesheets[info.sheet].spec.frames[info.texture];
      result.macroSize = dataset.spritesheets[info.sheet].spec.meta.size;
    }
    return result;
  }

  function makeThumbnailText(item, secondary, diff, diffColor) {
    if (!item || (!item.text && !item.description)) return '';

    let color = 'black';
    if (secondary && diff.size > 0 && !diff.has(item.id)) {
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

  $: if (
    thumbnailIDs.length == 1 &&
    previewFrame >= 0 &&
    previewFrame != frame
  ) {
    previewSecondaryIDs = dataset
      .frame(previewFrame)
      .get(thumbnailIDs[0], 'highlightIndexes');
  } else {
    previewSecondaryIDs = [];
  }

  onMount(() => {
    if (!!dataset.spritesheets) updateImageThumbnails();
  });

  onDestroy(() => {
    // Destroy blob URLs
    destroyImageThumbnails();
  });
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
      {#each thumbnailIDs.map((id) => getThumbnailInfo(id)) as d}
        <div class="thumbnail-row">
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
                style={`left: ${-d.spec.frame.x}px; top: ${-d.spec.frame
                  .y}px; width: ${d.macroSize.w}px; height: ${
                  d.macroSize.h
                }px;`}
                alt="Image preview for point {d.id}"
              />
            </div>
          {/if}
          <div class="thumbnail-text-section">
            {@html makeThumbnailText(d, false)}
          </div>
        </div>
      {/each}
    </div>
  {/if}
  {#if secondaryIDs.length > 0}
    <div class="header-bar">
      {secondaryTitle}
    </div>
    <div class="thumbnails-container column-container">
      <div class="thumbnail-column">
        {#each secondaryIDs.map((id) => getThumbnailInfo(id)) as d}
          <div class="thumbnail-row">
            {#if !!d.sheet}
              <div
                class="image-parent"
                class:diff-red={previewSecondaryIDs.size > 0 &&
                  !previewSecondaryIDs.includes(d.id)}
                style={`width: ${d.spec.frame.w}px; height: ${d.spec.frame.h}px;`}
              >
                <img
                  class="thumbnail-image"
                  src={blobURLs.get(d.sheet)}
                  width={`${d.macroSize.w}px`}
                  height={`${d.macroSize.h}px`}
                  style={`left: ${-d.spec.frame.x}px; top: ${-d.spec.frame
                    .y}px; width: ${d.macroSize.w}px; height: ${
                    d.macroSize.h
                  }px;`}
                  alt="Image preview for point {d.id}"
                />
              </div>
            {/if}
            <div class="thumbnail-text-section">
              {@html makeThumbnailText(
                d,
                true,
                new Set(previewSecondaryIDs),
                'red'
              )}
            </div>
          </div>
        {/each}
      </div>
      {#if previewSecondaryIDs.length > 0}
        <div class="thumbnail-column">
          {#each previewSecondaryIDs.map((id) => getThumbnailInfo(id)) as d}
            <div class="thumbnail-row">
              {#if !!d.sheet}
                <div
                  class="image-parent"
                  class:diff-green={secondaryIDs.size > 0 &&
                    !secondaryIDs.includes(d.id)}
                  style={`width: ${d.spec.frame.w}px; height: ${d.spec.frame.h}px;`}
                >
                  <img
                    class="thumbnail-image"
                    src={blobURLs.get(d.sheet)}
                    width={`${d.macroSize.w}px`}
                    height={`${d.macroSize.h}px`}
                    style={`left: ${-d.spec.frame.x}px; top: ${-d.spec.frame
                      .y}px; width: ${d.macroSize.w}px; height: ${
                      d.macroSize.h
                    }px;`}
                    alt="Image preview for point {d.id}"
                  />
                </div>
              {/if}
              <div class="thumbnail-text-section">
                {@html makeThumbnailText(
                  d,
                  true,
                  new Set(secondaryIDs),
                  'green'
                )}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .no-selection {
    max-width: 100%;
    text-align: center;
    margin-top: 80px;
    color: #999;
    padding: 0 24px;
  }
  .thumbnail-row {
    padding: 4px 6px;
    display: flex;
    align-items: center;
  }
  .thumbnails-container {
    padding: 12px 4px;
  }
  .column-container {
    display: flex;
    justify-content: stretch;
    width: 100%;
  }
  .thumbnail-column {
    flex: 1 1 auto;
  }
  .header-bar {
    background-color: #ddd;
    padding: 8px 12px;
    font-weight: 600;
    font-size: 10pt;
    text-transform: uppercase;
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
    border: 2px solid red;
  }

  .diff-green {
    border: 2px solid green;
  }
</style>
