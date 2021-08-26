import { approxEquals, makeTimeProvider } from "../utils/helpers";

// info can be a static value or an object containing the following allowed
// keys: value, transform, valueFn, cached, computeArg. One of (value, valueFn)
// is required.
export class Attribute {
  value = null;
  valueFn = null;
  transform = null;
  cached = false;
  _cachedValue = null;
  computeArg = null;
  precompute = false;
  lazy = false;
  needsUpdate = false;
  animation = null;
  label = null; // for debugging
  _getterValue = null; // This is precomputed in advance() and returned by get()
  _computedLastValue = null; // Value to use as initial interpolant if this is a computed value and animated
  _hasComputed = false;
  _timeProvider = null; // REQUIRED for animation
  currentTime = 0;

  constructor(info) {
    if (
      info == undefined ||
      info == null ||
      !(info.hasOwnProperty("value") || info.hasOwnProperty("valueFn"))
    ) {
      this.value = info;
      this.valueFn = null;
      this.transform = null;
      this.cached = false;
      this._cachedValue = null;
      this.computeArg = null;
      this.precompute = false;
      this.lazy = false;
    } else {
      if (info.hasOwnProperty("value")) {
        this.value = info.value;
      } else {
        this.valueFn = info.valueFn;
      }
      this.transform = info.transform || null;
      this.cached = info.cached || false;
      this._cachedValue = null;
      this.computeArg = info.computeArg || null;
      this.precompute = info.precompute || false; // if this is true, always compute this on advance()
      this.lazy = info.lazy || false; // if true, only updates computed value on animate() or compute()
    }
  }

  setTimeProvider(timeProvider) {
    this._timeProvider = timeProvider;
  }

  compute() {
    if (!!this.valueFn) {
      this._computedLastValue = this.valueFn(this.computeArg || this);
    }
  }

  // Advances the time of the animation by the given number of msec,
  // and returns whether or not a redraw is needed
  advance(dt) {
    if (this.animation != null || this.needsUpdate || !!this.valueFn) {
      if (!!dt) this.currentTime += dt;
      else this.currentTime = this._timeProvider();
    }

    if (this._animationFinished()) {
      this._computeAnimation();
    }
    if (this.animation != null || this.needsUpdate) {
      this.needsUpdate = false;
      return true;
    } else if (this.precompute) {
      this.compute();
    }
    return false;
  }

  _computeAnimation(recomputeOnComplete = true) {
    if (!this.animation) return;
    if (!!this._timeProvider) this.currentTime = this._timeProvider();

    // Evaluate the animation
    let { animator, start } = this.animation;
    let value = animator.evaluate(
      !!this.valueFn ? this._computedLastValue : this.value,
      Math.min(this.currentTime - start, animator.duration)
      // can add a debug flag here
    );
    // Complete the animation if within one frame
    if (this._animationFinished() && recomputeOnComplete) {
      if (!!this.valueFn) this.compute();
      else this.value = value;
      this.animation = null;
      this._getterValue = null;
    } else {
      this._getterValue = value;
    }
  }

  _animationFinished() {
    if (!this.animation) return true;
    return (
      this.animation.animator.duration - 20 <=
      this.currentTime - this.animation.start
    );
  }

  _transform(value) {
    if (!!this.transform) {
      let cached = this._cachedValue;
      if (!!cached && approxEquals(cached.raw, value)) {
        value = cached.result;
      } else {
        let raw = value;
        value = this.transform(value, this.computeArg);

        if (this.cached) {
          this._cachedValue = {
            raw,
            result: value,
          };
        }
      }
    }
    return value;
  }

  get(transform = true) {
    this._computeAnimation();

    let value;
    if (this._getterValue != null) value = this._getterValue;
    else if (!!this.valueFn) {
      if (!this.lazy || !this._hasComputed) {
        this.compute();
        this._hasComputed = true;
      }
      value = this._computedLastValue;
    } else value = this.value;

    if (transform) {
      value = this._transform(value);
    }

    return value;
  }

