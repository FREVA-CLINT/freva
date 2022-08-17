"""
.. moduleauthor:: Sebastian Illing / estani

This module manages the loading and access to all plug-ins. It is designed
as a central registration through which plug-ins can be accessed.

Plug-ins are automatically registered if found either in a specific
directory ``<evaluation_system_root_dir>/tools`` or by using the
environmental variable ``EVALUATION_SYSTEM_PLUGINS``. This variable must
point to modules containing classes which implement
:class:`evaluation_system.api.plugin.PluginAbstract`.

The value stored ``EVALUATION_SYSTEM_PLUGINS`` is a list of ``path,package``
pairs separated by ``:``. The path denotes where the source is to be
found, and the package is the module name with the class that implements
the PluginAbstract interface. For example:

EVALUATION_SYSTEM_PLUGINS=/path/to/some/dir/,something.else.myplugin:\
/other/different/path,some.plugin:\
/tmp/test,some.other.plugin
"""
from __future__ import annotations
import atexit
from contextlib import contextmanager
import importlib.machinery
import importlib.util
import inspect
import json
import os
import random
import re
import signal
import shutil
import string
import sys
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    cast,
    Dict,
    Iterator,
    Optional,
    Sequence,
    TypeVar,
    Union,
)
from typing_extensions import TypedDict

from django.db.models.query import QuerySet
from PIL import Image

from evaluation_system import __version__ as version_api
from evaluation_system.misc import config
from evaluation_system.misc import logger as log
from evaluation_system.misc import utils
from evaluation_system.misc.exceptions import (
    ConfigurationException,
    PluginManagerException,
    ParameterNotFoundError,
)
from evaluation_system.model.history.models import Configuration, History, HistoryTag
from evaluation_system.model.plugins.models import Parameter
from evaluation_system.model.user import User
from .plugin import PluginAbstract

PLUGIN_ENV = "EVALUATION_SYSTEM_PLUGINS"
"""Defines the environmental variable name for pointing to the plug-ins"""

IMAGE_RESIZE_EXCEPTIONS = ["PDF", "HDF5", "GRIB"]
"""Plugin output files of these types will not be resized.

    File type is determined by the file extension and the mapping PIL has in
    `Image.registered_extensions()`.
"""

__plugin_modules_user__: dict[str, dict[str, str]] = {}
"""Plugin module info per user. { user => { module name => filepath } }"""
__plugins_meta_user: dict[str, dict[str, PluginMetadata]] = {}
"""Plugin metadata per user. { user => { plugin name => metadata } } """
__version_cache: dict[str, tuple[str, str]] = {}
"""A dictionary which acts as a cache for the git information to
   reduce hard disk access"""


@dataclass
class PluginMetadata:
    name: str
    plugin_class: str
    plugin_module: str
    description: str
    user_exported: bool
    category: str
    tags: list[str]


@dataclass
class _PluginStateHandle:
    """Provide a handle to set/update the plugin states in the db.

    The handle will be instanciated with a state, a db rowid and a user
    object to identify the user running the plugin. Furthermore os
    termination signal will be captured to be able to set the last state
    of the plugin in the db.

    Parameters
    ----------
    status: int
        Integer representation of the plugin state
    rowid: int
        Unique ID of the plugin
    user: User
        user object holding all user information.
    """

    status: int
    rowid: int
    user: User

    def __post_init__(self):
        """Handle various signals and define what to do on exit of this process."""
        # Make sure the last state of this plugin exist of the process is set
        #
        atexit.register(self._update_plugin_state_in_db)
        # Make sure that the last plugin state gets set during when OS
        # termination signals are sent to this process.
        #
        signal.signal(signal.SIGTERM, self._update_plugin_state_in_db_and_quit)
        signal.signal(signal.SIGHUP, self._update_plugin_state_in_db_and_quit)

    def __enter__(self):

        # Initialize the plugin state the database
        self._update_plugin_state_in_db()
        return self

    def __exit__(self, *args):
        self._update_plugin_state_in_db()

    def _update_plugin_state_in_db(self):
        """Update the state of a plugin in the db."""
        self.user.getUserDB().upgradeStatus(
            self.rowid, self.user.getName(), self.status
        )

    def _update_plugin_state_in_db_and_quit(self, *args):
        """Update the plugin state of a plugin and quit."""
        self._update_plugin_state_in_db()
        print("Recieved termination signal: exiting", file=sys.stderr, flush=True)
        sys.exit(1)


T = TypeVar("T")


def munge(seq: Sequence[T]) -> Iterator[T]:
    """Generator to remove duplicates from a list without changing its order.

    Used to keep sys.path tidy.

    Parameters
    ----------
    seq
        any sequence

    Returns
    -------
    iterator
        a generator returning the same objects in the same sequence but
        skipping duplicates.
    """
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            yield item


