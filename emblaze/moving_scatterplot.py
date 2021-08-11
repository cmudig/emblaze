import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_distances, euclidean_distances
from sklearn.neighbors import NearestNeighbors
from scipy.spatial.transform import Rotation
from affine import Affine

def round_floats(o, amount):
    if isinstance(o, (float, np.float64)): return round(float(o), amount)
    if isinstance(o, np.int64): return int(o)
    if isinstance(o, dict): return {k: round_floats(v, amount) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [round_floats(x, amount) for x in o]
    return o

class ScatterplotFrame:
    def __init__(self, data, x_key="x", y_key="y", metric="euclidean"):
        """
        data: A list of dictionaries of values. The id field is required.
        x_key: Key to use for x coordinates.
        y_key: Key to use for y coordinates.
        metric: Metric to use for distance calculations.
        """
        super().__init__()
        df = pd.DataFrame(data)
        df["id"] = df["id"].astype(str)
        self.df = df.set_index("id")
        self._id_index = {id_val: i for i, id_val in enumerate(self.df.index)}

        self.x_key = x_key
        self.y_key = y_key
        self.metric = metric

        self._neighbors = None
        self._neighbor_dists = None
        self._distances = None
        
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, ids):
        return self.df.iloc[self.index(ids)]
    
    def to_viewer_dict(self, x_key="x", y_key="y", additional_fields=None, n_neighbors=10):
        """
        Converts this scatterplot frame into a dictionary from IDs to viewer-
        friendly values. Also adds the nearest neighbors for each point.
        
        Args:
            x_key: Key to use for x values. Remapped to the 'x' field in result.
            y_key: Key to use for y values. Remapped to the 'y' field in result.
            additional_fields: If not None, a dictionary of field names to
                lists of values or functions. A function value should take two
                parameters, the ID of the item and an indexable item, and return
                a value for the field.
            n_neighbors: Number of neighbors to write in the highlight field.
            
        Returns:
            A dictionary of IDs to item dictionaries. The keys present in the
            result will be 'id', 'x', 'y', 'highlight', and any fields specified
            in additional_fields.
        """
        
        items = pd.DataFrame({
            "id": self.df.index,
            "x": self.df[x_key],
            "y": self.df[y_key]
        }).set_index("id", drop=False)
        if additional_fields is None: additional_fields = {}
        for col, field_val in additional_fields.items():
            try:
                iter(field_val)
            except TypeError:
                # It's a function
                items[col] = [field_val(id_val, item)
                            for id_val, item in self.df.iterrows()]
            else:
                assert len(field_val) == len(self.df), f"Mismatched lengths for additional field {col}"
                items[col] = field_val

        return items.to_dict(orient="index")
        
    def index(self, id_vals):
        """
        Returns the index(es) of the given IDs.
        """
        if isinstance(id_vals, (list, np.ndarray, set)):
            return [self._id_index[str(id_val)] for id_val in id_vals]
        else:
            return self._id_index[str(id_vals)]

    def get_columns(self):
        """Returns the list of column names for the internal data."""
        return self.df.columns.tolist()
    
    def get_ids(self):
        """Returns the list of ids."""
        return self.df.index.tolist()
    
    def set_coordinate_keys(self, x_key, y_key):
        """Changes the field names for computing distances and neighbors."""
        self.x_key = x_key
        self.y_key = y_key
        self._neighbors = None
        self._neighbor_dists = None
        self._distances = None
    
    def __contains__(self, id_val):
        """Returns whether or not the frame contains the given ID."""
        return id_val in self.df.index
    
    def subframe(self, fields=None, ids=None):
        """
        Returns another ScatterplotFrame containing the given subset of fields
        and IDs.
        """
        sub_df = self.df
        if ids is not None:
            sub_df = self.df.iloc[self.index(ids)]
        if fields is not None:
            sub_df = sub_df[fields]
        return ScatterplotFrame(sub_df.reset_index().to_dict(orient='records'),
                                x_key=self.x_key,
                                y_key=self.y_key,
                                metric=self.metric)
        
    def mat(self, fields=None, ids=None):
        """
        Returns a numpy array containing the values in the given fields.
        """
        sub_df = self.df
        if ids is not None:
            sub_df = self.df.iloc[self.index(ids)]
        return (sub_df[fields] if fields else sub_df).values

    def set_mat(self, fields, mat):
        """
        Sets the values in the given fields to the columns of the matrix.
        """
        for col_name, col_idx in zip(fields, range(mat.shape[1])):
            self.df[col_name] = mat[:,col_idx]

    def _calc_neighbors(self, n_neighbors):
        """Calculates nearest neighbors for all points."""
        locations = self.mat([self.x_key, self.y_key])
        self.neighbor_clf = NearestNeighbors(metric=self.metric,
                                             n_neighbors=n_neighbors + 1).fit(locations)
        neigh_dists, neigh_indexes = self.neighbor_clf.kneighbors(locations)
        self._neighbors = neigh_indexes[:,1:]
        self._neighbor_dists = neigh_dists[:,1:]
        
    def neighbors(self, ids=None, k=10, return_distances=False):
        """
        Returns the k nearest neighbors to the given ID or set of IDs (or all
        points if ids is None). If return_distances is True, returns a tuple 
        (neighbor IDs, distances).
        """
        if self._neighbors is None or self._neighbors.shape[1] < k:
            self._calc_neighbors(k)
        
        if ids is None:
            indexes = np.arange(self._neighbors.shape[0])
        else:
            indexes = self.index(ids)

        neighbor_ids = np.vectorize(lambda i: self.df.index[i])(self._neighbors[indexes][:,:k])
        if return_distances:
            return neighbor_ids, self._neighbor_dists[indexes][:,:k]
        return neighbor_ids
    
    def external_neighbors(self, points, k=10, return_distances=False):
        """
        Returns the k nearest neighbors to the given set of points, where points
        is an N x 2 matrix. The coordinates will be compared to the x_key and
        y_key values in the frame, respectively.
        """
        if self._neighbors is None or self._neighbors.shape[1] < k - 1:
            self._calc_neighbors(k)
        dists, indexes = self.neighbor_clf.kneighbors(points)
        neighbor_ids = np.vectorize(lambda i: self.df.index[i])(indexes[:,:k])
        if return_distances:
            return neighbor_ids, dists[:,:k]
        return neighbor_ids

    def distances(self, ids=None, comparison_ids=None):
        """
        Returns the pairwise distances from the given IDs to each other (or all
        points to each other, if ids is None).
        """
        if self._distances is None:
            locations = self.mat([self.x_key, self.y_key])
            if self.metric == "euclidean":
                self._distances = euclidean_distances(locations, locations)
            elif self.metric == "cosine":
                self._distances = cosine_distances(locations, locations)
            else:
                raise NotImplementedError("Unsupported metric for distances")
        
        if ids is None:
            indexes = np.arange(len(self.df))
        else:
            indexes = self.index(ids)
            
        if comparison_ids is None:
            comparison_indexes = indexes
        else:
            comparison_indexes = self.index(comparison_ids)

        return self._distances[indexes,:][:,comparison_indexes]

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

