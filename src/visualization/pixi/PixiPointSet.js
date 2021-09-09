import * as PIXI from 'pixi.js';
import * as d3 from 'd3';

function _rgbStringToArray(rgb) {
  let comps = rgb.substring(4, rgb.length - 1).split(',');
  return [
    parseInt(comps[0]) / 255.0,
    parseInt(comps[1]) / 255.0,
    parseInt(comps[2]) / 255.0,
  ];
}

/**
 * A PIXI Geometry object that holds attributes for a MarkSet.
 */
class PointSetGeometry extends PIXI.Geometry {
  marks;
  rFactor = 1.0;
  hidden = false;

  constructor(marks, rFactor, hidden) {
    super();
    this.marks = marks;
    this.rFactor = rFactor;
    this.hidden = hidden;
    this.addAttribute('x', PIXI.Buffer.from(this.makeArray('x')), 4);
    this.addAttribute('y', PIXI.Buffer.from(this.makeArray('y')), 4);
    this.addAttribute('r', PIXI.Buffer.from(this.makeArray('r')), 4);
    this.addAttribute(
      'fillStyle',
      PIXI.Buffer.from(this.makeArray('fillStyle'))
    );
    this.addAttribute('alpha', PIXI.Buffer.from(this.makeArray('alpha')), 4);
  }

  // Creates a buffer for the given attribute (PIXI attributes, not Mark attributes).
  makeArray(attrName, currentTime = null) {
    let arr;
    if (attrName == 'r') {
      arr = [];
      this.marks.forEach((mark) => {
        let anim = mark.attributes[attrName].getPreload(false, currentTime);
        arr.push((anim.start * this.rFactor * window.devicePixelRatio) / 0.6);
        arr.push((anim.end * this.rFactor * window.devicePixelRatio) / 0.6);
        arr.push(anim.startTime);
        arr.push(anim.endTime);
      });
    } else if (attrName == 'fillStyle') {
      // Expects fill style to be an [R, G, B] array
      if (this.hidden) {
        arr = this.marks
          .map((mark) => _rgbStringToArray(mark.attr('colorID')))
          .flat();
      } else {
        arr = this.marks.map((mark) => mark.attr('fillStyle')).flat();
      }
    }
    // Assume it's the same attribute as the Mark
    else {
      arr = [];
      this.marks.forEach((mark) => {
        let anim = mark.attributes[attrName].getPreload(false, currentTime);
        arr.push(anim.start);
        arr.push(anim.end);
        arr.push(anim.startTime);
        arr.push(anim.endTime);
      });
    }

    return new Float32Array(arr);
  }

  update(currentTime) {
    this.getBuffer('x').update(this.makeArray('x', currentTime));
    this.getBuffer('y').update(this.makeArray('y', currentTime));
    this.getBuffer('r').update(this.makeArray('r', currentTime));
    this.getBuffer('fillStyle').update(
      this.makeArray('fillStyle', currentTime)
    );
    this.getBuffer('alpha').update(this.makeArray('alpha', currentTime));
  }
}

const VertexShader = `
    precision mediump float;

    attribute vec4 x;
    attribute vec4 y;
    attribute vec4 r;
    attribute vec3 fillStyle;
    attribute vec4 alpha;

    varying vec3 vFillStyle;
    varying float vAlpha;

    uniform mat3 translationMatrix;
    uniform mat3 projectionMatrix;

    uniform vec2 transformA;
    uniform vec2 transformB;
    uniform float rFactor;

    uniform float currentTime;
    
    void animate(in vec4 attrib, out float interpolatedValue) {
      float t = clamp(
        (attrib.w - attrib.z >= 0.001) ? (currentTime - attrib.z) / (attrib.w - attrib.z) : 0.0,
        0.0,
        1.0
      );
      t = t * t * (3.0 - 2.0 * t);
      interpolatedValue = attrib.y * t + attrib.x * (1.0 - t);
    }

    void main() {
      animate(alpha, vAlpha);
      vFillStyle = fillStyle;
      float animatedX, animatedY;
      animate(x, animatedX);
      animate(y, animatedY);
      vec2 transformedPosition = vec2(animatedX, animatedY) * transformA + transformB;
      gl_Position = vec4((projectionMatrix * translationMatrix * vec3(transformedPosition, 1.0)).xy, 0.0, 1.0);
      float animatedR;
      animate(r, animatedR);
      gl_PointSize = animatedR * 2.0 * rFactor;
    }
`;

