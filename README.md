# Emblaze - Interactive Embedding Comparison

A Jupyter notebook widget for visually comparing embeddings using dimensionally-reduced scatter plots.

## Installation

This widget has been tested using Python 3.7, Jupyter Notebook (6.3.0), Jupyter Lab (3.0), and ipykernel 5.5.3.

You can install using `pip`:

```bash
pip install emblaze
```

If you use JupyterLab, you will need to run the following additional commands:

```bash
jupyter labextension install emblaze
```

If you are using Jupyter Notebook 5.2 or earlier, you may also need to enable
the nbextension:

```bash
jupyter nbextension enable --py --sys-prefix emblaze
```

## Development Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the python package. This will also build the JS packages.

```bash
pip install -e .
```

Run the following commands if you use **Jupyter Lab**:

```
jupyter labextension install @jupyter-widgets/jupyterlab-manager --no-build
jupyter labextension install .
```

Run the following commands if you use **Jupyter Notebook**:

```
jupyter nbextension install --sys-prefix --symlink --overwrite --py emblaze
jupyter nbextension enable --sys-prefix --py emblaze
```

Note that the `--symlink` flag doesn't work on Windows, so you will here have to run
the `install` command every time that you rebuild your extension. For certain installations
you might also need another flag instead of `--sys-prefix`, but we won't cover the meaning
of those flags here.

### How to see your changes

#### Typescript:

To continuously monitor the project for changes and automatically trigger a rebuild, start Jupyter in watch mode:

```bash
jupyter lab --watch
```

And in a separate session, begin watching the source directory for changes:

```bash
npm run watch
```

After a change wait for the build to finish and then refresh your browser and the changes should take effect.

#### Python:

If you make a change to the python code then you will need to restart the notebook kernel to have it take effect.

## Examples

Please see `examples/example.ipynb` to try using the DR Viewer widget on the Boston housing prices or MNIST (TensorFlow import required) datasets.

**Example 1: Multiple projections of the same embedding dataset.** This can reveal areas of variation in the dimensionality reduction process, since tSNE and UMAP are randomized algorithms.

```python
import drviewer as dr

# X is an n x k array, Y is a length-n array
X, Y = ...

# Represent the high-dimensional embedding
emb = dr.Embedding({dr.Field.POSITION: X, dr.Field.COLOR: Y})
# Compute nearest neighbors in the high-D space
emb.compute_neighbors(metric='euclidean')

# Generate UMAP 2D representations - you can pass UMAP parameters to project()
variants = dr.EmbeddingSet([
    emb.project(method=dr.ProjectionTechnique.UMAP) for _ in range(10)
])

w = dr.DRViewer(embeddings=variants)
w
```

**Example 2: Multiple embeddings of the same data from different models.** This is useful to see how different models embed data differently.

```python
# Xs is a list of n x k arrays corresponding to different embedding spaces
Xs = ...
# Y is a length-n array of labels for color-coding
Y = ...
# List of strings representing the name of each embedding space (e.g.
# "Google News", "Wikipedia", "Twitter"). Omit to use generic names
embedding_names = [...]

# Make high-dimensional embedding objects
embeddings = dr.EmbeddingSet([
    dr.Embedding({dr.Field.POSITION: X, dr.Field.COLOR: Y}, label=emb_name)
    for X, emb_name in zip(Xs, embedding_names)
])
embeddings.compute_neighbors()

# Make aligned UMAP
reduced = embeddings.project(method=dr.ProjectionTechnique.ALIGNED_UMAP)

w = dr.DRViewer(embeddings=reduced)
w
```

**Example 3: Visualizing image data with image thumbnails.** The viewer will display image previews for each point as well as its nearest neighbors. (For text data, you can use `TextThumbnails` to show small pieces of text next to the points.)

```python
# images is an n x 100 x 100 x 3 numpy array of 100x100 RGB images (values from 0-255)
images = ...
thumbnails = dr.ImageThumbnails(images)
w = dr.DRViewer(embeddings=embeddings, thumbnails=thumbnails)
w
```

### Interactive Analysis

Once you have loaded a `DRViewer` instance in the notebook, you can read and write its properties to dynamically work with the visualization. The following properties are reactive:

- `embeddings` (`EmbeddingSet`) Modify this to change the entire dataset that is displayed.
- `thumbnails` (`Thumbnails`) Represents the image or text thumbnails displayed on hover and click.
- `currentFrame` (`int`) The current frame or embedding space that is being viewed (from `0` to `len(embeddings)`).
- `selectedIDs` (`List[int]`) The selected ID numbers. Unless you provide custom IDs when constructing the `EmbeddingSet`, these are simply zero-indexed integers.
- `alignedIDs` (`List[int]`) The IDs of the points to which the embedding spaces are aligned (same format as `selectedIDs`). Alignment is computed relative to the positions of the points in the current frame.

## Standalone App

The widget can also be run as a standalone application. In this case, you must include data and thumbnail files in the `data` directory for them to appear in the widget.

To build once and run the app, first run `npm run build:standalone`. (For development, see below).

Start the Flask server:

```bash
cd drviewer
python server.py
```

For development, run `npm run watch:standalone` to continuously build the frontend and automatically reload when the content changes.

## Notes

- Svelte transitions don't seem to work well as they force an expensive re-layout operation. Avoid using them during interactions.
