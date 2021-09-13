<script>
  import SynchronizedScatterplot from './visualization/SynchronizedScatterplot.svelte';
  import ScatterplotThumbnail from './visualization/components/ScatterplotThumbnail.svelte';
  import SpinnerButton from './visualization/components/SpinnerButton.svelte';
  import * as d3 from 'd3';
  import ColorSchemes from './colorschemes';

  export let model;

  // Creates a Svelte store (https://svelte.dev/tutorial/writable-stores) that syncs with the named Traitlet in widget.ts and example.py.
  import { syncValue } from './stores';
  import { Dataset, PreviewMode } from './visualization/models/dataset.js';
  import { onMount, onDestroy } from 'svelte';
  import { writable } from 'svelte/store';
  import { fade } from 'svelte/transition';
  import DefaultThumbnailViewer from './visualization/components/DefaultThumbnailViewer.svelte';
  import Legend from './visualization/components/Legend.svelte';
  import Autocomplete from './visualization/components/Autocomplete.svelte';
  import Modal from './visualization/components/Modal.svelte';
  import SelectionBrowser from './visualization/components/SelectionBrowser.svelte';
  import SaveSelectionPane from './visualization/components/SaveSelectionPane.svelte';
  import SegmentedControl from './visualization/components/SegmentedControl.svelte';
  import SettingsPane from './visualization/components/SettingsPane.svelte';
  import { ThumbnailProvider } from './visualization/models/thumbnails';

  let data = syncValue(model, 'data', {});
  let isLoading = syncValue(model, 'isLoading', true);
  let loadingMessage = syncValue(model, 'loadingMessage', '');

  let plotPadding = syncValue(model, 'plotPadding', 10.0);
  let height = 600; // can make this reactive later

  let dataset = null;
  let frameTransformations = syncValue(model, 'frameTransformations', []);
  let frameColors = syncValue(model, 'frameColors', []);
  let thumbnailData = syncValue(model, 'thumbnailData', {});

  let colorScheme = syncValue(model, 'colorScheme', 'tableau');
  let colorSchemeObject = ColorSchemes.getColorScheme($colorScheme);
  $: {
    let newScheme = ColorSchemes.getColorScheme($colorScheme);
    if (!!newScheme) colorSchemeObject = newScheme;
  }
  let previewMode = syncValue(
    model,
    'previewMode',
    PreviewMode.PROJECTION_SIMILARITY
  );
  let previewParameters = syncValue(model, 'previewParameters', {});
  let previewK = 10;
  let previewSimilarityThreshold = 0.5;
  let numNeighbors = syncValue(model, 'numNeighbors', 10);

  $: if (
    !!$frameTransformations &&
    $frameTransformations.length > 0 &&
    !!dataset
  ) {
    updateTransformations();
  }

  $: updateDataset($data);

  function updateDataset(rawData) {
    if (!!rawData && !!rawData['data']) {
      dataset = new Dataset(rawData, 'color');
      if (!!$frameTransformations && $frameTransformations.length > 0)
        updateTransformations(false);
    } else {
      dataset = null;
    }
  }

  function updateTransformations(animate = true) {
    dataset.transform($frameTransformations);
    if (!!canvas && animate) {
      canvas.animateDatasetUpdate();
    }
  }

  onMount(() => {
    // This logs if the widget is initialized successfully
    console.log('Mounted DR widget successfully');

    setupLogging();
  });

  onDestroy(() => {
    destroyLogging();
  });

  let canvas;
  let thumbnailViewer;

  let thumbnailProvider;

  //let thumbnailHoveredID = null;
  let scatterplotHoveredID = null;

  let selectedIDs = syncValue(model, 'selectedIDs', []);
  //$: console.log($selectedIDs);

  let alignedIDs = syncValue(model, 'alignedIDs', []);
  let alignedFrame = syncValue(model, 'alignedFrame', 0);
  // alignedFrame should match currentFrame as long as there is no current alignment
  $: if ($alignedIDs.length == 0) $alignedFrame = $currentFrame;

  let thumbnailIDs = [];
  let thumbnailHover = false;
  let thumbnailNeighbors = [];
  let previewThumbnailID = null;
  let previewThumbnailMessage = '';
  let previewThumbnailNeighbors = [];

  let currentFrame = syncValue(model, 'currentFrame', 0);
  let previewFrame = syncValue(model, 'previewFrame', 0);

  let saveSelectionFlag = syncValue(model, 'saveSelectionFlag', false);
  let selectionName = syncValue(model, 'selectionName', '');
  let selectionDescription = syncValue(model, 'selectionDescription', '');
  let isOpenDialogue = false;
  let nameField = '';
  let descriptionField = '';
  let name = '';
  let description = '';

  const SidebarPanes = {
    CURRENT: 0,
    SAVED: 1,
    RECENT: 2,
    SUGGESTED: 3,
  };
  let visibleSidebarPane = syncValue(
    model,
    'visibleSidebarPane',
    SidebarPanes.CURRENT
  );

  let filterIDs = syncValue(model, 'filterIDs', []);

  // Saving and loading selections

  let selectionList = syncValue(model, 'selectionList', []);

  function openSaveSelectionDialog() {
    $selectionName = '';
    $selectionDescription = '';
    isOpenDialogue = true;
  }

  function saveSelection(event) {
    $saveSelectionFlag = true;
    isOpenDialogue = false;
    logEvent({
      type: 'saveSelection',
      numSelected: $selectedIDs.length,
      numAligned: $alignedIDs.length,
      numFiltered: $filterIDs.length,
    });
  }

  function handleLoadSelection(event) {
    function filterFn(id) {
      return dataset.frame(event.detail.currentFrame).has(id);
    }

    if (
      event.detail.currentFrame < 0 ||
      event.detail.currentFrame >= dataset.frameCount ||
      event.detail.alignedFrame < 0 ||
      event.detail.alignedFrame >= dataset.frameCount
    ) {
      alert(
        'This saved selection has an invalid frame number and cannot be loaded.'
      );
    } else {
      let invalidSelected = !(event.detail.selectedIDs || []).every(filterFn);
      let invalidAligned = !(event.detail.alignedIDs || []).every(filterFn);
      let invalidFilter = !(event.detail.filterIDs || []).every(filterFn);

      $currentFrame = event.detail.currentFrame || $currentFrame;
      $alignedFrame = event.detail.alignedFrame || $currentFrame;
      if (!!event.detail.selectedIDs)
        $selectedIDs = event.detail.selectedIDs.filter(filterFn);
      if (!!event.detail.alignedIDs)
        $alignedIDs = event.detail.alignedIDs.filter(filterFn);
      if (!!event.detail.filterIDs)
        $filterIDs = event.detail.filterIDs.filter(filterFn);

      if (invalidSelected || invalidAligned || invalidFilter) {
        let messages = [];
        if (invalidSelected) messages.push('invalid selected IDs');
        if (invalidAligned) messages.push('invalid aligned IDs');
        if (invalidFilter) messages.push('invalid filter IDs');
        alert(
          'This saved selection had the following issues: ' +
            messages.join(', ') +
            '. The remainder of the selection was loaded.'
        );
      }
    }

    $visibleSidebarPane = SidebarPanes.CURRENT;
    setTimeout(() => canvas.showVicinityOfClickedPoint());
  }

  // Selection history

  let selectionHistory = syncValue(model, 'selectionHistory', []);
  const HistoryLength = 25;

  let oldSelectedIDs = [];

  $: if (oldSelectedIDs !== $selectedIDs) {
    updateSelectionHistory(oldSelectedIDs, $selectedIDs);
    oldSelectedIDs = $selectedIDs;
  }

  function _makeSelectionObjectFromList(selection) {
    return {
      selectionName: '',
      selectionDescription: new Date().toLocaleTimeString(),
      selectedIDs: selection,
      currentFrame: $currentFrame,
    };
  }

  function updateSelectionHistory(oldSelection, newSelection) {
    if (newSelection.length == 0) return;

    let selectionObj = _makeSelectionObjectFromList(newSelection);

    // Remove identical selection if it exists
    let idx = $selectionHistory.findIndex((sel) => {
      return (
        sel.selectedIDs.every((id) => newSelection.includes(id)) &&
        newSelection.every((id) => sel.selectedIDs.includes(id))
      );
    });
    if (idx >= 0)
      $selectionHistory = [
        ...$selectionHistory.slice(0, idx),
        ...$selectionHistory.slice(idx + 1),
      ];

    // Update history - either update the most recent one or add a new one.
    // If selectionHistory has a value in it, the first value should always be
    // equal to oldSelection
    if ($selectionHistory.length == 0 || oldSelection.length == 0) {
      $selectionHistory = [selectionObj, ...$selectionHistory];
    } else {
      let numAdded = newSelection.filter((id) => !oldSelection.includes(id))
        .length;
      let numRemoved = oldSelection.filter((id) => !newSelection.includes(id))
        .length;
      if (numAdded + numRemoved <= 1) {
        $selectionHistory = [selectionObj, ...$selectionHistory.slice(1)];
      } else {
        $selectionHistory = [selectionObj, ...$selectionHistory];
      }
    }

    if ($selectionHistory.length > HistoryLength) {
      $selectionHistory = $selectionHistory.slice(0, HistoryLength);
    }
  }

  // Suggested selections

  let suggestedSelections = syncValue(model, 'suggestedSelections', []);
  let suggestedSelectionWindow = syncValue(
    model,
    'suggestedSelectionWindow',
    []
  );
  let loadingSuggestions = syncValue(model, 'loadingSuggestions', false);
  let loadingSuggestionsProgress = syncValue(
    model,
    'loadingSuggestionsProgress',
    0.0
  );
  let recomputeSuggestionsFlag = syncValue(
    model,
    'recomputeSuggestionsFlag',
    false
  );
  let performanceSuggestionsMode = syncValue(
    model,
    'performanceSuggestionsMode',
    false
  );

  function suggestInViewport(bbox) {
    if (!canvas) return;
    $suggestedSelectionWindow = bbox;
    $recomputeSuggestionsFlag = true;
  }

  // Thumbnails

  function handleThumbnailClick(event) {
    if (event.detail.keyPressed) {
      let idx = $selectedIDs.indexOf(event.detail.id);
      if (idx == -1) {
        $selectedIDs = [...$selectedIDs, event.detail.id];
      } else {
        $selectedIDs = [
          ...$selectedIDs.slice(0, idx),
          ...$selectedIDs.slice(idx + 1),
        ];
      }
    } else {
      $selectedIDs = [event.detail.id];
    }
  }

  function handleThumbnailHover(event) {
    //thumbnailHoveredID = event.detail.id;
    scatterplotHoveredID = event.detail.id;
  }

  let showLegend = true;

  $: {
    thumbnailIDs = $selectedIDs;
    thumbnailHover = false;
  }

  function onScatterplotHover(e) {
    if (e.detail != null) {
      thumbnailIDs = [e.detail];
      thumbnailHover = true;
    } else {
      thumbnailIDs = $selectedIDs;
      thumbnailHover = false;
    }
  }

  $: if (!!dataset && !!canvas) {
    updateThumbnails($thumbnailData);
  }

  function updateThumbnails(td) {
    if (!!td && !!td.format) dataset.addThumbnails(td);
    else dataset.removeThumbnails();
    canvas.updateThumbnails();
    if (!!thumbnailProvider) thumbnailProvider.destroy();
    thumbnailProvider = new ThumbnailProvider(dataset);
    updatePointSelectorOptions();
  }

  // Previews and settings

  $: if (!!dataset) {
    dataset.setPreviewMode($previewMode);
  }

  $: if (!!dataset) {
    Object.keys($previewParameters).forEach((k) => {
      dataset.setPreviewParameter(k, $previewParameters[k]);
    });
  }

  $: $previewParameters = {
    k: previewK,
    similarityThreshold: previewSimilarityThreshold,
  };

  let isSettingsOpen = false;

  // Autocomplete

  let pointSelectorOptions = [];

  function updatePointSelectorOptions() {
    if (dataset == null || $currentFrame < 0) return;
    let frame = dataset.frame($currentFrame);
    pointSelectorOptions = frame.getIDs().map((itemID) => {
      let label = frame.get(itemID, 'label');
      if (!!label && !!label.text) {
        return {
          value: itemID,
          text: `${itemID} - ${label.text}`,
        };
      }
      return { value: itemID, text: itemID.toString() };
    });
  }

  $: if (dataset != null && $currentFrame >= 0) {
    updatePointSelectorOptions();
  }

  // Selection order

  let selectionUnit = syncValue(model, 'selectionUnit', '');
  let selectionOrderRequest = syncValue(model, 'selectionOrderRequest', {});
  let selectionOrder = syncValue(model, 'selectionOrder', []);
  const SelectionOrderTimeout = 100;

  async function selectionOrderFn(pointID, metric) {
    $selectionOrderRequest = {
      centerID: pointID,
      frame: $currentFrame,
      metric,
    };
    $selectionOrder = [];

    return await _checkSelectionOrder(); // dataset.map((id) => [id, id]);
  }

  async function _checkSelectionOrder() {
    if ($selectionOrder.length > 0) {
      $selectionOrderRequest = {};
      return $selectionOrder;
    }
    return await new Promise((resolve) => {
      setTimeout(() => {
        resolve(_checkSelectionOrder());
      }, SelectionOrderTimeout);
    });
  }

  $: {
    console.log(
      'selection order:',
      $selectionOrder,
      'request:',
      $selectionOrderRequest
    );
    //if ($selectionOrder.length > 0) $selectionOrderRequest = {};
  }

  // Interaction logging

  let loggingEnabled = syncValue(model, 'loggingEnabled', false);
  let interactionHistory = syncValue(model, 'interactionHistory', []);
  let saveInteractionsFlag = syncValue(model, 'saveInteractionsFlag', false);

  let loggingInterval = null;
  const LoggingIntervalTime = 10000;

  function setupLogging() {
    if (!!loggingInterval) clearInterval(loggingInterval);
    loggingInterval = setInterval(saveInteractionHistory, LoggingIntervalTime);
  }

  function destroyLogging() {
    if (!!loggingInterval) clearInterval(loggingInterval);
    loggingInterval = null;
  }

  function saveInteractionHistory() {
    $saveInteractionsFlag = true;
  }

  function logEvent(event) {
    if (!event) return;
    event.timestamp = new Date().toString();
    $interactionHistory = [...$interactionHistory, event];
  }

  $: logEvent({
    type: 'frameChange',
    current: $currentFrame,
    preview: $previewFrame,
  });

  $: logEvent({ type: 'align', numPoints: $alignedIDs.length });
  $: logEvent({ type: 'filter', numPoints: $filterIDs.length });
