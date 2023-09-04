"""Module to get information on and run Freva plgins.

To make use of any of the methods a Freva plugin has to be set up. Either
by you, the Freva admins or your collegues. If you want to create a plugin
pleas refer to the :class:`evaluation_system.api.plugin` section.
"""
from __future__ import annotations

import abc
import json
import logging
import textwrap
import time
import warnings
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Literal, NamedTuple, Optional, Tuple, Union

import appdirs
import lazy_import
import rich.layout
import rich.panel
import rich.table

import freva
from evaluation_system.misc import logger

from .utils import PluginStatus, handled_exception, is_jupyter, meta_type

django = lazy_import.lazy_module("django")
pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
user = lazy_import.lazy_module("evaluation_system.model.user")
config = lazy_import.lazy_module("evaluation_system.misc.config")
utils = lazy_import.lazy_module("evaluation_system.misc.utils")
PluginNotFoundError = lazy_import.lazy_callable(
    "evaluation_system.misc.exceptions.PluginNotFoundError"
)


CACHE_FILE = Path(appdirs.user_cache_dir()) / "freva" / "plugins.json"

PluginInfo = NamedTuple(
    "PluginInfo",
    [
        ("name", str),
        ("description", str),
        ("parameters", List[Tuple[str, str, Any]]),
    ],
)

__all__ = ["run_plugin", "list_plugins", "plugin_doc"]


class HelpStr:
    """A helper class that makes the string output prettier."""

    @abc.abstractmethod
    def __str__(self) -> str:
        """String conversion of the class."""

    @abc.abstractmethod
    def __repr__(self) -> str:
        """String representation of the class."""

    @abc.abstractmethod
    def _repr_html_(self) -> str:
        """Jupyter notebook representation of the class."""

    @abc.abstractmethod
    def __rich__(self) -> rich.table.Table:
        """Rich implementation of the class."""


def _write_plugin_cache() -> dict[str, dict[str, Any]]:
    """Write all plugins to a file."""
    out: dict[str, dict[str, Any]] = {}
    for plugin in pm.get_plugins().keys():
        pm_instance = pm.get_plugin_instance(plugin)
        out[plugin] = {}
        out[plugin]["description"] = pm_instance.__short_description__
        out[plugin]["parameters"] = []
        for key, param in pm_instance.__parameters__._params.items():
            if param.mandatory:
                desc = f"{param.help} (mandatory)"
            else:
                desc = f"{param.help} (default: {param.default})"
            out[plugin]["parameters"].append((key, desc, param.default))

    CACHE_FILE.parent.mkdir(exist_ok=True, parents=True)
    with CACHE_FILE.open("w") as f_obj:
        json.dump(out, f_obj)
    return out


@handled_exception
def read_plugin_cache(max_mtime: int = 180) -> list[PluginInfo]:
    """Cache plugin list."""
    CACHE_FILE.parent.mkdir(exist_ok=True, parents=True)
    CACHE_FILE.touch(exist_ok=True)
    plugin_cache = []
    if time.time() - CACHE_FILE.stat().st_mtime > max_mtime:
        cache = _write_plugin_cache()
    else:
        try:
            with CACHE_FILE.open("r") as f_obj:
                cache = json.load(f_obj)
        except:
            cache = _write_plugin_cache()
    if not cache:
        cache = _write_plugin_cache()
    for plugin, plugin_data in cache.items():
        plugin_cache.append(PluginInfo(name=plugin, **plugin_data))
    return plugin_cache


