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
import subprocess
import sys
from datetime import date

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
copyright = f"{date.today().year}, DKRZ"
author = "DKRZ"

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
    "sphinxcontrib.httpdomain",
    "sphinx_code_tabs",
    "sphinx_togglebutton",
    "nbsphinx",
    "recommonmark",
    "sphinx_execute_code",
    "sphinxcontrib_github_alt",
    "sphinx_copybutton",
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
html_static_path = ["_static"]
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/FREVA-CLINT/freva",
            "icon": "fa-brands fa-github",
        }
    ],
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
    "collapse_navigation": False,
    "navigation_depth": 4,
    "navbar_align": "left",
    "show_nav_level": 4,
    "navigation_depth": 4,
    "navbar_center": ["navbar-nav"],
    "secondary_sidebar_items": ["page-toc"],
    "light_css_variables": {
        "color-brand-primary": "tomato",
    },
}
html_context = {
    "github_user": "FREVA-CLINT",
    "github_repo": "freva",
    "github_version": "main",
    "doc_path": "docs",
}
html_logo = os.path.join(html_static_path[0], "logo.png")
html_favicon = html_logo
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".

source_parsers = {
    ".md": CommonMarkParser,
}

source_suffix = [".rst", ".md"]
