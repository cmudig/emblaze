/**
 * A helper class that manages retrieving elements by color ID from a framebuffer.
 * This is the color-picking trick (see http://www.opengl-tutorial.org/miscellaneous/clicking-on-objects/picking-with-an-opengl-hack/)
 */

import * as PIXI from "pixi.js";
import { ColorIDMap } from "../utils/helpers";

const ComponentsPerPixel = 4;

export default class PixiColorIDMap {
  fbo;
  frame;
  binaryColor = null;
  colorIDs = null;
  persistent = false;
  renderTexture;
  renderer;

  /**
   * Builds the texture and prepares for queries.
   *
   * @param {PIXI.Renderer} renderer the renderer to use
   * @param {PIXI.RenderObject} element a drawable element to render
   * @param {PIXI.Rectangle} frame the rectangle in which to draw the element
   * @param {ColorIDMap | Array} colorID either a ColorIDMap defining values, or
   *  a single RGB (0-255) color array for a binary classification
   */
  constructor(renderer, element, frame, colorID, persistent = false) {
    this.renderer = renderer;
    this.frame = frame;
    this.persistent = persistent;
    this.render(element);

    if (colorID instanceof Array) {
      this.binaryColor = colorID;
    } else {
      this.colorIDs = colorID;
    }
  }

  destroy() {
    if (this.persistent) {
      this.renderTexture.destroy(true);
      this.renderTexture = null;
    }
  }

  render(element) {
    if (!this.renderTexture) {
      this.renderTexture = this.renderer.generateTexture(
        element,
        PIXI.SCALE_MODES.NEAREST,
        1,
        this.frame
      );
    } else {
      this.renderer.render(element, this.renderTexture);
    }
    this.fbo = this.renderer.extract.pixels(this.renderTexture);
    if (!this.persistent) this.destroy();
  }

  colorAt(x, y) {
    x = Math.round(x);
    y = Math.round(y);
    if (x < 0 || x >= this.frame.width || y < 0 || y >= this.frame.height)
      return [0, 0, 0];
    let startIndex =
      y * this.frame.width * ComponentsPerPixel + x * ComponentsPerPixel;
    let rgb = this.fbo.slice(startIndex, startIndex + 3);
    return rgb;
  }

  // Only for binary classification maps - returns whether the region in the
  // map contains this point
  contains(x, y) {
    if (this.binaryColor == null) {
      console.warn("Attempting to use contains() on a non-binary color ID map");
      return false;
    }
    let color = this.colorAt(x, y);
    return (
      color[0] == this.binaryColor[0] &&
      color[1] == this.binaryColor[1] &&
      color[2] == this.binaryColor[2]
    );
  }

  // Only for non-binary classification maps - returns the object in the
  // ColorIDMap at the given point, or null
  obj(x, y) {
    if (this.colorIDs == null) {
      console.warn("Attempting to use obj() on a binary color ID map");
      return null;
    }
    let color;
    if (this.colorIDs.format == "hex") {
      let c = this.colorAt(x, y);
      color = (c[0] << 16) + (c[1] << 8) + c[2];
    } else color = "rgb(" + this.colorAt(x, y).join(",") + ")";
    return this.colorIDs.obj(color);
  }
}