def reload_plugins(user_name: Optional[str] = None) -> None:
    """Reload all plug-ins.

    Plug-ins are then loaded first from the :class:`PLUGIN_ENV`
    environmental variable and then from the configuration file. This means
    that the environmental variable has precedence and can therefore
    overwrite existing plug-ins (useful for debugging and testing).

    Parameters
    ----------
    user_name
        freva user to load the plugins for, if none, it will load the current user
    """

    user_name = user_name or User().getName()

    __plugin_modules__: dict[str, str] = {}
    __plugins__ = {}
    __plugins_meta: dict[str, PluginMetadata] = {}
    __plugin_modules_user__[user_name] = {}
    __plugins_meta_user[user_name] = {}
    extra_plugins = []
    if os.environ.get(PLUGIN_ENV):
        # now get all modules loaded from the environment
        for path, module_name in plugin_env_iter(os.environ[PLUGIN_ENV]):
            # extend path to be exact by resolving all
            # "user shortcuts" (e.g. '~' or '$HOME')
            path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
            if os.path.isdir(path):
                # we have a plugin_imp with defined api
                sys.path.append(path)
                # TODO this is not working like in the previous loop. Though we might
                # just want to remove it, as there seem to be no use for this info...
                __plugin_modules__[module_name] = os.path.join(path, module_name)
                extra_plugins.append(module_name)
            else:
                log.warning("Cannot load %s, directory missing: %s", module_name, path)
    # the same for user specific env variable
    if user_name:  # is it possible for User().getName() to be None?
        if PLUGIN_ENV + "_" + user_name in os.environ:
            # now get all modules loaded from the environment
            for path, module_name in plugin_env_iter(
                os.environ[PLUGIN_ENV + "_" + user_name]
            ):
                # extend path to be exact by resolving all
                # "user shortcuts" (e.g. '~' or '$HOME')
                path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
                if os.path.isdir(path):
                    # we have a plugin_imp with defined api
                    sys.path.append(path)
                    # TODO this is not working like in the previous loop. Though we
                    # might just want to remove it, as there seem to be no use for
                    # this info...
                    __plugin_modules__[module_name] = os.path.join(path, module_name)
                    extra_plugins.append(module_name)
                else:
                    log.warning(
                        "Cannot load %s, directory missing: %s", module_name, path
                    )
    # get the tools directory from the current one
    # get all modules from the tool directory
    plugins = list(config.get(config.PLUGINS))
    for plugin_name in plugins:
        try:
            py_dir = config.get_plugin(plugin_name, config.PLUGIN_PYTHON_PATH)
            py_mod = config.get_plugin(plugin_name, config.PLUGIN_MODULE)
        except ConfigurationException:
            log.error(
                f"{config.PLUGIN_PYTHON_PATH} and {config.PLUGIN_MODULE}"
                f" need to be configured for plugin {plugin_name}, check config."
            )
            continue
        if os.path.isdir(py_dir):
            if py_mod in __plugin_modules__:
                file_path = __plugin_modules__[py_mod] + ".py"
                log.warning(
                    "Module '%s' is being overwritten by: %s", py_mod, file_path
                )
            else:
                log.debug("Loading '%s'", plugin_name)
                sys.path.append(py_dir)
                __plugin_modules__[plugin_name] = os.path.join(py_dir, py_mod)
        else:
            log.warning("Cannot load '%s' directory missing: %s", plugin_name, py_dir)

    for plugin_name, plugin_mod in __plugin_modules__.items():

        try:
            loader = importlib.machinery.SourceFileLoader(
                plugin_name, plugin_mod + ".py"
            )
            mod = ModuleType(plugin_name)
            loader.exec_module(mod)
            plugin_class = find_plugin_class(mod)

            # in order to get the properties to resolve to their values
            # instead of give function references, we need to instantiate the class
            instance = plugin_class()

            description_str: str = instance.__short_description__
            category: str = instance.__category__
            tags: list[str] = instance.__tags__
            class_name_str = plugin_class.__name__
        except Exception as e:
            # if this isn't a valid plugin, log a warning but continue
            log.warning(f"Error loading plugin {plugin_name}: {e}")
            continue

        if class_name_str != "" and class_name_str.lower() not in __plugins_meta.keys():
            __plugins_meta[class_name_str.lower()] = PluginMetadata(
                name=class_name_str,
                plugin_class=class_name_str,
                plugin_module=plugin_mod,
                description=description_str,
                user_exported=plugin_name in extra_plugins,
                category=category,
                tags=tags,
            )
            __plugins__[class_name_str] = class_name_str
        elif class_name_str != "":
            log.warning(
                "Default plugin %s is being overwritten by: %s",
                class_name_str,
                __plugins_meta[class_name_str.lower()].plugin_module + ".py",
            )
    sys.path = [p for p in munge(sys.path)]
    __plugin_modules_user__[user_name] = __plugin_modules__
    __plugins_meta_user[user_name] = __plugins_meta


def get_plugins_user() -> dict[str, dict[str, PluginMetadata]]:
    """Get plugins per user

    Returns
    -------
    dict[str, dict[str, PluginMetadata]]
        dictionary holding map of user to plugin data
    """
    return __plugins_meta_user