  // Returns an object that tells a renderer how to animate this attribute,
  // including four properties: start and end (the initial and final values of
  // the attribute) and startTime and endTime (the timestamps for the start and
  // end of the animation, in ms). If there is no animation, startTime and endTime
  // will be equal.
  // If currentTime is provided, the startTime and endTime values will be
  // converted to match this time.
  getPreload(transform = true, currentTime = null) {
    if (!!this._timeProvider) this.currentTime = this._timeProvider();

    if (!this.animation) {
      let value = this.get(transform);
      return {
        start: value,
        end: value,
        startTime: currentTime || this.currentTime,
        endTime: currentTime || this.currentTime,
      };
    }
    if (!(this.animation.animator instanceof PreloadableAnimator)) {
      console.error(
        "Calling getPreload for a non-preloadable animation is forbidden. If using MarkSet, make sure this attribute is registered as preloadable."
      );
      return null;
    }

    if (this._animationFinished()) {
      this._computeAnimation();
      return this.getPreload(transform, currentTime);
    }

    let value;
    if (!!this.valueFn) {
      if (!this.lazy || !this._hasComputed) {
        this.compute();
        this._hasComputed = true;
      }
      value = this._computedLastValue;
    } else value = this.value;

    if (transform) {
      value = this._transform(value);
    }

    // Get final value
    let finalValue = this.animation.animator.finalValue;
    if (transform) {
      finalValue = this._transform(finalValue);
    }

    let timeDelta = (currentTime || this.currentTime) - this.currentTime;
    return {
      start: value,
      end: finalValue,
      startTime: this.animation.start + timeDelta,
      endTime:
        this.animation.start + this.animation.animator.duration + timeDelta,
    };
  }

  set(newValue) {
    if (typeof newValue == "function") {
      if (this.value != null) this._computedLastValue = this.value;
      this.valueFn = newValue;
      this.value = null;
      this._getterValue = null;
    } else {
      this.value = newValue;
      this.valueFn = null;
      this._getterValue = null;
    }
    this.needsUpdate = true;
  }

  // Gets the non-animated value
  data() {
    if (!!this.valueFn) {
      return this.valueFn(this.computeArg || this);
    } else {
      return this.value;
    }
  }

  // Returns the last value (including if computed), without doing any computation
  last() {
    if (!!this.animation) {
      // We're in a dirty state - a preloadable animation is underway and
      // the attribute hasn't been updated using the advance() method yet.
      // Because any updates to the attribute would result in the proper values
      // being set, we can just evaluate the animation here (without recomputing
      // if the animation is finished).
      this._computeAnimation(false);
    }

    if (this._getterValue != null) return this._getterValue;
    return this._computedLastValue;
  }

  // Returns the value that this attribute is approaching if animating (or null
  // if not available), or the current value if not animating.
  future() {
    if (!!this.animation) {
      return this.animation.animator.finalValue;
    }
    return this.last();
  }

  // Marks that the transform has changed for the given attribute
  updateTransform() {
    this._cachedValue = null;
  }

  // Animations should have an evaluate()
  // method that takes as parameter an initial value and a time
  // delta from start (in msec) and returns a new value for the
  // attribute, and a duration property in msec
  animate(animation) {
    if (!!this._timeProvider) this.currentTime = this._timeProvider();

    if (!!this.animation) {
      // Set the current value of the property to wherever it is now
      if (!this.valueFn) {
        this.value = this.last();
      } else {
        this._computedLastValue = this.last();
      }
    }

    this.animation = {
      animator: animation,
      start: this.currentTime,
    };
    this._computeAnimation();
  }
}

const ExcessiveUpdateThreshold = 5000;

export class Mark {
  // Describes the appearance of a scatterplot point.

  _timeProvider = null;
  id;
  special = false;
  attributes = {};

  constructor(id, attributes, special = false) {
    this.id = id;
    this.special = special;
    this.attributes = {};
    Object.keys(attributes).forEach((attrName) => {
      let attrib = new Attribute(attributes[attrName]);
      attrib.computeArg = this;
      this.attributes[attrName] = attrib;
    });
  }

  setTimeProvider(timeProvider) {
    this._timeProvider = timeProvider;
    Object.values(this.attributes).forEach((attr) =>
      attr.setTimeProvider(this._timeProvider)
    );
  }

