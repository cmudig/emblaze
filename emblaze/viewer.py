#!/usr/bin/env python
# coding: utf-8

# Copyright (c) venkatesh-sivaraman.
# Distributed under the terms of the Modified BSD License.

"""
Defines the main Emblaze visualization class, `emblaze.Viewer`.
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
import tqdm
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
    """
    Represents and maintains the state of an interactive Emblaze interface to
    display in a Jupyter notebook. The basic instantiation of an Emblaze viewer
    proceeds as follows:
    
    ```python
    embeddings = emblaze.EmbeddingSet(...)
    thumbnails = emblaze.TextThumbnails(...)
    w = emblaze.Viewer(embeddings=embeddings, thumbnails=thumbnails)
    w
    ```
    """
    _model_name = Unicode('ViewerModel').tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_name = Unicode('Viewer').tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)
    
    thread_starter = Any(default_thread_starter)
    _autogenerate_embeddings = Bool(True) # only set this if caching embedding data

    #: An [`EmbeddingSet`](datasets.html#emblaze.datasets.EmbeddingSet) containing
    #: one or more embeddings to visualize. The coordinates contained in this 
    #: `EmbeddingSet` must be 2-dimensional.
    embeddings = Instance(EmbeddingSet, allow_none=True)
    #: The JSON-serializable data passed to the frontend. You should not need to modify this variable.
    data = Dict(None, allow_none=True).tag(sync=True)
    #: A file path or file-like object from which to read an embedding comparison (see [`save_comparison`](viewer.html#emblaze.viewer.Viewer.save_comparison)).
    file = Any(allow_none=True).tag(sync=True)
    #: Padding around the plot in data coordinates.
    plotPadding = Float(10.0).tag(sync=True)
    
    #: `True` if the widget is currently loading a comparison from file, `False` otherwise.
    isLoading = Bool(False).tag(sync=True)
    
    #: The index of the currently-viewing frame in the Viewer's [`embeddings`](#emblaze.viewer.Viewer.embeddings).
    currentFrame = Integer(0).tag(sync=True)
    #: The index of the previewed frame in the Viewer's [`embeddings`](#emblaze.viewer.Viewer.embeddings). The
    #: previewed frame is the frame to which points move when the Star Trail visualization is active.
    previewFrame = Integer(0).tag(sync=True)
    #: The index of the aligned frame in the Viewer's [`embeddings`](#emblaze.viewer.Viewer.embeddings).
    #: When the frames are aligned to a selection, they are anchored to the same
    #: position as before in this frame only.
    alignedFrame = Integer(0).tag(sync=True)
    #: A list of integer IDs corresponding to the selected points. By default,
    #: these are zero-indexed and span the range from zero to the number of points in each
    #: embedding.
    selectedIDs = List([]).tag(sync=True)
    #: A list of integer IDs corresponding to the aligned points (points selected
    #: to minimize motion across frames). By default, these are zero-indexed and
    #: span the range from zero to the number of points in each embedding.    
    alignedIDs = List([]).tag(sync=True)
    #: A list of integer IDs corresponding to the filtered points (a subset of
    #: points selected to be visible in the plot). By default, these are zero-indexed and
    #: span the range from zero to the number of points in each embedding.        
    filterIDs = List([]).tag(sync=True)
    
    #: The number of neighbors to show in nearest neighbor lines and the detail
    #: sidebar. This number cannot be greater than [`storedNumNeighbors`](#emblaze.viewer.Viewer.storedNumNeighbors).
    numNeighbors = Integer(10).tag(sync=True)
    #: The number of nearest neighbors to store for each point in the frontend
    #: visualization. This number cannot be greater than the number of neighbors
    #: computed in the embeddings' `Neighbors` objects. This is 100 by default,
    #: but will be automatically reduced to improve performance and memory usage
    #: when many points or frames are visualized. This value can be configured in the
    #: initialization of the `Viewer` instance.
    storedNumNeighbors = Integer(0).tag(sync=True)

    #: The colors used to represent each frame in the sidebar, stored as lists
    #: of 3 HSV components each.
    frameColors = List([]).tag(sync=True)
    _defaultFrameColors = List([])
    #: Transformation matrices that result in an alignment of frames to the
    #: viewer's current [`alignedIDs`](#emblaze.viewer.Viewer.alignedIDs). The
    #: matrices are represented as 3x3 nested lists.
    frameTransformations = List([]).tag(sync=True)
    
    #: A [`Thumbnails`](thumbnails.html#emblaze.thumbnails.Thumbnails) instance
    #: containing text and/or image descriptions for the IDs of the points
    #: provided in [`embeddings`](#emblaze.viewer.Viewer.embeddings).
    thumbnails = Instance(Thumbnails, allow_none=True)
    #: A JSON-serializable dictionary of thumbnail info. You should not need to
    #: modify this variable.
    thumbnailData = Dict({}).tag(sync=True)
    
    #: A JSON-serializable list of high-dimensional neighbors, containing one
    #: dictionary corresponding to each `Embedding`. You should not need to
    #: modify this variable.
    neighborData = List([]).tag(sync=True)

    #: Boolean marking that the current state of the visualization should be
    #: saved to file. The current values of [`selectionName`](#emblaze.viewer.Viewer.selectionName)
    #: and [`selectionDescription`](#emblaze.viewer.Viewer.selectionDescription)
    #: will be used.
    saveSelectionFlag = Bool(False).tag(sync=True)
    #: The name of the selection to save.
    selectionName = Unicode("").tag(sync=True)
    #: A description of the selection to save.
    selectionDescription = Unicode("").tag(sync=True)
    #: Boolean indicating whether selection saving and restoring should be
    #: enabled in the interface.
    allowsSavingSelections = Bool(True).tag(sync=True)

    #: The currently-visible sidebar pane, enumerated in `emblaze.utils.SidebarPane`.
    visibleSidebarPane = Integer(SidebarPane.CURRENT).tag(sync=True)
    #: A list of saved selections, to be displayed in the Saved sidebar pane.
    selectionList = List([]).tag(sync=True)
    #: The [`SelectionRecommender`](recommender.html#emblaze.recommender.SelectionRecommender)
    #: responsible for generating suggested selections.
    recommender = None
    #: The current list of suggested selections. Each suggestion is represented
    #: as a dictionary in the same format as a saved selection, including keys
    #: for `currentFrame`, `selectedIDs`, `alignedIDs`, and `filterIDs`.
    suggestedSelections = List([]).tag(sync=True)
    #: `True` if the recommender is currently computing suggested selections, `False` otherwise.
    loadingSuggestions = Bool(False).tag(sync=True)
    #: Floating point value between 0 and 1 indicating the progress towards computing suggested selections.
    loadingSuggestionsProgress = Float(0.0).tag(sync=True)
    #: A flag that, when `True`, indicates that suggested selections should be recomputed.
    recomputeSuggestionsFlag = Bool(False).tag(sync=True)
    #: The bounding box of the screen in data coordinates, used to determine
    #: which points are currently visible and should be included in Suggested
    #: Selections. The bounding box is represented as a list of four values,
    #: consisting of the minimum and maximum *x* values, followed by the minimum
    #: and maximum *y* values.
    suggestedSelectionWindow = List([]).tag(sync=True)
    #: If `True`, recompute suggestions fully but only when less than `PERFORMANCE_SUGGESTIONS_RECOMPUTE`
    #: points are visible.
    performanceSuggestionsMode = Bool(False).tag(sync=True)
    
    #: A list of recent selections, represented in the same format as saved
    #: and suggested selections (including the `selectedIDs` and `currentFrame`)
    #: keys.
    selectionHistory = List([]).tag(sync=True)
    
    #: The supported selection unit for the current embeddings. This corresponds
    #: to the metric used by the embedding's `Neighbors` set.
    selectionUnit = Unicode("").tag(sync=True)
    #: A dictionary that, when populated, indicates that the `Viewer` instance
    #: should perform a radius select. The dictionary should contain three keys:
    #: `centerID` (int - ID of the point around which to select), `frame` (int -
    #: the frame in which to collect nearest neighbors), and `unit` (string -
    #: the metric to use to define nearest neighbors, such as "pixels" or "cosine").
    selectionOrderRequest = Dict({}).tag(sync=True)
    #: A list of tuples representing the results of a selection order request 
    #: (see [`selectionOrderRequest`](#emblaze.viewer.Viewer.selectionOrderRequest)).
    #: Each tuple contains a neighbor ID and its distance to the center point.
    selectionOrder = List([]).tag(sync=True)
    #: The number of points to return IDs and distances for in a selection order
    #: request (see [`selectionOrderRequest`](#emblaze.viewer.Viewer.selectionOrderRequest)).
    selectionOrderCount = Integer(2000)

    #: The name of the color scheme to use to color points in the scatter plot.
    #: Supported color schemes are documented in `src/colorschemes.ts` and
    #: include the following:
    #: * `tableau` (categorical)
    #: * `dark2` (categorical)
    #: * `paired` (categorical)
    #: * `set1` (categorical)
    #: * `set2` (categorical)
    #: * `set3` (categorical)
    #: * `turbo` (continuous)
    #: * `plasma` (continuous)
    #: * `magma` (continuous)
    #: * `viridis` (continuous)
    #: * `RdBu` (continuous)
    #: * `Blues` (continuous)
    #: * `Greens` (continuous)
    #: * `Reds` (continuous)
    #: * `rainbow` (continuous)
    colorScheme = Unicode("").tag(sync=True)
    
    #: String indicating how to compute Star Trails. Valid options are listed
    #: in [`utils.PreviewMode`](utils.html#emblaze.utils.PreviewMode).
    previewMode = Unicode("").tag(sync=True)
    #: Parameters for generating Star Trails. These can be adjusted in the
    #: Emblaze interface in the Settings menu, and consist of the following keys:
    #: * `k`: Integer indicating the number of neighbors to compare between
    #:   frames for each point. This cannot be greater than the Viewer's
    #:   [`storedNumNeighbors`](#emblaze.viewer.Viewer.storedNumNeighbors).
    #: * `similarityThreshold`: Similarity value above which a Star Trail will
    #:   *not* be shown for a point. Similarity is computed as the number of
    #:   neighbors in common between two frames divided by `k`.
    previewParameters = Dict({}).tag(sync=True)
    
    #: List of past interactions with the widget. When [`loggingEnabled`](#emblaze.viewer.Viewer.loggingEnabled)
    #: is set to `True` by the widget, the backend will save the interaction history
    #: to file using the `loggingHelper`.
    interactionHistory = List([]).tag(sync=True)
    #: Flag that, when `True`, indicates that the widget should save interaction
    #: history to a local file. This is used by the frontend to periodically save
    #: interactions when `loggingEnabled` is set to `True`. You should not need
    #: to modify this variable.
    saveInteractionsFlag = Bool(False).tag(sync=True)
    
    #: Flag that, when `True`, enables the widget to periodically save interaction
    #: history and logs to a local file.
    loggingEnabled = Bool(False).tag(sync=True)
    #: A `utils.LoggingHelper` object that handles saving interaction history.
    loggingHelper = None
    
    def __init__(self, *args, **kwargs):
        """
        You may pass additional traitlet values to the `Viewer` constructor
        beyond the ones listed below.
        Args:
            embeddings: An `EmbeddingSet` object.
            thumbnails: A `ThumbnailSet` object.
            file: A file path or file-like object from which to read a comparison JSON file.
        """
        super(Viewer, self).__init__(*args, **kwargs)
        if self.file:
            self.load_comparison(self.file)
        if len(self.embeddings) == 0:
            raise ValueError("Must have at least one embedding.")
        if not all(emb.dimension() == 2 for emb in self.embeddings):
            raise ValueError("All Embeddings must contain 2-dimensional coordinates. Try projecting the embeddings to 2D using the .project() method.")
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
        Infers an appropriate color scheme for the data based on whether the
        data type of the embeddings' `Field.COLOR` field is categorical or
        continuous.
        
        Returns:
            A string name for a default color scheme for the given type of data
            ("tableau" for categorical data or "plasma" for continuous data).
        """
        if len(self.embeddings) == 0:
            return "tableau"
        if self.embeddings[0].guess_data_type(Field.COLOR) == DataType.CATEGORICAL:
            return "tableau"
        return "plasma"
    
    def detect_preview_mode(self):
        """
        Infers the appropriate preview mode to use to generate Star Trails, based
        on whether the neighbors in all the frames are mostly the same or not.
        
        Returns:
            A value from [`utils.PreviewMode`](utils.html#emblaze.utils.PreviewMode)
            indicating how Star Trails should be computed.
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
        if self._autogenerate_embeddings or self.data is None:
            if embeddings is not None:
                self.isLoading = True
                self.neighborData = []
                if self.storedNumNeighbors > 0:
                    n_neighbors = self.storedNumNeighbors 
                else:
                    n_neighbors = self._select_stored_num_neighbors(embeddings)
                self.data = embeddings.to_json(save_neighbors=False)
                self.neighborData = embeddings.get_ancestor_neighbors().to_json(num_neighbors=n_neighbors)
                self.isLoading = False
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
        if self._autogenerate_embeddings or self.thumbnailData is None or len(self.thumbnailData) == 0:
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
            peripheral_points: Unused.
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
        the sidebar. The `selectedIDs` property is used first, followed by
        `alignedIDs` if applicable.
        """
        if len(self.embeddings) <= 1:
            self.frameColors = []
        elif not self.selectedIDs:
            if self.alignedIDs:
                self.frameColors = compute_colors(self.embeddings, self.alignedIDs)
            else:
                if not self._defaultFrameColors:
                    self._defaultFrameColors = compute_colors(self.embeddings, None)
                self.frameColors = self._defaultFrameColors
        else:
            self.frameColors = compute_colors(self.embeddings, self.selectedIDs)

    def _update_selection_unit(self, frame):
        """
        Sets the selection unit if the current frame can be queried for
        distances.
        """
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
        order, distances = hi_d.neighbor_distances(ids=[centerID], n_neighbors=self.selectionOrderCount)
        
        self.selectionOrder = [(int(x), np.round(y, 4)) for x, y in np.vstack([
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
        if len(self.embeddings) <= 1:
            self.performanceSuggestionsMode = False
        else:
            self.performanceSuggestionsMode = len(self.embeddings[0]) * len(self.embeddings) >= PERFORMANCE_SUGGESTIONS_ENABLE
        
    def precompute_suggested_selections(self):
        """
        Computes the suggested selections for all points in the embeddings. This
        is useful to get quick recommendations later, though it may take time to
        generate them upfront. When this method completes, the viewer's
        [`recommender`](#emblaze.viewer.Viewer.recommender) property will be a
        fully loaded `SelectionRecommender` that can be queried for suggestions
        relative to an area of the plot, selection, or set of frames.
        """
        bar = tqdm.tqdm(total=len(self.embeddings) * (len(self.embeddings) - 1), desc='Clustering')
        def progress_fn(progress):
            bar.update(1)
        self.recommender = SelectionRecommender(self.embeddings, progress_fn=progress_fn)
        bar.close()
        
    def _update_suggested_selections_background(self):
        """Function that runs in the background to recompute suggested selections."""
        self.recomputeSuggestionsFlag = False
        if self.loadingSuggestions: 
            return
        

        filter_points = None
        self._update_performance_suggestions_mode()
        if len(self.embeddings) == 1:
            # We cannot generate suggested selections when there is only one embedding
            self.suggestedSelections = []
            return
        if self.performanceSuggestionsMode and (not self.recommender or self.recommender.is_restricted):
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
            if self.recommender is None or (self.recommender.is_restricted and self.performanceSuggestionsMode):
                self.loadingSuggestionsProgress = 0.0
                def progress_fn(progress):
                    self.loadingSuggestionsProgress = progress
                self.recommender = SelectionRecommender(
                    self.embeddings, 
                    progress_fn=progress_fn,
                    frame_idx=self.currentFrame if self.performanceSuggestionsMode else None,
                    preview_frame_idx=self.previewFrame if self.performanceSuggestionsMode and self.previewFrame >= 0 and self.previewFrame != self.currentFrame else None,
                    filter_points=filter_points if self.performanceSuggestionsMode else None)

        
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
            
    def comparison_to_json(self, compressed=True, ancestor_data=True, suggestions=False):
        """
        Saves the data used to produce this comparison to a JSON object. This
        includes the `EmbeddingSet` and the `Thumbnails` that are visualized, as
        well as the immediate and ancestor neighbor data (see below). Ancestor
        neighbors are used to display nearest neighbors in the UI.
        
        Args:
            compressed: If `True`, then save the embeddings in a base-64 encoded
                format to save space.
            ancestor_data: If `True` (default), the full `Embedding` object that
                produces the ancestor neighbors will be stored, including its neighbor
                set. If `False`, only the ancestor neighbors themselves will be
                stored. This can save space if the ancestor embedding is very
                high-dimensional. However, the high-dimensional radius
                select tool will not work if ancestor data is not saved.
            suggestions: If `True` and the viewer has a `recommender` associated
                with it, the recommender will also be serialized.
        
        Returns:
            A JSON-serializable dictionary representing the comparison, including
            all `embeddings`, `thumbnails`, and optionally ancestor data and
            suggestions.
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
            
        if suggestions and self.recommender is not None:
            result["suggestions"] = self.recommender.to_json()
        return result
    
    def load_comparison_from_json(self, data):
        """
        Loads comparison information from a JSON object, including the
        `EmbeddingSet`, `Thumbnails`, and `NeighborSet`.
        
        Args:
            data: A JSON-serializable dictionary generated using
                [`Viewer.comparison_to_json`](#emblaze.viewer.Viewer.comparison_to_json).
                
        Returns:
            The populated `Viewer` object.
        """
        self.isLoading = True
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
        
        if "suggestions" in data:
            self.recommender = SelectionRecommender.from_json(data["suggestions"], self.embeddings)
        
        self.isLoading = False
        return self
                
    def save_comparison(self, file_path_or_buffer, **kwargs):
        """
        Saves the comparison data (`EmbeddingSet`, `Thumbnails`, and `NeighborSet`) to
        the given file path or file-like object. See [`Viewer.comparison_to_json()`](#emblaze.viewer.Viewer.comparison_to_json)
        for available keyword arguments. The comparison can be loaded later by
        specifying a `file` during initialization:
        
        ```python
        w = emblaze.Viewer(file=file_path)
        ```
        
        Args:
            file_path_or_buffer: A file path or file-like object to which to
                write the comparison.
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'w') as file:
                json.dump(self.comparison_to_json(**kwargs), file)
        else:
            # File object
            json.dump(self.comparison_to_json(**kwargs), file_path_or_buffer)
            
    def load_comparison(self, file_path_or_buffer):
        """
        Load the comparison data from the given file path or
        file-like object containing JSON data.
        
        Args:
            file_path_or_buffer: A file path or file-like object from which to
                load the comparison.
        """
        if isinstance(file_path_or_buffer, str):
            # File path
            with open(file_path_or_buffer, 'r') as file:
                return self.load_comparison_from_json(json.load(file))
        else:
            # File object
            return self.load_comparison_from_json(json.load(file_path_or_buffer))
