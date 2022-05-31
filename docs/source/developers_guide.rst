Plugin Developer Guide
----------------------

.. toctree::
   :maxdepth: 3

This documentation helps to get started with creating user defined ``Freva``
plugins. This section provides a minimal example of a make your *existing* data
analysis code a Freva plugin. Detailed usage information can be found in the
:ref:`APIReference`.

A Minimal Example
=================

.. automodule:: evaluation_system.api.plugin
.. currentmodule:: evaluation_system.api.plugin
.. autoclass:: PluginAbstract


Setting up your new plugin
===========================

This section illustrates the steps that are necessary to turn existing
data analysis code into a Freva plugin.
Like above we assume that the code is stored in a specific location for example
``~/workspace/tracking_tool``. Also let's assume that the analysis tool is written
in the *R* script language.

Creating a new repository from a template
++++++++++++++++++++++++++++++++++++++++++


We have created a `template repository <https://gitlab.dkrz.de/freva/plugins4freva/plugintemplate/>`_ repository that helps
you getting started with the Freva plugin development. Therefore we
recommend you to use this repository. Use the following commands to turn this
template repository into your new Freva plugin repository:

.. code-block:: console

    wget https://gitlab.dkrz.de/freva/plugins4freva/plugintemplate/-/archive/main/plugintemplate-main.zip
    unzip plugintemplate-main.zip
    mv plugintemplate-main freva_tracking
    cd freva_tracking
    git init --shared .
    cp -r ~/workspace/tracking_tool src
    git add .

You have now created a new Freva plugin repository. It is a good idea to use
some kind of repository server, like gitlab, where you make your code accessible.
Talk to your Freva admins to work out a good location for your code. Once you have agreed
upon a location you should create a new repository on the server side using the
web interface of your repository host system. Once created set
the remote host address on the locally created repository (the one where you did a `git init`):

.. code-block:: console

    git remote set-url origin https://gitlab.com/path/to/the/remote/repo.git

.. hint::

    If you are unfamiliar with git you can find plenty of online resources on
    the web. A good resource might be the
    `official git tutorial page <https://git-scm.com/docs/gittutorial>`_.

Installing dependencies
+++++++++++++++++++++++

Once the git repository has been set up and configured all dependencies the tool
needs should be installed. Here we assume the analysis tool is based on a gnu-R
stack. Therefore gnu-R and certain libraries have to be part of the plugin
environment. This environment will be created using
`anaconda <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html>`_.
To find out what dependencies you should be installing query the
`anaconda search page <https://anaconda.org/>`_.
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

Probably there are package dependencies that cannot be installed via
anaconda and need to bee installed otherwise. To do so you can use
a simple command line interface in ``deployment/install_resources.py``
and add the following command into the ``build``
section of the ``Makefile`` in the repository:

.. code-block:: Makefile

    build:
        python deployment/install_resources.py gnu-r ncdf4.helpers

To get an overview over the full functionality of the installation cli you
can query the help.


.. code-block:: console

    python deployment/install_resources.py --help

After everything is setup you can build use the ``make`` command to deploy the
plugin environment.

.. code-block:: console

   make all

.. note::

    The ``Makefile`` will use the ``conda`` command. If anaconda is not available
    by default on your system you can load the freva environment, which ships
    anaconda.

Afterwards you can refer to the :ref:`PluginAPI` and :ref:`ParameterAPI` docs to
create the wrapper file and finalize the creation of the plugin.
