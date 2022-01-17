<script>
  import Icon from 'fa-svelte';
  import { faInfoCircle } from '@fortawesome/free-solid-svg-icons/faInfoCircle';

  let messageVisible = false;
  export let width = 200;

  export let pad = true;

  export let anchor = 'upper left';
</script>

<div class="help-message-container" class:help-message-padded={pad}>
  <div class="help-message-wrapper">
    {#if messageVisible}
      <div
        class="help-message"
        class:anchor-upper={anchor.includes('upper')}
        class:anchor-lower={anchor.includes('lower')}
        class:anchor-left={anchor.includes('left')}
        class:anchor-right={anchor.includes('right')}
        style="width: {width}px;"
      >
        <button
          class="btn btn-link text-muted help-button bp3-button bp3-minimal jp-ToolbarButtonComponent minimal jp-Button"
          on:click={() => (messageVisible = false)}
        >
          &#x2715;
        </button>
        <p class="help-message-text">
          <slot />
        </p>
      </div>
    {:else}
      <button
        class="btn btn-link text-muted help-button bp3-button bp3-minimal jp-ToolbarButtonComponent minimal jp-Button"
        on:click={() => (messageVisible = true)}
      >
        <Icon icon={faInfoCircle} />
      </button>
    {/if}
  </div>
</div>

<style>
  .help-message-container {
    width: 24px;
    height: 24px;
    overflow-x: visible;
    overflow-y: visible;
    position: relative;
  }

  .help-message-padded {
    margin: 8px;
  }

  .help-message-wrapper {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
  }

  .help-button {
    width: 24px;
    height: 24px;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
    top: 0;
    left: 0;
    padding: 4px !important;
  }

  .help-button:hover {
    text-decoration: none !important;
  }

  .help-message {
    display: flex;
    align-items: flex-start;
    background-color: white;
    box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    position: relative;
    z-index: 1000;
  }

  .anchor-upper {
    top: 0;
  }

  .anchor-lower {
    top: 100%;
    transform: translateY(-100%);
  }

  .anchor-left {
    left: 0;
  }

  .anchor-right {
    left: 100%;
    transform: translateX(-100%);
  }

  .help-message-text {
    padding: 12px 12px 12px 0;
    flex-grow: 1;
    margin-bottom: 0;
  }
</style>
