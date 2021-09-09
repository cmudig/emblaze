import numpy as np
from sklearn.cluster import AgglomerativeClustering
from .utils import Field, inverse_intersection
from numba.typed import List
from scipy.sparse import csr_matrix
import collections

NUM_NEIGHBORS_FOR_SEARCH = 10

class SelectionRecommender:
    """
    Generates recommended selections based on a variety of inputs. The
    recommender works by pre-generating a list of clusters at various
    granularities, then sorting them by relevance to a given query.
    """
    def __init__(self, embeddings, progress_fn=None, frame_idx=None, preview_frame_idx=None, filter_points=None):
        super().__init__()
        self.embeddings = embeddings
        self.clusters = {}
        embs_first = [frame_idx] if frame_idx is not None else range(len(self.embeddings))
        embs_second = [preview_frame_idx] if preview_frame_idx is not None else range(len(self.embeddings))
        total_num_embs = sum(1 for x in embs_first for y in embs_second if x != y)
        for i in embs_first:
            for j in embs_second:
                if i == j: continue
                self.clusters[(i, j)] = self._make_clusters(i, j, np.log10(len(self.embeddings[i])), filter_points=filter_points)
                if progress_fn is not None:
                    progress_fn(len(self.clusters) / total_num_embs)
        
    def _make_neighbor_mat(self, neighbors, num_columns):
        """Converts a list of neighbor indexes into a one-hot encoded matrix."""
        neighbor_mat = np.zeros((len(neighbors), num_columns + 1), dtype=np.uint8)
        if isinstance(neighbors, list):
            max_len = max(len(n) for n in neighbors)
            neighbors_padded = -np.ones((len(neighbors), max_len), dtype=int)
            for i, n in enumerate(neighbors):
                neighbors_padded[i,:len(n)] = list(n)
            neighbors = neighbors_padded

        for i in range(neighbors.shape[1]):
            neighbor_mat[np.arange(len(neighbors)), neighbors[:,i] + 1] = 1
        return csr_matrix(neighbor_mat[:,1:])

    def _pairwise_jaccard_distances(self, neighbors):
        """Computes the jaccard distance between each row of the given set of neighbors."""
        # Make a one-hot matrix of neighbors
        neighbor_mat = self._make_neighbor_mat(neighbors, max(np.max([n for x in neighbors for n in x]) + 1, len(neighbors)))
        # Calculate intersection of sets using dot product
        intersection = np.dot(neighbor_mat, neighbor_mat.T)
        del neighbor_mat
        
        # Use set trick: len(x | y) = len(x) + len(y) - len(x & y)
        lengths = np.array([len(n) for n in neighbors], dtype=np.uint16)
        length_sums = lengths[:,np.newaxis] + lengths[np.newaxis,:]
        union = np.maximum(length_sums - intersection, np.array([1], dtype=np.uint16), casting='no')
        del length_sums
        result = np.zeros((len(neighbors), len(neighbors)), dtype=np.float16)
        np.true_divide(intersection.todense(), union, out=result)
        return np.array([1.0], dtype=np.float16) - result

    def _make_neighbor_changes(self, idx_1, idx_2, filter_points=None):
        """
        Computes the sets of gained IDs and lost IDs for the given pair of frames.
        """
        frame_1 = self.embeddings[idx_1]
        frame_2 = self.embeddings[idx_2]
        frame_1_neighbors = frame_1.field(Field.NEIGHBORS, ids=filter_points or None)
        frame_2_neighbors = frame_2.field(Field.NEIGHBORS, ids=filter_points or None)
        gained_ids = [set(frame_2_neighbors[i]) - set(frame_1_neighbors[i]) for i in range(len(filter_points or frame_1))]
        lost_ids = [set(frame_1_neighbors[i]) - set(frame_2_neighbors[i]) for i in range(len(filter_points or frame_1))]

        return gained_ids, lost_ids
        
    def _consistency_score(self, ids, frame):
        """
        Computes the consistency between the neighbors for the given set of IDs 
        in the given frame.
        """
        return (np.sum(1 - self._pairwise_jaccard_distances(frame.field(Field.NEIGHBORS, ids=ids))) - len(ids)) / (len(ids) * (len(ids) - 1))
        
    def _inner_change_score(self, ids, frame_1, frame_2):
        """
        Computes the inverse intersection of the neighbor sets in the given
        two frames.
        """
        return np.mean(inverse_intersection(frame_1.field(Field.NEIGHBORS, ids=ids),
                                            frame_2.field(Field.NEIGHBORS, ids=ids),
                                            List(ids),
                                            False))
        
    def _change_score(self, change_set, ids, num_neighbors=10):
        """
        Computes a score estimating the consistency in the changes for the given
        set of IDs
        """
        counter = collections.Counter([x for s in change_set for x in s if x not in ids])
        return np.mean([x[1] / len(ids) for x in sorted(counter.items(), key=lambda x: x[1], reverse=True)[:num_neighbors]])
        
    def _make_clusters(self, idx_1, idx_2, min_cluster_size=1, filter_points=None):
        """
        Produces clusters based on the pairwise distances between the given pair of frames.
        """
        filter_points = list(filter_points) if filter_points is not None else None
        all_ids = np.array(filter_points) if filter_points is not None else self.embeddings[idx_1].ids
        
        gained_ids, lost_ids = self._make_neighbor_changes(idx_1, idx_2, filter_points=filter_points)
        distances = (self._pairwise_jaccard_distances(gained_ids) + self._pairwise_jaccard_distances(lost_ids)) / 2
        clusters = []
        
        for threshold in np.arange(0.7, 0.91, 0.1):
            clusterer = AgglomerativeClustering(n_clusters=None,
                                                distance_threshold=threshold,
                                                affinity='precomputed',
                                                linkage='average')
            clusterer.fit(distances)
            cluster_labels = clusterer.labels_
            
            for label, count in zip(*np.unique(cluster_labels, return_counts=True)):
                if count < min_cluster_size: continue
                indexes = np.arange(len(cluster_labels))[cluster_labels == label]
                ids = all_ids[cluster_labels == label].tolist()

                clusters.append({
                    'ids': set(ids),
                    'frame': idx_1,
                    'previewFrame': idx_2,
                    'consistency': self._consistency_score(ids, self.embeddings[idx_1]), 
                    'innerChange': self._inner_change_score(ids, self.embeddings[idx_1], self.embeddings[idx_2]),
                    'gain': self._change_score([gained_ids[i] for i in indexes], ids), 
                    'loss': self._change_score([lost_ids[i] for i in indexes], ids)
                })
        return clusters
    
    def query(self, ids_of_interest=None, filter_ids=None, frame_idx=None, preview_frame_idx=None, bounding_box=None, num_results=10, id_type="selection"):
        """
        Returns a list of clusters in sorted order of relevance that match the
        given filters.
        
        ids_of_interest: A list of ID values. If there are sufficiently many clusters
            containing at least one ID in this list, only they will be returned.
            Otherwise, clusters containing IDs from the neighbor sets of those IDs
            may be returned as well.
        filter_ids: A list of IDs such that at least one point in every cluster
            MUST be present in this list.
        frame_idx: A base frame index to filter for. If None, clusters from any frame
            may be returned.
        preview_frame_idx: A preview frame index to filter for. frame_idx must be
            provided if this is provided.
        bounding_box: If provided, should be a tuple of four values: min x, max x, 
            min y, and max y. At least one point in each cluster will be required to
            be within the bounding box.
        num_results: Maximum number of results to return.
        id_type: The type of ID that ids_of_interest corresponds to. This goes into
            the explanation string for clusters, e.g. "shares 3 points with <id_type>".
        """
        
        # Determine which frames to look for clusters in
        frames_to_check = []
        if frame_idx is not None:
            if preview_frame_idx is not None:
                frames_to_check.append((frame_idx, preview_frame_idx))
            else:
                frames_to_check = [(frame_idx, j) for j in range(len(self.embeddings)) if frame_idx != j]
        else:
            frames_to_check = [(i, j) for i in range(len(self.embeddings)) for j in range(len(self.embeddings)) if i != j]
            
        interest_set = set(ids_of_interest) if ids_of_interest is not None else None
        filter_set = set(filter_ids) if filter_ids is not None else None
        
        candidates = []
        for frame_key in frames_to_check:
            base_frame = self.embeddings[frame_key[0]]
            if bounding_box is not None:
                positions = base_frame.field(Field.POSITION)
            else:
                positions = None
                
            # Assemble a list of candidates
            if ids_of_interest is not None:
                neighbor_ids = set([n for n in self.embeddings[frame_key[0]].field(Field.NEIGHBORS, ids_of_interest)[:,:NUM_NEIGHBORS_FOR_SEARCH].flatten()])
            else:
                neighbor_ids = None    

            for cluster in self.clusters[frame_key]:
                frame_labels = "{} &rarr; {}".format(self.embeddings[cluster['frame']].label, self.embeddings[cluster['previewFrame']].label)
                base_score = (cluster['consistency'] + cluster['innerChange'] + cluster['gain'] + cluster['loss']) * np.log(len(cluster['ids']))
                if filter_set is not None:
                    if not cluster['ids'] & filter_set:
                        continue
                    base_score *= len(cluster['ids'] & filter_set) / len(cluster['ids'])
                
                if interest_set is not None and cluster['ids'] & interest_set:
                    candidates.append((cluster, 
                                       base_score * len(cluster['ids'] & interest_set) / len(cluster['ids']),
                                       "shares {} points with {} ({})".format(len(cluster['ids'] & interest_set), id_type, frame_labels)))
                elif neighbor_ids is not None and cluster['ids'] & neighbor_ids:
                    candidates.append((cluster,
                                       base_score * 0.5 * len(cluster['ids'] & neighbor_ids) / len(cluster['ids']),
                                      "shares {} points with neighbors of {} ({})".format(len(cluster['ids'] & neighbor_ids), id_type, frame_labels)))
                elif bounding_box is not None:
                    point_positions = positions[base_frame.index(np.array(list(cluster['ids'])))]
                    num_within = np.sum((point_positions[:,0] >= bounding_box[0]) *
                              (point_positions[:,0] <= bounding_box[1]) *
                              (point_positions[:,1] >= bounding_box[2]) *
                              (point_positions[:,1] <= bounding_box[3]))
                    if num_within > 0:
                        candidates.append((cluster, base_score * np.log(num_within), frame_labels))
                elif ids_of_interest is None:
                    if frame_idx is not None and preview_frame_idx is not None:
                        reason = "matches frames "
                    elif preview_frame_idx is not None:
                        reason = "matches preview frame "
                    else:
                        reason = ""
                    candidates.append((cluster,
                                       base_score,
                                       "{}{}".format(reason, ("(" + frame_labels + ")") if reason else frame_labels)))
        
        # Sort candidates and make sure they don't include overlapping IDs
        seen_ids = set()
        results = []
        for cluster, _, reason in sorted(candidates, key=lambda x: x[1], reverse=True):
            if cluster['ids'] & seen_ids: continue
            results.append((cluster, reason))
            seen_ids |= cluster['ids']
            if len(results) >= num_results: break
                
        return results