<script>
  import { dummyData } from './dummy-data/data.js';
  import SynchronizedScatterplot from './visualization/SynchronizedScatterplot.svelte';
  import * as d3 from 'd3';

  export let model;

  // Creates a Svelte store (https://svelte.dev/tutorial/writable-stores) that syncs with the named Traitlet in widget.ts and example.py.
  import { syncValue } from './stores';
  import { Dataset } from './visualization/dataset.js';
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  let data = syncValue(model, 'data', {});

  let dataset = null;
  $: if (!!$data && !!$data['data']) {
    dataset = new Dataset($data, 'color', 3);
  } else {
    dataset = null;
  }

  onMount(() => {
    // This logs if the widget is initialized successfully
    console.log('Mounted DR widget successfully');
  });
</script>

<SynchronizedScatterplot
  data={dataset}
  hoverable
  animateTransitions
  width={400}
  height={400}
  colorScheme={{
    name: 'tableau',
    value: d3.schemeTableau10,
    type: 'categorical',
  }}
/>

<style>
</style>
