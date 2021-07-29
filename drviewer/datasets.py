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
        self.ids = ids if ids is not None else np.arange(length)
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
        
    def distances(self, ids=None, comparison_ids=None, metric=None):
        """
        Returns the pairwise distances from the given IDs to each other (or all
        points to each other, if ids is None). If the metric is not provided,
        the default metric for this Embedding object is used.
        """
        metric = metric or self.metric
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
        
        if ids is None:
            indexes = np.arange(len(self))
        else:
            indexes = self.index(ids)
            
        if comparison_ids is None:
            comparison_indexes = indexes
        else:
            comparison_indexes = self.index(comparison_ids)

        return self._distances[metric][indexes,:][:,comparison_indexes]

    def to_json(self):
        """
        Converts this embedding into a JSON object. Requires that the embedding
        have an n x 2 array at the Field.POSITION key.
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
        
        return result
    
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

    def to_json(self):
        """
        Converts this set of embeddings into a JSON object.
        """
        return {
            "data": [emb.to_json() for emb in self.embeddings],
            "frameLabels": [emb.label or "Frame {}".format(i) for i, emb in enumerate(self.embeddings)]
        }
