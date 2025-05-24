<script>
  import * as d3 from 'd3';
  import * as d3legend from 'd3-svg-legend';
  import { onMount } from 'svelte';
  import { getTextWidth } from '../utils/helpers';

  export let width = 600;
  export let height = 500;
  export let colorScale = null;
  export let numCells = 10; // for continuous
  export let type = 'categorical';

  export let fontSize = 12;
  export let fontWeight = 'normal';
  export let fontFamily = 'sans-serif';

  const CategoryRadius = 8;
  const CategoryPadding = 8;
  const ContinuousWidth = 30;
  const ContinuousPadding = 1;

  let container;
  let svg;

  $: if (!!colorScale && width > 0 && height > 0 && !!container) {
    update();
  }

  function update() {
    if (!!svg) svg.remove();

    if (!colorScale) return;

    let totalWidth;
    let totalHeight;
    if (type == 'categorical') {
      totalWidth =
        Math.max(
          ...colorScale
            .domain()
            .map((v) =>
              getTextWidth(v, `${fontWeight} ${fontSize}pt ${fontFamily}`)
            )
        ) +
        CategoryRadius * 2 +
        40;
      totalHeight =
        colorScale.domain().length * (CategoryRadius * 2 + CategoryPadding) -
        CategoryPadding +
        40;
    } else if (type == 'continuous') {
      totalWidth =
        ContinuousWidth * numCells + ContinuousPadding * (numCells - 1) + 40;
      totalHeight = 60;
    }

    svg = d3
      .select(container)
      .append('svg')
      .style('width', `${totalWidth}px`)
      .style('height', `${totalHeight}px`)
      .style('font-size', `${fontSize}pt`)
      .style('font-weight', fontWeight)
      .style('font-family', fontFamily);

    if (type == 'categorical') {
      //let domainLabels = colorScale.domain();
      svg
        .append('g')
        .attr('class', 'legendOrdinal')
        .attr('transform', 'translate(20, 20)');

      let legendOrdinal = d3legend
        .legendColor()
        .shape('circle')
        .shapeRadius(CategoryRadius)
        .shapePadding(CategoryPadding)
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
        .shapeWidth(ContinuousWidth)
        .shapePadding(ContinuousPadding)
        .cells(numCells)
        .orient('horizontal')
        .scale(colorScale);

      svg.select('.legendLinear').call(legendLinear);
    }
  }

  onMount(() => {
    setTimeout(update, 0);
  });
</script>

<div
  bind:this={container}
  class="legend-container"
  style="max-width: {width}px; max-height: {height}px;"
/>

<style>
  .legend-container {
    position: relative;
    pointer-events: none;
  }
</style>