  // Warning system to detect when an attribute is being listed as animated
  // for no reason
  framesWithUpdate = 0;

  // Advances the time of the animations by the given number of msec,
  // and returns whether or not a redraw is needed
  advance() {
    let updated = false;
    Object.values(this.attributes).forEach((attr) => {
      if (attr.advance()) updated = true;
    });
    if (updated) {
      this.framesWithUpdate += 1;
      if (this.framesWithUpdate > ExcessiveUpdateThreshold) {
        console.warn("Marks are being updated excessively!");
      }
      return true;
    }
    this.framesWithUpdate = 0;
    return false;
  }

  // Basically plays an instantaneous animation
  setAttr(attrName, newValue) {
    // Set the value in case there will be an animation from this point
    this.attributes[attrName].set(newValue);
    this.needsUpdate = true;
  }

  attr(attrName, transform = true) {
    if (!this.attributes[attrName]) {
      return undefined;
    }
    return this.attributes[attrName].get(transform);
  }

  // Gets the true data value (non-animated)
  data(attrName) {
    return this.attributes[attrName].data();
  }

  // Marks that the transform has changed for the given attribute
  updateTransform(attrName) {
    this.attributes[attrName].updateTransform();
  }

  // Animations should have an evaluate()
  // method that takes as parameter an initial value and a time
  // delta from start (in msec) and returns a new value for the
  // attribute, and a duration property in msec
  animate(attrName, animation) {
    if (!this.attributes.hasOwnProperty(attrName)) {
      console.error("Attempting to animate undefined property " + attrName);
      return;
    }

    this.attributes[attrName].animate(animation);
  }
}

// Decorations are visual elements that are drawn on top of marks.
// They are linked to a set of IDs, and will be updated whenever
// those marks change. The attr method of a decoration returns all
// attributes necessary to draw the decoration; the decoration's internal
// state will automatically be updated when the associated marks change
// (as long as the marks and decorations are embedded in a MarkSet).
// The values in the attributes object passed into the constructor can be
// static objects or functions that take an array of marks and return new values
// for the attributes.
//
// The following types of decorations are supported:
// * outline - takes one mark as argument. Exposes the following attributes:
//   x, y, lineWidth, color, r, alpha
// * line - takes two marks as arguments. Exposes the following attributes:
//   x, y, x2, y2, lineWidth, color, alpha
// * text - takes one mark as argument. Exposes the following attributes:
//   x, y, text, font, textAlignment, alpha
// The x, y, x2, and y2 properties are populated by default. Other properties
// must be specified in the attributes object.
export class Decoration {
  type;
  marks;

  constructor(type, marks, attributes) {
    this.type = type;
    this.marks = marks;

    // Initialize attributes
    this.attributes = {};
    Object.keys(attributes).forEach((attrName) => {
      let attrib = new Attribute(attributes[attrName]);
      this.attributes[attrName] = attrib;
    });
    if (!this.attributes.hasOwnProperty("x")) {
      this.attributes.x = new Attribute({
        valueFn: () => this.marks[0].attr("x"),
      });
    }
    if (!this.attributes.hasOwnProperty("y")) {
      this.attributes.y = new Attribute({
        valueFn: () => this.marks[0].attr("y"),
      });
    }
    if (!this.attributes.hasOwnProperty("alpha")) {
      this.attributes.alpha = new Attribute(1.0);
    }
    if (this.marks.length > 1) {
      if (!this.attributes.hasOwnProperty("x2")) {
        this.attributes.x2 = new Attribute({
          valueFn: () => this.marks[1].attr("x"),
        });
      }
      if (!this.attributes.hasOwnProperty("y2")) {
        this.attributes.y2 = new Attribute({
          valueFn: () => this.marks[1].attr("y"),
        });
      }
    }
    Object.values(this.attributes).forEach((val) => {
      val.computeArg = this;
      val.compute();
    });
  }

  // Advances the time of the animations by the given number of msec,
  // and returns whether or not a redraw is needed
  advance(dt) {
    let updated = false;
    Object.values(this.attributes).forEach((attr) => {
      if (attr.advance(dt)) updated = true;
    });
    return updated;
  }

