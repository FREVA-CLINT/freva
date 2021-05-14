"""
Created on 21.04.2015

@author: sebastian.illing@met.fu-berlin.de
"""

import abc
import sys
import os
import getopt
from evaluation_system.misc.utils import find_similar_words
from evaluation_system.misc import config
from evaluation_system.model import user
from optparse import OptionParser, BadOptionError

import logging


class CommandError(Exception):
    """
    Generic exception to raise and log different fatal errors.
    """
    def __init__(self, msg):
        super(CommandError).__init__(type(self))
        
        self.msg = " %s\nUse --help for getting help" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):  # pragma nocover
        return self.msg
 

class FrevaParser(OptionParser):

    def get_prog_name(self):
        # TODO: find better way to get second command
        return os.path.basename(sys.argv[0]) + ' ' + sys.argv[1]
    
    def error(self, msg):
        self.print_usage(sys.stderr)
        if 'no such option' in msg:
            raise BadOptionError(msg.replace('no such option: --', ''))
        self.exit(2, "%s: error: %s\n" % (self.get_prog_name(), msg))    

# TODO: I don't really see the point in having a meta class here
class FrevaBaseCommand(metaclass=abc.ABCMeta):
    
    DEBUG = False
    __is_admin = None

    def __init__(self, *args, **kwargs):
        self.set_logger()
    
    @abc.abstractproperty
    def _args(self):  # pragma nocover
        """
        List of allowed arguments. Ie. ['help','path',...]
        """
        raise NotImplementedError("This attribute must be implemented")   
    
    @abc.abstractproperty
    def __short_description__(self):  # pragma nocover
        raise NotImplementedError("This attribute must be implemented")
    
    @abc.abstractmethod
    def _run(self, *args, **kwargs):  # pragma nocover
        raise NotImplementedError("This method must be implemented")
    
    @property
    def is_admin(self):
        if self.__is_admin is None:
            admins = config.get('admins', '')
            # if user.User().getName() in admins.split(','):
            self.__is_admin = user.User().getName() in admins.split(',')
        return self.__is_admin
    
    def run(self, argv=None, *args, **kwargs):
        if argv is not None:
            args = self.parse_arguments(argv)
            self.argv = argv
        else:
            args = self.parse_arguments()
        # loop args for help and debug options
        if self.args.help:
            self.auto_doc()
        if self.args.debug:
            abort_on_errors = True
            self.DEBUG = True
            logging.getLogger().setLevel(logging.DEBUG)
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
            
    def parse_arguments(self, argv=None, *args, **kwargs):
        if argv is None:
            argv = sys.argv[1:]

        try:
            self.parser = FrevaParser(add_help_option=False)
            # add options to parser
            for arg in self._args:
                arg_tmp = arg.copy()
                self.parser.add_option(arg_tmp.pop('short', ''), arg_tmp.pop('name'), **arg_tmp)
            (self.args, self.last_args) = self.parser.parse_args(argv)
            return self.args
        except BadOptionError as e:
            # Did you mean functionality
            similar_words = None
            trimmed_args = []
            for arg in self._args:
                trimmed_args.append(arg['name'][2:])
            similar_words = find_similar_words(e.opt_str, trimmed_args)
            mesg = str(e)
            if similar_words:
                mesg = "%s\n Did you mean this?\n\t%s" % (mesg, '\n\t'.join(similar_words))
            print(mesg)
            exit(2)
        
    def _call(self, cmd_str):
        from subprocess import Popen, PIPE
        return Popen(cmd_str.split(), stdout=PIPE, stderr=PIPE).communicate()
    
    def handle_exceptions(self, e):
        """
        Override this method for custom exception handling"""
        pass

    def getEnvironment(self):
        """Parses required variables from the environment and return a dictionary of them"""
        result = {}
        console_size = self._call('stty size')[0]
        if console_size:
            rows, columns = console_size.strip().split()
            rows, columns = int(rows), int(columns)
        else:
            rows, columns = 25, 80
        
        result['rows'] = rows
        result['columns'] = columns
        return result

    def set_logger(self):
        log = logging.getLogger()
        if not log.handlers:
            class SpecialFormatter(logging.Formatter):
                FORMATS = {logging.DEBUG:"DBG: %(module)s: %(lineno)d: %(message)s",
                           logging.ERROR: "ERROR: %(message)s",
                           logging.INFO: "%(message)s",
                           'DEFAULT': "%(levelname)s: %(message)s"}
            
                def format(self, record):
                    self._fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
                    return logging.Formatter.format(self, record)
                
            hdlr = logging.StreamHandler(sys.stderr)
            hdlr.setFormatter(SpecialFormatter())
            logging.root.addHandler(hdlr)
            logging.root.setLevel(logging.INFO)

    def auto_doc(self, message=None):
        try:
            print(self.__description__+'\n')
        except:
            print(self.__short_description__+'\n')
        self.parser.print_help()
        exit(0)
            

