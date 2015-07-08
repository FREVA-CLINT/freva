# encoding: utf-8

'''
history - show history entries

@copyright:  2015 FU Berlin. All rights reserved.
        
@contact:    sebastian.illing@met.fu-berlin.de
'''

import sys, os, time
from evaluation_system.commands import FrevaBaseCommand, CommandError
import logging as log
from evaluation_system.model.esgf import P2P
import evaluation_system.api.plugin_manager as pm
from evaluation_system.model.db import HistoryEntry

class Command(FrevaBaseCommand):
 
    _short_args = 'hd'
#    _args = ['results','repos-version', 'full_text', 'return_command',
#             'limit=', 'tool=', 'since', 'until', 'entry_id', 'debug', 'help']
#    _args = ['help','debug']
    
    _args = [
             {'name':'--debug','short':'-d','help':'turn on debugging info and show stack trace on exceptions.','action':'store_true'},
             {'name':'--help','short':'-h', 'help':'show this help message and exit','action':'store_true'},
             {'name':'--full_text','help':'If present shows the complete configuration stored', 'action':'store_true', 'default': False},
             {'name':'--return_command','help':'Show freva commands belonging to the history entries instead of the entries themself.', 'action':'store_true'},
             {'name':'--limit','help':'n is the number of entries to be displayed','type':'int', 'metavar':'N', 'default':10},
             {'name':'--plugin','help':'Display only entries from plugin "name"', 'metavar':'NAME'},
             {'name':'--since','help':'Retrieve entries older than date (see DATE FORMAT) ', 'metavar':'DATE'},
             {'name':'--until','help':'Retrieve entries newer than date (see DATE FORMAT)', 'metavar':'DATE'},
             {'name':'--entry_ids','help':'Select entries whose ids are in "ids" (e.g. entry_ids=1,2 or entry_ids=5)', 'metavar':'IDs'},
             ] 

    __short_description__ = '''provides access to the configuration history (use --help for more help)'''
    __description__ = """Displays the last 10 entries with a one-line compact description.
The first number you see is the entry id, which you might use to select single entries.

DATE FORMAT
   Dates can be given in "YYYY-MM-DD HH:mm:ss.n" or any less accurate subset of it.
   These are all valid: "2012-02-01 10:08:32.1233431", "2012-02-01 10:08:32",
   "2012-02-01 10:08", "2012-02-01 10", "2012-02-01", "2012-02", "2012".
   
   These are *NOT*: "01/01/2010", "10:34", "2012-20-01"
   
   Missing values are assumed to be the minimal allowed value. For example:
   "2012" == "2012-01-01 00:00:00.0"
   
   Please note that in the shell you need to escape spaces. 
   All these are valid examples (at least for the bash shell):    
   freva --history --since=2012-10-1\ 10:35
   freva --history --since=2012-10-1" "10:35'"""
    
    def _run(self):
        args = self.args
        limit = args.limit
        since = HistoryEntry.timestampFromString(args.since) if args.since  else None
        until = HistoryEntry.timestampFromString(args.until) if args.until  else None
        tool_name=args.plugin
        entry_ids=map(int,args.entry_ids.split(',')) if args.entry_ids else None
        store_file=False
        return_command = args.return_command
        #parse arguments *!!!*
        for args in self.last_args:
            tmp = args.split('=')
            flag = tmp[0]
            arg = '='.join(tmp[1:]) if len(tmp) > 1 else None
                
        # this suspresses this debug info for generating commands
        if not args.return_command:
            log.debug('history of %s, limit=%s, since=%s, until=%s, entry_ids=%s',tool_name,limit, since, until, entry_ids)
        rows = pm.getHistory(user=None, plugin_name=tool_name, limit=limit, since=since, until=until, entry_ids=entry_ids)
        if rows:
            if store_file:                
                if len(rows) > 1:
                    raise AnalyzeError("Can only store one configuration at a time. We got %s back.\n" % len(rows) +
                                       "Trim your search and try again (better if you use entry_ids with a single id).")
                
                entry = rows[0]
                tool = pm.getPluginInstance(entry.tool_name)
                saved_in = pm.writeSetup(entry.tool_name, entry.configuration, config_file=store_file)
                log.info("Configuration stored in %s",  saved_in)
            else:
                # pass some option for generating the command string
                if return_command:
                    for row in rows:
                        command_name = sys.argv[0]
                        command_options = '--plugin'
                        
#                        if batchmode:
#                            command_options = "--batchmode true %s" % command_options
                        if self.DEBUG:
                            command_options = "-d %s" % command_options
                            
                        command_string = pm.getCommandStringFromRow(row, command_name, command_options)
                        
                        if len(rows) > 1:
                            print command_string + ';'
                            
                        else:
                            print command_string
                else:
                    print '\n'.join([row.__str__(compact=not args.full_text) for row in rows])
        else:
            log.error("No results. Check query.")

if __name__ == "__main__":
    Command().run()