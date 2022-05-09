Plugin Developer Guide
----------------------

.. toctree::
   :maxdepth: 3

This documentation helps to get started with creating user defined `freva`
plugins. The **Plugin API Reference** gives an overview of a plugin should
be setup to be able to interact with freva. It also introduces methods available
to the API wrapper.

The **Parameter API Reference** introduces the different available options to
configure the plugin setup.


Plugin API Reference
====================

.. automodule:: evaluation_system.api.plugin
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __version__, __long_description__, __short_description__, __parameters__, __category__, __tags__

.. _PluginAPI:


Parameter API Reference
=======================


.. automodule:: evaluation_system.api.parameters
   :members:
   :undoc-members:
   :show-inheritance:

Deploying your new Plugin
=========================

This section illustrates the steps that are necessary to turn an existing
data analysis code into a freva plugin - we refer to this step as *deployment*
Like above we assume that the code is stored in a specific location for example
``~/workspace/tracking_tool``. Also let's assume that the analysis tool is written
in the *R* script language.

Creating a new repository from a template
++++++++++++++++++++++++++++++++++++++++++


We have created a `template repository <https://gitlab.dkrz.de/freva/plugins4freva/plugintemplate/>`_ repository that helps
to help you getting started with the freva plugin development. Therefore we
recommend you to use this repository. Use the following commands to turn this
template repository into your new freva plugin repository:

.. code-block:: console

    git clone https://gitlab.dkrz.de/freva/plugins4freva/plugintemplate freva_tracking
    cd freva_tracking
    rm -r .git
    git init .
    git checkout -b first_attempt
    git add .
    cp -r ~/workspace/tracking_tool src
    git add src

You have now created a new freva plugin repository. It is a good idea to use
some kind of repository server (like `gitlab`) where you make your code accessible.
Talk to your freva admin to work out a good location for your code. Once you have agreed
upon a location you should create a new repository on the server side using the
web interface of your repository host system (e.g `gitlab`). Once created set
the remote host address on the locally created repository (the one where you did a `git init`):

.. code-block:: console

    git remote set-url origin https://gitlab.com/path/to/the/remote/repo

Installing dependencies
+++++++++++++++++++++++

Once the git repository has been setup and configured all dependencies the tool
needs should be installed. Here we assume the analysis tool is based on a gnu-R
code stack. Therefore gnu-R and certain libraries have to be part of the plugin
environment. This environment will be created using `anaconda <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>`_.
To find out what dependencies you should be installing query the `anaconda search page <https://anaconda.org/>`_.
Once you have found all packages that can be installed via anaconda you can add them
to the ``deployment/plugin-env.yaml`` file. Simply add the entries that are needed
to the existing file.


.. code-block:: yaml

   channels:
        - conda-forge
    dependencies:
        - conda
        - r-base
        - r-essentials
        - r-ncdf4
        - pip
        - black

Probably there are package dependencies missing that cannot be installed via
anaconda, hence you have to install additional packages. To do so you can use
a simple command line interface and add the following command into the ``build``
section of the ``Makefile`` in the repository:

.. code-block:: Makefile

    build:
        python deployment/install_resources.py gnu-r ncdf4.helpers

After everything is setup you can build use the ``make`` command to deploy the
plugin environment.

.. code-block:: bash

   make all

Afterwards you can use the :ref:`PluginAPI` to create the wrapper file
and finalize the creation of the plugin.
