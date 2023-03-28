# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import sys
# sys.path.insert(0, os.path.abspath('.'))
import os
import sys
import subprocess
from recommonmark.parser import CommonMarkParser

sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "src")))
os.environ.setdefault(
    "EVALUATION_SYSTEM_CONFIG_FILE",
    os.path.abspath(os.path.join("..", "..", "compose", "local-eval-system.conf")),
)
os.environ.setdefault(
    "EVALUATION_SYSTEM_DRS_CONFIG_FILE",
    os.path.abspath(os.path.join("..", "..", "compose", "drs_config.toml")),
)

from freva import __version__


# -- Project information -----------------------------------------------------

project = "freva user guide"
copyright = "2022, CLINT"
author = "CLINT"

# The full version, including alpha/beta/rc tags
release = __version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "nbsphinx",
    "recommonmark",
    "sphinx_execute_code",
    "sphinxcontrib_github_alt",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
nbsphinx_allow_errors = True

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

source_parsers = {
    ".md": CommonMarkParser,
}

source_suffix = [".rst", ".md"]
