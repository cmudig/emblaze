import { transformPoint, distance2, shuffle } from '../utils/helpers.js';
import { kdTree } from '../utils/kdTree.js';

/**
 * Handles interpreting the standard input formats for the widget. If arrayType
 * is:
 *  - Array: compressed base-64 string should be a JSON string
 *  - Float32Array/Int32Array: string should be a compressed string representing
 *    an array of floats/ints
 *
 * Courtesy of https://gist.github.com/sketchpunk/f5fa58a56dcfe6168a9328e7c32a4fd4
 */
function decodeBase64String(base64String, arrayType) {
  if (arrayType === Array) {
    return JSON.parse(window.atob(base64String));
  } else {
    var blob = window.atob(base64String), // Base64 string converted to a char array
      bytesPerElement = arrayType.BYTES_PER_ELEMENT,
      fLen = blob.length / bytesPerElement, // How many floats can be made, but be even
      dView = makeTypedReader(arrayType),
      result = new arrayType(fLen), // Final Output at the correct size
      p = 0; // Position

    for (var j = 0; j < fLen; j++) {
      p = j * bytesPerElement;
      for (var k = 0; k < bytesPerElement; k++)
        dView.set(k, blob.charCodeAt(p + k));
      result[j] = dView.get();
    }
    return result;
  }
}

function makeTypedReader(arrayType) {
  let base = new DataView(new ArrayBuffer(arrayType.BYTES_PER_ELEMENT));
  let result = {
    set(offset, value) {
      base.setUint8(offset, value);
    },
  };
  if (arrayType === Float32Array) result.get = () => base.getFloat32(0, true);
  else if (arrayType === Float64Array)
    result.get = () => base.getFloat64(0, true);
  else if (arrayType === Int32Array) result.get = () => base.getInt32(0, true);
  else if (arrayType === Uint32Array)
    result.get = () => base.getUint32(0, true);
  else if (arrayType === Int16Array) result.get = () => base.getInt16(0, true);
  else if (arrayType === Uint16Array)
    result.get = () => base.getUint16(0, true);
  else if (arrayType === Int8Array) result.get = () => base.getInt8(0, true);
  else if (arrayType === Uint8Array) result.get = () => base.getUint8(0, true);
  else
    console.error(
      "unsupported array type - note that int64 arrays aren't fully supported yet"
    );
  return result;
}

/**
 * Converts the given format string (e.g. 'i8', 'u1') into a TypedArray type.
 *
 */
function selectArrayType(format) {
  switch (format) {
    case 'i8':
      return BigInt64Array;
    case 'i4':
      return Int32Array;
    case 'i2':
      return Int16Array;
    case 'i1':
      return Int8Array;
    case 'u8':
      return BigUint64Array;
    case 'u4':
      return Uint32Array;
    case 'u2':
      return Uint16Array;
    case 'u1':
      return Uint8Array;
  }
}

/**
 * A class for representing a fixed number of objects using arrays. The
 * constructor accepts a schema, which is an object whose keys will be the
 * field names that the object stores, and whose values are objects containing
 * the following values:
 * - array: A type for initializing a fixed-length array, such as Float32Array.
 *     For arbitrary object types, Array may be used.
 * - field: The name of the field in the provided data from which to obtain the
 *     values to store. If this is not provided, the key name is used.
 *
 * If the input to ColumnarData is compressed, the data object must contain a
 * length property indicating the number of objects in each field. The remaining
 * keys of the object should be the fields defined in the schema, encoded as
 * base 64 strings according to the correct types.
 */
export class ColumnarData {
  columns = {};
  nestPositionColumns = {}; // for nested fields
  schema;
  idMapping = new Map();
  length = 0;
  computedData = {};

