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

class metadict(dict):
    def __init__(self, compact_creation=False, *args, **kw):
        self.metainfo = {}
        if compact_creation:
            #separate the special "value" in the first field from the dictionary in the second
            super(metadict,self).__init__()
            for key, values in kw.items():
                if isinstance(values, tuple):
                    self[key] = values[0]
                    self.metainfo[key] = values[1]
                else:
                    self[key] = values
        else:
            super(metadict,self).__init__(*args, **kw)
        
        
    def getMetadata(self, key):
        if key in self.metainfo: return self.metainfo[key]
        else: return None
        
    def setMetadata(self, key, meta_dict):
        if key not in self: raise KeyError(key)
        if key not in self.metainfo: self.metainfo[key] = {}
        self.metainfo[key].update(meta_dict)
    
    def clearMetadata(self, key):
        if key not in self: raise KeyError(key)
        if key in self.metainfo: del self.metainfo[key]

class PluginAbstract(object):
    """This is the base class for all plugins"""
    
    class __metaclass__(abc.ABCMeta):
        """This metaclass encapsulates the abstract class from abc and allows plugin self-registration
        and control. All plugin "classes" inheriting from this class will go through this method
        while being defined"""
        def __init__(self, name, bases, namespace):
            if name != 'PluginAbstract':
                #This is a new subclass. We may register it on the fly now.
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
    
    def __to_bool(self, bool_str):
        """Parses a string for a boolean value"""
        if isinstance(bool_str, basestring) and bool_str: 
            if bool_str.lower() in ['true', 't', '1']: return True
            elif bool_str.lower() in ['false', 'f', '0']: return False
            
        #if here we couldn't parse it
        raise ValueError("'%s' is no recognized as a boolean value" % bool_str)
        
    @abc.abstractmethod
    def parseArguments(self, opt_arr, default_cfg_metadict={}):
        """Parse an array of strings and return a configuration dictionary.
        The strings are of the type: ['key1=val1', 'key2']
        Throw a configuration error if the attributes are not expected."""
        config = {}
        
        for option in opt_arr:            
            parts = option.split('=')
            if len(parts) == 1:
                key, value = parts[0], 'true'
            else:
                key = parts[0]
                #just in case there were multiple '=' characters
                value = '='.join(parts[1:])
            
            if key in default_cfg_metadict:
                meta = default_cfg_metadict.getMetadata(key)
                if meta and 'type' in meta: key_type = meta['type']
                else: key_type = type(default_cfg_metadict[key])
                try:
                    if key_type is type(None):
                        raise ConfigurationError("Internal error at the API. Default arguments type missing.")
                    config[key] = {
                                int : int,
                                bool : self.__to_bool,
                                float: float,
                                str: lambda s: s,
                                }[key_type](value)
                except ValueError:
                    raise ConfigurationError("Can't parse value %s for option %s. Expected type: %s" % (value, key, key_type.__name__))
            else:
                raise ConfigurationError("Unknown parameter %s" % key)
        return config
        
    
    @abc.abstractmethod
    def setupConfiguration(self, config_dict = None, template = None, check_cfg = True):
        """Define the configuration required for processing this files. If a template was given,
        the return value is a string containing the complete configuration. If not the config_dict
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
