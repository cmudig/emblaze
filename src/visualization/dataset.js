import {
  buildKdTree,
  neighborMotionDifferencePreviewIntensities,
  neighborSimilarityPreviewIntensities,
  precomputedPreviewIntensities,
} from "./preview_intensity.js";
import * as d3 from "d3";

export function Dataset(rawData, colorKey, r = 4.0) {
  if (rawData["data"]) {
    // There are other keys
    this.frames = rawData.data;
    this.previews = rawData.previews;
    this.frameLabels = rawData.frameLabels;
  } else {
    // Old format
    this.frames = rawData;
    this.frameLabels = this.frames.map((f, i) => "Frame " + (i + 1));
  }

  this.getXExtent = function () {
    if (!this._xExtent) {
      let flatXs = this.map((d) => Object.values(d.xs)).flat();
      this._xExtent = d3.extent(flatXs);
    }
    return this._xExtent;
  };

  this.getYExtent = function () {
    if (!this._yExtent) {
      let flatYs = this.map((d) => Object.values(d.ys)).flat();
      this._yExtent = d3.extent(flatYs);
    }
    return this._yExtent;
  };

  this.getColorExtent = function (categorical = false) {
    if (!this._colorExtent) {
      let flatColors = this.map((d) => Object.values(d.colors)).flat();
      if (categorical) {
        this._colorExtent = Array.from(new Set(flatColors)).sort();
      } else {
        this._colorExtent = d3.extent(flatColors);
      }
    }
    return this._colorExtent;
  };

  this.at = function (idx) {
    return this.points[idx];
  };

  this.byID = function (id) {
    return this.index[id];
  };

  this.atFrame = function (id, frame) {
    if (!this.index[id]) return undefined;
    let el = this.index[id];
    if (!el.visibleFlags[frame]) return undefined;
    return {
      id,
      x: el.xs[frame],
      y: el.ys[frame],
      color: el.colors[frame],
      alpha: el.alphas[frame],
      halo: el.halos[frame],
      highlightIndexes: el.highlightIndexes[frame],
      r: el.rs[frame],
      visible: el.visibleFlags[frame],
      previewLineWidths: el.previewLineWidths[frame],
      previewLineAlphas: el.previewLineAlphas[frame],
    };
  };

  this.frame = function (frameNumber) {
    return this.frames[frameNumber];
  };

  this.map = function (mapper) {
    return this.points.map(mapper);
  };

  this.filter = function (filterer) {
    return this.points.filter(filterer);
  };

  this.forEach = function (fn) {
    this.points.forEach(fn);
  };

  this.reformat = function () {
    if (this.frames.length == 0) return [];

    // First scan the frames to see how many points there are
    let pointIDs = new Set();
    this.frames.forEach((frame) => {
      Object.keys(frame).forEach((k) => pointIDs.add(k));
    });

    // Make point templates
    let points = {};
    pointIDs.forEach(
      (id) =>
        (points[id] = {
          id,
          hoverText: null,
          xs: {},
          ys: {},
          colors: {},
          alphas: {},
          halos: {},
          highlightIndexes: {},
          rs: {},
          visibleFlags: {},
          previewLineWidths: {},
          previewLineAlphas: {},
        })
    );

    this.frames.forEach((frame, f) => {
      Object.keys(frame).forEach((id) => {
        let el = frame[id];
        points[id].hoverText = el.hoverText;
        points[id].xs[f] = el.x;
        points[id].ys[f] = el.y;
        points[id].colors[f] =
          colorKey == "constant" ? 0.0 : el[colorKey] || 0.0;
        points[id].alphas[f] = el.alpha != undefined ? el.alpha : 1.0;
        points[id].halos[f] = el.halo;
        points[id].highlightIndexes[f] = el.highlight.map((h) => "" + h);
        points[id].visibleFlags[f] = true;
        points[id].rs[f] = r;
      });
    });

    this.points = Object.values(points);
    this.index = points;
    this.length = this.points.length;
    this.neighborTrees = [];

    let xex = this.getXExtent();
    let yex = this.getYExtent();
    let neighborScale = (xex[1] - xex[0] + yex[1] - yex[0]) / 2.0;

    this.frames.forEach((frame, i) => {
      this.neighborTrees.push(buildKdTree(points, i));
      Object.keys(points).forEach((id, j) => {
        if (!frame[id]) return;

        if (!!frame[id].previewLineWidths) {
          points[id].previewLineWidths[i] = frame[id].previewLineWidths;
          if (!frame[id].previewLineAlphas)
            frame[id].previewLineAlphas = this.frames.map((_) => 0.1);
        }
        if (!!frame[id].previewLineAlphas) {
          points[id].previewLineAlphas[i] = frame[id].previewLineAlphas;
          if (!frame[id].previewLineWidths)
            frame[id].previewLineWidths = this.frames.map((_) => 0.1);
        }
        if (!frame[id].previewLineWidths && !frame[id].previewLineAlphas) {
          let intensities;
          if (this.hasPreviews) {
            intensities = precomputedPreviewIntensities(
              points[id],
              this,
              i,
              neighborScale
            );
          } else {
            /*intensities = neighborMotionDifferencePreviewIntensities(
              points[id],
              neighborTrees[i],
              i,
              neighborScale
            );*/
            intensities = neighborSimilarityPreviewIntensities(
              points[id],
              points,
              i
            );
          }

          points[id].previewLineAlphas[i] = {};
          points[id].previewLineWidths[i] = {};
          Object.keys(intensities).forEach((frameNum) => {
            points[id].previewLineAlphas[i][frameNum] =
              intensities[frameNum].lineAlpha;
            points[id].previewLineWidths[i][frameNum] =
              intensities[frameNum].lineWidth;
          });
        }
      });
    });
  };

  this.getPreviewIDs = function (frame, previewFrame) {
    if (!this.previews) return new Set();

    let allIDs = new Set();
    this.previews[frame][previewFrame].forEach((p) => {
      p.component.forEach((id) => allIDs.add(id));
    });
    return allIDs;
  };

  this.previewFrameHasID = function (frame, previewFrame, pointID) {
    if (!this.previews) return false;

    if (!this.previews[frame] || !this.previews[frame][previewFrame])
      return false;

    for (var comp of this.previews[frame][previewFrame]) {
      if (comp.component.includes(pointID)) return true;
    }
    return false;
  };

  // Gets the IDs of
  this.neighborsInFrame = function (pointID, frame, k) {
    return this.neighborTrees[frame]
      .nearest(pointID, k)
      .map((point) => point.id);
  };

  this.frameCount = this.frames.length;
  this.hasPreviews = !!this.previews;
  this.reformat();
}