const FragmentShader = `
    #ifdef GL_OES_standard_derivatives
    #extension GL_OES_standard_derivatives : enable
    #endif

    precision mediump float;

    uniform bool showBorders;

    const float fillAlpha = 0.5; // for some reason this isn't perceptually consistent with other alphas
    const float strokeWidth = 0.3;
    const float inset = 0.6;

    varying vec3 vFillStyle;
    varying float vAlpha;

    void main () {
      float r = 0.0, delta = 0.0, alpha = vAlpha;
      vec2 cxy = 2.0 * gl_PointCoord - 1.0;
      r = dot(cxy, cxy);
      if (showBorders) {
        #ifdef GL_OES_standard_derivatives
          delta = fwidth(r);
          float strokeMinInner = inset - strokeWidth - delta;
          float strokeMinOuter = inset - strokeWidth + delta;
          float strokeMaxInner = inset - delta;
          float strokeMaxOuter = inset + delta;
          alpha *= fillAlpha * step(-strokeMinOuter, -r) * (1.0 - smoothstep(strokeMinInner, strokeMinOuter, r)) + 
            1.0 * step(strokeMinInner, r) * step(-strokeMaxInner, -r) * smoothstep(strokeMinInner, strokeMinOuter, r) + 
            1.0 * step(strokeMaxInner, r) * (1.0 - smoothstep(strokeMaxInner, strokeMaxOuter, r));
        #else
          float strokeMin = inset - strokeWidth;
          float strokeMax = inset;
          alpha *= fillAlpha * step(-strokeMin, -r) + 
            1.0 * step(strokeMin, r) * step(-strokeMax, -r);
        #endif
      } else {
        #ifdef GL_OES_standard_derivatives
          delta = fwidth(r);
          float borderInner = inset - delta;
          float borderOuter = inset + delta;
          if (r > inset + delta) {
            discard;
          }
          alpha *= fillAlpha * step(-borderOuter, -r) * (1.0 - smoothstep(borderInner, borderOuter, r));
        #else
          if (r > inset) {
            discard;
          }
          alpha *= fillAlpha;
        #endif
      }

      gl_FragColor = vec4(vFillStyle * alpha, alpha);
    }
`;

// Uses just rectangles instead of circles
const HiddenFragmentShader = `
    precision mediump float;

    varying vec3 vFillStyle;
    varying float vAlpha;

    void main () {
      float r = 0.0, delta = 0.0;
      if (vAlpha < 0.001) {
        discard;
      }
      vec2 cxy = 2.0 * gl_PointCoord - 1.0;
      r = dot(cxy, cxy);
      if (r > 1.0) {
        discard;
      }

      gl_FragColor = vec4(vFillStyle, 1.0);
    }
`;

export default class PixiPointSet extends PIXI.Mesh {
  marks;
  rFactor = 1.0;
  renderBox = null;
  hidden = false;

  showBorders = true;

  constructor(
    marks,
    transformInfo,
    rFactor = 1.0,
    renderBox = null,
    hidden = false
  ) {
    let geometry = new PointSetGeometry(marks, rFactor, hidden);
    let uniforms = {
      transformA: { x: transformInfo.x.a, y: transformInfo.y.a },
      transformB: { x: transformInfo.x.b, y: transformInfo.y.b },
      currentTime: 0.0,
      rFactor,
    };
    if (!hidden) uniforms.showBorders = true;
    let shader = new PIXI.Shader.from(
      VertexShader,
      hidden ? HiddenFragmentShader : FragmentShader,
      uniforms
    );
    super(geometry, shader, PIXI.State.for2d(), PIXI.DRAW_MODES.POINTS);

    this.marks = marks;
    this.rFactor = rFactor;
    this.renderBox = renderBox;
  }

  updateCoordinateTransform(info) {
    this.shader.uniforms.transformA = { x: info.x.a, y: info.y.a };
    this.shader.uniforms.transformB = { x: info.x.b, y: info.y.b };
    if (!!info.rFactor) {
      this.rFactor = info.rFactor;
      this.shader.uniforms.rFactor = info.rFactor;
    }
  }

  update(currentTime, needsGeometryUpdate = false) {
    this.shader.uniforms.rFactor = this.rFactor;
    this.shader.uniforms.currentTime = currentTime;
    if (!this.hidden) this.shader.uniforms.showBorders = this.showBorders;
    if (needsGeometryUpdate) this.geometry.update(currentTime);
  }
}
