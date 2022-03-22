"""
This module defines the basic objects for implementing a plug-in.
"""
from __future__ import annotations
import abc
from configparser import ConfigParser, ExtendedInterpolation
from contextlib import contextmanager
from datetime import datetime
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess as sub
import sys
import stat
import shlex
import tempfile
import traceback
import textwrap
from time import time
from typing import Any, Dict, IO, Optional, Union, Iterator, Iterable, TextIO

from PyPDF2 import PdfFileReader

from evaluation_system.model.user import User
import evaluation_system.model.history.models as hist_model
from evaluation_system.misc.utils import TemplateDict
from evaluation_system.misc import config, logger as log
from evaluation_system.misc.utils import PIPE_OUT
from evaluation_system.model.solr_core import SolrCore
from .workload_manager import schedule_job

__version__ = (1, 0, 0)
config_dict_type = Dict[str, Optional[Union[str, float, int, bool]]]


class ConfigurationError(Exception):
    """Signals the configuration failed somehow."""

    pass


# TODO: I don't really see why we would need a metaclass here. Simple base.
class PluginAbstract(metaclass=abc.ABCMeta):
    """This is the base class for all plug-ins.

    It is the only class that needs to be inherited from when implementing a plug-in.
    From it, you'll need to implement the few attributes and/or methods marked
    as abstract with the decorator ``@abc.abstractproperty`` or
    ``@abc.abstractmethod``. If you don't you'll get a message informing you
    which methods and or variables need to be implemented. Refer to their
    documentation to know what they should do.

    As usual, you may overwrite all methods and properties defined in here,
    but you'll be breaking the contract between the methods so you'll have to
    make sure it doesn't break anything else. Please write some tests
    for your own class that checks it is working as expected. The best
    practice is to use what is provided as is and only
    implement what is required (and more, if you need, just don't overwrite
    any methods/variable if you don't need to)

    This very short example shows a complete plug-in. Although it does nothing
    it already show the most important part,
    the :class:`evaluation_system.api.parameters.ParameterDictionary` used
    for defining meta-data on the parameters::

    Example:
    --------
        from evaluation_system.api import plugin, parameters

        class MyPlugin(plugin.PluginAbstract):
            __short_description__ = "MyPlugin short description"
            __version__ = (0,0,1)
            __parameters__ =  parameters.ParameterDictionary(
                                parameters.Integer(
                                    name="number",
                                    help=("This is an optional configurable "
                                          "int variable named number without "
                                          default value and this description")
                                ),
                                parameters.Float(
                                    name="the_number",
                                    mandatory=True,
                                    help="Required float value without default"
                                ),
                                parameters.Bool(
                                    name="really",
                                    default=False,
                                    help=("a boolean parameter named really "
                                          "with default value of false")
                                ),
                                parameters.String(name='str')
                              )

            def runTool(self, config_dict=None):
                print("MyPlugin", config_dict)

    If you need to test it use the ``EVALUATION_SYSTEM_PLUGINS`` environmental
    variable to point to the source directory and package.
    For example assuming you have th source code in ``/path/to/source`` and
    the package holding the class implementing
    :class:`evaluation_system.api.plugin` is
    ``package.plugin_module`` (i.e. its absolute file path is
    ``/path/to/source/package/plugin_module.py``), you would tell the system
    how to find the plug-in by issuing the following command (bash & co)::

        export EVALUATION_SYSTEM_PLUGINS=/path/to/source,package.plugin_module

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
    """This dictionary is used to resolve the *special variables* that are available
to the plug-ins for defining some values of their parameters in a standardize manner.
These are initialized per user and plug-in. The variables are:

