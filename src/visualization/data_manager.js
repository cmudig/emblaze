import {
  Mark,
  MarkSet,
  interpolateTo,
  easeInOut,
  Decoration,
  Animator,
  interpolateToFunction,
} from "./data_items.js";
import { ColorGenerator, getWithFallback } from "./helpers.js";
import * as d3 from "d3";

const animationDuration = 4000;
const previewAnimDuration = 1000;
const dimmedAlpha = 0.5;
const dimmedRFactor = 0.7;

// Defines the visual decoration appearance of a star graph
function DecorationStarGraph(centerMark, neighborMarks) {
  this.centerMark = centerMark;
  this.neighborMarks = neighborMarks;
  this.isOn = false;

  this.outlineDecoration = new Decoration("outline", [this.centerMark], {
    r: {
      valueFn: () => (this.isOn ? this.centerMark.attr("r") + 3.0 : 0.0),
    },
    color: "darkgrey",
    lineWidth: 1.0,
  });

  this._makeNeighborDecoration = function (mark) {
    let dec = new Decoration("line", [this.centerMark, mark], {
      color: "darkgrey",
      lineWidth: 1.0,
      x2: {
        valueFn: () => (this.isOn ? mark.attr("x") : this.centerMark.attr("x")),
      },
      y2: {
        valueFn: () => (this.isOn ? mark.attr("y") : this.centerMark.attr("y")),
      },
    });
    return dec;
  };

  this.neighborDecorations = this.neighborMarks.map((mark) =>
    this._makeNeighborDecoration(mark)
  );

  this.getDecorations = function () {
    return [this.outlineDecoration, ...this.neighborDecorations];
  };

  this._updateNeighborDecoration = function (markSet, d, duration, curve) {
    markSet.animateDecoration(
      d,
      "x2",
      new Animator(interpolateTo(d.data("x2")), duration, curve)
    );
    markSet.animateDecoration(
      d,
      "y2",
      new Animator(interpolateTo(d.data("y2")), duration, curve)
    );
  };

  this.enter = function (markSet, duration = 300, curve = null) {
    this.isOn = true;
    markSet.animateDecoration(
      this.outlineDecoration,
      "r",
      new Animator(
        interpolateTo(this.outlineDecoration.data("r")),
        duration,
        curve
      )
    );

    this.neighborDecorations.forEach((d) =>
      this._updateNeighborDecoration(markSet, d, duration, curve)
    );
  };

  this.exit = function (markSet, duration = 300, curve = null) {
    this.isOn = false;
    markSet.animateDecoration(
      this.outlineDecoration,
      "r",
      new Animator(interpolateTo(0.0), duration, curve)
    );

    this.neighborDecorations.forEach((d) =>
      this._updateNeighborDecoration(markSet, d, duration, curve)
    );
  };

  this.updateNeighborMarks = function (
    newMarks,
    markSet,
    duration = 300,
    curve = null
  ) {
    // Remove marks that are no longer present
    let newMarkSet = new Set(newMarks);
    this.neighborMarks.forEach((m, i) => {
      if (!newMarkSet.has(m)) {
        let decoration = this.neighborDecorations[i];
        markSet.removeDecoration(decoration);
      }
    });

    // Update ordering and add new marks
    let newDecorations = [];
    newMarks.forEach((m, i) => {
      let idx = this.neighborMarks.indexOf(m);
      if (idx >= 0) {
        // Insert the appropriate decoration into the new array
        newDecorations.push(this.neighborDecorations[idx]);
      } else {
        // Add a new decoration
        let dec = this._makeNeighborDecoration(m);
        markSet.addDecoration(dec);
        this._updateNeighborDecoration(markSet, dec, duration, curve);
        newDecorations.push(dec);
      }
    });

    this.neighborMarks = newMarks;
    this.neighborDecorations = newDecorations;
  };
}

