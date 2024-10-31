"""This module queries the database for plugin history entries."""

from __future__ import annotations

import json
from typing import Any, Optional, Union

import lazy_import
from django.core.exceptions import ImproperlyConfigured
from evaluation_system.misc import logger
from evaluation_system.misc.config import reloadConfiguration

db_settings = lazy_import.lazy_module("evaluation_system.settings.database")
pm = lazy_import.lazy_module("evaluation_system.api.plugin_manager")
from .utils import config

try:
    from evaluation_system.model.user import User
except ImproperlyConfigured:
    reloadConfiguration()
    db_settings.reconfigure_django()


__all__ = ["history"]


def history(
    *args: str,
    limit: int = 10,
    plugin: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    entry_ids: Union[int, list[int], None] = None,
    full_text: bool = False,
    return_results: bool = False,
    return_command: bool = False,
    _return_dict: bool = True,
    user_name: Optional[str] = None,
) -> Union[list[Any], dict[str, Any]]:
    """Get access to the configurations of previously applied freva plugins.

    The `.history` method displays the entries with a one-line compact description.
    The first number you see is the entry id, which you might use to select
    single entries.

    Parameters
    ----------
    limit: int, default: 10
      Limit the number of entries to be displayed.
    plugin: str, default: None
      Display only entries from a given plugin name.
    since: str, datetime.datetime, default: None
      Retrieve entries older than date, see hint on date format below.
    until: str, datetime.datetime, default: None
      Retrieve entries younger than date, see hint on date format below.
    entry_ids: list, default: None
       Select entries whose ids are in "ids".
    full_text: bool, default: False
      Show the complete configuration.
    return_results: bool, default: False
      Also return the plugin results.
    return_command: bool, default: False
      Return the commands instead of history objects.
    user_name: str, default: None
      Select entries belonging to another user (e.g., user_name="<username>")
      or all users (all or *).
    _return_dict: bool, default: True
      Return a dictionary representation, this is only for internal use.

    Returns
    -------
      list:
        freva plugin history

    Example
    -------

    Get the last three history entries:

    .. execute_code::

        import freva
        hist = freva.history(limit=3)
        print(type(hist), len(hist))
        print(hist[-1].keys())
        config = hist[-1]['configuration']
        print(config)


    .. hint:: Date Format
        Dates are given in the ISO-8601 format and can be "YYYY-MM-DDTHH:mm:ss.n"
        or any less accurate subset. These are all valid: "2012-02-01T10:08:32.1233431",
        "2012-02-01T10:08:32", "2012-02-01T10:08", "2012-02-01T10", "2012-02-01",
        "2012-02", "2012". Missing values are assumed to be the minimal allowed value.
        For example: "2012" = "2012-01-01T00:00:00.0"
    """
    if not isinstance(entry_ids, (list, tuple, set)) and entry_ids is not None:
        entry_ids = [entry_ids]
    if not return_command:
        prefix = "history"
        if plugin:
            prefix = "history of {plugin}"
        logger.info(
            f"{prefix}, limit={limit}, since={since},"
            f" until={until}, entry_ids={entry_ids}"
        )

    rows = pm.get_history(
        user=None,
        plugin_name=plugin,
        limit=limit,
        since=since,
        until=until,
        entry_ids=entry_ids,
        user_name=user_name,
    )

    if rows:
        # pass some option for generating the command string
        if return_command:
            commands = []
            for row in rows:
                cmd = pm.get_command_string_from_row(row)
                commands.append(cmd)
            return commands
        if _return_dict:
            command_dicts = []
            for cmd_dict in [row.__dict__ for row in rows]:
                out_dict = {}
                for key, value in cmd_dict.items():
                    try:
                        out_dict[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        if key in ("_state",):
                            continue
                        if key == "timestamp":
                            out_dict[key] = value.isoformat()
                        else:
                            out_dict[key] = value
                if return_results:
                    out_dict["result"] = pm.get_result_output(cmd_dict["id"])
                else:
                    out_dict["result"] = {}
                command_dicts.append(out_dict)
            return command_dicts
        return rows
    return []