  attr(attrName) {
    if (!this.attributes.hasOwnProperty(attrName)) return null;
    return this.attributes[attrName].get();
  }

  data(attrName) {
    if (!this.attributes.hasOwnProperty(attrName)) return null;
    return this.attributes[attrName].data();
  }

  setAttr(attrName, value) {
    this.attributes[attrName].set(value);
  }

  update() {}

  animate(attrName, animation) {
    this.attributes[attrName].animate(animation);
  }
}

// Keeps track of a set of marks. This is helpful to track which
// marks are being animated, thereby saving on computation in each
// run loop.
export function MarkSet(marks, decorations = null) {
  let timeProvider = makeTimeProvider();

  // Array and object representations for marks
  this.marks = marks;
  this.marksByID = new Map();
  this.marks.forEach((m) => {
    this.marksByID.set(m.id, m);
    m.setTimeProvider(timeProvider);
  });

  // Array and object representations for decorations
  this.decorations = decorations || [];
  this.decorationsByID = new Map();
  this.decorations.forEach((d) => {
    d.marks.forEach((m) => {
      if (!this.decorationsByID.has(m.id)) {
        this.decorationsByID.set(m.id, new Set([d]));
      } else {
        this.decorationsByID.get(m.id).add(d);
      }
    });
  });

  let animatingMarks = new Set();
  let animatingDecorations = new Set();

  // Marks updated in this frame
  let updatedMarks = new Set();

  this.preloadableProperties = new Set();

  let visibleMarks = null;
  let visibleMarksChanged = false;

  this.setVisibleMarks = function (ids) {
    ids = Array.from(ids);
    if (ids.length == 0) visibleMarks = null;
    else visibleMarks = ids.map((id) => this.getMarkByID(id));
    visibleMarksChanged = true;
  }

  this.getVisibleMarks = function () {
    if (visibleMarks == null) return this.marks;
    return visibleMarks;
  }

  /**
   * Declares that the given attribute will only ever use preloadable animations.
   * Preloadable attributes will not be counted in calls to marksAnimating, and
   * only initial changes will be reflected in marksChanged. This permits
   * faster rendering by computing animations in shaders, and only computing
   * them on the CPU when explicitly requested through a call to Attribute.get().
   * Note that animations to these properties must be created through
   * MarkSet.animatePreload, animateComputed, or using MarkSet.animateOne with a
   * PreloadableAnimator.
   *
   * @param {string} attrName the attribute to register
   */
  this.registerPreloadableProperty = function (attrName) {
    this.preloadableProperties.add(attrName);
  };

  // Advances all of the marks and returns true if a redraw is needed
  this.advance = function (dt) {
    timeProvider.advance(dt);

    updatedMarks = new Set();
    if (animatingMarks.size == 0 && animatingDecorations.size == 0 && !visibleMarksChanged)
      return false;

    let updatedDecorations = new Set();
    for (let mark of animatingMarks) {
      if (!mark.advance()) {
        animatingMarks.delete(mark);
      } else if (this.decorationsByID.has(mark.id)) {
        // Animate decorations associated with this
        this.decorationsByID.get(mark.id).forEach((d) => {
          if (!updatedDecorations.has(d)) {
            d.advance(dt);
            d.update();
            updatedDecorations.add(d);
          }
        });
      }
    }
    for (let decoration of animatingDecorations) {
      if (updatedDecorations.has(decoration)) continue;
      if (!decoration.advance(dt)) animatingDecorations.delete(decoration);
    }

    visibleMarksChanged = false;

    return true;
  };

  // This reflects whether any mark properties have been changed since the last
  // advance() call, or if any animations have been added. If an animation is on
  // a non-preloadable property, this also returns true. Must be called BEFORE
  // advance().
  this.marksChanged = function () {
    return updatedMarks.size > 0 || visibleMarksChanged;
  };

  // This reflects if any marks are currently animating. Can be called before or
  // after advance().
  this.marksAnimating = function () {
    return animatingMarks.size > 0;
  };

  this.decorationsAnimating = function () {
    return animatingDecorations.size > 0;
  };

  this.animateAll = function (
    attrName,
    interpolatorMapper,
    duration = 1000,
    curve = null
  ) {
    if (this.preloadableProperties.has(attrName)) {
      console.warn(
        "Attempted to call animateAll on a preloadable property. You must use animatePreload or animateOne with a PreloadableAnimator."
      );
      return;
    }

    animatingMarks = new Set(this.getVisibleMarks());
    updatedMarks = new Set(this.getVisibleMarks());

    this.forEach((mark, i) =>
      mark.animate(
        attrName,
        new Animator(interpolatorMapper(mark, i), duration, curve)
      )
    );
  };

  this.animatePreload = function (attrName, finalValueMapper, duration = 1000) {
    if (!this.preloadableProperties.has(attrName)) {
      console.warn(
        "Attempted to call animatePreload on a non-preloadable property."
      );
      return;
    }
    // Don't update animatingMarks here because the animation will be computed
    // lazily
    updatedMarks = new Set(this.getVisibleMarks());

    this.forEach((mark, i) =>
      mark.animate(
        attrName,
        new PreloadableAnimator(finalValueMapper(mark, i), duration)
      )
    );
  };

  // Shorthand for animating a computed property. interpolatorFn should be an
  // interpolator function itself, such as interpolateTo
  this.animateComputed = function (
    attrName,
    interpolatorFn,
    duration = 1000,
    curve = null
  ) {
    let preloadable = this.preloadableProperties.has(attrName);
    this.forEach((mark, i) => {
      let newValue = mark.data(attrName);
      if (
        !approxEquals(newValue, mark.attributes[attrName].last()) ||
        !approxEquals(newValue, mark.attributes[attrName].future())
      ) {
        mark.animate(
          attrName,
          preloadable
            ? new PreloadableAnimator(newValue, duration)
            : new Animator(interpolatorFn(newValue), duration, curve)
        );
        if (!preloadable) animatingMarks.add(mark);
        updatedMarks.add(mark);
      }
    });
  };

  // Tells all marks to update a computed property.
  this.updateComputed = function (attrName) {
    this.forEach((mark) => {
      let attr = mark.attributes[attrName];
      let oldValue = attr.last();
      attr.compute();
      if (!approxEquals(oldValue, attr.data())) {
        animatingMarks.add(mark);
        updatedMarks.add(mark);
      }
    });
  };

  this.animateIf = function (
    attrName,
    predicateFn,
    interpolatorFn,
    duration = 1000,
    curve = null
  ) {
    this.forEach((mark, i) => {
      if (!predicateFn(mark, i)) return;
      animatingMarks.add(mark);
      updatedMarks.add(mark);
      mark.animate(
        attrName,
        new Animator(interpolatorFn(mark, i), duration, curve)
      );
    });
  };

  this.animateOne = function (index, attrName, animator) {
    animatingMarks.add(this.marks[index]);
    updatedMarks.add(this.marks[index]);
    this.marks[index].animate(attrName, animator);
  };

  this.setAll = function (attrName, valueFn) {
    animatingMarks = new Set(this.getVisibleMarks());
    updatedMarks = new Set(this.getVisibleMarks());

    this.forEach((mark, i) => mark.setAttr(attrName, valueFn(mark, i)));
  };

  this.setIf = function (attrName, predicateFn, valueFn) {
    this.forEach((mark, i) => {
      if (!predicateFn(mark, i)) return;
      animatingMarks.add(mark);
      updatedMarks.add(mark);
      mark.setAttr(attrName, valueFn(mark, i));
    });
  };

  this.setOne = function (index, attrName, value) {
    animatingMarks.add(this.marks[index]);
    updatedMarks.add(this.marks[index]);
    this.marks[index].setAttr(attrName, value);
  };

  this.addDecoration = function (decoration) {
    this.decorations.push(decoration);
    for (let m of decoration.marks) {
      if (!this.decorationsByID.has(m.id)) {
        this.decorationsByID.set(m.id, new Set([decoration]));
      } else {
        this.decorationsByID.get(m.id).add(decoration);
      }
    }
  };

  this.removeDecoration = function (decoration) {
    let idx = this.decorations.indexOf(decoration);
    if (idx < 0) {
      console.warn("Attempted to remove decoration that does not exist");
      return;
    }
    this.decorations.splice(idx, 1);
    for (let m of decoration.marks) {
      this.decorationsByID.get(m.id).delete(decoration);
    }
  };

  this.animateDecoration = function (decoration, attrName, animation) {
    animatingDecorations.add(decoration);
    decoration.animate(attrName, animation);
  };

  this.animateDecorationComputed = function (
    decoration,
    attrName,
    duration = 1000,
    curve = null
  ) {
    let newValue = decoration.data(attrName);
    if (
      !approxEquals(newValue, decoration.attributes[attrName].last()) ||
      !approxEquals(newValue, decoration.attributes[attrName].future())
    ) {
      animatingDecorations.add(decoration);
      decoration.animate(
        attrName,
        new Animator(interpolateTo(newValue), duration, curve)
      );
    }
  };

  this.updateAllDecorations = function () {
    this.decorations.forEach((d) => d.update());
  };

  this.getMarkByID = function (id) {
    return this.marksByID.get(id);
  };

  this.forEach = function (callbackfn) {
    this.getVisibleMarks().forEach(callbackfn);
  };

  this.map = function (mapper) {
    return this.getVisibleMarks().map(mapper);
  };

  this.filter = function (filterer) {
    return this.getVisibleMarks().filter(filterer);
  };

  this.reduce = function (reducer, initial) {
    return this.getVisibleMarks().reduce(reducer, initial);
  };

  this.updateTransform = function (attrName) {
    this.marks.forEach((m) => m.updateTransform(attrName));
  };
}

