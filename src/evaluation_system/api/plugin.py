'''
Created on 12.11.2012

@author: estani

In this file the only abstract class required for running a plugin is defined.
You'll need to implement the few attributes and/or methods marked as abstract with the decorator
@abc.abstractproperty or @abc.abstractmethod

You may overwrite all methods and properties defined in here, but you'll be breaking the contract
between the methods so you'll have to make sure it doesn't break anything else. Please write some tests
for your own class that checks it is working as expected.

If you are implementing the plugin for the evaluation_system a further constraint is required:
The class must be defined in the <plugin_name>.api module so it can be loaded dynamically.

This is an example on how you could write a Plugin that works both detached from the evaluation_system
as well as it integrates seamlessly.

The plugin module should be load dynamically depending on the context (i.e. if the evaluation_system is
present or not). This can be done with the following lines of code:

<pre>
#if the evaluation system module wasn't loaded load the interface.
#(if not, the interface is already loaded)
from sys import modules
if 'evaluation_system.api.plugin' not in modules:
    #if we don't have the framework around, we'll use the plugin provided here.
    from pca import plugin
else:
    #else just get the reference to the same module as defined in the framework 
    plugin = modules['evaluation_system.api.plugin']
</pre>

Now this is the minimal implementation at this time. (If I forgot to update it and there are more
methods/attributes required, you'll see a proper message telling you that when you try to cast an
instance of this class)
 
<pre>
class MyPlugin(plugin.PluginAbstract):
    "MyPlguin description for the developers"
    __short_description__ = "A Short description for the user."
    __version__ = (0,0,1)
    __config_metadict__ =  metadict(compact_creation=True, 
                                    number=(None, dict(type=int,help='This is an optional configurable int variable named number without default value and this description')),
                                    the_number=(None, dict(type=float,mandatory=True,help='A required float value without default')), 
                                    something='test', #a simple optional test value with default value and no description 
                                    other=1.4)        #another float value. You cannot define a value without a default value and no metadata 'type' attribute defining how to parse it from a string.

    def runTool(self, config_dict=None):
        pass    #make sure the plugin does what it needs with the configuration passed in the config_dict dictionary.
        

'''
import abc
from subprocess import Popen, PIPE, STDOUT
import os
import sys
from string import Template
from ConfigParser import SafeConfigParser
from copy import deepcopy
import logging
log = logging.getLogger(__name__)

from evaluation_system.model.user import User

__version__ = (1,0,0)

class ConfigurationError(Exception):
    """Signals the configuration failed somehow."""
    pass

class metadict(dict):
    """A dictionary extension for storing metadata along with the keys.
    It behaves like a normal dictionary in all other cases."""
    def __init__(self, *args, **kw):
        """Creates a metadict dictionary. If the keyword 'compact_creation' is used the
        entries will be given like: key1=(value1, dict1) or key2=value2
        and dict1 is the dictionary attached to the key providing metadata."""
        self.metainfo = {}
        compact_creation = kw.pop('compact_creation', False)
        if compact_creation:
            #separate the special "value" in the first field from the dictionary in the second
            super(metadict,self).__init__()
            for key, values in kw.items():
                if isinstance(values, tuple):
                    if len(values) != 2: 
                        raise AttributeError("On compact creation a tuple with only 2 values is expected: (value, metadata)")
                    if not isinstance(values[1],dict): 
                        raise AttributeError("metadata entry must be a dictionary")
                    self[key] = values[0]
                    self.metainfo[key] = values[1]
                else:
                    self[key] = values
        else:
            super(metadict,self).__init__(*args, **kw)
        
    def copy(self):
        """return a deep copy of this metadict"""
        return deepcopy(self)
    
    def getMetadata(self, key):
        """Return the metadata allocated for the given key if any."""
        if key in self.metainfo: return self.metainfo[key]
        else: return None
        
    def setMetadata(self, key, **meta_dict):
        """Store/replace the metadata allocated for the given key."""
        if key not in self: raise KeyError(key)
        if key not in self.metainfo: self.metainfo[key] = {}
        self.metainfo[key].update(meta_dict)
    
    def clearMetadata(self, key):
        """Clear all metadata allocated under the given key."""
        if key not in self: raise KeyError(key)
        if key in self.metainfo: del self.metainfo[key]
        
    def put(self, key, value, **meta):
        """Puts a key,value pair into the dictionary and all other keywords are added
        as meta-data to this key."""
        self[key] = value
        if meta:
            self.setMetadata(key, **meta)

    @staticmethod
    def hasMetadata(some_dict, key=None):
        """Returns if the given dictionary has metadata"""
        if key is None:
            return hasattr(some_dict, 'getMetadata')
        else:
            return hasattr(some_dict, 'getMetadata') and bool(some_dict.getMetadata(key))
    
    @staticmethod
    def getMetaValue(some_dict, key, meta_key):
        """Return the metadata associated with the key if any or None if not found or
        this is not a metadict"""
        if metadict.hasMetadata(some_dict):
            meta = some_dict.getMetadata(key)
            if meta and meta_key in meta: return meta[meta_key]

        
