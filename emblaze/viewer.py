#!/usr/bin/env python
# coding: utf-8

# Copyright (c) venkatesh-sivaraman.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from ipywidgets import DOMWidget
from numpy.core.fromnumeric import sort
from traitlets import Integer, Unicode, Dict, Bool, List, Float, Bytes, Instance, Set, observe, Any
from ._frontend import module_name, module_version
from .frame_colors import compute_colors
from .datasets import EmbeddingSet, NeighborOnlyEmbedding, Embedding
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

def default_thread_starter(fn, args=[], kwargs={}):
    thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
    thread.start()
    
def synchronous_thread_starter(fn, args=[], kwargs={}):
    fn(args, kwargs)

class Viewer(DOMWidget):
    """TODO: Add docstring here
    """
    _model_name = Unicode('ViewerModel').tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_name = Unicode('Viewer').tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)
    
    thread_starter = Any(default_thread_starter)

    embeddings = Instance(EmbeddingSet, allow_none=True)
    data = Dict(None, allow_none=True).tag(sync=True)
    file = Any(allow_none=True).tag(sync=True)    
    plotPadding = Float(10.0).tag(sync=True)
    
    currentFrame = Integer(0).tag(sync=True)
    previewFrame = Integer(0).tag(sync=True)
    alignedFrame = Integer(0).tag(sync=True)
    selectedIDs = List([]).tag(sync=True)
    alignedIDs = List([]).tag(sync=True)
    filterIDs = List([]).tag(sync=True)
    
    numNeighbors = Integer(10).tag(sync=True)
    storedNumNeighbors = Integer(0).tag(sync=True)

    # List of lists of 3 elements each, containing HSV colors for each frame
    frameColors = List([]).tag(sync=True)
    _defaultFrameColors = List([])
    # List of 3 x 3 matrices (expressed as 3x3 nested lists)
    frameTransformations = List([]).tag(sync=True)
    
    thumbnails = Instance(Thumbnails, allow_none=True)
    # JSON-serializable dictionary of thumbnail info
    thumbnailData = Dict({}).tag(sync=True)
    
    # High dimensional neighbors, one dictionary corresponding to each Embedding
    neighborData = List([]).tag(sync=True)

    saveSelectionFlag = Bool(False).tag(sync=True)
    selectionName = Unicode("").tag(sync=True)
    selectionDescription = Unicode("").tag(sync=True)
    allowsSavingSelections = Bool(True).tag(sync=True)

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
        file: A file path or file-like object from which to read a comparison JSON file.
        """
        super(Viewer, self).__init__(*args, **kwargs)
        if self.file:
            self.load_comparison(self.file)
        assert len(self.embeddings) > 0, "Must have at least one embedding"
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
        if not self.allowsSavingSelections:
            self.saveSelectionFlag = False
            return
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
        ancestor_neighbors = [emb.get_ancestor_neighbors() for emb in self.embeddings]
        for n1 in ancestor_neighbors:
            if not n1:
                return PreviewMode.PROJECTION_SIMILARITY
            for n2 in ancestor_neighbors:
                if not n2:
                    return PreviewMode.PROJECTION_SIMILARITY
                if n1 != n2:
                    return PreviewMode.NEIGHBOR_SIMILARITY
        return PreviewMode.PROJECTION_SIMILARITY
        
    def _select_stored_num_neighbors(self, embeddings):
        """
        Optionally reduces the number of stored neighbors in the JSON to save
        space. Prints a warning if it does so.
        """
        num_points = len(embeddings) * len(embeddings[0])
        new_val = None
        if num_points > 500000:
            new_val = 25
        elif num_points > 200000:
            new_val = 50
        elif num_points > 100000:
            new_val = 75
        if new_val is not None and any(new_val < emb.n_neighbors for emb in embeddings.embeddings):
            print(("WARNING: Reducing the number of nearest neighbors passed to the "
                   "widget to {} to save space. You can control this by setting the "
                   "storedNumNeighbors property of the widget when initializing.").format(new_val))
        return new_val                        
        
    @observe("file")
    def _observe_file(self, change):
        if change.new is not None:
            self.load_comparison(change.new)
        
    @observe("embeddings")
    def _observe_embeddings(self, change):
        embeddings = change.new
        assert len(embeddings) > 0, "Must have at least one embedding"
        assert not any(not e.any_ancestor_has_neighbors() for e in embeddings), "All embeddings must have at least one Neighbors previously computed"
        if embeddings is not None:
            self.neighborData = []
            if self.storedNumNeighbors > 0:
                n_neighbors = self.storedNumNeighbors 
            else:
                n_neighbors = self._select_stored_num_neighbors(embeddings)
            self.data = embeddings.to_json(save_neighbors=False)
            self.neighborData = embeddings.get_ancestor_neighbors().to_json(num_neighbors=n_neighbors)
        else:
            self.neighborData = []
            self.data = {}
        self.reset_state()
        
        # Compute padding based on first embedding
        base_frame = embeddings[0].field(Field.POSITION)
        mins = np.min(base_frame, axis=0)
        maxes = np.max(base_frame, axis=0)
        self.plotPadding = np.min(maxes - mins) * 0.2
        
        self.colorScheme = self.detect_color_scheme()
        self.previewMode = self.detect_preview_mode()
        self._update_selection_unit(embeddings[0])
        
        self._update_suggested_selections()

    @observe("currentFrame")
    def _observe_current_frame(self, change):
        self._update_selection_unit(self.embeddings[change.new])
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
            self.thread_starter(self.align_to_points, args=(change.new, list(set(ids_of_interest)),))
    
    @observe("selectedIDs")
    def _observe_selected_ids(self, change):
        """Change the color scheme to match the arrangement of the selected IDs."""
        self.update_frame_colors()
        self._update_suggested_selections()
            
    @observe("filterIDs")
    def _observe_filter_ids(self, change):
        """Update suggestions when the filter changes."""
        self._update_suggested_selections()

    def reset_state(self):
        """Resets the view state of the widget."""
        self.currentFrame = 0
        self.previewFrame = -1
        self.selectedIDs = []
        self.alignedIDs = []
        self.filterIDs = []
        self.reset_alignment()

    def reset_alignment(self):
        """Removes any transformations applied to the embedding frames."""
        self.frameTransformations = [
            np.eye(3).tolist()
            for i in range(len(self.embeddings))
        ]
        self.alignedFrame = 0
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

    def _update_selection_unit(self, frame):
        """Sets the selection unit if the current frame can be queried for
        distances."""
        ancestor = frame.find_ancestor_neighbor_embedding()
        if isinstance(ancestor, NeighborOnlyEmbedding):
            self.selectionUnit = ''
        else:
            self.selectionUnit = ancestor.metric
        
    @observe("selectionOrderRequest")
    def _compute_selection_order(self, change):
        """Compute an ordering of the points by distance from the selected ID."""
        if not change.new or 'centerID' not in change.new:
            self.selectionOrder = []
            return
        
        centerID = change.new['centerID']
        frame = change.new['frame']
        # metric = change.new['metric'] # for now, unused
        
        hi_d = self.embeddings[frame].find_ancestor_neighbor_embedding()
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
            filtered_points |= set(frame.get_ancestor_neighbors()[selection][:,:self.numNeighbors].flatten().tolist())
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
            print(e)
            self.loadingSuggestions = False
            raise e
        
    def _update_suggested_selections(self):
        """Recomputes the suggested selections."""
        self.thread_starter(self._update_suggested_selections_background)

    @observe("saveInteractionsFlag")
    def _save_interactions(self, change):
        """
        The widget sets the flag to save interaction history periodically
        because we can't use a timer in the backend.
        """
        if change.new and self.loggingHelper:
            self.loggingHelper.add_logs(self.interactionHistory)
            self.interactionHistory = []
            self.saveInteractionsFlag = False
            
    def comparison_to_json(self, compressed=True, ancestor_data=True):
        """
        Saves the data used to produce this comparison to a JSON object. This
        includes the EmbeddingSet and the Thumbnails that are visualized, as
        well as the immediate and ancestor neighbor data (see below). Ancestor
        neighbors are used to display nearest neighbors in the UI.
        
        If ancestor_data is True (default), the full Embedding object that
        produces the ancestor neighbors will be stored, including its neighbor
        set. If ancestor_data is set to False, only the ancestor
        neighbors themselves will be stored. This can save space if the ancestor
        embedding is very high-dimensional. However, the high-dimensional radius
        select tool will not work if ancestor data is not saved.
        """
        result = {}
        
        ancestor_neighbors = self.embeddings.get_ancestor_neighbors()
        recent_neighbors = self.embeddings.get_recent_neighbors()
        neighbors = self.embeddings.get_neighbors()
        
        result["_format"] = "emblaze.Viewer.SaveData"
        result["embeddings"] = self.embeddings.to_json(compressed=compressed,
                                                       save_neighbors=True)
        result["thumbnails"] = self.thumbnails.to_json()
        
        # Save recent neighbors (those used for frame colors and recommendations)
        # if they do not originate from the embeddings or in the ancestor embeddings
        if neighbors != recent_neighbors and recent_neighbors != ancestor_neighbors:
            # Save these in mock format
            if recent_neighbors.identical():
                result["recent_neighbors"] = [NeighborOnlyEmbedding.from_embedding(recent_neighbors[0]).to_json(compressed=compressed)]
            else:
                mock_embs = [NeighborOnlyEmbedding.from_embedding(a) for a in recent_neighbors]
                result["recent_neighbors"] = [e.to_json(compressed=compressed) for e in mock_embs]
        
        # Save ancestor neighbors (and positions, if ancestor_data = True)
        ancestors = EmbeddingSet([emb.find_ancestor_neighbor_embedding() for emb in self.embeddings], align=False)
        if ancestor_data:
            if ancestors.identical():
                result["ancestor_data"] = [ancestors[0].to_json(compressed=compressed)]
            else:
                result["ancestor_data"] = [
                    anc.to_json(compressed=compressed)
                    for anc in ancestors
                ]
        elif neighbors != ancestor_neighbors:
            # Create mock NeighborOnlyEmbeddings here to show that we are
            # saving only the neighbor data
            if ancestor_neighbors.identical():
                result["ancestor_neighbors"] = [NeighborOnlyEmbedding.from_embedding(ancestors[0]).to_json(compressed=compressed)]
            else:
                mock_embs = [NeighborOnlyEmbedding.from_embedding(a) for a in ancestors]
                result["ancestor_neighbors"] = [e.to_json(compressed=compressed) for e in mock_embs]
            
        return result
    
    def load_comparison_from_json(self, data):
        """
        Loads comparison information from a JSON object, including the
        EmbeddingSet, Thumbnails, and NeighborSet.
        """
        if self.embeddings is not None:
            self.reset_state()
            self.data = None
            self.neighborData = []
            self.thumbnailData = {}
        
        assert data["_format"] == "emblaze.Viewer.SaveData", "Unsupported JSON _format key '{}'".format(data["_format"])
        # Load neighbors first, to create mock parent embeddings
        parents = None
        if "ancestor_data" in data:
            parents = [Embedding.from_json(item) for item in data["ancestor_data"]]
        elif "ancestor_neighbors" in data:
            parents = [NeighborOnlyEmbedding.from_json(item) for item in data["ancestor_neighbors"]]
            
        if "recent_neighbors" in data:
            # The neighbors to display will come from these, so put them in between
            # the ancestor embeddings and the final ones
            recent_parents = parents
            if recent_parents is None:
                recent_parents = [None for _ in range(len(self.embeddings))]
            elif len(parents) == 1:
                recent_parents = [recent_parents[0] for _ in range(len(self.embeddings))]
            parents = [NeighborOnlyEmbedding.from_json(item, parent=p)
                       for item, p in zip(data["recent_neighbors"], recent_parents)]
        
        self.embeddings = EmbeddingSet.from_json(data["embeddings"], parents=parents)
        self.thumbnails = Thumbnails.from_json(data["thumbnails"])
        
        return self
                
    def save_comparison(self, file_path_or_buffer, ancestor_data=True):
        """
        Saves the comparison data (EmbeddingSet, Thumbnails, and NeighborSet) to
        the given file path or file-like object. See comparison_to_json() for
        more details.
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'w') as file:
                json.dump(self.comparison_to_json(ancestor_data=ancestor_data), file)
        else:
            # File object
            json.dump(self.comparison_to_json(ancestor_data=ancestor_data), file_path_or_buffer)
            
    def load_comparison(self, file_path_or_buffer):
        """
        Load the comparison data from the given file path or
        file-like object containing JSON data.
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'r') as file:
                return self.load_comparison_from_json(json.load(file))
        else:
            # File object
            return self.load_comparison_from_json(json.load(file_path_or_buffer))
