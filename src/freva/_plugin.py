"""Module to get information on and run Freva plgins.

To make use of any of the methods a Freva plugin has to be set up. Either
by you, the Freva admins or your collegues. If you want to create a plugin
pleas refer to the :class:`evaluation_system.api.plugin` section.
"""
from __future__ import annotations
import logging
from pathlib import Path
import json
import textwrap
from typing import Any, Union, List, Optional, NamedTuple, Tuple
import time

import appdirs
import lazy_import
from evaluation_system.misc import logger

django = lazy_import.lazy_module("django")
pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
user = lazy_import.lazy_module("evaluation_system.model.user")
config = lazy_import.lazy_module("evaluation_system.misc.config")
utils = lazy_import.lazy_module("evaluation_system.misc.utils")
PluginNotFoundError = lazy_import.lazy_callable(
    "evaluation_system.misc.exceptions.PluginNotFoundError"
)
ToolPullRequest = lazy_import.lazy_class(
    "evaluation_system.model.plugins.models.ToolPullRequest"
)


CACHE_FILE = Path(appdirs.user_cache_dir()) / "freva" / "plugins.json"

PluginInfo = NamedTuple(
    "PluginInfo",
    [("name", str), ("description", str), ("parameters", List[Tuple[str, str, Any]])],
)

__all__ = ["run_plugin", "list_plugins", "plugin_doc"]


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


