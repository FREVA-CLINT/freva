The freva command line interface
================================

This section introduces the usage of the freva command line interface -
*cli*. The tutorial assumes that you have already access to ``freva``
either because you've setup an instance yourself or one has been setup
by the freva *admin* team. Hence it is assumed that you know how to
access freva. If this is not the case please contact one of your
freva *admins* for help.

A general usage overview of the available freva sub-commands is
available via the ``--help`` option:

.. code:: bash

    freva --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


The most common sub-commands are ``databrowser`` and ``plugin``. You can
get more help on the actual commands using the sub-commands ``--help``
option, for example getting help on the ``databrowser usage``:

.. code:: bash

    freva databrowser --help


.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



.. note::
   Instead of using sub-commands you have also the option to use
   commands. For example the command ``freva-databrowser`` is equivalent to
   ``freva databrowser``, ``freva-crawl-my-data`` to
   ``freva crawl-my-data`` etc.

Searching for data: the ``freva-databrowser`` command
-----------------------------------------------------

All files available on in the project are scanned and indexed via a data
search server. This allows you to query the server which
responds almost immediately. To search for data you can either use the
``freva-databrowser`` command or the ``freva databrowser`` sub-command.
Let’s inspect the help menu of the databrowser sub-command:

.. code:: bash

    freva-databrowser --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


The databrowser expects a list of key=value pairs. The order of the
pairs doesn’t really matter. Most important is that you don’t need to
split the search according to the type of data you are searching for.
You can search for files both on observations, reanalysis, and
model data all at the same time. Also important is that all searches are
case *insensitive*. You can also search for attributes themselves
instead of file paths. For example you can search for the list of
variables available that satisfies a certain constraint (e.g. sampled
6hr, from a certain model, etc).

.. code:: bash

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
| attribute=‘val\*’                           | Search for files       |
|                                             | containing a value for |
|                                             | attribute that starts  |
|                                             | with the prefix val    |
+---------------------------------------------+------------------------+
| attribute=*lue                              | Search for files       |
|                                             | containing a value for |
|                                             | attribute that ends    |
|                                             | with the suffix lue    |
+---------------------------------------------+------------------------+
| attribute=*alu\*                            | Search for files       |
|                                             | containing a value for |
|                                             | attribute that has alu |
|                                             | somewhere              |
+---------------------------------------------+------------------------+
| attribute=/.*alu.*/                         | Search for files       |
|                                             | containing a value for |
|                                             | attribute that matches |
|                                             | the given regular      |
|                                             | expression (yes! you   |
|                                             | might use any regular  |
|                                             | expression to find     |
|                                             | what you want. (See    |
|                                             | appendix)              |
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
| attribute_not_=value1                       | attribute_not_=value2  |
|                                             | Search for files       |
|                                             | containing NEITHER     |
|                                             | value1 or value2       |
+---------------------------------------------+------------------------+

.. note::

    When using \* remember that your shell might give it a
    different meaning (normally it will try to match files with that name)
    to turn that off you can use backslash / in most shells

You might as well want to now about possible values that an attribute
can take after a certain search is done. For this you use the
``--facet`` flag (facets are the possible attributes that partition the
result set). For example to see the variables that are available in the
``observations`` project:

.. code:: bash

    freva-databrowser project=observations --all-facets

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--all-facets"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


Instead of querying all facet to you get information on certain keys
(facets) only:

.. code:: bash

    freva-databrowser --facet time_frequency --facet variable project=observations

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "databrowser", "--facet", "time_frequency", "--facet", "variable", "project=observations"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())


Running data analysis plugins: the ``freva-plugin`` command
-----------------------------------------------------------

Already defined data analysis tools can be started with the
``freva-plugin`` command or the ``freva plugin`` sub-command. Let’s
inspect the help menu of the ``plugin`` command:

.. code:: bash

    freva-plugin --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "plugin", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



As the help menu suggests you can list all available tools using the
``-l`` option (or ``--list``, ``--list-tools``):

.. code:: bash

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

.. code:: bash

    freva-plugin --doc animator

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "plugin", "--doc", "animator"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



The parameters are also given as key=values pairs. But not all of the
above parameters are mandatory. Let's use one ``project`` search key and
animate its content.

.. code:: bash

    freva plugin animator project=observations variable=pr cmap=Blues fps=5 output_unit=mm/h vmin=0 vmax=5 suffix=gif

.. execute_code::
   :hide_code:

   from pathlib import Path
   from subprocess import run, PIPE
   import shutil
   res = run(["freva", "plugin", "animator",
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
   out_f = Path(out.split("\n")[-2].split()[2]).absolute()
   gif = Path(".") / "source" / "_static" / "animator_output.gif"
   print(out_f, Path.cwd())
   shutil.copy(out_f, gif)

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

.. code:: bash

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
   out = res.stderr.decode()
   print(out)

Inspecting previous analysis jobs: the ``freva-history`` command
----------------------------------------------------------------

Sometimes it can be useful to access the status of past plugin
applications. The ``freva-history`` command or ``freva history``
sub-command can do that:

.. code:: bash

    freva-history --help

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "history", "--help"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())



Let’s get the last 3 entries of the ``dummyplugin`` plugin history

.. code:: bash

    freva-history --limit 1 --plugin dummyplugin

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "history", "--limit", "1", "--plugin", "dummyplugin"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stderr.decode())
   print(res.stdout.decode())



The entries are sorted by their ``id``. For example you can query the
full configuration by given the id:

.. code:: bash

    freva-history --entry-ids 136 --full-text

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "history", "--limit", "1", "--full-text"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())




If you wanted to re-run the command of a certain past configuration you
can use ``--return-command`` to get the command that was used:

.. code:: bash

    freva-history  --entry-ids 136 --return-command

.. execute_code::
   :hide_code:

   from subprocess import run, PIPE
   res = run(["freva", "history", "--limit", "1", "--return-command"], check=True, stdout=PIPE, stderr=PIPE)
   print(res.stdout.decode())
