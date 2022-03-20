URLS=[
"emblaze/index.html",
"emblaze/viewer.html",
"emblaze/frame_colors.html",
"emblaze/neighbors.html",
"emblaze/datasets.html",
"emblaze/utils.html",
"emblaze/thumbnails.html",
"emblaze/recommender.html"
];
INDEX=[
{
"ref":"emblaze",
"url":0,
"doc":"Emblaze is a Jupyter notebook widget for  visually comparing embeddings using animated scatter plots. It bundles an easy-to-use Python API for performing dimensionality reduction on multiple sets of embedding data (including aligning the results for easier comparison), and a full-featured interactive platform for probing and comparing embeddings that runs within a Jupyter notebook cell. ![](assets/cover_art.png)  Installation  Compatibility Note: Note that this widget has been tested using Python >= 3.7. If you are using JupyterLab, please make sure you are running version 3.0 or higher. The widget currently does not support displaying in the VS Code interactive notebook environment. Install Emblaze using  pip :   pip install emblaze   The widget should work out of the box when you run  jupyter lab (see \"Quickstart\" below). _Jupyter Notebook note:_ If you are using Jupyter Notebook 5.2 or earlier, you may also need to enable the nbextension:   jupyter nbextension enable  py  sys-prefix emblaze    Standalone Demo Although the full application is designed to work as a Jupyter widget, you can run a standalone version with most of the available features directly in your browser. To do so, simply run the following command after pip-installing the package (note: you do _not_ need to clone the repository to run the standalone app):   python -m emblaze.server   Visit  localhost:5000 to see the running application. This will allow you to view two demo datasets: one showing five different t-SNE projections of a subset of MNIST digits, and one showing embeddings of the same 5,000 words according to three different data sources (Google News, Wikipedia, and Twitter). To add your own datasets to the standalone app, you can create a directory containing your saved comparison JSON files (see Saving and Loading below), then pass it as a command-line argument:   python -m emblaze.server /path/to/comparisons    -  Quickstart Let's demonstrate the use of Emblaze to compare dimensionality reduction plots of the MNIST dataset. In a Jupyter notebook, use the following code to retrieve the MNIST dataset (or load your own feature and label data as variables  X and  Y ):   from tensorflow.keras.datasets import mnist import numpy as np _, (x_test, y_test) = mnist.load_data()  Get a random subset of the data indexes = np.random.choice(x_test.shape[0], size=2000, replace=False) X = x_test[indexes].reshape(-1, 28 28) Y = y_test[indexes]   The Emblaze viewer takes two basic objects as input for visualization: an [ EmbeddingSet ](datasets.html emblaze.datasets.EmbeddingSet), which contains one or more coordinate matrices as well as color-coding information, and a [ Thumbnails ](thumbnails.html emblaze.thumbnails.Thumbnails) object, which describes how each point in the visualization should be described (typically using a combination of text and/or images). First, let's construct the  EmbeddingSet . To do so, we first create a high-dimensional  Embedding to contain the  X and  Y matrices we defined above. We will also compute the nearest neighbors for each point, which will be displayed in the sidebar of the visualization.   import emblaze emb = emblaze.Embedding({emblaze.Field.POSITION: X, emblaze.Field.COLOR: Y}, metric='cosine') emb.compute_neighbors()   Next, we can project this embedding five times using random initializations of UMAP (a common dimensionality reduction technique). We compute neighbors here again, as we would like to study neighborhood differences in the DR plots. (If we were comparing multiple high-dimensional coordinate sets, such as different word embedding models, we would not compute neighbors again here. See the [Defining Comparisons]( defining-comparisons) section below for more details.)   variants = emblaze.EmbeddingSet([ emb.project(method=emblaze.ProjectionTechnique.UMAP) for _ in range(5) ]) variants.compute_neighbors(metric='euclidean')   Now, let's create some  thumbnails to represent these points visually. Since MNIST consists of images, we will use the  ImageThumbnails class:   thumbnails = emblaze.ImageThumbnails(X.reshape(-1, 28, 28, 1   Finally, we can initialize an [ emblaze.Viewer ](viewer.html emblaze.viewer.Viewer) object, which renders the visualization when printed:   w = emblaze.Viewer(embeddings=variants, thumbnails=thumbnails) w   You should see the Emblaze visualization appear in the cell output: ![](assets/mnist.png)  -  Using Emblaze Once you've loaded the Emblaze viewer, you can interact with the plot to start making comparisons of points and clusters. Emblaze offers the following features to support comparative analysis:  Star Trail visualization When you click a  frame thumbnail in the browser to the left of the main scatter plot, widening lines appear on the plot radiating out from particular points. This visualization, which we call a Star Trail visualization, highlights points whose neighbor sets change the most from one frame to another. When you click the frame thumbnail again, the points will smoothly animate along their Star Trails to arrive at their positions in the new frame.  Controllable animation When in the comparison view (and the Star Trail plot is visible), you can manually control the interpolation of the plot from one frame to the other. Simply drag the slider in the bottom right corner of the plot. The plot remains interactive while in this interpolated state, so you can drag the slider halfway and then find points of interest.  Selections You can make selections in Emblaze by clicking points in the scatter plot. You can add to the selection by holding Cmd (Mac) or Ctrl (other operating systems) and clicking. Additionally, you can select multiple points at once by holding Cmd/Ctrl and click-and-dragging to define a lasso region. To select points within a  high-dimensional radius of a point, select the central point, then click Start Radius Select. You can also read and write the selection programmatically by accessing the Viewer's [ selectedIDs ](viewer.html emblaze.viewer.Viewer.selectedIDs) property.  Nearest neighbor lines When a single point is selected, blue lines radiate from the selected point to its nearest neighbors in the high-dimensional space (see [Ancestor Neighbors]( recent-and-ancestor-neighbors) for more details). You can configure how many of these neighbors are highlighted by changing the Viewer's [ numNeighbors ](viewer.html emblaze.viewer.Viewer.numNeighbors) property, or by going to the Settings menu in the lower-right corner of the widget interface.  Selection info As you define selections, information about the selected points and their nearest neighborhoods is shown in the sidebar to the right of the plot under the  Current tab. At the top, you can see the names, descriptions, and/or images defined by the [ Thumbnails ](thumbnails.html emblaze.thumbnails.Thumbnails) object for the selected points. In the Neighbors section, you can see the top 10 nearest neighbors of the selection, which are weighted by their total rank with respect to each selected point. When you are comparing two frames (see above), the Current sidebar pane also updates to show you Common Changes in the nearest neighborhood of the selection between the two frames.  Aligning and Isolating For large datasets, it may be helpful to reduce the number of points visible in the scatter plot in order to focus on a selection of interest. To do so, select a set of points and then click the  Isolate button. This will limit the visible points to the selected points and their high-dimensional nearest neighbors in all frames. You can also set the visible points programmatically by accessing the Viewer's [ filterIDs ](viewer.html emblaze.viewer.Viewer.filterIDs) property. Relatedly, when animating between frames you may wish to minimize unnecessary motion of a set of points (for example, if a cluster rotates in a DR plot due to random initialization effects). To minimize the motion of a set of points with respect to the rest of the plot, select the points and click  Align . You can also do this programmatically by setting the Viewer's [ alignedIDs ](viewer.html emblaze.viewer.Viewer.alignedIDs) property.  Suggested Selections Emblaze includes a novel clustering algorithm designed to surface groups of points that change meaningfully from one frame to another. Check out the Suggested pane of the sidebar to see clustering recommendations relevant to the area of the plot you are currently looking at.  Color Stripes To highlight variation between different frames, each frame thumbnail in the browser to the left of the visualization has a color associated with it. These colors are dynamically chosen to reflect  differences between the frames with respect to the  current selection. In other words, frames in which the selected points are arranged similarly will have similar colors, while frames that have highly divergent arrangements of the points will have starkly different colors. See the [ compute_colors ](frame_colors.html emblaze.frame_colors.compute_colors) function for more information.  Interactive Notebook Analysis Once you have loaded a  Viewer instance in the notebook, you can read and write its properties to dynamically work with the visualization. The following properties are reactive: - [ embeddings ](viewer.html emblaze.viewer.Viewer.embeddings) ( EmbeddingSet ) Modify this to change the entire dataset that is displayed. - [ thumbnails ](viewer.html emblaze.viewer.Viewer.thumbnails) ( Thumbnails ) Represents the image or text thumbnails displayed on hover and click. - [ currentFrame ](viewer.html emblaze.viewer.Viewer.currentFrame) ( int ) The current frame or embedding space that is being viewed (from  0 to  len(embeddings) ). - [ selectedIDs ](viewer.html emblaze.viewer.Viewer.selectedIDs) ( List[int] ) The selected ID numbers. Unless you provide custom IDs when constructing the  EmbeddingSet , these are simply zero-indexed integers. - [ alignedIDs ](viewer.html emblaze.viewer.Viewer.alignedIDs) ( List[int] ) The IDs of the points to which the embedding spaces are aligned (same format as  selectedIDs ). Alignment is computed relative to the positions of the points in the current frame. - [ filterIDs ](viewer.html emblaze.viewer.Viewer.filterIDs) ( List[int] ) The IDs of the points that are visible in the plot (same format as  selectedIDs ). - [ colorScheme ](viewer.html emblaze.viewer.Viewer.colorScheme) ( string ) The name of a color scheme to use to render the points. A variety of color schemes are available, listed in  src/colorschemes.ts . This property can also be changed in the Settings panel of the widget. - [ previewMode ](viewer.html emblaze.viewer.Viewer.previewMode) ( string ) The method to use to generate preview lines, which should be one of the values in [ utils.PreviewMode ](utils.html emblaze.utils.PreviewMode).  Saving and Loading You can save the data used to make comparisons to JSON, so that it is easy to load them again in Jupyter or the standalone application without re-running the embedding/projection code. Comparisons consist of an  EmbeddingSet (containing the positions of the points in each 2D projection), a  Thumbnails object (dictating how to display each point), and one or more  NeighborSet s (which contain the nearest-neighbor sets used for comparison and display). To save a comparison, call the [ save_comparison() ](viewer.html emblaze.viewer.Viewer.save_comparison) method on the  Viewer . Note that if you are using high-dimensional nearest neighbors (most use cases), this method by default saves both the high-dimensional coordinates and the nearest-neighbor IDs. This can create files ranging from hundreds of MB to GBs. To store only the nearest neighbor IDs, pass  ancestor_data=False as a keyword argument. Note that if you disable storing the high-dimensional coordinates, you will be unable to use tools that depend on _distances_ in hi-D space (such as the high-dimensional radius select). To load a comparison, simply initialize the  Viewer as follows:   w = emblaze.Viewer(file=\"/path/to/comparison.json\")    -  Defining Comparisons Because Emblaze only depends on having a set of embeddings and thumbnails, it supports making a wide variety of comparisons. In the simplest case, the matrix of 2D coordinates, color values, and text descriptions is sufficient to populate the visualization. However, things get a little trickier when we start to incorporate nearest-neighbor analysis, a central part of defining what level we are performing comparison on.  On which set of coordinates should the nearest neighbors be computed? Emblaze gives you the flexibility to choose which neighbor sets are displayed under which contexts, but doing so requires some understanding of how neighbors are used under the hood.  Inherited Neighbor Sets When you call [ compute_neighbors ](datasets.html emblaze.datasets.Embedding.compute_neighbors) on an  Embedding or  EmbeddingSet instance, a [ Neighbors ](neighbors.html emblaze.neighbors.Neighbors) object is created that contains the nearest neighbor matrix for the coordinates defined in that embedding object. Now, when you create additional  Embedding or  EmbeddingSet objects that  derive from the previously-defined embeddings, the  Neighbors object is inherited by default. This means that if you project the embedding down to 2D using the [ project() ](datasets.html emblaze.datasets.EmbeddingSet.project) method, the nearest neighborhoods that are shown in the Star Trail or sidebar will be from the  high-dimensional space . This is often desirable, since dimensionality reduction plots are known to  distort nearest neighborhoods for large datasets. However, sometimes we do want to compare nearest neighborhoods in the projected data (such as in the Quickstart example above, where we compared five different random initializations of UMAP). If you'd like the differences in nearest neighborhoods to be shown in the Star Trail visualization, simply call [ compute_neighbors ](datasets.html emblaze.datasets.EmbeddingSet.compute_neighbors) again on the dimensionally-reduced  EmbeddingSet .  Recent and Ancestor Neighbors It is worth noting that sometimes we want the nearest neighbors shown in the Current sidebar pane to be different than those used to compute Star Trails, Suggested Selections, Color Stripes, etc. To support this, Emblaze keeps a parent pointer for each  Embedding object as you generate them, e.g. using the  project() method. At visualization time, Emblaze retrieves two neighbor sets from the parent tree (both of these may correspond to the same  Neighbors object, but not necessarily). Each of these two sets are used in different parts of the visualization:   Recent neighbors. These neighbors, which can be accessed using the [ get_recent_neighbors ](datasets.html emblaze.datasets.EmbeddingSet.get_recent_neighbors) method on  EmbeddingSet or  Embedding , are the neighbors inherited from the  most recent parent of the current embedding (or the current one, if it has neighbors). These are used to perform  all algorithmic comparisons of frames, including [Star Trail visualizations]( star-trail-visualization), [Suggested Selections]( suggested-selections), and [Color Stripes]( color-stripes).   Ancestor neighbors. These neighbors can be accessed using the [ get_ancestor_neighbors ](datasets.html emblaze.datasets.EmbeddingSet.get_ancestor_neighbors) method on  EmbeddingSet or  Embedding . They are the neighbors computed in the  oldest parent of the current embedding (which may be the current one if it has no parents with computed neighbors). These are the neighbors displayed in the [sidebar]( selection-info) and by the [nearest neighbor lines]( nearest-neighbor-lines), and are typically used to communicate the high-dimensional nearest neighbors regardless of the level at which embeddings are being compared."
},
{
"ref":"emblaze.viewer",
"url":1,
"doc":"Defines the main Emblaze visualization class,  emblaze.Viewer ."
},
{
"ref":"emblaze.viewer.Viewer",
"url":1,
"doc":"Represents and maintains the state of an interactive Emblaze interface to display in a Jupyter notebook. The basic instantiation of an Emblaze viewer proceeds as follows:   embeddings = emblaze.EmbeddingSet( .) thumbnails = emblaze.TextThumbnails( .) w = emblaze.Viewer(embeddings=embeddings, thumbnails=thumbnails) w   You may pass additional traitlet values to the  Viewer constructor beyond the ones listed below. Args: embeddings: An  EmbeddingSet object. thumbnails: A  ThumbnailSet object. file: A file path or file-like object from which to read a comparison JSON file."
},
{
"ref":"emblaze.viewer.Viewer.thread_starter",
"url":1,
"doc":"A trait which allows any value."
},
{
"ref":"emblaze.viewer.Viewer.embeddings",
"url":1,
"doc":"An [ EmbeddingSet ](datasets.html emblaze.datasets.EmbeddingSet) containing one or more embeddings to visualize. The coordinates contained in this  EmbeddingSet must be 2-dimensional."
},
{
"ref":"emblaze.viewer.Viewer.data",
"url":1,
"doc":"The JSON-serializable data passed to the frontend. You should not need to modify this variable."
},
{
"ref":"emblaze.viewer.Viewer.file",
"url":1,
"doc":"A file path or file-like object from which to read an embedding comparison (see [ save_comparison ](viewer.html emblaze.viewer.Viewer.save_comparison ."
},
{
"ref":"emblaze.viewer.Viewer.plotPadding",
"url":1,
"doc":"Padding around the plot in data coordinates."
},
{
"ref":"emblaze.viewer.Viewer.isLoading",
"url":1,
"doc":" True if the widget is currently loading a comparison from file,  False otherwise."
},
{
"ref":"emblaze.viewer.Viewer.currentFrame",
"url":1,
"doc":"The index of the currently-viewing frame in the Viewer's [ embeddings ]( emblaze.viewer.Viewer.embeddings)."
},
{
"ref":"emblaze.viewer.Viewer.previewFrame",
"url":1,
"doc":"The index of the previewed frame in the Viewer's [ embeddings ]( emblaze.viewer.Viewer.embeddings). The previewed frame is the frame to which points move when the Star Trail visualization is active."
},
{
"ref":"emblaze.viewer.Viewer.alignedFrame",
"url":1,
"doc":"The index of the aligned frame in the Viewer's [ embeddings ]( emblaze.viewer.Viewer.embeddings). When the frames are aligned to a selection, they are anchored to the same position as before in this frame only."
},
{
"ref":"emblaze.viewer.Viewer.selectedIDs",
"url":1,
"doc":"A list of integer IDs corresponding to the selected points. By default, these are zero-indexed and span the range from zero to the number of points in each embedding."
},
{
"ref":"emblaze.viewer.Viewer.alignedIDs",
"url":1,
"doc":"A list of integer IDs corresponding to the aligned points (points selected to minimize motion across frames). By default, these are zero-indexed and span the range from zero to the number of points in each embedding."
},
{
"ref":"emblaze.viewer.Viewer.filterIDs",
"url":1,
"doc":"A list of integer IDs corresponding to the filtered points (a subset of points selected to be visible in the plot). By default, these are zero-indexed and span the range from zero to the number of points in each embedding."
},
{
"ref":"emblaze.viewer.Viewer.numNeighbors",
"url":1,
"doc":"The number of neighbors to show in nearest neighbor lines and the detail sidebar. This number cannot be greater than [ storedNumNeighbors ]( emblaze.viewer.Viewer.storedNumNeighbors)."
},
{
"ref":"emblaze.viewer.Viewer.storedNumNeighbors",
"url":1,
"doc":"The number of nearest neighbors to store for each point in the frontend visualization. This number cannot be greater than the number of neighbors computed in the embeddings'  Neighbors objects. This is 100 by default, but will be automatically reduced to improve performance and memory usage when many points or frames are visualized. This value can be configured in the initialization of the  Viewer instance."
},
{
"ref":"emblaze.viewer.Viewer.frameColors",
"url":1,
"doc":"The colors used to represent each frame in the sidebar, stored as lists of 3 HSV components each."
},
{
"ref":"emblaze.viewer.Viewer.frameTransformations",
"url":1,
"doc":"Transformation matrices that result in an alignment of frames to the viewer's current [ alignedIDs ]( emblaze.viewer.Viewer.alignedIDs). The matrices are represented as 3x3 nested lists."
},
{
"ref":"emblaze.viewer.Viewer.thumbnails",
"url":1,
"doc":"A [ Thumbnails ](thumbnails.html emblaze.thumbnails.Thumbnails) instance containing text and/or image descriptions for the IDs of the points provided in [ embeddings ]( emblaze.viewer.Viewer.embeddings)."
},
{
"ref":"emblaze.viewer.Viewer.thumbnailData",
"url":1,
"doc":"A JSON-serializable dictionary of thumbnail info. You should not need to modify this variable."
},
{
"ref":"emblaze.viewer.Viewer.neighborData",
"url":1,
"doc":"A JSON-serializable list of high-dimensional neighbors, containing one dictionary corresponding to each  Embedding . You should not need to modify this variable."
},
{
"ref":"emblaze.viewer.Viewer.saveSelectionFlag",
"url":1,
"doc":"Boolean marking that the current state of the visualization should be saved to file. The current values of [ selectionName ]( emblaze.viewer.Viewer.selectionName) and [ selectionDescription ]( emblaze.viewer.Viewer.selectionDescription) will be used."
},
{
"ref":"emblaze.viewer.Viewer.selectionName",
"url":1,
"doc":"The name of the selection to save."
},
{
"ref":"emblaze.viewer.Viewer.selectionDescription",
"url":1,
"doc":"A description of the selection to save."
},
{
"ref":"emblaze.viewer.Viewer.allowsSavingSelections",
"url":1,
"doc":"Boolean indicating whether selection saving and restoring should be enabled in the interface."
},
{
"ref":"emblaze.viewer.Viewer.visibleSidebarPane",
"url":1,
"doc":"The currently-visible sidebar pane, enumerated in  emblaze.utils.SidebarPane ."
},
{
"ref":"emblaze.viewer.Viewer.selectionList",
"url":1,
"doc":"A list of saved selections, to be displayed in the Saved sidebar pane."
},
{
"ref":"emblaze.viewer.Viewer.recommender",
"url":1,
"doc":"The [ SelectionRecommender ](recommender.html emblaze.recommender.SelectionRecommender) responsible for generating suggested selections."
},
{
"ref":"emblaze.viewer.Viewer.suggestedSelections",
"url":1,
"doc":"The current list of suggested selections. Each suggestion is represented as a dictionary in the same format as a saved selection, including keys for  currentFrame ,  selectedIDs ,  alignedIDs , and  filterIDs ."
},
{
"ref":"emblaze.viewer.Viewer.loadingSuggestions",
"url":1,
"doc":" True if the recommender is currently computing suggested selections,  False otherwise."
},
{
"ref":"emblaze.viewer.Viewer.loadingSuggestionsProgress",
"url":1,
"doc":"Floating point value between 0 and 1 indicating the progress towards computing suggested selections."
},
{
"ref":"emblaze.viewer.Viewer.recomputeSuggestionsFlag",
"url":1,
"doc":"A flag that, when  True , indicates that suggested selections should be recomputed."
},
{
"ref":"emblaze.viewer.Viewer.suggestedSelectionWindow",
"url":1,
"doc":"The bounding box of the screen in data coordinates, used to determine which points are currently visible and should be included in Suggested Selections. The bounding box is represented as a list of four values, consisting of the minimum and maximum  x values, followed by the minimum and maximum  y values."
},
{
"ref":"emblaze.viewer.Viewer.performanceSuggestionsMode",
"url":1,
"doc":"If  True , recompute suggestions fully but only when less than  PERFORMANCE_SUGGESTIONS_RECOMPUTE points are visible."
},
{
"ref":"emblaze.viewer.Viewer.selectionHistory",
"url":1,
"doc":"A list of recent selections, represented in the same format as saved and suggested selections (including the  selectedIDs and  currentFrame ) keys."
},
{
"ref":"emblaze.viewer.Viewer.selectionUnit",
"url":1,
"doc":"The supported selection unit for the current embeddings. This corresponds to the metric used by the embedding's  Neighbors set."
},
{
"ref":"emblaze.viewer.Viewer.selectionOrderRequest",
"url":1,
"doc":"A dictionary that, when populated, indicates that the  Viewer instance should perform a radius select. The dictionary should contain three keys:  centerID (int - ID of the point around which to select),  frame (int - the frame in which to collect nearest neighbors), and  unit (string - the metric to use to define nearest neighbors, such as \"pixels\" or \"cosine\")."
},
{
"ref":"emblaze.viewer.Viewer.selectionOrder",
"url":1,
"doc":"A list of tuples representing the results of a selection order request (see [ selectionOrderRequest ]( emblaze.viewer.Viewer.selectionOrderRequest . Each tuple contains a neighbor ID and its distance to the center point."
},
{
"ref":"emblaze.viewer.Viewer.selectionOrderCount",
"url":1,
"doc":"The number of points to return IDs and distances for in a selection order request (see [ selectionOrderRequest ]( emblaze.viewer.Viewer.selectionOrderRequest ."
},
{
"ref":"emblaze.viewer.Viewer.colorScheme",
"url":1,
"doc":"The name of the color scheme to use to color points in the scatter plot. Supported color schemes are documented in  src/colorschemes.ts and include the following:   tableau (categorical)   dark2 (categorical)   paired (categorical)   set1 (categorical)   set2 (categorical)   set3 (categorical)   turbo (continuous)   plasma (continuous)   magma (continuous)   viridis (continuous)   RdBu (continuous)   Blues (continuous)   Greens (continuous)   Reds (continuous)   rainbow (continuous)"
},
{
"ref":"emblaze.viewer.Viewer.previewMode",
"url":1,
"doc":"String indicating how to compute Star Trails. Valid options are listed in [ utils.PreviewMode ](utils.html emblaze.utils.PreviewMode)."
},
{
"ref":"emblaze.viewer.Viewer.previewParameters",
"url":1,
"doc":"Parameters for generating Star Trails. These can be adjusted in the Emblaze interface in the Settings menu, and consist of the following keys:   k : Integer indicating the number of neighbors to compare between frames for each point. This cannot be greater than the Viewer's [ storedNumNeighbors ]( emblaze.viewer.Viewer.storedNumNeighbors).   similarityThreshold : Similarity value above which a Star Trail will  not be shown for a point. Similarity is computed as the number of neighbors in common between two frames divided by  k ."
},
{
"ref":"emblaze.viewer.Viewer.interactionHistory",
"url":1,
"doc":"List of past interactions with the widget. When [ loggingEnabled ]( emblaze.viewer.Viewer.loggingEnabled) is set to  True by the widget, the backend will save the interaction history to file using the  loggingHelper ."
},
{
"ref":"emblaze.viewer.Viewer.saveInteractionsFlag",
"url":1,
"doc":"Flag that, when  True , indicates that the widget should save interaction history to a local file. This is used by the frontend to periodically save interactions when  loggingEnabled is set to  True . You should not need to modify this variable."
},
{
"ref":"emblaze.viewer.Viewer.loggingEnabled",
"url":1,
"doc":"Flag that, when  True , enables the widget to periodically save interaction history and logs to a local file."
},
{
"ref":"emblaze.viewer.Viewer.loggingHelper",
"url":1,
"doc":"A  utils.LoggingHelper object that handles saving interaction history."
},
{
"ref":"emblaze.viewer.Viewer.refresh_saved_selections",
"url":1,
"doc":"Updates the selectionList property, which is displayed in the sidebar under the Saved tab.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.detect_color_scheme",
"url":1,
"doc":"Infers an appropriate color scheme for the data based on whether the data type of the embeddings'  Field.COLOR field is categorical or continuous. Returns: A string name for a default color scheme for the given type of data (\"tableau\" for categorical data or \"plasma\" for continuous data).",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.detect_preview_mode",
"url":1,
"doc":"Infers the appropriate preview mode to use to generate Star Trails, based on whether the neighbors in all the frames are mostly the same or not. Returns: A value from [ utils.PreviewMode ](utils.html emblaze.utils.PreviewMode) indicating how Star Trails should be computed.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.reset_state",
"url":1,
"doc":"Resets the view state of the widget.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.reset_alignment",
"url":1,
"doc":"Removes any transformations applied to the embedding frames.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.align_to_points",
"url":1,
"doc":"Re-align the projections to minimize motion for the given point IDs. Uses currentFrame as the base frame. Updates the self.frameTransformations traitlet. Args: point_ids: Iterable of point IDs to use for alignment. peripheral_points: Unused.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.update_frame_colors",
"url":1,
"doc":"Updates the colors of the color stripes next to each frame thumbnail in the sidebar. The  selectedIDs property is used first, followed by  alignedIDs if applicable.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.precompute_suggested_selections",
"url":1,
"doc":"Computes the suggested selections for all points in the embeddings. This is useful to get quick recommendations later, though it may take time to generate them upfront. When this method completes, the viewer's [ recommender ]( emblaze.viewer.Viewer.recommender) property will be a fully loaded  SelectionRecommender that can be queried for suggestions relative to an area of the plot, selection, or set of frames.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.comparison_to_json",
"url":1,
"doc":"Saves the data used to produce this comparison to a JSON object. This includes the  EmbeddingSet and the  Thumbnails that are visualized, as well as the immediate and ancestor neighbor data (see below). Ancestor neighbors are used to display nearest neighbors in the UI. Args: compressed: If  True , then save the embeddings in a base-64 encoded format to save space. ancestor_data: If  True (default), the full  Embedding object that produces the ancestor neighbors will be stored, including its neighbor set. If  False , only the ancestor neighbors themselves will be stored. This can save space if the ancestor embedding is very high-dimensional. However, the high-dimensional radius select tool will not work if ancestor data is not saved. suggestions: If  True and the viewer has a  recommender associated with it, the recommender will also be serialized. Returns: A JSON-serializable dictionary representing the comparison, including all  embeddings ,  thumbnails , and optionally ancestor data and suggestions.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.load_comparison_from_json",
"url":1,
"doc":"Loads comparison information from a JSON object, including the  EmbeddingSet ,  Thumbnails , and  NeighborSet . Args: data: A JSON-serializable dictionary generated using [ Viewer.comparison_to_json ]( emblaze.viewer.Viewer.comparison_to_json). Returns: The populated  Viewer object.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.save_comparison",
"url":1,
"doc":"Saves the comparison data ( EmbeddingSet ,  Thumbnails , and  NeighborSet ) to the given file path or file-like object. See [ Viewer.comparison_to_json() ]( emblaze.viewer.Viewer.comparison_to_json) for available keyword arguments. The comparison can be loaded later by specifying a  file during initialization:   w = emblaze.Viewer(file=file_path)   Args: file_path_or_buffer: A file path or file-like object to which to write the comparison.",
"func":1
},
{
"ref":"emblaze.viewer.Viewer.load_comparison",
"url":1,
"doc":"Load the comparison data from the given file path or file-like object containing JSON data. Args: file_path_or_buffer: A file path or file-like object from which to load the comparison.",
"func":1
},
{
"ref":"emblaze.frame_colors",
"url":2,
"doc":"A helper module to compute HSV colors for each frame in an animated DR plot. The colors are chosen such that the perceptual distance between colors corresponds to the difference between the frames, with respect to some set of points of interest."
},
{
"ref":"emblaze.frame_colors.compute_colors",
"url":2,
"doc":"Computes HSV colors for each frame. Args: frames: A list of Embeddings. ids_of_interest: A list of IDs to limit distance calculation to. If None, uses the full contents of each frame. scale_factor: Amount by which to scale the color wheel. Values larger than 1 effectively make the colors more saturated and appear more different. Returns: A list of HSV colors, expressed as tuples of (hue, saturation, value).",
"func":1
},
{
"ref":"emblaze.neighbors",
"url":3,
"doc":"Defines model classes to compute and store nearest neighbor sets that can be inherited across different  Embedding objects."
},
{
"ref":"emblaze.neighbors.Neighbors",
"url":3,
"doc":"An object representing a serializable set of nearest neighbors within an embedding. The  Neighbors object simply stores a matrix of integer IDs, where rows correspond to points in the embedding and columns are IDs of neighbors in order of proximity to each point. These neighbors can be accessed through the  values property. This constructor should typically not be used - use [ Neighbors.compute ]( emblaze.neighbors.Neighbors.compute) instead. Args: values: Matrix of n x D high-dimensional positions ids: If supplied, a list of IDs for the points in the matrix metric: Distance metric to use to compute neighbors (can be any supported metric for  sklearn.neighbors.NearestNeighbors ) n_neighbors: Number of neighbors to compute and save clf: The  NearestNeighbors object (only used when loading a  Neighbors object from file)"
},
{
"ref":"emblaze.neighbors.Neighbors.compute",
"url":3,
"doc":"Compute a nearest-neighbor set using a given metric. Args: pos: Matrix of n x D high-dimensional positions ids: If supplied, a list of IDs for the points in the matrix metric: Distance metric to use to compute neighbors (can be any supported metric for  sklearn.neighbors.NearestNeighbors ) n_neighbors: Number of neighbors to compute and save Returns: An initialized  Neighbors object containing computed neighbors.",
"func":1
},
{
"ref":"emblaze.neighbors.Neighbors.index",
"url":3,
"doc":"Returns the index(es) of the given IDs.",
"func":1
},
{
"ref":"emblaze.neighbors.Neighbors.calculate_neighbors",
"url":3,
"doc":"",
"func":1
},
{
"ref":"emblaze.neighbors.Neighbors.concat",
"url":3,
"doc":"Concatenates the two Neighbors together, discarding the original classifier.",
"func":1
},
{
"ref":"emblaze.neighbors.Neighbors.to_json",
"url":3,
"doc":"Serializes the neighbors to a JSON object.",
"func":1
},
{
"ref":"emblaze.neighbors.Neighbors.from_json",
"url":3,
"doc":"",
"func":1
},
{
"ref":"emblaze.neighbors.NeighborSet",
"url":3,
"doc":"An object representing a serializable collection of Neighbors objects."
},
{
"ref":"emblaze.neighbors.NeighborSet.to_json",
"url":3,
"doc":"Serializes the list of Neighbors objects to JSON.",
"func":1
},
{
"ref":"emblaze.neighbors.NeighborSet.from_json",
"url":3,
"doc":"",
"func":1
},
{
"ref":"emblaze.neighbors.NeighborSet.identical",
"url":3,
"doc":"Returns True if all Neighbors objects within this NeighborSet are equal to each other.",
"func":1
},
{
"ref":"emblaze.datasets",
"url":4,
"doc":"Defines model classes to store embedding data in both high-dimensional and dimensionally-reduced spaces."
},
{
"ref":"emblaze.datasets.Embedding",
"url":4,
"doc":"A single set of high-dimensional embeddings, which can be represented as an n x k 2D numpy array (n = number of points, k = dimensionality). Args: data: Dictionary of data fields. Must contain two fields: [ emblaze.Field.POSITION ](utils.html emblaze.utils.Field.POSITION) (an n x k numpy array of coordinates), and [ emblaze.Field.COLOR ](utils.html emblaze.utils.Field.COLOR) (a length-n vector of 'color' values, which can be either continuous quantitative values or string labels to assign categorical colors to). ids: An optional array of ID numbers corresponding to each of the n points in data. If not provided, the point IDs will simply be assigned as  np.arange(n) . label: A string label describing this embedding. In an  emblaze.Viewer instance, this will be displayed as the name of this embedding frame in the thumbnail sidebar. metric: The distance metric used to compute distances and nearest neighbors. Most high-dimensional embeddings should use 'cosine', but this can be set to any distance metric supported by scikit-learn. n_neighbors: The number of neighbors to precompute and save when compute_neighbors() is called. neighbors: an optional Neighbors object to initialize with, if the nearest neighbors for the embedding have already previously been computed. parent: The parent Embedding of this Embedding object. This is automatically assigned when creating new Embedding objects with the  project() method."
},
{
"ref":"emblaze.datasets.Embedding.copy",
"url":4,
"doc":"",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.copy_with_fields",
"url":4,
"doc":"",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.concat",
"url":4,
"doc":"Returns a new  Embedding with this  Embedding and the given one stacked together. Must have the same set of fields, and a disjoint set of IDs.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.get_root",
"url":4,
"doc":"Returns the root parent of this embedding.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.has_neighbors",
"url":4,
"doc":"",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.any_ancestor_has_neighbors",
"url":4,
"doc":"Returns  True if any of the Embeddings in the parent tree have embeddings computed.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.get_neighbors",
"url":4,
"doc":"",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.find_ancestor_neighbor_embedding",
"url":4,
"doc":"Returns the  Embedding that is furthest along this  Embedding 's parent tree and has a neighbor set.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.get_ancestor_neighbors",
"url":4,
"doc":"Gets the neighbor set of the  Embedding that is furthest along this  Embedding 's ancestry tree and has a neighbor set.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.find_recent_neighbor_embedding",
"url":4,
"doc":"Returns the  Embedding that is closest to this  Embedding in the parent tree (including this  Embedding ) that has a neighbor set.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.get_recent_neighbors",
"url":4,
"doc":"Gets the neighbor set of the  Embedding that is closest to this  Embedding in the parent tree (including itself) and that has a neighbor set.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.dimension",
"url":4,
"doc":"Returns the dimensionality of the  Field.POSITION field.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.project",
"url":4,
"doc":"Projects this embedding space into a lower dimensionality. The method parameter can be a callable, which will define a dimensionality reduction technique that takes as input a numpy array and a list of IDs, as well as any keyword arguments given to the params argument of this method, and returns a dimension-reduced matrix. If no metric is provided in the keyword params, the default metric of this Embedding is used. Returns: A new  Embedding object with the  Field.POSITION value set to the result of the projection.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.get_relations",
"url":4,
"doc":"Computes a mapping from the IDs in this embedding to the positions in the other embedding (used for  AlignedUMAP ).",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.compute_neighbors",
"url":4,
"doc":"Computes and saves a set of nearest neighbors in this embedding according to the  Field.POSITION values. This can be accessed after completing this step through the  neighbors property. If this  Embedding is copied or projected, it will inherit the same  Neighbors . Args: n_neighbors: The number of neighbors to compute for each point. If not provided, the default  n_neighbors for this  Embedding is used. metric: The distance metric to use to compute neighbors. If not provided, the default  metric for this  Embedding is used.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.clear_neighbors",
"url":4,
"doc":"Removes the saved  Neighbors associated with this  Embedding . This can be used to determine which Neighbors is returned by  get_ancestor_neighbors() .",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.clear_upstream_neighbors",
"url":4,
"doc":"Clears the neighbor sets for all  Embedding s in the parent tree of this  Embedding (but not this one).",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.neighbor_distances",
"url":4,
"doc":"Returns the list of nearest neighbors for each of the given IDs and the distances to each of those points. This does NOT use the  Neighbors object, and is therefore based only on the locations of the points in this  Embedding (not potentially on its parents).",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.distances",
"url":4,
"doc":"Returns the pairwise distances from the given IDs to each other (or all points to each other, if ids is None). If the metric is not provided, the default metric for this  Embedding object is used.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.within_bbox",
"url":4,
"doc":"Returns the list of IDs whose points are within the given bounding box. Only supports 2D embeddings. Args: bbox: The bounding box within which to retrieve points, specified as (xmin, xmax, ymin, ymax). Returns: A list of ID values corresponding to points within the bounding box.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.to_json",
"url":4,
"doc":"Converts this embedding into a JSON object. If the embedding is 2D, saves coordinates as separate x and y fields; otherwise, saves coordinates as n x d arrays. Args: compressed: whether to format JSON objects using base64 strings instead of as human-readable float arrays save_neighbors: If  True , serialize the  Neighbors object within the embedding JSON. Returns: A JSON-serializable dictionary representing the embedding.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.from_json",
"url":4,
"doc":"Builds an Embedding object from the given JSON object. Args: data: The JSON-serializable dictionary representing the embedding. label: A string label to use to represent this embedding. parent: An  Embedding to record as the new  Embedding 's parent. Returns: An  Embedding instance loaded with the specified data.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.save",
"url":4,
"doc":"Save this Embedding object to the given file path or file-like object (in JSON format). See [ Embedding.to_json ]( emblaze.datasets.Embedding.to_json) for acceptable keyword arguments. Args: file_path_or_buffer: A file path or file-like object to write the embedding to.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.load",
"url":4,
"doc":"Load the Embedding object from the given file path or file-like object containing JSON data. Args: file_path_or_buffer: A file path or file-like object to read the embedding from.",
"func":1
},
{
"ref":"emblaze.datasets.Embedding.align_to",
"url":4,
"doc":"Aligns this embedding to the base frame. The frames are aligned based on the keys they have in common. This requires both embeddings to have a dimensionality of 2. Args: base_frame: An Embedding to use as the base. frame: An Embedding to transform. ids: Point IDs to use for alignment (default None, which results in an alignment using the intersection of IDs between the two frames). return_transform: If true, return just the Affine object instead of the rotated data. base_transform: If not None, an Affine object representing the transformation to apply to the base frame before aligning. allow_flips: If true, test inversions as possible candidates for alignment. Returns: A new  Embedding object representing the second input frame (the first input frame is assumed to stay the same). Or, if  return_transform is  True , returns the optimal transformation as an  Affine object.",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet",
"url":4,
"doc":"A set of high-dimensional embeddings, composed of a series of  Embedding objects."
},
{
"ref":"emblaze.datasets.EmbeddingSet.identical",
"url":4,
"doc":"",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.project",
"url":4,
"doc":"Projects the embedding set into 2D. The method parameter can be a callable, which will define a dimensionality reduction technique that takes as input a list of numpy arrays and a list of lists of IDs, as well as any keyword arguments given to the params argument of this method, and returns a list of dimension-reduced arrays. Returns: A new  EmbeddingSet object with (optionally aligned) projected data.",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.compute_neighbors",
"url":4,
"doc":"Computes and saves a set of nearest neighbors in each embedding set according to the  Field.POSITION values. This can be accessed after completing this step by inspecting the  neighbors property of the embedding.",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.clear_neighbors",
"url":4,
"doc":"Removes the saved  Neighbors associated with each  Embedding . This can be used to determine which  Neighbors is returned by  get_ancestor_neighbors() .",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.get_neighbors",
"url":4,
"doc":"Returns a  NeighborSet object corresponding to the nearest neighbors of each embedding in the  EmbeddingSet .",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.get_recent_neighbors",
"url":4,
"doc":"Returns a  NeighborSet containing ancestor  Neighbors for each embedding in the  EmbeddingSet . This corresponds to the lowest-level  Embedding in each  Embedding 's parent tree (including the  Embedding itself) that has a neighbor set associated with it.",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.get_ancestor_neighbors",
"url":4,
"doc":"Returns a  NeighborSet containing ancestor  Neighbors for each embedding in the  EmbeddingSet . This corresponds to the highest-level  Embedding in each  Embedding 's parent tree that has a neighbor set associated with it.",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.to_json",
"url":4,
"doc":"Converts this set of embeddings into a JSON object. Args: compressed: whether to format  Embedding JSON objects using base64 strings instead of as human-readable float arrays save_neighbors: If  True , save the  Neighbors into the \"neighbors\" key of each individual embedding num_neighbors: number of neighbors to write for each point (can considerably save memory)",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.from_json",
"url":4,
"doc":"Builds an  EmbeddingSet from a JSON object. Args: data: A JSON-serializable dictionary representing the  EmbeddingSet , such as that generated by [ EmbeddingSet.to_json ]( emblaze.datasets.EmbeddingSet.to_json). parents: An optional list of  Embedding objects to use as parents for each of the created embeddings. Returns: An initialized  EmbeddingSet object.",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.save",
"url":4,
"doc":"Save this EmbeddingSet object to the given file path or file-like object (in JSON format). See [ EmbeddingSet.to_json ]( emblaze.datasets.EmbeddingSet.to_json) for acceptable keyword arguments. Args: file_path_or_buffer: A file path or file-like object to write the embedding to.",
"func":1
},
{
"ref":"emblaze.datasets.EmbeddingSet.load",
"url":4,
"doc":"Load the EmbeddingSet object from the given file path or file-like object containing JSON data. Args: file_path_or_buffer: A file path or file-like object to read the embedding from.",
"func":1
},
{
"ref":"emblaze.utils",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.Field",
"url":5,
"doc":"Standardized field names for embeddings and projections. These data can all be versioned within a ColumnarData object."
},
{
"ref":"emblaze.utils.Field.POSITION",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.Field.COLOR",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.Field.RADIUS",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.Field.ALPHA",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.Field.NAME",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.Field.DESCRIPTION",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.ProjectionTechnique",
"url":5,
"doc":"Names of projection techniques."
},
{
"ref":"emblaze.utils.ProjectionTechnique.UMAP",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.ProjectionTechnique.TSNE",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.ProjectionTechnique.ALIGNED_UMAP",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.ProjectionTechnique.PCA",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.DataType",
"url":5,
"doc":"Types of data, e.g. categorical vs continuous."
},
{
"ref":"emblaze.utils.DataType.CATEGORICAL",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.DataType.CONTINUOUS",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.PreviewMode",
"url":5,
"doc":"Ways of calculating preview lines."
},
{
"ref":"emblaze.utils.PreviewMode.PROJECTION_SIMILARITY",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.PreviewMode.NEIGHBOR_SIMILARITY",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.SidebarPane",
"url":5,
"doc":"Indexes of sidebar panes in the widget."
},
{
"ref":"emblaze.utils.SidebarPane.CURRENT",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.SidebarPane.SAVED",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.SidebarPane.RECENT",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.SidebarPane.SUGGESTED",
"url":5,
"doc":""
},
{
"ref":"emblaze.utils.projection_standardizer",
"url":5,
"doc":"Returns an affine transformation to translate an embedding to the centroid of the given set of points.",
"func":1
},
{
"ref":"emblaze.utils.affine_to_matrix",
"url":5,
"doc":"Returns a 3x3 matrix representing the transformation matrix.",
"func":1
},
{
"ref":"emblaze.utils.matrix_to_affine",
"url":5,
"doc":"Returns an Affine transformation object from the given 3x3 matrix.",
"func":1
},
{
"ref":"emblaze.utils.affine_transform",
"url":5,
"doc":"Transforms a set of N x 2 points using the given Affine object.",
"func":1
},
{
"ref":"emblaze.utils.standardize_json",
"url":5,
"doc":"Produces a JSON-compliant object by replacing numpy types with system types and rounding floats to save space.",
"func":1
},
{
"ref":"emblaze.utils.inverse_intersection",
"url":5,
"doc":"Computes the inverse intersection size of the two lists of sets. Args: seqs1: A list of iterables seqs2: Another list of iterables - must be the same length as seqs1 mask_ids: Iterable containing objects that should be EXCLUDED if outer is True, and INCLUDED if outer is False outer: Determines the behavior of mask_ids Returns: A numpy array of inverse intersection sizes between each element in seqs1 and seqs2.",
"func":1
},
{
"ref":"emblaze.utils.choose_integer_type",
"url":5,
"doc":"Chooses the best integer type (i.e. np.(u)int(8|16|32 for the given set of values. Returns the dtype and its name.",
"func":1
},
{
"ref":"emblaze.utils.encode_numerical_array",
"url":5,
"doc":"Encodes the given numpy array into a base64 representation for fast transfer to the widget frontend. The array will be encoded as a sequence of numbers with type 'astype'. If positions is not None, it should be a numpy array of positions at which the array for each ID  ends . For example, if there are ten IDs and ten numbers in the array for each ID, the positions array would be [10, 20,  ., 90, 100]. If interval is not None, it is passed into the result object directly (and signifies the same as positions, but with a regularly spaced interval).",
"func":1
},
{
"ref":"emblaze.utils.encode_object_array",
"url":5,
"doc":"Encodes the given array as a base64 string of a JSON string.",
"func":1
},
{
"ref":"emblaze.utils.decode_numerical_array",
"url":5,
"doc":"Decodes the given compressed dict into an array of the given dtype. The dict should contain a 'values' key (base64 string) and optionally a 'positions' key (base64 string to be turned into an int32 array, defining the shape of a 2d matrix) or an 'interval' key (integer defining the number of columns in the 2d matrix).",
"func":1
},
{
"ref":"emblaze.utils.decode_object_array",
"url":5,
"doc":"Decodes the given object's 'values' key into a JSON object.",
"func":1
},
{
"ref":"emblaze.thumbnails",
"url":6,
"doc":"Defines model classes to store thumbnail data in text and/or image formats."
},
{
"ref":"emblaze.thumbnails.Thumbnails",
"url":6,
"doc":"Defines a set of data suitable for displaying info about points visualized in an embedding set."
},
{
"ref":"emblaze.thumbnails.Thumbnails.to_json",
"url":6,
"doc":"Converts this set of thumbnails into a JSON object.",
"func":1
},
{
"ref":"emblaze.thumbnails.Thumbnails.from_json",
"url":6,
"doc":"Loads this Thumbnails object from JSON. This base method chooses the appropriate Thumbnails subclass to initialize, based on the format declared in the given JSON object data. The ids parameter can be used to subset the point IDs that are loaded from the file.",
"func":1
},
{
"ref":"emblaze.thumbnails.Thumbnails.get_ids",
"url":6,
"doc":"Return a numpy array of the IDs used in this thumbnails object.",
"func":1
},
{
"ref":"emblaze.thumbnails.Thumbnails.save",
"url":6,
"doc":"Save this Thumbnails object to the given file path or file-like object (in JSON format).",
"func":1
},
{
"ref":"emblaze.thumbnails.Thumbnails.load",
"url":6,
"doc":"Load the appropriate Thumbnails subclass from the given file path or file-like object containing JSON data.",
"func":1
},
{
"ref":"emblaze.thumbnails.TextThumbnails",
"url":6,
"doc":"Defines a set of textual thumbnails. names: String values corresponding to a name for each point in the dataset. descriptions: Optional longer string descriptions for each point in the dataset. ids: If not None, a list of IDs that these thumbnails correspond to. If not provided, the IDs are assumed to be zero-indexed ascending integers."
},
{
"ref":"emblaze.thumbnails.TextThumbnails.get_ids",
"url":6,
"doc":"Return a numpy array of the IDs used in this thumbnails object.",
"func":1
},
{
"ref":"emblaze.thumbnails.TextThumbnails.name",
"url":6,
"doc":"Returns the name(s) for the given set of IDs, or all points if ids is not provided.",
"func":1
},
{
"ref":"emblaze.thumbnails.TextThumbnails.description",
"url":6,
"doc":"Returns the description(s) for the given set of IDs, or all points if ids is not provided. Returns None if descriptions are not present.",
"func":1
},
{
"ref":"emblaze.thumbnails.TextThumbnails.to_json",
"url":6,
"doc":"Converts this set of thumbnails into a JSON object.",
"func":1
},
{
"ref":"emblaze.thumbnails.TextThumbnails.from_json",
"url":6,
"doc":"Builds a TextThumbnails object from a JSON object. The provided object should have an \"items\" key with a dictionary mapping ID values to text thumbnail objects, each of which must have a 'name' and optionally 'description' keys.",
"func":1
},
{
"ref":"emblaze.thumbnails.TextThumbnails.save",
"url":6,
"doc":"Save this Thumbnails object to the given file path or file-like object (in JSON format).",
"func":1
},
{
"ref":"emblaze.thumbnails.TextThumbnails.load",
"url":6,
"doc":"Load the appropriate Thumbnails subclass from the given file path or file-like object containing JSON data.",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails",
"url":6,
"doc":"Defines a set of image thumbnails. All thumbnails are scaled to the same dimensions to fit in a set of spritesheets. Args: images: An array of images, each represented as a numpy array. The images contained can be different sizes if the images object is provided as a list. spritesheets: If provided, ignores the other spritesheet-generating parameters and initializes the thumbnails object with previously generated spritesheets. ids: The IDs of the points to which each image belongs. If none, this is assumed to be a zero-indexed increasing index. grid_dimensions: Number of images per spritesheet, defined as (images per row, images per column). If this is not provided, it will be inferred to make the spritesheets a reasonable size. image_size: Number of pixels per image, defined as (rows, cols). If this is not defined, images will be resized to a maximum of MAX_IMAGE_DIM x MAX_IMAGE_DIM, maintaining aspect ratio if all images are the same size. names: If provided, adds text names to each point. Names are assumed to be in the same order as images. descriptions: Similar to names, but these descriptions may be longer and only show on the currently selected point(s)."
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.get_ids",
"url":6,
"doc":"Return a numpy array of the IDs used in this thumbnails object.",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.image",
"url":6,
"doc":"Returns the image(s) for the given ID or set of IDs, or all points if ids is not provided.",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.name",
"url":6,
"doc":"Returns the name(s) for the given set of IDs, or all points if ids is not provided. Returns None if names are not available.",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.description",
"url":6,
"doc":"Returns the description(s) for the given set of IDs, or all points if ids is not provided. Returns None if descriptions are not present.",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.get_spritesheets",
"url":6,
"doc":"",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.to_json",
"url":6,
"doc":"Converts this set of thumbnails into a JSON object.",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.from_json",
"url":6,
"doc":"Builds an ImageThumbnails object from a JSON object. The provided object should have a \"spritesheets\" object that defines PIXI spritesheets, and an optional \"items\" key that contains text thumbnails (see TextThumbnails for more information about the \"items\" field).",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.make_spritesheets",
"url":6,
"doc":"Generates a set of spritesheets from the given image data. Args: images: A matrix or list of images in RGBA format (e.g. shape = rows x cols x 4). ids: The point IDs to associate with each image. grid_dimensions: Number of images per spritesheet, defined as (images per row, images per column) image_size: Number of pixels per image, defined as (rows, cols)",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.save",
"url":6,
"doc":"Save this Thumbnails object to the given file path or file-like object (in JSON format).",
"func":1
},
{
"ref":"emblaze.thumbnails.ImageThumbnails.load",
"url":6,
"doc":"Load the appropriate Thumbnails subclass from the given file path or file-like object containing JSON data.",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails",
"url":6,
"doc":"A class representing a combination of images and/or text thumbnails. The thumbnail objects that are merged may have overlapping IDs, but they may not have overlapping IDs for the same thumbnail type. For example, two ImageThumbnails objects cannot both have images for the same point ID."
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.get_ids",
"url":6,
"doc":"Return a numpy array of the IDs used in this thumbnails object.",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.get_spritesheets",
"url":6,
"doc":"",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.to_json",
"url":6,
"doc":"Converts this set of thumbnails into a JSON object.",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.from_json",
"url":6,
"doc":"Loads this Thumbnails object from JSON. This base method chooses the appropriate Thumbnails subclass to initialize, based on the format declared in the given JSON object data. The ids parameter can be used to subset the point IDs that are loaded from the file.",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.image",
"url":6,
"doc":"Returns the image(s) for the given ID or set of IDs, or all points if ids is not provided.",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.name",
"url":6,
"doc":"Returns the name(s) for the given set of IDs, or all points if ids is not provided. Returns None if names are not available.",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.description",
"url":6,
"doc":"Returns the description(s) for the given set of IDs, or all points if ids is not provided. Returns None if descriptions are not present.",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.save",
"url":6,
"doc":"Save this Thumbnails object to the given file path or file-like object (in JSON format).",
"func":1
},
{
"ref":"emblaze.thumbnails.CombinedThumbnails.load",
"url":6,
"doc":"Load the appropriate Thumbnails subclass from the given file path or file-like object containing JSON data.",
"func":1
},
{
"ref":"emblaze.recommender",
"url":7,
"doc":"Defines a class to compute Suggested Selections, or clusters that exhibit consistent or noteworthy changes from one frame to another."
},
{
"ref":"emblaze.recommender.SelectionRecommender",
"url":7,
"doc":"Generates recommended selections based on a variety of inputs. The recommender works by pre-generating a list of clusters at various granularities, then sorting them by relevance to a given query."
},
{
"ref":"emblaze.recommender.SelectionRecommender.query",
"url":7,
"doc":"Returns a list of clusters in sorted order of relevance that match the given filters. Args: ids_of_interest: A list of ID values. If there are sufficiently many clusters containing at least one ID in this list, only they will be returned. Otherwise, clusters containing IDs from the neighbor sets of those IDs may be returned as well. filter_ids: A list of IDs such that at least one point in every cluster MUST be present in this list. frame_idx: A base frame index to filter for. If None, clusters from any frame may be returned. preview_frame_idx: A preview frame index to filter for. frame_idx must be provided if this is provided. bounding_box: If provided, should be a tuple of four values: min x, max x, min y, and max y. At least one point in each cluster will be required to be within the bounding box. num_results: Maximum number of results to return. id_type: The type of ID that ids_of_interest corresponds to. This goes into the explanation string for clusters, e.g. \"shares 3 points with  \". Returns: A list of suggested selections. Each suggestion is returned as a tuple of two values - a list of point IDs, and a string \"reason\" explaining why the cluster is recommended.",
"func":1
},
{
"ref":"emblaze.recommender.SelectionRecommender.to_json",
"url":7,
"doc":"Converts the clusters stored in this Recommender object to JSON.",
"func":1
},
{
"ref":"emblaze.recommender.SelectionRecommender.from_json",
"url":7,
"doc":"Reads the clusters stored in the given JSON object to a Recommender.",
"func":1
}
]