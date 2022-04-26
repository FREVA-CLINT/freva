"""Module to query the database for plugin history entries."""
from __future__ import annotations
import json
from typing import Optional, Union

import evaluation_system.api.plugin_manager as pm
from evaluation_system.misc import logger

__all__ = ["history"]


def history(
    *args: str,
    limit: int = 10,
    plugin: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    entry_ids: Union[int, list[int]] = None,
    full_text: bool = False,
    return_command: bool = False,
    _return_dict: bool = True,
) -> Union[list[str], dict[str, str]]:
    """Get access to the configuration history.

    The `.history` mthod displays the entries with a one-line compact description.
    The first number you see is the entry id, which you might use to select
    single entries.

    Parameters:
    -----------
    full_text: bool, (default False)
      Get the full configuration.
    return_command: bool, (default False)
      Show freva commands belonging to the history entries instead
      of the entries themself.
    limit: int, (default 10)
      Limit the number of entires to be displayed.
    plugin: str, (default None)
      Display only entries from a given plugin name.
    since: str, datetime.datetime, (default None)
      Retrieve entries older than date, see DATE FORMAT.
    until: str, datetime.datetime, (default None)
      Retrieve entries younger than date, see DATE FORMAT.
    entry_ids: list (default None)
       Select entries whose ids are in "ids",
    full_text: bool (default False)
      Show the complete configuration.
    return_command: bool (default False)
      Return the commands instead of history objects
    _return_dict: bool (default True)
      Return a dictionary representation, this is only for internal use
    Returns:
    --------
      list: collection of freva plugin commands

    DATE FORMAT:
    ------------
      Dates can be given in "YYYY-MM-DD HH:mm:ss.n" or any less accurate subset of it.
      These are all valid: "2012-02-01 10:08:32.1233431", "2012-02-01 10:08:32",
      "2012-02-01 10:08", "2012-02-01 10", "2012-02-01", "2012-02", "2012".
      Missing values are assumed to be the minimal allowed value. For example:
      "2012" = "2012-01-01 00:00:00.0"
    """
    if not isinstance(entry_ids, (list, tuple, set)) and entry_ids is not None:
        entry_ids = [entry_ids]
    try:
        command_name = args[0]
    except IndexError:
        command_name = "freva"
    if not return_command:
        logger.info(
            f"history of {plugin}, limit={limit}, since={since},"
            f" until={until}, entry_ids={entry_ids}"
        )
    rows = pm.get_history(
        user=None,
        plugin_name=plugin,
        limit=limit,
        since=since,
        until=until,
        entry_ids=entry_ids,
    )
    if rows:
        # pass some option for generating the command string
        if return_command:
            commands = []
            for row in rows:
                command_options = "plugin"
                cmd = pm.get_command_string_from_row(row, command_name, command_options)
                commands.append(cmd)
            return commands
        else:
            if _return_dict:
                command_dicts = [row.__dict__ for row in rows]
                for nn, cmd_dict in enumerate(command_dicts):
                    for key, value in cmd_dict.items():
                        try:
                            command_dicts[nn][key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                return command_dicts
            else:
                return [row for row in rows]
    else:
        return []