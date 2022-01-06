<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { Dataset, PreviewMode } from './visualization/models/dataset';
  import TemporalVisualization from './visualization/TemporalVisualization.svelte';
  import SpatialVisualization from './visualization/SpatialVisualization.svelte';
  import ColorSchemes from './colorschemes';
  import { ThumbnailProvider } from './visualization/models/thumbnails';
  import { SocketModel } from './socketstores';
  import App from './App.svelte';
  import { syncValue } from './stores';

  // Socket boilerplate

  let connected = false;

  let model = new SocketModel();

  let socket = io();

  onMount(async () => {
    datasetOptions = await (await fetch('/datasets')).json();

    socket.on('connect', () => {
      connected = true;
      model.attach(socket);
    });
    socket.on('disconnect', () => {
      connected = false;
      model.detach();
    });
  });

  // Config

  let datasetOptions = [];
  let datasetPath = syncValue(model, 'file', '');

  function getDatasetName(path) {
    let match = path.match(/\/([^\/]+)\/data.json/);
    if (!match) return '';
    return match[1];
  }

  let colorScheme = syncValue(model, 'colorScheme', 'tableau');
  let previewMode = syncValue(
    model,
    'previewMode',
    PreviewMode.PROJECTION_SIMILARITY
  );
</script>

<main>
  <div class="config-view">
    <h3>Dataset Configuration</h3>
    <div style="display: flex">
      <select bind:value={$datasetPath} class="config-item">
        {#each datasetOptions as opt}
          <option value={opt}>{getDatasetName(opt)}</option>
        {/each}
      </select>
      <select bind:value={$colorScheme} class="config-item">
        {#each ColorSchemes.allColorSchemes as opt}
          <option value={opt.name}>{opt.name}</option>
        {/each}
      </select>
      <select bind:value={$previewMode} class="config-item">
        {#each Object.values(PreviewMode) as mode}
          <option value={mode}>{mode}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="visualization-view">
    {#if connected}
      <App {model} fillHeight={true} />
    {:else}
      <p>Disconnected from server!</p>
    {/if}
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
