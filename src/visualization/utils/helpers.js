export function scaleCanvas(c, w, h) {
  // Scales the canvas for the device screen resolution
  var result = c
    .attr('width', w * window.devicePixelRatio)
    .attr('height', h * window.devicePixelRatio)
    .style('width', w + 'px')
    .style('height', h + 'px');

  var context = c.node().getContext('2d');
  context.scale(window.devicePixelRatio, window.devicePixelRatio);
  return result;
}

// Function to create new colours for the hidden canvas.
export function ColorIDMap(format = 'css') {
  this.nextColor = 1;
  this.format = format; // "css" or "hex"

  this.mapping = {};
  this.reverseMapping = {};

  this._next = function () {
    var ret = [];
    if (this.nextColor < 16777215) {
      ret.push(this.nextColor & 0xff); // R
      ret.push((this.nextColor & 0xff00) >> 8); // G
      ret.push((this.nextColor & 0xff0000) >> 16); // B
      this.nextColor += 5;
    }
    if (this.format == 'css') return 'rgb(' + ret.join(',') + ')';
    else if (this.format == 'hex') return this.nextColor;
  };

  this.id = function (id, obj = null) {
    if (!this.mapping.hasOwnProperty(id)) this.mapping[id] = this._next();
    this.reverseMapping[this.mapping[id]] = obj || id;

    return this.mapping[id];
  };

  this.obj = function (color) {
    return this.reverseMapping[color];
  };
}

export function colorWithOpacity(stringVal, opacity) {
  var rgb = stringVal.substring(4, stringVal.length - 1);
  return 'rgba(' + rgb + ', ' + opacity + ')';
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
  if (typeof obj1 == 'number' && typeof obj2 == 'number') {
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

// Transforms the [x, y] point by the given transform 3x3 list (row-major).
export function transformPoint(transform, point) {
  return [
    transform[0][0] * point[0] + transform[0][1] * point[1] + transform[0][2],
    transform[1][0] * point[0] + transform[1][1] * point[1] + transform[1][2],
  ];
}

export function hexToRgb(hex) {
  var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? [
        parseInt(result[1], 16) / 255.0,
        parseInt(result[2], 16) / 255.0,
        parseInt(result[3], 16) / 255.0,
      ]
    : [0, 0, 0];
}

export function makeTimeProvider() {
  var currentTime = 0;
  let fn = function () {
    return currentTime;
  };
  fn.advance = function (dt) {
    currentTime += dt;
  };
  return fn;
}

export function distance2(a, b) {
  let dx = a.x - b.x;
  let dy = a.y - b.y;
  return dx * dx + dy * dy;
}

export function euclideanDistance(a, b) {
  return Math.sqrt(distance2(a, b));
}

export class ValueHistory {
  lastValues = {};

  update(newValues) {
    let changed = false;
    Object.keys(newValues).forEach((key) => {
      changed = changed || !approxEquals(newValues[key], this.lastValues[key]);
      this.lastValues[key] = newValues[key];
    });
    return changed;
  }
}

export function base64ToBlob(b64Data, contentType = '', sliceSize = 512) {
  const byteCharacters = atob(b64Data);
  const byteArrays = [];

  for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
    const slice = byteCharacters.slice(offset, offset + sliceSize);

    const byteNumbers = new Array(slice.length);
    for (let i = 0; i < slice.length; i++) {
      byteNumbers[i] = slice.charCodeAt(i);
    }

    const byteArray = new Uint8Array(byteNumbers);
    byteArrays.push(byteArray);
  }

  const blob = new Blob(byteArrays, { type: contentType });
  return blob;
}

/**
 * Uses canvas.measureText to compute and return the width of the given text of given font in pixels.
 *
 * @param {String} text The text to be rendered.
 * @param {String} font The css font descriptor that text is to be rendered with (e.g. "bold 14px verdana").
 *
 * @see https://stackoverflow.com/questions/118241/calculate-text-width-with-javascript/21015393#21015393
 */
export function getTextWidth(text, font) {
  // re-use canvas object for better performance
  var canvas =
    getTextWidth.canvas ||
    (getTextWidth.canvas = document.createElement('canvas'));
  var context = canvas.getContext('2d');
  context.font = font;
  var metrics = context.measureText(text);
  return metrics.width;
}

/**
 * @returns the most likely OS the user is running ("Windows", "MacOS", "UNIX", or "Linux").
 */
export function getOSName() {
  if (navigator.appVersion.indexOf('Win') != -1) return 'Windows';
  if (navigator.appVersion.indexOf('Mac') != -1) return 'MacOS';
  if (navigator.appVersion.indexOf('X11') != -1) return 'UNIX';
  if (navigator.appVersion.indexOf('Linux') != -1) return 'Linux';

  return 'Unknown';
}
