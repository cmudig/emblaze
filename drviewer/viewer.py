#!/usr/bin/env python
# coding: utf-8

# Copyright (c) venkatesh-sivaraman.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from ipywidgets import DOMWidget
from traitlets import Integer, Unicode, Dict, Bool, List, Float, observe
from ._frontend import module_name, module_version
from . import moving_scatterplot as ms
from .frame_colors import compute_colors
from sklearn.metrics.pairwise import cosine_distances, euclidean_distances
from sklearn.neighbors import NearestNeighbors
from scipy.spatial.transform import Rotation
import threading
import multiprocessing as mp
from functools import partial
import numpy as np
import affine

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
        return PCA(**params).fit_transform(hi_d)
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
    frames = List([])
    isLoading = Bool(True).tag(sync=True)
    loadingMessage = Unicode("").tag(sync=True)
    numNeighbors = Integer(10)
    numReplicates = Integer(10).tag(sync=True)
    method = Unicode("tsne").tag(sync=True)
    params = Dict({}).tag(sync=True)
    metric = Unicode("euclidean").tag(sync=True)
    
    plotPadding = Float(10.0).tag(sync=True)
    plotScale = Float(100.0)
    
    currentFrame = Integer(0).tag(sync=True)
    alignedIDs = List([]).tag(sync=True)
    # List of lists of 3 elements each, containing HSV colors for each frame
    frameColors = List([]).tag(sync=True)
    # List of 3 x 3 matrices (expressed as 3x3 nested lists)
    frameTransformations = List([]).tag(sync=True)
    
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

        self.frames = []
        self.loadingMessage = "frame 0/{}".format(self.numReplicates)
        pool = mp.Pool(3)
        num_results = 0
        worker = partial(apply_projection, metric=self.metric, method=self.method, params=self.params)
        for lo_d in pool.imap_unordered(worker, (hi_d for _ in range(self.numReplicates))):
            self.frames = self.frames + [ms.ScatterplotFrame([{
                "id": i,
                "x": lo_d[i,0],
                "y": lo_d[i,1],
                "label": labels[i],
                "highlight": neigh_indexes[i,1:]
            } for i in range(len(hi_d))])]
            num_results += 1
            self.loadingMessage = "frame {}/{}".format(num_results, self.numReplicates)
        
        # Scale frames by the same amount
        base_frame = self.frames[0]
        base_data = base_frame.mat(["x", "y"])
        mins = np.min(base_data, axis=0)
        maxes = np.max(base_data, axis=0)
        scale_factor = np.min(self.plotScale / (maxes - mins))
        for frame in self.frames:
            frame.set_mat(["scaled_x", "scaled_y"], frame.mat(["x", "y"]) * scale_factor)
            frame.set_coordinate_keys("scaled_x", "scaled_y")

        # Align frames
        self.loadingMessage = "aligning frames"
        for i, frame in enumerate(self.frames):
            best_proj = ms.align_projection(self.frames[0], frame)
            frame.set_mat(["aligned_x", "aligned_y"], best_proj[:,:2])
            frame.set_coordinate_keys("aligned_x", "aligned_y")
            
        # Write out JSON
        data = [frame.to_viewer_dict(x_key="aligned_x", 
                                     y_key="aligned_y",
                                     additional_fields={
                                         "highlight": lambda _, item: item["highlight"].tolist(),
                                         "color": lambda _, item: item["label"]
                                     }) for frame in self.frames]

        colors = compute_colors(self.frames)
        
        self.isLoading = False
        self.loadingMessage = ""
        self.data = {
            "data": data,
            "frameLabels": [str(i) for i in range(len(self.frames))]
        }
        self.frameColors = colors
        self.frameTransformations = [
            np.eye(3).tolist()
            for i in range(len(self.frames))
        ]
        
    @observe("alignedIDs")
    def _observe_alignment_ids(self, change):
        """Align to the currently selected points and their neighbors."""
        if not change.new:
            self.align_to_points(None, None)
        else:
            ids_of_interest = change.new
            for neighbors in self.frames[0].mat("highlight", ids=ids_of_interest):
                ids_of_interest += neighbors.tolist()
            thread = threading.Thread(target=self.align_to_points, args=(change.new, list(set(ids_of_interest)),))
            thread.start()
    
    def align_to_points(self, point_ids, peripheral_points):
        """
        Re-align the projections to minimize motion for the given point IDs.
        Uses currentFrame as the base frame. Updates the 
        self.frameTransformations traitlet.
        
        Args:
            point_ids: Iterable of point IDs to use for alignment.
        """
        if point_ids is None:
            self.frameTransformations = [
                np.eye(3).tolist()
                for i in range(len(self.frames))
            ]
            self.frameColors = compute_colors(self.frames)
            return
    
        transformations = []
        base_transform = ms.matrix_to_affine(np.array(self.frameTransformations[self.currentFrame]))

        for frame in self.frames:
            transformations.append(ms.affine_to_matrix(ms.align_projection(
                self.frames[self.currentFrame], 
                frame, 
                ids=list(set(point_ids + peripheral_points)),
                base_transform=base_transform,
                return_transform=True,
                allow_flips=False)).tolist())

        self.frameTransformations = transformations
        self.frameColors = compute_colors(self.frames, point_ids, peripheral_points)
