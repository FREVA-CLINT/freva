What's new
===========

.. toctree::
   :maxdepth: 0
   :titlesonly:

v2303.0.0
~~~~~~~~~

New Features
++++++++++++
- User data can be ingested also if not all data files match directory reference
  standard.
- A new databrowser key (uri) was added that representing the object storge
  where the data is stored.

Breaking changes
++++++++++++++++


Deprecations
++++++++++++

Bug fixes
+++++++++
- Only save the hostname when submitting jobs, not the host + domain name

Documentations
++++++++++++++

Internal Changes
++++++++++++++++


v2208.1.1
~~~~~~~~~

New Features
++++++++++++

Breaking changes
++++++++++++++++

Deprecations
++++++++++++

Bug fixes
+++++++++
- Fix typo in deployment routine

Documentations
++++++++++++++
- Fix binder instance

Internal Changes
++++++++++++++++
- Make all scheduler options non-mandatory
- Add metadata-inspector as dependency


v2208.0.1
~~~~~~~~~

New Features
++++++++++++
- ``count`` keyword/flag for the databrowser counts also the number of files
  found by the databrowser, not only the facet counts.
- databrowser can subset results by time.
- add functionality to add new data to databrowser
- add functionality to delete existing user data from databrowser
- add new class to handle user data requests

Breaking changes
++++++++++++++++
- ``count_facet_values`` keyword (``count-facet-values`` flag in cli) has been renamed to ``count``

Deprecations
++++++++++++
- move ``freva.crawl_my_data`` functionality to `freva.UsersData.index`
- renamed ``freva crawl_my_data`` to ``freva user-data```

Bug fixes
+++++++++

Documentations
++++++++++++++
- Documentation of the python modules has been improved

Internal Changes
++++++++++++++++
- Files found by the databrowser are *alphabetically* sorted.
- ``follow/unfolllow_history_tag`` recieves a user object as argument instead of string
- lazy loading has been improved

v2206.0.10
~~~~~~~~~~

New Features
++++++++++++


Breaking changes
++++++++++++++++

Deprecations
++++++++++++

Bug fixes
+++++++++

- Set plugin status to broken in OS related termination signals that can be
  handled by python (SIGTERM, SIGINT ...) and any other internal python errors.
- Update databrowser query algorithm.

Documentations
++++++++++++++

Internal Changes
++++++++++++++++

- Introduce lazy loading to make freva cli a little more responsive
- Explicitly set EVALUATION_SYSTEM_CONFIG_FILE env variable in workload
  manager job script.
- Increase batch size to 5000 as default for querying data.

v2206.0.1
~~~~~~~~~

New Features
++++++++++++

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
++++++++++++++++
- Command line arguments taking boolean values do not require True or False:
    - Instead of ``freva plugin animtor --batchmode=True`` → ``freva plugin animtor --batchmode``
- :py:meth:`add_output_to_databrowser` formerly :py:meth:`linkmydata` does not infer meta data
  from file and directory structure anymore (i.e., does not need to
  follow a particular folder path and naming convention)

Deprecations
++++++++++++
- The `tool-pull-request` sub command has been made deprecated.
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
+++++++++

Documentations
++++++++++++++
- Add user sphinx documentation

Internal Changes
++++++++++++++++
- Add support for different workload managers
- Install ``freva`` in dedicated anaconda environment
- Install each Freva plugin in dedicated anaconda environment
