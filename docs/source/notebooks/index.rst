Examples
========

This chapters contains a collection of examples that demonstrate
the usage for freva by jupyter notebooks.

After loading the freva module or installing freva in your own python
environment you should create a new
`jupyter kernel <https://pypi.org/project/ipykernel/>`_. This kernel should have
the environment variables needed by freva set automatically. You can do this via
the following command:


.. code:: console

    python -m ipykernel install --user --name my-kernel-name --env EVALUATION_SYSTEM_CONFIG_FILE <path_to_evalfile>

The path to the environment variable is project specific for example

``/work/ch1187/clint/nextgems/freva/evaluation_system.conf``

Enjoy!

.. toctree::
   :maxdepth: 2

   01-Using_the_Databrowser
   02-Add_own_datasets
   03-Applying_Plugins_and_Search_for_History
   04-The_CommandLineInterface
