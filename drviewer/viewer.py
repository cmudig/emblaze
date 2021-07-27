#!/usr/bin/env python
# coding: utf-8

# Copyright (c) venkatesh-sivaraman.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from ipywidgets import DOMWidget
from traitlets import Integer, Unicode, Dict, Bool, List, Float, Bytes, Instance, observe
from ._frontend import module_name, module_version
from .frame_colors import compute_colors
from .datasets import EmbeddingSet
from .thumbnails import Thumbnails
from .utils import Field, matrix_to_affine, affine_to_matrix, DataType
from sklearn.metrics.pairwise import cosine_distances, euclidean_distances
from sklearn.neighbors import NearestNeighbors
from scipy.spatial.transform import Rotation
import threading
import multiprocessing as mp
from functools import partial
import numpy as np
import affine
import base64
import os

class DRViewer(DOMWidget):
    """TODO: Add docstring here
    """
    _model_name = Unicode('ViewerModel').tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_name = Unicode('DRViewer').tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)

    embeddings = Instance(EmbeddingSet, allow_none=True)
    data = Dict({}).tag(sync=True)
    isLoading = Bool(True).tag(sync=True)
    loadingMessage = Unicode("").tag(sync=True)
    
    plotPadding = Float(10.0).tag(sync=True)
    
    currentFrame = Integer(0).tag(sync=True)
    selectedIDs = List([]).tag(sync=True)
    alignedIDs = List([]).tag(sync=True)

    # List of lists of 3 elements each, containing HSV colors for each frame
    frameColors = List([]).tag(sync=True)
    # List of 3 x 3 matrices (expressed as 3x3 nested lists)
    frameTransformations = List([]).tag(sync=True)
    
    thumbnails = Instance(Thumbnails, allow_none=True)
    # JSON-serializable dictionary of thumbnail info
    thumbnailData = Dict({}).tag(sync=True)
    
    # Name of a color scheme (e.g. tableau, turbo, reds)
    colorScheme = Unicode("tableau").tag(sync=True)
    
    def __init__(self, *args, **kwargs):
        """
        embeddings: An EmbeddingSet object.
        thumbnails: A ThumbnailSet object.
        """
        super(DRViewer, self).__init__(*args, **kwargs)
        assert len(self.embeddings) > 0, "Must have at least one embedding"
        self.isLoading = False
        self.colorScheme = self.detect_color_scheme()
        
    def detect_color_scheme(self):
        """
        Returns a default color scheme for the given type of data.
        """
        if len(self.embeddings) == 0:
            return "tableau"
        if self.embeddings[0].guess_data_type(Field.COLOR) == DataType.CATEGORICAL:
            return "tableau"
        return "plasma"
        
    @observe("embeddings")
    def _observe_embeddings(self, change):
        embeddings = change.new
        assert len(embeddings) > 0, "Must have at least one embedding"
        if embeddings is not None:
            self.data = embeddings.to_json()
        else:
            self.data = {}
        self.selectedIDs = []
        self.alignedIDs = []
        self.currentFrame = 0
        self.reset_alignment()
        
        # Compute padding based on first embedding
        base_frame = embeddings[0].field(Field.POSITION)
        mins = np.min(base_frame, axis=0)
        maxes = np.max(base_frame, axis=0)
        self.plotPadding = np.min(maxes - mins) * 0.2

    @observe("thumbnails")
    def _observe_thumbnails(self, change):
        if change.new is not None:
            self.thumbnailData = change.new.to_json()
        else:
            self.thumbnailData = {}
    
    @observe("alignedIDs")
    def _observe_alignment_ids(self, change):
        """Align to the currently selected points and their neighbors."""
        if not change.new:
            self.align_to_points(None, None)
        else:
            ids_of_interest = change.new
            thread = threading.Thread(target=self.align_to_points, args=(change.new, list(set(ids_of_interest)),))
            thread.start()
    
    def reset_alignment(self):
        """Removes any transformations applied to the embedding frames."""
        self.frameTransformations = [
            np.eye(3).tolist()
            for i in range(len(self.embeddings))
        ]
        self.frameColors = compute_colors(self.embeddings)
        
    def align_to_points(self, point_ids, peripheral_points):
        """
        Re-align the projections to minimize motion for the given point IDs.
        Uses currentFrame as the base frame. Updates the 
        self.frameTransformations traitlet.
        
        Args:
            point_ids: Iterable of point IDs to use for alignment.
        """
        if point_ids is None:
            self.reset_alignment()
            self.frameColors = compute_colors(self.embeddings)
            return
    
        transformations = []
        base_transform = matrix_to_affine(np.array(self.frameTransformations[self.currentFrame]))

        for emb in self.embeddings:
            transformations.append(affine_to_matrix(emb.align_to(
                self.embeddings[self.currentFrame], 
                ids=list(set(point_ids)),
                base_transform=base_transform,
                return_transform=True,
                allow_flips=False)).tolist())

        self.frameTransformations = transformations
        self.frameColors = compute_colors(self.embeddings, point_ids, peripheral_points)