class BaseCommand(metaclass=abc.ABCMeta):  # pragma nocover
    """
    DEPRECATED: User FrevaBaseCommand instead
    """
    
    DEBUG = False
    
    def __init__(self, *args, **kwargs):
        self.set_logger()

    @abc.abstractproperty
    def _short_args(self):
        """
        Allowed short arguments. Ie -h or -l as string ("hl")
        """
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractproperty
    def _args(self):
        """
        List of allowed arguments. Ie. ['help','path',...]
        """
        raise NotImplementedError("This attribute must be implemented")   

    @abc.abstractproperty
    def __short_description__(self):
        raise NotImplementedError("This attribute must be implemented")
    
    @abc.abstractmethod
    def _run(self, *args, **kwargs):
        raise NotImplementedError("This method must be implemented")
    
    def run(self, argv=None, *args, **kwargs):
        
        if argv is not None:
            args = self.parse_arguments(argv)
            self.argv = argv
        else:
            args = self.parse_arguments()
        # loop args for help and debug options
        for flag, arg in args:
            if flag in ['-h', '--help']:
                self.auto_doc()
            if flag in ['-d', '--debug']:
                abort_on_errors = True
                self.DEBUG = True
                logging.getLogger().setLevel(logging.DEBUG)
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

    def parse_arguments(self, argv=None, *args, **kwargs):
        if argv is None:
            argv = sys.argv[1:]
        try:
            self.args, self.last_args = getopt.getopt(argv, self._short_args, self._args)
            return self.args
        except getopt.GetoptError as e:
            # Did you mean functionality
            similar_words = None
            if len(e.opt) > 1:
                trimmed_args = []
                for arg in self._args:
                    if arg[-1] == '=':
                        trimmed_args.append(arg[:-1])
                    else:
                        trimmed_args.append(arg)
                similar_words = find_similar_words(e.opt, trimmed_args)
            mesg = e.msg
            if similar_words:
                mesg = "%s\n Did you mean this?\n\t%s" % (mesg, '\n\t'.join(similar_words))
            print(mesg)
            exit(2)
        
    def _call(self, cmd_str):
        from subprocess import Popen, PIPE
        return Popen(cmd_str.split(), stdout=PIPE, stderr=PIPE).communicate()
    
    def handle_exceptions(self, e):
        """Override this method for custom exception handling"""
        pass

    def getEnvironment(self):
        """Parses required variables from the environment and return a dictionary of them"""
        result = {}
        console_size = self._call('stty size')[0]
        if console_size:
            rows, columns = console_size.strip().split()
            rows, columns = int(rows), int(columns)
        else:
            rows, columns = 25, 80
        
        result['rows'] = rows
        result['columns'] = columns
        return result

    def set_logger(self):
        log = logging.getLogger()
        if not log.handlers:
            class SpecialFormatter(logging.Formatter):
                FORMATS = {logging.DEBUG:"DBG: %(module)s: %(lineno)d: %(message)s",
                           logging.ERROR: "ERROR: %(message)s",
                           logging.INFO: "%(message)s",
                           'DEFAULT': "%(levelname)s: %(message)s"}
            
                def format(self, record):
                    self._fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
                    return logging.Formatter.format(self, record)
                
            hdlr = logging.StreamHandler(sys.stderr)
            hdlr.setFormatter(SpecialFormatter())
            logging.root.addHandler(hdlr)
            logging.root.setLevel(logging.INFO)

    def auto_doc(self, message=None):
        """
        automatically parses the source code for help options (-h or --help).
        ie. flag == '--path': #helpstring for path option
        will produce a help entry for "path". 
        Additionally the __short_description__ parameter is added to helpstrng
        """
        import re, os
        _short_args = self._short_args
        _args = self._args
#        script_file = sys.argv[0]
#        script_name = os.path.basename(script_file)
        import inspect
        script_file = inspect.getfile(self.__class__)
        script_file = script_file.replace('.pyc', '.py')
        script_name = os.path.basename(script_file)
        # check if in unit tests (runfiles.py is starting the unit test)
        if script_name == 'runfiles.py':
            print("No auto doc for unit test.")
            return
        
        re_start = re.compile('.*\*!!!\*$')
        re_end = re.compile('^[ \t]*$')
        re_entries = re.compile("^[^']*'([^']*)'[^']*(?:'([^']*)')?[^#]*#(.*)$")
        parsing = False
        
        args_w_param = ['-%s' % _short_args[i-1] for i in range(len(_short_args)) if _short_args[i] == ':'] + ['--'+ar[:-1] for ar in _args if ar[-1] == '=']
        results = [('-h,--help', 'displays this help or that of the given context.'),
                   ('-d,--debug', 'turn on debugging info')]
        for line in open(script_file, 'r'):
            if parsing:
                items = re_entries.match(line)
                if items:
                    flag, flag_opt, mesg = items.groups()
                    # if multiple flags, all should accept parameters!
                    has_param = flag in args_w_param
                    if flag_opt:
                        flag = '%s, %s' % (flag, flag_opt)
                    if has_param:
                        flag = '%s <value>' % flag
                    results.append((flag, mesg))
                if re_end.match(line):
                    break
            elif re_start.match(line):
                parsing = True
        # Help must be written as just one line comment, here we wrap it properly
        import textwrap
        env = self.getEnvironment()
        if results:
            max_length = max([len(i[0]) for i in results])
        else:
            max_length = 0
        wrapper = textwrap.TextWrapper(width=env['columns'], initial_indent='', subsequent_indent=' '*(max_length+5))
        results = [wrapper.fill(('  %-'+str(max_length)+'s: %s') % (flag, mesg)) for flag, mesg in results]
        
        if message:
            message = ': ' + message
        else:
            message = ''
        if results:
            print('%s [opt] query %s\nopt:\n%s' % (script_name, message, '\n'.join(results)))
        else:
            print('%s %s' % (script_name, message))
        
        if not hasattr(self, '__description__'):
            self.__description__ = self.__short_description__
        
        print('\n'.join([textwrap.fill(r, width=env['columns'], replace_whitespace=False) for r in (self.__description__).splitlines()]))
        exit(0)
