import * as PIXI from 'pixi.js';
import { Circle } from 'pixi.js';

const v = 80.0;

export default class PixiRadiusSelect extends PIXI.Graphics {
  centerID;
  centerX;
  centerY;
  radius;
  fillColor;
  timeCounter;

  constructor(centerID, centerX, centerY, radius, fillColor) {
    super();
    this.centerID = centerID;
    this.centerX = centerX;
    this.centerY = centerY;
    this.radius = radius;
    this.fillColor = fillColor;
    this.circle = new Circle(centerX, centerY, radius);
    this.timeCounter = 0;
  }

  _drawShape(dashed) {
    // Draw the path in reverse so the line dash moves
    let points = [];
    let numDashes = Math.round((2.0 * this.radius * Math.PI) / 2.0);
    for (let i = 0; i < numDashes; i++) {
      let theta =
        ((2 * Math.PI) / numDashes) * i +
        this.timeCounter * (v / (this.radius * numDashes));
      points.push([
        this.centerX + this.radius * Math.cos(theta),
        this.centerY + this.radius * Math.sin(theta),
      ]);
    }
    let dashPattern = [2, 2]; // cumulative
    let currentDashPosition = 0;
    let currentDashIndex = 0;
    let dashOn = true;

    this.moveTo(points[points.length - 1][0], points[points.length - 1][1]);
    points
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

  update(centerX, centerY) {
    this.timeCounter += 1;
    // 0x30cdfc
    this.centerX = centerX;
    this.centerY = centerY;
    this.circle = new Circle(this.centerX, this.centerY, this.radius);

    this.clear();
    this.lineStyle(2, this.fillColor, 0.6);
    this._drawShape(true);
    this.lineStyle(0, this.fillColor, 0.0);
    this.beginFill(this.fillColor, 0.25);
    this._drawShape(false);
    this.endFill();
  }
}