  constructor(schema, data, additionalFields = null) {
    this.schema = schema;

    if (data['_format'] == 'compressed') {
      this.length = data['_length'];

      // Get the ids list as an Int32Array
      if (!data.ids) {
        console.error('compressed data object has no ids field');
        return;
      }
      let idType = selectArrayType(data['_idtype']);
      let ids = decodeBase64String(data.ids.values, idType);
      ids.forEach((id, i) => this.idMapping.set(id, i));

      // first read all compressed arrays from the input
      Object.keys(this.schema).forEach((col) => {
        let fieldName = this.schema[col].field || col;

        let val = data[fieldName]; // this is a JSON object
        if (!val) return;

        if (this.schema[col].nested) {
          // The value should contain an additional 'positions' key or an 'interval' key
          if (!!val.positions) {
            this.nestPositionColumns[col] = decodeBase64String(
              val.positions,
              Int32Array
            );
          } else if (!!val.interval) {
            this.nestPositionColumns[col] = new Int32Array(this.length);
            for (let k = 0; k < this.length; k++) {
              // the nest positions list the position of the END of each row's values
              this.nestPositionColumns[col][k] = (k + 1) * val.interval;
            }
          }
        }
        this.columns[col] = decodeBase64String(
          val.values,
          this.schema[col].array == 'id' ? idType : this.schema[col].array
        );
        if (!this.schema[col].nested && this.columns[col].length != this.length)
          console.warn(
            `field '${fieldName}' has incorrect length: expected ${this.length}, got ${this.columns[col].length}`
          );
      });

      // Now go back and add additional fields from the input argument
      if (!!additionalFields) {
        let newCols = {};
        Object.keys(additionalFields).forEach((f) => {
          let colSchema = this.schema[f];
          if (!colSchema) {
            console.warn("can't add additional fields without a schema column");
            return;
          }
          if (colSchema.nested) {
            console.warn(
              "can't currently add nested columns using additional fields"
            );
            return;
          }
          let arrayType =
            colSchema.array == 'id' ? Int32Array : colSchema.array;
          let newCol = new arrayType(this.length);
          newCols[f] = newCol;
        });
        ids.forEach((id, i) => {
          let pt = this.byID(id);
          Object.keys(additionalFields).forEach((f) => {
            newCols[f][i] = additionalFields[f](pt);
          });
        });
        Object.keys(newCols).forEach(
          (col) => (this.columns[col] = newCols[col])
        );
      }
    } else {
      this.length = Object.keys(data).length;
      Object.keys(this.schema).forEach((col) => {
        let len = this.length;
        if (this.schema[col].nested) {
          // This column will contain the flattened contents of arrays of
          // integers. We need to compute the exact length of the column and store
          // an additional column for "nest position", indicating where to jump to
          // for each index.
          this.nestPositionColumns[col] = new Int32Array(this.length);
          len = Object.keys(data)
            .map((id) => data[id])
            .reduce(
              (total, pt) => total + pt[this.schema[col].field || col].length,
              0
            );
        }
        let arrayType =
          this.schema[col].array == 'id' ? Int32Array : this.schema[col].array;
        this.columns[col] = new arrayType(len);
      });
      Object.keys(data).forEach((id, i) => {
        id = parseInt(id);
        this.idMapping.set(id, i);
        let pt = data[id];
        if (!!additionalFields) {
          Object.keys(additionalFields).forEach((f) => {
            pt[f] = additionalFields[f](pt, id);
          });
        }
        Object.keys(this.schema).forEach((col) => {
          let fieldVal = pt[this.schema[col].field || col];
          if (this.schema[col].nested) {
            // Set the flattened array and the current position
            let currentPos = i == 0 ? 0 : this.nestPositionColumns[col][i - 1];
            fieldVal.forEach(
              (val, j) => (this.columns[col][currentPos + j] = val)
            );
            this.nestPositionColumns[col][i] = currentPos + fieldVal.length;
          } else this.columns[col][i] = fieldVal;
        });
      });
    }
  }

  byID(id) {
    if (!this.idMapping.has(id)) return null;
    let result = {};
    Object.keys(this.schema).forEach((col) => {
      result[col] = this.get(id, col);
    });
    Object.keys(this.computedData).forEach((col) => {
      result[col] = this.computedData[col](id);
    });
    return result;
  }

  has(id) {
    return this.idMapping.has(id);
  }

  get(id, field, fallback = null) {
    if (!this.idMapping.has(id)) return fallback;
    if (!this.columns.hasOwnProperty(field)) {
      if (!this.computedData.hasOwnProperty(field)) return fallback;
      return this.computedData[field](id);
    }
    let i = this.idMapping.get(id);
    if (this.schema[field].nested) {
      // Get the subarray of the column that corresponds to this index
      let pos = i == 0 ? 0 : this.nestPositionColumns[field][i - 1];
      let endPos = this.nestPositionColumns[field][i];
      return Array.from(this.columns[field].slice(pos, endPos));
    }
    return this.columns[field][i];
  }

