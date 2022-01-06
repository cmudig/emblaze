<script>
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import { Dataset, PreviewMode } from './visualization/models/dataset';
  import TemporalVisualization from './visualization/TemporalVisualization.svelte';
  import SpatialVisualization from './visualization/SpatialVisualization.svelte';
  import Modal from './visualization/components/Modal.svelte';
  import ColorSchemes from './colorschemes';
  import { ThumbnailProvider } from './visualization/models/thumbnails';
  import { SocketModel } from './socketstores';
  import App from './App.svelte';
  import { syncValue } from './stores';
  import { MODULE_VERSION } from './version';

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
    let match = path.match(/\/([^\/.]+)\.json/);
    if (!match) return '';
    return match[1];
  }

  let colorScheme = syncValue(model, 'colorScheme', 'tableau');
  let previewMode = syncValue(
    model,
    'previewMode',
    PreviewMode.PROJECTION_SIMILARITY
  );

  // About

  let isAboutPaneOpen = false;
</script>

<main>
  <Modal visible={isAboutPaneOpen} width={400}>
    <div class="dialog-body">
      <h4>Emblaze v{MODULE_VERSION}</h4>
      <p>
        This software is provided on a BSD 3-Clause license. To cite Emblaze in
        your publications, please use the following reference:
      </p>
      <p>
        Sivaraman, V., Wu, Y., and Perer, A. (2022). Emblaze: Illuminating
        Machine Learning Representations through Interactive Comparison of
        Embedding Spaces. <em
          >IUI '22: Proceedings of 27th International Conference on Intelligent
          User Interfaces.</em
        >
      </p>
    </div>
    <div class="dialog-footer">
      <button
        type="button"
        class="dialog-footer-button btn btn-secondary jp-Dialog-button jp-mod-reject jp-mod-styled"
        on:click={() => (isAboutPaneOpen = false)}>Close</button
      >
    </div>
  </Modal>

  <nav
    class="title-bar navbar navbar-expand-lg navbar-dark"
    style="justify-content: space-between;"
  >
    <span class="navbar-brand">Emblaze Demo</span>
    <button
      class="navbar-toggler"
      type="button"
      data-toggle="collapse"
      data-target="#navbarSupportedContent"
      aria-controls="navbarSupportedContent"
      aria-expanded="false"
      aria-label="Toggle navigation"
    >
      <span class="navbar-toggler-icon" />
    </button>

    <div
      class="collapse navbar-collapse"
      style="flex-grow: 0;"
      id="navbarSupportedContent"
    >
      <ul class="navbar-nav">
        <li class="nav-item">
          <a
            class="nav-link"
            href="https://github.com/cmudig/emblaze"
            target="_blank">GitHub</a
          >
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#" on:click={() => (isAboutPaneOpen = true)}
            >About</a
          >
        </li>
      </ul>
    </div>
  </nav>
  <div class="config-view">
    <div style="display: flex; align-items: center;">
      <h6 class="config-item">Dataset</h6>
      <select bind:value={$datasetPath} class="config-item">
        {#each datasetOptions as opt}
          <option value={opt}>{getDatasetName(opt)}</option>
        {/each}
      </select>
      <h6 class="config-item">Color Scheme</h6>
      <select bind:value={$colorScheme} class="config-item">
        {#each ColorSchemes.allColorSchemes as opt}
          <option value={opt.name}>{opt.name}</option>
        {/each}
      </select>
      <h6 class="config-item">Star Trails</h6>
      <select bind:value={$previewMode} class="config-item">
        <option value={PreviewMode.NEIGHBOR_SIMILARITY}>
          High-D Neighbors
        </option>
        <option value={PreviewMode.NEIGHBOR_SIMILARITY}>
          Projection Neighbors
        </option>
      </select>
    </div>
  </div>

  <div class="visualization-view">
    {#if connected}
      <App {model} fillHeight={true} />
    {:else}
      <div class="loading-container">
        <div class="spinner-border text-primary" role="status" />
        <div class="loading-message text-center">Connecting...</div>
      </div>
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
  .title-bar {
    background-color: darkslateblue;
    color: white;
  }
  .config-view {
    padding: 12px;
    background-color: #eee;
    border-bottom: 1px solid #bbb;
  }
  .config-item {
    margin-right: 16px;
    margin-bottom: 0;
  }
  .visualization-view {
    flex: 1;
    overflow: scroll;
    padding: 8px;
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
</style>
