import { base64ToBlob } from '../utils/helpers';

/**
 * A helper class that returns objects that direct how to represent thumbnails
 * for given point IDs. If the given dataset has spritesheets, this object loads
 * the spritesheets as blobs and returns the URLs needed to render image
 * thumbnails.
 *
 * Note that destroy() should be called before releasing this
 * object.
 */
export class ThumbnailProvider {
  blobURLs = new Map();
  hasImages = false;
  dataset;

  constructor(dataset) {
    this.dataset = dataset;
    this.updateImageThumbnails();
  }

  updateImageThumbnails() {
    if (this.blobURLs.size > 0) this.destroy();
    if (!!this.dataset.spritesheets) {
      this.hasImages = true;
      Object.keys(this.dataset.spritesheets).forEach((sheet) => {
        // Make a blob containing this spritesheet image
        let sheetInfo = this.dataset.spritesheets[sheet];
        let blob = base64ToBlob(sheetInfo.image, sheetInfo.imageFormat);
        this.blobURLs.set(sheet, URL.createObjectURL(blob));
      });
    } else {
      this.hasImages = false;
    }
  }

  destroy() {
    // Remove all blobs used for this thumbnail viewer
    for (var sheet of this.blobURLs.keys()) {
      URL.revokeObjectURL(this.blobURLs.get(sheet));
    }
    this.blobURLs.clear();
    this.hasImages = false;
  }

  get(id, inFrame, into = null) {
    if (into == null) {
      into = {};
    }

    let itemInfo = this.dataset.frame(inFrame).get(id, 'label');
    if (!itemInfo)
      return {
        id,
        text: id.toString(),
      };

    into.id = id;
    into.text = itemInfo.text;
    into.description = itemInfo.description;

    if (
      !!itemInfo.sheet &&
      !!this.dataset.spritesheets &&
      !!this.dataset.spritesheets[itemInfo.sheet]
    ) {
      // Add properties to indicate where to retrieve the image thumbnail from
      // the spritesheet
      into.src = this.blobURLs.get(itemInfo.sheet);
      let sheet = this.dataset.spritesheets[itemInfo.sheet];
      into.spec = sheet.spec.frames[itemInfo.texture];
      into.macroSize = sheet.spec.meta.size;
    }

    return into;
  }
}
