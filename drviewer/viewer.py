#!/usr/bin/env python
# coding: utf-8

# Copyright (c) venkatesh-sivaraman.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from ipywidgets import DOMWidget
from traitlets import Integer, Unicode, Dict, Bool
from ._frontend import module_name, module_version
from . import moving_scatterplot as ms
from sklearn.metrics.pairwise import cosine_distances, euclidean_distances
from sklearn.neighbors import NearestNeighbors
from scipy.spatial.transform import Rotation
import threading
import multiprocessing as mp
from functools import partial

def apply_projection(hi_d, method='tsne', metric='euclidean', params={}):
    """
    Applies the DR technique specified for this widget.
    
    Args:
        hi_d: An n x k numpy array of point coordinates.
        
    Returns:
        An n x 2 numpy array of reduced point coordinates.
    """

    if method.lower() == "tsne":
        from sklearn.manifold import TSNE            
        return TSNE(metric=metric, **params).fit_transform(hi_d)
    elif method.lower() == "umap":
        import umap
        return umap.UMAP(metric=metric, **params).fit_transform(hi_d)
    elif method.lower() == "pca":
        from sklearn.decomposition import PCA
        return PCA(metric=metric, **params).fit_transform(hi_d)
    else:
        raise ValueError("Method '{}' not recognized".format(method))
        
class DRViewer(DOMWidget):
    """TODO: Add docstring here
    """
    _model_name = Unicode('ViewerModel').tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_name = Unicode('DRViewer').tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)

    data = Dict({}).tag(sync=True)
    isLoading = Bool(True).tag(sync=True)
    loadingMessage = Unicode("").tag(sync=True)
    numNeighbors = Integer(10)
    numReplicates = Integer(10).tag(sync=True)
    method = Unicode("tsne").tag(sync=True)
    params = Dict({}).tag(sync=True)
    metric = Unicode("euclidean").tag(sync=True)

    def __init__(self, hi_d, labels, *args, **kwargs):
        super(DRViewer, self).__init__(*args, **kwargs)
        self.load_projections(hi_d, labels)
    

    def load_projections(self, hi_d, labels):
        """
        Args:
            hi_d: An n x k numpy array of point coordinates, where n is the
            number of points and k is the number of dimensions
        """
        self.isLoading = True
        thread = threading.Thread(target=self._load_projections_background, args=(hi_d, labels))
        thread.start()
        
    def _load_projections_background(self, hi_d, labels):
        # Set up neighbors
        neighbor_clf = NearestNeighbors(metric=self.metric,
                                        n_neighbors=self.numNeighbors + 1).fit(hi_d)
        _, neigh_indexes = neighbor_clf.kneighbors(hi_d)

        frames = []
        self.loadingMessage = "frame 0/{}".format(self.numReplicates)
        pool = mp.Pool(3)
        num_results = 0
        worker = partial(apply_projection, metric=self.metric, method=self.method, params=self.params)
        for lo_d in pool.imap_unordered(worker, (hi_d for _ in range(self.numReplicates))):
            frames.append(ms.ScatterplotFrame([{
                "id": i,
                "x": lo_d[i,0],
                "y": lo_d[i,1],
                "label": labels[i],
                "highlight": neigh_indexes[i,1:]
            } for i in range(len(hi_d))]))
            num_results += 1
            self.loadingMessage = "frame {}/{}".format(num_results, self.numReplicates)
        
        self.loadingMessage = "aligning frames"
        for i, frame in enumerate(frames):
            best_proj = ms.align_projection(frames[0], frame)
            frame.set_mat(["aligned_x", "aligned_y"], best_proj[:,:2])
            
        data = [frame.to_viewer_dict(x_key="aligned_x", 
                                     y_key="aligned_y",
                                     additional_fields={
                                         "highlight": lambda _, item: item["highlight"].tolist(),
                                         "color": lambda _, item: item["label"]
                                     }) for frame in frames]

        self.isLoading = False
        self.loadingMessage = ""
        self.data = {
            "data": data,
            "frameLabels": [str(i) for i in range(len(frames))]
        }
        