import * as d3 from 'd3';
import * as math from 'mathjs';
import { transformPoint } from '../utils/helpers.js';
import {
  ColumnarData,
  ColumnarFrame,
  FramePreview,
  NeighborPreview,
  PrecomputedPreview,
  ProjectionPreview,
} from './frames';

export const PreviewMode = {
  PROJECTION_SIMILARITY: 'projectionNeighborSimilarity',
  NEIGHBOR_SIMILARITY: 'neighborSimilarity',
  PRECOMPUTED: 'precomputed',
};

export class Dataset {
  frames = [];
  frameTransformations = [];
  colorKey = 'color';
  length = 0; // number of points
  frameCount = 0;
  hasPreviews = false;
  previewMode = PreviewMode.PROJECTION_SIMILARITY;
  previewParameters = {};
  ids = [];

  thumbnailData = null;
  spritesheets = null;

  constructor(rawData, colorKey) {
    let frameSource;
    if (rawData['data']) {
      // There are other keys
      frameSource = rawData.data;
      this.previews = rawData.previews;
      this.frameLabels = rawData.frameLabels;
      this.previewMode =
        rawData.previewMode || PreviewMode.PROJECTION_SIMILARITY;
    } else {
      // Old format
      frameSource = rawData;
      this.frameLabels = frameSource.map((f, i) => 'Frame ' + (i + 1));
    }
    this.colorKey = colorKey;

    this.frameCount = frameSource.length;
    this.hasPreviews = !!this.previews;
    this.reformat(frameSource);
  }

  reformat(rawData) {
    if (rawData.length == 0) return;

    this.frames = rawData.map((frame, f) => {
      return new ColumnarFrame(frame, this.frameLabels[f], (el) => {
        let point = [el.x, el.y];
        if (
          !!this.frameTransformations &&
          this.frameTransformations.length > f
        ) {
          point = transformPoint(this.frameTransformations[f], point);
        }
        return {
          x: point[0],
          y: point[1],
          color: this.colorKey == 'constant' ? 0.0 : el[this.colorKey] || 0.0,
          alpha: el.alpha != undefined ? el.alpha : 1.0,
          highlight: el.highlight.map((h) => parseInt(h)),
          r: 1.0,
          visible: true,
        };
      });
    });

    let allIDs = new Set();
    this.frames.forEach((frame) => {
      frame.getIDs().forEach((id) => allIDs.add(id));
    });
    this.ids = Array.from(allIDs);
    this.length = this.ids.length;
  }

  getXExtent() {
    if (!this._xExtent) {
      let minVal = 1e9;
      let maxVal = -1e9;
      this.frames.forEach((frame) => {
        let field = frame.getField('x');
        minVal = field.reduce((curr, val) => Math.min(curr, val), minVal);
        maxVal = field.reduce((curr, val) => Math.max(curr, val), maxVal);
      });
      this._xExtent = [minVal, maxVal];
    }
    return this._xExtent;
  }

  getYExtent() {
    if (!this._yExtent) {
      let minVal = 1e9;
      let maxVal = -1e9;
      this.frames.forEach((frame) => {
        let field = frame.getField('y');
        minVal = field.reduce((curr, val) => Math.min(curr, val), minVal);
        maxVal = field.reduce((curr, val) => Math.max(curr, val), maxVal);
      });
      this._yExtent = [minVal, maxVal];
    }
    return this._yExtent;
  }

  getColorExtent(categorical = false) {
    if (categorical) {
      let uniqueColors = new Set();
      this.frames.forEach((frame) => {
        frame.getField('color').forEach((c) => uniqueColors.add(c));
      });
      this._colorExtent = Array.from(uniqueColors).sort();
    } else {
      let minVal = 1e9;
      let maxVal = -1e9;
      this.frames.forEach((frame, f) => {
        let field = frame.getField('color');
        minVal = field.reduce((curr, val) => Math.min(curr, val), minVal);
        maxVal = field.reduce((curr, val) => Math.max(curr, val), maxVal);
      });
      this._colorExtent = [minVal, maxVal];
    }
    return this._colorExtent;
  }

  // Generates a color scale function using the given color scheme. The input
  // object can have a 'type' property (either "continuous" or "categorical"),
  // as well as a 'value' property that defines a d3 color scale function.
  colorScale(scheme) {
    let colorType = scheme.type || 'continuous';
    if (colorType == 'categorical') {
      return d3.scaleOrdinal(scheme.value).domain(this.getColorExtent(true));
    }
    return d3.scaleSequential(scheme.value).domain(this.getColorExtent());
  }

