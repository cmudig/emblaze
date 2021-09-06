import numpy as np
from affine import Affine

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
