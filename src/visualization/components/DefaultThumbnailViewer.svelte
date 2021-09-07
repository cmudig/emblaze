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

  // each value in these arrays is an object with required id field and optional
  // count field
  let secondaryItems = [];
  let previewSecondaryItems = [];
  let commonChangeItems = [];

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

  function getThumbnailInfo(item, inFrame = -1) {
    inFrame = inFrame >= 0 ? inFrame : frame;
    let id = item.id;
    if (!dataset || id === null || inFrame < 0) return null;

    let info = dataset.frame(inFrame).get(id, 'label');
    if (!info)
      return {
        id,
        text: id.toString(),
      };

    let result = {
      id, // pass along from input
      text: info.text,
      description: info.description,
    };
    if (!!item.count) {
      result.rate = { count: item.count, total: thumbnailIDs.length };
    } else if (!!item.gained || !!item.lost) {
      result.change = {
        gained: item.gained,
        lost: item.lost,
        total: thumbnailIDs.length,
      };
    }
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

  $: updateNeighborArrays(thumbnailIDs, frame, previewFrame);

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

  /**
   * Ranks the neighbors of the given set of ids in the given frame based on
   * the position of each neighbor in each id's neighbor set. For instance, an
   * id that is within the top 5 neighbors of most points will be closer to the
   * beginning of the array than one that is farther from most points.
   *
   * filters can be an object including the following properties:
   *  - exclude: frame number whose neighbors to exclude from the list
   *  - intersect: frame number whose neighbors to intersect with the list
   * The rank numbers of each neighbor are preserved across the filter.
   *
   * @return a list of objects, each containing an id and a count, where count
   *  indicates the number of input ids that included this neighbor id
   */
  function rankNeighbors(ids, inFrame, filters = null) {
    let individualNeighbors = ids.map((id) => {
      let neighbors = dataset.frame(inFrame).get(id, 'highlightIndexes');
      if (!neighbors) return null;
      neighbors = neighbors
        .map((n, i) => ({
          id: n,
          score: neighbors.length - i,
        }))
        .filter((n) => !ids.includes(n.id));
      if (!!filters) {
        if (filters.hasOwnProperty('exclude')) {
          let excludeNeighbors = dataset
            .frame(filters.exclude)
            .get(id, 'highlightIndexes');
          if (!!excludeNeighbors) {
            excludeNeighbors = new Set(excludeNeighbors);
            neighbors = neighbors.filter((n) => !excludeNeighbors.has(n.id));
          }
        }
        if (filters.hasOwnProperty('intersect')) {
          let intersectNeighbors = dataset
            .frame(filters.intersect)
            .get(id, 'highlightIndexes');
          if (!!intersectNeighbors) {
            intersectNeighbors = new Set(intersectNeighbors);
            neighbors = neighbors.filter((n) => intersectNeighbors.has(n.id));
          }
        }
      }
      return neighbors;
    });

    let totalRanks = new Map();
    individualNeighbors.forEach((neighbors) => {
      if (!neighbors) return;
      neighbors.forEach((n) => {
        if (!totalRanks.has(n.id))
          totalRanks.set(n.id, { score: n.score, count: 1 });
        else {
          let existing = totalRanks.get(n.id);
          totalRanks.set(n.id, {
            score: existing.score + n.score,
            count: existing.count + 1,
          });
        }
      });
    });

    return [...totalRanks.entries()]
      .sort((a, b) => b[1].score - a[1].score)
      .map((item) => ({
        id: item[0],
        count: item[1].count,
      }));
  }

  function _getRankedNeighbors(ids, inFrame) {
    return ids.map((id) => {
      let neighbors = dataset.frame(inFrame).get(id, 'highlightIndexes');
      if (!neighbors) return null;
      neighbors = neighbors
        .map((n, i) => ({
          id: n,
          score: neighbors.length - i,
        }))
        .filter((n) => !ids.includes(n.id));
      return neighbors;
    });
  }

  function makeDeltaNeighbors(ids, fromFrame, toFrame) {
    let fromNeighbors = _getRankedNeighbors(ids, fromFrame);
    let toNeighbors = _getRankedNeighbors(ids, toFrame);

    let totalRanks = new Map();
    let updateFn = (id, score, gained) => {
      if (totalRanks.has(id)) {
        let curr = totalRanks.get(id);
        totalRanks.set(id, {
          id,
          score: curr.score + score * (gained ? 1 : -1),
          gained: curr.gained + (gained ? 1 : 0),
          lost: curr.lost + (gained ? 0 : 1),
        });
      } else {
        totalRanks.set(id, {
          id,
          score: score * (gained ? 1 : -1),
          gained: gained ? 1 : 0,
          lost: gained ? 0 : 1,
        });
      }
    };
    ids.forEach((_, i) => {
      let fromN = fromNeighbors[i];
      let toN = toNeighbors[i];
      let fromNIds = new Set(fromN.map((n) => n.id));
      let toNIds = new Set(toN.map((n) => n.id));
      fromN.forEach((n) => {
        if (!toNIds.has(n.id)) updateFn(n.id, n.score, false);
      });
      toN.forEach((n) => {
        if (!fromNIds.has(n.id)) updateFn(n.id, n.score, true);
      });
    });

    return [...totalRanks.entries()]
      .sort((a, b) => b[1].score - a[1].score)
      .map((item) => item[1]);
  }

  function updateNeighborArrays(
    primaryIDs,
    currentFrameNumber,
    previewFrameNumber
  ) {
    if (previewFrameNumber >= 0 && previewFrameNumber != currentFrameNumber) {
      if (primaryIDs.length == 1) {
        // with preview frame, single
        previewSecondaryItems = dataset
          .frame(previewFrameNumber)
          .get(primaryIDs[0], 'highlightIndexes')
          .slice(0, numNeighbors)
          .map((id) => ({ id }));
        commonChangeItems = [];
      } else if (primaryIDs.length > 1) {
        previewSecondaryItems = rankNeighbors(
          primaryIDs,
          previewFrameNumber
        ).slice(0, numNeighbors);

        let commonChanges = makeDeltaNeighbors(
          primaryIDs,
          currentFrameNumber,
          previewFrameNumber
        );
        commonChangeItems = [
          ...commonChanges.slice(0, Math.floor(numNeighbors / 2)),
          ...commonChanges.slice(
            commonChanges.length - Math.floor(numNeighbors / 2)
          ),
        ];
      } else {
        commonChangeItems = [];
        previewSecondaryItems = [];
      }
    } else {
      commonChangeItems = [];
      previewSecondaryItems = [];
    }
    if (currentFrameNumber >= 0) {
      if (primaryIDs.length == 1) {
        // without preview frame, single
        secondaryItems = dataset
          .frame(currentFrameNumber)
          .get(primaryIDs[0], 'highlightIndexes')
          .slice(0, numNeighbors)
          .map((id) => ({ id }));
      } else if (primaryIDs.length > 1) {
        // without preview frame, multiple
        secondaryItems = rankNeighbors(primaryIDs, currentFrameNumber).slice(
          0,
          numNeighbors
        );
      } else {
        secondaryItems = [];
      }
    }
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
          .map((id) => getThumbnailInfo({ id }))
          .filter((d) => !!d)
          .slice(0, showingFullSelection ? thumbnailIDs.length : MaxSelectionVisible) as d}
          <ThumbnailRow
            on:thumbnailClick
            on:thumbnailHover
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
  {#if secondaryItems.length > 0}
    <div class="header-bar">
      {secondaryTitle}
    </div>
    <div class="thumbnails-container column-container">
      <div class="thumbnail-column">
        {#if previewSecondaryItems.length > 0}
          <div class="subheader">{dataset.frame(frame).title}</div>
        {/if}
        {#each secondaryItems
          .map((item) => getThumbnailInfo(item))
          .filter((d) => !!d) as d}
          <ThumbnailRow
            on:thumbnailClick
            on:thumbnailHover
            mini={previewSecondaryItems.length > 0}
            {blobURLs}
            {d}
            color={previewSecondaryItems.length > 0 &&
            !previewSecondaryItems.find((item) => item.id == d.id)
              ? 'red'
              : 'black'}
          />
        {/each}
      </div>

      {#if previewSecondaryItems.length > 0}
        <div class="thumbnail-column">
          <div class="subheader">{dataset.frame(previewFrame).title}</div>
          {#each previewSecondaryItems
            .map((item) => getThumbnailInfo(item))
            .filter((d) => !!d) as d}
            <ThumbnailRow
              on:thumbnailClick
              on:thumbnailHover
              mini
              {blobURLs}
              {d}
              color={secondaryItems.length > 0 &&
              !secondaryItems.find((item) => item.id == d.id)
                ? 'green'
                : 'black'}
            />
          {/each}
        </div>
      {/if}
    </div>
    {#if thumbnailIDs.length > 1}
      <div class="explanatory-text">
        Points sorted by average nearest neighbor rank; bars = # of selected
        points containing each point as a neighbor
      </div>
    {/if}
  {/if}
  {#if commonChangeItems.length > 0}
    <div class="header-bar">Common Changes</div>
    <div class="thumbnails-container column-container">
      <div class="thumbnail-column">
        {#each commonChangeItems
          .map((item) => getThumbnailInfo(item))
          .filter((d) => !!d) as d}
          <ThumbnailRow
            on:thumbnailClick
            on:thumbnailHover
            mini
            {blobURLs}
            {d}
            color="black"
          />
        {/each}
      </div>
    </div>
    <div class="explanatory-text">
      Bars = # of selected points for which each point was gained or lost as a
      neighbor
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
    flex: 1;
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
  .explanatory-text {
    color: #999;
    text-align: center;
    width: 100%;
    padding: 0 16px 8px 16px;
    font-size: 9pt;
    line-height: 1.2em;
  }
</style>
