import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_distances, euclidean_distances
from sklearn.neighbors import NearestNeighbors
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from scipy.spatial.transform import Rotation
from affine import Affine
from .utils import *
from .neighbors import Neighbors, NeighborSet
    
class ColumnarData:
    """
    A data structure that contains multiple fields, each of which stores a
    numpy array of values with the same number of rows.
    """
    def __init__(self, data, ids=None):
        """
        data: A dictionary where the keys are members from the Field class and
            the values are numpy or regular arrays.
        """
        self.data = {}
        length = None
        for field, values in data.items():
            assert isinstance(field, str), "Field name not string: {}".format(field)
            if length is None:
                length = len(values)
            assert length == len(values), "Field '{}' has mismatched length (expected {}, got {})".format(field, length, len(values))
            self.data[field] = np.array(values)

        self.length = length
        self.ids = np.array(ids) if ids is not None else np.arange(length)
        self._id_index = {id: i for i, id in enumerate(self.ids)}
        
    def set_ids(self, new_ids):
        """
        Gives the ColumnarData a new set of ID numbers.
        """
        self.ids = np.array(new_ids) if new_ids is not None else np.arange(len(self))
        self._id_index = {id: i for i, id in enumerate(self.ids)}
        
    def copy(self):
        return ColumnarData(self.data, self.ids)
    
    def __str__(self):
        return "<{} with {} items, {} fields ({})>".format(
            type(self).__name__,
            len(self),
            len(self.data),
            ', '.join(list(self.data.keys())))
    
    def __repr__(self):
        return str(self)
    
    def copy_with_fields(self, updated_fields):
        copy = self.copy()
        for field, vals in updated_fields.items():
            copy.set_field(field, vals)
        return copy

    def __len__(self):
        return self.length
    
    def __contains__(self, id_val):
        """
        Returns whether the data has the given ID.
        """
        return int(id_val) in self._id_index
    
    def index(self, id_vals):
        """
        Returns the index(es) of the given IDs.
        """
        if isinstance(id_vals, (list, np.ndarray, set)):
            return [self._id_index[int(id_val)] for id_val in id_vals]
        else:
            return self._id_index[int(id_vals)]

    def has_field(self, field):
        return field in self.data
    
    def field(self, field, ids=None):
        if field not in self.data:
            return None
        if ids is not None:
            return self.data[field][self.index(ids)]
        return self.data[field]
    
    def stack_fields(self, fields, ids=None):
        return np.hstack([self.field(field, ids) for field in fields])
    
    def concat(self, other):
        """
        Returns a new ColumnarData with this ColumnarData and the given one
        stacked together. Must have the same set of fields, and a disjoint set of
        IDs.
        """
        assert set(self.data.keys()) == set(other.data.keys()), "Cannot concatenate ColumnarData objects with different sets of fields"
        assert not (set(self.ids.tolist()) & set(other.ids.tolist())), "Cannot concatenate ColumnarData objects with overlapping ID values"
        
        return ColumnarData({k: np.concatenate([self.field(k), other.field(k)])
                             for k in self.data.keys()},
                            ids=np.concatenate([self.ids, other.ids]))
    
    def set_field(self, field, values):
        assert self.length == len(values), "Field '{}' has mismatched length (expected {}, got {})".format(field, self.length, len(values))
        self.data[field] = np.array(values)
        
    def guess_data_type(self, field):
        """
        Guesses the likely data type for the given field, returning either
        DataType.CATEGORICAL or DataType.CONTINUOUS.
        """
        if field not in self.data:
            return None
        if np.issubdtype(self.data[field].dtype, np.number) and len(np.unique(self.data[field])) >= 12:
            return DataType.CONTINUOUS
        return DataType.CATEGORICAL
    
