<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { Dataset, PreviewMode } from './visualization/models/dataset';
  import TemporalVisualization from './visualization/TemporalVisualization.svelte';
  import SpatialVisualization from './visualization/SpatialVisualization.svelte';
  import ColorSchemes from './colorschemes';

  let datasetOptions = ['mnist-tsne'];
  let datasetName = 'mnist-tsne';

  let colorChannel = 'constant';
  let colorChannelOptions = ['constant'];

  let colorScheme = ColorSchemes.getColorScheme('tableau');

  let useHalos = false;

  let thumbnailsURL = '';
  let thumbnailData;

  var data = null;
  let previewMode = PreviewMode.PROJECTION_SIMILARITY;

  let visualizationMode = 'temporal'; // "spatial" or "temporal"

  let visualization;

  onMount(async () => {
    datasetOptions = await (await fetch('/datasets')).json();
  });

  // Simple method to get a list of quantitative channels in the data
  function getQuantitativeChannels(frame) {
    let ids = Object.keys(frame);
    let testItem = frame[ids[0]];
    let fields = Object.keys(testItem);
    return fields.filter(
      (f) => typeof testItem[f] == 'number' || typeof testItem[f] == 'string'
    );
  }

  function getChannelType(channelName) {
    let frame = data.frame(0);
    let ids = Object.keys(frame);
    let testItem = frame[ids[0]];
    return typeof testItem[channelName];
  }

  let oldColorChannel = null;
  let oldDatasetName = null;

  $: if (oldDatasetName != datasetName || oldColorChannel != colorChannel) {
    fetchData(datasetName, oldDatasetName != datasetName);
    oldDatasetName = datasetName;
    oldColorChannel = colorChannel;
  }

  async function fetchData(datasetName, resetColor = true) {
    try {
      let result = await fetch('/datasets/' + datasetName + '/data');
      let respJSON = await result.json();
      let thumbnailJSON;
      try {
        result = await fetch('/datasets/' + datasetName + '/thumbnails');
        thumbnailJSON = await result.json();
      } catch (error) {
        console.log(error);
      } finally {
        initializeData(respJSON, resetColor);
        if (!!thumbnailJSON) {
          thumbnailData = thumbnailJSON;
          data.addThumbnails(thumbnailData);
          setTimeout(() => {
            if (!!visualization) visualization.updateThumbnails();
          }, 0);
          thumbnailsURL = '/datasets/' + datasetName + '/supplementary';
        }
      }
    } catch (error) {
      console.log(error);
    }
  }

  function initializeData(respJSON, resetColor = true) {
    let testFrame;
    if (!!respJSON['data']) testFrame = respJSON['data'][0];
    else testFrame = respJSON[0];
    let options = ['constant', ...getQuantitativeChannels(testFrame)];
    colorChannelOptions = options;
    if (resetColor || !options.includes(colorChannel)) {
      if (options.includes('color')) {
        // Automatically initialize it to color
        colorChannel = 'color';
      } else {
        colorChannel = 'constant';
      }
    }
    oldColorChannel = colorChannel; // this prevents the color channel reloader from being called
    console.log('Initializing data', respJSON);
    data = new Dataset(respJSON, colorChannel, 3);
    if (data.previewMode != previewMode) previewMode = data.previewMode;
    let colorType = getChannelType(colorChannel);
    if (
      (colorType == 'string' || colorType == 'object') &&
      colorScheme.type != 'categorical'
    ) {
      colorScheme = ColorSchemes.defaultColorScheme('categorical');
    }
  }

  $: if (!!data) data.setPreviewMode(previewMode);

  async function alignVisualization(e) {
    let { baseFrame, alignedIDs } = e.detail;
    try {
      let postBody = { ids: alignedIDs };
      if (
        !!data.frameTransformations &&
        data.frameTransformations.length > baseFrame
      ) {
        postBody.initialTransform = data.frameTransformations[baseFrame];
      }

      let response = await fetch(`/align/${datasetName}/${baseFrame}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(postBody),
      });
      let result = await response.json();
      if (!!result && !!result.transformations) {
        data.transform(result.transformations);
        visualization.animateDatasetUpdate();
      }
      return null;
    } catch (error) {
      console.log('Error aligning points:', error);
      return null;
    }
  }
</script>

<main>
  <div class="config-view">
    <h3>Dataset Configuration</h3>
    <div style="display: flex">
      <select bind:value={datasetName} class="config-item">
        {#each datasetOptions as opt}
          <option value={opt}>{opt}</option>
        {/each}
      </select>
      <select bind:value={colorChannel} class="config-item">
        {#each colorChannelOptions as opt}
          <option value={opt}>{opt}</option>
        {/each}
      </select>
      <select bind:value={colorScheme} class="config-item">
        {#each ColorSchemes.allColorSchemes as opt}
          <option value={opt}>{opt.name}</option>
        {/each}
      </select>
      <label class="config-item"
        ><input type="checkbox" bind:checked={useHalos} />
        Halos</label
      >
      <select bind:value={previewMode} class="config-item">
        {#each Object.values(PreviewMode) as mode}
          <option value={mode}>{mode}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="visualization-view">
    <TemporalVisualization
      bind:this={visualization}
      {data}
      {thumbnailsURL}
      {thumbnailData}
      {colorScheme}
      {useHalos}
      on:align={alignVisualization}
    />
  </div>
</main>

<style>
  main {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  .config-item {
    margin-right: 16px;
  }
  .visualization-view {
    flex: 1;
    overflow: scroll;
  }
</style>