def get_plugins(user_name: Optional[str] = None) -> dict[str, PluginMetadata]:
    """Get plugins and their metadata for the given user

    It's a dictionary with the ``plugin_name`` in lower case of what
    :class:`get_plugin_dict` returns.  This can be used if the plug-in
    name is unknown.

    Parameters
    ----------
    user_name
        If present, gets plugins for given user. Otherwise gets plugins
        for current user

    Returns
    -------
    dict[str, PluginMetadata]
        dict of plugin name to metadata
    """
    user_name = user_name or User().getName()

    return __plugins_meta_user[user_name]


def get_plugin_metadata(
    plugin_name: str, user_name: Optional[str] = None
) -> PluginMetadata:
    """Return the requested plug-in metadata or raise an exception if not found.

    Parameters
    ----------
    plugin_name
        Name of the plug-in to search for.
    user_name
        If present, looks for the plugin for the given user.
        Otherwise uses current user.

    Returns
    -------
    PluginMetadata
        metadata for the plug-in
    """

    user_name = user_name or User().getName()

    plugin_name = plugin_name.lower()
    if plugin_name not in get_plugins(user_name):
        reload_plugins(user_name)
        if plugin_name not in get_plugins(user_name):
            mesg = "No plugin named: %s" % plugin_name
            similar_words = utils.find_similar_words(
                plugin_name, get_plugins(user_name).keys()
            )
            if similar_words:
                mesg = "%s\n Did you mean this?\n\t%s" % (
                    mesg,
                    "\n\t".join(similar_words),
                )
            raise PluginManagerException(mesg + "\n")
    return get_plugins(user_name)[plugin_name]


def get_plugin_instance(
    plugin_name: str, user: Optional[User] = None
) -> PluginAbstract:
    """Return an instance of the requested plug-in.

    At the current time we are just creating new instances, but this might
    change in the future, so it's *not* guaranteed that the instances are
    *unique*, i.e. they might be re-used and/or shared.

    Parameters
    ----------
    plugin_name
        Name of the plugin to search for.
    user
        User for which this plug-in instance is to be acquired. If not
        given the user running this program will be used.

    Returns
    -------
    PluginAbstract
        An instance of the plug-in. Might not be unique.
    """
    user = user or User()

    # in case we want to cache the creation of the plugin classes.
    plugin = get_plugin_metadata(plugin_name, user.getName())
    spec = importlib.util.spec_from_file_location(
        f"{plugin.plugin_class}", f"{plugin.plugin_module}.py"
    )
    if spec is None:
        raise ImportError(
            f"Could not import {plugin.plugin_class} from {plugin.plugin_module}"
        )
    mod = importlib.util.module_from_spec(spec)
    spec_loader = spec.loader
    if spec_loader is None:
        raise ImportError(
            f"Could not import {plugin.plugin_class} from {plugin.plugin_module}"
        )
    spec_loader.exec_module(mod)
    sys.modules[spec.name] = mod
    return getattr(mod, plugin.plugin_class)(user=user)


def parse_arguments(
    plugin_name: str,
    arguments: list[str],
    use_user_defaults: bool = False,
    user: Optional[User] = None,
    config_file: Optional[str] = None,
    check_errors: bool = True,
) -> dict[str, Any]:
    """Parges arguments to send to a plugin.

    Arguments are sent to an instance of the plugin that will handle the
    parsing. This is why the user is required to be known at this stage.

    Parameters
    ----------
    plugin_name
        Name of the plugin to search for.
    arguments
        it will be parsed by the plug-in (see
        :class:`evaluation_system.api.plugin.parse_arguments`)
    use_user_defaults
        If ``True`` and a user configuration is found, this will be used
        as a default for all non set arguments. So the value will be
        determined according to the first found instance of: argument,
        user default, tool default
    user
        The user for whom this arguments are parsed.
    config_file
        Path to a file from where the setup will read a configuration. If
        None, the default user dependent one will be used. This will be
        completely skipped if ``use_user_defaults`` is ``False``.

    Returns
    -------
    dict[str, Any]
        A dictionary with the parsed configuration.
    """
    plugin_name = plugin_name.lower()
    user = user or User()

    p = get_plugin_instance(plugin_name, user)
    complete_conf = p.__parameters__.parse_arguments(
        arguments, use_defaults=True, check_errors=False
    )
    # if we are using user defaults then load them first
    if use_user_defaults:
        user_config_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(user_config_file):
            with open(user_config_file, "r") as f:
                complete_conf.update(p.read_configuration(f))
    # now if we still have a config file update what the configuration with it
    if isinstance(config_file, str):
        if config_file == "-":
            # reading from stdin
            complete_conf.update(p.read_configuration(sys.stdin))
        elif config_file is not None:
            with open(config_file, "r") as f:
                complete_conf.update(p.read_configuration(f))
    # update with user defaults if desired
    complete_conf.update(
        p.__parameters__.parse_arguments(arguments, check_errors=False)
    )
    # we haven't check for errors because we might have a half implemented
    # configuration some required field might have already been setup
    # (user/system defaults, files, etc)
    # but better if we check them
    if check_errors:
        p.__parameters__.validate_errors(complete_conf, raise_exception=True)
    return complete_conf


