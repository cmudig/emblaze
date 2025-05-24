import {
  Attribute,
  Animator,
  easeInOut,
  interpolateTo,
  interpolateToFunction,
} from './data_items';
import { boundingBox, padExtent } from '../utils/helpers';

const ZoomAnimationDuration = 1000; // milliseconds
const ZoomBoxPadding = 50; // pixels

// This type handles x and y axis scales with zooming and panning.
export function Scales(
  xDomain,
  yDomain,
  xRange,
  yRange,
  padding = 0.5,
  aspect = true
) {
  if (aspect) {
    // Rescale one to the other based on whichever has the smallest scale factor
    let xScale = (xRange[1] - xRange[0]) / (xDomain[1] - xDomain[0]);
    let yScale = (yRange[1] - yRange[0]) / (yDomain[1] - yDomain[0]);
    if (xScale < yScale) {
      let yMid = (yDomain[0] + yDomain[1]) * 0.5;
      let newWidth = (yRange[1] - yRange[0]) / xScale;
      yDomain = [yMid - newWidth * 0.5, yMid + newWidth * 0.5];
    } else {
      let xMid = (xDomain[0] + xDomain[1]) * 0.5;
      let newWidth = (xRange[1] - xRange[0]) / yScale;
      xDomain = [xMid - newWidth * 0.5, xMid + newWidth * 0.5];
    }
  }
  this.xDomain = padExtent(xDomain, padding);
  this.yDomain = padExtent(yDomain, padding);
  this.xDExtent = this.xDomain[1] - this.xDomain[0];
  this.yDExtent = this.yDomain[1] - this.yDomain[0];

  this.xRange = xRange;
  this.yRange = yRange;
  this.xRExtent = xRange[1] - xRange[0];
  this.yRExtent = yRange[1] - yRange[0];
  this.scaleFactor = new Attribute(1.0);
  this.translateX = new Attribute(0.0);
  this.translateY = new Attribute(0.0);
  this.translateX.label = 'scaleFactor';

  this.minScale = 0.1;
  this.maxScale = 14.0;

  this._updatedNoAdvance = false;
  this.listeners = [];

  this.onUpdate = function (fn) {
    this.listeners.push(fn);
  };

  this.isNeutral = function () {
    return (
      Math.abs(this.scaleFactor.get() - 1.0) <= 0.01 &&
      Math.abs(this.translateX.get()) <= 5.0 &&
      Math.abs(this.translateY.get()) <= 5.0
    );
  };

  this.advance = function (dt) {
    let a = this.scaleFactor.advance(dt);
    let b = this.translateX.advance(dt);
    let c = this.translateY.advance(dt);
    if (a || b || c) {
      this._updatedNoAdvance = false;
      this.listeners.forEach((fn) => fn(this));
      return true;
    }
    if (!this._updatedNoAdvance) {
      this.listeners.forEach((fn) => fn(this));
      this._updatedNoAdvance = true;
    }
    return false;
  };

  this.scaleX = function (dataX) {
    let base =
      ((dataX - this.xDomain[0]) * this.xRExtent) / this.xDExtent +
      this.xRange[0];
    return base * this.scaleFactor.get() - this.translateX.get();
  };

  this.scaleY = function (dataY) {
    let base =
      ((dataY - this.yDomain[0]) * this.yRExtent) / this.yDExtent +
      this.yRange[0];
    return base * this.scaleFactor.get() - this.translateY.get();
  };

  // Returns values that can be used to transform raw x, y coordinates into
  // screen-space. Specifically, the screen-space coordinates can be calculated
  // as follows:
  // x_screen = x_data * info.x.a + info.x.b
  // y_screen = y_data * info.y.a + info.y.b
  this.getTransformInfo = function () {
    let baseScaleX = this.xRExtent / this.xDExtent;
    let baseScaleY = this.yRExtent / this.yDExtent;
    let scale = this.scaleFactor.get();
    return {
      x: {
        a: baseScaleX * scale,
        b:
          scale * (this.xRange[0] - baseScaleX * this.xDomain[0]) -
          this.translateX.get(),
      },
      y: {
        a: baseScaleY * scale,
        b:
          scale * (this.yRange[0] - baseScaleY * this.yDomain[0]) -
          this.translateY.get(),
      },
    };
  };

  // Returns a factor k such that <screen distance> = <data distance> * k when
  // the scales' scaleFactor is 1
  this.getDataToUniformScaleFactor = function () {
    return Math.min(
      this.xRExtent / this.xDExtent,
      this.yRExtent / this.yDExtent
    );
  };

  // Returns the scale factor that would be needed to make two points at the
  // given data distance be pixelDistance apart
  this.scaleFactorForDistance = function (dataDistance, pixelDistance) {
    let baseScaleX = this.xRExtent / this.xDExtent;
    let baseScaleY = this.yRExtent / this.yDExtent;
    return pixelDistance / (Math.min(baseScaleX, baseScaleY) * dataDistance);
  };

  // These parameters tell the scales how to transform the coordinates after
  // they have been converted into pixel space.
  this.transform = function (scaleInfo, animated = false) {
    this.unfollow();

    if (animated) {
      if (scaleInfo.hasOwnProperty('scale'))
        this.scaleFactor.animate(
          new Animator(
            interpolateTo(scaleInfo.scale),
            ZoomAnimationDuration,
            easeInOut
          )
        );
      if (scaleInfo.hasOwnProperty('translateX'))
        this.translateX.animate(
          new Animator(
            interpolateTo(scaleInfo.translateX),
            ZoomAnimationDuration,
            easeInOut
          )
        );
      if (scaleInfo.hasOwnProperty('translateY'))
        this.translateY.animate(
          new Animator(
            interpolateTo(scaleInfo.translateY),
            ZoomAnimationDuration,
            easeInOut
          )
        );
    } else {
      if (scaleInfo.hasOwnProperty('scale'))
        this.scaleFactor.set(scaleInfo.scale);
      if (scaleInfo.hasOwnProperty('translateX'))
        this.translateX.set(scaleInfo.translateX);
      if (scaleInfo.hasOwnProperty('translateY'))
        this.translateY.set(scaleInfo.translateY);
    }
  };

  // Increases the scale by the given amount, optionally centering by the given
  // point in transformed pixel space
  this.scaleBy = function (ds, centerPoint = null) {
    this.unfollow();

    let tx = this.translateX.get();
    let ty = this.translateY.get();
    let s = this.scaleFactor.get();

    if (!centerPoint) {
      centerPoint = [
        (this.xRange[0] + this.xRange[1]) * 0.5,
        (this.yRange[0] + this.yRange[1]) * 0.5,
      ];
    } else {
      centerPoint = [(centerPoint[0] + tx) / s, (centerPoint[1] + ty) / s];
    }

    var newScaleFactor = s + ds;
    if (newScaleFactor > this.maxScale || newScaleFactor < this.minScale)
      return;

    this.scaleFactor.set(newScaleFactor);
    this.translateX.set(tx + ds * centerPoint[0]);
    this.translateY.set(ty + ds * centerPoint[1]);
  };

  // Translates the scales by the given amount
  this.translateBy = function (dx, dy) {
    this.unfollow();
    this.translateX.set(this.translateX.get() + dx);
    this.translateY.set(this.translateY.get() + dy);
  };

  this._computeZoomBox = function (
    points,
    fixedCenter = null,
    fixedScale = null
  ) {
    let newCenterX, newCenterY, newScale;
    if (!!fixedScale) {
      newScale = fixedScale;
      if (!!fixedCenter) {
        newCenterX = fixedCenter.x;
        newCenterY = fixedCenter.y;
      } else {
        let { x: xExtent, y: yExtent } = boundingBox(points);
        newCenterX = (xExtent[0] + xExtent[1]) * 0.5;
        newCenterY = (yExtent[0] + yExtent[1]) * 0.5;
      }
    } else {
      let { x: xExtent, y: yExtent } = boundingBox(points);
      if (!!fixedCenter) {
        // Adjust the extents so that the center point is centered
        let xDist = Math.max(
          xExtent[1] - fixedCenter.x,
          fixedCenter.x - xExtent[0]
        );
        let yDist = Math.max(
          yExtent[1] - fixedCenter.y,
          fixedCenter.y - yExtent[0]
        );
        xExtent = [fixedCenter.x - xDist, fixedCenter.x + xDist];
        yExtent = [fixedCenter.y - yDist, fixedCenter.y + yDist];
      }

      let xScale =
        this.xRExtent /
        (xExtent[1] - xExtent[0]) /
        (this.xRExtent / this.xDExtent);
      let yScale =
        this.yRExtent /
        (yExtent[1] - yExtent[0]) /
        (this.yRExtent / this.yDExtent);

      // pad by roughly ZoomBoxPadding (this isn't exact)
      xExtent = padExtent(
        xExtent,
        ZoomBoxPadding / ((this.xRExtent / this.xDExtent) * xScale)
      );
      yExtent = padExtent(
        yExtent,
        ZoomBoxPadding / ((this.yRExtent / this.yDExtent) * yScale)
      );

      xScale =
        this.xRExtent /
        (xExtent[1] - xExtent[0]) /
        (this.xRExtent / this.xDExtent);
      yScale =
        this.yRExtent /
        (yExtent[1] - yExtent[0]) /
        (this.yRExtent / this.yDExtent);

      newScale = Math.min(Math.min(xScale, yScale), this.maxScale);
      newCenterX = (xExtent[0] + xExtent[1]) * 0.5;
      newCenterY = (yExtent[0] + yExtent[1]) * 0.5;
    }

    newCenterX =
      ((newCenterX - this.xDomain[0]) * this.xRExtent) / this.xDExtent +
      this.xRange[0];
    newCenterY =
      ((newCenterY - this.yDomain[0]) * this.yRExtent) / this.yDExtent +
      this.yRange[0];

    let newTranslateX =
      newCenterX * newScale - (this.xRange[0] + this.xRange[1]) * 0.5;
    let newTranslateY =
      newCenterY * newScale - (this.yRange[0] + this.yRange[1]) * 0.5;

    return {
      scale: newScale,
      translateX: newTranslateX,
      translateY: newTranslateY,
    };
  };

  // Animates the scale and translate factors to show the given points.
  // points should be an array of objects with x and y properties.
  this.zoomTo = function (marks, animated = true, xAttr = 'x', yAttr = 'y') {
    let points = marks.map((mark) => ({
      x: mark.attr(xAttr, false),
      y: mark.attr(yAttr, false),
    }));
    this.transform(this._computeZoomBox(points), animated);
  };

  this.followingMarks = [];
  this.centerMark = null;
  this._markBoxCache = null;
  this._markPointFn = null;
  this._fixedScale = null;

  this._computeMarkBox = function () {
    if (!!this._markBoxCache) {
      // Check the cache to see if the points are the same
      if (this._markBoxCache.time == this.scaleFactor.currentTime) {
        //console.log("Cached", this._markBoxCache.value);
        return this._markBoxCache.value;
      }
    }

    let value = this._computeZoomBox(
      this._markPointFn(this.followingMarks),
      !!this.centerMark ? this._markPointFn([this.centerMark])[0] : null,
      this._fixedScale
    );
    this._markBoxCache = {
      time: this.scaleFactor.currentTime,
      value,
    };
    //console.log(value.scale);

    return value;
  };

  // Sets the scales to follow the locations of the given marks
  this.follow = function (marks, animated = true, xAttr = 'x', yAttr = 'y') {
    this.followingMarks = marks;
    this.centerMark = null;
    this._markPointFn = (m) =>
      m.map((mark) => ({
        x: mark.attr(xAttr, false),
        y: mark.attr(yAttr, false),
      }));
    this._markBoxCache = null;

    this.scaleFactor.set(() => this._computeMarkBox().scale);
    this.translateX.set(() => this._computeMarkBox().translateX);
    this.translateY.set(() => this._computeMarkBox().translateY);
    if (animated) {
      this.scaleFactor.animate(
        new Animator(
          interpolateTo(this.scaleFactor.data()),
          ZoomAnimationDuration,
          easeInOut
        )
      );
      this.translateX.animate(
        new Animator(
          interpolateTo(this.translateX.data()),
          ZoomAnimationDuration,
          easeInOut
        )
      );
      this.translateY.animate(
        new Animator(
          interpolateTo(this.translateY.data()),
          ZoomAnimationDuration,
          easeInOut
        )
      );
    }
  };

  // Centers the viewport on the given mark, while keeping the other given marks in frame
  this.centerOn = function (
    mark,
    peripheralMarks,
    animated = true,
    xAttr = 'x',
    yAttr = 'y'
  ) {
    this.followingMarks = [mark, ...peripheralMarks];
    this.centerMark = mark;
    this._markPointFn = (m) =>
      m.map((mark) => ({
        x: mark.attr(xAttr, false),
        y: mark.attr(yAttr, false),
      }));
    this._markBoxCache = null;

    this._fixedScale = null;
    this.scaleFactor.set(() => this._computeMarkBox().scale);
    this.translateX.set(() => this._computeMarkBox().translateX);
    this.translateY.set(() => this._computeMarkBox().translateY);
    this._fixedScale = this.scaleFactor.data();
    if (animated) {
      this.scaleFactor.animate(
        new Animator(
          interpolateToFunction(() => this.scaleFactor.data()),
          ZoomAnimationDuration,
          easeInOut
        )
      );
      this.translateX.animate(
        new Animator(
          interpolateToFunction(() => this.translateX.data()),
          ZoomAnimationDuration,
          easeInOut
        )
      );
      this.translateY.animate(
        new Animator(
          interpolateToFunction(() => this.translateY.data()),
          ZoomAnimationDuration,
          easeInOut
        )
      );
    }
  };

  this.unfollow = function () {
    if (this.followingMarks.length > 0) {
      this.scaleFactor.set(this.scaleFactor.get());
      this.translateX.set(this.translateX.get());
      this.translateY.set(this.translateY.get());
      this.followingMarks = [];
      this.centerMark = null;
      this._markPointFn = null;
      this._markBoxCache = null;
    }
  };

  this.resetZoom = function (animated = true) {
    this.unfollow();
    this.transform({ scale: 1, translateX: 0, translateY: 0 }, animated);
  };
}
