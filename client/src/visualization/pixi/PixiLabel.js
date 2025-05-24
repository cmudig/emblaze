import * as PIXI from "pixi.js";
import { ColorIDMap, ValueHistory } from "../utils/helpers";
import PixiColorIDMap from "./PixiColorIDMap";

const BaseFontSize = 10;

export class PixiTextLabel extends PIXI.Text {
  decoration;
  rFactor = 1;
  renderBox = null;
  zIndexBase = 0;
  occluded = false;

  history = new ValueHistory();
  changed = false;

  constructor(decoration, rFactor = 1, zIndexBase = 0) {
    super(decoration.attr("text") || "", {
      fontFamily: "Arial",
      fontSize: BaseFontSize,
      stroke: "white",
      strokeThickness: 3.0,
    });
    this.resolution = window.devicePixelRatio;
    this.decoration = decoration;
    this.rFactor = rFactor;
    this.zIndexBase = zIndexBase;
    this.anchor.set(0.5, 1.0);
  }

  getBoundingBox() {
    let priority = this.decoration.attr("priority");
    let text = this.decoration.attr("text");
    if (priority == null || text == null || text.length == 0) {
      return null;
    }

    let x = this.decoration.attr("x");
    let y = this.decoration.attr("y");
    let r = this.decoration.marks[0].attr("r") * this.rFactor;
    let bottom = y - r - 2;
    return [
      Math.round(x - this.width / 2),
      Math.round(bottom - this.height),
      Math.round(this.width),
      Math.round(this.height),
    ];
  }

  update() {
    let priority = this.decoration.attr("priority");
    let text = this.decoration.attr("text");
    if (priority == null || text == null || text.length == 0 || this.occluded) {
      this.visible = false;
      this.changed = this.history.update({ priority, text, x: null, y: null });
      return;
    }

    let x = this.decoration.attr("x");
    let y = this.decoration.attr("y");
    this.changed = this.history.update({ priority, text, x, y });
    if (
      !!this.renderBox &&
      (x < this.renderBox[0] ||
        x > this.renderBox[1] ||
        y < this.renderBox[2] ||
        y > this.renderBox[3])
    ) {
      this.visible = false;
      return;
    }
    this.visible = true;

    this.visible = true;
    if (priority + this.zIndexBase != this.zIndex) {
      this.zIndex = priority + this.zIndexBase;
    }

    let r = this.decoration.marks[0].attr("r") * this.rFactor;
    this.position.set(x, y - r - 2);
    this.text = text;
    this.style.fill = this.decoration.attr("color") || "black";
    this.style.fontSize =
      BaseFontSize * (this.decoration.attr("textScale") || 1.0);
    this.alpha = this.decoration.attr("alpha") || 1.0;
    this.scale.set(this.decoration.attr("scale") || 1.0);
  }
}

export class PixiImageLabel extends PIXI.Sprite {
  decoration;
  renderBox = null;
  rFactor = 1;
  zIndexBase = 0;
  outline = null;
  lastColor = null;
  colorHex = null;
  scaleFactor = 0.0;
  occluded = false;

  history = new ValueHistory();
  changed = false;

  constructor(decoration, texture, rFactor = 1, zIndexBase = 0) {
    super(texture);
    this.decoration = decoration;
    this.rFactor = rFactor;
    this.zIndexBase = zIndexBase;
    this.anchor.set(0.5, 1.0);

    let maxDim = this.decoration.attr("maxDim");
    if (
      !!maxDim &&
      (this.width > maxDim + 0.001 || this.height > maxDim + 0.001)
    ) {
      this.scaleFactor = Math.min(maxDim / this.width, maxDim / this.height);
      this.width *= this.scaleFactor;
      this.height *= this.scaleFactor;
    } else {
      this.scaleFactor = 1.0;
    }

    this.outline = new PIXI.Graphics();
    this.addChild(this.outline);
  }

  getBoundingBox() {
    let priority = this.decoration.attr("priority");
    if (priority == null) {
      return null;
    }

    let x = this.decoration.attr("x");
    let y = this.decoration.attr("y");
    let r = this.decoration.marks[0].attr("r") * this.rFactor;
    let bottom = y - r - 4;
    return [
      Math.round(x - this.width / 2),
      Math.round(bottom - this.height),
      Math.round(this.width),
      Math.round(this.height),
    ];
  }

  update() {
    let priority = this.decoration.attr("priority");
    if (priority == null || this.occluded) {
      this.visible = false;
      this.changed = this.history.update({ priority });
      return;
    }

    let x = this.decoration.attr("x");
    let y = this.decoration.attr("y");
    if (
      !!this.renderBox &&
      (x < this.renderBox[0] ||
        x > this.renderBox[1] ||
        y < this.renderBox[2] ||
        y > this.renderBox[3])
    ) {
      this.visible = false;
      this.changed = this.history.update({ priority, x, y });
      return;
    }
    this.visible = true;

    if (priority + this.zIndexBase != this.zIndex) {
      this.zIndex = priority + this.zIndexBase;
    }

    let r = this.decoration.marks[0].attr("r") * this.rFactor;
    this.position.set(x, y - r - 4);
    this.alpha = this.decoration.attr("alpha") || 1.0;

    let color = this.decoration.attr("color") || "#FFFFFF";
    this.changed = this.history.update({ priority, x, y, color });
    if (this.lastColor != color) {
      this.lastColor = color;
      this.colorHex = PIXI.utils.string2hex(color);

      this.outline.clear();
      this.outline.lineStyle(2, this.colorHex, 1.0);
      this.outline.drawRect(
        -this.width / 2.0 / this.scaleFactor,
        -this.height / this.scaleFactor,
        this.width / this.scaleFactor,
        this.height / this.scaleFactor
      );
    }
  }
}

