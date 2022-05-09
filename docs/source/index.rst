.. freva documentation master file, created by
   sphinx-quickstart on Wed May  4 19:35:26 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to freva's documentation!
=================================

Freva, the freva evaluation system framework, is a data search and analysis
platform developed by the atmospheric science community for the atmospheric
science community. With help of freva researchers can:

- quickly and intuitively search for data stored at typical data centers that
  host many datasets.
- provide and apply data analysis tools to and from other researchers in a
  reproducible manner.

Data analysis is realised by user developed data analysis plugins. These plugins
are code agnostic, meaning that users don't have to rewrite the core of their
plugins to make them work with freva. All that freva does is providing a user
interface for the plugins.

Currently freva comes in three different flavours:

- python module, that allows the usage of freva in python environments, like jupyter notebooks
- a command line interface (cli) that allows using freva from the command lines and shell scripts.
- a web user interface (web-ui)

This documentation covers the usage of the python module as well the cli. We
have also added a section on plugin development for users who want to get started
with developing their own data analysis plugins and provide these to their
community. The last section covers the answers to frequently asked questions
and best practices when it comes to plugin development.


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   Freva
   FrevaCli
   developers_guide
   FAQ.ipynb


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
