# dr-viewer-widget

Interactive uncertainty-aware dimensionality reduction viewer

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

You can install using `pip`:

```bash
pip install drviewer
```

Or if you use jupyterlab:

```bash
pip install drviewer
jupyter labextension install @jupyter-widgets/jupyterlab-manager
```

If you are using Jupyter Notebook 5.2 or earlier, you may also need to enable
the nbextension:

```bash
jupyter nbextension enable --py [--sys-prefix|--user|--system] drviewer
```

## Development Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

```bash
# First install the python package. This will also build the JS packages.
pip install -e .
```

When developing your extensions, you need to manually enable your extensions with the
notebook / lab frontend. For lab, this is done by the command:

```
jupyter labextension install @jupyter-widgets/jupyterlab-manager --no-build
jupyter labextension install .
```

For classic notebook, you can run:

```
jupyter nbextension install --sys-prefix --symlink --overwrite --py drviewer
jupyter nbextension enable --sys-prefix --py drviewer
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

## Notes

- Svelte transitions don't seem to work well as they force an expensive re-layout operation. Avoid using them during interactions.

# Standalone App

To build once and run the app, first run `npm run build:standalone`. (For development, see below).

Start the Flask server:

```bash
cd drviewer
python server.py
```

For development, run `npm run watch:standalone` to continuously build the frontend and automatically reload when the content changes.