  byID(id) {
    let obj = { id };
    this.frames.forEach((frame, f) => {
      let frameObj = frame.byID(id);
      if (!frameObj) return;
      Object.keys(frameObj).forEach((col) => {
        if (col == 'id') return;
        if (!obj.hasOwnProperty(col)) obj[col] = {};
        obj[col][f] = frameObj[col];
      });
    });
    return obj;
  }

  atFrame(id, frame) {
    return this.frames[frame].byID(id);
  }

  frame(frameNumber) {
    return this.frames[frameNumber];
  }

  map(mapper) {
    return this.ids.map(mapper);
  }

  filter(filterer) {
    return this.ids.filter(filterer);
  }

  forEach(fn) {
    this.ids.forEach(fn);
  }

  setPreviewMode(previewMode) {
    this.previewMode = previewMode;
  }

  setPreviewParameter(param, value) {
    this.previewParameters[param] = value;
  }

  getPreviewParameter(param) {
    if (this.previewParameters.hasOwnProperty(param))
      return this.previewParameters[param];
    if (param == 'k') return 10;
    else if (param == 'similarityThreshold') return 0.5;
  }

  previewInfo(frameNumber, previewFrameNumber) {
    // Could cache these values
    let frame = this.frames[frameNumber];
    let previewFrame = this.frames[previewFrameNumber];
    if (
      this.previewMode == PreviewMode.PRECOMPUTED &&
      this.hasPreviews &&
      !!this.previews &&
      !!this.previews[frameNumber] &&
      !!this.previews[previewFrameNumber]
    ) {
      let xex = this.getXExtent();
      let yex = this.getYExtent();
      let neighborScale = (xex[1] - xex[0] + yex[1] - yex[0]) / 2.0;
      return new PrecomputedPreview(
        frame,
        previewFrame,
        this.previews[frameNumber][previewFrameNumber],
        neighborScale
      );
    } else if (this.previewMode == PreviewMode.PROJECTION_SIMILARITY) {
      return new ProjectionPreview(
        frame,
        previewFrame,
        this.getPreviewParameter('k'),
        this.getPreviewParameter('similarityThreshold')
      );
    } else if (this.previewMode == PreviewMode.NEIGHBOR_SIMILARITY) {
      return new NeighborPreview(
        frame,
        previewFrame,
        this.getPreviewParameter('k'),
        this.getPreviewParameter('similarityThreshold')
      );
    }
    return new FramePreview(frame, previewFrame);
  }

  transform(frameTransformations) {
    // Invert the last transforms since everything is done in place
    let actualTransforms = !!this.frameTransformations
      ? this.frameTransformations.map((old, i) =>
          math.multiply(frameTransformations[i], math.inv(old))
        )
      : frameTransformations;
    this.frames.forEach((frame, f) => {
      if (!!actualTransforms && actualTransforms.length > f) {
        frame.transform(actualTransforms[f]);
      }
    });
    this.frameTransformations = frameTransformations;
  }

  // Adds metadata to each point based on the given thumbnails.json data
  addThumbnails(thumbnailData) {
    if (!thumbnailData) return;

    let positionData = {};
    if (!!thumbnailData.items) {
      Object.keys(thumbnailData.items).forEach((id) => {
        positionData[id] = {
          text: thumbnailData.items[id].name,
          description: thumbnailData.items[id].description,
        };
      });
    }

    if (!!thumbnailData.spritesheets) {
      this.spritesheets = thumbnailData.spritesheets;
      Object.keys(this.spritesheets).forEach((sheet) =>
        Object.keys(this.spritesheets[sheet].spec.frames).forEach((id) => {
          if (!positionData[id]) positionData[id] = {};
          positionData[id].sheet = sheet;
          positionData[id].texture = id;
        })
      );
      this.thumbnailData = new ColumnarData(
        {
          sheet: { array: Array },
          texture: { array: Array },
          text: { array: Array },
          description: { array: Array },
        },
        positionData
      );
    } else {
      this.spritesheets = null;
      this.thumbnailData = new ColumnarData(
        {
          text: { array: Array },
          description: { array: Array },
        },
        positionData
      );
    }

    if (!!this.thumbnailData)
      this.frames.forEach((f) => f.linkData('label', this.thumbnailData));
  }

  removeThumbnails() {
    this.spritesheets = null;
    this.thumbnailData = null;
    this.frames.forEach((f) => f.removeComputedField('label'));
  }
}
