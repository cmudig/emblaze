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
  import { helpMessagesVisible } from './visualization/utils/stores';
  import HelpMessage from './visualization/components/HelpMessage.svelte';
  import { getOSName } from './visualization/utils/helpers';

  // Socket boilerplate

  let connected = false;
  let errorMessage = '';

  let model = new SocketModel();

  let socket = io();

  let app;

  onMount(async () => {
    socket.on('connect', () => {
      connected = true;
      model.attach(socket);
    });
    socket.on('disconnect', () => {
      connected = false;
      model.detach();
      errorMessage =
        'The connection to the server has been lost. Please reload the page to reconnect.';
    });

    try {
      let datasetResult = await fetch('/datasets');
      if (!datasetResult.ok) {
        errorMessage = await datasetResult.text();
      } else {
        datasetOptions = await datasetResult.json();
      }
    } catch (e) {
      errorMessage =
        'An error occurred connecting to the server. Please try again later.';
      console.log('Connection error:', e);
    }
  });

  // Config

  let datasetOptions = [];
  let datasetPath = syncValue(model, 'file', '');

  // let oldDatasetPath = '';
  // $: if (oldDatasetPath != datasetPath) {
  //   $colorScheme = 'tableau';
  //   oldDatasetPath = datasetPath;
  // }

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

  $: if (!!app && !!$colorScheme) {
    validateColorSchemeCompatibility();
  }

  function validateColorSchemeCompatibility() {
    let cs = ColorSchemes.getColorScheme($colorScheme);
    if (
      !!app &&
      !!app.dataset &&
      !app.dataset.supportsContinuousColorSchemes &&
      !!cs &&
      cs.type == 'continuous'
    ) {
      $colorScheme = 'tableau';
      alert('Continuous color schemes are not supported for this dataset.');
    }
  }

  // About

  let isAboutPaneOpen = false;

  let isTutorialPaneOpen = false;
</script>

<main>
  <Modal visible={isAboutPaneOpen} width={400}>
    <div class="dialog-body">
      <h4>Install Emblaze</h4>
      <p>
        Emblaze is available for use as a Jupyter notebook widget. You can
        install it from PyPI:
      </p>
      <pre class="code-snippet">pip install emblaze</pre>
      <p>
        For more detailed instructions and usage examples, please visit the <a
          href="https://github.com/cmudig/emblaze"
          target="_blank">GitHub page</a
        >.
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

  <Modal visible={isTutorialPaneOpen} width={600}>
    <div class="dialog-body">
      <h4>What is Emblaze?</h4>
      <p>
        <strong
          >Emblaze is a visual tool for comparing embedding spaces through
          animated 2D scatter plots.</strong
        > Each provided dataset consists of multiple "frames", or variants for comparison.
        You can navigate between and compare these frames using the thumbnails to
        the left of the main scatter plot.
      </p>
      <p>
        The tool offers a variety of methods to select and browse groups of
        points in each embedding. Try clicking on points, {#if getOSName() == 'MacOS'}Cmd{:else}Ctrl{/if}
        + clicking and dragging to lasso select, or going to the Suggested pane to
        see recommendations.
      </p>
      <p>For more tips, click the Help button in the lower-right corner.</p>
      <p>
        <small>
          Emblaze is provided on a BSD 3-Clause license. To cite Emblaze in your
          publications, please use the following reference:
        </small>
      </p>
      <p>
        <small>
          Sivaraman, V., Wu, Y., and Perer, A. (2022). Emblaze: Illuminating
          Machine Learning Representations through Interactive Comparison of
          Embedding Spaces. <em
            >IUI '22: Proceedings of 27th International Conference on
            Intelligent User Interfaces.</em
          >
        </small>
      </p>
    </div>
    <div class="dialog-footer">
      <button
        type="button"
        class="dialog-footer-button btn btn-secondary jp-Dialog-button jp-mod-reject jp-mod-styled"
        on:click={() => (isTutorialPaneOpen = false)}>Continue</button
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
            href="#"
            on:click={() => (isTutorialPaneOpen = true)}>What is Emblaze?</a
          >
        </li>
        <li class="nav-item">
          <a class="nav-link" href="#" on:click={() => (isAboutPaneOpen = true)}
            >Install</a
          >
        </li>
        <li class="nav-item">
          <a
            class="nav-link"
            href="https://github.com/cmudig/emblaze"
            target="_blank">GitHub</a
          >
        </li>
      </ul>
    </div>
  </nav>
  <div class="mobile-warning">
    <div class="loading-container">
      <div class="loading-message text-center">
        Sorry, Emblaze is not supported on small screen sizes.
      </div>
    </div>
  </div>
  <div class="config-view">
    <div style="display: flex; align-items: center;">
      {#if $helpMessagesVisible}
        <HelpMessage pad={false} width={300}>
          Choose among available <strong>sample datasets</strong> here. You can
          view your own datasets by installing Emblaze and trying it in a
          Jupyter notebook (see
          <a href="https://github.com/cmudig/emblaze" target="_blank">here</a> for
          details).
        </HelpMessage>
      {/if}
      <h6 class="config-item">Dataset</h6>
      <select bind:value={$datasetPath} class="config-item">
        {#each datasetOptions as opt}
          <option value={opt}>{getDatasetName(opt)}</option>
        {/each}
      </select>
      {#if $helpMessagesVisible}
        <HelpMessage pad={false} width={300}>
          Choose the <strong>colors</strong> used to label points. Note that continuous
          color schemes (such as 'turbo' and 'plasma') cannot be used for categorical
          labels.
        </HelpMessage>
      {/if}
      <h6 class="config-item">Color Scheme</h6>
      <select bind:value={$colorScheme} class="config-item">
        {#each ColorSchemes.allColorSchemes as opt}
          <option value={opt.name}>{opt.name}</option>
        {/each}
      </select>
      {#if $helpMessagesVisible}
        <HelpMessage pad={false} width={300}>
          Choose the method used to compute <strong
            >similarity between frames</strong
          > for displaying star trails. 'Projection Neighbors' uses the nearest neighbors
          in the 2D space, while 'Hi-D Neighbors' uses nearest neighbors in the original
          embedding.
        </HelpMessage>
      {/if}
      <h6 class="config-item">Star Trails</h6>
      <select bind:value={$previewMode} class="config-item">
        <option value={PreviewMode.NEIGHBOR_SIMILARITY}>
          High-D Neighbors
        </option>
        <option value={PreviewMode.PROJECTION_SIMILARITY}>
          Projection Neighbors
        </option>
      </select>
    </div>
  </div>

  <div class="visualization-view">
    {#if connected && !errorMessage}
      <App bind:this={app} {model} fillHeight={true} />
    {:else}
      <div class="loading-container">
        {#if !!errorMessage}
          <div class="loading-message text-center">{errorMessage}</div>
        {:else}
          <div class="spinner-border text-primary" role="status" />
          <div class="loading-message text-center">Connecting...</div>
        {/if}
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

  .mobile-warning {
    display: none;
    margin-top: 200px;
    padding: 0 40px;
  }

  .code-snippet {
    padding: 12px;
    background-color: #eeeeee;
    border-radius: 4px;
  }

  @media (max-width: 640px) {
    .mobile-warning {
      display: block;
    }

    .config-view {
      display: none;
    }

    .visualization-view {
      display: none;
    }
  }
</style>
