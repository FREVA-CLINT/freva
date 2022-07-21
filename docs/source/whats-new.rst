What's new
===========

v2206.0.3 (unreleased)
----------------------

New Features
~~~~~~~~~~~~


Breaking changes
~~~~~~~~~~~~~~~~

Deprecations
~~~~~~~~~~~~

Bug fixes
~~~~~~~~~

Documentations
~~~~~~~~~~~~~~

Internal Changes
~~~~~~~~~~~~~~~~


v2206.0.2
---------

New Features
~~~~~~~~~~~~


Breaking changes
~~~~~~~~~~~~~~~~

Deprecations
~~~~~~~~~~~~

Bug fixes
~~~~~~~~~

- Set plugin status to broken in OS related termination signals that can be
  handled by python (SIGTERM, SIGINT ...) and any other internal python errors.

Documentations
~~~~~~~~~~~~~~

Internal Changes
~~~~~~~~~~~~~~~~

- Introduce lazy loading to make freva cli a little more responsive
- Explicitly set EVALUATION_SYSTEM_CONFIG_FILE env variable in workload
  manager job script.

v2206.0.1
----------

New Features
~~~~~~~~~~~~

- Add python module for importing :py:meth:`freva` directly in python
  environments
- Rename command line interface sub modules:
    - ``freva --databrowser`` → ``freva databrowser``,
    - ``freva --plugin`` → ``freva plugin``
    - ``freva --history`` → ``freva history``
    - ``freva --esgf`` → ``freva esgf``
    - ``freva --crawl_my_data`` → ``freva crawl-my-data``
- Add new commands as alternative for freva sub commands
    - ``freva-databrowser`` = ``freva databrowser`` etc
- Argument completion works for all sub commands, including plugin setup.
- Interactive jobs can be controlled from the web user interface
- Output of interactive jobs can be displayed in the web user interface

Breaking changes
~~~~~~~~~~~~~~~~
- Command line arguments taking boolean values do not require True or False:
    - Instead of ``freva plugin animtor --batchmode=True`` → ``freva plugin animtor --batchmode``
- :py:meth:`add_output_to_databrowser` formerly :py:meth:`linkmydata` does not infer meta data
  from file and directory structure anymore (i.e., does not need to
  follow a particular folder path and naming convention)

Deprecations
~~~~~~~~~~~~
 - the `tool-pull-request` sub command has been made deprecated.
- The following methods in the :ref:`PluginAPI` have been renamed:
    - :py:meth:`runTool` → :py:meth:`run_tool`
    - :py:meth:`linkmydata` → :py:meth:`add_output_to_databrowser`
    - :py:meth:`prepareOutput` → :py:meth:`prepare_output`
    - :py:meth:`getHelp` → :py:meth:`get_help`
    - :py:meth:`getClassBaseDir` → :py:attr:`class_basedir`
    - :py:meth:`setupConfiguration` → :py:meth:`setup_configuration`
    - :py:meth:`readConfiguration` → :py:meth:`read_configuration`
- The following methods in the :ref:`ParameterAPI` have been renamed:
    - :py:meth:`parseArguments` → :py:meth:`parse_arguments`

Bug fixes
~~~~~~~~~

Documentations
~~~~~~~~~~~~~~
- Add user sphinx documentation

Internal Changes
~~~~~~~~~~~~~~~~
- Add support for different workload managers
- Install ``freva`` in dedicated anaconda environment
- Install each Freva plugin in dedicated anaconda environment
