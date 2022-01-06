<script>
  export let selected = 1;
  export let options = [
    { value: 1, name: 'A' },
    { value: 2, name: 'B' },
  ];
</script>

<ul class="segmented-control">
  {#each options as option, i}
    <li
      class="segmented-control__item"
      style="width: {(100.0 / options.length).toFixed(0)}%;"
    >
      <input
        class="segmented-control__input"
        type="radio"
        value={option.value}
        name="option"
        id="option-{i + 1}"
        bind:group={selected}
      />
      <label class="segmented-control__label" for="option-{i + 1}"
        >{option.name}</label
      >
    </li>
  {/each}
</ul>

<style>
  .segmented-control {
    display: table;
    width: 100%;
    margin: 0;
    padding: 0;
  }

  .segmented-control__item {
    display: table-cell;
    margin: 0;
    padding: 0;
    list-style-type: none;
  }

  .segmented-control__input {
    position: absolute;
    visibility: hidden;
  }

  .segmented-control__label {
    display: block;
    padding: 4px 0;

    border: 1px solid #555;
    border-right: none;

    font: 12px/1.5 sans-serif;
    text-align: center;

    cursor: pointer;
  }

  .segmented-control__item:last-child .segmented-control__label {
    border-right: 1px solid #555;
  }

  .segmented-control__label:hover {
    background: #ddd;
  }

  .segmented-control__input:checked + .segmented-control__label {
    background: #555;
    color: white;
  }
</style>