@handled_exception
def plugin_doc(tool_name: Optional[str]) -> HelpStr:
    """Display the documentation of a given plugin.

    Parameters
    ----------
    tool_name:
        The name of the tool that should be documented.

    Returns
    -------
    str:
        plugin help string.

    Raises
    ------
    PluginNotFoundError:
        if the plugin name does not exist.

    Example
    -------

    .. execute_code::

        import freva
        import rich
        rich.print(freva.plugin_doc("animator"))


    """
    tool_name = (tool_name or "").lower()
    _write_plugin_cache()
    _check_if_plugin_exists(tool_name)

    class HelpCls(HelpStr):
        def __init__(self, tool_name: str) -> None:
            self._plugin = pm.get_plugin_instance(tool_name)
            self._help = (
                self._plugin.__long_description__.strip()
                or self._plugin.__short_description__.strip()
            )
            self._version = ".".join([str(i) for i in self._plugin.__version__])
            self._name = self._plugin.__class__.__name__

        def __str__(self) -> str:
            return "{} (v{}): {}\n{}".format(
                self._name,
                self._version,
                self._help,
                self._plugin.__parameters__.get_help(),
            )

        def __repr__(self) -> str:
            return "{} (v{}): {}\n{}".format(
                self._plugin.__class__.__name__,
                self._version,
                self._help,
                self._plugin.__parameters__.get_help(),
            )

        def _repr_html_(self) -> str:
            return "<b>{}</b> (v{}): {}</p>{}".format(
                self._plugin.__class__.__name__,
                self._version,
                self._help.replace("\n", "<br>"),
                self._plugin.__parameters__.get_help(notebook=True),
            )

        def __rich__(self) -> rich.table.Table:
            help_text = rich.table.Text(
                self._help,
                overflow="fold",
                style="normal",
                justify="left",
            )
            title_text = rich.table.Text(
                overflow="fold", style="normal", justify="left"
            )
            title_text.append(
                self._plugin.__class__.__name__,
                style="bold",
            )
            title_text.append(" (")
            title_text.append(f"v{self._version}", style="italic")
            title_text.append("): ")
            title_text += help_text
            table = rich.table.Table(
                highlight=True,
                title=title_text,
                title_style="normal",
            )
            table.add_column("Option")
            table.add_column("Description")
            for key, param in self._plugin.__parameters__._params.items():
                param_str = param.format()
                var_name = key
                if param.mandatory:
                    var_name = f"[red][b]{var_name}[/b][/red]"
                param_desc = rich.table.Text(
                    f"{param.help} (default: {param_str})",
                    overflow="fold",
                )
                table.add_row(var_name, param_desc)
            return table

    return HelpCls(tool_name)


@handled_exception
def list_plugins() -> list[str]:
    """Get the plugins that are available on the system.

    Returns
    --------
    list[str]:
            List of available Freva plugins

    Example
    -------

    .. execute_code::

        import freva
        import rich
        rich.print(freva.list_plugins())
    """
    _write_plugin_cache()
    return list([k.lower() for k in pm.get_plugins().keys()])


@handled_exception
def get_tools_list() -> HelpStr:
    """Get a list of plugins with their short description.

    Returns
    -------
    str:
        String representation of all available plugins.

    Example
    -------

    .. execute_code::

        import freva
        import rich
        rich.print(freva.get_tools_list())

    """
    _write_plugin_cache()

    class HelpCls(HelpStr):
        def __init__(self) -> None:
            env = utils.get_console_size()
            # we just have to show the list and stop processing
            name_width = 0
            self.plugins = pm.get_plugins()
            for key in self.plugins:
                name_width = max(name_width, len(key))
            self.offset = name_width + 2
            self.column_width = env["columns"] - self.offset
            self.result = self.constructor()

        def constructor(self) -> Dict[str, List[str]]:
            """Construct the things that should be displayed."""
            results = {}
            for _, plugin in sorted(self.plugins.items()):
                lines = textwrap.wrap(
                    str(plugin.description),
                    self.column_width,
                )
                if not lines:
                    lines = ["No description."]
                results[str(plugin.name)] = [lines[0]]
                if len(lines) > 1:
                    # multi-line
                    results[str(plugin.name)] += [
                        f"{' '*(len(plugin.name)+2)}{line}" for line in lines[1:]
                    ]
            return results

        def __rich__(self) -> rich.table.Table:
            table = rich.table.Table(highlight=True)
            table.add_column("Tool")
            table.add_column("Description")
            for plugin, desc in self.result.items():
                text = " ".join(" ".join(desc).split())
                table.add_row(plugin, rich.table.Text(text, overflow="fold"))
            return table

        def __str__(self) -> str:
            results = []
            for plugin, desc in self.result.items():
                results.append(f"{plugin}: " + "\n".join(desc))
            return "\n".join(results)

        def __repr__(self) -> str:
            return self.__str__()

        def _repr_html_(self) -> str:
            result = ["<table>"]
            for _, plugin in sorted(self.plugins.items()):
                result.append(
                    (
                        '<tr><td style="text-align: left;"><b>{}</b></td>'
                        '<td style="text-align: left;">{}</td></tr>'
                    ).format(plugin.name, plugin.description or "No description.")
                )
            result.append("</table>")
            return "".join(result)

    return HelpCls()


