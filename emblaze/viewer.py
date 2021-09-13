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
from .utils import Field, LoggingHelper, SidebarPane, matrix_to_affine, affine_to_matrix, DataType, PreviewMode
from .recommender import SelectionRecommender
from datetime import datetime
import json
import glob
import threading
import numpy as np

PERFORMANCE_SUGGESTIONS_RECOMPUTE = 1000
PERFORMANCE_SUGGESTIONS_ENABLE = 10000

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
    previewFrame = Integer(0).tag(sync=True)
    alignedFrame = Integer(0).tag(sync=True)
    selectedIDs = List([]).tag(sync=True)
    alignedIDs = List([]).tag(sync=True)
    filterIDs = List([]).tag(sync=True)
    
    numNeighbors = Integer(10).tag(sync=True)

    # List of lists of 3 elements each, containing HSV colors for each frame
    frameColors = List([]).tag(sync=True)
    _defaultFrameColors = List([])
    # List of 3 x 3 matrices (expressed as 3x3 nested lists)
    frameTransformations = List([]).tag(sync=True)
    
    thumbnails = Instance(Thumbnails, allow_none=True)
    # JSON-serializable dictionary of thumbnail info
    thumbnailData = Dict({}).tag(sync=True)

    saveSelectionFlag = Bool(False).tag(sync=True)
    selectionName = Unicode("").tag(sync=True)
    selectionDescription = Unicode("").tag(sync=True)

    visibleSidebarPane = Integer(SidebarPane.CURRENT).tag(sync=True)
    selectionList = List([]).tag(sync=True)
    recommender = None
    suggestedSelections = List([]).tag(sync=True)
    loadingSuggestions = Bool(False).tag(sync=True)
    loadingSuggestionsProgress = Float(0.0).tag(sync=True)
    recomputeSuggestionsFlag = Bool(False).tag(sync=True)
    suggestedSelectionWindow = List([]).tag(sync=True)
    # if True, recompute suggestions fully but only when less than PERFORMANCE_SUGGESTIONS_RECOMPUTE points are visible
    performanceSuggestionsMode = Bool(False).tag(sync=True)
    
    selectionHistory = List([]).tag(sync=True)
    
    # Contains three keys: centerID (int), frame (int), unit (string)
    selectionUnit = Unicode("").tag(sync=True)
    selectionOrderRequest = Dict({}).tag(sync=True)
    selectionOrder = List([]).tag(sync=True)

    # Name of a color scheme (e.g. tableau, turbo, reds)
    colorScheme = Unicode("").tag(sync=True)
    
    # Preview info
    previewMode = Unicode("").tag(sync=True)
    previewParameters = Dict({}).tag(sync=True)
    
    # List of past interactions with the widget. When saveInteractionsFlag is
    # set to True by the widget, the backend will save the interaction history
    # to file using the loggingHelper.
    interactionHistory = List([]).tag(sync=True)
    saveInteractionsFlag = Bool(False).tag(sync=True)
    
    # Whether to save interaction history/logs to file
    loggingEnabled = Bool(False).tag(sync=True)
    loggingHelper = None
    
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
        if self.loggingEnabled:
            self.loggingHelper = LoggingHelper('emblaze_logs_{}.json'.format(datetime.now().strftime("%Y%m%d_%H%M%S")),
                                               {'numFrames': len(self.embeddings),
                                                'numPoints': len(self.embeddings[0])})

        self._update_performance_suggestions_mode()
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
        
        self._update_suggested_selections()

    @observe("currentFrame")
    def _observe_current_frame(self, change):
        self.selectionUnit = self.embeddings[change.new].metric
        self._update_suggested_selections()

    @observe("previewFrame")
    def _observe_preview_frame(self, change):
        self._update_suggested_selections()

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
    
    @observe("selectedIDs")
    def _observe_selected_ids(self, change):
        """Change the color scheme to match the arrangement of the selected IDs."""
        self.update_frame_colors()
        self._update_suggested_selections()
            
    @observe("filterIDs")
    def _observe_filter_ids(self, change):
        """Update suggestions when the filter changes."""
        self._update_suggested_selections()

    def reset_alignment(self):
        """Removes any transformations applied to the embedding frames."""
        self.frameTransformations = [
            np.eye(3).tolist()
            for i in range(len(self.embeddings))
        ]
        self.update_frame_colors()
        
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
            self.update_frame_colors()
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
        self.update_frame_colors()

    def update_frame_colors(self):
        """
        Updates the colors of the color stripes next to each frame thumbnail in
        the sidebar. The selectedIDs property is used first, followed by
        alignedIDs if applicable.
        """
        if not self.selectedIDs:
            if self.alignedIDs:
                self.frameColors = compute_colors(self.embeddings, self.alignedIDs)
            else:
                if not self._defaultFrameColors:
                    self._defaultFrameColors = compute_colors(self.embeddings, None)
                self.frameColors = self._defaultFrameColors
        else:
            self.frameColors = compute_colors(self.embeddings, self.selectedIDs)

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
        order, distances = hi_d.neighbor_distances(ids=[centerID], n_neighbors=2000)
        
        self.selectionOrder = [(int(x), y) for x, y in np.vstack([
            order.flatten(),
            distances.flatten()
        ]).T.tolist()]

    @observe("visibleSidebarPane")
    def _observe_sidebar_pane(self, change):
        if change.new == SidebarPane.SUGGESTED:
            self._update_suggested_selections()
        elif change.new == SidebarPane.SAVED:
            self.refresh_saved_selections()

    def _get_filter_points(self, selection, in_frame=None):
        """Returns a list of points that should be visible if the given selection
        is highlighted."""
        filtered_points = set()
        for id_val in selection:
            filtered_points.add(id_val)
        for frame in self.embeddings.embeddings if in_frame is None else [in_frame]:
            filtered_points |= set(frame.field(Field.NEIGHBORS, ids=selection)[:,:self.numNeighbors].flatten().tolist())
        return list(filtered_points)
    
    @observe("recomputeSuggestionsFlag")
    def _observe_suggestion_flag(self, change):
        """Recomputes suggestions when recomputeSuggestionsFlag is set to True."""
        if change.new and not self.loadingSuggestions:
            self._update_suggested_selections()
    
    def _update_performance_suggestions_mode(self):
        """Determines whether to use the performance mode for computing suggestions."""
        self.performanceSuggestionsMode = len(self.embeddings[0]) * len(self.embeddings) >= PERFORMANCE_SUGGESTIONS_ENABLE
        
    def _update_suggested_selections_background(self):
        """Function that runs in the background to recompute suggested selections."""
        self.recomputeSuggestionsFlag = False
        if self.loadingSuggestions: 
            return

        filter_points = None
        self._update_performance_suggestions_mode()
        if self.performanceSuggestionsMode:
            # Check if sufficiently few points are visible to show suggestions
            if self.filterIDs and len(self.filterIDs) <= PERFORMANCE_SUGGESTIONS_RECOMPUTE:
                filter_points = self.filterIDs
            if self.suggestedSelectionWindow:
                bbox_points = self.embeddings[self.currentFrame].within_bbox(self.suggestedSelectionWindow)
                if filter_points:
                    filter_points = list(set(filter_points) & set(bbox_points))
                else:
                    filter_points = bbox_points
            if (self.visibleSidebarPane != SidebarPane.SUGGESTED or
                not filter_points or
                len(filter_points) > PERFORMANCE_SUGGESTIONS_RECOMPUTE):
                self.suggestedSelections = []
                return
            # Add the vicinity around these points just to be safe
            filter_points = self._get_filter_points(filter_points, in_frame=self.embeddings[self.currentFrame])
            
        self.loadingSuggestions = True
        
        try:
            if self.recommender is None or self.performanceSuggestionsMode:
                self.loadingSuggestionsProgress = 0.0
                def progress_fn(progress):
                    self.loadingSuggestionsProgress = progress
                self.recommender = SelectionRecommender(
                    self.embeddings, 
                    progress_fn=progress_fn,
                    frame_idx=self.currentFrame if self.performanceSuggestionsMode else None,
                    preview_frame_idx=self.previewFrame if self.performanceSuggestionsMode and self.previewFrame >= 0 and self.previewFrame != self.currentFrame else None,
                    filter_points=filter_points)

        
            # Only compute suggestions when pane is open
            if self.previewFrame >= 0 and self.previewFrame != self.currentFrame:
                preview_frame_idx = self.previewFrame
            else:
                preview_frame_idx = None
              
            if self.selectedIDs:
                ids_of_interest = self.selectedIDs
                id_type = "selection"  
            elif self.filterIDs and not self.performanceSuggestionsMode:
                ids_of_interest = self.filterIDs
                id_type = "visible points"
            else:
                ids_of_interest = None
                id_type = "visible points" if self.performanceSuggestionsMode else None

            suggestions = []
            results = self.recommender.query(ids_of_interest=ids_of_interest,
                                             filter_ids=self.filterIDs or None,
                                             frame_idx=self.currentFrame,
                                             preview_frame_idx=preview_frame_idx,
                                             bounding_box=self.suggestedSelectionWindow or None,
                                             num_results=25,
                                             id_type=id_type)
            for result, reason in results:
                ids = list(result["ids"])
                suggestions.append({
                    "selectionName": "",
                    "selectionDescription": reason,
                    "currentFrame": result["frame"],
                    "selectedIDs": ids,
                    "alignedIDs": ids,
                    "filterIDs": self._get_filter_points(ids),
                    "frameColors": compute_colors(self.embeddings, ids)
                })
            self.suggestedSelections = suggestions
                
            self.loadingSuggestions = False
        except Exception as e:
            self.loadingSuggestions = False
            raise e
        
    def _update_suggested_selections(self):
        """Recomputes the suggested selections."""
        thread = threading.Thread(target=self._update_suggested_selections_background)
        thread.start()

    @observe("saveInteractionsFlag")
    def _save_interactions(self, change):
        """
        The widget sets the flag to save interaction history periodically
        because we can't use a timer in the backend.
        """
        if change.new:
            self.loggingHelper.add_logs(self.interactionHistory)
            self.interactionHistory = []
            self.saveInteractionsFlag = False