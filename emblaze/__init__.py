#!/usr/bin/env python
# coding: utf-8

# Copyright (c) venkatesh-sivaraman.
# Distributed under the terms of the Modified BSD License.

from .viewer import Viewer
from .datasets import Embedding, EmbeddingSet
from .utils import ProjectionTechnique, Field, PreviewMode
from .thumbnails import Thumbnails, TextThumbnails, ImageThumbnails
from ._version import __version__, version_info

from .nbextension import _jupyter_nbextension_paths

import json
from pathlib import Path

from ._version import __version__

HERE = Path(__file__).parent.resolve()

with (HERE / "labextension" / "package.json").open() as fid:
    data = json.load(fid)

def _jupyter_labextension_paths():
    return [{
        "src": "labextension",
        "dest": data["name"]
    }]