@handled_exception
def _check_if_plugin_exists(tool_name: Optional[str]) -> None:
    """Check if a given plugin name is part of the plugin stack."""
    if tool_name in pm.get_plugins():
        return
    if not tool_name:
        error = "Available tools are:\n"
        tool_list = "\n".join(list_plugins())
    else:
        tool_list = "\n".join(utils.find_similar_words(tool_name, list_plugins()))
        error = f"{tool_name} plugin not found, did you mean:\n"
    raise PluginNotFoundError(f"\n{error}{tool_list}")


def _get_tool_dict(
    tool_name: str, **options: Union[str, float, int, bool]
) -> Dict[str, Any]:
    options_str, tool_dict = [], {}
    for k, v in options.items():
        options_str.append(f"{k}={v}")
    tool_dict = pm.parse_arguments(tool_name, options_str)
    if logger.level == logging.DEBUG:
        tool_dict["debug"] = True
    return tool_dict


@handled_exception
def plugin_info(
    tool_name: str,
    what: Literal["repository", "config"] = "repository",
    **options: Union[str, float, int, bool],
) -> str:
    """Get additional information on a specific plugin.

    This is a utility function that lets you inspect additional information
    of a specific plugin. You can either get information on the plugin
    repository or get the current plugin configuration if you want to save
    the configuration to a file and use this file instead of calling the
    :py:meth:`freva.run_plugin` with the same options all over again.

    Parameters
    ----------
    tool_name: str
        The name of the plugin.
    what: str, default: repo_version
        What information should be returned. This can either be ``repo_version``
        for getting information on the tool repository or ``config`` for
        creating a string representing the current tool configuration that
        can then be saved to a file.
    **options:
        Parameters that should be passed to the tool.

    Returns
    -------
    str: The information that was requested.


    Example
    -------

    Get the repository and the last commit hash of a specific plugin:

    .. execute_code::

        import freva
        print(freva.plugin_info("animator", "repository"))

    Get the configuration for a plugin so it can be saved to a config file.

    .. execute_code::

        from tempfile import NamedTemporaryFile
        import freva
        config = freva.plugin_info("animator", what="config", variabel="pr")
        print(config)
        with NamedTemporaryFile(suffix=".conf") as tf:
            with open(tf.name, "w") as f_obj:
                f_obj.write(config)

    """
    choices = ("repository", "config")
    if what not in choices:
        raise ValueError(f"what argument must be one of {', '.join(choices)}")
    if what == "repository":
        (repos, version) = pm.get_plugin_version(tool_name)
        return f"Repository and version of :{tool_name}\n{repos}\n{version}"
    tool_dict = _get_tool_dict(tool_name, **options)
    with NamedTemporaryFile() as tf:
        pm.write_setup(tool_name, tool_dict, config_file=tf.name)
        return Path(tf.name).read_text()


