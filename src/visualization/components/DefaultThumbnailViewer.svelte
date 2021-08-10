<script>
  import { onMount, onDestroy } from 'svelte';
  import App from '../../App.svelte';
  import { base64ToBlob, getOSName } from '../utils/helpers';
  import ThumbnailRow from './ThumbnailRow.svelte';
  export let width = null;
  export let height = null;

  export let dataset = null;
  export let primaryTitle = 'Selection';
  export let secondaryTitle = 'Neighbors';
  export let thumbnailIDs = [];
  export let frame = -1;
  export let previewFrame = -1;
  export let message = '';

  export let numNeighbors = 10;

  let secondaryIDs = [];
  let previewSecondaryIDs = [];
  let gainedIDs = [];
  let lostIDs = [];
  let sameIDs = [];

  const MaxSelectionVisible = 6;
  let showingFullSelection = false;

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

  function mostCommonValues(arr, k) {
    let freqMap = new Map();

    for (const x of arr) {
      if (freqMap.has(x)) {
        freqMap.set(x, freqMap.get(x) + 1);
      } else {
        freqMap.set(x, 1);
      }
    }

    return [...freqMap.keys()]
      .sort((a, b) => freqMap.get(b) - freqMap.get(a))
      .slice(0, k);
  }

  function genNeighborArray() {
    let neighborArray = [];

    for (const id of thumbnailIDs) {
      for (const n of dataset.frame(frame).get(id, 'highlightIndexes')) {
        neighborArray.push(n);
      }
    }

    return neighborArray;
  }

  // without preview frame, single or multiple:
  $: if (thumbnailIDs.length == 1 && frame >= 0) {
    secondaryIDs = dataset
      .frame(frame)
      .get(thumbnailIDs[0], 'highlightIndexes')
      .slice(0, numNeighbors);
  } else if (thumbnailIDs.length > 1 && frame >= 0) {
    secondaryIDs = mostCommonValues(genNeighborArray(), numNeighbors);
  } else {
    secondaryIDs = [];
  }

  // with preview frame, single
  $: if (
    thumbnailIDs.length == 1 &&
    previewFrame >= 0 &&
    previewFrame != frame
  ) {
    previewSecondaryIDs = dataset
      .frame(previewFrame)
      .get(thumbnailIDs[0], 'highlightIndexes')
      .slice(0, numNeighbors);
  } else {
    previewSecondaryIDs = [];
  }

  // with preview frame, multiple
  $: if (
    thumbnailIDs.length > 1 &&
    previewFrame >= 0 &&
    previewFrame != frame
  ) {
    let frame1Neighbors = new Set();
    let frame2Neighbors = new Set();

    for (const id of thumbnailIDs) {
      for (const n of dataset.frame(frame).get(id, 'highlightIndexes')) {
        frame1Neighbors.add(n);
      }

      for (const n of dataset.frame(previewFrame).get(id, 'highlightIndexes')) {
        frame2Neighbors.add(n);
      }
    }

    sameIDs = mostCommonValues(
      [...frame1Neighbors].filter(
        (x) => frame2Neighbors.has(x) && !thumbnailIDs.includes(x)
      ),
      numNeighbors
    );
    lostIDs = mostCommonValues(
      [...frame1Neighbors].filter((x) => !frame2Neighbors.has(x)),
      numNeighbors
    );
    gainedIDs = mostCommonValues(
      [...frame2Neighbors].filter((x) => !frame1Neighbors.has(x)),
      numNeighbors
    );
  } else {
    sameIDs = [];
    lostIDs = [];
    gainedIDs = [];
  }

  onMount(() => {
    if (!!dataset.spritesheets) {
      updateImageThumbnails();
      thumbnailIDs = thumbnailIDs; // force re-layout
    }
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
      <p><strong>Click</strong> to select points</p>
      <p>
        <strong
          >{#if getOSName() == 'MacOS'}Cmd{:else}Ctrl{/if} + click</strong
        > to add to selection
      </p>
      <p>
        <strong
          >{#if getOSName() == 'MacOS'}Cmd{:else}Ctrl{/if} + drag</strong
        > to select a region
      </p>
    </div>
  {:else}
    <div class="header-bar">
      {primaryTitle}
    </div>
    <div class="thumbnails-container">
      {#if !!message}
        <p>{message}</p>
      {/if}
      <div class:wrap-container={blobURLs.size > 0 && thumbnailIDs.length > 1}>
        {#each thumbnailIDs
          .map((id) => getThumbnailInfo(id))
          .filter((d) => !!d)
          .slice(0, showingFullSelection ? thumbnailIDs.length : MaxSelectionVisible) as d}
          <ThumbnailRow
            {blobURLs}
            {d}
            mini={blobURLs.size > 0 && thumbnailIDs.length > 1}
            detail={thumbnailIDs.length == 1}
          />
        {/each}
      </div>
      {#if thumbnailIDs.length > MaxSelectionVisible}
        <a
          class="selection-toggle-link"
          href="#"
          on:click|preventDefault={() =>
            (showingFullSelection = !showingFullSelection)}
        >
          {#if showingFullSelection}
            Show less
          {:else}
            Show more
          {/if}
        </a>
      {/if}
    </div>
  {/if}
  {#if secondaryIDs.length > 0}
    <div class="header-bar">
      {secondaryTitle}
    </div>
    <div class="thumbnails-container column-container">
      {#if sameIDs.length > 0}
        <div class="thumbnail-column">
          <div class="subheader">Both</div>
          {#each sameIDs.map((id) => getThumbnailInfo(id)) as d}
            <ThumbnailRow mini {blobURLs} {d} color="black" />
          {/each}
        </div>
      {/if}

      {#if lostIDs.length > 0}
        <div class="thumbnail-column">
          <div class="subheader">{dataset.frame(frame).title}</div>
          {#each lostIDs.map((id) => getThumbnailInfo(id)) as d}
            <ThumbnailRow mini {blobURLs} {d} color="red" />
          {/each}
        </div>
      {/if}

      {#if gainedIDs.length > 0}
        <div class="thumbnail-column">
          <div class="subheader">{dataset.frame(previewFrame).title}</div>
          {#each gainedIDs.map((id) => getThumbnailInfo(id)) as d}
            <ThumbnailRow mini {blobURLs} {d} color="green" />
          {/each}
        </div>
      {/if}

      {#if lostIDs.length == 0 && gainedIDs.length == 0 && sameIDs.length == 0}
        <div class="thumbnail-column">
          {#if previewSecondaryIDs.length > 0}
            <div class="subheader">{dataset.frame(frame).title}</div>
          {/if}
          {#each secondaryIDs
            .map((id) => getThumbnailInfo(id))
            .filter((d) => !!d) as d}
            <ThumbnailRow
              mini={previewSecondaryIDs.length > 0}
              {blobURLs}
              {d}
              color={previewSecondaryIDs.length > 0 &&
              !previewSecondaryIDs.includes(d.id)
                ? 'red'
                : 'black'}
            />
          {/each}
        </div>
      {/if}

      {#if previewSecondaryIDs.length > 0 && lostIDs.length == 0 && gainedIDs.length == 0 && sameIDs.length == 0}
        <div class="thumbnail-column">
          <div class="subheader">{dataset.frame(previewFrame).title}</div>
          {#each previewSecondaryIDs.map((id) => getThumbnailInfo(id)) as d}
            <ThumbnailRow
              mini
              {blobURLs}
              {d}
              color={secondaryIDs.length > 0 && !secondaryIDs.includes(d.id)
                ? 'green'
                : 'black'}
            />
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
    color: #999;
    padding: 80px 24px 0 24px;
  }
  .no-selection p {
    margin-bottom: 12px;
  }
  .thumbnails-container {
    padding: 12px 4px;
    box-sizing: border-box;
  }
  .column-container {
    display: flex;
    justify-content: stretch;
    width: 100%;
    box-sizing: border-box;
  }
  .wrap-container {
    display: flex;
    flex-wrap: wrap;
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
  .subheader {
    text-align: center;
    font-weight: 600;
    font-size: 10pt;
    text-transform: uppercase;
    margin-bottom: 8px;
    width: 100%;
  }
  .selection-toggle-link {
    margin-left: 10px;
  }
</style>
