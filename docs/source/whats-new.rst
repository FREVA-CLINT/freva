What's new
===========

.. toctree::
   :maxdepth: 0
   :titlesonly:

v2506.0.0
~~~~~~~~~

Bug fixes
+++++++++
- Fix sig term handler.

v2504.0.0
~~~~~~~~~

New Features
++++++++++++
- Plugin SelectField can receive multiple and custom user input values.
- ``PluginStatus`` can access the status of ``job_ids`` of any user.


v2502.0.1
~~~~~~~~~

Bug fixes
+++++++++
- Catch PermissionError when user config dir does not exist.

Documentations
++++++++++++++
- Added multi-version queries.



v2502.0.0
~~~~~~~~~

New Features
++++++++++++
- When submitting a plugin the freva history ID can be queried by
  accessing the ``history_id`` property of the ``PluginStatus`` response
  class.

Bug fixes
+++++++++
- Fixed unique output file bug for interactive plugin jobs.


v2408.0.0
~~~~~~~~~

Internal Changes
++++++++++++++++
- Change ``root_dir`` -> ``root_path`` in DRS specs.



v2406.0.1
~~~~~~~~~

New Features
++++++++++++
- The history method and cli history command can expand the query
  to other user with ``user-name=<username>`` (for all users, ``user-name=all``)
  in the python module or ``--user-name`` in the cli.

Bug fixes
+++++++++

- Fixed how the .gif animations are transformed and moved into the `preview` folder
  (for the web).

Documentations
++++++++++++++
- Added documentation of the freva history.

Internal Changes
++++++++++++++++
- Updated unit tests.


v2406.0.0
~~~~~~~~~

Bug fixes
+++++++++

- Fixed plugin batchmode submit bug. Batchmode plugins did not pick up the
  correct evaluation system config file. This has been fixed now.
- Revised minor typographical errors in the documentation and code comments.
- Created a standard_main function in ``utils.py`` for cli

Documentations
++++++++++++++
- Added documentation of the freva databrowser rest api.

Internal Changes
++++++++++++++++
- Updated unit tests.
- Added .pre-commit-config.yaml

v2309.0.1
~~~~~~~~~~
New Features
++++++++++++

Breaking changes
++++++++++++++++

Deprecations
++++++++++++
- move ``freva.esgf`` to the following methods:
  - :py:meth:`freva.esgf_browser`
  - :py:meth:`freva.esgf_facets`
  - :py:meth:`freva.esgf_datasets`
  - :py:meth:`freva.esgf_download`
  - :py:meth:`freva.esgf_query`

Bug fixes
+++++++++

Documentations
++++++++++++++
- added documentation to ``esgf`` method both for cli and python module.

Internal Changes
++++++++++++++++


v2309.0.0
~~~~~~~~~~

New Features
++++++++++++
- Plugin and history output can be parsed using the ``--json`` flag from the
   command line
- The plugin method and cli plugin command can be instructed to wait for any
  batch job. ``wait=True`` in the python module or ``--wait`` in the cli
- Users can interact with the plugin output, using the return value of the
  ``freva.run_plugin`` method.

Breaking changes
++++++++++++++++

Deprecations
++++++++++++

Bug fixes
+++++++++

Documentations
++++++++++++++

Internal Changes
++++++++++++++++



v2307.0.2
~~~~~~~~~

New Features
++++++++++++

Breaking changes
++++++++++++++++

Deprecations
++++++++++++
- cli ``freva databrowser --all-facets`` is made deprecated, use ``--facet '*'`` or ``--facet all`` instead

Bug fixes
+++++++++
- cli ``freva plugin --unique-output False`` feature reinstated, working as within python module.

Documentations
++++++++++++++

Internal Changes
++++++++++++++++

v2303.0.0
~~~~~~~~~

New Features
++++++++++++
- User data can be ingested also if not all data files match directory reference
  standard.
- A new databrowser key (uri) was added which represents the object storage
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
- ``follow/unfollow_history_tag`` receives a user object as argument instead of string
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
    - Instead of ``freva plugin animtaor --batchmode=True`` → ``freva plugin animator --batchmode``
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