// The purpose of the DatasetManager is to convert user interactions on data into visual attributes
// of marks.
export function DatasetManager(
  dataset,
  colorScale,
  xScale,
  yScale,
  currentFrame = 0
) {
  this.data = dataset;
  this.currentFrameNumber = currentFrame;
  this.previewFrameNumber = -1; // no preview

  this.xScale = xScale;
  this.yScale = yScale;
  this.colorScale = colorScale;

  let colorGen = new ColorGenerator();
  this._colorMap = {};

  this.dimmedPoints = new Set();
  this.filterVisiblePoints = new Set();

  this.marks = new MarkSet(
    this.data.map((d, i) => {
      let colorID = colorGen.next();
      this._colorMap[colorID] = d.id;
      /*let special =
        !labeled &&
        d.visibleFlags[this.currentFrameNumber] &&
        Math.random() < 0.01;
      if (special) labeled = true;*/
      return new Mark(
        d.id,
        {
          x: {
            value: getWithFallback(d.xs, this.currentFrameNumber, 0.0),
            transform: (v) => this.xScale(v),
          },
          y: {
            value: getWithFallback(d.ys, this.currentFrameNumber, 0.0),
            transform: (v) => this.yScale(v),
          },
          halo: 0.0, // halo is now only to be used for preview frames
          x2: {
            value: getWithFallback(d.xs, this.currentFrameNumber, 0.0),
            transform: (v) => this.xScale(v),
          },
          y2: {
            value: getWithFallback(d.ys, this.currentFrameNumber, 0.0),
            transform: (v) => this.yScale(v),
          },
          fillStyle: {
            value: getWithFallback(d.colors, this.currentFrameNumber, 0.0),
            transform: (c) => d3.color(this.colorScale(c)).formatRgb(),
            cache: true,
          },
          alpha: { valueFn: () => this._getPointAlpha(d) },
          r: { valueFn: () => this._getPointRadius(d) },
          visible: d.visibleFlags[this.currentFrameNumber] || false,
          colorID,
          hoverText: null,
          lineWidth: { valueFn: () => this._getLineWidth(d) },
          lineAlpha: { valueFn: () => this._getLineAlpha(d) },
        }
        // special
      );
    })
  );

  this.getPointByColorID = function (color) {
    let id = this._colorMap[color];
    if (id == undefined) {
      return null;
    }
    return id;
  };

  this._useHalos = false;

  this._getPointAlpha = function (dataItem) {
    if (
      this.filterVisiblePoints.size > 0 &&
      !this.filterVisiblePoints.has(dataItem.id)
    )
      return 0.0;

    let alpha = getWithFallback(dataItem.alphas, this.currentFrameNumber, 0.0);

    // Dimmed for a hover/selection
    if (this.dimmedPoints.has(dataItem.id)) alpha *= dimmedAlpha;
    else if (
      this.dimmedPoints.size == 0 &&
      this.previewFrameNumber >= 0 &&
      this.previewFrameNumber != this.currentFrameNumber &&
      !this._useHalos
    ) {
      // Dimmed for a preview frame
      alpha *= 0.2;
    }
    return alpha;
  };

  this._getLineAlpha = function (dataItem) {
    if (
      this.previewFrameNumber < 0 ||
      this.previewFrameNumber == this.currentFrameNumber
    )
      return 0.0;

    let previewAlphas = dataItem.previewLineAlphas[this.currentFrameNumber];
    if (!previewAlphas) return 0.0;
    let alpha = previewAlphas[this.previewFrameNumber] || 0.0;

    // Dimmed for a hover/selection
    if (this.dimmedPoints.has(dataItem.id)) alpha *= dimmedAlpha;
    return alpha;
  };

  this._getLineWidth = function (dataItem) {
    if (
      this.previewFrameNumber < 0 ||
      this.previewFrameNumber == this.currentFrameNumber
    )
      return 0.0;

    let previewWidths = dataItem.previewLineWidths[this.currentFrameNumber];

    if (!previewWidths) return 0.0;
    return previewWidths[this.previewFrameNumber] || 0.0;
  };

  this._getPointRadius = function (dataItem) {
    let r = getWithFallback(dataItem.rs, this.currentFrameNumber, 0.0);

    // Dimmed for a hover/selection
    if (this.dimmedPoints.has(dataItem.id)) r *= dimmedRFactor;

    // Dimmed for a preview frame
    if (
      this.previewFrameNumber >= 0 &&
      this.previewFrameNumber != this.currentFrameNumber &&
      this._useHalos
    ) {
      let previewAlphas = dataItem.previewLineAlphas[this.currentFrameNumber];
      if (!!previewAlphas)
        r *= !!previewAlphas[this.previewFrameNumber] ? 1.0 : 0.2;
    }
    return r;
  };

  // Sets the current displayed frame
  this.setFrame = function (frameNumber, animated = true) {
    let oldFrame = this.currentFrameNumber;
    if (animated) {
      // Set positions for marks that were hidden before. This prevents
      // them from appearing to move
      this.marks.forEach((mark, i) => {
        if (
          mark.attr("r") < 0.001 &&
          this.data.at(i).visibleFlags[frameNumber]
        ) {
          mark.setAttr(
            "x",
            getWithFallback(this.data.at(i).xs, frameNumber, mark.data("x"))
          );
          mark.setAttr(
            "y",
            getWithFallback(this.data.at(i).ys, frameNumber, mark.data("y"))
          );
          mark.setAttr(
            "x2",
            getWithFallback(this.data.at(i).xs, frameNumber, mark.data("x"))
          );
          mark.setAttr(
            "y2",
            getWithFallback(this.data.at(i).ys, frameNumber, mark.data("y"))
          );
          mark.setAttr(
            "fillStyle",
            getWithFallback(
              this.data.at(i).colors,
              frameNumber,
              mark.data("fillStyle")
            )
          );
        }
      });

      this.currentFrameNumber = frameNumber;

      // Update visible flag
      this.marks.setAll(
        "visible",
        (_, i) => this.data.at(i).visibleFlags[frameNumber] || false
      );

      // Register animations
      this.marks.animateAll(
        "x",
        (mark, i) =>
          interpolateTo(
            getWithFallback(
              this.data.at(i).xs,
              frameNumber,
              getWithFallback(this.data.at(i).xs, oldFrame, mark.data("x"))
            )
          ),
        animationDuration,
        easeInOut
      );
      this.marks.animateAll(
        "y",
        (mark, i) =>
          interpolateTo(
            getWithFallback(
              this.data.at(i).ys,
              frameNumber,
              getWithFallback(this.data.at(i).ys, oldFrame, mark.data("y"))
            )
          ),
        animationDuration,
        easeInOut
      );
      this.marks.animateAll(
        "x2",
        (mark, i) =>
          interpolateTo(
            getWithFallback(
              this.data.at(i).xs,
              frameNumber,
              getWithFallback(this.data.at(i).xs, oldFrame, mark.data("x"))
            )
          ),
        animationDuration,
        easeInOut
      );
      this.marks.animateAll(
        "y2",
        (mark, i) =>
          interpolateTo(
            getWithFallback(
              this.data.at(i).ys,
              frameNumber,
              getWithFallback(this.data.at(i).ys, oldFrame, mark.data("y"))
            )
          ),
        animationDuration,
        easeInOut
      );
      this.marks.animateAll(
        "halo",
        (mark, i) =>
          interpolateTo(
            getWithFallback(
              this.data.at(i).halos,
              frameNumber,
              mark.data("halo")
            )
          ),
        animationDuration,
        easeInOut
      );
      this.marks.animateAll(
        "fillStyle",
        (mark, i) =>
          interpolateTo(
            getWithFallback(
              this.data.at(i).colors,
              frameNumber,
              mark.data("fillStyle")
            )
          ),
        animationDuration,
        easeInOut
      );
      this.marks.animateComputed(
        "r",
        interpolateTo,
        animationDuration,
        easeInOut
      );
      this.marks.animateComputed(
        "alpha",
        interpolateTo,
        animationDuration,
        easeInOut
      );
      this.marks.animateComputed(
        "lineAlpha",
        interpolateTo,
        animationDuration,
        easeInOut
      );
      this.marks.animateComputed(
        "lineWidth",
        interpolateTo,
        animationDuration,
        easeInOut
      );
    } else {
      this.currentFrameNumber = frameNumber;

      this.marks.setAll("x", (mark, i) =>
        getWithFallback(this.data.at(i).xs, frameNumber, mark.data("x"))
      );
      this.marks.setAll("y", (mark, i) =>
        getWithFallback(this.data.at(i).ys, frameNumber, mark.data("y"))
      );
      this.marks.setAll("x2", (mark, i) =>
        getWithFallback(this.data.at(i).xs, frameNumber, mark.data("x"))
      );
      this.marks.setAll("y2", (mark, i) =>
        getWithFallback(this.data.at(i).ys, frameNumber, mark.data("y"))
      );
      this.marks.setAll("halo", (mark, i) =>
        getWithFallback(this.data.at(i).halos, frameNumber, mark.data("halo"))
      );
      this.marks.setAll("lineWidth", () => 0.0);
      this.marks.setAll("fillStyle", (mark, i) =>
        getWithFallback(
          this.data.at(i).colors,
          frameNumber,
          mark.data("fillStyle")
        )
      );
    }
  };

  // Sets the frame previewed using semitransparent lines (or halos, if halos is true)
  this.previewFrame = function (
    previewFrameNumber,
    animated = true,
    halos = false
  ) {
    this.previewFrameNumber = previewFrameNumber;
    let duration = animated ? previewAnimDuration : 0;
    this._useHalos = halos;

    // Compute destination attributes first
    let destFrame =
      previewFrameNumber >= 0 ? previewFrameNumber : this.currentFrameNumber;

    // Animate properties
    if (halos) {
      this.marks.animateAll(
        "halo",
        (_, i) => {
          if (destFrame != this.currentFrameNumber) {
            let previewWidths = this.data.at(i).previewLineWidths[
              this.currentFrameNumber
            ];

            if (!previewWidths) return interpolateTo(0.0);
            return interpolateTo(previewWidths[destFrame] || 0.0);
          }
          return interpolateTo(0.0);
        },
        duration,
        easeInOut
      );
    }
    this.marks.animateAll(
      "x2",
      (mark, i) =>
        interpolateTo(
          getWithFallback(
            this.data.at(i).xs,
            destFrame,
            getWithFallback(
              this.data.at(i).xs,
              this.currentFrameNumber,
              mark.data("x")
            )
          )
        ),
      duration,
      easeInOut
    );
    this.marks.animateAll(
      "y2",
      (mark, i) =>
        interpolateTo(
          getWithFallback(
            this.data.at(i).ys,
            destFrame,
            getWithFallback(
              this.data.at(i).ys,
              this.currentFrameNumber,
              mark.data("y")
            )
          )
        ),
      duration,
      easeInOut
    );
    this.marks.animateComputed("alpha", interpolateTo, duration, easeInOut);
    this.marks.animateComputed("r", interpolateTo, duration, easeInOut);
    this.marks.animateComputed("lineWidth", interpolateTo, duration, easeInOut);
    this.marks.animateComputed("lineAlpha", interpolateTo, duration, easeInOut);

    // Show hover text for points that have preview lines (up to a point)
    /*this.marks.setAll("hoverText", (mark, i) => {
      if (!mark.data("visible") || previewFrameNumber < 0) return null;
      let previews = this.data.at(i).previewLineWidths[this.currentFrameNumber];
      if (!previews || !previews[previewFrameNumber]) return null;
      return this.data.at(i).hoverText;
    });*/
  };

  // Highlighting subgraphs

  let displayedGraphs = {};

  const highlightDuration = 300;

  this.createStarGraph = function (nodeID, linkedNodeIDs) {
    let graph = new DecorationStarGraph(
      this.marks.getMarkByID(nodeID),
      linkedNodeIDs.map((id) => this.marks.getMarkByID(id)).filter((m) => !!m)
    );
    let graphID = "stargraph_" + nodeID + "_" + Math.floor(Math.random() * 1e9);
    let graphInfo = {
      highlightedNodes: [nodeID, ...linkedNodeIDs],
      graph,
      state: "waiting",
    };
    displayedGraphs[graphID] = graphInfo;
    graph.getDecorations().forEach((d) => this.marks.addDecoration(d));

    return graphID;
  };

  this.updateStarGraph = function (graphID, newNeighbors, animated = true) {
    let graphInfo = displayedGraphs[graphID];
    if (!graphInfo) {
      console.warn("Trying to update a non-existent graph");
      return;
    }
    graphInfo.highlightedNodes = [
      graphInfo.highlightedNodes[0],
      ...newNeighbors,
    ];
    graphInfo.graph.updateNeighborMarks(
      newNeighbors.map((id) => this.marks.getMarkByID(id)).filter((m) => !!m),
      this.marks,
      animated ? highlightDuration : 0
    );
    this.updateDimmedPoints(animated);
  };

  this.highlightStarGraph = function (graphID, animated = true) {
    let graphInfo = displayedGraphs[graphID];
    if (!graphInfo) {
      console.warn("Trying to highlight a non-existent graph");
      return;
    }
    if (graphInfo.state == "visible") {
      return Promise.resolve();
    }
    if (graphInfo.state == "entering") {
      return Promise.reject();
    }

    let graph = graphInfo.graph;
    graphInfo.state = "entering";
    graph.enter(this.marks, animated ? highlightDuration : 0);

    this.updateDimmedPoints(animated);

    // Return a promise for completion
    return new Promise((resolve, reject) => {
      setTimeout(
        () => {
          // Resolve if it's still highlighted, otherwise reject
          if (graphInfo.state == "entering") {
            graphInfo.state = "visible";
            resolve();
          } else reject();
        },
        animated ? highlightDuration : 0
      );
    });
  };

  this.unhighlightStarGraph = function (graphID, animated = true) {
    let graphInfo = displayedGraphs[graphID];
    if (!graphInfo || graphInfo.state == "waiting") {
      return Promise.resolve();
    }
    if (graphInfo.state == "exiting") {
      return Promise.reject();
    }

    let graph = graphInfo.graph;
    graphInfo.state = "exiting";
    graph.exit(this.marks, animated ? highlightDuration : 0);
    this.updateDimmedPoints(animated);

    // Return a promise for completion
    return new Promise((resolve, reject) => {
      setTimeout(
        () => {
          // Resolve if it's still gone, otherwise reject
          if (!!displayedGraphs[graphID] && graphInfo.state == "exiting") {
            // Remove it from the cache too
            graph
              .getDecorations()
              .forEach((d) => this.marks.removeDecoration(d));
            delete displayedGraphs[graphID];

            resolve();
          } else {
            reject();
          }
        },
        animated ? highlightDuration : 0
      );
    });
  };

  this._computeHighlightedPoints = function () {
    let highlightedPointIDs = new Set();

    Object.keys(displayedGraphs).forEach((graphID) => {
      let g = displayedGraphs[graphID];
      if (g.state == "entering" || g.state == "visible") {
        g.highlightedNodes.forEach((n) => highlightedPointIDs.add(n));
      }
    });
    return highlightedPointIDs;
  };

  this.updateDimmedPoints = function (animated = true) {
    let highlightedPointIDs = this._computeHighlightedPoints();
    let newDimmedPoints =
      highlightedPointIDs.size == 0
        ? new Set()
        : new Set(
            this.data
              .filter((d, i) => !highlightedPointIDs.has(d.id))
              .map((d) => d.id)
          );
    if (newDimmedPoints == this.dimmedPoints) {
      return;
    }
    this.dimmedPoints = newDimmedPoints;

    let centerIDs = new Set(
      Object.values(displayedGraphs)
        .filter(
          (graphInfo) =>
            graphInfo.state == "entering" || graphInfo.state == "visible"
        )
        .map((graphInfo) => graphInfo.graph.centerMark.id)
    );
    this.showHoverText((datum) => centerIDs.has(datum.id));

    if (animated) {
      this.marks.animateComputed("alpha", interpolateTo, highlightDuration);
      this.marks.animateComputed("r", interpolateTo, highlightDuration);
    }
  };

  this.filter = function (visibleIDs) {
    this.filterVisiblePoints = new Set(visibleIDs);
    this.marks.animateComputed("alpha", interpolateTo, highlightDuration);
  };

  this.clearFilter = function () {
    this.filterVisiblePoints = new Set();
    this.marks.animateComputed("alpha", interpolateTo, highlightDuration);
  };

  this.showHoverText = function (hoverTextFn) {
    this.marks.setAll("hoverText", (_, i) =>
      hoverTextFn(this.data.at(i), i) ? this.data.at(i).hoverText : null
    );
  };

  // Takes a dictionary with possible values colorScale, xScale, yScale
  this.rescale = function (options = {}) {
    this.xScale = options.xScale || this.xScale;
    this.yScale = options.yScale || this.yScale;
    this.colorScale = options.colorScale || this.colorScale;
    this.marks.updateAllDecorations();
  };
}
