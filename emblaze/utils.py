import sys
import numpy as np
from affine import Affine
from numba import jit
import json
import datetime
import platform
import os
import base64

class Field:
    """Standardized field names for embeddings and projections. These data can
    all be versioned within a ColumnarData object."""
    POSITION = "position"
    COLOR = "color"
    RADIUS = "r"
    NEIGHBORS = "highlight"
    ALPHA = "alpha"
    
    # Thumbnail fields
    NAME = "name"
    DESCRIPTION = "description"
    
class ProjectionTechnique:
    """Names of projection techniques."""
    UMAP = "umap"
    TSNE = "tsne"
    ALIGNED_UMAP = "aligned-umap"
    PCA = "pca"
    
class DataType:
    """Types of data, e.g. categorical vs continuous."""
    CATEGORICAL = "categorical"
    CONTINUOUS = "continuous"

class PreviewMode:
    """Ways of calculating preview lines."""
    PROJECTION_SIMILARITY = "projectionNeighborSimilarity"
    NEIGHBOR_SIMILARITY = "neighborSimilarity"
    
class SidebarPane:
    """Indexes of sidebar panes in the widget."""
    CURRENT = 0
    SAVED = 1
    RECENT = 2
    SUGGESTED = 3

FLIP_FACTORS = [
    np.array([1, 1, 1]),
    np.array([-1, 1, 1]),
    np.array([1, -1, 1])    
]

def projection_standardizer(emb):
    """Returns an affine transformation to translate an embedding to the centroid
    of the given set of points."""
    return Affine.translation(*(-emb.mean(axis=0)[:2]))

def affine_to_matrix(t):
    """
    Returns a 3x3 matrix representing the transformation matrix.
    """
    return np.array([
        [t.a, t.b, t.c],
        [t.d, t.e, t.f],
        [t.g, t.h, t.i]
    ])
    
def matrix_to_affine(mat):
    """
    Returns an Affine transformation object from the given 3x3 matrix.
    """
    return Affine(*(mat.flatten()[:6]))

def affine_transform(transform, points):
    """
    Transforms a set of N x 2 points using the given Affine object.
    """
    reshaped_points = np.vstack([points.T, np.ones((1, points.shape[0]))])
    transformed = np.dot(affine_to_matrix(transform), reshaped_points)
    return transformed.T[:,:2] # pylint: disable=unsubscriptable-object

def standardize_json(o, round_digits=4):
    """
    Produces a JSON-compliant object by replacing numpy types with system types
    and rounding floats to save space.
    """
    if isinstance(o, (float, np.float32, np.float64)): return round(float(o), round_digits)
    if isinstance(o, (np.int64, np.int32, np.uint8)): return int(o)
    if isinstance(o, dict): return {standardize_json(k, round_digits): standardize_json(v, round_digits) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [standardize_json(x, round_digits) for x in o]
    return o

@jit(nopython=True)
def inverse_intersection(seqs1, seqs2, mask_ids, outer):
    """
    Computes the inverse intersection size of the two lists of sets.
    
    Args:
        seqs1: A list of iterables
        seqs2: Another list of iterables - must be the same length as seqs1
        mask_ids: Iterable containing objects that should be EXCLUDED if outer
            is True, and INCLUDED if outer is False
        outer: Determines the behavior of mask_ids
        
    Returns:
        A numpy array of inverse intersection sizes between each element in
        seqs1 and seqs2.
    """
    distances = np.zeros(len(seqs1))
    mask_ids = set(mask_ids)
    for i in range(len(seqs1)):
        set1 = set([n for n in seqs1[i] if (n in mask_ids) != outer])
        set2 = set([n for n in seqs2[i] if (n in mask_ids) != outer])
        num_intersection = len(set1 & set2)
        if len(set1) or len(set2):
            distances[i] = 1 / (1 + num_intersection)
    return distances

class LoggingHelper:
    """
    Writes and/or updates a JSON file with interaction information.
    """
    def __init__(self, filepath, addl_info=None):
        super().__init__()
        self.filepath = filepath
        
        if not os.path.exists(self.filepath):
            current_data = {
                "timestamp": str(datetime.datetime.now()),
                "platform": platform.platform(),
                "version": sys.version,
                "logs": []
            }
            if addl_info is not None:
                current_data.update(addl_info)
            with open(self.filepath, "w") as file:
                json.dump(current_data, file)

        
    def add_logs(self, entries):
        """
        Adds a list of logging entries to the log file.
        """
        with open(self.filepath, "r") as file:
            current_data = json.load(file)
                
        current_data["logs"] += entries
        
        with open(self.filepath, "w") as file:
            json.dump(current_data, file)
            
def choose_integer_type(values):
    """
    Chooses the best integer type (i.e. np.(u)int(8|16|32)) for the given set
    of values. Returns the dtype and its name.
    """
    min_val = values.min()
    max_val = values.max()
    rng = max_val - min_val
    if min_val < 0:
        if rng > 2 ** 32 - 1:
            return np.int64, "i8"
        elif rng > 2 ** 16 - 1:
            return np.int32, "i4"
        elif rng > 2 ** 8 - 1:
            return np.int16, "i2"
        return np.int8, "i1"
    elif rng > 2 ** 32 - 1:
        return np.uint64, "u8"
    elif rng > 2 ** 16 - 1:
        return np.uint32, "u4"
    elif rng > 2 ** 8 - 1:
        return np.uint16, "u2"
    return np.uint8, "u1"
    
def encode_numerical_array(arr, astype=np.float32, positions=None, interval=None):
    """
    Encodes the given numpy array into a base64 representation for fast transfer
    to the widget frontend. The array will be encoded as a sequence of numbers
    with type 'astype'.
    
    If positions is not None, it should be a numpy array of positions at which the
    array for each ID *ends*. For example, if there are ten IDs and ten numbers
    in the array for each ID, the positions array would be [10, 20, ..., 90, 100].
    
    If interval is not None, it is passed into the result object directly (and
    signifies the same as positions, but with a regularly spaced interval).
    """
    result = { "values": base64.b64encode(arr.astype(astype)).decode('ascii') }
    if positions is not None:
        result["positions"] = base64.b64encode(positions.astype(np.int32)).decode('ascii')
    if interval is not None:
        result["interval"] = interval
    return result

def encode_object_array(arr):
    """
    Encodes the given array as a base64 string of a JSON string.
    """
    if isinstance(arr, np.ndarray):
        arr = arr.tolist()
        
    return { "values": base64.b64encode(json.dumps(standardize_json(arr)).encode("utf-8")).decode('ascii') }

def decode_numerical_array(obj, astype=np.float32):
    """
    Decodes the given compressed dict into an array of the given dtype. The 
    dict should contain a 'values' key (base64 string) and optionally a
    'positions' key (base64 string to be turned into an int32 array, defining
    the shape of a 2d matrix) or an 'interval' key (integer defining the number
    of columns in the 2d matrix).
    """
    values = np.frombuffer(base64.decodebytes(obj["values"].encode('ascii')), dtype=astype)
    if "positions" in obj:
        positions = np.frombuffer(base64.decodebytes(obj["positions"].encode('ascii')), dtype=np.int32)
        deltas = positions[1:] - positions[:-1]
        assert np.allclose(deltas, deltas[0]), "cannot currently decode numerical arrays with non-standard positions array"
        values = values.reshape(-1, deltas[0])
    elif "interval" in obj:
        values = values.reshape(-1, obj["interval"])
    return values

def decode_object_array(obj):
    """
    Decodes the given object's 'values' key into a JSON object.
    """
    return json.loads(base64.b64decode(obj["values"].encode('ascii')))


