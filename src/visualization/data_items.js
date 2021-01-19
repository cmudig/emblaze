import { approxEquals } from "./helpers";

// info can be a static value or an object containing the following allowed
// keys: value, transform, valueFn, cached, computeArg. One of (value, valueFn)
// is required.
export function Attribute(info) {
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
  }

  this.currentTime = 0;
  this.needsUpdate = false;
  this.animation = null;
  this.label = null;
  this._getterValue = null; // This is precomputed in advance() and returned by get()
  this._computedLastValue = null; // Value to use as initial interpolant if this is a computed value and animated

  this.compute = function () {
    if (!!this.valueFn) {
      this._computedLastValue = this.valueFn(this.computeArg || this);
    }
  };

  // Advances the time of the animation by the given number of msec,
  // and returns whether or not a redraw is needed
  this.advance = function (dt) {
    if (this.animation != null || this.needsUpdate || !!this.valueFn) {
      this.currentTime += dt;
    }

    if (this.animation != null || this.needsUpdate) {
      this.needsUpdate = false;
      this._computeAnimation();
      return true;
    }
    return false;
  };

  this._computeAnimation = function () {
    if (!this.animation) return;

    // Evaluate the animation
    let { animator, start } = this.animation;
    let value = animator.evaluate(
      !!this.valueFn ? this._computedLastValue : this.value,
      Math.min(this.currentTime - start, animator.duration)
      // can add a debug flag here
    );
    // Complete the animation if within one frame
    if (animator.duration - 20 <= this.currentTime - start) {
      if (!!this.valueFn) this.compute();
      else this.value = value;
      this.animation = null;
      this._getterValue = null;
    } else {
      this._getterValue = value;
    }
  };

  this.get = function (transform = true) {
    let value;
    if (this._getterValue != null) value = this._getterValue;
    else if (!!this.valueFn) {
      this.compute();
      value = this._computedLastValue;
    } else value = this.value;

    if (transform && !!this.transform) {
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
  };

  this.set = function (newValue) {
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
  };

  // Gets the non-animated value
  this.data = function () {
    if (!!this.valueFn) {
      return this.valueFn(this.computeArg || this);
    } else {
      return this.value;
    }
  };

  // Marks that the transform has changed for the given attribute
  this.updateTransform = function () {
    this._cachedValue = null;
  };

  // Animations should have an evaluate()
  // method that takes as parameter an initial value and a time
  // delta from start (in msec) and returns a new value for the
  // attribute, and a duration property in msec
  this.animate = function (animation) {
    if (!!this.animation) {
      // Set the current value of the property to wherever it is now
      if (!this.valueFn) {
        this.value = this.get(false);
      } else {
        this._computedLastValue = this.get(false);
      }
    }

    this.animation = {
      animator: animation,
      start: this.currentTime,
    };
    this._computeAnimation();
  };
}

const ExcessiveUpdateThreshold = 5000;

