'''
Created on 21.04.2015

@author: sebastian.illing@met.fu-berlin.de
'''

import abc
import sys
import getopt
from evaluation_system.misc.utils import find_similar_words

import logging

class CommandError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CommandError).__init__(type(self))
        
        self.msg = " %s\nUse --help for getting help" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg
    
class BaseCommand(object):
    __metaclass__ = abc.ABCMeta
    
    DEBUG = False
    
    @abc.abstractproperty
    def _short_args(self):
        '''
        Allowed short arguments. Ie -h or -l as string ("hl")
        '''
        raise NotImplementedError("This attribute must be implemented")
    @abc.abstractproperty
    def _args(self):
        '''
        List of allowed arguments. Ie. ['help','path',...]
        '''
        raise NotImplementedError("This attribute must be implemented")   
    @abc.abstractproperty
    def __short_description__(self):
        raise NotImplementedError("This attribute must be implemented")
    
    @abc.abstractmethod
    def _run(self,*args,**kwargs):
        raise NotImplementedError("This method must be implemented")
    
    def run(self,argv=None,*args,**kwargs):
        if argv is not None:
            args = self.parseArguments(argv)
        else:
            args = self.parseArguments()
        #loop args for help and debug options
        for flag,arg in args:
            if flag in ['-h','--help']:
                self.auto_doc()
            if flag in ['-d','--debug']:
                abort_on_errors=True
                self.DEBUG = True
                logging.getLogger().setLevel(logging.DEBUG)
        print 'now running'        
        try:
            return self._run()
        except KeyboardInterrupt:
            ### handle keyboard interrupt ###
            return 0
        except Exception as e:
            print 'jpjp'
            if isinstance(e, IOError) and e.errno == 32:
                #this is just a broken pipe, which mean the stdout was closed 
                #(e.g when using head after 10 lines are read)
                #just stop normally
                exit(0)
            self.handle_exceptions(e)
            if self.DEBUG:# or __name__ != "__main__":
                raise
            else: print "ERROR: ",sys.exc_info()[1]
            exit(2)
    def parseArguments(self,argv=None,*args,**kwargs):
        if argv is None:
            argv = sys.argv[1:]
        try:
            self.args, self.last_args = getopt.getopt(argv, self._short_args, self._args)
            return self.args
        except getopt.GetoptError as e:
            #Did you mean functionality
            similar_words = None
            if len(e.opt) > 1:
                trimmed_args = []
                for arg in self._args:
                    if arg[-1] == '=': trimmed_args.append(arg[:-1])
                    else: trimmed_args.append(arg)
                similar_words = find_similar_words(e.opt, trimmed_args)
            mesg = e.msg
            if similar_words: mesg = "%s\n Did you mean this?\n\t%s" % (mesg, '\n\t'.join(similar_words))
            print mesg
            exit(2)
        
    def _call(self,cmd_str):
        from subprocess import Popen, PIPE
        return Popen(cmd_str.split(), stdout=PIPE, stderr=PIPE).communicate()
    
    def handle_exceptions(self,e):
        '''Override this method for custom exception handling'''
        pass

    def getEnvironment(self):
        """Parses required variablems from the environment and return a dictionary of them"""
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

    def auto_doc(self,message=None):
        '''
        automatically parses the source code for help options (-h or --help).
        ie. flag == '--path': #helpstring for path option
        will produce a help entry for "path". 
        Additionally the __short_description__ parameter is added to helpstrng
        '''
        import re, os
        _short_args = self._short_args
        _args = self._args
        script_file = sys.argv[0]
        script_name = os.path.basename(script_file)
        #check if in unit tests (runfiles.py is starting the unit test)
        if script_name == 'runfiles.py':
            print "No auto doc for unit test."
            return
        
        re_start = re.compile('.*\*!!!\*$')
        re_end = re.compile('^[ \t]*$')
        re_entries= re.compile("^[^']*'([^']*)'[^']*(?:'([^']*)')?[^#]*#(.*)$")
        parsing=False
        
        args_w_param = ['-%s' % _short_args[i-1] for i in range(len(_short_args)) if _short_args[i] == ':'] + ['--'+ar[:-1] for ar in _args if ar[-1] == '=']
        results = [('-h,--help', 'displays this help or that of the given context.'),
                   ('-d,--debug', 'turn on debugging info')]
        for line in open(script_file, 'r'):
            if parsing:
                items = re_entries.match(line)
                if items:
                    flag, flag_opt, mesg = items.groups()
                    #if multiple flags, all should accept parameters!
                    has_param = flag in args_w_param
                    if flag_opt: flag = '%s, %s' % (flag, flag_opt)
                    if has_param:
                        flag = '%s <value>' % flag
                    results.append((flag, mesg))
                if re_end.match(line): break
            elif re_start.match(line): parsing = True
        #Help must be written as just one line comment, here we wrap it properly
        import textwrap
        env = self.getEnvironment()
        if results:
            max_length = max([len(i[0]) for i in results])
        else: max_length = 0
        wrapper = textwrap.TextWrapper(width=env['columns'], initial_indent='', subsequent_indent=' '*(max_length+5))
        results = [wrapper.fill(('  %-'+str(max_length)+'s: %s') % (flag, mesg)) for flag, mesg in results]
        
        if message: message = ': ' + message
        else: message = ''
        if results: print '%s [opt] query %s\nopt:\n%s' % (script_name, message, '\n'.join(results))
        else: print '%s %s' % (script_name, message)
        
        print '\n'.join([textwrap.fill(r, width = env['columns'], replace_whitespace=False) for r in (self.__short_description__).splitlines()])
        exit(0)
        
