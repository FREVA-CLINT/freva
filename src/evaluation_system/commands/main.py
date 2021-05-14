#!/usr/bin/env python
# encoding: utf-8

import os
import sys
from evaluation_system.commands import FrevaBaseCommand, CommandError
import logging
import textwrap


class Freva(FrevaBaseCommand):

    _command_order = ['plugin', 'history', 'databrowser']
    _args = []
    __short_description__ = '''\nThis is the main tool for the evaluation system.
Usage: freva --COMMAND [OPTIONS]
To get help for the individual commands use
  freva --COMMAND --help
'''

    _commands = None
    _admin_commands = None
    
    def run(self, argv=None, *args, **kwargs):
        """
        We need to override the run method because we don't use the auto_doc and
        parse_arguments function from BaseCommand
        """
        args = self.parse_arguments(argv)
        # loop args for help and debug options
        self.show_help = False
        for flag in args:
            if flag in ['-h', '--help']:
                self.show_help = True
            if flag in ['-d', '--debug']:
                abort_on_errors = True
                self.DEBUG = True
                logging.getLogger().setLevel(logging.DEBUG)
        # show help if no argument is provided
        if len(args) == 0:
            self.show_help = True
        try:
            return self._run()
        except KeyboardInterrupt:
            ### handle keyboard interrupt ###
            return 0
        except Exception as e:
            if isinstance(e, IOError) and e.errno == 32:
                # this is just a broken pipe, which mean the stdout was closed
                # (e.g when using head after 10 lines are read)
                # just stop normally
                exit(0)
            self.handle_exceptions(e)
            if self.DEBUG:  # or __name__ != "__main__":
                raise
            else:
                print("ERROR: ", sys.exc_info()[1])
            exit(2)
    
    def find_commands(self, management_dir):
        """
        Given a path to a management directory, returns a list of all the command
        names that are available.
    
        Returns an empty list if no commands are defined.
        """
        command_dir = os.path.join(management_dir)
        try:
            return [f[:-3] for f in os.listdir(command_dir)
                    if not f.startswith('_') and f.endswith('.py') and 'basecommand' not in f]
        except OSError:
            return []
    
    @property
    def admin_commands(self):
        """
        Property which holds all available commands for administration
        """
        if not self.is_admin:
            return []
        if self._admin_commands is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))     
            self._admin_commands = self.find_commands(
                os.path.join(base_dir, '..', 'src', 'evaluation_system/commands/admin/')
            )
        return self._admin_commands
    
    @property
    def commands(self):
        """
        Property which holds all available commands
        """
        if self._commands is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))     
            self._commands = self.find_commands(os.path.join(base_dir, '..', 'src', 'evaluation_system/commands'))
        return self._commands
    
    def _run(self):
        """
        Loop all arguments and find command to execute
        """
        for flag in self.args:
            if flag.replace('--','') in (self.commands+self.admin_commands):
                f = flag.replace('--','')
                class_ = self._load_command(f)
                argv = sys.argv[:]
                argv.remove(flag)
                return class_().run(argv[1:])
        #if self.show_help:
        self.auto_doc()
    
    def list_commands(self, commands):
        """
        Returns a text wrapper containing all commands including help text
        """
        env = self.getEnvironment()
        results = list()
        for cm in self._reorder_commands(commands):
            results.append((cm, self._load_command(cm).__short_description__))
        if results:
            max_length = max([len(i[0]) for i in results])
        else: 
            max_length = 0
        wrapper = textwrap.TextWrapper(width=env['columns'], initial_indent='', subsequent_indent=' '*(max_length+5))
        return [wrapper.fill(('  --%-'+str(max_length)+'s: %s') % (flag, mesg)) for flag, mesg in results]        
              
    def auto_doc(self, message=None):
        """
        Override FrevaBaseCommands auto_doc.
        We just want to show all available commands
        """
        print('%s \nAvailable commands:\n%s' % ('Freva', '\n'.join(self.list_commands(self.commands))))
        
        if self.is_admin:
            print('\n\nAdministration commands:\n%s' % '\n'.join(self.list_commands(self.admin_commands)))
        env = self.getEnvironment()
        print('\n'.join([textwrap.fill(r, width=env['columns'],
                                       replace_whitespace=False) for r in self.__short_description__.splitlines()]))

    def _reorder_commands(self, command_list):
        """
        If there is a specified command_order. This method rearranges the command list 
        """
        if hasattr(self, '_command_order'):
            cm_order = reversed(self._command_order)
            for cm in cm_order:
                if cm in command_list:
                    command_list.remove(cm)
                    command_list = [cm] + command_list
        return command_list

    def _load_command(self, command):
        """
        Import command from python module
        """
        try:
            module = __import__('evaluation_system.commands.%s' % command, fromlist=['Command'])
        except ImportError as e:
            module = __import__('evaluation_system.commands.admin.%s' % command, fromlist=['Command'])
        except:
            raise

        return getattr(module, 'Command')
    
    def parse_arguments(self, argv=None, *args, **kwargs):
        """
        Custom parse_arguments function. 
        In the end we just remove "freva" don't really parse the rest at all
        """
        if argv is None:
            argv = sys.argv[1:]
        self.args = argv
        return argv

def _run():
    Freva().run()

if __name__ == "__main__":
    _run()