  map(mapper) {
    return Array.from(this.idMapping.keys()).map((id) => mapper(this.byID(id)));
  }

  forEach(fn) {
    for (var id of this.idMapping.keys()) {
      fn(this.byID(id));
    }
  }

  getIDs() {
    return Array.from(this.idMapping.keys());
  }

  size() {
    return this.idMapping.size;
  }

  getField(field) {
    if (!this.columns.hasOwnProperty(field)) return null;
    return this.columns[field];
  }

  setComputedField(fieldName, valueFn) {
    this.computedData[fieldName] = valueFn;
  }

  removeComputedField(fieldName) {
    if (this.computedData.hasOwnProperty(fieldName))
      delete this.computedData[fieldName];
  }

  // Enables this ColumnarData to retrieve values from the field in the given other
  // ColumnarData when the first field name is requested. Values are only retrieved
  // when the ID exists in this ColumnarData.
  linkField(field, data, otherField = null) {
    this.setComputedField(field, (id) => data.get(id, otherField || field));
  }

  // Enables this ColumnarData to retrieve a row of the given other ColumnarData
  // when the given field name is requested. Values are only retrieved
  // when the ID exists in this ColumnarData.
  linkData(field, data) {
    this.setComputedField(field, (id) => data.byID(id));
  }
}

const FRAME_SCHEMA = {
  x: { array: Float32Array },
  y: { array: Float32Array },
  alpha: { array: Float32Array },
  r: { array: Float32Array },
  color: { array: Array },
  highlightIndexes: { array: 'id', field: 'highlight', nested: true },
  visible: { array: Array },
};

export class ColumnarFrame extends ColumnarData {
  _kdTree;
  title;

  constructor(frame, title, additionalFields = null) {
    super(FRAME_SCHEMA, frame, additionalFields);
    this.title = title;
  }

  // Transforms all xy coordinates according to the given transformation matrix
  transform(transformation) {
    this.idMapping.forEach((i) => {
      let point = [this.columns.x[i], this.columns.y[i]];
      point = transformPoint(transformation, point);
      this.columns.x[i] = point[0];
      this.columns.y[i] = point[1];
    });
  }

  buildKdTree() {
    let coordinates = this.getIDs().map((id) => ({
      id,
      x: this.get(id, 'x'),
      y: this.get(id, 'y'),
    }));

    let tree = new kdTree(coordinates, distance2, ['x', 'y']);
    this._kdTree = {
      _tree: tree,
      nearest: (pointID, k) => {
        if (!pointID || !this.has(pointID)) return [];

        let results = tree.nearest(
          { x: this.get(pointID, 'x'), y: this.get(pointID, 'y') },
          k
        );
        return results.map((el) => parseInt(el[0].id));
      },
    };
  }

  neighbors(pointID, k) {
    if (!this._kdTree) this.buildKdTree();
    return this._kdTree.nearest(pointID, k);
  }
}

// Previews

const PREVIEW_LINE_SCHEMA = {
  lineAlpha: { array: Float32Array },
  lineWidth: { array: Float32Array },
};

/**
 * Base class for previews between frames.
 */
export class FramePreview {
  frame;
  previewFrame;
  lineData;
  _sortedByAlpha;

  constructor(frame, previewFrame, dataFn = null) {
    this.frame = frame;
    this.previewFrame = previewFrame;
    this.lineData = new ColumnarData(
      PREVIEW_LINE_SCHEMA,
      !!dataFn
        ? Object.fromEntries(this.frame.getIDs().map((id) => [id, dataFn(id)]))
        : {}
    );
  }

  /**
   * Returns the top k IDs with the highest alpha values, optionally filtering
   * to the given set of IDs.
   */
  getTopK(k, inSet = null) {
    if (this._sortedByAlpha == null) {
      let ids = this.frame.getIDs();
      this._sortedByAlpha = shuffle([...Array(ids.length).keys()]);
      let alphas = this.lineData.getField('lineAlpha');
      this._sortedByAlpha.sort((a, b) => alphas[b] - alphas[a]);
    }

    let result = [];
    this._sortedByAlpha.some((id) => {
      if (inSet != null && !inSet.has(id)) return false;
      result.push(id);
      return result.length >= k;
    });
    return result;
  }

  get(id) {
    return this.lineData.byID(id) || { lineAlpha: 0, lineWidth: 0 };
  }
}

