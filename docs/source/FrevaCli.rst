The Freva command line interface
================================

This section introduces the usage of the Freva command line interface -
cli. The tutorial assumes that you have already access to Freva
either because you've setup an instance yourself or one has been setup
by the Freva admin team. Hence it is assumed that you know how to
access Freva. If this is not the case please contact one of your
Freva admins for help.

A general usage overview of the available Freva sub-commands is
available via the ``--help`` option:

.. code:: console

    freva --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


The most common sub-commands are ``databrowser`` and ``plugin``. You can
get more help on the actual commands using the sub-commands ``--help``
option, for example getting help on the ``databrowser usage``:

.. code:: console

    freva databrowser --help


.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



.. note::
   Instead of using sub-commands you have also the option to use
   commands. For example the command ``freva-databrowser`` is equivalent to
   ``freva databrowser``, ``freva-user-data`` to
   ``freva user-data`` etc.

Searching for data: the ``freva-databrowser`` command
-----------------------------------------------------

All files available on in the project are scanned and indexed via a data
search server. This allows you to query the server which
responds almost immediately. To search for data you can either use the
``freva-databrowser`` command or the ``freva databrowser`` sub-command.
Let’s inspect the help menu of the databrowser sub-command:

.. code:: console

    freva-databrowser --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


The databrowser expects a list of key=value pairs. The order of the
pairs doesn’t really matter. Most important is that you don’t need to
split the search according to the type of data you are searching for.
You can search for files within observations, reanalysis and
model data at the same time. Also important is that all queries are
case *insensitive*. You can also search for attributes themselves
instead of file paths. For example you can search for the list of
variables available that satisfies a certain constraint (e.g. sampled
6hr, from a certain model, etc).

.. code:: console

    freva-databrowser project=observations variable=pr model=cp*

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


There are many more options for defining a value for a given key:

+---------------------------------------------+------------------------+
| Attribute syntax                            | Meaning                |
+=============================================+========================+
| attribute=value                             | Search for files       |
|                                             | containing exactly     |
|                                             | that attribute         |
+---------------------------------------------+------------------------+
| attribute='val\*'                           | Search for files       |
|                                             | containing a value for |
|                                             | attribute that starts  |
|                                             | with the prefix val    |
+---------------------------------------------+------------------------+
| attribute='*lue'                            | Search for files       |
|                                             | containing a value for |
|                                             | attribute that ends    |
|                                             | with the suffix lue    |
+---------------------------------------------+------------------------+
| attribute='*alu\*'                          | Search for files       |
|                                             | containing a value for |
|                                             | attribute that has alu |
|                                             | somewhere              |
+---------------------------------------------+------------------------+
| attribute='/.*alu.*/'                       | Search for files       |
|                                             | containing a value for |
|                                             | attribute that matches |
|                                             | the given regular      |
|                                             | expression (yes! you   |
|                                             | might use any regular  |
|                                             | expression to find     |
|                                             | what you want.)        |
+---------------------------------------------+------------------------+
| attribute=value1 attribute=value2           | Search for files       |
|                                             | containing either      |
|                                             | value1 OR value2 for   |
|                                             | the given attribute    |
|                                             | (note that’s the same  |
|                                             | attribute twice!)      |
+---------------------------------------------+------------------------+
| attribute1=value1 attribute2=value2         | Search for files       |
|                                             | containing value1 for  |
|                                             | attribute1 AND value2  |
|                                             | for attribute2         |
+---------------------------------------------+------------------------+
| attribute_not_=value                        | Search for files NOT   |
|                                             | containing value       |
+---------------------------------------------+------------------------+
| attribute_not_=value1 attribute_not_=value2 | Search for files       |
|                                             | containing neither     |
|                                             | value1 nor value2      |
+---------------------------------------------+------------------------+

.. note::

    When using \* remember that your shell might give it a
    different meaning (normally it will try to match files with that name)
    to turn that off you can use backslash \ (key=\*) or use quotes (key='*').

