#!/usr/bin/env python
# coding: utf-8

# Copyright (c) venkatesh-sivaraman.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from ipywidgets import DOMWidget
from numpy.core.fromnumeric import sort
from traitlets import Integer, Unicode, Dict, Bool, List, Float, Bytes, Instance, Set, observe
from ._frontend import module_name, module_version
from .frame_colors import compute_colors
from .datasets import EmbeddingSet
from .thumbnails import Thumbnails
from .utils import Field, matrix_to_affine, affine_to_matrix, DataType, PreviewMode
from datetime import datetime
import json
import glob
import threading
import numpy as np


class Viewer(DOMWidget):
    """TODO: Add docstring here
    """
    _model_name = Unicode('ViewerModel').tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_name = Unicode('Viewer').tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)

    embeddings = Instance(EmbeddingSet, allow_none=True)
    data = Dict({}).tag(sync=True)
    isLoading = Bool(True).tag(sync=True)
    loadingMessage = Unicode("").tag(sync=True)
    
    plotPadding = Float(10.0).tag(sync=True)
    
    currentFrame = Integer(0).tag(sync=True)
    alignedFrame = Integer(0).tag(sync=True)
    selectedIDs = List([]).tag(sync=True)
    alignedIDs = List([]).tag(sync=True)
    filterIDs = List([]).tag(sync=True)
    
    numNeighbors = Integer(10).tag(sync=True)

    # List of lists of 3 elements each, containing HSV colors for each frame
    frameColors = List([]).tag(sync=True)
    # List of 3 x 3 matrices (expressed as 3x3 nested lists)
    frameTransformations = List([]).tag(sync=True)
    
    thumbnails = Instance(Thumbnails, allow_none=True)
    # JSON-serializable dictionary of thumbnail info
    thumbnailData = Dict({}).tag(sync=True)

    saveSelectionFlag = Bool(False).tag(sync=True)
    selectionName = Unicode("").tag(sync=True)
    selectionDescription = Unicode("").tag(sync=True)

    loadSelectionFlag = Bool(False).tag(sync=True)
    selectionList = List([]).tag(sync=True)
    
    # Contains three keys: centerID (int), frame (int), unit (string)
    selectionUnit = Unicode("").tag(sync=True)
    selectionOrderRequest = Dict({}).tag(sync=True)
    selectionOrder = List([]).tag(sync=True)

    # Name of a color scheme (e.g. tableau, turbo, reds)
    colorScheme = Unicode("").tag(sync=True)
    
    # Preview info
    previewMode = Unicode("").tag(sync=True)
    previewParameters = Dict({}).tag(sync=True)
    
    def __init__(self, *args, **kwargs):
        """
        embeddings: An EmbeddingSet object.
        thumbnails: A ThumbnailSet object.
        """
        super(Viewer, self).__init__(*args, **kwargs)
        assert len(self.embeddings) > 0, "Must have at least one embedding"
        self.isLoading = False
        self.saveSelectionFlag = False
        self.loadSelectionFlag = False
        self.selectionList = []
        if not self.colorScheme:
            self.colorScheme = self.detect_color_scheme()
        if not self.previewMode:
            self.previewMode = self.detect_preview_mode()
        if len(self.previewParameters) == 0:
            self.previewParameters = {'k': 10, 'similarityThreshold': 0.5}

    @observe("saveSelectionFlag")
    def _observe_save_selection(self, change):
        if change.new:
            newSelection = { }
            newSelection["selectedIDs"] = self.selectedIDs
            newSelection["alignedIDs"] = self.alignedIDs
            newSelection["filterIDs"] = self.filterIDs
            newSelection["selectionDescription"] = self.selectionDescription
            newSelection["currentFrame"] = self.currentFrame
            newSelection["alignedFrame"] = self.alignedFrame
            now = datetime.now()
            dateTime = now.strftime("%Y-%m-%d %H:%M:%S")
            with open(dateTime + ' ' + self.selectionName + '.selection', 'w') as outfile:
                json.dump(newSelection, outfile)
            
            self.saveSelectionFlag = False
            self.selectionName = ""
            self.selectionDescription = ""
            self.refresh_saved_selections()

    @observe("loadSelectionFlag")
    def _observe_load_selection(self, change):
        if change.new:
            self.refresh_saved_selections()
            
    def refresh_saved_selections(self):
        """
        Updates the selectionList property, which is displayed in the sidebar
        under the Saved tab.
        """
        tmpList = []
        # self.selectionList = []
        for file in glob.glob("*.selection"):
            with open(file, "r") as jsonFile:
                data = json.load(jsonFile)                            
                data["selectionName"] = file.split('.')[0]
                tmpList.append(data)
        self.selectionList = sorted(tmpList, key=lambda x: x["selectionName"], reverse=True)
        self.loadSelectionFlag = False
        
    def detect_color_scheme(self):
        """
        Returns a default color scheme for the given type of data.
        """
        if len(self.embeddings) == 0:
            return "tableau"
        if self.embeddings[0].guess_data_type(Field.COLOR) == DataType.CATEGORICAL:
            return "tableau"
        return "plasma"
    
    def detect_preview_mode(self):
        """
        Returns a projection similarity preview mode if the neighbors in all the
        frames are mostly the same, and a neighbor similarity preview mode
        otherwise.
        """
        for emb_1 in self.embeddings:
            if not emb_1.has_field(Field.NEIGHBORS):
                return PreviewMode.PROJECTION_SIMILARITY
            for emb_2 in self.embeddings:
                if not emb_2.has_field(Field.NEIGHBORS):
                    return PreviewMode.PROJECTION_SIMILARITY
                if not np.allclose(emb_1.field(Field.NEIGHBORS),
                                   emb_2.field(Field.NEIGHBORS)):
                    return PreviewMode.NEIGHBOR_SIMILARITY
        return PreviewMode.PROJECTION_SIMILARITY
        
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
        
        self.colorScheme = self.detect_color_scheme()
        self.previewMode = self.detect_preview_mode()
        self.selectionUnit = embeddings[0].metric

    @observe("currentFrame")
    def _observe_current_frame(self, change):
        self.selectionUnit = self.embeddings[change.new].metric

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
        base_transform = matrix_to_affine(np.array(self.frameTransformations[self.alignedFrame]))

        for emb in self.embeddings:
            transformations.append(affine_to_matrix(emb.align_to(
                self.embeddings[self.alignedFrame], 
                ids=list(set(point_ids)),
                base_transform=base_transform,
                return_transform=True,
                allow_flips=False)).tolist())

        self.frameTransformations = transformations
        self.frameColors = compute_colors(self.embeddings, point_ids, peripheral_points)

    @observe("selectionOrderRequest")
    def _compute_selection_order(self, change):
        """Compute an ordering of the points by distance from the selected ID."""
        if not change.new or 'centerID' not in change.new:
            self.selectionOrder = []
            return
        
        centerID = change.new['centerID']
        frame = change.new['frame']
        # metric = change.new['metric'] # for now, unused
        
        hi_d = self.embeddings[frame].get_root()
        distances = hi_d.distances(ids=[centerID], comparison_ids=hi_d.ids).flatten()
        
        order = np.argsort(distances)
        self.selectionOrder = [(int(x), y) for x, y in np.vstack([
            order,
            distances[order]
        ]).T.tolist()]
