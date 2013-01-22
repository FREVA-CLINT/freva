'''

.. moduleauthor:: estani <estanislao.gonzalez@met.fu-berlin.de>


This module defines the basic objects for implementing a plug_in.

* :class:`metadict`: It's used for defining :class:`PluginAbstract.__config_metadict__` which holds
                     information about the parameters the plug-in will be requiring.
* :class:`PluginAbstract`: It's an abstract class which provides many useful methods, requires
                           some to be defined and keeps track of the classes implementing it.
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
from evaluation_system.misc.utils import TemplateDict

__version__ = (1,0,0)

class ConfigurationError(Exception):
    """Signals the configuration failed somehow."""
    pass

class metadict(dict):
    """A dictionary extension for storing metadata along with the keys.
In all other cases, it behaves like a normal dictionary."""
    def __init__(self, *args, **kw):
        """Creates a metadict dictionary. 
If the keyword ``compact_creation`` is used and set to ``True`` the entries will be given like this: 

    key1=(value1, dict1) or key2=value2
    
Where dict1 is the dictionary attached to the key providing its meta-data (key2 has no meta-data, by the way)."""
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
        """:return: a deep copy of this metadict."""
        return deepcopy(self)
    
    def getMetadata(self, key):
        """:return: The meta-data value associated with this key or ``None`` if no meta-data was stored."""
        if key in self.metainfo: return self.metainfo[key]
        else: return None
        
    def setMetadata(self, key, **meta_dict):
        """Store/replace the meta-data allocated for the given key.

:raises: KeyError if key is not present."""
        if key not in self: raise KeyError(key)
        if key not in self.metainfo: self.metainfo[key] = {}
        self.metainfo[key].update(meta_dict)
    
    def clearMetadata(self, key):
        """Clear all meta-data allocated under the given key.

:raises: KeyError if key is not present."""
        if key not in self: raise KeyError(key)
        if key in self.metainfo: del self.metainfo[key]
        
    def put(self, key, value, **meta_dict):
        """Puts a key,value pair into the dictionary and all other keywords are added
as meta-data to this key. If key was already present, it will be over-written and its
meta-data will be removed (even if no new meta-data is provided)."""
        self[key] = value
        if meta_dict:
            self.clearMetadata(key)
            self.setMetadata(key, **meta_dict)

    @staticmethod
    def hasMetadata(some_dict, key=None):
        """if the given dictionary has meta-data for the given key or, if no key was given,
 if the dictionary can hold meta-data at all.

:returns: if ``some_dict`` has stored meta-data for ``key`` or any meta-data at all if ``key==None``."""
        if key is None:
            return hasattr(some_dict, 'getMetadata')
        else:
            return hasattr(some_dict, 'getMetadata') and bool(some_dict.getMetadata(key))
    
    @staticmethod
    def getMetaValue(some_dict, key, meta_key):
        """This method allows to work both with normal dictionaries and metadict transparently.
        
:returns: the meta-data associated with the key if any or None if not found or
          this is not a metadict at all."""
        if metadict.hasMetadata(some_dict):
            meta = some_dict.getMetadata(key)
            if meta and meta_key in meta: return meta[meta_key]


        
class PluginAbstract(object):
    """This is the base class for all plug-ins. It is the only class that needs to be inherited from when implementing a plug-in.
    
From it, you'll need to implement the few attributes and/or methods marked as abstract with the decorator
``@abc.abstractproperty`` or ``@abc.abstractmethod`` (Sphinx can't handle decorators, so you'll see this in the code only
though I've added them to the docs so they show in the API documentation).

You may overwrite all methods and properties defined in here, but you'll be breaking the contract
between the methods so you'll have to make sure it doesn't break anything else. Please write some tests
for your own class that checks it is working as expected.

This very short example that shows a complete plug-in. Although it does nothing it already show the most important part,
the :class:`evaluation_system.api.plugin.metadict` used for defining meta-data on the parameters::

    from evaluation_system.api import plugin
    
    class MyPlugin(plugin.PluginAbstract):
        __short_description__ = "MyPlugin short description (just to know what it does)" 
        __version__ = (0,0,1)
        __config_metadict__ =  plugin.metadict(compact_creation=True, 
                                    number=(None, dict(type=int, help='This is an optional configurable int variable named number without default value and this description')),
                                    the_number=(None, dict(type=float, mandatory=True, help='A required float value without default')), 
                                    something='test', #a simple optional test value with default value and no description 
                                    other=1.4)        #another float value. 
                                                      #You cannot define a parameter without a default value and no metadata 'type' attribute 
                                                      #as it defines how it should be parsed from a string (for config files, command line arguments, etc).
    
        def runTool(self, config_dict=None):
            print "MyPlugin", config_dict

If you need to test it use the ``EVALUATION_SYSTEM_PLUGINS`` environmental variable to point to the source directory and package.
For example assuming you have th source code in ``/path/to/source`` and the package holding the class implementing :class:`evaluation_system.api.plugin` is
``package.plugin_module`` (i.e. its absolute file path is ``/path/to/source/package/plugin_module.py``), you would tell the system how to find
the plug-in by issuing the following command (bash & co)::

    export EVALUATION_SYSTEM_PLUGINS=/path/to/source,package.plugin_module

Use a colon to separate multiple items::

    export EVALUATION_SYSTEM_PLUGINS=/path1,plguin1:/path2,plugin2:/path3,plugin3

By telling the system where to find the packages it can find the :class:`evaluation_system.api.plugin` implementations. The system just loads the packages and get to the classes using the :py:meth:`class.__subclasses__` method. The reference speaks about *weak references* so it's not clear if (and when) they get removed. 
We might have to change this in the future if it's not enough. Another approach would be forcing self-registration of a class in the :ref:`__metaclass__ <python:datamodel>` attribute when the class is implemented. 

For more general (and less technical) information refer to the wiki: https://code.zmaw.de/projects/miklip-d-integration/wiki
"""
    
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
    special_variables = None
    """This dictionary is used to resolve the *special variables* that are available
to the plug-ins for defining some values of their parameters in a standardize manner.
These are initialized per user and plug-in. The variables are:

================== ====================================================================
   Variables          Description
================== ====================================================================
USER_BASE_DIR      central directory for this user in the evaluation system.
USER_OUTPUT_DIR    directory where the output data for this user is stored.
USER_PLOTS_DIR     directory where the plots for this user is stored.
USER_CACHE_DIR     directory where the cached data for this user is stored.
SYSTEM_DATE        current date in the form YYYYMMDD (e.g. 20120130)
SYSTEM_DATETIME    current date in the form YYYYMMDD_HHmmSS (e.g. 20120130_101123)
SYSTEM_TIMESTAMP   milliseconds since epoch (i.e. a new number every millisecond)
SYSTEM_RANDOM_UUID a random UUID string (just something random of the form a3e7-e12...)
================== ====================================================================

A plug-in/user might then use them to define a value in the following way::

    output_file='$USER_OUTPUT_DIR/myfile_${SYSTEM_DATETIME}blah.nc'

"""
    def __init__(self, *args, **kwargs):
        """Plugin main constructor. It is designed to catch all calls. It accepts a ``user``
argument containing an :class:`evaluation_system.model.user.User` representing the user for 
which this plug-in will be created. It is used here for setting up the user-defined configuration but 
the implementing plug-in will also have access to it. If no user is provided an object representing 
the current user, i.e. the user that started this program, is created.""" 
        if 'user' in kwargs:
            self._user = kwargs.pop('user')
        else:
            self._user = User()
            
        #this construct fixes some values but allow others to be computed on demand
        #it holds the special variables that are accessible to both users and developers
        #self._special_vars = SpecialVariables(self.__class__.__name__, self._user)
        
        from functools import partial
        from datetime import datetime
        from time import time
        from uuid import uuid4
        plugin_name, user = self.__class__.__name__, self._user
        self._special_variables = TemplateDict(
            USER_BASE_DIR      = user.getUserBaseDir,
            USER_CACHE_DIR     = partial(user.getUserCacheDir, tool=plugin_name, create=True),
            USER_PLOTS_DIR     = partial(user.getUserPlotsDir, tool=plugin_name, create=True),
            USER_OUTPUT_DIR    = partial(user.getUserOutputDir, tool=plugin_name, create=True),
            SYSTEM_DATE        = lambda: datetime.now().strftime('%Y%m%d'),
            SYSTEM_DATETIME    = lambda: datetime.now().strftime('%Y%m%d_%H%M%S'),
            SYSTEM_TIMESTAMP   = lambda: str(long(time() * 1000)),
            SYSTEM_RANDOM_UUID = lambda: str(uuid4()))
        
    @abc.abstractproperty
    def __version__(self):
        """``@abc.abstractproperty`` 

A 3-value tuple representing the version of the plug-in. E.g. ``(1, 0, 3)`` that's (major, minor, build)."""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractproperty
    def __short_description__(self):
        """``@abc.abstractproperty``

A short description of this plug-in. It will be displayed to the user in the help and
when listing all plug-ins."""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractproperty
    def __config_metadict__(self):
        """``@abc.abstractproperty``

A :class:`metadict` containing the definition of all known configurable parameters for the
implementing class. The meta-data items used from it are:

type
    defines the class of the parameter, it will also be used for casting the string values stored
    in configurations files. Normally is one of str, int, float or bool. It's only required if there's
    no default value, i.e. it's ``None``, and therefore the type cannot be inferred from it.
    
help
    A string providing some explanation regarding the parameter, this will get written in the 
    configuration file and displayed to the user when requesting help.
    
mandatory
    boolean equivalent that tells if this attribute is mandatory (if not present, it is not)

You may use the ``compact_creation`` special key to create the dictionary in a compact manner::

    metadict('compact_creation' = True, 
        a_number = (None, dict(type = int, mandatory = True, help = 'Just a number.')),
        another = (1.4, dict(help = 'Some optional parameter with a default value')),
        nothing = 'a string')

You may use a simple dictionary too, but there are huge limitations applied by doing so, e.g. all values *must* have
default values and there will be no help whatsoever."""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractmethod
    def runTool(self, config_dict = None):
        """``@abc.abstractmethod``

Starts the tool with the given configuration. It is expected to return a :class:`metadict` with the
paths to the created files and some info about them. This can be directly handled by passing just
a list (or anything iterable) to :class:`prepareOutput` .


:param config_dict: A dict/metadict with the current configuration with which the tool will be run
:return: see and use self.prepareOutput([<list_of_created_files>])"""
        raise NotImplementedError("This method must be implemented")
    
    def prepareOutput(self, output_files):
        """Prepare output for files supposedly created. This method checks the files exist
and returns a dictionary with information about them::

    { <absolute_path_to_file>: {
        'timestamp': os.path.getctime(<absolute_path_to_file>),
        'size': os.path.getsize(<absolute_path_to_file>)
        }
    }

Use it for the return call of runTool.
    
:param output_files: iterable of strings or single string with paths to all files that where created by the tool.
:return: dictionary with the paths to the files that were created as key and a dictionary as value.
    """
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
        """This method uses the information from the implementing class name, :class:`__version__`, 
:class:`__short_description__` and :class:`__config_metadict__` to create a proper help.
Since it returns a string, the implementing class might use it and extend it if required. 

:returns: a string containing the help."""
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
    
    def getCurrentConfig(self, config_dict = {}):
        """
:param config_dict: the dict/metadict containing the current configuration being displayed. 
                    This info will update the default values.
:return: the current configuration in a string for displaying."""
        max_size= max([len(k) for k in self.__config_metadict__])
        
        current_conf = []
        config_dict_resolved = self.setupConfiguration(config_dict=config_dict, check_cfg=False)
        config_dict_orig = dict(self.__config_metadict__)
        config_dict_orig.update(config_dict)
        
        def show_key(key):
            "This functions formats the results depending on whether the values contain variables or not."
            if config_dict_resolved[key] == config_dict_orig[key]:
                return  config_dict_orig[key]
            else:
                return '%s [%s]' % (config_dict_orig[key], config_dict_resolved[key]) 
        
        for key in sorted(self.__config_metadict__):
            line_format = '%%%ss: %%s' % max_size
            
            
            if key in config_dict:
                #user defined
                curr_val = show_key(key)
            else:
                #default value
                default_value = self.__config_metadict__[key]
                if default_value is None: 
                    if metadict.getMetaValue(self.__config_metadict__, key, 'mandatory'):
                        curr_val = '- *MUST BE DEFINED!*'
                    else:
                        curr_val = '-'
                else:
                    curr_val = '- (default: %s)' % show_key(key)
                    

            
            current_conf.append(line_format % (key, curr_val))
    
        return '\n'.join(current_conf)

    def getClassBaseDir(self):
        """:returns: the absolute path to the module defining the class implementing this plug-in."""
        subclass_file = os.path.abspath(sys.modules[self.__module__].__file__)
        return os.path.join(*self._splitPath(subclass_file)[:-len(self.__module__.split('.'))])

    def getCurrentUser(self):
        """:returns: the :class:`evaluation_system.model.user.User` for which this instance was generated."""
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
        """Try to parse the string in ``str_value`` into the most appropriate value according 
to the following logic:

#. if there's no :class:`__config_metadict__` ``str_value`` is returned as is.
#. if the :class:`__config_metadict__` is a :class:`metadict` and has a *type* 
   metadata attribute, this will be used for casting.
#. if the :class:`__config_metadict__` has a value for ``key``, then ``type(``:class:`__config_metadict__` ``[key]``) will be used.
#. if ``key`` is not found in the reference :class:`__config_metadict__` an exception will be thrown unless
   ``fail_on_missing`` was set to `False`, in which case it will return ``str_value``. 
#. if the type results in NoneType an exception will be thrown

:param key: Reference to the value being parsed.
:type key: str
:param str_value: The string that will be parsed.
:type str_value: str
:param fail_on_missing: If the an exception should be risen in case the key is not found in :class:`__config_metadict__`
:type fail_on_missing: bool
:return: the parsed string, or the string itself if it couldn't be parsed, but no exception was thrown.
:raises: ( :class:`ConfigurationError` ) if parsing couldn't succeed.
"""
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
        """Parses an array of strings and return a configuration dictionary.
The strings are of the type: ``key1=val1`` or ``key2``

:type opt_arr: List of strings
:param opt_arr: See :class:`_parseConfigStrValue` for more information on how the parsing is done.
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
        """Defines the configuration required for running this plug-in. If ``template`` was given,
the return value is a string containing the complete configuration that results from filling out
the template with the resulting configuration.
If not a dictionary will be returned but with all indirections being resolved. E.g.::

    dict(a=1, b='1.txt', c='old_1.txt') == setupConfiguration(config_dict=dict(a=1, b='$a.txt', c='old_$b'))

Basically :class:`__config_metadict__` will be updated with the values from ``config_dict``.
There are some special values pointing to user-related managed by the system defined in :class:`evaluation_system.model.user.User.getUserVarDict` .
 
:param config_dic: dictionary with the configuration to be used when generating the configuration file.
:type config_dic: dict or :class:`metadict`
:param template: defines the template for the configuration.
:type template: string.Template
:param check_cfg: whether the method checks that the resulting configuration dictionary (i.e. the default 
                  updated by `config_dict`) has no None values after all substituions are made.
:type check_cfg: bool
:param recursion: Whether when resolving the template recursion will be applied, i.e. variables can be set
                  with the values of other variables, e.g. ``recursion && a==1 && b=="x${a}x" => f(b)=="x1x"`` 
:type recursion: bool
:return:  if a template was provided, the substituted configuration string
          else a metadict with all defaults values plus those provided here.
        """
        if config_dict:
            conf = self.__config_metadict__.copy() 
            conf.update(config_dict)
            config_dict = conf
        else:
            config_dict = self.__config_metadict__.copy()
        
        results = self._special_variables.substitute(config_dict, recursive=recursion)

        #Allow inheriting class to modify the final configuration before issuing it
        results = self._postTransformCfg(results)
        
        if check_cfg:
            missing =[ k for k,v in results.items() if v is None and metadict.getMetaValue(config_dict, k ,'mandatory')]
            if missing:
                raise ConfigurationError("Missing required configuration for: %s" % ', '.join(missing))
        
        if template:
            if isinstance(template, Template):
                return template.substitute(results)
            else:
                return Template(template).substitute(results)
        else:
            return results
   
    def readFromConfigParser(self, config_parser):
        """Reads a configuration from a config parser object.
The values are assumed to be in a section named just like the class implementing this method.
        
:param config_parser: From where the configuration is going to be read.
:type config_parser: ConfigParser.RawConfigParser
:return: a :class:`metadict` which is a clone of :class:`__config_metadict__` (if available) updated with the
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
        """Read the configuration from a file object using a SafeConfigParser. See also :class:`saveConfiguration` .

:param fp: An object with a readline argument (e.g. as return by :py:func:`open` ) from where the configuration is going to be read.
:return: a :class:`metadict` which is a clone of :class:`__config_metadict__` (if available) updated with the
         information found in ``fp``"""
        config_parser = SafeConfigParser()
        config_parser.readfp(fp)
        return self.readFromConfigParser(config_parser)

    def saveConfiguration(self, fp, config_dict=None):
        """Stores the given configuration to the provided file object.
if no configuration is provided the default one will be used.

:param fp: An object with a readline argument (e.g. as return by :py:func:`open` ) from where the configuration is going to be read.
:param config_dict: a metadict with the configuration to be stored. If none is provided the result from
                    :class:`setupConfiguration` with ``check_cfg=False`` will be used."""
        #store the section header
        if config_dict is None:
            #a default incomplete one
            config_dict = self.setupConfiguration(check_cfg = False)
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
        """Allow plugins to give a final check or modification to the configuration before being issued.
This hook is especially useful if you need to transform booleans to special values (e.g. ``0`` or ``yes``)
or if the plug-in needs to define some values that overides what the user selects, etc.
Checking the completenes of the dictionary happens after this call return.

:param config_dict: the complete configuration dictionary as it would be used.
:returns: the final configuration in a dictionary that will be used for starting the underlaying tool."""
        return config_dict
    
    def call(self, cmd_string, stdin=None, stdout=PIPE, stderr=STDOUT):
        """Simplify the interaction with the shell. It calls a bash shell so it's **not** secure. 
It means, **never** start a plug-in comming from unknown sources.

:param cmd_string: the command to be issued in a string.
:type cmd_string: str
:param stdin: a string that will be forwarded to the stdin of the started process.
:type stdin: str
:param stdout: link the standard output of this command call to the given file descriptor. passing None will shut it up.
:type stdout: see :py:class:`subprocess.Popen`
:param stderr: link the standard error of this command call to the given file descriptor. Passing None will shut it up.
               Default is to forward ``stderr`` to ``stdout``. 
:type stderr: see :py:class:`subprocess.Popen`"""
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