class Embedding(ColumnarData):
    """
    A single set of high-dimensional embeddings, which can be represented as an
    n x k 2D numpy array (n = number of points, k = dimensionality).
    """
    def __init__(self, data, ids=None, label=None, metric='euclidean', n_neighbors=100, neighbors=None, parent=None):
        super().__init__(data, ids)
        assert Field.POSITION in data, "Field.POSITION is required"
        assert Field.COLOR in data, "Field.COLOR is required"
        self.label = label
        self.metric = metric
        self.n_neighbors = n_neighbors
        self._distances = {}
        self.parent = parent # keep track of where this embedding came from
        self.neighbors = neighbors

    def copy(self):
        return Embedding(self.data,
                         self.ids,
                         label=self.label,
                         metric=self.metric,
                         n_neighbors=self.n_neighbors,
                         neighbors=self.neighbors,
                         parent=self)
    
    def copy_with_fields(self, updated_fields, clear_neighbors=False):
        copy = self.copy()
        for field, vals in updated_fields.items():
            copy.set_field(field, vals)
        if clear_neighbors:
            copy.clear_neighbors()
        return copy

    def concat(self, other):
        """
        Returns a new Embedding with this Embedding and the given one
        stacked together. Must have the same set of fields, and a disjoint set of
        IDs.
        """
        assert set(self.data.keys()) == set(other.data.keys()), "Cannot concatenate Embedding objects with different sets of fields"
        assert not (set(self.ids.tolist()) & set(other.ids.tolist())), "Cannot concatenate Embedding objects with overlapping ID values"
        assert self.has_neighbors() == other.has_neighbors(), "Either both or neither Embedding object must have a Neighbors"
        
        return Embedding({k: np.concatenate([self.field(k), other.field(k)])
                          for k in self.data.keys()},
                         ids=np.concatenate([self.ids, other.ids]),
                         neighbors=self.get_neighbors().concat(other.get_neighbors()) if self.has_neighbors() else None,
                         n_neighbors=max(self.n_neighbors, other.n_neighbors),
                         label=self.label, metric=self.metric)
    
    def get_root(self):
        """Returns the root parent of this embedding."""
        if self.parent is None: return self
        return self.parent.get_root()
    
    def has_neighbors(self):
        return self.neighbors is not None
    
    def any_ancestor_has_neighbors(self):
        """
        Returns True if any of the Embeddings in the parent tree have embeddings
        computed.
        """
        return self.find_recent_neighbor_embedding() is not None
    
    def get_neighbors(self):
        return self.neighbors
    
    def find_ancestor_neighbor_embedding(self):
        """
        Returns the Embedding that is furthest along this Embedding's parent
        tree and has a neighbor set.
        """
        ancestor = None
        curr = self
        while curr is not None:
            ancestor = curr if curr.has_neighbors() else ancestor
            curr = curr.parent
        return ancestor
                
    def get_ancestor_neighbors(self):
        """
        Gets the neighbor set of the Embedding that is furthest along this
        Embedding's ancestry tree and has a neighbor set.
        """
        ancestor = self.find_ancestor_neighbor_embedding()
        if ancestor:
            return ancestor.get_neighbors()
    
    def find_recent_neighbor_embedding(self):
        """
        Returns the Embedding that is closest to this Embedding in the parent
        tree (including this Embedding) that has a neighbor set.
        """
        curr = self
        while curr is not None and not curr.has_neighbors():
            curr = curr.parent
        return curr
    
    def get_recent_neighbors(self):
        """
        Gets the neighbor set of the Embedding that is closest to this Embedding
        in the parent tree (including itself) and that has a neighbor set.
        """
        recent = self.find_recent_neighbor_embedding()
        if recent:
            return recent.get_neighbors()
    
    def dimension(self):
        """Returns the dimensionality of the Field.POSITION field."""
        return self.field(Field.POSITION).shape[1]

    def project(self, method=ProjectionTechnique.UMAP, **params):
        """
        Projects this embedding space into a lower dimensionality. The method
        parameter can be a callable, which will define a dimensionality
        reduction technique that takes as input a numpy array and a list of IDs,
        as well as any keyword arguments given to the params argument of this
        method, and returns a dimension-reduced matrix. If no metric is provided
        in the keyword params, the default metric of this Embedding is used.
        
        Returns: A new Embedding object with the Field.POSITION value set to the
            result of the projection.
        """
        hi_d = self.field(Field.POSITION)
        params = params or {}
        if method != ProjectionTechnique.PCA:
            params["metric"] = params.get("metric", self.metric)
        
        if method == ProjectionTechnique.UMAP:
            import umap
            lo_d = umap.UMAP(**params).fit_transform(hi_d)
        elif method == ProjectionTechnique.TSNE:
            lo_d = TSNE(**params).fit_transform(hi_d)
        elif method == ProjectionTechnique.PCA:
            lo_d = PCA(**params).fit_transform(hi_d)
        elif callable(method):
            lo_d = method(hi_d, self.ids, **params)
        else:
            raise ValueError("Unrecognized projection technique '{}'".format(method))
        
        return self.copy_with_fields({Field.POSITION: lo_d}, clear_neighbors=True)
    
    def get_relations(self, other_emb):
        """
        Computes a mapping from the IDs in this embedding to the positions
        in the other embedding (used for AlignedUMAP).
        """
        return {self.index(id_val): other_emb.index(id_val)
                for id_val in self.ids if id_val in other_emb}
    
    def compute_neighbors(self, n_neighbors=None, metric=None):
        """
        Computes and saves a set of nearest neighbors in this embedding according
        to the Field.POSITION values. This can be accessed after completing this
        step through the neighbors property. If the metric or n_neighbors
        is not provided, the default metric and n_neighobrs for this Embedding
        object is used.
        
        If this Embedding is copied or projected, it will inherit the same
        Neighbors.
        """
        pos = self.field(Field.POSITION)
        # Save the metric and n_neighbors here so that they can be used to
        # re-generate the Neighbors later if needed
        self.metric = metric or self.metric
        self.n_neighbors = n_neighbors or self.n_neighbors
        self.neighbors = Neighbors.compute(pos,
                                             ids=self.ids,
                                             metric=metric or self.metric,
                                             n_neighbors=self.n_neighbors)
        
    def clear_neighbors(self):
        """
        Removes the saved Neighbors associated with this Embedding. This can
        be used to determine which Neighbors is returned by get_ancestor_neighbors().
        """
        self.neighbors = None
        
    def clear_upstream_neighbors(self):
        """
        Clears the neighbor sets for all Embeddings in the parent tree of this
        Embedding (but not this one).
        """
        curr = self.parent
        while curr is not None:
            curr.clear_neighbors()
            curr = curr.parent
        
    def neighbor_distances(self, ids=None, n_neighbors=100, metric=None):
        """
        Returns the list of nearest neighbors for each of the given IDs and the
        distances to each of those points. This does NOT use the Neighbors
        object, and is therefore based only on the locations of the points in 
        this Embedding (not potentially on its parents).
        """
        pos = self.field(Field.POSITION, ids=ids)
        neighbor_clf = NearestNeighbors(metric=metric or self.metric).fit(self.field(Field.POSITION))
        neigh_distances, neigh_indexes = neighbor_clf.kneighbors(pos, n_neighbors=min(n_neighbors + 1, len(self)))
        return neigh_indexes[:,1:], neigh_distances[:,1:]
        
    def distances(self, ids=None, comparison_ids=None, metric=None):
        """
        Returns the pairwise distances from the given IDs to each other (or all
        points to each other, if ids is None). If the metric is not provided,
        the default metric for this Embedding object is used.
        """
        metric = metric or self.metric
        
        if ids is None:
            indexes = np.arange(len(self))
        else:
            indexes = self.index(ids)
            
        if comparison_ids is None:
            comparison_indexes = indexes
        else:
            comparison_indexes = self.index(comparison_ids)

        if len(self) > 2000 and len(indexes) < 2000 and len(comparison_indexes) < 2000:
            # Just compute the requested distances
            if metric == "euclidean":
                return euclidean_distances(self.field(Field.POSITION, indexes),
                                           self.field(Field.POSITION, comparison_indexes))
            elif metric == "cosine":
                return cosine_distances(self.field(Field.POSITION, indexes),
                                        self.field(Field.POSITION, comparison_indexes))
            elif metric == "precomputed":
                return self.field(Field.POSITION, indexes)
            else:
                raise NotImplementedError("Unsupported metric for distances")
        else:
            # Cache all pairwise distances
            if metric not in self._distances:
                locations = self.field(Field.POSITION)
                if metric == "euclidean":
                    self._distances[metric] = euclidean_distances(locations, locations)
                elif metric == "cosine":
                    self._distances[metric] = cosine_distances(locations, locations)
                elif metric == "precomputed":
                    self._distances[metric] = locations
                else:
                    raise NotImplementedError("Unsupported metric for distances")
        
            return self._distances[metric][indexes,:][:,comparison_indexes]

    def within_bbox(self, bbox):
        """
        Returns the list of IDs whose points are within the given bounding box,
        where bbox is specified as (xmin, xmax, ymin, ymax). Only supports
        2D embeddings.
        """
        assert self.dimension() == 2, "Non-2D embeddings are not supported by within_bbox()"
        positions = self.field(Field.POSITION)
        return [id_val for id_val, pos in zip(self.ids, positions)
                if (pos[0] >= bbox[0] and pos[0] <= bbox[1] and
                    pos[1] >= bbox[2] and pos[1] <= bbox[3])]

    def to_json(self, compressed=True, save_neighbors=True, num_neighbors=None):
        """
        Converts this embedding into a JSON object. If the embedding is 2D, saves
        coordinates as separate x and y fields; otherwise, saves coordinates as
        n x d arrays.
        
        compressed: whether to format JSON objects using base64 strings
            instead of as human-readable float arrays
        """
        result = {}
        indexes = self.index(self.ids)
        
        positions = self.field(Field.POSITION)
        colors = self.field(Field.COLOR)
        alphas = self.field(Field.ALPHA)
        sizes = self.field(Field.RADIUS)
        
        if compressed:
            result["_format"] = "compressed"
            # Specify the type name that will be used to encode the point IDs.
            # This is important because the highlight array takes up the bulk
            # of the space when transferring to file/widget.
            dtype, type_name = choose_integer_type(self.ids)
            result["_idtype"] = type_name
            result["_length"] = len(self)
            result["ids"] = encode_numerical_array(self.ids, dtype)
            
            if self.dimension() == 2:
                result["x"] = encode_numerical_array(positions[:,0])
                result["y"] = encode_numerical_array(positions[:,1])
            else:
                result["position"] = encode_numerical_array(positions, interval=self.dimension())
                
            result["color"] = encode_object_array(colors)
            if alphas is not None:
                result["alpha"] = encode_numerical_array(alphas)
            if sizes is not None:
                result["r"] = encode_numerical_array(sizes)
        else:
            result["points"] = {}
            for id_val, index in zip(self.ids, indexes):
                obj = {}
                if self.dimension() == 2:
                    obj["x"] = positions[index, 0]
                    obj["y"] = positions[index, 1]
                else:
                    obj["position"] = positions[index].tolist()

                obj["color"] = colors[index]
                if alphas is not None:
                    obj["alpha"] = alphas[index]
                if sizes is not None:
                    obj["r"] = sizes[index]
                result["points"][id_val] = obj

        if save_neighbors and self.has_neighbors():
            result["neighbors"] = self.get_neighbors().to_json(compressed=compressed, num_neighbors=num_neighbors)
        result["metric"] = self.metric
        result["n_neighbors"] = self.n_neighbors
        return standardize_json(result)
    
    @classmethod
    def from_json(cls, data, label=None, parent=None):
        """
        Builds an Embedding object from the given JSON object.
        """
        mats = {}
        if data.get("_format", "expanded") == "compressed":
            dtype = np.dtype(data["_idtype"])
            ids = decode_numerical_array(data["ids"], dtype)
            
            if "position" in data:
                mats[Field.POSITION] = decode_numerical_array(data["position"])
            else:
                mats[Field.POSITION] = np.hstack([
                    decode_numerical_array(data["x"]).reshape(-1, 1),
                    decode_numerical_array(data["y"]).reshape(-1, 1),
                ])

            mats[Field.COLOR] = np.array(decode_object_array(data["color"]))
            if "alpha" in data:
                mats[Field.ALPHA] = decode_numerical_array(data["alpha"])
            if "r" in data:
                mats[Field.RADIUS] = decode_numerical_array(data["r"])
        else:
            point_data = data["points"]
            try:
                ids = [int(id_val) for id_val in list(point_data.keys())]
                point_data = {int(k): v for k, v in point_data.items()}
            except:
                ids = list(point_data.keys())
            ids = sorted(ids)
            
            try:
                mats[Field.POSITION] = np.array([point_data[id_val]["position"] for id_val in ids])
            except KeyError:   
                mats[Field.POSITION] = np.array([[point_data[id_val]["x"], point_data[id_val]["y"]] for id_val in ids])

            mats[Field.COLOR] = np.array([point_data[id_val]["color"] for id_val in ids])
            if "alpha" in data[ids[0]]:
                mats[Field.ALPHA] = np.array([point_data[id_val]["alpha"] for id_val in ids])
            if "r" in data[ids[0]]:
                mats[Field.RADIUS] = np.array([point_data[id_val]["r"] for id_val in ids])

        if "neighbors" in data:
            neighbors = Neighbors.from_json(data["neighbors"])
        else:
            neighbors = None
        metric = data.get("metric", "euclidean")
        n_neighbors = data.get("n_neighbors", 100)
        return cls(mats, ids=ids, label=label, metric=metric, n_neighbors=n_neighbors, neighbors=neighbors, parent=parent)
    
    def save(self, file_path_or_buffer, **kwargs):
        """
        Save this Embedding object to the given file path or file-like object
        (in JSON format).
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'w') as file:
                json.dump(self.to_json(**kwargs), file)
        else:
            # File object
            json.dump(self.to_json(**kwargs), file_path_or_buffer)
            
    @classmethod
    def load(cls, file_path_or_buffer, **kwargs):
        """
        Load the Embedding object from the given file path or
        file-like object containing JSON data.
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'r') as file:
                return cls.from_json(json.load(file), **kwargs)
        else:
            # File object
            return cls.from_json(json.load(file_path_or_buffer), **kwargs)
        
    def align_to(self, base_frame, ids=None, return_transform=False, base_transform=None, allow_flips=True):
        """
        Aligns this embedding to the base frame. The frames are aligned based
        on the keys they have in common. This requires both embeddings to have
        a dimensionality of 2.
        
        Args:
            base_frame: An Embedding to use as the base.
            frame: An Embedding to transform.
            ids: Point IDs to use for alignment (default None, which results in an
                alignment using the intersection of IDs between the two frames).
            return_transform: If true, return just the Affine object instead of the
                rotated data.
            base_transform: If not None, an Affine object representing the
                transformation to apply to the base frame before aligning.
            allow_flips: If true, test inversions as possible candidates for alignment.
            
        Returns:
            A new Embedding object representing the second input frame (the first
            input frame is assumed to stay the same). Or, if return_transform is
            True, returns the optimal transformation as an Affine object.
        """
        # Determine a set of points to use for comparison
        ids_to_compare = list(ids) if ids is not None else list(set(self.ids) & set(base_frame.ids))
        
        proj_subset = self.field(Field.POSITION, ids=ids_to_compare)
        assert proj_subset.shape[1] == 2, "Alignment of embeddings with dimension > 2 not supported"
        proj_scaler = projection_standardizer(proj_subset)
        
        base_proj_subset = base_frame.field(Field.POSITION, ids=ids_to_compare)
        assert base_proj_subset.shape[1] == 2, "Alignment of embeddings with dimension > 2 not supported"
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
                        self.field(Field.POSITION))

        if return_transform:
            return best_variant
        return self.copy_with_fields({Field.POSITION: best_variant})

