import * as PIXI from "pixi.js";
import * as d3 from "d3";

const textureRadius = 12;
const textureDim = Math.round(textureRadius / 0.5) * 2;

let pointTexture = {
  texture: null,
  make() {
    let dotCanvas = document.createElement("canvas");
    d3.select(dotCanvas)
      .attr("width", textureDim * window.devicePixelRatio)
      .attr("height", textureDim * window.devicePixelRatio)
      .style("width", textureDim + "px")
      .style("height", textureDim + "px");

    let ctx = dotCanvas.getContext("2d");
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
    ctx.strokeStyle = "white";
    ctx.lineWidth = Math.round(textureRadius * 0.4);
    ctx.beginPath();
    ctx.ellipse(
      textureDim / 2,
      textureDim / 2,
      textureRadius,
      textureRadius,
      0.0,
      0.0,
      2 * Math.PI
    );
    ctx.fill();
    ctx.stroke();

    return PIXI.Texture.from(dotCanvas, {
      resolution: window.devicePixelRatio,
    });
  },
  retainCount: 0,
};

function usePointTexture(tex) {
  if (!tex.texture) tex.texture = tex.make();
  tex.retainCount++;
  return tex.texture;
}

function unusePointTexture(tex) {
  tex.retainCount--;
  if (tex.retainCount <= 0 && !!tex.texture) {
    tex.texture.destroy();
    tex.texture = null;
  }
}

export default class PixiMarkPoint extends PIXI.Sprite {
  lastFillStyle = null;
  rFactor = 1.0;
  renderBox = null;

  constructor(mark, rFactor = 1.0, renderBox = null) {
    super(usePointTexture(pointTexture));

    this.anchor.set(0.5);
    this.interactive = true;
    this.mark = mark;
    this.rFactor = rFactor;
    this.renderBox = renderBox;
  }

  update() {
    let x = this.mark.attr("x");
    let y = this.mark.attr("y");
    let alpha = this.mark.attr("alpha");
    let zIndex = this.mark.attr("zIndex") || 0;

    if (
      (!!this.renderBox &&
        (x < this.renderBox[0] ||
          x > this.renderBox[1] ||
          y < this.renderBox[2] ||
          y > this.renderBox[3])) ||
      alpha < 0.001
    ) {
      this.visible = false;
      return;
    }
    this.visible = true;

    this.zIndex = zIndex;

    let fillStyle = this.mark.attr("fillStyle");
    if (this.lastFillStyle != fillStyle) {
      this.lastFillStyle = fillStyle;
      this.tint = PIXI.utils.string2hex(fillStyle);
    }

    this.position.set(x, y);

    let r = this.mark.attr("r") * this.rFactor;

    this.scale.set(r / textureRadius);
    this.alpha = alpha;
  }

  destroy() {
    unusePointTexture(pointTexture);
  }
}