export function Mark(id, attributes, special = false) {
  // Describes the appearance of a scatterplot point.

  this.id = id;
  this.special = special;
  this.attributes = {};
  Object.keys(attributes).forEach((attrName) => {
    let attrib = new Attribute(attributes[attrName]);
    attrib.computeArg = this;
    this.attributes[attrName] = attrib;
  });

  // Warning system to detect when an attribute is being listed as animated
  // for no reason
  this.framesWithUpdate = 0;

  // Advances the time of the animations by the given number of msec,
  // and returns whether or not a redraw is needed
  this.advance = function (dt) {
    let updated = false;
    Object.values(this.attributes).forEach((attr) => {
      if (attr.advance(dt)) updated = true;
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
  };

  // Basically plays an instantaneous animation
  this.setAttr = function (attrName, newValue) {
    // Set the value in case there will be an animation from this point
    this.attributes[attrName].set(newValue);
    this.needsUpdate = true;
  };

  this.attr = function (attrName, transform = true) {
    if (!this.attributes[attrName]) {
      console.error("Attempting to access unknown attribute:", attrName);
      return undefined;
    }
    return this.attributes[attrName].get(transform);
  };

  // Gets the true data value (non-animated)
  this.data = function (attrName) {
    return this.attributes[attrName].data();
  };

  // Marks that the transform has changed for the given attribute
  this.updateTransform = function (attrName) {
    this.attributes[attrName].updateTransform();
  };

  // Animations should have an evaluate()
  // method that takes as parameter an initial value and a time
  // delta from start (in msec) and returns a new value for the
  // attribute, and a duration property in msec
  this.animate = function (attrName, animation) {
    if (!this.attributes.hasOwnProperty(attrName)) {
      console.error("Attempting to animate undefined property " + attrName);
      return;
    }

    this.attributes[attrName].animate(animation);
  };
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
export function Decoration(type, marks, attributes) {
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

  this._marks = [];
  this._data = {};
  this._updatedAttributes = new Set(); // attribute names that have been calculated since the last update

  // Advances the time of the animations by the given number of msec,
  // and returns whether or not a redraw is needed
  this.advance = function (dt) {
    let updated = false;
    Object.values(this.attributes).forEach((attr) => {
      if (attr.advance(dt)) updated = true;
    });
    return updated;
  };

  this.attr = function (attrName) {
    return this.attributes[attrName].get();
  };

  this.data = function (attrName) {
    return this.attributes[attrName].data();
  };

  this.setAttr = function (attrName, value) {
    this.attributes[attrName].set(value);
  };

  this.update = function () {};

  this.animate = function (attrName, animation) {
    this.attributes[attrName].animate(animation);
  };
}

// Keeps track of a set of marks. This is helpful to track which
// marks are being animated, thereby saving on computation in each
// run loop.
export function MarkSet(marks, decorations = null) {
  // Array and object representations for marks
  this.marks = marks;
  this.marksByID = {};
  this.marks.forEach((m) => (this.marksByID[m.id] = m));

  // Array and object representations for decorations
  this.decorations = decorations || [];
  this.decorationsByID = {};
  this.decorations.forEach((d) => {
    d.marks.forEach((m) => {
      if (!this.decorationsByID.hasOwnProperty(m.id)) {
        this.decorationsByID[m.id] = new Set([d]);
      } else {
        this.decorationsByID[m.id].add(d);
      }
    });
  });

  let animatingMarks = new Set();
  let animatingDecorations = new Set();

  // Advances all of the marks and returns true if a redraw is needed
  this.advance = function (dt) {
    if (animatingMarks.size == 0 && animatingDecorations.size == 0)
      return false;

    let updatedDecorations = new Set();
    for (let mark of animatingMarks) {
      if (!mark.advance(dt)) {
        animatingMarks.delete(mark);
      } else if (!!this.decorationsByID[mark.id]) {
        // Animate decorations associated with this
        this.decorationsByID[mark.id].forEach((d) => {
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
    return animatingMarks.size > 0 || animatingDecorations.size > 0;
  };

  this.animateAll = function (
    attrName,
    interpolatorMapper,
    duration = 1000,
    curve = null
  ) {
    animatingMarks = new Set(this.marks);

    this.marks.forEach((mark, i) =>
      mark.animate(
        attrName,
        new Animator(interpolatorMapper(mark, i), duration, curve)
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
    animatingMarks = new Set(this.marks);

    this.marks.forEach((mark, i) =>
      mark.animate(
        attrName,
        new Animator(interpolatorFn(mark.data(attrName)), duration, curve)
      )
    );
  };

  this.animateIf = function (
    attrName,
    predicateFn,
    interpolatorFn,
    duration = 1000,
    curve = null
  ) {
    this.marks.forEach((mark, i) => {
      if (!predicateFn(mark, i)) return;
      animatingMarks.add(mark);
      mark.animate(
        attrName,
        new Animator(interpolatorFn(mark, i), duration, curve)
      );
    });
  };

  this.animateOne = function (index, attrName, animator) {
    animatingMarks.add(this.marks[index]);
    this.marks[index].animate(attrName, animator);
  };

  this.setAll = function (attrName, valueFn) {
    animatingMarks = new Set(this.marks);

    this.marks.forEach((mark, i) => mark.setAttr(attrName, valueFn(mark, i)));
  };

  this.setIf = function (attrName, predicateFn, valueFn) {
    this.marks.forEach((mark, i) => {
      if (!predicateFn(mark, i)) return;
      animatingMarks.add(mark);
      mark.setAttr(attrName, valueFn(mark, i));
    });
  };

  this.setOne = function (index, attrName, value) {
    animatingMarks.add(this.marks[index]);
    this.marks[index].setAttr(attrName, value);
  };

  this.addDecoration = function (decoration) {
    this.decorations.push(decoration);
    for (let m of decoration.marks) {
      if (!this.decorationsByID.hasOwnProperty(m.id)) {
        this.decorationsByID[m.id] = new Set([decoration]);
      } else {
        this.decorationsByID[m.id].add(decoration);
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
      this.decorationsByID[m.id].delete(decoration);
    }
  };

  this.animateDecoration = function (decoration, attrName, animation) {
    animatingDecorations.add(decoration);
    decoration.animate(attrName, animation);
  };

  this.updateAllDecorations = function () {
    this.decorations.forEach((d) => d.update());
  };

  this.getMarkByID = function (id) {
    return this.marksByID[id];
  };

  this.forEach = function (callbackfn) {
    this.marks.forEach(callbackfn);
  };

  this.map = function (mapper) {
    return this.marks.map(mapper);
  };

  this.filter = function (filterer) {
    return this.marks.filter(filterer);
  };

  this.reduce = function (reducer, initial) {
    return this.marks.reduce(reducer, initial);
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
  return (initialValue, interpolant, debug = false) => {
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
  };
}

// Interpolates to a potentially changing final value
export function interpolateToFunction(finalValueFn) {
  return (initialValue, interpolant) =>
    initialValue * (1 - Math.min(interpolant, 1.0)) +
    finalValueFn() * Math.min(interpolant, 1.0);
}

export function Animator(interpolator, duration = 1000, curve = null) {
  this.duration = duration;

  curve = curve || ((x) => x);

  this.evaluate = function (initialValue, dt, debug = false) {
    let t = curve(dt / this.duration);
    return interpolator(initialValue, t, debug);
  };
}