const BBOX_PADDING = 2;
const DEBUG_BBOXES = false;

/**
 * Manages a set of label decorations. This class handles making sure the labels
 * don't overlap by setting the occluded property on the labels (which must be
 * either PixiTextLabel or PixiImageLabel instances).
 */
export class PixiLabelContainer extends PIXI.Container {
  labels = [];
  bboxes = [];
  frame;
  renderer;
  blockContainer = new PIXI.Container();
  colorIDs = null;
  colorIDMap = null;

  labelListChanged = false;

  constructor(renderer, frame) {
    super();
    this.renderer = renderer;
    this.frame = frame;
    if (DEBUG_BBOXES) this.addChild(this.blockContainer);
  }

  _corners(bbox) {
    return [
      [bbox[0] + BBOX_PADDING, bbox[1] + BBOX_PADDING],
      [bbox[0] + bbox[2] - BBOX_PADDING, bbox[1] + BBOX_PADDING],
      [bbox[0] + BBOX_PADDING, bbox[1] + bbox[3] - BBOX_PADDING],
      [bbox[0] + bbox[2] - BBOX_PADDING, bbox[1] + bbox[3] - BBOX_PADDING],
    ];
  }

  update() {
    // Redrawing and computing bounding boxes is a relatively expensive
    // operation. Therefore, we only want to do it when we have at least two
    // boxes, and one of the boxes has changed since the last computation.
    if (this.labels.length == 0) {
      return;
    } else if (this.labels.length == 1) {
      this.labels[0].occluded = false;
      return;
    }

    let anyChanged = false;
    for (var l of this.labels) {
      if (l.changed) {
        anyChanged = true;
        break;
      }
    }
    if (!anyChanged && !this.labelListChanged) {
      return;
    }
    this.labelListChanged = false;

    this.blockContainer.sortableChildren = true;
    if (!this.colorIDs) this.colorIDs = new ColorIDMap("hex");
    this.labels.forEach((label, i) => {
      let priority = label.decoration.attr("priority");
      if (priority == null) return;

      let bbox = label.getBoundingBox();
      let graphics = this.bboxes[i];
      graphics.clear();
      graphics.zIndex = priority;
      let color = this.colorIDs.id(i);
      graphics.beginFill(color);
      graphics.drawRect(
        bbox[0] - BBOX_PADDING,
        bbox[1] - BBOX_PADDING,
        bbox[2] + BBOX_PADDING * 2,
        bbox[3] + BBOX_PADDING * 2
      );
      graphics.endFill();
    });
    this.blockContainer.sortChildren();

    // Render a snapshot of the bounding box collection so we can read pixels
    if (!this.colorIDMap) {
      this.colorIDMap = new PixiColorIDMap(
        this.renderer,
        this.blockContainer,
        this.frame,
        this.colorIDs,
        true
      );
    } else {
      this.colorIDMap.render(this.blockContainer);
    }
    this.labels.forEach((label, i) => {
      let bbox = label.getBoundingBox();
      if (bbox == null) return;

      label.occluded = false;
      for (let corner of this._corners(bbox)) {
        let obj = this.colorIDMap.obj(corner[0], corner[1]);
        // if (label.decoration.attr("priority") > 100)
        //   console.log(
        //     label.decoration.marks[0].id,
        //     label.decoration.attr("priority"),
        //     corner[0],
        //     corner[1],
        //     obj,
        //     i,
        //     this.colorIDMap.colorAt(corner[0], corner[1]),
        //     this.colorIDMap.colorIDs.reverseMapping
        //   );
        if (obj != null && obj != i) {
          label.occluded = true;
          break;
        }
      }
    });
  }

  addLabel(label) {
    this.labels.push(label);
    let bbox = new PIXI.Graphics();
    this.bboxes.push(bbox);
    this.addChild(label);
    this.blockContainer.addChild(bbox);
    this.labelListChanged = true;
  }

  removeLabel(label) {
    let idx = this.labels.indexOf(label);
    if (idx >= 0) {
      this.labels.splice(idx, 1);
      this.blockContainer.removeChild(this.bboxes[idx]);
      this.bboxes[idx].destroy();
      this.bboxes.splice(idx, 1);
    }
    this.removeChild(label);
    this.labelListChanged = true;
  }

  destroy() {
    super.destroy();
    if (!!this.colorIDMap) this.colorIDMap.destroy();
  }
}
