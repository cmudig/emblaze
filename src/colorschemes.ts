// import * as d3 from "d3";
const d3 = require('d3');

class ColorScheme {
  name: string;
  value: Function;
  type: string;

  constructor(name: string, value: Function, type = 'continuous') {
    this.name = name;
    this.value = value;
    this.type = type;
  }
}

let colorSchemes: Array<ColorScheme> = [
  new ColorScheme('turbo', d3.interpolateTurbo),
  new ColorScheme('tableau', d3.schemeTableau10, 'categorical'),
  new ColorScheme('plasma', d3.interpolatePlasma),
  new ColorScheme('magma', d3.interpolateMagma),
  new ColorScheme('viridis', d3.interpolateViridis),
  new ColorScheme('RdBu', d3.interpolateRdBu),
  new ColorScheme('Blues', d3.interpolateBlues),
  new ColorScheme('Greens', d3.interpolateGreens),
  new ColorScheme('Reds', d3.interpolateReds),
  new ColorScheme('rainbow', d3.interpolateRainbow),
];

function getColorScheme(name: string): ColorScheme | undefined {
  return colorSchemes.find((item) => item.name == name);
}

export default {
  getColorScheme,
  defaultColorScheme(dataType: string): ColorScheme | undefined {
    if (dataType == 'categorical') return getColorScheme('tableau');
    return getColorScheme('plasma');
  },
  allColorSchemes: colorSchemes.map((v) => v),
};
