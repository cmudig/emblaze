<!-- A script-only component that reactively manages the state of the scatterplot -->
<svelte:options accessors />

<script>
  import * as d3 from 'd3';
  import { getWithFallback } from '../utils/helpers';
  import {
    MarkSet,
    Mark,
    Decoration,
    interpolateTo,
    easeInOut,
  } from '../models/data_items';
  import AnimationPool from '../models/animation_pool';
  import {
    DecorationStarGraph,
    WideningLineDecoration,
  } from '../models/decorations';
  import { onDestroy } from 'svelte';

  // State variables - these should fully encode the visual state of the scatterplot,
  // except for visibility due to scaling

  export let data = null;
  export let colorScale = null;
  export let xScale = null;
  export let yScale = null;
  export let pointRadius = 1.0;

  export let hoveredID = null;
  export let selectedIDs = [];
  export let alignedIDs = [];
  export let tentativeSelectedIDs = []; // preview a selection before executing
  export let idsOfInterest = [];

  export let frame = null;
  export let previewFrame = null;
  export let previewInfo = null;
  export let previewProgress = 0.0; // From 0 to 1, where 0 is frame and 1 is previewFrame

  export let thumbnail = false;

  // Additional props

  export let marks = null;
  export let colorMap; // For hidden IDs
  export let filterIDs = [];

  // Mark styles may be specified in different formats for different renderers
  export let colorFormat = 'hex';

  // Number of neighbors to display
  export let numNeighbors = 10;

  // set this to false to save on animations and additional decorations when
  // displaying lots of data
  export let highlightFocusedPoints = true;

  // set this to false to disable showing preview lines when displaying lots
  // of data
  export let showPreviewLines = true;

  // Constants

  const frameDuration = 4000;
  const previewAnimDuration = 1000;
  const defaultDuration = 500;
  const decorationDuration = 300;

  // Initialization

  $: if (!!data && !!colorScale && !!xScale && !!yScale && !!colorMap) {
    initializeMarks();
  }

  function initializeMarks() {
    marks = new MarkSet(
      data.map((id) => {
        let colorID = colorMap.id(id, { type: 'mark', id });
        return new Mark(
          id,
          {
            x: {
              valueFn: _getX,
              transform: (v) => xScale(v),
              lazy: true,
            },
            y: {
              valueFn: _getY,
              transform: (v) => yScale(v),
              lazy: true,
            },
            halo: 0.0,
            fillStyle: {
              valueFn: () => frame.get(id, 'color', 0.0),
              transform: _transformColor,
              cached: true,
            },
            alpha: { valueFn: _getPointAlpha, lazy: true },
            r: { valueFn: _getPointRadius, lazy: true },
            visible: frame.has(id) || false,
            colorID,
            hoverText: frame.get(id, 'hoverText'),
          }
          // special
        );
      })
    );
    marks.registerPreloadableProperty('x');
    marks.registerPreloadableProperty('y');
    marks.registerPreloadableProperty('r');
    marks.registerPreloadableProperty('alpha');

    setupDecorationPools();

    previousFrame = null; // Prevent "animating" to the first frame shown
  }

  export function destroyMarks() {
    marks = null;
  }

  onDestroy(() => {
    destroyMarks();
    data = null;
  });

  // Computed attributes

  let highlightedPoints = new Set();

  let previewLinePoints = new Set();
  $: previewLinePoints = new Set(idsOfInterest);

  function _getX(mark) {
    let id = mark.id;
    let base = frame.get(id, 'x', mark.attributes.x.last() || 0.0);
    if (previewFrame != null && previewProgress > 0.0) {
      let dest = previewFrame.get(id, 'x', base);
      return base * (1 - previewProgress) + dest * previewProgress;
    }
    return base;
  }

  function _getY(mark) {
    let id = mark.id;
    let base = frame.get(id, 'y', mark.attributes.y.last() || 0.0);
    if (previewFrame != null && previewProgress > 0.0) {
      let dest = previewFrame.get(id, 'y', base);
      return base * (1 - previewProgress) + dest * previewProgress;
    }
    return base;
  }

  let oldColorScale = null;
  $: if (!!marks && colorScale !== oldColorScale) {
    marks.forEach((mark) => mark.updateTransform('fillStyle'));
    oldColorScale = colorScale;
  }

  function _transformColor(c) {
    let color = d3.color(colorScale(c));
    if (color == null) return null;

    if (colorFormat == 'hex') return color.formatHex();
    else if (colorFormat == 'rgb') return color.formatRgb();
    else if (colorFormat == 'rgbArray') {
      color = color.rgb();
      return [color.r / 255.0, color.g / 255.0, color.b / 255.0];
    }
    return c;
  }

  function _getPointAlpha(mark) {
    // if (filter.size > 0 && !filter.has(mark.id)) return 0.0;
    let alpha = frame.get(mark.id, 'alpha') || 0.0;

    if (
      highlightFocusedPoints &&
      highlightedPoints.size != 0 &&
      !highlightedPoints.has(mark.id)
    )
      alpha *= 0.3;

    return alpha;
  }

  function _getPointRadius(mark) {
    let r = frame.get(mark.id, 'r') || 0.0;
    if (highlightFocusedPoints) {
      if (highlightedPoints.size != 0 && !highlightedPoints.has(mark.id))
        r *= 0.7;
      if (selectedIDs.includes(mark.id)) r *= 1.5;
    }
    return r * pointRadius;
  }

  function _getLineAlpha(mark) {
    if (filter.size > 0 && !filter.has(mark.id)) return 0.0;
    if (previewLinePoints.size > 0 && !previewLinePoints.has(mark.id))
      return 0.0;
    if (previewInfo == null) return 0.0;
    return previewInfo.get(mark.id).lineAlpha || 0.0;
  }

  function _getLineWidth(mark) {
    if (filter.size > 0 && !filter.has(mark.id)) return 0.0;
    if (previewLinePoints.size > 0 && !previewLinePoints.has(mark.id))
      return 0.0;
    if (previewInfo == null) return 0.0;
    return previewInfo.get(mark.id).lineWidth || 0.0;
  }

  const SelectionOutlineZIndex = 20;
  const StarGraphZIndex = 15;

  const HoverTextPriority = 150;
  const SelectionTextPriority = 100;
  const NeighborTextPriority = 50;
  const FilterTextPriority = 25;

  function _getLabelPriority(mark) {
    if (mark.id == hoveredID) return HoverTextPriority;
    else if (selectedIDs.includes(mark.id)) return SelectionTextPriority;
    else if (highlightedPoints.has(mark.id)) return NeighborTextPriority;

    return null;
  }

  // Frame transitions

  let previousFrame = null;
  $: if (!!marks && previousFrame !== frame) {
    setFrame(previousFrame, frame, !thumbnail && previousFrame != null);
    if (!thumbnail) updatePreviewLines();
    previousFrame = frame;
  }

  function setFrame(oldFrame, newFrame, animated = true) {
    previewProgress = 0.0;

    if (animated) {
      // Set positions for marks that were hidden before. This prevents
      // them from appearing to move
      marks.forEach((mark) => {
        if (!oldFrame || (!oldFrame.has(mark.id) && newFrame.has(mark.id))) {
          mark.attributes.x.compute();
          mark.attributes.y.compute();
          mark.attributes.fillStyle.compute();
        }
      });

      // Update visible flag
      marks.setAll(
        'visible',
        (mark) => (!!newFrame && newFrame.has(mark.id)) || false
      );

      // Register animations
      marks.animateComputed('x', interpolateTo, frameDuration, easeInOut);
      marks.animateComputed('y', interpolateTo, frameDuration, easeInOut);

      marks.animateComputed(
        'fillStyle',
        interpolateTo,
        frameDuration,
        easeInOut
      );
      marks.animateComputed('r', interpolateTo, frameDuration, easeInOut);
      marks.animateComputed('alpha', interpolateTo, frameDuration, easeInOut);
    }

    starGraphPool.getAllVisibleIDs().forEach((id) => {
      updateStarGraph(id, animated);
    });
  }

  export function animateDatasetUpdate() {
    marks.animateComputed('x', interpolateTo, frameDuration, easeInOut);
    marks.animateComputed('y', interpolateTo, frameDuration, easeInOut);
    marks.animateComputed('r', interpolateTo, defaultDuration, easeInOut);
    marks.animateComputed('alpha', interpolateTo, defaultDuration, easeInOut);
    marks.animateComputed(
      'fillStyle',
      interpolateTo,
      defaultDuration,
      easeInOut
    );
  }

  // Preview frames

  let oldPreviewProgress = 0.0;
  let oldPreviewFrame = null;

  $: if (
    previewFrame != null &&
    previewFrame !== frame &&
    oldPreviewProgress != previewProgress
  ) {
    marks.updateComputed('x');
    marks.updateComputed('y');
    oldPreviewProgress = previewProgress;
  }

  $: if (oldPreviewFrame !== previewFrame) {
    if (previewProgress != 0.0) {
      if (previewFrame == null) previewProgress = 0.0;
      marks.animateComputed('x', interpolateTo, frameDuration, easeInOut);
      marks.animateComputed('y', interpolateTo, frameDuration, easeInOut);
      oldPreviewProgress = previewProgress;
    }
    oldPreviewFrame = previewFrame;
  }

  $: if (!!data && !!marks && !!previewLinePool)
    updatePreviewLines(previewInfo);

  function updatePreviewLines(info) {
    if (!marks || !previewLinePool) return;

    if (!!info && showPreviewLines) {
      marks.forEach((mark) => {
        if (_getLineAlpha(mark) <= 0.01) {
          previewLinePool.hide(mark.id);
        } else {
          previewLinePool.show(mark.id);
        }
      });
      previewLinePool.getAllVisible().forEach((item) => {
        let dec = item.element;
        dec.animateToFrames(
          marks,
          frame,
          previewFrame || frame,
          previewAnimDuration
        );
        dec.updateLineAppearance(marks, previewAnimDuration);
      });
    } else {
      previewLinePool.getAllVisibleIDs().forEach((id) => {
        previewLinePool.hide(id);
      });
    }
  }

  // Filter

  let filter = new Set();
  $: filter = new Set(filterIDs);

  let prevFilter = null;
  $: if (prevFilter !== filter) {
    if (prevFilter != null && !!marks) {
      marks.setVisibleMarks(filter);
      if (highlightFocusedPoints) {
        marks.animateComputed('r', interpolateTo, defaultDuration);
        marks.animateComputed('alpha', interpolateTo, defaultDuration);
      } else {
        marks.updateComputed('x');
        marks.updateComputed('y');
        marks.updateComputed('r');
        marks.updateComputed('alpha');
        marks.updateComputed('fillStyle');
      }
    }
    if (previewInfo != null) {
      updatePreviewLines(previewInfo);
    }
    prevFilter = filter;
  }

  // Hover and select

  var prevHoverID = null;
  var prevSelectedIDs = [];
  var prevAlignedIDs = [];
  var prevTentativeSelectedIDs = [];
  let starGraphPool;
  let previewLinePool;
  let selectionDecorationPool;
  let tentativeSelectionDecorationPool;
  let alignDecorationPool;
  let labelPool;

  $: if (
    !!marks &&
    (prevHoverID !== hoveredID ||
      prevSelectedIDs !== selectedIDs ||
      prevAlignedIDs !== alignedIDs)
  ) {
    updateSelectionState(
      prevHoverID,
      hoveredID,
      prevSelectedIDs,
      selectedIDs,
      prevAlignedIDs,
      alignedIDs
    );
    prevHoverID = hoveredID;
    prevSelectedIDs = selectedIDs;
    prevAlignedIDs = alignedIDs;
  }

  $: if (!!marks && prevTentativeSelectedIDs != tentativeSelectedIDs) {
    updateTentativeSelectionVisibility(
      prevTentativeSelectedIDs,
      tentativeSelectedIDs
    );
  }

  export function selectElement(element, multi) {
    if (!element) {
      selectedIDs = [];
    } else if (element.type == 'mark') {
      let selection = new Set(selectedIDs);
      if (multi) {
        if (selection.has(element.id)) selection.delete(element.id);
        else selection.add(element.id);
      } else {
        selection = new Set([element.id]);
      }
      selectedIDs = Array.from(selection);
    } else if (element.type == 'halo') {
      selectedIDs = element.ids;
    }
    return selectedIDs;
  }

  // This function should make ALL the mutations that arise from selection/alignment
  // changes
  function updateSelectionState(
    oldHoveredID,
    newHoveredID,
    oldSelectedIDs,
    newSelectedIDs,
    oldAlignedIDs,
    newAlignedIDs
  ) {
    oldSelectedIDs.forEach((id) => selectionDecorationPool.hide(id));
    newSelectedIDs.forEach((id) => selectionDecorationPool.show(id));
    updateAlignmentDecorations();
    updateStarGraphVisibility();
    updateLabelVisibility();
  }

  $: if (!!marks) {
    highlightedPoints = new Set(
      selectedIDs
        .map((id) => {
          return [
            id,
            ...frame.get(id, 'highlightIndexes').slice(0, numNeighbors),
          ];
        })
        .flat()
    );
    if (highlightFocusedPoints) {
      marks.animateComputed('r', interpolateTo, defaultDuration);
      marks.animateComputed('alpha', interpolateTo, defaultDuration);
    }
    updateLabelVisibility();
  }

  let oldHighlightFocusedPoints = true;
  $: if (oldHighlightFocusedPoints != highlightFocusedPoints) {
    if (!!marks) {
      marks.updateComputed('r');
      marks.updateComputed('alpha');
    }
    oldHighlightFocusedPoints = highlightFocusedPoints;
  }

  let oldShowPreviewLines = true;
  $: if (oldShowPreviewLines != showPreviewLines && !!previewInfo) {
    updatePreviewLines(previewInfo);
    oldShowPreviewLines = showPreviewLines;
  }

  function setupDecorationPools() {
    previewLinePool = new AnimationPool({
      create: (nodeID) => {
        let mark = marks.getMarkByID(nodeID);
        if (!mark) return null;
        let dec = new WideningLineDecoration(
          mark,
          frame,
          _getLineWidth,
          _getLineAlpha
        );
        marks.addDecoration(dec);
        return dec;
      },
      show: (element) => {
        element.animateToFrames(
          marks,
          frame,
          previewFrame || frame,
          previewAnimDuration
        );
        element.updateLineAppearance(marks, previewAnimDuration);
        return new Promise((resolve) =>
          setTimeout(resolve, previewAnimDuration)
        );
      },
      hide: (element) => {
        element.animateToFrames(marks, frame, frame, previewAnimDuration);
        element.updateLineAppearance(marks, previewAnimDuration);
        return new Promise((resolve) =>
          setTimeout(resolve, previewAnimDuration)
        );
      },
      destroy: (element) => {
        marks.removeDecoration(element);
      },
    }); // don't defer changes here because we want animations on computed properties

    starGraphPool = new AnimationPool(
      {
        create: (nodeID, info) => {
          let graph = new DecorationStarGraph(
            marks.getMarkByID(nodeID),
            info.linkedNodeIDs
              .map((id) => marks.getMarkByID(id))
              .filter((m) => !!m),
            SelectionOutlineZIndex,
            StarGraphZIndex
          );
          info.highlightedNodes = [nodeID, ...info.linkedNodeIDs];
          info.transient = info.transient || false;
          graph.getDecorations().forEach((d) => marks.addDecoration(d));
          return graph;
        },
        show: (element) => {
          element.enter(marks, decorationDuration);
          return new Promise((resolve) =>
            setTimeout(resolve, decorationDuration)
          );
        },
        hide: (element) => {
          element.exit(marks, decorationDuration);
          return new Promise((resolve) =>
            setTimeout(resolve, decorationDuration)
          );
        },
        destroy: (element) => {
          element.getDecorations().forEach((d) => marks.removeDecoration(d));
        },
      },
      true
    ); // defer changes to next frame to stabilize animations

    selectionDecorationPool = new AnimationPool(
      {
        create: (nodeID) => {
          let mark = marks.getMarkByID(nodeID);
          if (!mark) return null;
          return new Decoration('outline', [mark], {
            r: {
              valueFn: () => mark.attr('r') + 3.0,
            },
            color: '007bff',
            lineWidth: 2.0,
            zIndex: SelectionOutlineZIndex,
          });
        },
        show: async (element) => marks.addDecoration(element),
        hide: async (element) => marks.removeDecoration(element),
        destroy: () => {},
      },
      true
    );

    tentativeSelectionDecorationPool = new AnimationPool(
      {
        create: (nodeID) => {
          let mark = marks.getMarkByID(nodeID);
          if (!mark) return null;
          return new Decoration('outline', [mark], {
            r: {
              valueFn: () => mark.attr('r') + 3.0,
            },
            color: '007bff',
            lineWidth: 2.0,
            zIndex: SelectionOutlineZIndex,
            pulseDuration: 2.0,
          });
        },
        show: async (element) => marks.addDecoration(element),
        hide: async (element) => marks.removeDecoration(element),
        destroy: () => {},
      },
      true
    );

    alignDecorationPool = new AnimationPool(
      {
        create: (nodeID) => {
          let mark = marks.getMarkByID(nodeID);
          if (!mark) return null;
          return new Decoration('outline', [mark], {
            r: {
              valueFn: () => mark.attr('r') + 3.0,
            },
            color: '#aaaaaa',
            lineWidth: 2.0,
            zIndex: SelectionOutlineZIndex,
          });
        },
        show: async (element) => marks.addDecoration(element),
        hide: async (element) => marks.removeDecoration(element),
        destroy: () => {},
      },
      true
    );

    labelPool = new AnimationPool(
      {
        create: (nodeID) => {
          let mark = marks.getMarkByID(nodeID);
          let dataItem = frame.byID(nodeID);
          if (!mark || !dataItem || !dataItem.label) return null;
          if (!!dataItem.label.sheet) {
            return new Decoration('image', [mark], {
              color: null,
              labelInfo: dataItem.label,
              priority: { valueFn: () => _getLabelPriority(mark) },
              alpha: 0.0,
              maxDim: 50.0, // maximum width or height
            });
          } else if (!!dataItem.label.text) {
            return new Decoration('text', [mark], {
              color: 'black',
              text: dataItem.label.text,
              priority: { valueFn: () => _getLabelPriority(mark) },
              textScale: 1.0,
              alpha: 0.0,
            });
          }
        },
        show: async (element) => marks.addDecoration(element),
        hide: async (element) => marks.removeDecoration(element),
        destroy: () => {},
      },
      true
    );
  }

  function setStarGraphTransient(nodeID, transient) {
    let info = starGraphPool.getInfo(nodeID);
    if (!!info) info.transient = transient;
  }

  let oldNeighbors = 0;
  $: if (oldNeighbors != numNeighbors) {
    if (!!starGraphPool) {
      starGraphPool.getAllVisibleIDs().forEach((id) => {
        updateStarGraph(id);
      });
    }
    oldNeighbors = numNeighbors;
  }

  function updateStarGraph(nodeID, animated = true) {
    let info = starGraphPool.getInfo(nodeID);
    let element = starGraphPool.getElement(nodeID);
    if (!element) {
      showStarGraph(nodeID);
      return;
    }

    let item = frame.byID(nodeID);
    if (item) {
      let newNeighbors = (item.highlightIndexes || []).slice(0, numNeighbors);
      info.highlightedNodes = [info.highlightedNodes[0], ...newNeighbors];
      element.updateNeighborMarks(
        newNeighbors.map((id) => marks.getMarkByID(id)).filter((m) => !!m),
        marks,
        animated ? decorationDuration : 0
      );
    } else {
      starGraphPool.hide(nodeID);
    }
  }

  function showStarGraph(id, transient = false) {
    setStarGraphTransient(id, transient);
    starGraphPool.show(id, () => {
      let item = frame.byID(id);
      if (!item) return;
      let neighbors = (item.highlightIndexes || []).slice(0, numNeighbors);
      return {
        linkedNodeIDs: neighbors,
        transient,
      };
    });
  }

  function updateStarGraphVisibility() {
    if (!starGraphPool) return;

    // Only show for hovered ID and single clicked ID
    let visibleGraphs = new Set();
    let transientID = null;
    if (!!hoveredID) {
      visibleGraphs.add(hoveredID);
      transientID = hoveredID;
    }
    if (selectedIDs.length == 1) {
      let selected = selectedIDs[0];
      setStarGraphTransient(selected, false);
      visibleGraphs.add(selected);
      if (transientID == selected) transientID = null;
    }
    starGraphPool.getAllIDs().forEach((key) => {
      if (!visibleGraphs.has(key)) starGraphPool.hide(key);
    });
    visibleGraphs.forEach((key) => {
      showStarGraph(key, key == transientID);
    });
  }

  function updateAlignmentDecorations() {
    // Only show for points in alignedIDs but not selectedIDs
    let idsToShow = new Set();
    alignedIDs.forEach((id) => idsToShow.add(id));
    selectedIDs.forEach((id) => idsToShow.delete(id));

    alignDecorationPool.getAllVisibleIDs().forEach((id) => {
      alignDecorationPool.hide(id);
    });
    idsToShow.forEach((id) => alignDecorationPool.show(id));
  }

  function updateLabelVisibility() {
    let labeledPoints;
    if (selectedIDs.length > 10) {
      // Only label the selected points
      labeledPoints = new Set(selectedIDs);
    } else {
      labeledPoints = new Set(highlightedPoints);
    }
    if (!!hoveredID) labeledPoints.add(hoveredID);
    labelPool.getAllIDs().forEach((key) => {
      if (!labeledPoints.has(key)) labelPool.hide(key);
    });
    labeledPoints.forEach((id) => labelPool.show(id));
  }

  function updateTentativeSelectionVisibility(
    oldTentativeIDs,
    newTentativeIDs
  ) {
    tentativeSelectionDecorationPool.getAllIDs().forEach((id) => {
      tentativeSelectionDecorationPool.hide(id);
    });
    newTentativeIDs.forEach((id) => tentativeSelectionDecorationPool.show(id));
  }
</script>
