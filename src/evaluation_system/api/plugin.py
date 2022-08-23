"""Definition of the base class that is used to implement user plugins.

The plugin API (Application Program Interface) is the central connection
of a user plugin code and the Freva system infrastructure. The API
enables the users to conveniently set up, run, and keep track of applied plugins.
The reference below gives an overview of how to set up user defined plugins.
For this purpose we assume that a plugin core (without Freva) already exists
- for example as a command line interface tool (cli). Once such a cli has been
set up a interface to Freva must be defined. This reference will introduce
the possible definition options below.

Here we assume that the above mentioned cli code is stored in a directory
name ``/mnt/freva/plugins/new_plugin`` furthermore the actual cli code can be
excecuted via:
    .. code-block:: console

        cli/calculate -c 5 -n 6.4 --overwrite --name=Test

With help of this API a Freva plugin can be created in ``/mnt/freva/plugin/new_plugin/plugin.py``

"""
from __future__ import annotations
import abc
from configparser import ConfigParser, ExtendedInterpolation
from contextlib import contextmanager
from datetime import datetime
from functools import partial
import logging
import os
from pathlib import Path
import re
import subprocess as sub
import sys
import stat
import shlex
import shutil
import socket
import tempfile
import traceback
import textwrap
from time import time
from typing import cast, Any, Dict, IO, Optional, Union, Iterator, Iterable, TextIO
from uuid import uuid4


from PyPDF2 import PdfReader

from evaluation_system.model.user import User
import evaluation_system.model.history.models as hist_model
import evaluation_system.model.repository as repository
from evaluation_system.misc.utils import TemplateDict
from evaluation_system.misc import config, logger as log
from evaluation_system.misc.exceptions import (
    ConfigurationException,
    deprecated_method,
    hide_exception,
)

from evaluation_system.misc.utils import PIPE_OUT
from evaluation_system.model.solr_core import SolrCore
from .workload_manager import schedule_job
from .user_data import DataReader

__version__ = (1, 0, 0)

ConfigDictType = Dict[str, Optional[Union[str, float, int, bool]]]


