<script>
  import { createEventDispatcher } from 'svelte';

  export let name = '';
  export let description = '';

  const dispatch = createEventDispatcher();
</script>

<div class="dialog-body">
  <form>
    <div class="form-group">
      <label for="name-of-selection" class="col-form-label"
        >Name of Selection:</label
      >
      <br />
      <input
        type="text"
        class="form-control"
        id="name-of-selection"
        bind:value={name}
      />
    </div>
    <div class="form-group">
      <label for="description" class="col-form-label">Description:</label>
      <br />
      <textarea
        class="form-control"
        id="description"
        bind:value={description}
      />
    </div>
  </form>
  <div class="summary-info">
    <h5>SUMMARY</h5>
    <slot name="summary" />
  </div>
</div>
<div class="dialog-footer">
  <button
    type="button"
    class="dialog-footer-button btn btn-secondary jp-Dialog-button jp-mod-reject jp-mod-styled"
    on:click={() => dispatch('cancel')}>Cancel</button
  >
  <button
    type="button"
    class="dialog-footer-button btn btn-primary jp-Dialog-button jp-mod-accept jp-mod-styled"
    on:click={() => dispatch('save')}
    >Save
  </button>
</div>

<style>
  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    padding-top: 12px;
  }

  .dialog-footer-button {
    margin-left: 12px;
    margin-right: 0 !important;
  }

  .summary-info {
    color: #666;
  }

  .summary-info p {
    margin: 0;
  }
</style>
