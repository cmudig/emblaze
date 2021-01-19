export function scaleCanvas(c, w, h) {
  // Scales the canvas for the device screen resolution
  var result = c
    .attr("width", w * window.devicePixelRatio)
    .attr("height", h * window.devicePixelRatio)
    .style("width", w + "px")
    .style("height", h + "px");

  var context = c.node().getContext("2d");
  context.scale(window.devicePixelRatio, window.devicePixelRatio);
  return result;
}

// Function to create new colours for the hidden canvas.
export function ColorGenerator() {
  this.nextColor = 1;

  this.next = function () {
    var ret = [];
    if (this.nextColor < 16777215) {
      ret.push(this.nextColor & 0xff); // R
      ret.push((this.nextColor & 0xff00) >> 8); // G
      ret.push((this.nextColor & 0xff0000) >> 16); // B
      this.nextColor += 5;
    }
    var col = "rgb(" + ret.join(",") + ")";
    return col;
  };
}

export function colorWithOpacity(stringVal, opacity) {
  var rgb = stringVal.substring(4, stringVal.length - 1);
  return "rgba(" + rgb + ", " + opacity + ")";
}

export function shuffle(array) {
  var currentIndex = array.length,
    temporaryValue,
    randomIndex;

  // While there remain elements to shuffle...
  while (0 !== currentIndex) {
    // Pick a remaining element...
    randomIndex = Math.floor(Math.random() * currentIndex);
    currentIndex -= 1;

    // And swap it with the current element.
    temporaryValue = array[currentIndex];
    array[currentIndex] = array[randomIndex];
    array[randomIndex] = temporaryValue;
  }

  return array;
}

export function getWithFallback(obj, attrName, fallback) {
  if (obj[attrName] == undefined) return fallback;
  return obj[attrName];
}

export function approxEquals(obj1, obj2) {
  if (typeof obj1 == "number" && typeof obj2 == "number") {
    return Math.abs(obj1 - obj2) <= 0.001;
  }
  return obj1 == obj2;
}

// Normalizes a 2D vector
export function normalizeVector(vec) {
  let mag = Math.sqrt(vec[0] * vec[0] + vec[1] * vec[1]);
  return [vec[0] / mag, vec[1] / mag];
}

// points should be an array of objects with x and y properties
export function boundingBox(points) {
  let minX = 1e9;
  let maxX = -1e9;
  let minY = 1e9;
  let maxY = -1e9;
  points.forEach((point) => {
    if (point.x < minX) minX = point.x;
    if (point.x > maxX) maxX = point.x;
    if (point.y < minY) minY = point.y;
    if (point.y > maxY) maxY = point.y;
  });
  return { x: [minX, maxX], y: [minY, maxY] };
}

// Pads outward
export function padExtent(extent, padding) {
  return [extent[0] - padding, extent[1] + padding];
}