def plugin_doc(tool_name: Optional[str]) -> str:
    """Display the documentation of a given plugin.

    Parameters
    ----------
    tool_name:
        The name of the tool that should be documented

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
        print(freva.plugin_doc("animator"))


    """
    tool_name = (tool_name or "").lower()
    _write_plugin_cache()
    _check_if_plugin_exists(tool_name)
    return pm.get_plugin_instance(tool_name).get_help()


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
        print(freva.list_plugins())
    """
    _write_plugin_cache()
    return list([k.lower() for k in pm.get_plugins().keys()])


def get_tools_list() -> str:
    """Get a list of plugins with their short description.

    Returns
    -------
    str:
        String representation of all available plugins.

    :meta private:
    """
    _write_plugin_cache()
    env = utils.get_console_size()
    # we just have to show the list and stop processing
    name_width = 0
    plugins = pm.get_plugins()
    for key in plugins:
        name_width = max(name_width, len(key))
    offset = name_width + 2
    result = []
    for key, plugin in sorted(plugins.items()):
        lines = textwrap.wrap("%s" % plugin.description, env["columns"] - offset)
        if not lines:
            lines = ["No description."]
        if len(lines) > 1:
            # multi-line
            result.append(f"{plugin.name}: {lines[0]}\n{' '*offset}\n{' '*offset}")
        else:
            result.append(f"{plugin.name}: {lines[0]}")
    return "\n".join(result)


def handle_pull_request(
    tag: Optional[str], tool_name: Optional[str]
) -> tuple[int, str]:
    """:meta private:"""
    # TODO: This method should go
    if not tag:
        return 1, 'Missing required option "--tag"'
    # create new entry in
    freva_user = user.User()
    db_user = freva_user.getUserDB().getUserId(freva_user.getName())
    pull_request = ToolPullRequest.objects.create(
        user_id=db_user, tool=tool_name, tagged_version=tag, status="waiting"
    )
    print("Please wait while your pull request is processed.")
    while pull_request.status in ["waiting", "processing"]:
        time.sleep(5)
        pull_request = ToolPullRequest.objects.get(id=pull_request.id)
    if pull_request.status == "failed":
        # TODO: Better error messages, like tag not valid or other
        return 1, "The pull request failed.\nPlease contact the admins."
    else:
        return (
            0,
            (f"{tool_name} plugin is now updated in the system.\nNew version: {tag}"),
        )


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


def _return_value(value: int, result: Any, return_result: bool = True) -> Any:
    if return_result:
        return value, result
    return value, ""


def run_plugin(
    tool_name: str,
    *,
    save: bool = False,
    save_config: Optional[Union[str, Path]] = None,
    show_config: bool = False,
    dry_run: bool = False,
    scheduled_id: Optional[int] = None,
    repo_version: bool = False,
    unique_output: bool = False,
    batchmode: bool = False,
    pull_request: bool = False,
    caption: str = "",
    tag: Optional[str] = None,
    return_result: bool = False,
    **options: dict[str, Union[str, float, int]],
) -> tuple[int, Any]:
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
    show_config:
        Show the resulting configuration (implies dry-run).
    scheduled_id:
        Run a scheduled job from database
    dry_run:
        Perform no computation. Useful for development.
    batchmode:
        Create a Batch job and submit it to the scheduling system.
    unique_output:
        Append a Freva run id to every output folder
    pull_request:
        Issue a new pull request for the tool
    return_result:
        Return the plugin result, this can be useful for pipelining.
    repo_version:
        show the version number from the repository.
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
        freva.run_plugin("animator", variable="pr", project="obs*")

    Run a plugin in the background

    .. execute_code::

        import freva
        freva.run_plugin("animator",
                         variable="pr",
                         project="observations",
                         batchmode=True)

    """
    tool_name = tool_name.lower()
    _check_if_plugin_exists(tool_name)
    if save_config:
        save_config = str(Path(save_config).expanduser().absolute())
    if pull_request:
        return _return_value(*handle_pull_request(tag, tool_name))
    if repo_version:
        (repos, version) = pm.get_plugin_version(tool_name)
        return _return_value(
            0, "Repository and version of " f":{tool_name}\n{repos}\n{version}"
        )
    options_str, tool_dict = [], {}
    for k, v in options.items():
        options_str.append(f"{k}={v}")
    if scheduled_id is None:
        tool_dict = pm.parse_arguments(tool_name, options_str)
    if logger.level == logging.DEBUG:
        tool_dict["debug"] = True
    extra_scheduler_options = tool_dict.pop("extra_scheduler_options", "")
    if caption:
        caption = caption.strip()
    if save_config or save:
        save_in = pm.write_setup(tool_name, tool_dict, config_file=save_config)
        logger.info("Configuration file saved in %s", save_in)
    elif show_config:
        return _return_value(
            0,
            pm.get_plugin_instance(tool_name).get_current_config(config_dict=tool_dict),
        )
    if scheduled_id and not dry_run:
        logger.info(
            "Running %s as scheduled in history with ID %i", tool_name, scheduled_id
        )
        out = pm.run_tool(
            tool_name, scheduled_id=scheduled_id, unique_output=unique_output
        )
        return _return_value(0, out, return_result)
    extra_options: list[str] = [
        opt.strip() for opt in extra_scheduler_options.split(",") if opt.strip()
    ]
    # now run the tool
    (error, warning) = pm.get_error_warning(tool_name)
    if warning:
        logger.warning(warning)
    if error:
        logger.error(error)
    logger.debug("Running %s with configuration: %s", tool_name, tool_dict)
    if not dry_run and not error:
        # we check if the user is external and activate batchmode
        django_user = django.contrib.auth.models.User.objects.get(
            username=user.User().getName()
        )
        if django_user.groups.filter(
            name=config.get("external_group", "noexternalgroupset")
        ).exists():
            batchmode = True
        if batchmode:
            [scheduled_id, job_file] = pm.schedule_tool(
                tool_name,
                config_dict=tool_dict,
                user=user.User(),
                caption=caption,
                extra_options=extra_options,
                unique_output=unique_output,
            )
            logger.info("Scheduled job with history id: %s", scheduled_id)
            logger.info("You can view the job's status with the command squeue")
            logger.info("Your job's progress will be shown with the command")
            logger.info("tail -f %s", job_file)
            return 0, ""
        results = pm.run_tool(
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
    return _return_value(0, results, return_result)
