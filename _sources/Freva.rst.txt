Freva python module
-------------------

.. toctree::
   :maxdepth: 3

The following section gives an overview over the usage of the Freva python
module. This section assumes that you know how to get to access to the
python environment that has Freva installed. If this is not the case please
contact one of your Freva admins or the
`Frequently Asked Questions <FAQ.html>`_ section for help.

Searching for data
==================
To query data databrowser and search for data you have three different options.
You can the to following methods

- :py:meth:`freva.databrowser`: The main method for searching data is the
  :py:meth:`freva.databrowser` method. The data browser method lets you search
  for data *files* or *uris*. *Uris* instead of file paths are useful because
  an uri indicates the storage system where the *files* are located.

- :py:meth:`freva.facet_search`: This method lists all search categories (facets) and
  their values.

- :py:meth:`freva.count_values`: You can count the occurrences of search results with
  this method.


Below you can find a more detailed documentation.

.. automodule:: freva
   :members: databrowser, facet_search, count_values
   :show-inheritance:

.. _databrowser:


Running analysis plugins
========================
.. _plugin:

Already defined data analysis tools can be started with the :py:meth:`freva.run_plugin`
method. Besides the :py:meth:`freva.run_plugin` method three more utility methods
(:py:meth:`freva.list_plugins`, :py:meth:`freva.get_tools_list`,
:py:meth:`freva.plugin_doc`) are available to get an overview over
existing plugins and the documentation of each plugins.

.. automodule:: freva
   :members: list_plugins, get_tools_list, plugin_doc, run_plugin
   :undoc-members:
   :show-inheritance:

This specific plugin has created the following output:

.. image:: _static/animator_output.gif
   :width: 400


After the application of a data analysis plugin you can check the status of the
plugin and make use of any of the plugin output either by directly using the
return value of the :py:meth:`freva.run_plugin` method or create an instance
of the :py:class:`freva.PluginStatus` status class with help of a history id.

.. automodule:: freva
   :members: PluginStatus
   :undoc-members:
   :show-inheritance:



Accessing the previous plugin runs
==================================

.. automodule:: freva
   :members: history
   :undoc-members:
   :show-inheritance:

The ``UserData`` class
======================

.. automodule:: freva
   :members: UserData
   :undoc-members:
   :show-inheritance:

Overriding or using a freva configuration
=========================================
If you want to install and maintain an instance of the freva client in your
own python environment you will most likely have to load the freva configuration
to be able to use the freva infrastructure. To do so you can use the
:py:class:`freva.config` class. This class allows you to either override or
set the path to the freva configuration file.

.. automodule:: freva
   :members: config
   :undoc-members:

Searching for ESGF data
=======================
Freva also allows to query for data in all the ESGF nodes. You have the following 5
methods:

- :py:meth:`freva.esgf_browser`: The main method for searching data. The browser
  method lets you search for data URLs (default) or their opendap/gridftp endpoints.

- :py:meth:`freva.esgf_facets`: This method lists all search categories (facets) and
  their values.

- :py:meth:`freva.esgf_datasets`: This method lists the name of the datasets (and version)
  in the ESGF.

- :py:meth:`freva.esgf_download`: You can download the data with the script file
  that this method creates.

- :py:meth:`freva.esgf_query`: Similarly to :py:meth:`freva.esgf_facets`, this method lists
  all query elements but groups them *by dataset*.

.. note::

   The collection of methods
   are derived from `ESGF's rest API <https://github.com/ESGF/esgf.github.io/wiki/ESGF_Search_REST_API>`_.
   The query facets follow the syntax of the datasets hosted there (CMIP5, CORDEX, CMIP6, etc.)
   that might differ from :py:meth:`freva.databrowser` and **are** case
   sensitive. They also have some special query keys, e.g.:

   - ``distrib``: (**true**, false) search globally or only locally (e.g. at DKRZ, MPI data and replicas)
   - ``latest`` : (true, false, **unset**) search for the latest version, older ones or all.
   - ``replica``: (true, false, **unset**) search only for replicas, non-replicas, or all.


Below you can find a more detailed documentation.

.. automodule:: freva
   :members: esgf_browser, esgf_facets, esgf_datasets, esgf_download, esgf_query
   :show-inheritance:
