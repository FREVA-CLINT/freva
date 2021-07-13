
__all__ = ['history']

from evaluation_system.commands.history import Command

def history(full_text=False, return_command=False,
            limit=10, plugin=None, since=None, unitl=None,
            entry_ids=None):
    """Get access to the configuration history.

      The `.history` mthod displays the entries with a one-line compact description.
      The first number you see is the entry id, which you might use to select single entries.

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
    if not isinstance(entry_ids, (list, tuple, set)):
        entry_ids = [entry_ids]
    return Command.search_history(full_text=full_text,
                                  return_command=return_command,
                                  limit=limit,
                                  plugin=plugin,
                                  since=sine,
                                  unitl=until,
                                  entry_ids=entry_ids)
