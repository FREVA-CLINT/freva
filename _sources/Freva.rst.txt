Freva python module
-------------------

.. toctree::
   :maxdepth: 3

The following section gives an overview over the usage of the Freva python
module. This section assumes that you know how to get to access to the
python environment that has Freva installed. If this is not the case please
contact one of your Freva admins or the
`Frequently Asked Questions <FAQ.html>`_ section for help.

The ``databrowser`` module
==========================

.. automodule:: freva
   :members: databrowser
   :show-inheritance:

.. _databrowser:


The ``plugin`` module
======================
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

The ``history`` module
======================

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