def align_projection(base_frame, frame, ids=None, return_transform=False, base_transform=None, allow_flips=True):
    """
    Aligns the given projection to the base frame. The frames are aligned based
    on the keys they have in common.
    
    Args:
        base_frame: A ScatterplotFrame to use as the base.
        frame: A ScatterplotFrame to transform.
        ids: Point IDs to use for alignment (default None, which results in an
            alignment using the intersection of IDs between the two frames).
        return_transform: If true, return just the Affine object instead of the
            rotated data.
        base_transform: If not None, an Affine object representing the
            transformation to apply to the base frame before aligning.
        allow_flips: If true, test inversions as possible candidates for alignment.
        
    Returns:
        A numpy array containing the x and y coordinates for the points in
        frame.
    """
    # Determine a set of points to use for comparison
    ids_to_compare = list(ids) if ids is not None else list(set(frame.get_ids()) & set(base_frame.get_ids()))
    proj_subset = frame.mat(fields=[frame.x_key, frame.y_key], ids=ids_to_compare)
    proj_scaler = projection_standardizer(proj_subset)
    base_proj_subset = base_frame.mat(fields=[base_frame.x_key, base_frame.y_key], ids=ids_to_compare)
    if base_transform is not None:
        base_proj_subset = affine_transform(base_transform, base_proj_subset)    
    base_proj_scaler = projection_standardizer(base_proj_subset)
    
    proj = np.hstack([
        affine_transform(proj_scaler, proj_subset),
        np.zeros((len(proj_subset), 1))
    ])
    base_proj = np.hstack([
        affine_transform(base_proj_scaler, base_proj_subset),
        np.zeros((len(base_proj_subset), 1))
    ])
    
    # Test flips
    min_rmsd = 1e9
    best_variant = None
    for factor in (FLIP_FACTORS if allow_flips else FLIP_FACTORS[:1]):
        opt_rotation, rmsd = Rotation.align_vectors( # pylint: disable=unbalanced-tuple-unpacking
            base_proj,
            proj * factor)
        if rmsd < min_rmsd:
            min_rmsd = rmsd
            transform = ~base_proj_scaler * matrix_to_affine(opt_rotation.as_matrix()) * Affine.scale(*factor[:2]) * proj_scaler
            if return_transform:
                best_variant = transform
            else:
                best_variant = affine_transform(transform,
                    frame.mat([frame.x_key, frame.y_key]))

    return best_variant

if __name__ == "__main__":
    # Testing
    frame = ScatterplotFrame([{"id": 3, "x": 3, "y": 5},
                              {"id": 7, "x": 4, "y": 6},
                              {"id": 10, "x": -1, "y": 3}])
    print(frame.get_columns(), frame.get_ids())
    print(frame.mat(ids=["7", 3]))
    print(frame.distances([3, 7]))
    print(frame.to_viewer_dict(additional_fields={"t": np.arange(3), "u": lambda i, item: item["x"] + 1}, n_neighbors=1))