class PluginAbstract(abc.ABC):
    """Base class that is used as a template for all Freva plugins.
    Any api wrapper class defining Freva plugins must inherit from this class.

    Parameters
    ----------
    user : evaluation_system.model.user.User, default None
          Pre defined evaluation system user object, if None given (default)
          a new instance of a user object for the current user will be created.


    The following attributes are mandatory and have to be set:
        * :class:`__short_description__`
        * :class:`__version__`
        * :class:`__parameters__`
        * :class:`run_tool`

    Whereas the following properties can be optionally set:
        * :class:`__long_description__`
        * :class:`__tags__`
        * :class:`__category__`



    Example
    -------

    In order to configure and call this cli, a Freva wrapper api class will
    have the be created in ``/mnt/freva/plugins/new_plugin/plugin.py``.
    A minimal configuration example would look as follows:

    .. code-block:: python

        from evaluation_system.api import plugin, parameters
        class MyPlugin(plugin.PluginAbstract):
            __short_description__ = "Short plugin description"
            __long_description__ = "Optional longer description"
            __version__ = (2022, 1, 1)
            __parameters__ =  parameters.ParameterDictionary(
                                parameters.Integer(
                                    name="count",
                                    default=1,
                                    help=("This is an optional configurable "
                                          "int variable named number without "
                                          "default value and this description")
                                ),
                                parameters.Float(
                                    name="number",
                                    mandatory=True,
                                    help="Required float value without default"
                                ),
                                parameters.Bool(
                                    name="overwrite",
                                    default=False,
                                    help=("a boolean parameter "
                                          "with default value of false")
                                ),
                                parameters.String(name='str')
                              )
            def run_tool(
                self, config_dict: dict[str, str|int|bool]
            ) -> None:
                '''Definition of the tool the is running the cli.

                Parameters:
                -----------
                config_dict: dict
                    Plugin configuration stored in a dictionary
                '''

                self.call(
                    (
                      f"cli/calculate -c {config_dict['count']} "
                      f"-n {config_dict['number']} --name={config_dict['name']}
                    )
                )
                print("MyPlugin was run with", config_dict)

    .. note::
        The actual configuration is defined by the :class:`__parameters__`
        property, which is of type
        :class:`evaluation_system.api.parameters.ParameterDictionary`.


    If you need to test it use the ``EVALUATION_SYSTEM_PLUGINS`` environment
    variable to point to the source directory and package.
    For example assuming you have the source code in ``/mnt/freva/plugins``
    and the package holding the class implementing
    :class:`evaluation_system.api.plugin` is
    ``my_plugin.plugin`` (i.e. its absolute file path is
    ``/mnt/freva/plugins/my_plugin/plugin_module.py``), you would tell the system
    how to find the plugin by issuing the following command (bash & co)::

        export EVALUATION_SYSTEM_PLUGINS=/mnt/freva/plugins/my_plugin,plugin

    Use a colon to separate multiple items::

        export EVALUATION_SYSTEM_PLUGINS=/path1,plguin1:/path2,plugin2:/path3,plugin3

    By telling the system where to find the packages it can find the
    :class:`evaluation_system.api.plugin` implementations. The system just
    loads the packages and get to the classes using the
    :py:meth:`class.__subclasses__` method. The reference speaks about
    *weak references* so it's not clear if (and when) they get removed.
    We might have to change this in the future if it's not enough.
    Another approach would be forcing self-registration of a
    class in the :ref:`__metaclass__ <python:datamodel>` attribute when the
    class is implemented.

    """

    special_variables: Optional[dict[str, str]] = None
    """This dictionary resolves the *special variables* that are available

    to the plugins in a standardized manner. These variables are initialized per user and
    plugin. They go as follow:

    ================== ==================================================================
    Variables          Description
    ================== ==================================================================
    USER_BASE_DIR      Absolute path to the central directory for this user.
    USER_OUTPUT_DIR    Absolute path to where the plugin outputs for this user are stored.
    USER_PLOTS_DIR     Absolute path to where the plugin plots for this user are stored.
    USER_CACHE_DIR     Absolute path to the cached data (temp data) for this user.
    USER_UID           The users' User IDentifier
    SYSTEM_DATE        Current date in the form YYYYMMDD (e.g. 20120130).
    SYSTEM_DATETIME    Current date in the form YYYYMMDD_HHmmSS (e.g. 20120130_101123).
    SYSTEM_TIMESTAMP   Milliseconds since epoch (i.e. e.g. 1358929581838).
    SYSTEM_RANDOM_UUID A random Universal Unique Identifier (e.g. 912cca21-6364-4f46-9b03-4263410c9899).
    ================== ==================================================================

    A plugin/user might then use them to define a value in the following way::

        output_file='$USER_OUTPUT_DIR/myfile_${SYSTEM_DATETIME}blah.nc'

    """

    tool_developer: Optional[str] = None
    """Name of the developer who is responsible for the tool."""

    def __init__(self, *args, user: Optional[User] = None, **kwargs) -> None:
        """Plugin main constructor.

        It is designed to catch all calls. It accepts a ``user``
        argument containing an :class:`evaluation_system.model.user.User`
        representing the user for which this plugin will be created.
        It is used here for setting up the user-defined configuration but
        the implementing plugin will also have access to it. If no user
        is provided an object representing the current user, i.e. the user
        that started this program, is created.
        """
        self._user = user or User()
        # id of row in history table I think
        # this was being spontaneously created when running the plugin which
        # works for now because it creates a new instance on every run
        self.rowid = 0
        self._plugin_out: Optional[Path] = None

        # this construct fixes some values but allow others to be computed on
        # demand it holds the special variables that are accessible to both users
        # and developers
        # self._special_vars = SpecialVariables(self.__class__.__name__, self._user)

        plugin_name, user = self.__class__.__name__.lower(), self._user
        self._special_variables = TemplateDict(
            USER_BASE_DIR=user.getUserBaseDir,
            USER_CACHE_DIR=partial(
                user.getUserCacheDir, tool=plugin_name, create=False
            ),
            USER_PLOTS_DIR=partial(
                user.getUserPlotsDir, tool=plugin_name, create=False
            ),
            USER_OUTPUT_DIR=partial(
                user.getUserOutputDir, tool=plugin_name, create=False
            ),
            USER_UID=user.getName,
            SYSTEM_DATE=lambda: datetime.now().strftime("%Y%m%d"),
            SYSTEM_DATETIME=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"),
            SYSTEM_TIMESTAMP=lambda: str(int(time() * 1000)),
            SYSTEM_RANDOM_UUID=lambda: str(uuid4()),
        )

    @property
    @abc.abstractmethod
    def __version__(self) -> tuple[int, int, int]:
        """3-value tuple representing the plugin version.

        Example
        -------

        >>>    verion = (1, 0, 3)
        """
        raise NotImplementedError("This attribute must be implemented")

    @property
    def __long_description__(self) -> str:
        """Optional long description of this plugin."""
        return ""

    @property
    @abc.abstractmethod
    def __short_description__(self) -> str:
        """Mandatory short description of this plugin.

        It will be displayed to the user in the help and
        when listing all plugins.
        """
        raise NotImplementedError("This attribute must be implemented")

    @property
    @abc.abstractmethod
    def __parameters__(self):
        """Mandatory definitions of all known configurable parameters."""
        raise NotImplementedError("This attribute must be implemented")

    @property
    def __category__(self) -> str:
        """Optional category this plugin belongs to."""
        return ""

    @property
    def __tags__(self) -> list[str]:
        """Optional tags, that are the plugin can be described with."""
        return [""]

    def run_tool(self, config_dict: Optional[ConfigDictType] = None) -> Optional[Any]:
        """Method executing the tool.

        The method should be overidden by the custom plugin tool method.

        Parameters
        ----------
        config_dict:
            A dict with the current configuration (param name, value)
            which the tool will be run with

        Returns
        -------
        list[str]:
            Return values of :class:`prepare_output([<list_of_created_files>])` method
        """
        raise NotImplementedError("This method must be implemented")

    def _execute(self, cmd: list[str], check=True, **kwargs):
        # Do not allow calling shell=True
        kwargs["shell"] = False
        kwargs["stdout"] = sub.PIPE
        kwargs["stdin"] = None
        kwargs["universal_newlines"] = True
        kwargs.setdefault("stderr", sub.STDOUT)
        with sub.Popen(cmd, **kwargs) as res:
            stdout = cast(IO[Any], res.stdout)
            for line in iter(stdout.readline, ""):
                print(line, end="", flush=True)
            return_code = res.wait()
            if return_code and check:
                log.error("An error occured calling %s", cmd)
                log.error("Check also %s", self.plugin_output_file)
                raise sub.CalledProcessError(
                    return_code,
                    cmd,
                )
            return res

    @property
    def plugin_output_file(self) -> Path:
        """Filename where stdout is written to."""
        if self._plugin_out is None:
            pid = os.getpid()
            plugin_name = self.__class__.__name__
            log_directory = os.path.join(
                self._user.getUserSchedulerOutputDir(),
                plugin_name.lower(),
            )
            self._plugin_out = Path(log_directory) / f"{plugin_name}-{pid}.local"
        return self._plugin_out

    def _set_interactive_job_as_running(self, rowid: Optional[int]):
        """Set an interactive job as running."""
        host = socket.getfqdn()
        try:
            hist = hist_model.History.objects.get(id=rowid)
            hist.slurm_output = str(self.plugin_output_file)
            hist.host = host.partition(".")[0]
            hist.status = hist_model.History.processStatus.running
            hist.save()
        except hist_model.History.DoesNotExist:
            pass

    @contextmanager
    def _set_environment(
        self, rowid: Optional[int], is_interactive_job: bool
    ) -> Iterator[None]:
        """Set the environement."""
        env_path = os.environ["PATH"]
        stdout = [sys.stdout]
        stderr = [sys.stderr]
        log_stream_handle: Optional[logging.StreamHandler] = None
        try:
            self.plugin_output_file.touch(mode=0o2755)
        except FileNotFoundError:
            self.plugin_output_file.parent.mkdir(parents=True, mode=0o2777)
            self.plugin_output_file.touch(mode=0o2755)
        try:
            os.environ["PATH"] = f"{self.conda_path}:{env_path}"
            if is_interactive_job is True:
                f = self.plugin_output_file.open("w")
                self._set_interactive_job_as_running(rowid)
                stdout.append(f)
                stderr.append(f)
            with PIPE_OUT(*stdout) as p_sto, PIPE_OUT(*stderr) as p_ste:
                sys.stdout = p_sto
                sys.stderr = p_ste
                log_stream_handle = logging.StreamHandler(p_ste)
                log.addHandler(log_stream_handle)
                yield
        except Exception as error:
            if is_interactive_job is True:
                traceback.print_exc(file=f)
            raise error
        finally:
            os.environ["PATH"] = env_path
            sys.stdout = stdout[0]
            sys.stderr = stderr[0]
            if is_interactive_job is True:
                if log_stream_handle is not None:
                    log.removeHandler(log_stream_handle)
                f.flush()
                f.close()

    @property
    def conda_path(self) -> str:
        """Add the conda env path of the plugin to the environment.i

        :meta private:
        """

        from evaluation_system.api import plugin_manager as pm

        plugin_name = self.__class__.__name__.lower()
        try:
            plugin_path = Path(pm.get_plugins()[plugin_name].plugin_module)
        except KeyError:
            return ""
        return f"{plugin_path.parent / 'plugin_env' / 'bin'}"

    def _run_tool(
        self,
        config_dict: Optional[ConfigDictType] = None,
        unique_output: bool = True,
        out_file: Optional[Path] = None,
        rowid: Optional[int] = None,
    ) -> Optional[Any]:
        config_dict = self._append_unique_id(config_dict, unique_output)
        if out_file is None:
            is_interactive_job = True
        else:
            is_interactive_job = False
            self._plugin_out = out_file
        for key in config.exclude:
            config_dict.pop(key, "")
        with self._set_environment(rowid, is_interactive_job):
            try:
                result = self.run_tool(config_dict=config_dict)
            except NotImplementedError:
                result = deprecated_method("PluginAbstract", "run_tool")(self.runTool)(config_dict=config_dict)  # type: ignore
            return result

    def _append_unique_id(
        self, config_dict: Optional[ConfigDictType], unique_output: bool
    ) -> ConfigDictType:
        from evaluation_system.api.parameters import Directory, CacheDirectory

        config_dict = config_dict or {}
        for key, param in self.__parameters__.items():
            tmp_param = self.__parameters__.get_parameter(key)
            if isinstance(tmp_param, (Directory, CacheDirectory)) and unique_output:
                if key in config_dict.keys() and config_dict[key] is not None:
                    config_dict[key] = os.path.join(
                        str(config_dict[key]), str(self.rowid)
                    )
        return config_dict

    def quitnkill(self):
        """If error occurs quit python and kill child processes by group ID

        :meta private:
        """
        PID = os.getpid()
        self.call(f'setsid nohup bash -c "kill -9 -- -{PID}"  </dev/null &>/dev/null &')
        raise SystemExit

    @deprecated_method("PluginAbstract", "add_output_to_databrowser")
    def linkmydata(self, *args, **kwargs):  # pragma: no cover
        """Deprecated version of the :class:`add_output_to_databrowser` method.

        :meta private:
        """
        return self.add_output_to_databrowser(**args, **kwargs)

    def add_output_to_databrowser(
        self,
        plugin_output: os.PathLike,
        project: str,
        product: str,
        *,
        model: str = "freva",
        institute: Optional[str] = None,
        ensemble: str = "r1i1p1",
        time_frequency: Optional[str] = None,
        variable: Optional[str] = None,
        experiment: Optional[str] = None,
    ) -> Path:
        """Add Plugin output data to the solr database.

        This methods crawls the plugin output data directory and adds
        any files that were found to the apache solr database.

        ..note::
            Use the ``ensemble`` and ``model``
            arguments to specify the search facets that are going to be
            added to the solr server for this pluign run. This will help
            users better to better distinguish their plugin result search.

        The following facets are fixed:

        - project: ``user-<user_name>``
        - product: ``<plugin_name>``
        - dataset version: ``<history_id>``
        - realm: ``plugins``

        Parameters
        ----------
        plugin_output: os.PathLike
            Plugin output directory or file created by the files. If a
            directory is given all data files within the sub directories
            will be collected for ingestion.
        project: str
            Project facet of the input data. The project argument will distinguish
            plugin results for different setups.
        product: str
            Product facet of the input data. The product argument will distinguish
            plugin results for different setups.
        model: str, default: None
            Default model facet. If None is given (default) the model name will
            be set to ``freva``. The model argument can be used to distinguish
            plugin results for different setups.
        institute: str, default: None
            Default institute facet. Use the argument to make plugin results
            from various setups better distinguishable. If None given (default)
            the institute will be set the the freva project name.
        ensemble: str, default: r0i0p0
            Default ensemble facet. Like for model the ensemble argument should
            be used to distinguish plugins results with different setups.
        time_frequency: str, default: None
            Default time frequency facet. If None is given (default) the time
            frequency will be retrieved from the output files.
        experiment: str, default: freva-plugin
            Default time experiment facet.
        variable: str, default: None
            Default variable facet. If None is given (default) the variable
            will be retrieved from the output files.

        Returns
        -------
            Path: Path to the new directory that containes the data.
        """
        _, plugin_version = repository.get_version(self.wrapper_file)
        plugin_version = plugin_version or "no_plugin_version"
        plugin = self.__class__.__name__.lower().replace("_", "-")
        project_name = config.get("project_name", "").replace("_", "-")

        product_dir = f"{project}.{product}"
        root_dir = DataReader.get_output_directory() / f"user-{self._user.getName()}"
        drs_config = dict(
            project=root_dir.name,
            product=product_dir,
            model=model,
            experiment=experiment or "frev-plugin",
            realm=plugin,
            institute=institute or project_name,
            ensemble=ensemble,
            version=f"v{self.rowid}",
        )
        if time_frequency:
            drs_config["time_frequency"] = time_frequency
        if variable:
            drs_config["variable"] = variable
        user_data = DataReader(plugin_output, **drs_config)
        for output_file in user_data:
            new_file = user_data.file_name_from_metdata(output_file)
            new_file.parent.mkdir(exist_ok=True, parents=True, mode=0o2775)
            shutil.copy(str(output_file), str(new_file))
        SolrCore.load_fs(root_dir / product_dir, drs_type=user_data.drs_specification)
        return root_dir / product_dir

    @deprecated_method("PluginAbstract", "prepare_output")
    def prepareOutput(self, *args) -> dict[str, dict[str, str]]:
        """Deprecated method for :class:`prepare_output`.

        :meta private:
        """
        return self.prepare_output(*args)

    def prepare_output(
        self, output_files: Union[str, list[str], dict[str, dict[str, str]]]
    ) -> dict[str, dict[str, str]]:
        """Prepare output for files supposedly created.


        This method checks if the files exist and returns a dictionary with
        information about them::

            { <absolute_path_to_file>: {
                'timestamp': os.path.getctime(<absolute_path_to_file>),
                'size': os.path.getsize(<absolute_path_to_file>)
                }
            }

        Use it for the return call of run_tool.

        Parameters
        ----------
        output_files:
            iterable of strings or single string with paths to all files that
            where created by the tool.

        Returns
        -------
        dict:
            dictionary with the paths to the files that were created as
            key and a dictionary as value.
        """
        result = {}
        metadata: dict[str, str] = {}
        if isinstance(output_files, str):
            output_files = [output_files]
        for file_path in output_files:
            # we expect a meta data dictionary
            if isinstance(output_files, dict):
                if not isinstance(output_files[file_path], dict):
                    raise ValueError("Meta information must be of type dict")
                metadata = output_files[file_path]
            if os.path.isfile(file_path):

                self._extend_output_metadata(file_path, metadata)
                result[os.path.abspath(file_path)] = metadata
            elif os.path.isdir(file_path):
                # ok, we got a directory, so parse the contents recursively
                for file_path in [
                    os.path.join(r, f)
                    for r, _, files in os.walk(file_path)
                    for f in files
                ]:
                    filemetadata = metadata.copy()
                    self._extend_output_metadata(file_path, filemetadata)

                    # update meta data with user entries
                    usermetadata = result.get(os.path.abspath(file_path), {})
                    filemetadata.update(usermetadata)

                    result[os.path.abspath(file_path)] = filemetadata
            else:
                result[os.path.abspath(file_path)] = metadata
        return result

    def _extend_output_metadata(self, file_path, metadata):
        fstat = os.stat(file_path)
        if "timestamp" not in metadata:
            metadata["timestamp"] = fstat[stat.ST_CTIME]
            # metadata['timestamp'] = os.path.getctime(file_path)
        if "size" not in metadata:
            metadata["size"] = fstat[stat.ST_SIZE]
            # metadata['size'] = os.path.getsize(file_path)
        if "type" not in metadata:
            ext = os.path.splitext(file_path)
            if ext:
                ext = ext[-1].lower()
                if ext in ".jpg .jpeg .png .gif .mp4 .mov".split():
                    metadata["type"] = "plot"
                    metadata["todo"] = "copy"

                if ext in ".tif .svg .ps .eps".split():
                    metadata["type"] = "plot"
                    metadata["todo"] = "convert"

                if ext == ".pdf":

                    # If pdfs have more than one page we don't convert them,
                    # instead we offer a download link
                    pdf = PdfReader(open(file_path, "rb"))
                    num_pages = len(pdf.pages)
                    metadata["type"] = "pdf"
                    if num_pages > 1:
                        metadata["todo"] = "copy"
                    else:
                        metadata["todo"] = "convert"

                if ext in ".tex".split():
                    metadata["type"] = "plot"

                elif ext in ".nc .bin .ascii".split():
                    metadata["type"] = "data"
                if ext in [".zip"]:
                    metadata["type"] = "pdf"
                    metadata["todo"] = "copy"
                elif ext in [".html", ".xhtml"]:
                    metadata["todo"] = "copy"

    @deprecated_method("PluginAbstract", "get_help")
    def getHelp(self, **kwargs) -> str:
        """Deprecated version of the :class:`get_help` method.

        :meta private:
        """
        return self.get_help(**kwargs)

    def get_help(self, width: int = 80) -> str:
        """Representation of the help string

        This method uses the information from the implementing class name,
        :class:`__version__`, :class:`__short_description__` and
        :class:`__config_metadict__` to create a proper help. Since it returns
        a string, the implementing class might use it and extend it if required.

        Parameters
        ----------
        width:
            Wrap text to this width.

        Returns
        -------
        str:
            A string containing the help.


        :meta private:
        """
        help_txt = self.__long_description__.strip()
        if not help_txt:
            help_txt = self.__short_description__
        return "{} (v{}): {}\n{}".format(
            self.__class__.__name__,
            ".".join([str(i) for i in self.__version__]),
            help_txt,
            self.__parameters__.get_help(),
        )

    def get_current_config(self, config_dict: Optional[ConfigDictType] = None) -> str:
        """Retreive the plugin configuration as string representation.

        Parameters
        ----------
            config_dict:
                the dict containing the current configuration being displayed.
                This info will update the default values.

        Returns
        -------
        str:
            The current configuration in a string for displaying.


        :meta private:
        """
        max_size = max([len(k) for k in self.__parameters__])
        config_dict = config_dict or {}
        current_conf = []
        config_dict_resolved = self.setup_configuration(
            config_dict=config_dict, check_cfg=False
        )
        config_dict_orig = cast(Dict[str, Any], dict(self.__parameters__))
        config_dict_orig.update(config_dict or {})

        def show_key(key: str) -> str:
            """Format the configuration values.
            This functions formats the configuration depending on whether the
            configuration values contain variables or not.

            Returns
            -------
            str

            :meta private:
            """
            if config_dict_resolved[key] == config_dict_orig[key]:
                return config_dict_orig[key]
            return f"{config_dict_orig[key]} [{config_dict_resolved[key]}]"

        for key in self.__parameters__:
            line_format = "%%%ss: %%s" % max_size

            if key in config_dict:
                # user defined
                curr_val = show_key(key)
            else:
                # default value
                default_value = self.__parameters__[key]
                if default_value is None:
                    if self.__parameters__.get_parameter(key).mandatory:
                        curr_val = "- *MUST BE DEFINED!*"
                    else:
                        curr_val = "-"
                else:
                    curr_val = "- (default: %s)" % show_key(key)

            current_conf.append(line_format % (key, curr_val))

        return "\n".join(current_conf)

    @deprecated_method("PluginAbstract", "class_basedir")
    def getClassBaseDir(self) -> Optional[str]:
        """Deprecated method for class_basedir.

        :meta private:
        """
        return self.class_basedir

    @property
    def class_basedir(self) -> str:
        """Get absolute path to the module defining the plugin class."""
        return os.path.join(
            *self._split_path(self.wrapper_file)[: -len(self.__module__.split("."))]
        )

    @property
    def wrapper_file(self) -> str:
        """Get the location of the wrapper file."""
        module_path: Optional[str] = sys.modules[self.__module__].__file__
        return os.path.abspath(module_path or "")

    @property
    def user(self) -> User:
        """Return the user class for which this instance was generated."""
        return self._user

    def parse_config_str_value(
        self, param_name: str, str_value: str, fail_on_missing: bool = True
    ) -> Optional[str]:
        """Parse the string in ``str_value`` into the most appropriate value.

        The string *None* will be mapped to the value ``None``.
        On the other hand the quoted word *"None"* will remain as the string
        ``"None"`` without any quotes.

        Parameters
        ----------
        param_name:
            Parameter name to which the string belongs.
        str_value:
            The string that will be parsed.
        fail_on_missing:
            If the an exception should be risen in case the param_name is not
            found in :class:`__parameters__`

        Returns
        -------
        str:
            the parsed string, or the string itself if it couldn't be parsed,
            but no exception was thrown.

        Raises
        ------
        ( :class:`ConfigurationException` ) if parsing couldn't succeed.

        :meta private:
        """

        if str_value == "None" or str_value == '"None"':
            return None

        if self.__parameters__ is None or (
            not fail_on_missing and param_name not in self.__parameters__
        ):
            # if there's no dictionary reference or the param_name is not in it
            # and we are not failing
            # just return the str_value
            return str_value

        else:
            return self.__parameters__.get_parameter(param_name).parse(str_value)

    @deprecated_method("PluginAbstract", "setup_configuration")
    def setupConfiguration(
        self, **kwargs
    ) -> dict[str, Union[str, int, float, bool, None]]:  # pragma: no cover
        """Deprecated version of the :class:`setup_configuration` method.

        :meta private:
        """
        return self.setup_configuration(**kwargs)

    def setup_configuration(
        self,
        config_dict: Optional[ConfigDictType] = None,
        check_cfg: bool = True,
        recursion: bool = True,
        substitute: bool = True,
    ) -> dict[str, Union[str, int, float, bool, None]]:
        """Defines the configuration required for running this plugin.

        Basically the default values from :class:`__parameters__` will be
        updated with the values from ``config_dict``.
        There are some special values pointing to user-related managed by the
        system defined in :class:`evaluation_system.model.user.User.getUserVarDict` .

        Parameters
        ----------
        config_dict:
            dictionary with the configuration to be used when generating the
            configuration file.
        check_cfg:
            whether the method checks that the resulting configuration
            dictionary (i.e. the default updated by `config_dict`) has no None
            values after all substituions are made.
        recursion:
            Whether when resolving the template recursion will be applied,
            i.e. variables can be set with the values of other variables,
            e.g. ``recursion && a==1 && b=="x${a}x" => f(b)=="x1x"``

        Returns
        -------
        dict:
            a copy of self.self.__config_metadict__ with all defaults values
            plus those provided here.


        :meta private:
        """
        config_dict = config_dict or {}
        if config_dict:
            conf = dict(self.__parameters__)
            conf.update(config_dict)
            config_dict = conf
        else:
            config_dict = dict(self.__parameters__)
        if substitute:
            results = self._special_variables.substitute(
                config_dict, recursive=recursion
            )
        else:
            results = config_dict.copy()

        if check_cfg:
            self.__parameters__.validate_errors(results, raise_exception=True)

        return results

    def read_from_config_parser(self, config_parser: ConfigParser) -> dict[str, str]:
        """Reads a configuration from a config parser object.

        The values are assumed to be in a section named just like the
        class implementing this method.

        Parameters
        ----------
        config_parser:
            From where the configuration is going to be read.

        Returns
        -------
        dict[str, str]:
            Updated copy of :class:`__config_metadict__`

        :meta private:
        """

        section = self.__class__.__name__
        # create a copy of metadict
        result = dict(self.__parameters__)
        # we do this to avoid having problems with the "DEFAULT" section as it
        # might define
        # more options that what this plugin requires
        keys = set(result).intersection(config_parser.options(section))
        # update values as found in the configuration
        for key in keys:
            # parse the value as good as possible
            result[key] = self.parse_config_str_value(
                key, config_parser.get(section, key)
            )
        return result

    @deprecated_method("PluginAbstract", "read_configuration")
    def readConfiguration(self, **kwargs) -> dict[str, str]:  # pragma: no cover
        """Deprecated version of the :class:`read_configuration` method.

        :meta private:
        """
        return self.read_configuration(**kwargs)

    def read_configuration(self, fp: Iterable[str]) -> dict[str, str]:
        """Read the configuration from a file object using a ConfigParser.

        Parameters
        ----------
        fp:
            File descriptor pointing to the file where the configuration is stored.

        Returns
        -------
        dict : Updated copy of :class:`__config_metadict__`

        :meta private:
        """
        config_parser = ConfigParser(interpolation=ExtendedInterpolation())
        config_parser.read_file(fp)
        return self.read_from_config_parser(config_parser)

    def save_configuration(
        self,
        fp: Union[TextIO, IO[str]],
        config_dict: Optional[ConfigDictType] = None,
        include_defaults: bool = False,
    ) -> IO[str]:
        """Stores the given configuration to the provided file object.

        If no configuration is provided the default one will be used.

        Parameters
        ----------
        fp:
            File descriptor pointing to the file where the configuration is stored.
        config_dict:
            a metadict with the configuration to be stored. If none is provided
            the result from :class:`setup_configuration`
            with ``check_cfg=False`` will be used.
        include_defaults:
            include the default parameters.

        Returns
        -------
        typing.IO: Open file descriptor, pointing to the file where the config
                   is stored

        :meta private:
        """
        # store the section header
        if config_dict is None:
            # a default incomplete one
            config_dict = self.setup_configuration(check_cfg=False, substitute=False)
        fp.write("[%s]\n" % self.__class__.__name__)
        wrapper = textwrap.TextWrapper(
            width=80,
            initial_indent="#: ",
            subsequent_indent="#:  ",
            replace_whitespace=False,
            break_on_hyphens=False,
            expand_tabs=False,
        )
        # preserve order
        for param_name in self.__parameters__:
            if include_defaults:
                param = self.__parameters__.get_parameter(param_name)
                if param.help:
                    # make sure all new lines are comments!
                    help_lines = param.help.splitlines()
                    if param.mandatory:
                        help_lines[0] = "[mandatory] " + help_lines[0]
                    fp.write("\n".join([wrapper.fill(line) for line in help_lines]))
                    fp.write("\n")
                value = config_dict.get(param_name, None)
                if value is None:
                    # means this is not setup
                    if param.mandatory:
                        value = "<THIS MUST BE DEFINED!>"
                    else:
                        value = param.default
                        param_name = "#" + param_name
                fp.write("%s=%s\n\n" % (param_name, value))
                fp.flush()  # in case we want to stream this
            elif param_name in config_dict:
                param = self.__parameters__.get_parameter(param_name)
                value = config_dict[param_name]
                key_help = param.help
                if key_help:
                    # make sure all new lines are comments!
                    help_lines = key_help.splitlines()
                    if param.mandatory:
                        help_lines[0] = "[mandatory] " + help_lines[0]
                    fp.write("\n".join([wrapper.fill(line) for line in help_lines]))
                    fp.write("\n")
                if value is None:
                    # means this is not setup
                    if param.mandatory:
                        value = "<THIS MUST BE DEFINED!>"
                    else:
                        value = ""
                        param_name = "#" + param_name
                fp.write("%s=%s\n\n" % (param_name, param.to_str(value)))
                fp.flush()  # in case we want to stream this
        return fp

    def suggest_batchscript_name(self) -> str:
        """
        Return a suggestion for the batch script file name

        Returns
        -------
        str:
            file name of the batch mode script

        :meta private:
        """

        filename = (
            datetime.now().strftime("%Y%m%d_%H%M%S_")
            + self.__class__.__name__
            + "_"
            + str(self.rowid)
        )
        return filename

    def submit_job_script(
        self,
        config_dict: Optional[ConfigDictType] = None,
        user: Optional[User] = None,
        scheduled_id: Optional[int] = None,
        log_directory: Optional[str] = None,
        unique_output: bool = True,
        extra_options: Optional[list[str]] = None,
    ) -> tuple[int, str]:
        """Create a job script suitable for the configured workload manager.

        Parameters
        ----------

        config_dict:
            Dictionary holding the plugin config setup
        user:
            Django user object
        scheduled_id:
            The row-id of a scheduled job in history
        unique_output:
            flag indicating if the output directory should be unique
        extra_options:
            Extra options passed to the workload manager, batchmode only

        Returns
        -------
        tuple[int, str]:
            The workload manager job id, the file containing the std out.

        :meta private:
        """
        log_directory = log_directory or tempfile.mkdtemp()
        if user is None:
            user = self.user
        if scheduled_id:
            cmd = self.compose_command(
                scheduled_id=scheduled_id, unique_output=unique_output
            )
        else:
            cmd = self.compose_command(
                config_dict=config_dict or {}, unique_output=unique_output
            )

        cfg = config.get_section("scheduler_options").copy()
        cfg["args"] = cmd
        cfg["extra_options"] = extra_options or []
        cfg["name"] = self.__class__.__name__
        return schedule_job(
            config.get("scheduler_system"),
            Path(config.CONFIG_FILE).parent / "activate_sh",
            cfg,
            delete_job_script=log.root.level <= logging.DEBUG,
            log_directory=log_directory,
            config_file=Path(config.CONFIG_FILE),
        )

    class ExceptionMissingParam(Exception):
        """
        An exception class if a mandatory parameter has not been set

        :meta private:
        """

        def __init__(self, param: str):
            """
            Exceptions constructor

            Parameters
            -----------
            param:
                The missing parameter
            """
            Exception.__init__(self, "Parameter %s has to be set" % param)

    def compose_command(
        self,
        config_dict: Optional[ConfigDictType] = None,
        scheduled_id: Optional[int] = None,
        batchmode: bool = False,
        email: Optional[str] = None,
        caption: Optional[str] = None,
        unique_output: bool = True,
    ) -> list[str]:
        """Create the plugin command that is submitted.

        :meta private:
        """
        logging.debug("config dict:" + str(config_dict))
        logging.debug("scheduled_id:" + str(scheduled_id))
        tool_param = [self.__class__.__name__.lower()]
        cmd_param = []
        # write explicitly if batchmode is requested
        if batchmode:
            cmd_param.append("--batchmode")
        # add a given e-mail
        if email:
            cmd_param.append(f"--mail={email}")
        # add a caption if given
        if caption is not None:
            quote_caption = caption
            quote_caption = caption.replace("\\", "\\\\")
            quote_caption = quote_caption.replace("'", "'\\''")
            cmd_param.append(f"--caption '{quote_caption}'")

        # append the unique_output param
        cmd_param.append(f"--unique_output {unique_output}")

        # a scheduled id overrides the dictionary behavior
        if scheduled_id:
            cmd_param.append(f"--scheduled-id {scheduled_id}")

        else:
            # store the section header
            if config_dict is None:
                # a default incomplete one
                config_dict = self.setup_configuration(
                    check_cfg=False, substitute=False
                )
            else:
                config_dict = self.setup_configuration(
                    config_dict=config_dict, check_cfg=False, substitute=False
                )

            # compose the parameters preserve order
            for param_name in self.__parameters__:
                if param_name in config_dict:
                    param = self.__parameters__.get_parameter(param_name)
                    value = config_dict[param_name]
                    isMandatory = param.mandatory

                if value is None and param_name not in config.exclude:
                    if isMandatory:
                        raise self.ExceptionMissingParam(param_name)
                elif param_name not in config.exclude:
                    tool_param.append(f"{param_name}={param.to_str(value)}")
        logging.debug(f"Execute command: {' '.join(tool_param+cmd_param)}")
        return tool_param + cmd_param

    def call(
        self,
        cmd_string: Union[str, list[str]],
        check: bool = True,
        **kwargs,
    ) -> sub.Popen[Any]:
        """Run command with arguments and return a CompletedProcess instance.

        The returned instance will have attributes args, returncode, stdout and
        stderr. By default, stdout and stderr are not captured, and those
        attributes will be None. Pass stdout=PIPE and/or stderr=PIPE in order
        to capture them.

        Please refer to the ``subprocess.Popen`` python build in module for
        more details.

        Parameters
        ----------
        cmd_string:
            the command to be submitted.
        check:
            If check is True and the exit code was non-zero, it raises a
            CalledProcessError. The CalledProcessError object will have the
            return code in the returncode attribute, and output & stderr
            attributes if those streams were captured.
        kwargs:
            Additional arguments passed to ``subprocess.Popen``

        Returns
        -------
        subprocess.Popen:
            sub-process return value
        """
        if isinstance(cmd_string, str):
            cmd = shlex.split(cmd_string)
        else:
            cmd = cmd_string
        log.debug("Calling: %s", " ".join(cmd))
        try:
            res = self._execute(cmd, check=check, **kwargs)
        except sub.CalledProcessError as cmd_error:
            with hide_exception():
                raise cmd_error
        return res

    def _split_path(self, path: str) -> list[str]:
        """Help function to split a path"""
        rest_path = os.path.normpath(path)
        result: list[str] = []
        while rest_path:
            old_path = rest_path
            rest_path, path_item = os.path.split(rest_path)
            if old_path == rest_path:
                result.insert(0, rest_path)
                break
            result.insert(0, path_item)
        return result