In some cases it might be useful to know how many files are found in the
databrowser for certain search constraints. In such cases you can use the
``count`` flag to count the number of *found* files instead of getting
the files themselves.

.. code:: console

    freva-databrowser project=observations --count

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--count"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

Sometimes it might be useful to subset the data you're interested in by time.
To do so you can use the `time` search key to subset time steps and whole time
ranges. For example let's get the for certain time range:

.. code:: console

    freva-databrowser project=observations time='2016-09-02T22:15 to 2016-10'

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "time=2016-09-02T22:15 to 2016-10"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

The default method for selecting time periods is ``flexible``, which means
all files are selected that cover at least start or end date. The
``strict`` method implies that the *entire* search time period has to be
covered by the files. Using the ``strict`` method in the example above would
only yield on file because the first file contains time steps prior to the
start of the time period:

.. code:: console

    freva-databrowser project=observations time='2016-09-02T22:15 to 2016-10' --time-select strict

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "time=2016-09-02T22:15 to 2016-10", "--time-select", "strict"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

Giving single time steps is also possible:

.. code:: console

    freva-databrowser project=observations time='2016-09-02T22:10'

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "time=2016-09-02T22:00"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

.. note::

    The time format has to follow the
    `ISO-8601 <https://en.wikipedia.og/wiki/ISO_8601>`_ standard. Time *ranges*
    are indicated by the ``to`` keyword such as ``2000 to 2100`` or
    ``2000-01 to 2100-12`` and alike. Single time steps are given without the
    ``to`` keyword.


You might as well want to know about possible values that an attribute
can take after a certain search is done. For this you use the
``--facet`` flag (facets are the attributes used to search for and sub set
the data). For example to see all facets that are available in the
``observations`` project:

.. code:: console

    freva-databrowser project=observations --facet all

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--facet", "all"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

Instead of querying all facets to get information on specific ones:

.. code:: console

    freva-databrowser --facet time_frequency --facet variable project=observations

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--facet", "time_frequency", "--facet", "variable", "project=observations"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

You can also retrieve information on how many facets are found by the databrowser
by giving the `count` flag

.. code:: console

    freva-databrowser --facet time_frequency --facet variable project=observations --count

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--facet", "time_frequency", "--facet", "variable", "project=observations", "--count"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


In some cases it might be useful to retrieve meta data from a file path this
can be achieved by using the ``file=`` search facet:

.. code:: console

    freva-databrowser file=.docker/data/observations/grid/CPC/CPC/cmorph/30min/atmos/30min/r1i1p1/v20210618/pr/pr_30min_CPC_cmorph_r1i1p1_201609020000-201609020030.nc --facet all

.. execute_code::
   :hide_code:

   import freva
   from pathlib import Path
   file = Path(".") / ".docker/data/observations/grid/CPC/CPC/cmorph/30min/atmos/30min/r1i1p1/v20210618/pr/pr_30min_CPC_cmorph_r1i1p1_201609020000-201609020030.nc"
   res = freva.databrowser(file=file.absolute(), all_facets=True)
   print(res)


Running data analysis plugins: the ``freva-plugin`` command
-----------------------------------------------------------

Already defined data analysis tools can be started with the
``freva-plugin`` command or the ``freva plugin`` sub-command. Let’s
inspect the help menu of the ``plugin`` command:

.. code:: console

    freva-plugin --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "plugin", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



As the help menu suggests you can list all available tools using the
``-l`` option (or ``--list``, ``--list-tools``):

.. code:: console

    freva-plugin -l

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "plugin", "-l"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



This means currently we have two plugins available (``animator`` and
``dummyplugin``). The general syntax is
``freva-plugin <plugin-name> [options]`` for example to inspect the
documentation of a certain plugin you can use the ``--doc`` option.
Here we concentrate on the Animator plugin. A simple plugin that creates
animations of geospatial data. The basic usage of that command can be
retrieved by:

