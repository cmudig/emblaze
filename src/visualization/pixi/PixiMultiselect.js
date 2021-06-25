import * as PIXI from "pixi.js";

export default class PixiMultiselect extends PIXI.Graphics {
  points = [];
  fillColor;
  strokeColor = null;
  hidden = false;

  constructor(fillColor, strokeColor = null) {
    super();
    this.fillColor = fillColor;
    this.strokeColor = strokeColor;
  }

  addPoint(x, y) {
    this.points.push([x, y]);
  }

  setPoints(points) {
    this.points = points;
  }

  _drawShape(dashed) {
    // Draw the path in reverse so the line dash moves
    let dashPattern = [2, 4]; // cumulative
    let currentDashPosition = 0;
    let currentDashIndex = 0;
    let dashOn = true;

    this.moveTo(
      this.points[this.points.length - 1][0],
      this.points[this.points.length - 1][1]
    );
    this.points
      .slice()
      .reverse()
      .forEach((point) => {
        if (dashed) {
          if (currentDashPosition == dashPattern[currentDashIndex]) {
            currentDashIndex = (currentDashIndex + 1) % dashPattern.length;
            dashOn = !dashOn;
          }
          currentDashPosition =
            (currentDashPosition + 1) %
            (dashPattern[dashPattern.length - 1] + 1);
        }

        if (dashOn) {
          this.lineTo(point[0], point[1]);
        } else {
          this.moveTo(point[0], point[1]);
        }
      });
  }

  update() {
    this.clear();
    if (this.strokeColor != null) {
      this.lineStyle(2, this.strokeColor, 0.6);
      this._drawShape(true);
    }
    this.lineStyle(0, this.strokeColor, 0.0);
    this.beginFill(this.fillColor, this.hidden ? 1.0 : 0.25);
    this._drawShape(false);
    this.endFill();
  }
}
