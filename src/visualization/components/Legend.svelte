<script>
  import * as d3 from 'd3';
  import * as d3legend from 'd3-svg-legend';
  import { onMount } from 'svelte';

  export let width = 600;
  export let height = 500;
  export let colorScale = null;
  export let numCells = 10; // for continuous
  export let type = 'categorical';

  let container;
  let svg;

  let oldColorScale = null;
  $: if (oldColorScale != colorScale && !!container) {
    update();
    oldColorScale = colorScale;
  }

  function update() {
    if (!!svg) svg.remove();

    if (!colorScale) return;

    let totalWidth;
    let totalHeight;
    if (type == 'categorical') {
      totalWidth = 300;
      totalHeight = colorScale.domain().length * 25 - 5 + 20;
    } else if (type == 'continuous') {
      totalWidth = 30 * numCells + 1 * (numCells - 1) + 40;
      totalHeight = 100;
    }

    svg = d3
      .select(container)
      .append('svg')
      .style('width', totalWidth)
      .style('height', totalHeight)
      .style('font-family', 'sans-serif');

    if (type == 'categorical') {
      //let domainLabels = colorScale.domain();
      svg
        .append('g')
        .attr('class', 'legendOrdinal')
        .attr('transform', 'translate(20, 20)');

      let legendOrdinal = d3legend
        .legendColor()
        .shape('circle')
        .shapePadding(5)
        .shapeRadius(10)
        .orient('vertical')
        .scale(colorScale);

      svg.select('.legendOrdinal').call(legendOrdinal);
    } else if (type == 'continuous') {
      svg
        .append('g')
        .attr('class', 'legendLinear')
        .attr('transform', 'translate(20,20)');

      let legendLinear = d3legend
        .legendColor()
        .shapeWidth(30)
        .shapePadding(1)
        .cells(numCells)
        .orient('horizontal')
        .scale(colorScale);

      svg.select('.legendLinear').call(legendLinear);
    }
  }

  onMount(() => {
    console.log('updating mount');
    update();
  });
</script>

<div
  bind:this={container}
  style="position: relative; max-width: {width}px; max-height: {height}px;"
/>
