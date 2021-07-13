# encoding: utf-8

"""
history - show history entries

@copyright:  2015 FU Berlin. All rights reserved.

@contact:    sebastian.illing@met.fu-berlin.de
"""

import sys
from evaluation_system.commands import FrevaBaseCommand
import logging as log
import evaluation_system.api.plugin_manager as pm
from evaluation_system.model.db import timestamp_from_string


class Command(FrevaBaseCommand):
 
    _short_args = 'hd'
    _args = [
             {'name': '--debug', 'short': '-d', 'help': 'turn on debugging info and show stack trace on exceptions.',
              'action': 'store_true'},
             {'name': '--help', 'short': '-h', 'help': 'show this help message and exit', 'action': 'store_true'},
             {'name': '--full_text', 'help': 'If present shows the complete configuration stored',
              'action': 'store_true', 'default': False},
             {'name': '--return_command',
              'help': 'Show freva commands belonging to the history entries instead of the entries themself.',
              'action': 'store_true'},
             {'name': '--limit', 'help': 'n is the number of entries to be displayed', 'type': 'int',
              'metavar': 'N', 'default': 10},
             {'name': '--plugin', 'help': 'Display only entries from plugin "name"', 'metavar': 'NAME'},
             {'name': '--since', 'help': 'Retrieve entries older than date (see DATE FORMAT) ', 'metavar': 'DATE'},
             {'name': '--until', 'help': 'Retrieve entries newer than date (see DATE FORMAT)', 'metavar': 'DATE'},
             {'name': '--entry_ids', 'help': 'Select entries whose ids are in "ids" (e.g. entry_ids=1,2 or entry_ids=5)',
              'metavar': 'IDs'},
             ] 

    __short_description__ = '''provides access to the configuration history (use --help for more help)'''
    __description__ = """Displays the last 10 entries with a one-line compact description.
The first number you see is the entry id, which you might use to select single entries.

DATE FORMAT
   Dates can be given in "YYYY-MM-DD HH:mm:ss.n" or any less accurate subset of it.
   These are all valid: "2012-02-01 10:08:32.1233431", "2012-02-01 10:08:32",
   "2012-02-01 10:08", "2012-02-01 10", "2012-02-01", "2012-02", "2012".
   
   Missing values are assumed to be the minimal allowed value. For example:
   "2012" == "2012-01-01 00:00:00.0"
   
   Please note that in the shell you need to escape spaces. 
   All these are valid examples (at least for the bash shell):    
   freva --history --since=2012-10-1\\ 10:35
   freva --history --since=2012-10-1" "10:35'"""

    @staticmethod
    def search_history(*args, **kwargs):

        limit = int(kwargs.pop('limit', 10))
        since = timestamp_from_string(kwargs.pop('since', None))
        until = timestamp_from_string(kwargs.pop('until', None))
        tool_name = kwargs.pop('plugin', None)
        entry_ids = kwargs.pop('entry_ids', None)
        debug = kwargs.pop('debug', False)
        full_text = kwargs.pop('full_text', False)
        command_line = kwargs.pop('command_line', False)
        command_name = args[0]
        try:
            entry_ids = list(map(int, entry_ids.split(',')))
        except AttributeError:
            pass
        return_command = kwargs.pop('return_command', None)
        # this suspresses this debug info for generating commands
        if not return_command:
            log.debug(f'history of {tool_name}, limit={limit}, since={since},'
                      f' until={until}, entry_ids={entry_ids}')
        rows = pm.getHistory(user=None, plugin_name=tool_name,
                             limit=limit, since=since,
                             until=until, entry_ids=entry_ids)
        command_string = []
        if rows:
            # pass some option for generating the command string
            if return_command:
                for row in rows:
                    command_name = sys.argv[0]
                    command_options = '--plugin'
                    if debug:
                        command_options = f"-d {command_options}"
                    cmd = pm.getCommandStringFromRow(row,
                                                     command_name,
                                                     command_options)
                    if len(rows) > 1:
                        cmd += ';'
                    command_string.append(cmd)
            else:
                command_string = [row.__str__(compact=not full_text) for row in rows]
        return command_string

    def _run(self):
        #args = self.args
        kwargs = dict(limit=self.args.limit,
                      since=self.args.since,
                      until=self.args.until,
                      plugin=self.args.plugin,
                      entry_ids=self.args.entry_ids,
                      return_command=self.args.return_command,
                      debug=self.DEBUG,
                      command_line=True,
                      )
        # parse arguments *!!!*
        commands = self.search_history(sys.argv[0], **kwargs)
        if not commands:
            log.error("No results. Check query.")
        for command in commands:
            print(command)

if __name__ == "__main__":
    Command().run()