export function easeInOut(t) {
  return t * t * (3.0 - 2.0 * t);
}

// A simple interpolator that takes the initial value as argument
export function interpolateTo(finalValue) {
  return {
    finalValue,
    interpolator: (initialValue, interpolant, debug = false) => {
      if (typeof initialValue != "number" || typeof finalValue != "number") {
        if (debug) {
          console.log(
            "Not a number, returning final value",
            initialValue,
            finalValue
          );
        }
        return finalValue;
      }
      if (debug) {
        console.log("Interpolating", initialValue, finalValue, interpolant);
      }
      return (
        initialValue * (1 - Math.min(interpolant, 1.0)) +
        finalValue * Math.min(interpolant, 1.0)
      );
    },
  };
}

// Interpolates to a potentially changing final value
export function interpolateToFunction(finalValueFn) {
  return (initialValue, interpolant) =>
    initialValue * (1 - Math.min(interpolant, 1.0)) +
    finalValueFn() * Math.min(interpolant, 1.0);
}

// Interpolates along a sequence of values
export function interpolateAlongPath(path) {
  return (initialValue, interpolant) => {
    let interpIndex = Math.min(interpolant, 1.0) * (path.length - 1) - 1;
    let stepInterpolant = Math.min(interpIndex - Math.floor(interpIndex), 1.0);
    if (interpIndex < 0.0)
      return initialValue * (1 - stepInterpolant) + path[0] * stepInterpolant;
    else
      return (
        path[Math.floor(interpIndex)] * (1 - stepInterpolant) +
        path[Math.floor(interpIndex) + 1] * stepInterpolant
      );
  };
}

export class Animator {
  duration = 0;
  finalValue = null;
  interpolator = null;
  curve = null;

  constructor(interpolator, duration = 1000, curve = null) {
    this.duration = duration;
    if (interpolator.hasOwnProperty("finalValue")) {
      this.finalValue = interpolator.finalValue;
      this.interpolator = interpolator.interpolator;
    } else {
      this.finalValue = null;
      this.interpolator = interpolator;
    }

    this.curve = curve || ((x) => x);
  }

  evaluate(initialValue, dt, debug = false) {
    let t = this.curve(this.duration > 0 ? dt / this.duration : 1.0);
    return this.interpolator(initialValue, t, debug);
  }
}

// Implements a basic ease-in-out animation with a final value.
export class PreloadableAnimator extends Animator {
  constructor(finalValue, duration) {
    super(interpolateTo(finalValue), duration, easeInOut);
  }
}
