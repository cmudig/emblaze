/**
 * A helper class that manages a pool of objects with animatable states, such as
 * decorations.
 */

/**
 * A pool of objects with animatable states. You manage the appearance of
 * objects by calling show() and hide(). The animation pool keeps track of
 * objects that are in the process of being animated in and out, and destroys
 * them when hidden. All changes take effect at the frame *after* they are
 * registered, which enables you to call show() and hide() as much as necessary
 * without creating excessive animation calls.
 *
 * @param {Object} callbacks A set of callbacks defining how to create, show,
 *   update, and hide elements. Callbacks:
 *   - create(id, info): Create an element based on the given ID and info.
 *   - show(element): Show the given element and return a Promise that resolves
 *       after the animation would be completed.
 *   - hide(element): Hide the given element and return a Promise that resolves
 *       after the animation would be completed.
 *   - destroy(element): Destroy the element.
 */
export default function AnimationPool(callbacks, defer = false) {
  this.callbacks = callbacks;
  this.defer = defer;
  if (
    !this.callbacks.create ||
    !this.callbacks.show ||
    !this.callbacks.hide ||
    !this.callbacks.destroy
  )
    console.error("Missing required callbacks for AnimationPool");

  this.pool = {};

  // Contains directives per pool ID that are cleared at every run loop.
  this.queuedAnimations = {};
  this._flushTimer = null;

  this._perform = function (id, action) {
    let item = this.pool[id];
    if (!item || !item.element) return;

    if (action == "show") {
      if (item.lastState == "visible") return;
      item.lastState = "entering";
      this.callbacks.show(item.element).then(
        () => {
          if (item.state == "entering") {
            item.state = "visible";
            item.lastState = "visible";
          }
        },
        () => {}
      );
    } else if (action == "hide") {
      if (item.lastState == "exiting" || item.lastState == "waiting") return;
      item.lastState = "exiting";
      this.callbacks.hide(item.element).then(
        () => {
          // Resolve if it's still gone, otherwise reject
          let item = this.pool[id];
          if (!!item && item.lastState == "exiting") {
            this.callbacks.destroy(item.element);
            delete this.pool[id];
          }
        },
        () => {}
      );
    }
  };

  this.flush = function () {
    this._flushTimer = null;
    Object.keys(this.queuedAnimations).forEach((id) => {
      this._perform(id, this.queuedAnimations[id]);
    });
    this.queuedAnimations = {};
  };

  this._enqueue = function (id, action) {
    let item = this.pool[id];
    if (!item.element) return false;
    if (action == "show") {
      if (item.state == "entering" || item.state == "visible") return false;
      item.state = "entering";
    } else if (action == "hide") {
      if (item.state == "exiting") return false;
      item.state = "exiting";
    } else {
      console.error("Unknown action enqueued:", action);
    }

    if (this.defer) {
      this.queuedAnimations[id] = action;
      if (!this._flushTimer) {
        this._flushTimer = setTimeout(() => this.flush(), 0);
      }
    } else {
      this._perform(id, action);
    }
    return true;
  };

  this.show = function (id, infoCB) {
    if (!this.pool[id]) {
      let info = infoCB != null ? infoCB(id) : null;
      this.pool[id] = {
        element: this.callbacks.create(id, info),
        info,
        state: "waiting",
        lastState: "waiting",
      };
    }

    return this._enqueue(id, "show");
  };

  this.getInfo = function (id) {
    if (!this.pool[id]) return null;
    return this.pool[id].info;
  };

  this.getElement = function (id) {
    if (!this.pool[id]) return null;
    return this.pool[id].element;
  };

  this.getAll = function () {
    let result = {};
    Object.assign(result, this.pool);
    return result;
  };

  this.getAllVisible = function () {
    let result = {};
    Object.keys(this.pool).forEach((key) => {
      if (
        (this.pool[key].state == "visible" ||
          this.pool[key].state == "entering") &&
        !!this.pool[key].element
      )
        result[key] = this.pool[key];
    });
    return result;
  };

  this.hide = function (id) {
    if (!this.pool[id]) {
      return;
    }
    return this._enqueue(id, "hide");
  };
}