/**
 * A type of preview where line alpha and width are determined by the number of
 * nearest neighbors of a point in the 2D space that differ between two frames.
 * This is suitable for comparing different projections of the same high-
 * dimensional embedding space, since the hi-D nearest neighbors will remain
 * constant.
 */
export class ProjectionPreview extends FramePreview {
  constructor(frame, previewFrame, k = 10, similarityThreshold = 0.7) {
    super(frame, previewFrame, (id) =>
      ProjectionPreview._calculate(
        id,
        frame,
        previewFrame,
        k,
        similarityThreshold
      )
    );
  }

  static _calculate(
    pointID,
    frame,
    previewFrame,
    k = 10,
    similarityThreshold = 0.7
  ) {
    let currentNeighbors = new Set(frame.neighbors(pointID, k));

    let previewNeighbors = new Set(previewFrame.neighbors(pointID, k));
    let intersectionCount = 0;
    currentNeighbors.forEach((n) => {
      if (previewNeighbors.has(n)) {
        intersectionCount++;
      }
    });

    let fraction = intersectionCount / currentNeighbors.size;
    let intensity;
    if (fraction >= similarityThreshold) {
      intensity = { lineWidth: 0.0, lineAlpha: 0.0 };
    } else {
      intensity = {
        lineWidth: (1 - fraction / similarityThreshold) * 10.0,
        lineAlpha: 1 - fraction / similarityThreshold,
      }; //5.0 + 20.0 * (1.0 - fraction * fraction));
    }
    return intensity;
  }
}

/**
 * A type of preview where line alpha and width are determined by the difference
 * in nearest neighbors of a point in the high-dimensional space. This is best
 * for comparing different hi-D embedding spaces, since the high-dimensional
 * neighbors may change. Depending on the dataset, there may be too many preview
 * lines shown.
 */
export class NeighborPreview extends FramePreview {
  constructor(frame, previewFrame, k = 10, similarityThreshold = 0.3) {
    super(frame, previewFrame, (id) =>
      NeighborPreview._calculate(
        id,
        frame,
        previewFrame,
        k,
        similarityThreshold
      )
    );
  }

  static _getNeighbors(frame, pointID, k) {
    let n = frame.get(pointID, 'highlightIndexes');
    if (k < n.length) n = n.slice(0, k);
    return new Set(n);
  }

  static _calculate(
    pointID,
    frame,
    previewFrame,
    k = 10,
    similarityThreshold = 0.3
  ) {
    let currentNeighbors = this._getNeighbors(frame, pointID, k);
    let previewNeighbors = this._getNeighbors(previewFrame, pointID, k);

    let intersectionCount = 0;
    currentNeighbors.forEach((n) => {
      if (previewNeighbors.has(n)) {
        intersectionCount++;
      }
    });

    let fraction = intersectionCount / currentNeighbors.size;
    let intensity;
    if (fraction >= similarityThreshold) {
      intensity = { lineWidth: 0.0, lineAlpha: 0.0 };
    } else {
      intensity = {
        lineWidth: Math.pow(1 - fraction / similarityThreshold, 3) * 5.0, //20.0,
        lineAlpha: Math.pow(1 - fraction / similarityThreshold, 3),
      }; //5.0 + 20.0 * (1.0 - fraction * fraction));
    }
    return intensity;
  }
}

/**
 * Frame preview that simply accesses precomputed preview data.
 */
export class PrecomputedPreview extends FramePreview {
  constructor(frame, previewFrame, precomputedData, scale = 1.0) {
    super(frame, previewFrame, (id) =>
      PrecomputedPreview._calculate(
        id,
        frame,
        previewFrame,
        precomputedData,
        scale
      )
    );
  }

  static _calculate(
    pointID,
    frame,
    previewFrame,
    precomputedData,
    scale = 1.0
  ) {
    let alpha = null;
    for (var comp of precomputedData) {
      if (comp.component.includes(pointID)) {
        alpha = comp.distance;
        break;
      }
    }
    if (!alpha) {
      return { lineAlpha: 0, lineWidth: 0 };
    }

    let dx = previewFrame.get(pointID, 'x') - frame.get(pointID, 'x');
    let dy = previewFrame.get(pointID, 'y') - frame.get(pointID, 'y');
    let distance = Math.sqrt(dx * dx + dy * dy);
    return {
      lineWidth: 10.0 * (distance / scale + 0.2),
      lineAlpha: alpha,
    };
  }
}