def write_setup(
    plugin_name: str,
    config_dict: Optional[Union[PluginMetadata, dict[str, str]]] = None,
    user: Optional[User] = None,
    config_file: Optional[Union[str, Path]] = None,
) -> Union[str, Path]:
    """Writes the plug-in setup to disk.

    This is the configuration for the plug-in itself and not that of the
    tool (which is what normally the plug-in encapsulates). The plug-in
    is not required to write anything to disk when running the tool; it
    might instead configure it from the command line, environmental
    variables or any other method.

    Parameters
    ----------
    plugin_name
        Name of the referred plugin.
    config_dict
        The configuration being stored. If None, the default configuration
        will be stored, this might be incomplete.
    user
        The user for whom this arguments are parsed.
    config_file
        The path to the file where the setup will be stored. If None, the
        default user dependent one will be used. This will be completely
        skipped if ``use_user_defaults`` is ``False``.

    Returns
    -------
    Union[str, Path]
        The path to the configuration file that was written.
    """
    plugin_name = plugin_name.lower()
    user = user or User()
    cfg = cast(Dict[str, Union[str, int, float, bool, None]], config_dict or {})
    p = get_plugin_instance(plugin_name, user)
    complete_conf = p.setup_configuration(
        config_dict=cfg, check_cfg=False, substitute=False
    )

    if config_file is None:
        # make sure the required directory structure and data is in place
        user.prepareDir()

        config_file = user.getUserToolConfig(plugin_name, create=True)

    if config_file == "-":
        p.save_configuration(sys.stdout, config_dict=complete_conf)
    else:
        with open(config_file, "w") as f:
            p.save_configuration(f, config_dict=complete_conf)
    return config_file


def _preview_copy(source_path: str, dest_path: str) -> None:
    """Copy images for preview.

    If the source file is a recognized image file, it will be resized for
    preview, otherwise it will be copied as is with the exception of
    PDFs which are supported by PIL but previously were excluded from
    being resized.

    Parameters
    ----------
    source_path
        the source
    dest_path
        the destination
    """

    extension = Path(source_path).suffix
    supported = Image.registered_extensions()
    if extension in supported and supported[extension] not in IMAGE_RESIZE_EXCEPTIONS:
        _preview_convert(source_path, dest_path)
    else:
        shutil.copyfile(source_path, dest_path)


