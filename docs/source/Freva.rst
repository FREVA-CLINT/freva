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

- ``databrower``: The main method for searching data is the ``databrowser``
    method. The data browser method lets you search for data *files* or *uris*. *Uris* instead of file paths are useful because an uri indicates the storage system
    where the *files* are located.

- ``facet_search``: This method lists all search categories (facets) and their values.

- ``count_values``: You can count the occurrences of search results with this method.

Below you can find a more detailed documentation.

.. automodule:: freva
   :members: databrowser, facet_search, count_values
   :show-inheritance:

.. _databrowser:


Runing analysis plugins
=======================
Already defined data analysis tools can be started with the ``freva.run_plugin``
method. Besides the ``run_plugin`` method two more utility methods
(``list_plugins`` and ``plugin_doc``) are available to get an overview over
existing plugins and the documentation of each plugins.

.. automodule:: freva
   :members: list_plugins, plugin_doc, run_plugin
   :undoc-members:
   :show-inheritance:

This specific plugin has created the following output:

.. image:: _static/animator_output.gif
   :width: 400

.. _plugin:

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
