'''
Created on 12.11.2012

@author: estani
'''
import abc
from subprocess import Popen, PIPE, STDOUT
import shlex
import os
import sys
from string import Template

class ConfigurationError(Exception):
    pass

class PluginAbstract(object):
    """This is the base class for all plugins"""
    
    class __metaclass__(abc.ABCMeta):
        """This metaclass encapsulates the abstract class from abc and allows plugin self-registration
        and control. All plugin "classes" inheriting from this class will go through this method
        while being defined"""
        def __init__(self, name, bases, namespace):
            if name != 'PluginAbstract':
                #there's a subclass
                pass
                return abc.ABCMeta.__init__(PluginAbstract, name, bases, namespace)
            return abc.ABCMeta.__init__(abc.ABCMeta, name, bases, namespace)

    @abc.abstractproperty
    def __version__(self):
        """Returns the version of the plugin"""
        raise NotImplementedError("This method must be implemented")

    @abc.abstractproperty
    def __short_description__(self):
        """Returns the version of the plugin"""
        raise NotImplementedError("This method must be implemented")
           
    @abc.abstractmethod
    def getHelp(self):
        """Return some help for the user"""
        raise NotImplementedError("This method must be implemented")

    @abc.abstractmethod
    def setupConfiguration(self, config_dict = None, template = None, check_cfg = True):
        """Define the configuration required for processing this files. If a template was given,
        the return value is a string containing the complete configuration. IF not the config_dict
        will be returned but with all indirections being resolved. Eg:
        dict(a=1, b='1.txt', c='old_1.txt') == setpuConfiguration(config_dict=dict(a=1, b='$a.txt', c='old_$b'))
        
        Parameters
        config_dic : dict, optional
            dictionary with the configuration to be used when generating the configuration file
        template : string.Template, optional
            defines the template for the configuration.
        check_cfg : boolean, optional(True)
            whether the method checks that the resulting configuration dictionary (i.e. the default 
            updated by `config_dict`) has no None values after all substituions are made.
            
        Returns
        template : string
            the substituted configuration string
        """
        
        #accept a maximal recursion of 5 for resolving all tokens
        #5 is a definite number larger than any thinkable recursion for this case
        max_iter = 5
        recursion = True
        while recursion and max_iter > 0:
            recursion = False   #assume no recursion until one possible case is found
            for key, value in config_dict.items():                
                if isinstance(value, basestring) and '$' in value:
                    config_dict[key] = Template(value).safe_substitute(config_dict)
                    recursion = True
            max_iter -= 1
        
        #Allow inheriting class to modify the final configuration before issuing it
        config_dict = self._postTransformCfg(config_dict)
        
        if check_cfg:
            missing =[ k for k, v in config_dict.items() if v is None]
            if missing:
                raise ConfigurationError("These items must be configured: %s" % ', '.join(missing))
        if template:
            return template.substitute(config_dict)
        else:
            return config_dict
    
    def _postTransformCfg(self, config_dict):
        """Allow plugins to give a final check or modification to the configuration before being issued"""
        return config_dict
    
    @abc.abstractmethod
    def runTool(self, config_dict = None):
        """Starts the tool with the given configuration"""
        raise NotImplementedError("This method must be implemented")
    
    def getToolBaseDir(self):
        """Returns the absolute path to the tool subcasting this plugin"""
        subclass_file = sys.modules[self.__module__].__file__
        return os.path.join(*self._splitPath(os.path.abspath(subclass_file))[:-len(self.__module__.split('.'))-1])
    
    def call(self, cmd_string, stdin=None, stdout=PIPE, stderr=STDOUT):
        """Simplify the interaction with the tool.
        Parameters
        cmd_string : string
            the command to be issued in a string
        stdin : string, optional
            a string that will be forwarded in the stdin of the started process
        stdout : file descriptor, optional(PIPE)
            link the standard output of this command call to the given file descriptor. Passing None will shut it up.
        stderr : file descriptor, optional(STDOUT)
            link the standard error of this command call to the given file descriptor. Passing None will shut it up."""
        
        #check if we have any module at all...
        env_file = '%s/etc/setup_bash.env' % self.getToolBaseDir()
        if os.path.isfile(env_file):         
            #This is not much less secure than running the plugins themselves...
            #it spawns a bash shell, sources the environment and issue the given command 
            p = Popen(['/bin/bash', '-c', '. "%s" >/dev/null; %s' % (env_file, cmd_string)], stdout=stdout, stderr=stderr)
        else:
            #but if we don't need a shell, then we don't do it
            cmd = shlex.split(cmd_string)
            p = Popen(cmd, stdout=stdout, stderr=stderr)

        return p.communicate(stdin)
    
    def _splitPath(self, path):
        """Help function to split a path"""
        rest_path = os.path.normpath(path)
        result=[]
        while rest_path:
            old_path = rest_path
            rest_path, path_item = os.path.split(rest_path)
            if old_path == rest_path:
                result.insert(0,rest_path)
                break        
            result.insert(0, path_item)
        return result
