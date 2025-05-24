import * as PIXI from 'pixi.js';
import { normalizeVector } from '../utils/helpers';

export class PixiLineDecoration extends PIXI.Graphics {
  decoration = null;
  lastColor = null;
  colorHex = null;

  constructor(dec) {
    super();
    this.decoration = dec;
  }

  update() {
    let x = this.decoration.attr('x');
    let y = this.decoration.attr('y');
    let alpha = this.decoration.attr('alpha');
    let zIndex = this.decoration.attr('zIndex');

    let x2 = this.decoration.attr('x2');
    let y2 = this.decoration.attr('y2');

    let color = this.decoration.attr('color');
    if (this.lastColor != color) {
      this.lastColor = color;
      this.colorHex = PIXI.utils.string2hex(color);
    }
    if (zIndex != this.zIndex) {
      this.zIndex = zIndex;
    }

    this.clear();
    this.lineStyle(this.decoration.attr('lineWidth'), this.colorHex, alpha);
    this.moveTo(x, y);
    this.lineTo(x2, y2);
  }
}

export class PixiOutlineDecoration extends PIXI.Graphics {
  decoration = null;
  lastColor = null;
  colorHex = null;
  rFactor = 1.0;

  constructor(dec) {
    super();
    this.decoration = dec;
  }

  update(currentTime) {
    let x = this.decoration.attr('x');
    let y = this.decoration.attr('y');
    let alpha = this.decoration.attr('alpha');
    let zIndex = this.decoration.attr('zIndex');

    let pulseDuration = this.decoration.attr('pulseDuration');
    if (!!pulseDuration) {
      alpha *=
        0.5 *
        (1 + Math.sin((currentTime / (pulseDuration * 1000)) * 2 * Math.PI));
    }

    let color = this.decoration.attr('color');
    if (this.lastColor != color) {
      this.lastColor = color;
      this.colorHex = PIXI.utils.string2hex(color);
    }
    if (zIndex != this.zIndex) this.zIndex = zIndex;

    this.clear();
    this.lineStyle(this.decoration.attr('lineWidth'), this.colorHex, alpha);
    this.drawCircle(x, y, this.decoration.attr('r') * this.rFactor);
  }
}

// A simple widening line decoration. TODO convert this to a single Mesh once
// we know what the exact preview mechanism will be
export class PixiWideningLineDecoration extends PIXI.Graphics {
  decoration = null;
  lastColor = null;
  colorHex = null;

  constructor(dec) {
    super();
    this.decoration = dec;
  }

  update() {
    let x = this.decoration.attr('x');
    let y = this.decoration.attr('y');
    let alpha = this.decoration.attr('alpha');
    let zIndex = this.decoration.attr('zIndex');

    let x2 = this.decoration.attr('x2');
    let y2 = this.decoration.attr('y2');

    let color = this.decoration.attr('color');
    // Assume [r, g, b] from 0 to 1
    let colorHex =
      Math.round(color[0] * 255) * 256 * 256 +
      Math.round(color[1] * 255) * 256 +
      Math.round(color[2] * 255);
    if (zIndex != this.zIndex) {
      this.zIndex = zIndex;
    }

    this.clear();
    this.beginFill(colorHex, alpha);
    let start = [x, y];
    let end = [x2, y2];
    let startWidth = 1;
    let endWidth = this.decoration.attr('lineWidth');
    let path = [end[0] - start[0], end[1] - start[1]];
    let normal;
    if (path[1] > 0.0) normal = normalizeVector([path[1], -path[0]]);
    else normal = normalizeVector([-path[1], path[0]]);
    this.moveTo(
      start[0] - (normal[0] * startWidth) / 2,
      start[1] - (normal[1] * startWidth) / 2
    );
    this.lineTo(
      start[0] + (normal[0] * startWidth) / 2,
      start[1] + (normal[1] * startWidth) / 2
    );
    this.lineTo(
      end[0] + (normal[0] * endWidth) / 2,
      end[1] + (normal[1] * endWidth) / 2
    );
    this.lineTo(
      end[0] - (normal[0] * endWidth) / 2,
      end[1] - (normal[1] * endWidth) / 2
    );
    this.endFill();
  }
}
