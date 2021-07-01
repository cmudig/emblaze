import * as PIXI from 'pixi.js';

/*
  A Loader-mimicking class that provides access to spritesheets already loaded
  in memory.

  Thanks to https://github.com/pixijs/pixi.js/issues/5597
*/
export class PixiInMemoryLoader {
  resources = {};

  /**
   * Adds a spritesheet with the given name, loading from the given spritesheet
   * spec JSON object and with the given binary image data.
   * @param {string} name the name of the spritesheet to save
   * @param {object} spritesheetSpec PIXI spritesheet-format JSON object
   * @param {string} imageData raw base-64 encoded image data
   * @param {string} imageFormat the encoding of the image data
   */
  add(name, spritesheetSpec, imageData, imageFormat = 'image/png') {
    let image = new Image();
    image.src = `data:${imageFormat};base64,${imageData}`;

    // Manually create a spritesheet using the given spec and image
    let baseTexture = new PIXI.BaseTexture(image);
    let spritesheet = new PIXI.Spritesheet(baseTexture, spritesheetSpec);
    this.resources[name] = spritesheet;

    return new Promise((resolve) => {
      spritesheet.parse(resolve);
    });
  }

  destroy() {
    // Make sure the textures all get removed from the cache
    Object.values(this.resources).forEach((s) => {
      var baseTex;
      Object.keys(s.textures).forEach((t) => {
        PIXI.Texture.removeFromCache(t);
        baseTex = s.textures[t].baseTexture; //they all have same base texture
      });
      PIXI.BaseTexture.removeFromCache(baseTex);
      s.destroy(true);
    });
    this.resources = {};
  }
}
