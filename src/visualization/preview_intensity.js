/*
  The functions in this module take a point, a set of comparison points, and
  a frame number for the current frame. They produce an object
  containing keys for each preview frame, each value containing lineWidth and
  lineAlpha keys that correspond to the width and alpha to use for previewing
  this point's transition into each preview frame.
*/

import { kdTree } from "./kdTree";

export function neighborSimilarityPreviewIntensities(
  point,
  allPoints,
  currentFrameNumber
) {
  if (!point.visibleFlags[currentFrameNumber]) return {};

  let currentNeighbors = new Set(point.highlightIndexes[currentFrameNumber]);
  let result = {};

  Object.keys(point.visibleFlags).forEach((previewFrameNumber) => {
    if (!point.visibleFlags[previewFrameNumber]) return;
    let previewNeighbors = new Set(point.highlightIndexes[previewFrameNumber]);
    let intersectionCount = 0;
    currentNeighbors.forEach((n) => {
      if (previewNeighbors.has(n)) {
        intersectionCount++;
      }
    });

    let fraction = intersectionCount / currentNeighbors.size;
    let intensity;
    if (fraction >= 0.3) {
      intensity = { lineWidth: 0.0, lineAlpha: 0.0 };
    } else {
      intensity = {
        lineWidth: Math.pow(1 - fraction / 0.3, 3) * 20.0,
        lineAlpha: Math.pow(1 - fraction / 0.3, 3),
      }; //5.0 + 20.0 * (1.0 - fraction * fraction));
    }
    result[previewFrameNumber] = intensity;
  });

  return result;
}

function distance2(a, b) {
  let dx = a.x - b.x;
  let dy = a.y - b.y;
  return dx * dx + dy * dy;
}

export function buildKdTree(allPoints, currentFrameNumber) {
  let coordinates = Object.values(allPoints)
    .filter((p) => !!p.visibleFlags[currentFrameNumber])
    .map((p) => ({
      id: p.id,
      x: p.xs[currentFrameNumber],
      y: p.ys[currentFrameNumber],
      xs: p.xs,
      ys: p.ys,
    }));

  let tree = new kdTree(coordinates, distance2, ["x", "y"]);
  return {
    _tree: tree,
    nearest: (pointID, k) => {
      let point = allPoints[pointID];
      if (!point || !point.visibleFlags[currentFrameNumber]) return [];

      let results = tree.nearest(
        { x: point.xs[currentFrameNumber], y: point.ys[currentFrameNumber] },
        k
      );
      return results.map((el) => el[0]);
    },
  };
}

// Takes the result of buildKdTree as an argument instead of allPoints
export function neighborMotionDifferencePreviewIntensities(
  point,
  kdTree,
  currentFrameNumber,
  scale = 1.0 // this normalizes the distances between delta vectors
) {
  if (!point.visibleFlags[currentFrameNumber]) return {};

  let currentNeighbors = kdTree.nearest(point.id, 10);
  let result = {};

  Object.keys(point.visibleFlags).forEach((previewFrameNumber) => {
    if (!point.visibleFlags[previewFrameNumber]) return;

    // Compute the average vector of translation of the neighbors
    let neighborDiff = { x: 0.001, y: 0.001 };
    currentNeighbors.forEach((neighborPoint) => {
      if (isNaN(neighborPoint.xs[previewFrameNumber])) return;

      neighborDiff.x +=
        (neighborPoint.xs[previewFrameNumber] - neighborPoint.x) /
        currentNeighbors.length;
      neighborDiff.y +=
        (neighborPoint.ys[previewFrameNumber] - neighborPoint.y) /
        currentNeighbors.length;
    });
    let neighborMag = Math.sqrt(
      neighborDiff.x * neighborDiff.x + neighborDiff.y * neighborDiff.y
    );

    // Compute the translation of this point
    let currentDiff = {
      x: point.xs[previewFrameNumber] - point.xs[currentFrameNumber],
      y: point.ys[previewFrameNumber] - point.ys[currentFrameNumber],
    };
    let currentMag = Math.sqrt(
      currentDiff.x * currentDiff.x + currentDiff.y * currentDiff.y
    );

    let distance = Math.sqrt(distance2(neighborDiff, currentDiff));
    /*1.0 -
      (currentDiff.x * neighborDiff.x + currentDiff.y * neighborDiff.y) /
        (neighborMag * currentMag);*/
    if (distance / scale <= 0.4) {
      result[previewFrameNumber] = { lineWidth: 0.0, lineAlpha: 0.0 };
    } else {
      result[previewFrameNumber] = {
        lineWidth: Math.max(Math.min((distance / scale) * 40.0, 40.0), 2.0),
        lineAlpha: 0.4 + Math.min((distance / scale) * 0.4, 0.4),
      };
    }
  });

  return result;
}

export function precomputedPreviewIntensities(
  point,
  dataset,
  currentFrameNumber,
  scale = 1.0
) {
  // This is probably slow because it gets run a lot unnecessarily
  let result = {};

  Object.keys(point.visibleFlags).forEach((preview) => {
    if (!point.visibleFlags[preview]) return;

    if (dataset.previewFrameHasID(currentFrameNumber, preview, point.id)) {
      let dx = point.xs[preview] - point.xs[currentFrameNumber];
      let dy = point.ys[preview] - point.ys[currentFrameNumber];
      let distance = Math.sqrt(dx * dx + dy * dy);
      result[preview] = {
        lineWidth: 30.0 * (distance / scale + 0.2),
        lineAlpha: 0.8,
      };
    } else {
      result[preview] = { lineWidth: 0.0, lineAlpha: 0.0 };
    }
  });

  return result;
}