class PluginAbstract(object):
    """This is the base class for all plugins"""
    
    __metaclass__ = abc.ABCMeta
    #===========================================================================
    # class __metaclass__(abc.ABCMeta):
    #    """This metaclass encapsulates the abstract class from abc and allows plugin self-registration
    #    and control. All plugin "classes" inheriting from this class will go through this method
    #    while being defined"""
    #    def __init__(self, name, bases, namespace):
    #        if name != 'PluginAbstract':
    #            #This is a new subclass. We may register it on the fly now.
    #            pass
    #            return abc.ABCMeta.__init__(PluginAbstract, name, bases, namespace)
    #        return abc.ABCMeta.__init__(abc.ABCMeta, name, bases, namespace)
    #===========================================================================

    def __init__(self, *args, **kwargs):
        """Plugin main constructor. It is designed to catch all calls. It accepts a "user"
argument containing an evaluation_system.model.user.User object for which this plugin will
be created. If given it will be passed to the implementing plugin and use to get different
user-defined configurations. If no user is provided an object representing the user
that started this program is created.""" 
        self._user = kwargs.pop('user', None)
        if 'user' in kwargs:
            self._user = kwargs['user']
        else:
            self._user = User()
        
    @abc.abstractproperty
    def __version__(self):
        """Returns the version of the plugin"""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractproperty
    def __short_description__(self):
        """Returns the version of the plugin"""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractproperty
    def __config_metadict__(self):
        """A metadict containing the definition of all known configurable parameters for the
        implementing plugin class. The used metadata items are:
        type:=class
            define the class of the parameter, it will also be used for casting the string values stored
            in configurations files. Normally is one of str, int, float or bool. It'S only required if there's
            no default value and therefore the type cannot be infered from it.
        help:=string
            some explanation regarding the parameter, this will get written in the config file and displayed to
            the user.
        mandatory:=any
            if this attribute is mandatory (if not present it is not)"""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractmethod
    def runTool(self, config_dict = None):
        """Starts the tool with the given configuration and returns a metadict with the created files
        Parametes
        config_dict: metadict
            Current configuration with which the tool will be run
        @return: see and use self.prepareOutput([<list_of_created_files>])"""
        raise NotImplementedError("This method must be implemented")
    
    def prepareOutput(self, output_files):
        """Prepare output for files supposedly created. This method checks the files exists
        and return a dictionary with information about them. Use it for the return call of runTool.
        Parameters
        output_files: iterable of strings or single string
            Paths to all files that where created by the tool.
        @return: dict with the paths to the files that were created and some info if possible:
            {<absolute_path_to_file>:{'timestamp': os.path.getctime(<absolute_path_to_file>),
                                      'size': os.path.getsize(<absolute_path_to_file>)}"""
        result = {}
        if isinstance(output_files, basestring): output_files = [output_files]
        for file_path in output_files:
            if isinstance(output_files, dict): metadata = output_files
            else: metadata = {}
            if os.path.isfile(file_path):
                if 'timestamp' not in metadata:
                    metadata['timestamp'] = os.path.getctime(file_path)
                if 'size' not in metadata:
                    metadata['size'] = os.path.getsize(file_path)
                if 'type' not in metadata:    
                    ext = os.path.splitext(file_path)
                    if ext:
                        ext = ext[-1].lower()
                        if ext in '.jpg .jpeg .png .gif .tif .svg .pdf .ps .eps .tex'.split():
                            metadata['type'] = 'plot'
                        elif ext in '.nc .bin .ascii'.split():
                            metadata['type'] = 'data'
            result[os.path.abspath(file_path)] = metadata
                        
        return result


    def getHelp(self):
        """Return some help for the user"""
        import textwrap
        separator=''
        help_str = ['%s (v%s): %s' % (self.__class__.__name__, '.'.join([str(i) for i in self.__version__]), self.__short_description__)]
        #compute maximal param length for better viewing
        max_size= max([len(k) for k in self.__config_metadict__] + [0])
        if max_size > 0:
            wrapper = textwrap.TextWrapper(width=80, initial_indent=' '*(max_size+1), subsequent_indent=' '*(max_size+1), replace_whitespace=False)
            help_str.append('Options:')
        
         
            for key in sorted(self.__config_metadict__):
                value = self.__config_metadict__[key]

                param_format = '%%-%ss (default: %%s)' % (max_size) 
                help_str.append(param_format % (key, value))
                if metadict.getMetaValue(self.__config_metadict__, key, 'mandatory'):
                    help_str[-1] = help_str[-1] + ' [mandatory]'

                key_help = metadict.getMetaValue(self.__config_metadict__, key, 'help')
                if key_help:
                    #wrap it properly
                    help_str.append('\n'.join(wrapper.fill(line) for line in 
                           key_help.splitlines()))
                help_str.append(separator)
        
        return '\n'.join(help_str)
    
    def getCurrentConfig(self, config_dict=None):
        """Return the given configuration ready for displaying
        Parameters
        config_dict: dict
            Contains the current configuration being displayed, if missing the default values will be shown
        @return: a string displaying the given configuration values"""
        max_size= max([len(k) for k in self.__config_metadict__])
        if config_dict is None: config_dict = {}
        
        current_conf = []
        for key in sorted(self.__config_metadict__):
            line_format = '%%%ss: %%s' % max_size
            
            if key in config_dict and config_dict[key]:
                curr_val = config_dict[key]
            else:
                if self.__config_metadict__[key] is None: 
                    if metadict.getMetaValue(self.__config_metadict__, key, 'mandatory'):
                        curr_val = '- *MUST BE DEFINED!*'
                    else:
                        curr_val = '-'
                else:
                    curr_val = '- (default: %s)' % (self.__config_metadict__[key])
            
            current_conf.append(line_format % (key, curr_val))
    
        return '\n'.join(current_conf)

    def getClassBaseDir(self):
        """Returns the absolute path to the class subcasting this plugin"""
        subclass_file = os.path.abspath(sys.modules[self.__module__].__file__)
        return os.path.join(*self._splitPath(subclass_file)[:-len(self.__module__.split('.'))])

    def getCurrentUser(self):
        """Returns the user for which this instance was generated."""
        return self._user
        
    @staticmethod
    def __to_bool(bool_str):
        """Parses a string for a boolean value"""
        if isinstance(bool_str, basestring) and bool_str: 
            if bool_str.lower() in ['true', 't', '1']: return True
            elif bool_str.lower() in ['false', 'f', '0']: return False
            
        #if here we couldn't parse it
        raise ValueError("'%s' is no recognized as a boolean value" % bool_str)
        
    def _parseConfigStrValue(self, key, str_value, fail_on_missing=True):
        """Try to parse a str_value that is a string into the most appropriate str_value according. 
        The logic is as follows:
        0) If there's no reference dictionary the str_value is returned as is.
        1) if the __config_metadict__ is a metadict and has a 'type' metadata attribute, that will be used for casting
        2) if the __config_metadict__ has a str_value for the key, the type of the __config_metadict__ str_value would be used
        3) if the key is not found in the reference __config_metadict__ an exception will be thrown unless
           `fail_on_missing` was set to `False`, in which case it will return str_value as it was. 
        4) if the type results in NoneType an exception will be thrown"""
        if self.__config_metadict__ is None or (not fail_on_missing and key not in self.__config_metadict__):
            #if there's no dictionary reference or the key is not in it and we are not failling
            #just return the str_value 
            return str_value 
        key_type = metadict.getMetaValue(self.__config_metadict__, key, 'type')
        
        #if no metadata is present infer from default str_value
        if key_type is None: 
            if key in self.__config_metadict__:
                key_type = type(self.__config_metadict__[key])
            else:
                raise ConfigurationError("Unknown parameter %s" % key)
        try:
            if key_type is type(None):
                raise ConfigurationError("Default arguments type missing. Can't infer argument type.")
            elif key_type is bool:
                return PluginAbstract.__to_bool(str_value)
            else:
                return key_type(str_value)
        except ValueError:
            raise ConfigurationError("Can't parse str_value %s for option %s. Expected type: %s" % (str_value, key, key_type.__name__))
        
    def parseArguments(self, opt_arr):
        """Parse an array of strings and return a configuration dictionary.
        The strings are of the type: ['key1=val1', 'key2']
        Parameters:
        opt_arr:= string array with options to be parsed
        See `_parseConfigStrValue` for more information on how the parsing is done.
        """
        config = {}
        
        for option in opt_arr:            
            parts = option.split('=')
            if len(parts) == 1:
                key, value = parts[0], 'true'
            else:
                key = parts[0]
                #just in case there were multiple '=' characters
                value = '='.join(parts[1:])
                
            config[key] = self._parseConfigStrValue(key, value)

        return config
        
    def setupConfiguration(self, config_dict = None, template = None, check_cfg = True, recursion=True):
        """Define the configuration required for processing this files. If a template was given,
        the return value is a string containing the complete configuration. If not the config_dict
        will be returned but with all indirections being resolved. Eg:
        dict(a=1, b='1.txt', c='old_1.txt') == setpuConfiguration(config_dict=dict(a=1, b='$a.txt', c='old_$b'))
        
        Parameters
        config_dic : dict (None)
            dictionary with the configuration to be used when generating the configuration file
        template : string.Template, optional
            defines the template for the configuration.
        check_cfg : boolean (True)
            whether the method checks that the resulting configuration dictionary (i.e. the default 
            updated by `config_dict`) has no None values after all substituions are made.
        recursion : boolean (True)
            Whether when resolving the template recursion will be applied, i.e. variables can be set
            with the values of other variables, e.g. recursion^a==1^b=="x${a}x" => f(b)=="x1x" 
        @return
            if a template was provided, the substituted configuration string
            else a metadict with all defaults values plus those provided here.
        """
        
        
        if config_dict:
            conf = self.__config_metadict__.copy() 
            conf.update(config_dict)
            config_dict = conf
        else:
            config_dict = self.__config_metadict__.copy()
        
        if template and isinstance(template, basestring):
            #be nice with whomever is implementing dice and accept normal strings
            import string 
            template = string.Template(template)
            
        user_vars_dict = self._user.getUserVarDict(self.__class__.__name__)
        user_vars_dict.update(config_dict)
        
        #accept a maximal recursion of 5 for resolving all tokens
        #5 is a definite number larger than any thinkable recursion for this case
        max_iter = 5
        while recursion and max_iter > 0:
            recursion = False   #assume no recursion until one possible case is found
            for key, value in config_dict.items():                
                if isinstance(value, basestring) and '$' in value:
                    config_dict[key] = Template(value).safe_substitute(user_vars_dict)
                    recursion = True
            max_iter -= 1
        
        #Allow inheriting class to modify the final configuration before issuing it
        config_dict = self._postTransformCfg(config_dict)
        
        if check_cfg:
            missing =[ k for k,v in config_dict.items() if v is None and metadict.getMetaValue(config_dict, k ,'mandatory')]
            if missing:
                raise ConfigurationError("Missing required configuration for: %s" % ', '.join(missing))
        if template:
            return template.substitute(config_dict)
        else:
            return config_dict
        
    def _dictValuesToString(self, dictionary):
        """Transform a dictionary into its representation. no recursion is been handled here, that should
        be left to the implementing class to solve. The original dictionary is not transformed a copy is created
        and returned.
        Parameters
        dictionary := The dictionary to transform"""
        result = {}
        for key, value in dictionary.items():
            result[key] = repr(value)
        return result
    
    def writeToConfigParser(self, config_dict, config_parser=None):
        """Add the given configuration dictionary to a ConfigParser object.
        The section is determined by the name of the implemnting class.
        Parameters
        confi_dict := dict or metadict
            configuration dict to be stored
        config_parser := subclass of ConfigParser.RawConfigParser
            config parser where this info is stored. If None is give a config parser is created (default: None)"""
        section = self.__class__.__name__
        if config_parser is None: config_parser = SafeConfigParser()
        if not config_parser.has_section(section): config_parser.add_section(section)
        for key, value in config_dict.items():
            key_help = metadict.getHelp(config_dict, key)            
            if key_help:
                config_parser.set(section, '#%s' % key, key_help)
            config_parser.set(section, key, repr(value))
        return config_parser
    
    def readFromConfigParser(self, config_parser):
        """Reads a configuration from a config parser object.
        The values are assumed to be in a section named just like the class implementing this method.
        Parameters
        config_parser:= subclass of ConfigParser.RawConfigParser
            From where the configuration is going to be read

        @return: a metadict which is a clone of the default one (if provided) updated with the
            information found in the config Parser"""
        
        section = self.__class__.__name__
        #create a copy of metadict
        result = self.__config_metadict__.copy()
        #we do this to avoid having problems with the "DEFAULT" section as it might define
        #more options that what this plugin requires
        keys = set(result).intersection(config_parser.options(section))
        #update values as found in the configuration
        for key in keys:
            #parse the value as good as possible
            result[key] = self._parseConfigStrValue(key, config_parser.get(section, key))
        return result
        
    def readConfiguration(self, fp):
        """Read the configuration from a file object using a SafeConfigParser.
        Parameters
        fp:= file object
            From where the configuration is going to be read
        default_metadict:= dict or metadict
            Reference information for parsing the values.
        @return: a metadict which is a clone of the default one (if provided) updated with the
            information found in the config Parser"""
        config_parser = SafeConfigParser()
        config_parser.readfp(fp)
        return self.readFromConfigParser(config_parser)

    def saveConfiguration(self, fp, config_dict=None):
        """Stores the given configuration to the provided file object.
        if no configuration is provided the default one will be used."""
        #store the section header
        if config_dict is None:
            #a default incomplete one
            config_dict = self.setupConfiguration(check_cfg=False)
        fp.write('[%s]\n' % self.__class__.__name__)

        import textwrap
        wrapper = textwrap.TextWrapper(width=80, initial_indent='#: ', subsequent_indent='#:  ', replace_whitespace=False,drop_whitespace=False,break_on_hyphens=False,expand_tabs=False)

        for key, value in config_dict.items():
            key_help = metadict.getMetaValue(config_dict, key, 'help')
            isMandatory = metadict.getMetaValue(config_dict, key, 'mandatory')
            if key_help:
                    #make sure all new lines are comments!
                    help_lines = key_help.splitlines()                    
                    if isMandatory:
                        help_lines[0] = '[mandatory] ' + help_lines[0]
                    fp.write('\n'.join([wrapper.fill(line) for line in help_lines]))
                    fp.write('\n')
            if value is None:
                #means this is not setup
                if isMandatory:
                    value="<THIS MUST BE DEFINED!>"
                else:
                    value=""
                    key='#'+key
            fp.write('%s=%s\n\n' % (key, value))
            fp.flush()  #in case we want to stream this for a very awkward reason...
        return fp
        
    
    def _postTransformCfg(self, config_dict):
        """Allow plugins to give a final check or modification to the configuration before being issued"""
        return config_dict
    
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
        #=======================================================================
        # env_file = '%s/etc/setup_bash.env' % self.getClassBaseDir()
        # if os.path.isfile(env_file):         
        #    #This is not much less secure than running the plugins themselves...
        #    #it spawns a bash shell, sources the environment and issue the given command 
        #    p = Popen(['/bin/bash', '-c', '. "%s" >/dev/null; %s' % (env_file, cmd_string)], stdout=stdout, stderr=stderr)
        # else:
        #    #but if we don't need a shell, then we don't do it
        #    cmd = shlex.split(cmd_string)
        #    p = Popen(cmd, stdout=stdout, stderr=stderr)
        #=======================================================================

        log.debug("Calling: %s", cmd_string)
        p = Popen(['/bin/bash', '-c', cmd_string], stdout=stdout, stderr=stderr)

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
