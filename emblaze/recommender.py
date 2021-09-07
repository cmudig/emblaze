import numpy as np
from sklearn.cluster import AgglomerativeClustering
from .utils import Field
import collections

NUM_NEIGHBORS_FOR_SEARCH = 10

class SelectionRecommender:
    """
    Generates recommended selections based on a variety of inputs. The
    recommender works by pre-generating a list of clusters at various
    granularities, then sorting them by relevance to a given query.
    """
    def __init__(self, embeddings, progress_fn=None):
        super().__init__()
        self.embeddings = embeddings
        self.clusters = {}
        for i in range(len(self.embeddings)):
            for j in range(len(self.embeddings)):
                if i == j: continue
                self.clusters[(i, j)] = self._make_clusters(i, j, np.log10(len(self.embeddings[i])))
                if progress_fn is not None:
                    progress_fn(len(self.clusters) / (len(self.embeddings) * (len(self.embeddings) - 1)))
        
    def _make_neighbor_mat(self, neighbors, num_columns):
        """Converts a list of neighbor indexes into a one-hot encoded matrix."""
        neighbor_mat = np.zeros((len(neighbors), num_columns + 1))
        if isinstance(neighbors, list):
            max_len = max(len(n) for n in neighbors)
            neighbors_padded = -np.ones((len(neighbors), max_len), dtype=int)
            for i, n in enumerate(neighbors):
                neighbors_padded[i,:len(n)] = list(n)
            neighbors = neighbors_padded

        for i in range(neighbors.shape[1]):
            neighbor_mat[np.arange(len(neighbors)), neighbors[:,i] + 1] = 1
        return neighbor_mat[:,1:]

    def _pairwise_jaccard_distances(self, neighbors):
        """Computes the jaccard distance between each row of the given set of neighbors."""
        # Make a one-hot matrix of neighbors
        neighbor_mat = self._make_neighbor_mat(neighbors, max(np.max([n for x in neighbors for n in x]) + 1, len(neighbors)))
        intersection = np.dot(neighbor_mat, neighbor_mat.T)
        negation = 1 - neighbor_mat
        union = neighbor_mat.shape[1] - np.dot(negation, negation.T)
        return 1.0 - intersection / np.maximum(union, 1)

    def _make_neighbor_changes(self, idx_1, idx_2):
        """
        Computes the sets of gained IDs and lost IDs for the given pair of frames.
        """
        frame_1 = self.embeddings[idx_1]
        frame_2 = self.embeddings[idx_2]
        frame_1_neighbors = frame_1.field(Field.NEIGHBORS)
        frame_2_neighbors = frame_2.field(Field.NEIGHBORS)
        gained_ids = [set(frame_2_neighbors[i]) - set(frame_1_neighbors[i]) for i in range(len(frame_1))]
        lost_ids = [set(frame_1_neighbors[i]) - set(frame_2_neighbors[i]) for i in range(len(frame_1))]

        return gained_ids, lost_ids
        
    def _consistency_score(self, ids, frame):
        """
        Computes the consistency between the neighbors for the given set of IDs 
        in the given frame.
        """
        return (np.sum(1 - self._pairwise_jaccard_distances(frame.field(Field.NEIGHBORS, ids=ids))) - len(ids)) / (len(ids) * (len(ids) - 1))
        
    def _change_score(self, change_set, ids, num_neighbors=10):
        """
        Computes a score estimating the consistency in the changes for the given
        set of IDs
        """
        counter = collections.Counter([x for s in change_set for x in s if x not in ids])
        return np.mean([x[1] / len(ids) for x in sorted(counter.items(), key=lambda x: x[1], reverse=True)[:num_neighbors]])
        
    def _make_clusters(self, idx_1, idx_2, min_cluster_size=1):
        """
        Produces clusters based on the pairwise distances between the given pair of frames.
        """
        gained_ids, lost_ids = self._make_neighbor_changes(idx_1, idx_2)
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
                ids = np.arange(len(cluster_labels))[cluster_labels == label].tolist()

                clusters.append({
                    'ids': set(self.embeddings[idx_1].ids[ids]),
                    'frame': idx_1,
                    'previewFrame': idx_2,
                    'consistency': self._consistency_score(ids, self.embeddings[idx_1]), 
                    'gain': self._change_score([gained_ids[i] for i in ids], ids), 
                    'loss': self._change_score([lost_ids[i] for i in ids], ids)
                })
        return clusters
    
    def query(self, ids_of_interest=None, frame_idx=None, preview_frame_idx=None, bounding_box=None, num_results=10, id_type="selection"):
        """
        Returns a list of clusters in sorted order of relevance that match the
        given filters.
        
        ids_of_interest: A list of ID values. If there are sufficiently many clusters
            containing at least one ID in this list, only they will be returned.
            Otherwise, clusters containing IDs from the neighbor sets of those IDs
            may be returned as well.
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
            frames_to_check = [(i, j) for i in range(len(self.embeddings)) for j in range(len(self.embeddings))]
            
        assert ids_of_interest is None or bounding_box is None, "Cannot query with both ids_of_interest and bounding_box"
            
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
                ids_of_interest = set(ids_of_interest)
            else:
                neighbor_ids = None    

            for cluster in self.clusters[frame_key]:
                frame_labels = "{} &rarr; {}".format(self.embeddings[cluster['frame']].label, self.embeddings[cluster['previewFrame']].label)
                base_score = (cluster['consistency'] + cluster['gain'] + cluster['loss']) * np.log(len(cluster['ids']))
                if ids_of_interest is not None and cluster['ids'] & ids_of_interest:
                    candidates.append((cluster, 
                                       base_score * len(cluster['ids'] & ids_of_interest) / len(cluster['ids']),
                                       "shares {} points with {} {}".format(len(cluster['ids'] & ids_of_interest), id_type, frame_labels)))
                elif neighbor_ids is not None and cluster['ids'] & neighbor_ids:
                    candidates.append((cluster,
                                       base_score * 0.5 * len(cluster['ids'] & ids_of_interest) / len(cluster['ids']),
                                      "shares {} points with neighbors of {} {}".format(len(cluster['ids'] & neighbor_ids), id_type, frame_labels)))
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
                    candidates.append((cluster, base_score, "{}{}".format(reason, frame_labels)))
        
        # Sort candidates and make sure they don't include overlapping IDs
        seen_ids = set()
        results = []
        for cluster, _, reason in sorted(candidates, key=lambda x: x[1], reverse=True):
            if cluster['ids'] & seen_ids: continue
            results.append((cluster, reason))
            seen_ids |= cluster['ids']
            if len(results) >= num_results: break
                
        return results