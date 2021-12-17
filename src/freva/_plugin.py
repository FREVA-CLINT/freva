import logging
from pathlib import Path
import json
import textwrap
from typing import Any, Union, Dict, Optional, Tuple
import time


from django.contrib.auth.models import User
import evaluation_system.api.plugin_manager as pm
from evaluation_system.model import user
from evaluation_system.misc import config, utils, logger
from evaluation_system.misc.exceptions import PluginNotFoundError
from evaluation_system.model.plugins.models import ToolPullRequest


__all__ = ["run_plugin", "list_plugins", "plugin_doc"]


def plugin_doc(tool_name: Optional[str]) -> str:
    """Display the documentation of a given plugin."""
    _check_if_plugin_exists(tool_name or "")
    return pm.getPluginInstance(tool_name).getHelp()


def list_plugins() -> Tuple[str]:
    """Get the plugins that are available on the system."""
    return tuple(pm.getPlugins().keys())


def get_tools_list() -> str:
    """Get a list of plugins with thier describtion."""
    env = utils.get_console_size()
    # we just have to show the list and stop processing
    name_width = 0
    plugins = pm.getPlugins()
    for key in plugins:
        name_width = max(name_width, len(key))
    offset = name_width + 2
    result = []
    for key, plugin in sorted(plugins.items()):
        lines = textwrap.wrap("%s" % plugin["description"], env["columns"] - offset)
        if not lines:
            lines = ["No description."]
        if len(lines) > 1:
            # multi-line
            result.append(f"{plugin['name']}: {lines[0]}\n{' '*offset}\n{' '*offset}")
        else:
            result.append(f"{plugin['name']}: {lines[0]}")
        return "\n".join(result)


def handle_pull_request(tag, tool_name):
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
        return 0, (
            f"{tool_name} plugin is now updated in the system." f"\nNew version: {tag}"
        )


def _check_if_plugin_exists(tool_name: str) -> None:
    """Check if a given plugin name is part of the plugin stack."""
    if tool_name in pm.getPlugins():
        return
    error = f"{tool_name} Plugin not found, "
    similar_tools = utils.find_similar_words(tool_name, list_plugins())
    if similar_tools:
        error += "did you mean this:\n" + "\n".join(similar_tools)
    else:
        error += "available tools:\n" + "\n".join(list_plugins())
    raise PluginNotFoundError(f"\n{error}")


def _return_value(value: int, result: Any, return_result: bool = True) -> Any:
    if return_result:
        return value, result
    return value, ""


def run_plugin(
    tool_name: Optional[str] = None,
    *,
    save: bool = False,
    save_config: Optional[Union[str, Path]] = None,
    show_config: bool = False,
    dry_run: bool = False,
    scheduled_id: bool = False,
    repo_version: bool = False,
    unique_output: bool = False,
    batchmode: bool = False,
    pull_request: bool = False,
    caption: str = "",
    tag: bool = False,
    return_result: bool = False,
    **options: Dict[str, Union[str, float, int]],
) -> Tuple[int, Any]:
    """Apply an available data analysis plugin.

    Parameters:
    ===========
    tool_name:
        The name of the plugin that is to be applied.
    repo_version:
        show the version number from the repository.
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
        Append a freva run id to every output folder
    pull_request:
        Issue a new pull request for the tool
    return_result:
        Return the plugin result, this can be useful for pipelining.
    tag:
       Use git commit hash

    Returns:
    ========

    """
    if save_config:
        save_config = str(Path(save_config).expanduser().absolute())
    tools = ""
    results = ""
    _check_if_plugin_exists(tool_name or "")
    if pull_request:
        return _return_value(*handle_pull_request(tag, tool_name))
    if repo_version:
        (repos, version) = pm.getPluginVersion(tool_name)
        return _return_value(
            0, "Repository and version of " f":{tool_name}\n{repos}\n{version}"
        )
    email = None
    tool_dict = []
    for k, v in options.items():
        tool_dict.append(f"{k}={v}")
    tool_dict = pm.parseArguments(tool_name, tool_dict)
    if logger.level == logging.DEBUG:
        tool_dict["debug"] = True
    if caption:
        caption = pm.generateCaption(caption, tool_name)
    if save_config or save:
        save_in = pm.writeSetup(tool_name, tool_dict, config_file=save_config)
        logger.info("Configuration file saved in %s", save_in)
    elif show_config:
        return _return_value(
            0, pm.getPluginInstance(tool_name).getCurrentConfig(config_dict=tool_dict)
        )
    if scheduled_id and not dry_run:
        logger.info(
            "Running %s as scheduled in history with ID %i", tool_name, scheduled_id
        )
        out = pm.runTool(
            tool_name, scheduled_id=scheduled_id, unique_output=unique_output
        )
        return _return_value(0, out, return_result)
    # now run the tool
    (error, warning) = pm.getErrorWarning(tool_name)
    if warning:
        logger.warning(warning)
    if error:
        logger.error(error)
    logger.debug("Running %s with configuration: %s", tool_name, tool_dict)
    if not dry_run and (not error or debug):
        # we check if the user is external and activate batchmode
        django_user = User.objects.get(username=user.User().getName())
        if django_user.groups.filter(
            name=config.get("external_group", "noexternalgroupset")
        ).exists():
            batchmode = True
        if batchmode:
            [id, file] = pm.scheduleTool(
                tool_name,
                config_dict=tool_dict,
                user=user.User(email=email),
                caption=caption,
                unique_output=unique_output,
            )
            logger.info(f"Scheduled job with history id: {id}")
            logger.info("You can view the job's status with the command squeue")
            logger.info("Your job's progress will be shown with the command")
            logger.info(f"tail -f {file}")
            return 0, ""
        results = pm.runTool(
            tool_name,
            config_dict=tool_dict,
            caption=caption,
            unique_output=unique_output,
        )
        # repeat the warning at the end of the run
        # for readability don't show the warning in debug mode
        if logger.level > logging.DEBUG:
            logger.warning(warning)
    logger.debug("Arguments: %s", options)
    logger.debug("Current configuration:\n%s", json.dumps(tool_dict, indent=4))
    return _return_value(0, results, return_result)