</script>

{#if $isLoading}
  <div class="text-center">
    Loading {#if $loadingMessage.length > 0} ({$loadingMessage}){/if}...
    <i class="text-primary fa fa-spinner fa-spin" />
  </div>
{:else}
  <Modal visible={isOpenDialogue} width={400}>
    <SaveSelectionPane
      bind:name={$selectionName}
      bind:description={$selectionDescription}
      on:cancel={() => (isOpenDialogue = false)}
      on:save={saveSelection}
    >
      <div slot="summary">
        <p>
          <strong>Frame number:</strong>
          {$currentFrame}
        </p>
        <p>
          <strong>Filter:</strong>
          {#if $filterIDs.length > 0}
            {$filterIDs.length} points
          {:else}
            No filter
          {/if}
        </p>
        <p>
          <strong>Selected:</strong>
          {$selectedIDs.length} points
        </p>
        <p>
          <strong>Aligned:</strong>
          {#if $alignedIDs.length > 0}
            {$alignedIDs.length} points, to frame {$alignedFrame}
          {:else}
            No alignment
          {/if}
        </p>
      </div>
    </SaveSelectionPane>
  </Modal>

  <Modal visible={isSettingsOpen} width={400}>
    <SettingsPane
      bind:colorScheme={$colorScheme}
      bind:showLegend
      bind:previewMode={$previewMode}
      previewModes={Object.values(PreviewMode)}
      colorSchemes={ColorSchemes.allColorSchemes.map((c) => c.name)}
      bind:numNeighbors={$numNeighbors}
      bind:previewK
      bind:similarityThreshold={previewSimilarityThreshold}
      on:close={() => (isSettingsOpen = false)}
    />
  </Modal>

  <div class="vis-container">
    <div class="frame-sidebar">
      <div class="frame-thumbnail-container">
        {#each [...d3.range(dataset.frameCount)] as i}
          <div class="frame-thumbnail-item">
            <ScatterplotThumbnail
              on:click={() => {
                if ($previewFrame == i) {
                  $currentFrame = i;
                  $previewFrame = -1;
                } else if ($currentFrame != i) $previewFrame = i;
                else if ($currentFrame == i) $previewFrame = -1;
              }}
              isSelected={$currentFrame == i}
              isPreviewing={$previewFrame == i &&
                $previewFrame != $currentFrame}
              colorScale={!!dataset
                ? dataset.colorScale(colorSchemeObject)
                : null}
              data={dataset}
              frame={!!dataset ? dataset.frame(i) : null}
              accentColor={!!$frameColors && $frameColors.length > i
                ? $frameColors[i]
                : null}
            />
          </div>
        {/each}
      </div>
      <div class="frame-sidebar-message">
        Similar color stripes = similar arrangements of selected points
      </div>
    </div>

    <div class="scatterplot">
      <div class="scatterplot-parent">
        <SynchronizedScatterplot
          bind:this={canvas}
          data={dataset}
          padding={$plotPadding}
          frame={$currentFrame}
          previewFrame={$previewFrame}
          numNeighbors={$numNeighbors}
          hoverable
          showPreviewControls
          animateTransitions
          backgroundColor={$previewFrame != $currentFrame && $previewFrame != -1
            ? '#f8f8ff'
            : 'white'}
          bind:hoveredID={scatterplotHoveredID}
          bind:clickedIDs={$selectedIDs}
          bind:alignedIDs={$alignedIDs}
          bind:filterIDs={$filterIDs}
          on:datahover={onScatterplotHover}
          colorScheme={colorSchemeObject}
          {selectionOrderFn}
          selectionUnits={!!$selectionUnit
            ? ['pixels', $selectionUnit]
            : ['pixels']}
          on:viewportChanged={(e) => suggestInViewport(e.detail)}
          on:logEvent={(e) => logEvent(e.detail)}
        />
        {#if showLegend}
          <div class="legend-container">
            <Legend
              colorScale={!!dataset
                ? dataset.colorScale(colorSchemeObject)
                : null}
              type={colorSchemeObject.type || 'continuous'}
            />
          </div>
        {/if}
      </div>
    </div>
    <div class="sidebar">
      <div class="search-bar">
        <Autocomplete
          placeholder="Search for a point..."
          options={pointSelectorOptions}
          maxOptions={10}
          fillWidth={true}
          on:change={(e) => {
            $selectedIDs = [e.detail];
            logEvent({ type: 'selection', source: 'autocomplete' });
          }}
        />
      </div>
      <div class="action-toolbar">
        <SegmentedControl
          bind:selected={$visibleSidebarPane}
          options={['Current', 'Saved', 'Recent', 'Suggested']}
        />
      </div>
      <div class="sidebar-content">
        {#if $visibleSidebarPane == SidebarPanes.CURRENT && !!$thumbnailData}
          <DefaultThumbnailViewer
            on:thumbnailClick={handleThumbnailClick}
            on:thumbnailHover={handleThumbnailHover}
            bind:this={thumbnailViewer}
            {dataset}
            {thumbnailProvider}
            primaryTitle={thumbnailHover ? 'Hovered Point' : 'Selection'}
            frame={$currentFrame}
            previewFrame={$previewFrame}
            {thumbnailIDs}
            numNeighbors={$numNeighbors}
            on:logEvent={(e) => logEvent(e.detail)}
          />
        {:else if $visibleSidebarPane == SidebarPanes.SAVED}
          <SelectionBrowser
            data={$selectionList}
            {thumbnailProvider}
            emptyMessage="No saved selections yet! To create one, first select, align, or isolate some points, then click Save Selection."
            on:loadSelection={(e) => {
              handleLoadSelection(e);
              logEvent({ type: 'loadSelection', source: 'saved' });
            }}
          />
        {:else if $visibleSidebarPane == SidebarPanes.RECENT}
          <SelectionBrowser
            data={$selectionHistory}
            {thumbnailProvider}
            emptyMessage="No recent selections yet! Start selecting some points."
            on:loadSelection={(e) => {
              handleLoadSelection(e);
              logEvent({ type: 'loadSelection', source: 'recents' });
            }}
          />
        {:else if $visibleSidebarPane == SidebarPanes.SUGGESTED}
          <SelectionBrowser
            data={$suggestedSelections}
            {thumbnailProvider}
            loading={$loadingSuggestions}
            loadingMessage={'Loading suggestions' +
              ($loadingSuggestionsProgress > 0.0
                ? ` (${($loadingSuggestionsProgress * 100.0).toFixed(0)}%)`
                : '') +
              '...'}
            emptyMessage="No suggested selections right now.{performanceSuggestionsMode
              ? ' Suggestions are in performance mode - will compute when less than 1,000 points are displayed.'
              : ''}"
            on:loadSelection={(e) => {
              handleLoadSelection(e);
              logEvent({ type: 'loadSelection', source: 'suggested' });
            }}
          />
        {/if}
      </div>
      <div class="action-toolbar">
        <button
          type="button"
          class="btn btn-primary btn-sm jp-Dialog-button jp-mod-accept jp-mod-styled"
          on:click|preventDefault={openSaveSelectionDialog}
          disabled={$selectedIDs.length == 0 &&
            $alignedIDs.length == 0 &&
            $filterIDs.length == 0}
        >
          Save Selection
        </button>
        <div style="flex-grow: 1" />
        <button
          type="button"
          class="btn btn-secondary btn-sm jp-Dialog-button jp-mod-reject jp-mod-styled"
          on:click|preventDefault={() => (isSettingsOpen = true)}
        >
          Settings
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .scatterplot {
    height: 100%;
    flex: 1 1;
    min-width: 0;
  }

  .scatterplot-parent {
    position: relative;
    width: 100%;
    height: 100%;
    /*border: 1px solid #bbb;*/
  }

  .vis-container {
    width: 100%;
    height: 600px;
    display: flex;
    justify-items: stretch;
    /*border: 2px solid #bbb;*/
  }

  .frame-sidebar {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid #bbb;
  }

  .frame-thumbnail-item {
    border-bottom: 1px solid #bbb;
  }

  .frame-thumbnail-container {
    flex-grow: 1;
    overflow-y: scroll;
  }

  .frame-sidebar-message {
    color: #999;
    background-color: #eee;
    border-top: 1px solid #bbb;
    padding: 8px;
    text-align: center;
    font-size: 8pt;
    max-width: 100px;
    line-height: 1.3em;
  }

  .legend-container {
    position: absolute;
    top: 12px;
    left: 12px;
    border-radius: 4px;
    background-color: rgba(255, 255, 255, 0.8);
    pointer-events: none;
  }

  .sidebar {
    width: 300px;
    height: 600px;
    display: flex;
    flex-direction: column;
    margin-right: 8px;
    box-sizing: border-box;
  }

  .sidebar-content {
    border: 1px solid #bbb;
    flex-grow: 1;
    overflow-y: scroll;
    box-sizing: border-box;
  }

  .search-bar {
    display: flex;
    align-items: center;
    height: 44px;
    padding: 4px;
    flex: 0 0 auto;
  }
  .action-toolbar {
    display: flex;
    align-items: center;
    height: 48px;
    padding: 4px 0;
    flex: 0 0 auto;
  }

  .jp-Dialog-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