================== ============================================================
Variables          Description
================== ============================================================
USER_BASE_DIR      Absolute path to the central directory for this user.
USER_OUTPUT_DIR    Absolute path to where the output data for this user.
USER_PLOTS_DIR     Absolute path to where the plots for this user is stored.
USER_CACHE_DIR     Absolute path to to the cached data for this user.
USER_UID           The users UID
SYSTEM_DATE        Current date in the form YYYYMMDD (e.g. 20120130).
SYSTEM_DATETIME    Current date in the form YYYYMMDD_HHmmSS (e.g. 20120130_101123).
SYSTEM_TIMESTAMP   Milliseconds since epoch (i.e. e.g. 1358929581838).
SYSTEM_RANDOM_UUID A random UUID string (e.g. 912cca21-6364-4f46-9b03-4263410c9899).
================== ============================================================

A plug-in/user might then use them to define a value in the following way::

    output_file='$USER_OUTPUT_DIR/myfile_${SYSTEM_DATETIME}blah.nc'

"""

    tool_developer: Optional[str] = None

    def __init__(self, *args, **kwargs):
        """Plugin main constructor.

        It is designed to catch all calls. It accepts a ``user``
        argument containing an :class:`evaluation_system.model.user.User`
        representing the user for which this plug-in will be created.
        It is used here for setting up the user-defined configuration but
        the implementing plug-in will also have access to it. If no user
        is provided an object representing the current user, i.e. the user
        that started this program, is created.
        """
        if "user" in kwargs:
            self._user = kwargs.pop("user")
        else:
            self._user = User()
        # id of row in history table I think
        # this was being spontaneously created when running the plugin which works
        # for now because it creates a new instance on every run
        self.rowid = 0
        self._plugin_out: Optional[Path] = None

        # this construct fixes some values but allow others to be computed on demand
        # it holds the special variables that are accessible to both users
        # and developers
        # self._special_vars = SpecialVariables(self.__class__.__name__, self._user)

        from functools import partial
        from uuid import uuid4

        plugin_name, user = self.__class__.__name__, self._user
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

    @abc.abstractproperty
    def __version__(self):
        """3-value tuple representing the plugin version.

        Example:
        --------
            verion = (1, 0, 3)
        """
        raise NotImplementedError("This attribute must be implemented")

    @property
    def __long_description__(self):
        """Long description of the plugion."""
        return ""

    @abc.abstractproperty
    def __short_description__(self):
        """A short description of this plug-in.

        It will be displayed to the user in the help and
        when listing all plug-ins.
        """
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractproperty
    def __parameters__(self):
        """The the definitions of all known configurable parameters."""
        raise NotImplementedError("This attribute must be implemented")

    @property
    def __category__(self) -> str:
        return ""

    @property
    def __tags__(self) -> list[str]:
        return [""]

    @abc.abstractmethod
    def runTool(self, config_dict: config_dict_type = {}) -> Optional[Any]:
        """Method executing the tool.

        Starts the tool with the given configuration.

        Parameters:
        -----------
        config_dict:
            A dict with the current configuration (param name, value)
            which the tool will be run with

        Returns:
        --------
        see and use self.prepareOutput([<list_of_created_files>])
        """
        raise NotImplementedError("This method must be implemented")

    @staticmethod
    def _execute(cmd):
        res = sub.Popen(cmd, stdout=sub.PIPE, universal_newlines=True)
        for stdout_line in iter(res.stdout.readline, ""):
            yield stdout_line
        res.stdout.close()
        return_code = res.wait()
        if return_code:
            raise sub.CalledProcessError(return_code, cmd)

    @property
    def plugin_output_file(self) -> Path:
        """Define a plugin output file."""
        if self._plugin_out is None:
            pid = os.getpid()
            plugin_name = self.__class__.__name__
            log_directory = os.path.join(
                self._user.getUserSchedulerOutputDir(),
                plugin_name.lower(),
            )
            self._plugin_out = Path(log_directory) / f"{plugin_name}-{pid}.local"
        return self._plugin_out

    def _set_interactive_job_as_running(self, rowid: int):
        """Set an interactive job as running."""
        try:
            h = hist_model.History.objects.get(id=rowid)
            h.slurm_output = str(self.plugin_output_file)
            h.status = hist_model.History.processStatus.running
            h.save()
        except hist_model.History.DoesNotExist:
            pass

    @contextmanager
    def set_environment(self, rowid: int, is_interactive_job: bool) -> Iterator[None]:
        """Set the environement."""
        env_path = os.environ["PATH"]
        stdout = [sys.stdout]
        stderr = [sys.stderr]
        try:
            self.plugin_output_file.parent.mkdir(exist_ok=True, parents=True)
            os.environ["PATH"] = f"{self.conda_path}:{env_path}"
            if is_interactive_job is True:
                f = self.plugin_output_file.open("w")
                self._set_interactive_job_as_running(rowid)
                stdout.append(f), stderr.append(f)
            with PIPE_OUT(*stdout) as p_sto, PIPE_OUT(*stderr) as p_ste:
                sys.stdout = p_sto
                sys.stderr = p_ste
                yield
        except Exception as e:
            if is_interactive_job is True:
                traceback.print_exc(file=f)
            raise e
        finally:
            os.environ["PATH"] = env_path
            sys.stdout = stdout[0]
            sys.stderr = stderr[0]
            if is_interactive_job is True:
                f.flush()
                f.close()

    @property
    def conda_path(self) -> str:
        """Add the conda env path of the plugin to the environment."""

        from evaluation_system.api import plugin_manager as pm

        plugin_name = self.__class__.__name__.lower()
        try:
            plugin_path = Path(pm.get_plugins()[plugin_name].plugin_module)
        except KeyError:
            return ""
        return f"{plugin_path.parent / 'plugin_env' / 'bin'}"

    def _runTool(
        self,
        config_dict: config_dict_type = {},
        unique_output: bool = True,
        is_interactive_job: bool = True,
        rowid: Optional[int] = None,
    ) -> Optional[Any]:
        config_dict = self.append_unique_id(config_dict, unique_output)
        for key in config.exclude:
            config_dict.pop(key, "")
        with self.set_environment(rowid, is_interactive_job):
            result = self.runTool(config_dict=config_dict)
            return result

    def append_unique_id(
        self, config_dict: config_dict_type, unique_output: bool
    ) -> config_dict_type:
        from evaluation_system.api.parameters import Directory, CacheDirectory

        for key, param in self.__parameters__.items():
            tmp_param = self.__parameters__.get_parameter(key)
            if isinstance(tmp_param, Directory):
                if isinstance(tmp_param, CacheDirectory) or unique_output:
                    if key in config_dict.keys() and config_dict[key] is not None:
                        config_dict[key] = os.path.join(
                            str(config_dict[key]), str(self.rowid)
                        )
        return config_dict

    def quitnkill(self):
        """If error occurs quit python and kill child processes by group ID"""
        PID = os.getpid()
        self.call(f'setsid nohup bash -c "kill -9 -- -{PID}"  </dev/null &>/dev/null &')
        raise SystemExit

    def linkmydata(self, outputdir=None):  # pragma: no cover
        """Link the CMOR Data Structure of any output created by a tool
        crawl the directory and ingest the directory with solr::
         :param outputdir: cmor outputdir that where created by the tool.
         :return: nothing
        """
        user = self._user
        workpath = os.path.join(user.getUserBaseDir(), "CMOR4LINK")
        rootpath = config.get("project_data")
        solr_in = config.get("solr.incoming")
        solr_bk = config.get("solr.backup")
        solr_ps = config.get("solr.processing")

        # look for tool in tool
        toolintool = re.compile(
            r"^((?P<tool>[\w%]+)%(\d+|none)%(?P<project>[\w_]+)%(?P<product>[\w_]+)$)"
        )
        # Maybe os.walk for multiple projects or products
        if len(os.listdir(outputdir)) == 1:
            project = os.listdir(outputdir)[0]
            # link?
        if len(os.listdir(os.path.join(outputdir, project))) == 1:
            product = os.listdir(os.path.join(outputdir, project))[0]
        new_product = "%s.%s.%s.%s" % (
            self.__class__.__name__.lower(),
            self.rowid,
            project,
            product,
        )
        if re.match(toolintool, product):
            nproduct = re.match(toolintool, product).group("product")
            nproject = re.match(toolintool, product).group("project")
            ntool = ".%s" % re.match(toolintool, product).group("tool")
            new_product = "%s.%s.%s.%s.%s" % (
                self.__class__.__name__.lower(),
                ntool,
                self.rowid,
                nproject,
                nproduct,
            )

        # Link section
        link_path = os.path.join(rootpath, "user-" + user.getName())
        if os.path.islink(link_path):
            if not os.path.exists(link_path):
                os.unlink(link_path)
                os.symlink(workpath, os.path.join(link_path))
                if not os.path.isdir(workpath):
                    os.makedirs(workpath)
            workpath = os.path.join(os.path.dirname(link_path), os.readlink(link_path))
        else:
            if not os.path.isdir(workpath):
                os.makedirs(workpath)
            os.symlink(workpath, link_path)
        os.symlink(
            os.path.join(outputdir, project, product),
            os.path.join(workpath, new_product),
        )

        # Prepare for solr
        crawl_dir = os.path.join(link_path, new_product)
        now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output = os.path.join(solr_in, "solr_crawl_%s.csv.gz" % (now))

        # Solr part with move orgy
        SolrCore.dump_fs_to_file(crawl_dir, output)
        shutil.move(os.path.join(solr_in, output), os.path.join(solr_ps, output))
        # hallo = SolrCore.load_fs_from_file(dump_file=os.path.join(solr_ps, output))
        shutil.move(os.path.join(solr_ps, output), os.path.join(solr_bk, output))

    def prepareOutput(
        self, output_files: Union[str, list[str], dict[str, dict[str, str]]]
    ) -> dict[str, dict[str, str]]:
        """Prepare output for files supposedly created.

        This method checks the files exist and returns a dictionary with
        information about them::

            { <absolute_path_to_file>: {
                'timestamp': os.path.getctime(<absolute_path_to_file>),
                'size': os.path.getsize(<absolute_path_to_file>)
                }
            }

        Use it for the return call of runTool.

        Parameters:
        -----------
        output_files:
            iterable of strings or single string with paths to all files that
            where created by the tool.

        Returns:
        --------
        result: dict
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
                    pdf = PdfFileReader(open(file_path, "rb"))
                    num_pages = pdf.getNumPages()
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

    def getHelp(self, width: int = 80) -> str:
        """Representation of the help string

        This method uses the information from the implementing class name,
        :class:`__version__`, :class:`__short_description__` and
        :class:`__config_metadict__` to create a proper help. Since it returns
        a string, the implementing class might use it and extend it if required.

        Parameters:
        -----------
        width:
            Wrap text to this width.

        Returns:
        --------
        help_str: str
            A string containing the help.
        """
        help_txt = self.__long_description__.strip()
        if not help_txt:
            help_txt = self.__short_description__
        return "{} (v{}): {}\n{}".format(
            self.__class__.__name__,
            ".".join([str(i) for i in self.__version__]),
            help_txt,
            self.__parameters__.getHelpString(),
        )

    def getCurrentConfig(self, config_dict: config_dict_type = {}) -> str:
        """Retreive the plugin configuration as string representation.

        Parameters:
        -----------
            config_dict:
                the dict containing the current configuration being displayed.
                This info will update the default values.

        Returns:
        --------
        current_conf: str
            The current configuration in a string for displaying.
        """
        max_size = max([len(k) for k in self.__parameters__])

        current_conf = []
        config_dict_resolved = self.setupConfiguration(
            config_dict=config_dict, check_cfg=False
        )
        config_dict_orig = dict(self.__parameters__)
        config_dict_orig.update(config_dict)

        def show_key(key: str) -> str:
            """Format the configuration values.
            This functions formats the configuration depending on whether the
            configuration values contain variables or not.
            """
            if config_dict_resolved[key] == config_dict_orig[key]:
                return config_dict_orig[key]
            else:
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

    def getClassBaseDir(self) -> Optional[str]:
        """Get absolute path to the module defining the plugin class."""
        module_path: Optional[str] = sys.modules[self.__module__].__file__
        subclass_file = os.path.abspath(module_path or "")
        return os.path.join(
            *self._splitPath(subclass_file)[: -len(self.__module__.split("."))]
        )

    def getCurrentUser(self) -> User:
        """Return the user name for which this instance was generated."""
        return self._user

    def _parseConfigStrValue(
        self, param_name: str, str_value: str, fail_on_missing: bool = True
    ) -> Optional[str]:
        """Parse the string in ``str_value`` into the most appropriate value.

        The string *None* will be mapped to the value ``None``.
        On the other hand the quoted word *"None"* will remain as the string
        ``"None"`` without any quotes.

        Parameters:
        -----------
        param_name:
            Parameter name to which the string belongs.
        str_value:
            The string that will be parsed.
        fail_on_missing:
            If the an exception should be risen in case the param_name is not
            found in :class:`__parameters__`

        Returns:
        --------
        str_values: str
            the parsed string, or the string itself if it couldn't be parsed,
            but no exception was thrown.

        Raises:
        -------
        ( :class:`ConfigurationError` ) if parsing couldn't succeed.

        """

        if str_value == "None":
            return None
        elif str_value == '"None"':
            str_value = "None"

        if self.__parameters__ is None or (
            not fail_on_missing and param_name not in self.__parameters__
        ):
            # if there's no dictionary reference or the param_name is not in it
            # and we are not failing
            # just return the str_value
            return str_value

        else:
            return self.__parameters__.get_parameter(param_name).parse(str_value)

    def setupConfiguration(
        self,
        config_dict: config_dict_type = None,
        check_cfg: bool = True,
        recursion: bool = True,
        substitute: bool = True,
    ) -> dict[str, Union[str, int, float, bool, None]]:
        """Defines the configuration required for running this plug-in.

        Basically the default values from :class:`__parameters__` will be
        updated with the values from ``config_dict``.
        There are some special values pointing to user-related managed by the
        system defined in :class:`evaluation_system.model.user.User.getUserVarDict` .

        Parameters:
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

        Returns:
        --------
        results : dict
            a copy of self.self.__config_metadict__ with all defaults values
            plus those provided here.
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

    def readFromConfigParser(self, config_parser: ConfigParser) -> dict[str, str]:
        """Reads a configuration from a config parser object.

        The values are assumed to be in a section named just like the
        class implementing this method.

        config_parser:
            From where the configuration is going to be read.

        Returns:
        --------
        result: dict
            Updated copy of :class:`__config_metadict__`
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
            result[key] = self._parseConfigStrValue(
                key, config_parser.get(section, key)
            )
        return result

    def readConfiguration(self, fp: Iterable[str]) -> dict[str, str]:
        """Read the configuration from a file object using a ConfigParser.

        Parameters:
        -----------
        fp:
            File descriptor pointing to the file where the configuration is stored.

        Returns:
        --------
        result : dcit
            Updated copy of :class:`__config_metadict__`
        """
        config_parser = ConfigParser(interpolation=ExtendedInterpolation())
        config_parser.read_file(fp)
        return self.readFromConfigParser(config_parser)

    def saveConfiguration(
        self,
        fp: Union[TextIO, IO[str]],
        config_dict: config_dict_type = None,
        include_defaults: bool = False,
    ) -> IO[str]:
        """Stores the given configuration to the provided file object.

        If no configuration is provided the default one will be used.

        Parameters:
        ----------
        fp:
            File descriptor pointing to the file where the configuration is stored.
        config_dict:
            a metadict with the configuration to be stored. If none is provided
            the result from :class:`setupConfiguration`
            with ``check_cfg=False`` will be used.
        include_defaults:
            include the default parameters.
        """
        # store the section header
        if config_dict is None:
            # a default incomplete one
            config_dict = self.setupConfiguration(check_cfg=False, substitute=False)
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
                fp.write("%s=%s\n\n" % (param_name, param.str(value)))
                fp.flush()  # in case we want to stream this
        return fp

    def suggest_batchscript_name(self) -> str:
        """
        Return a suggestion for the batch script file name
        :return: file name
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
        config_dict: config_dict_type = {},
        user: Optional[User] = None,
        scheduled_id: Optional[int] = None,
        log_directory: Optional[str] = None,
        unique_output: bool = True,
        extra_options: list[str] = [],
    ) -> tuple[int, str]:
        """Create a job script suitable for the configured workload manager.

        Parameters:
        -----------

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

        Returns:
        --------
        job_id, stdout_file: int, str
            The workload manager job id, the file containing the std out.
        """
        log_directory = log_directory or tempfile.mkdtemp()
        if user is None:
            user = self.getCurrentUser()

        if scheduled_id:
            cmd = self.composeCommand(
                scheduled_id=scheduled_id, unique_output=unique_output
            )
        else:
            cmd = self.composeCommand(
                config_dict=config_dict, unique_output=unique_output
            )

        cfg = config.get_section("scheduler_options").copy()
        cfg["args"] = cmd
        cfg["extra_options"] = extra_options
        cfg["name"] = self.__class__.__name__
        return schedule_job(
            config.get("scheduler_system"),
            Path(config.CONFIG_FILE).parent / "activate_sh",
            cfg,
            delete_job_script=log.root.level <= logging.DEBUG,
            log_directory=log_directory,
        )

    class ExceptionMissingParam(Exception):
        """
        An exception class if a mandatory parameter has not been set
        """

        def __init__(self, param: str):
            """
            Exceptions constructor

            Parameters:
            -----------
            param:
                The missing parameter
            """
            Exception.__init__(self, "Parameter %s has to be set" % param)

    def composeCommand(
        self,
        config_dict: config_dict_type = None,
        scheduled_id: Optional[int] = None,
        batchmode: bool = False,
        email: Optional[str] = None,
        caption: Optional[str] = None,
        unique_output: bool = True,
    ) -> list[str]:
        """Create the plugin command that is submitted."""
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
                config_dict = self.setupConfiguration(check_cfg=False, substitute=False)
            else:
                config_dict = self.setupConfiguration(
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
                    tool_param.append(f"{param_name}={param.str(value)}")
        logging.debug(f"Execute command: {' '.join(tool_param+cmd_param)}")
        return tool_param + cmd_param

    def call(
        self,
        cmd_string: Union[str, list[str]],
        verbose: bool = True,
        return_stdout: bool = True,
        **kwargs,
    ) -> Optional[str]:
        """Simplify the interaction with the shell.

        It calls a bash shell so it's **not** secure.
        It means, **never** start a plug-in comming from unknown sources.

        Parameters:
        -----------
        cmd_string:
            the command to be issued in a string.
        return_stdout:
            return the stdout of the sub-process

        Returns:
        --------
        stdout:
            Stdout of the sub-process if return_stdout was set to true
        """
        log.debug("Calling: %s", cmd_string)
        # if you enter -x to the bash options the validation algorithm
        # after calling SLURM fails. Use -x temporary for debugging only
        if isinstance(cmd_string, str):
            cmd = shlex.split(cmd_string)
        out = ""
        for line in self._execute(cmd):
            if verbose:
                print(line, end="", flush=True)
            out += line
        if return_stdout:
            return out
        return None

    def _splitPath(self, path: str) -> list[str]:
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
