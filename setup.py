#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function
from glob import glob
from os.path import join as pjoin
import sys

sys.path.insert(0, '.')

from setupbase import (
    create_cmdclass, install_npm, ensure_targets,
    find_packages, combine_commands, ensure_python,
    get_version, HERE
)

from setuptools import setup

# The name of the project
name = 'emblaze'

# Ensure a valid python version
ensure_python('>=3.4')

# Get our version
version = get_version(pjoin(name, '_version.py'))

nb_path = pjoin(HERE, name, 'nbextension', 'static')
lab_path = pjoin(HERE, name, 'labextension')

# Representative files that should exist after a successful build
jstargets = [
    pjoin(nb_path, 'index.js'),
    pjoin(HERE, 'lib', 'index.js'),
]

ensured_targets = [
    pjoin(lab_path, "package.json"),
    pjoin(lab_path, "static/style.js")
]

package_data_spec = {
    name: [
        'nbextension/static/*.*js*',
        'labextension/*.tgz'
    ]
}

data_files_spec = [
    ('share/jupyter/nbextensions/emblaze',
        nb_path, '*.js*'),
    # ('share/jupyter/lab/extensions', lab_path, '*.tgz'),
    ("share/jupyter/labextensions/%s" % name, lab_path, "**"),
    ('etc/jupyter/nbconfig/notebook.d', HERE,
     'emblaze.json')
]

setup_args = dict(
    name=name,
    description='Interactive Jupyter notebook widget for visually comparing embeddings',
    long_description=open(pjoin(HERE, 'README.md')).read(),
    long_description_content_type='text/markdown',
    version=version,
    scripts=glob(pjoin('scripts', '*')),
    packages=find_packages(),
    author='venkatesh-sivaraman',
    author_email='venkatesh.sivaraman.98@gmail.com',
    url='https://github.com/cmudig/emblaze',
    license='BSD',
    platforms="Linux, Mac OS X, Windows",
    keywords=['Jupyter', 'Widgets', 'IPython'],
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Jupyter',
    ],
    include_package_data=True,
    install_requires=[
        'ipywidgets>=7.0.0',
        'affine>=2.3.0',
        'colormath>=3.0.0',
        'numpy>=1.19.5',
        'pandas>=1.2.0',
        'scikit-learn>=0.24.1',
        'scipy>=1.6.0',
        'pillow>=8.2.0',
        'umap-learn>=0.5.1',
        'flask>=1.1.2'
    ],
    entry_points={
    },
)

try:
    from jupyter_packaging import (
        wrap_installers,
        npm_builder,
        get_data_files
    )
    post_develop = npm_builder(
        build_cmd="build:all", source_dir="src", build_dir=lab_path
    )
    setup_args["cmdclass"] = wrap_installers(post_develop=post_develop, ensured_targets=ensured_targets)
    setup_args["data_files"] = get_data_files(data_files_spec)
except ImportError as e:
    import logging
    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.warning("Build tool `jupyter-packaging` is missing. Install it with pip or conda.")
    if not ("--name" in sys.argv or "--version" in sys.argv):
        raise e

if __name__ == '__main__':
    setup(**setup_args)