def _preview_convert(source_path: str, dest_path: str, width: int = 800) -> None:
    """Resizes and converts image

    Resulting image format is based on dest_path file extension

    Parameters
    ----------
    source_path
        the file name of the file to convert
    dest_path
        the file name of the converted file
    width
        width in pixels of resulting image, aspect ratio is maintained
        so height is calculated automatically. Default is 800
    """

    with Image.open(source_path) as img:
        x, y = img.size
        height = 2 * (int(y / (x / width)) // 2)
        im_resize = img.resize((width, height))
        im_resize.save(dest_path)
    os.chmod(dest_path, 509)


def _preview_generate_name(plugin_name: str, metadata: dict[str, Any]) -> str:
    """Creates a filename for plugin output.

    Creates a unique name according to the plugin_name and an eight
    character random string.

    Parameters
    ----------
    plugin_name
        Name of the referred plugin.
    metadata
        The meta-data for the file, to access timestamp

    Returns
    -------
    str
        Generated filename string
    """
    random_suffix = "".join(random.choice(string.ascii_letters) for i in range(8))
    ctime = metadata.get("timestamp", "")
    if ctime:
        time_string = datetime.fromtimestamp(ctime).strftime("%Y%m%d_%H%M%S")
        ctime = "%s_" % time_string
    return plugin_name + "_" + ctime + random_suffix


def _preview_unique_file(plugin_name: str, ext: str, metadata: dict[str, str]) -> str:
    """Creates a unique filename for the preview

    Parameters
    ----------
    plugin_name
        Name of the referred plugin.
    ext
        The extension of the file to be created
    metadata
        the meta-data for the file, to access timestamp
    """
    path = config.get(config.PREVIEW_PATH)
    subdir = datetime.now().strftime("%Y%m%d")
    name = _preview_generate_name(plugin_name, metadata)
    name += ext
    full_path = os.path.join(path, subdir)
    full_name = os.path.join(full_path, name)
    if path.strip() and not os.path.isdir(full_path):
        utils.supermakedirs(full_path, 0o2777)
    return full_name


def _preview_create(plugin_name: str, result: utils.metadict) -> list[str]:
    """Creates the preview.

    Also adds the created files to the result dictionary.

    Parameters
    ----------
    plugin_name
        Name of the referred plugin.
    meta_dict
        A meta dictionary describing the result files

    Returns
    -------
    list[str]
        List of output files
    """
    todo_list = []
    result_list = []
    for file_name in result:
        metadata = result[file_name]
        todo = metadata.get("todo", "")
        if todo == "copy":
            ext = os.path.splitext(file_name)[-1]
            target_name = _preview_unique_file(plugin_name, ext, metadata)
            todo_list.append((_preview_copy, file_name, target_name))
            metadata["preview_path"] = target_name
            result_list.append(target_name)
        elif todo == "convert":
            target_name = _preview_unique_file(plugin_name, ".png", metadata)
            todo_list.append((_preview_convert, file_name, target_name))
            metadata["preview_path"] = target_name
            result_list.append(target_name)
        result[file_name] = metadata
    preview_path = config.get(config.PREVIEW_PATH)
    if preview_path.strip() and todo_list:
        p = Pool(config.NUMBER_OF_PROCESSES)
        p.map(utils.mp_wrap_fn, todo_list)
    return result_list


def run_tool(
    plugin_name: str,
    config_dict: Optional[Union[dict[str, str], utils.metadict]] = None,
    user: Optional[User] = None,
    scheduled_id: Optional[int] = None,
    caption: Optional[str] = None,
    unique_output: bool = True,
) -> Optional[utils.metadict]:
    """Runs a tool and stores the run information.

    Run information is stored in :class:`evaluation_system.model.db.UserDB`.

    Parameters
    ----------
    plugin_name
        Name of the plugin to run.
    config_dict
        The configuration used for running the tool. If is None, the
        default configuration will be stored, this might be incomplete.
    user
        The user starting the tool
    scheduled_id
        If the process is already scheduled then put the row id here
    caption
        The caption to set.

    Returns
    -------
    Optional[utils.metadict]
        Output from the plugin
    """
    plugin_name = plugin_name.lower()
    user = user or User()
    config_dict = config_dict or {}
    p = get_plugin_instance(plugin_name, user)
    complete_conf: dict[str, Union[str, int, float, bool, None]] = {}
    # check whether a scheduled id is given
    if scheduled_id:
        config_dict = cast(
            Dict[str, str],
            load_scheduled_conf(plugin_name, scheduled_id, user),
        )
    if not config_dict:
        conf_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(conf_file):
            log.debug("Loading config file %s", conf_file)
            with open(conf_file, "r") as f:
                complete_conf = cast(
                    Dict[str, Union[str, int, float, bool, None]],
                    p.read_configuration(f),
                )
        else:
            log.debug("No config file was found in %s", conf_file)
    if not complete_conf:
        # at this stage we want to resolve or tokens and perform some kind of sanity
        # check before going further
        cfg = cast(
            Dict[str, Union[str, int, float, bool, None]],
            {k: v for (k, v) in config_dict.items()},
        )
        complete_conf = p.setup_configuration(cfg, recursion=True)
    log.debug("Running %s with %s", plugin_name, complete_conf)
    out_file: Optional[Path] = None
    rowid = 0
    if scheduled_id:
        rowid = scheduled_id
        out_file = Path(History.objects.get(pk=scheduled_id).slurm_output)
    else:
        version_details = get_version(plugin_name)
        rowid = user.getUserDB().storeHistory(
            p,
            complete_conf,
            user.getName(),
            History.processStatus.running,
            version_details=version_details,
            caption=caption,
        )
    with _PluginStateHandle(
        rowid=rowid, status=History.processStatus.running, user=user
    ) as plugin_state:
        if user:
            # follow the notes
            follow_history_tag(rowid, user, "Owner")
        p.rowid = rowid
        # Set last state to broken, before we start the plugin
        # in case something goes wrong it will stay in broken because
        # the PluginStateHandle context manager will set it to the last state
        # regardless (which would be broken).
        plugin_state.status = History.processStatus.broken
        # we want that the rowid to be visible to the tool
        # TODO: not sure if this is really optional, the docs don't say much
        result: Optional[utils.metadict] = p._run_tool(
            config_dict=complete_conf,
            unique_output=unique_output,
            out_file=out_file,
            rowid=rowid,
        )
        # save results when existing
        if result is None:
            plugin_state.status = History.processStatus.finished_no_output
        else:
            # create the preview
            preview_path = config.get(config.PREVIEW_PATH, None)
            if preview_path:
                log.debug("Converting....")
                _preview_create(plugin_name, result)
                log.debug("finished")
            # write the created files to the database
            log.debug("Storing results into data base....")
            user.getUserDB().storeResults(rowid, result)
            log.debug("finished")
            # temporary set all processes to finished
            plugin_state.status = History.processStatus.finished
        return result


def schedule_tool(
    plugin_name: str,
    log_directory: Optional[str] = None,
    config_dict: Optional[dict[str, Optional[Union[str, int, bool, float]]]] = None,
    user: Optional[User] = None,
    caption: Optional[str] = None,
    extra_options: list[str] = [],
    unique_output: bool = True,
) -> tuple[int, str]:
    """Schedules a tool and stores the run information.

    Parameters
    ----------
    plugin_name:
        Name of the plugin to run
    log_directory:
        Directory for the output
    config_dict:
        The configuration used for running the tool. If None, the default
        configuration will be stored, this might be incomplete.
    user:
        The user starting the tool
    scheduled_id:
        If the process is already scheduled then put the row id here
    caption:
        The caption to set.
    extra_options:
        Extra options passed to the workload manager, batchmode only

    Returns:
    -------
    job_id, output_file:
        The slurm job id, path to the std out file.
    """

    plugin_name = plugin_name.lower()
    user = user or User()
    config_dict = config_dict or {}
    p = get_plugin_instance(plugin_name, user)
    complete_conf: dict[str, Union[str, int, float, bool, None]] = {}
    # check whether a scheduled id is given
    if not config_dict:
        conf_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(conf_file):
            log.debug("Loading config file %s", conf_file)
            with open(conf_file, "r") as f:
                complete_conf = cast(
                    Dict[str, Union[str, int, float, bool, None]],
                    p.read_configuration(f),
                )
        else:
            log.debug("No config file was found in %s", conf_file)
    if not complete_conf:
        # at this stage we want to resolve or tokens and perform some kind of sanity
        # check before going further
        conf = cast(Dict[str, Union[str, int, float, bool, None]], config_dict)
        complete_conf = cast(
            Dict[str, Union[str, int, float, bool, None]],
            p.setup_configuration(conf, recursion=True),
        )
    log.debug("Schedule %s with %s", plugin_name, complete_conf)
    version_details = get_version(plugin_name)
    rowid = user.getUserDB().storeHistory(
        p,
        complete_conf,
        user.getName(),
        History.processStatus.not_scheduled,
        version_details=version_details,
        caption=caption,
    )
    # follow the notes
    follow_history_tag(rowid, user, "Owner")
    # set the output directory
    if log_directory is None:
        log_directory = user.getUserSchedulerOutputDir()
        log_directory = os.path.join(log_directory, plugin_name)

    if not os.path.exists(log_directory):
        utils.supermakedirs(log_directory, 0o2777)
    # write the std out file
    p.rowid = rowid
    job_id, output_file = p.submit_job_script(
        config_dict=config_dict,
        scheduled_id=rowid,
        user=user,
        log_directory=log_directory,
        unique_output=unique_output,
        extra_options=extra_options,
    )
    # create a standard slurm file to view with less
    with open(output_file, "w") as the_file:
        if job_id:
            the_file.write(
                f"Your job is pending with id {job_id}.\n"
                f"\nThis file was automatically "
                "created by the evaluation system.\n"
                f"It will be overwritten by the output of {plugin_name}.\n"
            )
        else:
            the_file.write(
                f"The job id for the submission of {plugin_name} "
                "could not be retreived.\n"
            )
    # set the slurm output file
    user.getUserDB().scheduleEntry(rowid, user.getName(), output_file)
    return rowid, output_file


def get_history(
    plugin_name: Optional[str] = None,
    limit: int = -1,
    since: Optional[str] = None,
    until: Optional[str] = None,
    entry_ids: list[int] = None,
    user: Optional[User] = None,
) -> QuerySet[History]:
    """Returns the history from the given user.

    This is just a wrapper for the defined db interface accessed via the
    user object. See :class:`evaluation_system.model.db.UserDB.getHistory`
    for more information on this interface.

    Parameters
    ----------
    plugin_name
        Name of plugin to get the history for
    limit
        Limits on number of results to get. -1 means no limit
    since
        Only get results after since.
    until
        Only get results earlier than until.
    entry_ids
        Result entry IDs to filter for.
    user
        User to get plugins results for.

    Returns
    -------
    QuerySet[History]
        Results from the database query.
    """
    user = user or User()

    if plugin_name is not None:
        plugin_name = plugin_name.lower()

    return user.getUserDB().getHistory(
        plugin_name,
        limit,
        since=since,
        until=until,
        entry_ids=entry_ids,
        uid=user.getName(),
    )


def get_command_string(
    entry_id: int,
    user: Optional[User] = None,
    command_name: str = "freva-plugin",
    command_options: str = "",
) -> str:
    """Return the parameter string of a history entry.

    Parameters
    ----------
    entry_id
        The history id.
    user
        A user to access the database

    Returns
    -------
    str
        Command string to run the plugin again with the same config.
    """
    user = user or User()

    h: QuerySet[History] = user.getUserDB().getHistory(entry_ids=int(entry_id))
    return get_command_string_from_row(h[0], command_name, command_options)


class CommandConfig(TypedDict):
    name: str
    options: str
    tool: str
    args: dict[str, Any]


def get_command_config_from_row(
    history_row: History, command_name: str, command_options: str
) -> CommandConfig:
    """Get the configuration of a plugin command.

    Parameters
    ----------
    history_row
        History to get command config from.
    command_name
        Name of the CLI command
    command_options
        Options for the given CLI command

    Returns
    -------
    CommandConfig
        Configuration of given command
    """

    configuration = history_row.config_dict()
    result: CommandConfig = {
        "name": command_name,
        "options": command_options,
        "tool": history_row.tool,
        "args": {},
    }
    # find lists
    re_list_pattern = r"^\[.*\]$"
    re_list = re.compile(re_list_pattern)
    for k, value in configuration.items():
        if value is not None:
            # remove brackets from list if value is string
            if re_list.match(str(value)) and isinstance(value, str):
                value = value[1:-1]
            result["args"][k] = value
    return result


def get_command_string_from_config(
    config: CommandConfig,
) -> str:
    """Get the command string for a command

    Parameters
    ----------
    config
        Command config to get the string for.

    Returns
    -------
    str
        CLI command string to run this command.
    """
    result: list[str] = [
        cast(str, config.get(a, ""))
        for a in ("name", "options", "tool")
        if config.get(a)
    ]
    for key, value in config["args"].items():
        if isinstance(value, list):
            result.append(f"{key}={','.join(value)}")
        elif isinstance(value, bool):
            result.append(f"{key}={str(value).lower()}")
        else:
            result.append(f"{key}={value}")
    return " ".join(result)


def get_command_string_from_row(
    history_row: History,
    command_name: str = "freva-plugin",
    command_options: str = "",
) -> str:
    """Get the command string for a command

    Parameters
    ----------
    history_row
        Histroy entry to get string for.
    command_name
        Name of the CLI command
    command_options
        Options for the given CLI command

    Returns
    -------
    str
        CLI command string to run this command.
    """
    config = get_command_config_from_row(history_row, command_name, command_options)
    return get_command_string_from_config(config)


def load_scheduled_conf(plugin_name: str, entry_id: int, user: User) -> dict[str, str]:
    """Loads the configuration from a scheduled plug-in.

    Parameters
    ----------
    plugin_name
        Name of plugin
    entry_id
        Plugin run's History entry ID
    user
        User that ran the plugin

    Returns
    -------
    dict[str, Any]
        History entry's config dict
    """
    h = get_history(plugin_name=plugin_name, entry_ids=[entry_id], user=user)
    # only one row should be selected
    row = h[0]
    # scheduled jobs only
    if row.status != History.processStatus.scheduled:
        raise Exception("This is not a scheduled job (status %i)!" % row.status)
    return row.config_dict()


def get_config_name(pluginname: str) -> Optional[str]:
    """Returns the name of a tool as written in the configuration file.

    This is especially useful when accessing the configuration. This
    will get plugins for the current user only.

    Parameters
    ----------
    pluginname
        Name of the plugin to get
    """
    import inspect

    try:
        plugin = get_plugin_metadata(pluginname.lower())
        modulename = inspect.getmodulename(plugin.plugin_module + ".py")
        for name, module in __plugin_modules_user__[User().getName()].items():
            if modulename == inspect.getmodulename(module + ".py"):
                return pluginname
    except Exception as e:
        log.debug(e.__str__())
    return None


def get_error_warning(tool_name: str) -> tuple[str, str]:
    """Returns error and warning messages from the config file.

    Parameters
    ----------
    tool_name
        Name of plugin

    Returns
    -------
    tuple[str, str]
        Tuple of (errors, warnings)
    """
    plugin_name = get_config_name(tool_name)
    error_file = ""
    error_message = ""
    warning_file = ""
    warning_message = ""
    try:
        error_file = config.get_plugin(plugin_name, "error_file", "")
        error_message = config.get_plugin(plugin_name, "error_message", "")
        warning_file = config.get_plugin(plugin_name, "warning_file", "")
        warning_message = config.get_plugin(plugin_name, "warning_message", "")
    except ConfigurationException:
        pass
    if error_file:
        try:
            f = open(error_file, "r")
            error_message = f.read()
            f.close()
        except Exception as e:
            if not error_message:
                log.warning("Could not read error description\n%s" % str(e))
                error_message = ""
    if warning_file:
        try:
            f = open(warning_file, "r")
            warning_message = f.read()
            f.close()
        except Exception as e:
            if not warning_message:
                log.warning("Could not read warning\n%s" % str(e))
                warning_message = ""
    error_message = error_message.strip()
    warning_message = warning_message.strip()
    return error_message, warning_message


def follow_history_tag(history_id: int, user: User, info: str = "") -> None:
    """Add the history tag follow

    Parameters
    ----------
    history_id
        ID of the history object to tag
    user
        User object holding user information
    info
        information to add to the tag
    """
    user_name = user.getName()
    tagType = HistoryTag.tagType.follow
    rows = HistoryTag.objects.filter(
        history_id_id=history_id, type=tagType, uid_id=user_name
    )
    if len(rows) == 0:
        user.getUserDB().addHistoryTag(history_id, tagType, info, uid=user_name)


def unfollow_history_tag(history_id: int, user: User) -> None:
    """Unfollow a history tag.

    Updates all follow history tags to unfollow for the specified history
    entry and user.

    Parameters
    ----------
    history_id
        ID of the history object to unfollow
    user
        User object holding user information
    """
    user_name = user.getName()
    tagType = HistoryTag.tagType.follow
    rows = HistoryTag.objects.filter(
        history_id_id=history_id, type=tagType, uid_id=user_name
    )
    for row in rows:
        user.getUserDB().updateHistoryTag(
            row.id, HistoryTag.tagType.unfollow, uid=user_name
        )


def get_plugin_version(pluginname: str) -> tuple[str, str]:
    """Extracts plugin version from plugin module.

    Parameters
    ----------
    pluginname
        name of the plugin

    Returns
    -------
    tuple[str, str]
        Tuple of (repository URL, git hash)
    """
    from inspect import currentframe, getfile

    import evaluation_system.model.repository as repository

    version = __version_cache.get(pluginname, None)
    if version is None:
        plugin = get_plugins().get(pluginname, None)
        srcfile = ""
        if plugin is not None:
            srcfile = plugin.plugin_module
        elif pluginname == "self":
            # these are both from python's stdlib, the types aren't compatible
            # but it does seem to work
            srcfile = getfile(currentframe())  # type: ignore [arg-type]
        else:
            mesg = "Plugin <%s> not found" % pluginname
            raise PluginManagerException(mesg)
        version = repository.get_version(srcfile)
        __version_cache[pluginname] = version
    return version


def get_version(pluginname: str) -> tuple[int, int, int]:
    """Returns the internal version of a tool (index in datatable)

    If the version is not indexed it will be created.

    Parameters
    ----------
    pluginname
        Name of the plugin

    Returns
    -------
    tuple[int, int, int]
        Tuple of (major, minor, patch) versions
    """
    tool_name = pluginname.lower()
    p = get_plugin_instance(pluginname)
    version = repr(p.__version__)
    (repos_tool, version_tool) = get_plugin_version(pluginname)
    version_id = (
        User()
        .getUserDB()
        .getVersionId(tool_name, version, "", version_api, repos_tool, version_tool)
    )
    if version_id is None:
        version_id = (
            User()
            .getUserDB()
            .newVersion(tool_name, version, "", version_api, repos_tool, version_tool)
        )
    return version_id


def dict2conf(
    toolname: str, conf_dict: dict[str, str], user: Optional[User] = None
) -> list[Configuration]:
    """Get a list of configuration model objects.

    Useful for getting similar results.

    Parameters
    ----------
    conf_dict
        dictionary with configuration to look up

    Returns
    -------
    list[Configuration]
        list of configuration objects
    """
    user = user or User()

    conf = []
    paramstring = []
    tool = get_plugin_instance(toolname, user)
    for key, value in conf_dict.items():
        o = Parameter.objects.filter(tool=toolname, parameter_name=key).order_by("-id")
        if len(o) == 0:
            string = "Parameter <%s> not found" % key
            raise ParameterNotFoundError(string)

        else:
            paramstring = ["%s=%s" % (key, str(value))]
            realvalue = tool.__parameters__.parse_arguments(
                paramstring, check_errors=False
            )[key]
            conf_object = Configuration()
            # Because django adds attributes with suffix `_id`
            # to foreign key attribute and mypy doesn't understand this yet
            # will skip the typ check. Otherwise mypy will complain that we
            # are trying to access an attribute that doesn't exist.
            conf_object.parameter_id_id = o[0].id  # type: ignore
            conf_object.value = json.dumps(realvalue)
            conf.append(conf_object)
    return conf


def plugin_env_iter(envvar: str) -> Iterator[tuple[str, ...]]:
    """Splits the elements of a plugin env string.

    Returns an interator over all elements in a plugin environment
    variable string

    Parameters
    ----------
    envvar
        string to split

    Returns
    -------
    Iterator[tuple[str, ...]]
        Iterator over the (path, package) elements found in the string.
        The type is variable length but this will only ever return
        a 2 element tuple when given a well formed string.
    """
    return map(
        lambda item: tuple([e.strip() for e in item.split(",")]),
        envvar.split(":"),
    )


def find_plugin_class(mod: ModuleType) -> type[PluginAbstract]:
    """Looks for a subclass of PluginAbstract within a module.

    Only returns the first one found if there are multiple.

    Parameters
    ----------
    mod
        module to search for plugin

    Returns
    -------
    type[PluginAbstract]
        The subclass of PluginAbstract found

    Raises
    ------
    PluginManagerException
        Raised when no subclass of PluginAbstract is found
    """
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if inspect.isclass(attr) and attr.__base__ == PluginAbstract:
            return attr
    raise PluginManagerException()


# This only runs once after start. To load new plugins on the fly we have
# 2 possibilities:
# 1) Watch the tool directory
# 2) Use the plugin metaclass trigger (see `evaluation_system.api.plugin`
reload_plugins()
