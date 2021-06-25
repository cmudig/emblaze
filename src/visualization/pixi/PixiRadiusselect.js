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

  
  update(centerX, centerY) {
    // 0x30cdfc
    this.centerX = centerX;
    this.centerY = centerY;
    this.circle = new Circle(this.centerX, this.centerY, this.radius);
    this.clear();
    this.beginFill(this.fillColor, 0.5);
    this.lineStyle(2, this.fillColor);
    this.arc(0, 0, this.radius, 0, 2 * Math.PI);
    this.position = {x: this.centerX, y: this.centerY};
    // this.radiusselectContainer.addChild(circle);
    this.endFill();
  }
}
