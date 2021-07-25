<script>
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  export let fillWidth = false;
  export let placeholder = 'Search...';
  export let maxOptions = -1;
  let autocomplete;
  let autocompleteDropdownVisible = false;
  let autocompleteDropdown;
  let autocompleteText;

  let selectedItem = null;

  // Should contain a value attribute and a text attribute
  export let options = [];

  let visibleOptions = [];

  $: {
    if (!!autocompleteText) {
      let searchTerm = autocompleteText.toLocaleLowerCase();
      visibleOptions = options.filter((item) =>
        item.text.toLocaleLowerCase().includes(searchTerm)
      );
      if (maxOptions >= 0 && visibleOptions.length > maxOptions)
        visibleOptions = visibleOptions.slice(0, maxOptions);
    } else {
      visibleOptions = [];
    }
  }

  function onPointSelectorItemClick(itemID) {
    selectedItem = itemID;
    dispatch('change', itemID);
  }

  $: if (selectedItem != null) autocompleteText = selectedItem.toString();
</script>

<div class="autocomplete-container" style={fillWidth ? 'width: 100%;' : ''}>
  <input
    type="text"
    {placeholder}
    bind:this={autocomplete}
    bind:value={autocompleteText}
    data-toggle="dropdown"
    on:focus={() => (autocompleteDropdownVisible = true)}
    on:blur={() => {
      setTimeout(() => (autocompleteDropdownVisible = false), 100);
    }}
    style={fillWidth ? 'width: 100%;' : ''}
  />
  <ul
    class="dropdown-menu"
    bind:this={autocompleteDropdown}
    style="visibility: {autocompleteDropdownVisible ? 'visible' : 'hidden'}"
    role="menu"
  >
    {#each visibleOptions as option}
      <div
        class="dropdown-item"
        on:click={() => onPointSelectorItemClick(option.value)}
      >
        {option.text}
      </div>
    {/each}
  </ul>
</div>

<style>
  .autocomplete-container {
    position: relative;
  }
  .dropdown-item {
    padding: 4px 12px;
  }
  .dropdown-item:hover {
    background-color: #ddd;
    cursor: pointer;
  }

  /* These styles are borrowed from bootstrap's dropdowns.less to ensure compatibility
  when bootstrap styles are not available */
  .dropdown-menu {
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 100;
    float: left;
    min-width: 160px;
    padding: 4px 0;
    margin: 1px 0 0;
    list-style: none;
    background-color: white;
    border: 1px solid #ccc;
    border: 1px solid rgba(0, 0, 0, 0.2);
    border-radius: 5px;
    box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
    -webkit-background-clip: padding-box;
    -moz-background-clip: padding;
    background-clip: padding-box;
  }
</style>
