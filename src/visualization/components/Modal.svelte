<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { fade } from 'svelte/transition';

  const dispatch = createEventDispatcher();

  // set this to toggle visibility of the modal
  export let visible = false;
  // adjust width of the modal in pixels
  export let width = 300;
</script>

{#if visible}
  <div class="dimmer-view" transition:fade>
    <div class="modal-container" style="width: {width}px;">
      <slot />
    </div>
  </div>
{/if}

<style>
  .dimmer-view {
    z-index: 10;
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background-color: rgba(0, 0, 0, 0.6);
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .modal-container {
    z-index: 11;
    padding: 32px;
    background-color: white;
    border-radius: 8px;
  }
</style>
