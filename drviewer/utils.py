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