class NeighborOnlyEmbedding(Embedding):
    """
    An Embedding object that contains no point locations, just neighbor IDs.
    """
    def __init__(self, neighbors, label=None, metric='euclidean', n_neighbors=100, parent=None):
        super().__init__({Field.POSITION: np.zeros((len(neighbors), 1)),
                          Field.COLOR: np.zeros((len(neighbors), 1))},
                          neighbors.ids,
                          label=label,
                          metric=metric,
                          n_neighbors=n_neighbors,
                          neighbors=neighbors,
                          parent=parent)

    @staticmethod
    def from_embedding(emb):
        """
        Creates a NeighborOnlyEmbedding that mocks an existing embedding, but
        contains only its neighbor set with no positions or color data.
        """
        return NeighborOnlyEmbedding(emb.get_neighbors(),
                                     metric=emb.metric,
                                     n_neighbors=emb.n_neighbors)
    
    def copy(self):
        return NeighborOnlyEmbedding(self.neighbors,
                                    label=self.label,
                                    metric=self.metric,
                                    n_neighbors=self.n_neighbors,
                                    parent=self)
    
    def concat(self, other):
        """
        Returns a new Embedding with this Embedding and the given one
        stacked together. Must have the same set of fields, and a disjoint set of
        IDs.
        """
        assert isinstance(other, NeighborOnlyEmbedding), "Cannot concatenate non-neighbor-only to neighbor-only Embedding"
        assert not (set(self.ids.tolist()) & set(other.ids.tolist())), "Cannot concatenate Embedding objects with overlapping ID values"
        assert self.has_neighbors() and other.has_neighbors(), "Both NeighborOnlyEmbedding objects must have a Neighbors"
        
        return NeighborOnlyEmbedding(self.get_neighbors().concat(other.get_neighbors()),
                                     n_neighbors=max(self.n_neighbors, other.n_neighbors),
                                     label=self.label, metric=self.metric)
    
    def project(self, method=ProjectionTechnique.UMAP, **params):
        raise NotImplementedError
    
    def compute_neighbors(self, n_neighbors=None, metric=None):
        raise NotImplementedError
        
    def clear_neighbors(self):
        self.neighbors = None
         
    def neighbor_distances(self, ids=None, n_neighbors=100, metric=None):
        raise NotImplementedError
        
    def distances(self, ids=None, comparison_ids=None, metric=None):
        raise NotImplementedError

    def within_bbox(self, bbox):
        raise NotImplementedError

    def to_json(self, compressed=True, save_neighbors=True, num_neighbors=None):
        """
        Converts this embedding into a (neighbor-only) JSON object.
        
        compressed: whether to format JSON objects using base64 strings
            instead of as human-readable float arrays
        """
        result = {}
        result["_format"] = "neighbor_only"
        
        if save_neighbors and self.has_neighbors():
            result["neighbors"] = self.get_neighbors().to_json(compressed=compressed, num_neighbors=num_neighbors)
        result["metric"] = self.metric
        result["n_neighbors"] = self.n_neighbors
        return standardize_json(result)
    
    @classmethod
    def from_json(cls, data, label=None, parent=None):
        """
        Builds a neighbor-only Embedding object from the given JSON object.
        """
        format = data.get("_format", "expanded")
        if format != "neighbor_only":
            raise ValueError("Cannot load NeighborOnlyEmbedding from JSON with format '{}'".format(data))
        
        assert "neighbors" in data
        neighbors = Neighbors.from_json(data["neighbors"])
        metric = data.get("metric", "euclidean")
        n_neighbors = data.get("n_neighbors", 100)
        return cls(neighbors, label=label, metric=metric, n_neighbors=n_neighbors, parent=parent)
    
    def align_to(self, base_frame, ids=None, return_transform=False, base_transform=None, allow_flips=True):
        raise NotImplementedError
    
