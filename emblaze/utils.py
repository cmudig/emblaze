import sys
import numpy as np
from affine import Affine
from numba import jit
import json
import datetime
import platform
import os

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
    if isinstance(o, (np.int64, np.int32)): return int(o)
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