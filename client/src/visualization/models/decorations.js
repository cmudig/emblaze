import {
  interpolateTo,
  Decoration,
  Animator,
  easeInOut,
} from './data_items.js';
import { circumscribeCircle } from '../utils/enclosing_circle.js';
import { getWithFallback } from '../utils/helpers';

// Defines the visual decoration appearance of a star graph
export function DecorationStarGraph(
  centerMark,
  neighborMarks,
  outlineZIndex = 0,
  lineZIndex = 0
) {
  this.centerMark = centerMark;
  this.neighborMarks = neighborMarks;
  this.isOn = false;

  this.outlineDecoration = new Decoration('outline', [this.centerMark], {
    r: {
      valueFn: () => (this.isOn ? this.centerMark.attr('r') + 3.0 : 0.0),
    },
    color: '007bff',
    lineWidth: 1.0,
    zIndex: outlineZIndex,
  });

  this._makeNeighborDecoration = function (mark) {
    let dec = new Decoration('line', [this.centerMark, mark], {
      color: '007bff',
      lineWidth: 0.5,
      alpha: { valueFn: () => (this.isOn ? 1.0 : 0.0) },
      x2: {
        valueFn: () => (this.isOn ? mark.attr('x') : this.centerMark.attr('x')),
      },
      y2: {
        valueFn: () => (this.isOn ? mark.attr('y') : this.centerMark.attr('y')),
      },
      zIndex: lineZIndex,
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
    markSet.animateDecorationComputed(d, 'x2', duration, curve);
    markSet.animateDecorationComputed(d, 'y2', duration, curve);
    markSet.animateDecorationComputed(d, 'alpha', duration, curve);
  };

  this.enter = function (markSet, duration = 300, curve = null) {
    this.isOn = true;
    markSet.animateDecoration(
      this.outlineDecoration,
      'r',
      new Animator(
        interpolateTo(this.outlineDecoration.data('r')),
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
      'r',
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

const PreviewHaloMargin = 5.0;

// This class wraps a simple circular decoration that positions itself to surround
// the marks it's associated with.
export function ClusterPreviewHalo(marks, color, alpha, colorID) {
  this.marks = marks;
  this.isOn = false;
  this.alpha = alpha;

  this.isHovering = false;

  // Compute static location
  let points = this.marks.map((mark) => [
    mark.attr('x', false),
    mark.attr('y', false),
  ]);
  this.circle = circumscribeCircle(points);
  let xTransform = this.marks[0].attributes.x.transform;
  let yTransform = this.marks[0].attributes.y.transform;

  this.decoration = new Decoration('halo', this.marks, {
    x: {
      value: this.circle.x,
      transform: xTransform,
    },
    y: {
      value: this.circle.y,
      transform: yTransform,
    },
    r: {
      valueFn: () => (this.isOn ? this.circle.r : 0.0),
      transform: (val) =>
        this.isOn ? xTransform(val) - xTransform(0.0) + PreviewHaloMargin : 0.0,
    },
    color,
    colorID,
    alpha: {
      valueFn: () => (this.isOn ? this.alpha : 0.0),
    },
    lineWidth: {
      valueFn: () => (this.isOn && this.isHovering ? 3.0 : 0.0),
    },
  });

  this.getDecorations = function () {
    return [this.decoration];
  };

  this.enter = function (markSet, duration = 300, curve = null) {
    this.isOn = true;
    markSet.animateDecoration(
      this.decoration,
      'r',
      new Animator(interpolateTo(this.decoration.data('r')), duration, curve)
    );
    markSet.animateDecoration(
      this.decoration,
      'alpha',
      new Animator(
        interpolateTo(this.decoration.data('alpha')),
        duration,
        curve
      )
    );
  };

  this.exit = function (markSet, duration = 300, curve = null) {
    this.isOn = false;
    markSet.animateDecoration(
      this.decoration,
      'r',
      new Animator(interpolateTo(this.decoration.data('r')), duration, curve)
    );
    markSet.animateDecoration(
      this.decoration,
      'alpha',
      new Animator(
        interpolateTo(this.decoration.data('alpha')),
        duration,
        curve
      )
    );
  };

  this.animateHover = function (markSet, hovering) {
    this.isHovering = hovering;
    markSet.animateDecoration(
      this.decoration,
      'lineWidth',
      new Animator(interpolateTo(this.decoration.data('lineWidth')), 200)
    );
  };
}

export class WideningLineDecoration extends Decoration {
  mark;
  dataItem;
  frame1;
  frame2;

  constructor(mark, frame, lineWidthFn, lineAlphaFn) {
    super('wideningLine', [mark], {
      x2: {
        value: 0.0,
        transform: mark.attributes['x'].transform,
      },
      y2: {
        value: 0.0,
        transform: mark.attributes['y'].transform,
      },
      lineWidth: {
        valueFn: () => lineWidthFn(mark),
      },
      alpha: {
        valueFn: () => mark.attr('alpha') * lineAlphaFn(mark),
      },
      color: {
        valueFn: () => mark.attr('fillStyle'),
      },
    });

    this.frame1 = frame;
    this.frame2 = frame;
    this.mark = mark;
    this.attributes['x2'].set(() => this._getX2());
    this.attributes['x2'].compute();
    this.attributes['y2'].set(() => this._getY2());
    this.attributes['y2'].compute();
  }

  _getX() {
    return this.frame1.get(this.mark.id, 'x', this.mark.attr('x'));
  }

  _getY() {
    return this.frame1.get(this.mark.id, 'y', this.mark.attr('y'));
  }

  _getX2() {
    return this.frame2.get(this.mark.id, 'x', this.mark.attr('x'));
  }

  _getY2() {
    return this.frame2.get(this.mark.id, 'y', this.mark.attr('y'));
  }

  animateToFrames(markSet, frame1, frame2, duration = 300) {
    if (this.frame1 !== frame1) {
      this.frame1 = frame1;
      markSet.animateDecorationComputed(this, 'x', duration, easeInOut);
      markSet.animateDecorationComputed(this, 'y', duration, easeInOut);
    }
    if (this.frame2 !== frame2) {
      this.frame2 = frame2;
      markSet.animateDecorationComputed(this, 'x2', duration, easeInOut);
      markSet.animateDecorationComputed(this, 'y2', duration, easeInOut);
    }
  }

  updateLineAppearance(markSet, duration = 300) {
    markSet.animateDecorationComputed(this, 'lineWidth', duration, easeInOut);
    markSet.animateDecorationComputed(this, 'alpha', duration, easeInOut);
    markSet.animateDecorationComputed(this, 'color', duration, easeInOut);
  }
}