@handled_exception
def run_plugin(
    tool_name: str,
    *,
    save: bool = False,
    save_config: Optional[Union[str, Path]] = None,
    show_config: bool = False,
    scheduled_id: Optional[int] = None,
    unique_output: bool = True,
    batchmode: bool = False,
    caption: str = "",
    tag: Optional[str] = None,
    **options: Union[str, float, int, bool],
) -> PluginStatus:
    """Apply an available data analysis plugin.

    Parameters
    ----------
    tool_name:
        The name of the plugin that is to be applied.
    caption:
        Set a caption for the results.
    save:
        Save the plugin configuration to default destination.
    save_config:
        Save the plugin configuration.
    scheduled_id:
        Run a scheduled job from database
    batchmode:
        Create a Batch job and submit it to the scheduling system.
    unique_output:
        Append a Freva run id to the output/cache folder(s).
    tag:
       Use git commit hash to specify a specific versrion of this tool.

    Returns
    -------
    tuple:
        Return code, and the return value of the plugin


    Example
    -------

    Run a plugin in the foreground.

    .. execute_code::

        import freva
        res = freva.run_plugin("animator", variable="pr", project="obs*")
        output = res.get_result_paths("plot", "*.*") # Check the plot output

    Run a plugin in the background. You can interact with the plugin using
    the ``.wait`` method of the :py:class:``freva.PluginStatus`` class.

    .. execute_code::

        import freva
        res = freva.run_plugin("animator",
                               variable="pr",
                               project="observations",
                               batchmode=True)
        res.wait() # Wait until the plugin has finished

    """
    tool_name = tool_name.lower()
    _check_if_plugin_exists(tool_name)
    if save_config:
        save_config = str(Path(save_config).expanduser().absolute())
    tool_dict: Dict[str, Any] = {}
    if scheduled_id is None:
        tool_dict = _get_tool_dict(tool_name, **options)
    if logger.level == logging.DEBUG:
        tool_dict["debug"] = True
    extra_scheduler_options = tool_dict.pop("extra_scheduler_options", "")
    if caption:
        caption = caption.strip()
    if save_config or save:
        save_in = pm.write_setup(tool_name, tool_dict, config_file=save_config)
        logger.info("Configuration file saved in %s", save_in)
    if scheduled_id:
        logger.info(
            "Running %s as scheduled in history with ID %i",
            tool_name,
            scheduled_id,
        )
        tool_id, result = pm.run_tool(
            tool_name, scheduled_id=scheduled_id, unique_output=unique_output
        )
        return PluginStatus(tool_id)
    extra_options: list[str] = [
        opt.strip() for opt in extra_scheduler_options.split(",") if opt.strip()
    ]
    # now run the tool
    result, tool_id = None, -1
    (error, warning) = pm.get_error_warning(tool_name)
    if warning:
        logger.warning(warning)
    if error:
        logger.error(error)
    logger.debug("Running %s with configuration: %s", tool_name, tool_dict)
    if not error:
        # we check if the user is external and activate batchmode
        django_user = django.contrib.auth.models.User.objects.get(
            username=user.User().getName()
        )
        if django_user.groups.filter(
            name=config.get("external_group", "noexternalgroupset")
        ).exists():
            batchmode = True
        if batchmode:
            if freva.config.db_reloaded[0]:
                raise ValueError(
                    "batchmode and overriding the config is not implemented"
                )
            [scheduled_id, job_file] = pm.schedule_tool(
                tool_name,
                config_dict=tool_dict,
                user=user.User(),
                caption=caption,
                extra_options=extra_options,
                unique_output=unique_output,
            )
            print(f"Scheduled job with history id: {scheduled_id}")
            print("You can view the job's status with the command squeue")
            print("Your job's progress will be shown with the command")
            print(f"tail -f {job_file}")
            return PluginStatus(scheduled_id or 0)
        if freva.config.db_reloaded[0]:
            warnings.warn(
                "History will not be available in currently active system but"
                " in previously active system.",
                UserWarning,
            )
        tool_id, result = pm.run_tool(
            tool_name,
            config_dict=tool_dict,
            caption=caption,
            unique_output=unique_output,
        )

        # repeat the warning at the end of the run
        # for readability don't show the warning in debug mode
        if warning:
            logger.warning(warning)
    logger.debug("Arguments: %s", options)
    logger.debug("Current configuration:\n%s", json.dumps(tool_dict, indent=4))
    return PluginStatus(tool_id)
