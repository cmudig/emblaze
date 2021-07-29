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
    console.error('Missing required callbacks for AnimationPool');

  this.pool = new Map();

  // Contains directives per pool ID that are cleared at every run loop.
  this.queuedAnimations = new Map();
  this._flushTimer = null;

  this._perform = function (id, action) {
    let item = this.pool.get(id);
    if (!item || !item.element) return;

    if (action == 'show') {
      if (item.lastState == 'visible') return;
      item.lastState = 'entering';
      this.callbacks.show(item.element).then(
        () => {
          if (item.state == 'entering') {
            item.state = 'visible';
            item.lastState = 'visible';
          }
        },
        () => {}
      );
    } else if (action == 'hide') {
      if (item.lastState == 'exiting' || item.lastState == 'waiting') return;
      item.lastState = 'exiting';
      this.callbacks.hide(item.element).then(
        () => {
          // Resolve if it's still gone, otherwise reject
          let item = this.pool.get(id);
          if (!!item && item.lastState == 'exiting') {
            this.callbacks.destroy(item.element);
            this.pool.delete(id);
          }
        },
        () => {}
      );
    }
  };

  this.flush = function () {
    this._flushTimer = null;
    this.queuedAnimations.forEach((action, id) => {
      this._perform(id, action);
    });
    this.queuedAnimations.clear();
  };

  this._enqueue = function (id, action) {
    let item = this.pool.get(id);
    if (!item.element) return false;
    if (action == 'show') {
      if (item.state == 'entering' || item.state == 'visible') return false;
      item.state = 'entering';
    } else if (action == 'hide') {
      if (item.state == 'exiting') return false;
      item.state = 'exiting';
    } else {
      console.error('Unknown action enqueued:', action);
    }

    if (this.defer) {
      this.queuedAnimations.set(id, action);
      if (!this._flushTimer) {
        this._flushTimer = setTimeout(() => this.flush(), 0);
      }
    } else {
      this._perform(id, action);
    }
    return true;
  };

  this.show = function (id, infoCB) {
    if (!this.pool.has(id)) {
      let info = infoCB != null ? infoCB(id) : null;
      this.pool.set(id, {
        element: this.callbacks.create(id, info),
        info,
        state: 'waiting',
        lastState: 'waiting',
      });
    }

    return this._enqueue(id, 'show');
  };

  this.getInfo = function (id) {
    if (!this.pool.has(id)) return null;
    return this.pool.get(id).info;
  };

  this.getElement = function (id) {
    if (!this.pool.has(id)) return null;
    return this.pool.get(id).element;
  };

  this.getAll = function () {
    return new Map(this.pool);
  };

  this.getAllIDs = function () {
    return Array.from(this.pool.keys());
  };

  this.getAllVisible = function () {
    let result = new Map();
    for (let [key, value] of this.pool) {
      if (
        (value.state == 'visible' || value.state == 'entering') &&
        !!value.element
      )
        result.set(key, value);
    }
    return result;
  };

  this.getAllVisibleIDs = function () {
    return Array.from(this.pool.keys()).filter(
      (key) =>
        (this.pool.get(key).state == 'visible' ||
          this.pool.get(key).state == 'entering') &&
        !!this.pool.get(key).element
    );
  };

  this.hide = function (id) {
    if (!this.pool.has(id)) {
      return;
    }
    return this._enqueue(id, 'hide');
  };
}