.. code:: console

    freva-plugin --doc animator

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "plugin", "--doc", "animator"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



The parameters are also given as key=values pairs. But not all of the
above parameters are mandatory. Let's use one ``project`` search key and
animate its content.

.. code:: console

    freva plugin animator project=observations variable=pr cmap=Blues fps=5 output_unit=mm/h vmin=0 vmax=5 suffix=gif

.. execute_code::
   :hide_code:

   from pathlib import Path
   from subprocess import run, PIPE
   import shutil
   res = run(["freva", "plugin", "animator",
             "project=observations",
             "variable=pr",
             ], check=True, stdout=PIPE, stderr=PIPE)
   out = res.stdout.decode()
   print(out)
   out_f = Path(out.split("\n")[-2].split()[2]).absolute()

The plugin will produce the following output:

.. image:: _static/animator_output.gif
   :width: 400

This plugin will run in so called interactive mode. That means that it
will run on the login node and block your shell until the command is
completed. This can be problematic if you have jobs that might take time
to finish. An alternative is setting the ``-–batchmode`` flag. This flag
tells the plugin to submit a job to the computing queue. The computing
nodes are the core of any high performance computing system. Let’s
submit the previous plugin job to the computing queue:

.. code:: console

    freva plugin animator project=observations variable=pr cmap=Blues fps=5 output_unit=mm/h vmin=0 vmax=5 suffix=gif --batchmode

.. execute_code::
   :hide_code:

   from pathlib import Path
   from subprocess import run, PIPE
   import shutil
   res = run(["freva", "plugin", "animator",
             "--batchmode",
             "project=observations",
             "variable=pr",
             "cmap=Blues",
             "fps=5",
             "output_unit=mm/h",
             "vmin=0",
             "vmax=5",
             "suffix=gif",
             ], check=True, stdout=PIPE, stderr=PIPE)
   out = res.stdout.decode()
   print(out)


If you want to evaluate the plugins output you can use the ``--json`` flag.
This flag converts the result of a plugin application to a json string that
can be processed by a json parser for example ``jq``. Consider the following
exmample (in bash/zsh) where we use ``--json`` flag to get all netcdf output
files from a plugin run.

.. code:: console

    files=$(freva plugin dummypluginfolders --json|jq -r '.result| keys[] | select(endswith(".nc"))')
    echo $files

.. execute_code::
   :hide_code:

   import freva
   res = freva.run_plugin("dummypluginfolders")
   for file in res.get_result_paths():
      print(file)

.. note::

    If you use the ``--batchmode`` flag in combination with ``--json`` flag the
    commandline will wait for the batch job to finish.


Inspecting previous analysis jobs: the ``freva-history`` command
----------------------------------------------------------------

Sometimes it can be useful to access the status of past plugin
applications. The ``freva-history`` command or ``freva history``
sub-command can do that:

.. code:: console

    freva-history --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "history", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



Let’s get the last entry (default is 10 entries) of the ``dummyplugin`` plugin history

.. code:: console

    freva-history --limit 1 --plugin dummyplugin

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "history", "--limit", "1", "--plugin", "dummyplugin"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


Dates are given using the `ISO-8601 <https://en.wikipedia.og/wiki/ISO_8601>`_
format.

The entries are sorted by their ``id``. For example you can query the
full configuration by giving the id:


.. code:: console

    freva-history --entry-ids 136 --full-text


.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "history", "--limit", "1", "--full-text"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())




To re-run a command of a past configuration you
can use the ``--return-command`` option to get the command that was used:

.. code:: console

    freva-history  --entry-ids 136 --return-command

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "history", "--limit", "1", "--return-command"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


Like in for the ``plugin`` sub command you can use the ``--json`` flag to
to make the output of the history command machine readable and evaluate its
output. For example can we query the output files of the last 3 plugin
applications:

