import * as PIXI from "pixi.js";
import { Circle } from "pixi.js";

export default class PixiRadiusSelect extends PIXI.Graphics {
  centerID;
  centerX;
  centerY;
  radius;
  fillColor;

  constructor(centerID, centerX, centerY, radius, fillColor) {
    super();
    this.centerID = centerID;
    this.centerX = centerX;
    this.centerY = centerY;
    this.radius = radius;
    this.fillColor = fillColor;
    this.circle = new Circle(centerX, centerY, radius);
  }

  _drawShape(dashed) {
    // Draw the path in reverse so the line dash moves
    let points = [];
    let v = 100000.0;
    for (let i = 0; i < 60; i++) {
        let theta = ((2 * Math.PI) / 60.0) * i + v / (this.radius * 60.0);
        points.push([this.centerX + this.radius * Math.cos(theta), 
                     this.centerY + this.radius * Math.sin(theta)]);
    }
    let dashPattern = [2, 4]; // cumulative
    let currentDashPosition = 0;
    let currentDashIndex = 0;
    let dashOn = true;

    this.moveTo(
        points[points.length - 1][0],
        points[points.length - 1][1]
      );
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
    // 0x30cdfc
    this.centerX = centerX;
    this.centerY = centerY;
    this.circle = new Circle(this.centerX, this.centerY, this.radius);
    // this.clear();
    // this.beginFill(this.fillColor, 0.5);
    // this.lineStyle(2, this.fillColor);
    // for (let i = 0; i < 50; i += 2) {
    //     this.arc(0, 0, this.radius, ((2 * Math.PI) / 50.0) * i, ((2 * Math.PI) / 50.0) * (i + 1));
    // }
    // //this.arc(0, 0, this.radius, 0, 2 * Math.PI);
    // this.position = {x: this.centerX, y: this.centerY};
    // // this.radiusselectContainer.addChild(circle);
    // this.endFill();
    this.clear();
    // if (this.strokeColor != null) {
    //   this.lineStyle(2, this.strokeColor, 0.6);
    //   this._drawShape(true);
    // }
    this.lineStyle(2, this.fillColor, 0.6);
    this._drawShape(true);
    this.lineStyle(0, this.fillColor, 0.0);
    this.beginFill(this.fillColor, 0.25);
    this._drawShape(false);
    this.endFill();
  }
}