class EmbeddingSet:
    """
    A set of high-dimensional embeddings, composed of a series of Embedding
    objects.
    """
    def __init__(self, embs, align=True):
        if align:
            if not all(emb.dimension() == 2 for emb in embs):
                print("Embeddings are not 2D, skipping alignment")
                self.embeddings = embs
            else:
                self.embeddings = [embs[0]] + [emb.align_to(embs[0]) for emb in embs[1:]]
        else:
            self.embeddings = embs

        self.ids = np.array(sorted(set.union(*(set(emb.ids.tolist()) for emb in self.embeddings))))
    
    def __str__(self):
        return "<{} with {} embeddings:\n\t{}>".format(
            type(self).__name__,
            len(self.embeddings),
            "\n\t".join(str(emb) for emb in self.embeddings)
        )
        
    def __repr__(self):
        return str(self)
        
    def __getitem__(self, idx):
        return self.embeddings[idx]

    def __len__(self):
        return len(self.embeddings)
    
    def identical(self):
        if len(self) == 0: return True
        return all(e == self[0] for e in self.embeddings)
    
    def project(self, method=ProjectionTechnique.ALIGNED_UMAP, align=True, **params):
        """
        Projects the embedding set into 2D. The method parameter can be a
        callable, which will define a dimensionality reduction technique that
        takes as input a list of numpy arrays and a list of lists of IDs, as
        well as any keyword arguments given to the params argument of this
        method, and returns a list of dimension-reduced arrays.
        
        Returns: A new EmbeddingSet object with (optionally aligned) projected
            data.
        """
        params = params or {}
        hi_ds = [emb.field(Field.POSITION) for emb in self.embeddings]
        id_sets = [emb.ids for emb in self.embeddings]
        pre_aligned = False
        if method == ProjectionTechnique.ALIGNED_UMAP:
            import umap
            lo_d_mats = umap.AlignedUMAP(**params).fit_transform(
                hi_ds,
                relations=[self.embeddings[i].get_relations(self.embeddings[i + 1])
                            for i in range(len(self.embeddings) - 1)])
            pre_aligned = True
            lo_ds = [emb.copy_with_fields({Field.POSITION: lo_d}, clear_neighbors=True)
                     for emb, lo_d in zip(self.embeddings, lo_d_mats)]
        elif callable(method):
            lo_d_mats = method(hi_ds, id_sets, **params)
            lo_ds = [emb.copy_with_fields({Field.POSITION: lo_d}, clear_neighbors=True)
                     for emb, lo_d in zip(self.embeddings, lo_d_mats)]
        else:
            lo_ds = [emb.project(method=method, **params)
                     for emb in self.embeddings]

        return EmbeddingSet(lo_ds, align=align and not pre_aligned)
    
    def compute_neighbors(self, n_neighbors=100, metric=None):
        """
        Computes and saves a set of nearest neighbors in each embedding set according
        to the Field.POSITION values. This can be accessed after completing this
        step by inspecting the neighbors property of the embedding.
        """
        for emb in self.embeddings:
            emb.compute_neighbors(n_neighbors=n_neighbors, metric=metric)

    def clear_neighbors(self):
        """
        Removes the saved Neighbors associated with this Embedding. This can
        be used to determine which Neighbors is returned by get_ancestor_neighbors().
        """
        for emb in self.embeddings:
            emb.clear_neighbors()
                
    def get_neighbors(self):
        """
        Returns a NeighborSet object corresponding to the nearest neighbors
        of each embedding in the EmbeddingSet.
        """
        return NeighborSet([emb.get_neighbors() for emb in self.embeddings])

    def get_recent_neighbors(self):
        """
        Returns a NeighborSet containing ancestor Neighbors for each embedding in the
        EmbeddingSet. This corresponds to the lowest-level Embedding in each
        Embedding's parent tree (including the Embedding itself) that has a
        neighbor set associated with it.
        """
        return NeighborSet([emb.get_recent_neighbors() for emb in self.embeddings])
                
    def get_ancestor_neighbors(self):
        """
        Returns a NeighborSet containing ancestor Neighbors for each embedding in the
        EmbeddingSet. This corresponds to the highest-level Embedding in each
        Embedding's parent tree that has a neighbor set associated with it.
        """
        return NeighborSet([emb.get_ancestor_neighbors() for emb in self.embeddings])
            
    def to_json(self, compressed=True, save_neighbors=True, num_neighbors=None):
        """
        Converts this set of embeddings into a JSON object.
        
        compressed: whether to format Embedding JSON objects using base64 strings
            instead of as human-readable float arrays
        save_neighbors: If True, save the Neighbors into the "neighbors" key
            of each individual embedding
        num_neighbors: number of neighbors to write for each point (can considerably
            save memory)
        """
        return {
            "data": [emb.to_json(compressed=compressed,
                                 save_neighbors=save_neighbors,
                                 num_neighbors=num_neighbors) for emb in self.embeddings],
            "frameLabels": [emb.label or "Frame {}".format(i) for i, emb in enumerate(self.embeddings)]
        }

    @classmethod
    def from_json(cls, data, parents=None):
        """
        Builds an EmbeddingSet from a JSON object. The provided object should
        contain a "data" field containing frames, and optionally a "frameLabels"
        field containing a list of string names for each field.
        """
        assert "data" in data, "JSON object must contain a 'data' field"
        embs = data["data"]
        labels = data.get("frameLabels", [None for _ in range(len(embs))])
        if parents is None:
            parents = [None for _ in range(len(embs))]
        elif len(parents) == 1:
            parents = [parents[0] for _ in range(len(embs))]
        embs = [Embedding.from_json(frame, label=label, parent=parent) for frame, label, parent in zip(embs, labels, parents)]
        return cls(embs, align=False)
    
    def save(self, file_path_or_buffer, **kwargs):
        """
        Save this EmbeddingSet object to the given file path or file-like object
        (in JSON format).
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'w') as file:
                json.dump(self.to_json(**kwargs), file)
        else:
            # File object
            json.dump(self.to_json(**kwargs), file_path_or_buffer)
            
    @classmethod
    def load(cls, file_path_or_buffer, **kwargs):
        """
        Load the EmbeddingSet object from the given file path or
        file-like object containing JSON data.
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'r') as file:
                return cls.from_json(json.load(file), **kwargs)
        else:
            # File object
            return cls.from_json(json.load(file_path_or_buffer), **kwargs)
        