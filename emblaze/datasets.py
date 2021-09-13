import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_distances, euclidean_distances
from sklearn.neighbors import NearestNeighbors
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from scipy.spatial.transform import Rotation
from affine import Affine
from .utils import *
    
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
            return self.data[field][ids]
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
    def __init__(self, data, ids=None, label=None, metric='euclidean', parent=None):
        super().__init__(data, ids)
        assert Field.POSITION in data, "Field.POSITION is required"
        assert Field.COLOR in data, "Field.COLOR is required"
        self.label = label
        self.metric = metric
        self._distances = {}
        self.parent = parent # keep track of where this embedding came from

    def copy(self):
        return Embedding(self.data, self.ids, label=self.label, metric=self.metric, parent=self)
    
    def concat(self, other):
        """
        Returns a new Embedding with this Embedding and the given one
        stacked together. Must have the same set of fields, and a disjoint set of
        IDs.
        """
        assert set(self.data.keys()) == set(other.data.keys()), "Cannot concatenate Embedding objects with different sets of fields"
        assert not (set(self.ids.tolist()) & set(other.ids.tolist())), "Cannot concatenate Embedding objects with overlapping ID values"
        
        return Embedding({k: np.concatenate([self.field(k), other.field(k)])
                          for k in self.data.keys()},
                         ids=np.concatenate([self.ids, other.ids]),
                         label=self.label, metric=self.metric)
    
    def get_root(self):
        """Returns the root parent of this embedding."""
        if self.parent is None: return self
        return self.parent.get_root()
    
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
        
        return self.copy_with_fields({Field.POSITION: lo_d})
    
    def get_relations(self, other_emb):
        """
        Computes a mapping from the IDs in this embedding to the positions
        in the other embedding (used for AlignedUMAP).
        """
        return {self.index(id_val): other_emb.index(id_val)
                for id_val in self.ids if id_val in other_emb}
    
    def compute_neighbors(self, n_neighbors=100, metric=None):
        """
        Computes and saves a set of nearest neighbors in this embedding according
        to the Field.POSITION values. This can be accessed after completing this
        step by calling .field(Field.NEIGHBORS). If the metric is not provided,
        the default metric for this Embedding object is used.
        """
        pos = self.field(Field.POSITION)
        neighbor_clf = NearestNeighbors(metric=metric or self.metric,
                                        n_neighbors=n_neighbors + 1).fit(pos)
        _, neigh_indexes = neighbor_clf.kneighbors(pos)
        self.set_field(Field.NEIGHBORS, neigh_indexes[:,1:])
        
    def neighbor_distances(self, ids=None, n_neighbors=100, metric=None):
        """
        Returns the list of nearest neighbors for each of the given IDs and the
        distances to each of those points.
        """
        pos = self.field(Field.POSITION, ids=ids)
        neighbor_clf = NearestNeighbors(metric=metric or self.metric).fit(self.field(Field.POSITION))
        neigh_distances, neigh_indexes = neighbor_clf.kneighbors(pos, n_neighbors=n_neighbors + 1)
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

    def to_json(self, compressed=True, num_neighbors=None):
        """
        Converts this embedding into a JSON object. Requires that the embedding
        have an n x 2 array at the Field.POSITION key.
        
        compressed: whether to format JSON objects using base64 strings
            instead of as human-readable float arrays
        num_neighbors: number of neighbors to write for each point (can considerably
            save memory)
        """
        assert self.dimension() == 2, "Non-2D embeddings are not supported by to_json()"
        result = {}
        indexes = self.index(self.ids)
        
        positions = self.field(Field.POSITION)
        colors = self.field(Field.COLOR)
        alphas = self.field(Field.ALPHA)
        sizes = self.field(Field.RADIUS)
        neighbors = self.field(Field.NEIGHBORS)
        if neighbors is None:
            print("Warning: The embedding has no computed nearest neighbors, so none will be displayed. You may want to call compute_neighbors() to generate them.")
        elif num_neighbors is not None:
            neighbors = neighbors[:,:min(num_neighbors, neighbors.shape[1])]
        
        if compressed:
            result["_format"] = "compressed"
            # Specify the type name that will be used to encode the point IDs.
            # This is important because the highlight array takes up the bulk
            # of the space when transferring to file/widget.
            dtype, type_name = choose_integer_type(self.ids)
            result["_idtype"] = type_name
            result["_length"] = len(self)
            result["ids"] = encode_numerical_array(self.ids, dtype)
            
            result["x"] = encode_numerical_array(positions[:,0])
            result["y"] = encode_numerical_array(positions[:,1])
            result["color"] = encode_object_array(colors)
            if alphas is not None:
                result["alpha"] = encode_numerical_array(alphas)
            if sizes is not None:
                result["r"] = encode_numerical_array(sizes)
            if neighbors is not None:
                result["highlight"] = encode_numerical_array(neighbors.flatten(),
                                                             astype=dtype,
                                                             interval=neighbors.shape[1])
        else:
            for id_val, index in zip(self.ids, indexes):
                obj = {
                    "x": positions[index, 0],
                    "y": positions[index, 1],
                    "color": colors[index]
                }
                if alphas is not None:
                    obj["alpha"] = alphas[index]
                if sizes is not None:
                    obj["r"] = sizes[index]
                if neighbors is not None:
                    obj["highlight"] = neighbors[index].tolist()
                else:
                    obj["highlight"] = []
                result[id_val] = obj
        
        return standardize_json(result)
    
    @staticmethod
    def from_json(data, label=None, metric='euclidean', parent=None):
        """
        Builds a 2-dimensional Embedding object from the given JSON object.
        """
        mats = {}
        if data.get("_format", "expanded") == "compressed":
            dtype = np.dtype(data["_idtype"])
            ids = decode_numerical_array(data["ids"], dtype)
            mats[Field.POSITION] = np.hstack([
                decode_numerical_array(data["x"]).reshape(-1, 1),
                decode_numerical_array(data["y"]).reshape(-1, 1),
            ])
            mats[Field.COLOR] = np.array(decode_object_array(data["color"]))
            if "alpha" in data:
                mats[Field.ALPHA] = decode_numerical_array(data["alpha"])
            if "r" in data:
                mats[Field.RADIUS] = decode_numerical_array(data["r"])
            if "highlight" in data:
                mats[Field.NEIGHBORS] = decode_numerical_array(data["highlight"], dtype)
        else:
            try:
                ids = [int(id_val) for id_val in list(data.keys())]
                data = {int(k): v for k, v in data.items()}
            except:
                ids = list(data.keys())
            ids = sorted(ids)
            
            mats[Field.POSITION] = np.array([[data[id_val]["x"], data[id_val]["y"]] for id_val in ids])
            mats[Field.COLOR] = np.array([data[id_val]["color"] for id_val in ids])
            if "alpha" in data[ids[0]]:
                mats[Field.ALPHA] = np.array([data[id_val]["alpha"] for id_val in ids])
            if "r" in data[ids[0]]:
                mats[Field.RADIUS] = np.array([data[id_val]["r"] for id_val in ids])
            if "highlight" in data[ids[0]]:
                mats[Field.NEIGHBORS] = np.array([data[id_val]["highlight"] for id_val in ids])
                
        return Embedding(mats, ids=ids, label=label, metric=metric, parent=parent)
    
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
            lo_ds = [emb.copy_with_fields({Field.POSITION: lo_d})
                     for emb, lo_d in zip(self.embeddings, lo_d_mats)]
        elif callable(method):
            lo_d_mats = method(hi_ds, id_sets, **params)
            lo_ds = [emb.copy_with_fields({Field.POSITION: lo_d})
                     for emb, lo_d in zip(self.embeddings, lo_d_mats)]
        else:
            lo_ds = [emb.project(method=method, **params)
                     for emb in self.embeddings]

        return EmbeddingSet(lo_ds, align=align and not pre_aligned)
    
    def compute_neighbors(self, n_neighbors=100, metric=None):
        """
        Computes and saves a set of nearest neighbors in each embedding set according
        to the Field.POSITION values. This can be accessed after completing this
        step by calling .field(Field.NEIGHBORS).
        """
        for emb in self.embeddings:
            emb.compute_neighbors(n_neighbors=n_neighbors, metric=metric)

    def to_json(self, compressed=True, num_neighbors=None):
        """
        Converts this set of embeddings into a JSON object.
        
        compressed: whether to format Embedding JSON objects using base64 strings
            instead of as human-readable float arrays
        num_neighbors: number of neighbors to write for each point (can considerably
            save memory)
        """
        return {
            "data": [emb.to_json(compressed=compressed, num_neighbors=num_neighbors) for emb in self.embeddings],
            "frameLabels": [emb.label or "Frame {}".format(i) for i, emb in enumerate(self.embeddings)]
        }

    @staticmethod
    def from_json(data, metric='euclidean'):
        """
        Builds an EmbeddingSet from a JSON object. The provided object should
        contain a "data" field containing frames, and optionally a "frameLabels"
        field containing a list of string names for each field.
        """
        assert "data" in data, "JSON object must contain a 'data' field"
        labels = data.get("frameLabels", [None for _ in range(len(data["data"]))])
        embs = [Embedding.from_json(frame, label=label, metric=metric) for frame, label in zip(data["data"], labels)]
        return EmbeddingSet(embs, align=False)