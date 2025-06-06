<svelte:options accessors />

<script>
  import SynchronizedScatterplot from './visualization/SynchronizedScatterplot.svelte';
  import ScatterplotThumbnail from './visualization/components/ScatterplotThumbnail.svelte';
  import SpinnerButton from './visualization/components/SpinnerButton.svelte';
  import * as d3 from 'd3';
  import ColorSchemes from './colorschemes';

  export let model;

  // Creates a Svelte store (https://svelte.dev/tutorial/writable-stores) that syncs with the named Traitlet in widget.ts and example.py.
  import { traitlet } from './stores';
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
  import HelpMessage from './visualization/components/HelpMessage.svelte';
  import { helpMessagesVisible } from './visualization/utils/stores';

  export let fillHeight = false;

  let isLoading = traitlet(model, 'isLoading', false);

  let data = traitlet(model, 'data', null);
  let neighborData = traitlet(model, 'neighborData', []);

  let plotPadding = traitlet(model, 'plotPadding', 10.0);
  let height = 600; // can make this reactive later

  export let dataset = null;
  let frameTransformations = traitlet(model, 'frameTransformations', []);
  let frameColors = traitlet(model, 'frameColors', []);
  let thumbnailData = traitlet(model, 'thumbnailData', {});

  let colorScheme = traitlet(model, 'colorScheme', 'tableau');
  let colorSchemeObject = ColorSchemes.getColorScheme($colorScheme);
  $: {
    let newScheme = ColorSchemes.getColorScheme($colorScheme);
    if (!!newScheme) colorSchemeObject = newScheme;
  }
  let previewMode = traitlet(
    model,
    'previewMode',
    PreviewMode.PROJECTION_SIMILARITY
  );
  let previewParameters = traitlet(model, 'previewParameters', {});
  let previewK = 10;
  let previewSimilarityThreshold = 0.5;
  let numNeighbors = traitlet(model, 'numNeighbors', 10);

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
    if (dataset.frameCount != $frameTransformations.length) return;
    dataset.transform($frameTransformations);
    if (!!canvas && animate) {
      canvas.animateDatasetUpdate();
    }
  }

  $: if (!!$neighborData && $neighborData.length > 0 && !!dataset) {
    dataset.setNeighbors($neighborData);
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

  let selectedIDs = traitlet(model, 'selectedIDs', []);
  //$: console.log($selectedIDs);

  let alignedIDs = traitlet(model, 'alignedIDs', []);
  let alignedFrame = traitlet(model, 'alignedFrame', 0);
  // alignedFrame should match currentFrame as long as there is no current alignment
  $: if ($alignedIDs.length == 0) $alignedFrame = $currentFrame;

  let thumbnailIDs = [];
  let thumbnailHover = false;
  let thumbnailNeighbors = [];
  let previewThumbnailID = null;
  let previewThumbnailMessage = '';
  let previewThumbnailNeighbors = [];

  let currentFrame = traitlet(model, 'currentFrame', 0);
  let previewFrame = traitlet(model, 'previewFrame', 0);

  let allowsSavingSelections = traitlet(model, 'allowsSavingSelections', false);
  let saveSelectionFlag = traitlet(model, 'saveSelectionFlag', false);
  let selectionName = traitlet(model, 'selectionName', '');
  let selectionDescription = traitlet(model, 'selectionDescription', '');
  let isOpenDialogue = false;
  let nameField = '';
  let descriptionField = '';
  let name = '';
  let description = '';

  const SidebarPanes = {
    CURRENT: 1,
    SAVED: 2,
    RECENT: 3,
    SUGGESTED: 4,
  };
  let sidebarPaneOptions = [];
  $: {
    if ($allowsSavingSelections)
      sidebarPaneOptions = [
        { value: SidebarPanes.CURRENT, name: 'Current' },
        { value: SidebarPanes.SAVED, name: 'Saved' },
        { value: SidebarPanes.RECENT, name: 'Recent' },
        { value: SidebarPanes.SUGGESTED, name: 'Suggested' },
      ];
    else
      sidebarPaneOptions = [
        { value: SidebarPanes.CURRENT, name: 'Current' },
        { value: SidebarPanes.RECENT, name: 'Recent' },
        { value: SidebarPanes.SUGGESTED, name: 'Suggested' },
      ];
  }
  let visibleSidebarPane = traitlet(
    model,
    'visibleSidebarPane',
    SidebarPanes.CURRENT
  );

  let filterIDs = traitlet(model, 'filterIDs', []);

  // Saving and loading selections

  let selectionList = traitlet(model, 'selectionList', []);

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

      $currentFrame = event.detail.currentFrame || $currentFrame || 0;
      $alignedFrame = event.detail.alignedFrame || $currentFrame || 0;
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

  let selectionHistory = traitlet(model, 'selectionHistory', []);
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
      let numAdded = newSelection.filter(
        (id) => !oldSelection.includes(id)
      ).length;
      let numRemoved = oldSelection.filter(
        (id) => !newSelection.includes(id)
      ).length;
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

  let suggestedSelections = traitlet(model, 'suggestedSelections', []);
  let suggestedSelectionWindow = traitlet(
    model,
    'suggestedSelectionWindow',
    []
  );
  let loadingSuggestions = traitlet(model, 'loadingSuggestions', false);
  let loadingSuggestionsProgress = traitlet(
    model,
    'loadingSuggestionsProgress',
    0.0
  );
  let recomputeSuggestionsFlag = traitlet(
    model,
    'recomputeSuggestionsFlag',
    false
  );
  let performanceSuggestionsMode = traitlet(
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

  let selectionUnit = traitlet(model, 'selectionUnit', '');
  let selectionOrderRequest = traitlet(model, 'selectionOrderRequest', {});
  let selectionOrder = traitlet(model, 'selectionOrder', []);
  const SelectionOrderTimeout = 100;

  async function selectionOrderFn(pointID, metric) {
    $selectionOrder = [];
    $selectionOrderRequest = {
      centerID: pointID,
      frame: $currentFrame,
      metric,
    };

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

  let loggingEnabled = traitlet(model, 'loggingEnabled', false);
  let interactionHistory = traitlet(model, 'interactionHistory', []);
  let saveInteractionsFlag = traitlet(model, 'saveInteractionsFlag', false);

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

{#if !dataset || $isLoading}
  <div class="loading-container">
    <div class="spinner-border text-primary" role="status" />
    <div class="loading-message text-center">Loading data...</div>
  </div>
{:else}
  <div class="vis-container" style="height: {fillHeight ? '100%' : '600px'};">
    <div class="frame-sidebar">
      {#if $helpMessagesVisible}
        <HelpMessage width={360}>
          Click a <strong>frame thumbnail</strong> once to compare it with the
          current frame, and click again to animate to that frame. You can
          compare the <strong>color stripes</strong> next to each thumbnail to get
          a sense of how different the frames are.
        </HelpMessage>
      {/if}
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
        {#if $helpMessagesVisible}
          <HelpMessage>
            Search to select a point by its ID number or text description.
          </HelpMessage>
        {/if}
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
          options={sidebarPaneOptions}
        />
      </div>
      <div class="sidebar-content">
        {#if $visibleSidebarPane == SidebarPanes.CURRENT && !!$thumbnailData && !!$neighborData}
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
            emptyMessage="No suggested selections right now.{$performanceSuggestionsMode
              ? ' Suggestions are in performance mode - will compute when less than 1,000 points are displayed.'
              : dataset != null && dataset.frameCount <= 1
                ? ' Add more embeddings to see suggestions.'
                : ''}"
            helpMessage="This view lists <strong>Suggested Selections</strong>, which are groups of points that exhibit potentially interesting changes between frames. Try selecting different frames or moving around the scatter plot to see different suggestions."
            on:loadSelection={(e) => {
              handleLoadSelection(e);
              logEvent({ type: 'loadSelection', source: 'suggested' });
            }}
          />
        {/if}
      </div>
      <div class="action-toolbar">
        {#if $allowsSavingSelections}
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
        {/if}
        <div style="flex-grow: 1" />
        <button
          type="button"
          class="btn btn-sm jp-Dialog-button jp-mod-styled mr-2 {$helpMessagesVisible
            ? 'jp-mod-accept btn-primary'
            : 'jp-mod-reject btn-secondary'}"
          on:click|preventDefault={() =>
            ($helpMessagesVisible = !$helpMessagesVisible)}
        >
          Help
        </button>
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
    display: flex;
    justify-items: stretch;
    /*border: 2px solid #bbb;*/
  }

  .loading-container {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }

  .loading-message {
    padding-top: 12px;
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
    height: 100%;
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

  .mr-2 {
    margin-right: 0.5rem !important; /* from bootstrap */
  }
</style>
