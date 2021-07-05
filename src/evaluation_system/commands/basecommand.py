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
        self.log = logging.getLogger()
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
            self.log.setLevel(logging.DEBUG)
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
                raise e
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
        if not self.log.handlers:
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