.. code:: console

    freva-history  --limit 3 --json|jq -r '.[].result | keys[]'

.. execute_code::
   :hide_code:

   import freva
   for hist in freva.history(limit=3, return_results=True):
      for file in hist["result"].keys():
         print(file)

Managing your own datasets: the ``freva-user-data`` command
-----------------------------------------------------------

Freva offers the possibility to share custom datasets with other users
by making it searchable via ``freva-databrowser``. With help of the
``freva-user-data`` command users can add their own data to the
central data location, (re)-index or delete data in the databrowser.


.. note::

    Any data that has been added by users will be assigned a special project
    name: ``project=user-$USER``.

Let’s inspect the help menu of the ``freva-user-data`` or ``freva user-data``
command:

.. code:: console

    freva-user-data --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "user-data", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

Add new data to the databrowser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To be able to add data to the databrowser the file names must follow a strict
standard and the files must reside in a specific location. The
``add`` sub command takes care about the correct file naming and location.
No pre requirements other than the file has to be a valid ``netCDF`` or
``grib`` file are assumed. In other words this sub command places the user data
with the correct naming structure to the correct location.

.. code:: console

    freva-user-data add --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "user-data", "add", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

Suppose you've gotten data from somewhere and want to add this data into the
databrowser to make it accessible to others. In this specific
example we assume that you have stored your `original` data in the
``/tmp/my_awesome_data`` folder.
E.g ``/tmp/my_awesome_data/outfile_0.nc...tmp/my_awesome_data/outfile_9.nc``
The routine will try to gather all necessary metadata from the files. You'll
have to provide additional metadata if mandatory keywords are missing.
To make the routine work in this example we have to provide the ``institute``,
``model`` and ``experiment`` keywords:

.. code:: console

    freva-user-data add eur-11b /tmp/my_awesome_data/outfile_?.nc \
    --institute clex --model UM-RA2T --experiment Bias-correct
    freva-databrowser experiment=bias-correct

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "user-data", "add", "eur-11b", "/tmp/my_awesome_data/outfile_?.nc",
              "--institute", "clex", "--model", "UM-RA2T", "--experiment",
              "Bias-correct"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())
   run(["freva-databrowser", "experiment=bias-correct"], check=True, stderr=PIPE)

.. note::
   Freva allows also *plugins* to directly index output datasets via
   :class:`add_output_to_databrowser` method (``linkmydata`` is the deprecated
   method of former Freva versions). For more information please
   take a look at :ref:`PluginAPI`.

Remove your data from the databrowser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``delete`` sub command removes entries from the databrowser and if necessary
existing files from the central user data location.

.. code:: console

    freva-user-data delete --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "user-data", "delete", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

Any data in the central user directory that belongs to the user can
be deleted from the databrowser and also from the central data location:

.. code:: console

    freva-user-data delete /tmp/user_data/user-<user_name>
    freva-databrowser experiment=bias-correct

.. execute_code::
   :hide_code:

   from freva import UserData
   from subprocess import run, PIPE
   user_data = UserData()
   user_data.delete(user_data.user_dir)
   run(["freva-databrowser", "experiment=bias-correct"], check=True, stderr=PIPE)


(Re)-Index existing data to the databrowser
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``index`` subcommand can be used to update the databrowser for existing
user data. For example, if data has been removed from the databrowser it can
be re-added:

.. code:: console

    freva-user-data index --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "user-data", "index", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())

Currently, only files on the file system (``--data-type {fs}``) are supported.

.. code:: console

    freva-user-data delete /tmp/user_data/user-freva
    freva-databrowser experiment=bias-correct

.. execute_code::
   :hide_code:

   from freva import UserData
   from subprocess import run, PIPE
   user_data = UserData()
   user_data.index(user_data.user_dir)
   run(["freva-databrowser", "experiment=bias-correct"], check=True, stderr=PIPE)
