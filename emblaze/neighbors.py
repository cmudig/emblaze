import numpy as np
from sklearn.neighbors import NearestNeighbors
from .utils import *

class Neighbors:
    """
    An object representing a serializable set of nearest neighbors within an
    embedding. The Neighbors object simply stores a matrix of integer IDs, where rows
    correspond to points in the embedding and columns are IDs of neighbors in
    order of proximity to each point.
    """
    def __init__(self, values, ids=None, metric='euclidean', n_neighbors=100, clf=None):
        """
        pos: Matrix of n x D vectors indicating high-dimensional positions
        ids: If supplied, a list of IDs for the points in the matrix
        """
        super().__init__()
        self.values = values
        self.ids = ids
        self._id_index = {id: i for i, id in enumerate(self.ids)}
        self.metric = metric
        self.n_neighbors = n_neighbors
        self.clf = clf
    
    @classmethod
    def compute(cls, pos, ids=None, metric='euclidean', n_neighbors=100):
        ids = ids if ids is not None else np.arange(len(pos))
        neighbor_clf = NearestNeighbors(metric=metric,
                                        n_neighbors=n_neighbors + 1).fit(pos)
        _, neigh_indexes = neighbor_clf.kneighbors(pos)
        
        return cls(ids[neigh_indexes[:,1:]], ids=ids, metric=metric, n_neighbors=n_neighbors, clf=neighbor_clf)
        
    def index(self, id_vals):
        """
        Returns the index(es) of the given IDs.
        """
        if isinstance(id_vals, (list, np.ndarray, set)):
            return [self._id_index[int(id_val)] for id_val in id_vals]
        else:
            return self._id_index[int(id_vals)]

    def __getitem__(self, ids):
        """ids can be a single ID or a sequence of IDs"""
        if ids is None: return self.values
        return self.values[self.index(ids)]
    
    def __eq__(self, other):
        if isinstance(other, NeighborSet): return other == self
        if not isinstance(other, Neighbors): return False
        return np.allclose(self.ids, other.ids) and np.allclose(self.values, other.values)
    
    def __ne__(self, other):
        return not (self == other)
        
    def __len__(self):
        return len(self.values)
    
    def calculate_neighbors(self, pos, return_distance=True, n_neighbors=None):
        if self.clf is None:
            raise ValueError(
                ("Cannot compute neighbors because the Neighbors was not "
                 "initialized with a neighbor classifier - was it deserialized "
                 "from JSON without saving the original coordinates or "
                 "concatenated to another Neighbors?"))
        neigh_dists, neigh_indexes = self.clf.kneighbors(pos, n_neighbors=n_neighbors or self.n_neighbors)
        if return_distance:
            return neigh_dists, neigh_indexes
        return neigh_indexes
    
    def concat(self, other):
        """Concatenates the two Neighbors together, discarding the original 
        classifier."""
        assert not (set(self.ids.tolist()) & set(other.ids.tolist())), "Cannot concatenate Neighbors objects with overlapping ID values"
        assert self.metric == other.metric, "Cannot concatenate Neighbors objects with different metrics"
        return Neighbors(
            np.concatenate(self.values, other.values),
            ids=np.concatenate(self.ids, other.ids),
            metric=self.metric,
            n_neighbors = max(self.n_neighbors, other.n_neighbors)
        )
    
    def to_json(self, compressed=True, num_neighbors=None):
        """Serializes the neighbors to a JSON object."""
        result = {}
        result["metric"] = self.metric
        result["n_neighbors"] = self.n_neighbors
        
        neighbors = self.values
        if num_neighbors is not None:
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
            
            result["neighbors"] = encode_numerical_array(neighbors.flatten(),
                                                            astype=dtype,
                                                            interval=neighbors.shape[1])
        else:
            result["_format"] = "expanded"
            result["neighbors"] = {}
            indexes = self.index(self.ids)
            for id_val, index in zip(self.ids, indexes):
                result["neighbors"][id_val] = neighbors[index].tolist()
        return result
    
    @classmethod
    def from_json(cls, data):
        if data.get("_format", "expanded") == "compressed":
            dtype = np.dtype(data["_idtype"])
            ids = decode_numerical_array(data["ids"], dtype)
            neighbors = decode_numerical_array(data["neighbors"], dtype)
        else:
            neighbor_dict = data["neighbors"]
            try:
                ids = [int(id_val) for id_val in list(neighbor_dict.keys())]
                neighbor_dict = {int(k): v for k, v in neighbor_dict.items()}
            except:
                ids = list(neighbor_dict.keys())
            ids = sorted(ids)
            neighbors = np.array([neighbor_dict[id_val] for id_val in ids])
                
        return cls(neighbors, ids=ids, metric=data["metric"], n_neighbors=data["n_neighbors"])

class NeighborSet:
    """
    An object representing a serializable collection of Neighbors objects.
    """
    def __init__(self, neighbor_objects):
        super().__init__()
        self._neighbors = neighbor_objects
        
    def __getitem__(self, slice):
        return self._neighbors[slice]
    
    def __setitem__(self, slice, val):
        self._neighbors[slice] = val
        
    def __len__(self):
        return len(self._neighbors)
    
    def __iter__(self):
        return iter(self._neighbors)
    
    def __eq__(self, other):
        if isinstance(other, NeighborSet):
            return len(other) == len(self) and all(n1 == n2 for n1, n2 in zip(self, other))
        elif isinstance(other, Neighbors):
            return all(n1 == other for n1 in self)
        return False
    
    def __ne__(self, other):
        return not (self == other)
    
    def to_json(self, compressed=True, num_neighbors=None):
        """
        Serializes the list of Neighbors objects to JSON.
        """
        return [n.to_json(compressed=compressed, num_neighbors=num_neighbors)
                for n in self]
        
    @classmethod
    def from_json(cls, data):
        return [Neighbors.from_json(d) for d in data]
    
    def identical(self):
        """Returns True if all Neighbors objects within this NeighborSet are equal to each other."""
        if len(self) == 0: return True
        return all(n == self[0] for n in self)