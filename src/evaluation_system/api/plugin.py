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
from time import time
from datetime import datetime
from ConfigParser import SafeConfigParser
import logging
log = logging.getLogger(__name__)

from evaluation_system.model.user import User
from evaluation_system.misc.utils import TemplateDict

__version__ = (1,0,0)

class ConfigurationError(Exception):
    """Signals the configuration failed somehow."""
    pass




        
class PluginAbstract(object):
    """This is the base class for all plug-ins. It is the only class that needs to be inherited from when implementing a plug-in.
    
From it, you'll need to implement the few attributes and/or methods marked as abstract with the decorator
``@abc.abstractproperty`` or ``@abc.abstractmethod`` (Sphinx can't handle decorators, so you'll see this in the code only
though I've added them to the docs so they show in the API documentation).

You may overwrite all methods and properties defined in here, but you'll be breaking the contract
between the methods so you'll have to make sure it doesn't break anything else. Please write some tests
for your own class that checks it is working as expected.

This very short example that shows a complete plug-in. Although it does nothing it already show the most important part,
the :class:`evaluation_system.api.parameters.ParameterDictionary` used for defining meta-data on the parameters::

    from evaluation_system.api import plugin, parameters
    
    class MyPlugin(plugin.PluginAbstract):
        __short_description__ = "MyPlugin short description (just to know what it does)" 
        __version__ = (0,0,1)
        __parameters__ =  parameters.ParameterDictionary(
                            parameters.Integer(name='number', help='This is an optional configurable int variable named number without default value and this description'),
                            parameters.Float(name='the_number',mandatory=True, help='A required float value without default'),
                            parameters.Bool(name='really', default=False, help='a boolean parameter named really with default value of false'), 
                            parameters.String(name='str')) #a simple optional string without any other information
    
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

    special_variables = None
    """This dictionary is used to resolve the *special variables* that are available
to the plug-ins for defining some values of their parameters in a standardize manner.
These are initialized per user and plug-in. The variables are:

================== ===================================================================================
   Variables          Description
================== ===================================================================================
USER_BASE_DIR      Absolute path to the central directory for this user in the evaluation system. 
USER_OUTPUT_DIR    Absolute path to where the output data for this user is stored. 
USER_PLOTS_DIR     Absolute path to where the plots for this user is stored. 
USER_CACHE_DIR     Absolute path to where the cached data for this user is stored. 
SYSTEM_DATE        Current date in the form YYYYMMDD (e.g. 20120130). 
SYSTEM_DATETIME    Current date in the form YYYYMMDD_HHmmSS (e.g. 20120130_101123). 
SYSTEM_TIMESTAMP   Milliseconds since epoch (i.e. a new number every millisecond, e.g. 1358929581838).
SYSTEM_RANDOM_UUID A random UUID string (e.g. 912cca21-6364-4f46-9b03-4263410c9899). 
================== ===================================================================================

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
    def __parameters__(self):
        """``@abc.abstractproperty``

A :class:`evaluation_system.plugin.parameters.ParametersDictionary` containing the definition of all known configurable 
parameters for the implementing class."""
        raise NotImplementedError("This attribute must be implemented")

    @abc.abstractmethod
    def runTool(self, config_dict = None):
        """``@abc.abstractmethod``

Starts the tool with the given configuration. It is expected to return a :class:`metadict` with the
paths to the created files and some info about them. This can be directly handled by passing just
a list (or anything iterable) to :class:`prepareOutput` .


:param config_dict: A dict with the current configuration (param name, value) with which the tool will be run
:return: see and use self.prepareOutput([<list_of_created_files>])"""
        raise NotImplementedError("This method must be implemented")
    
    def _runTool(self, config_dict = None):
        #start = time()
        
        result = self.runTool(config_dict=config_dict)
        #end = time()
        
        #length_seconds = end - start
        #datetime.fromtimestamp(start)
        return result
    
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
                self._extend_output_metadata(file_path, metadata)
                result[os.path.abspath(file_path)] = metadata
            elif os.path.isdir(file_path):
                #ok, we got a directory, so parse the contents recursively
                for file_path in [os.path.join(r,f) for r,_,files in os.walk(file_path) for f in files]:
                    metadata = {}
                    self._extend_output_metadata(file_path, metadata)
                    result[os.path.abspath(file_path)] = metadata
            else:
                result[os.path.abspath(file_path)] = metadata
        return result

    def _extend_output_metadata(self, file_path, metadata):
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
        
        
    def getHelp(self, width=80):
        """This method uses the information from the implementing class name, :class:`__version__`, 
:class:`__short_description__` and :class:`__config_metadict__` to create a proper help.
Since it returns a string, the implementing class might use it and extend it if required. 

:param width: Wrap text to this width.
:returns: a string containing the help."""
        return '%s (v%s): %s\n%s' % (self.__class__.__name__, '.'.join([str(i) for i in self.__version__]), \
                                     self.__short_description__, self.__parameters__.getHelpString())
        
    def getCurrentConfig(self, config_dict = {}):
        """
:param config_dict: the dict containing the current configuration being displayed. 
                    This info will update the default values.
:return: the current configuration in a string for displaying."""
        max_size= max([len(k) for k in self.__parameters__])
        
        current_conf = []
        config_dict_resolved = self.setupConfiguration(config_dict=config_dict, check_cfg=False)
        config_dict_orig = dict(self.__parameters__)
        config_dict_orig.update(config_dict)
        
        def show_key(key):
            "This functions formats the results depending on whether the values contain variables or not."
            if config_dict_resolved[key] == config_dict_orig[key]:
                return  config_dict_orig[key]
            else:
                return '%s [%s]' % (config_dict_orig[key], config_dict_resolved[key]) 
        
        for key in self.__parameters__:
            line_format = '%%%ss: %%s' % max_size
            
            
            if key in config_dict:
                #user defined
                curr_val = show_key(key)
            else:
                #default value
                default_value = self.__parameters__[key]
                if default_value is None: 
                    if self.__parameters__.get_parameter(key).mandatory:
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
        
    def _parseConfigStrValue(self, param_name, str_value, fail_on_missing=True):
        """Try to parse the string in ``str_value`` into the most appropriate value according 
to the parameter logic.

The string *None* will be mapped to the value ``None``. On the other hand the quoted word *"None"* will remain as the
string ``"None"`` without any quotes.

:param param_name: Parameter name to which the string belongs.
:type param_name: str
:param str_value: The string that will be parsed.
:type str_value: str
:param fail_on_missing: If the an exception should be risen in case the param_name is not found in :class:`__parameters__`
:type fail_on_missing: bool
:return: the parsed string, or the string itself if it couldn't be parsed, but no exception was thrown.
:raises: ( :class:`ConfigurationError` ) if parsing couldn't succeed.
"""
        
        if str_value == "None": return None
        elif str_value == '"None"': str_value = "None"
        
        if self.__parameters__ is None or (not fail_on_missing and param_name not in self.__parameters__):
            #if there's no dictionary reference or the param_name is not in it and we are not failing
            #just return the str_value 
            return str_value
        
        else:
            return self.__parameters__.get_parameter(param_name).parse(str_value) 
  
        
        
    def setupConfiguration(self, config_dict = None, check_cfg = True, recursion=True, substitute=True):
        """Defines the configuration required for running this plug-in. 
If not a dictionary will be returned but with all indirections being resolved. E.g.::

    dict(a=1, b='1.txt', c='old_1.txt') == setupConfiguration(config_dict=dict(a=1, b='$a.txt', c='old_$b'))

Basically the default values from :class:`__parameters__` will be updated with the values from ``config_dict``.
There are some special values pointing to user-related managed by the system defined in :class:`evaluation_system.model.user.User.getUserVarDict` .
 
:param config_dic: dictionary with the configuration to be used when generating the configuration file.
:type config_dic: dict or :class:`metadict`
:param check_cfg: whether the method checks that the resulting configuration dictionary (i.e. the default 
                  updated by `config_dict`) has no None values after all substituions are made.
:type check_cfg: bool
:param recursion: Whether when resolving the template recursion will be applied, i.e. variables can be set
                  with the values of other variables, e.g. ``recursion && a==1 && b=="x${a}x" => f(b)=="x1x"`` 
:type recursion: bool
:return:  a copy of self.self.__config_metadict__ with all defaults values plus those provided here.
        """
        if config_dict:
            conf = dict(self.__parameters__) 
            conf.update(config_dict)
            config_dict = conf
        else:
            config_dict = dict(self.__parameters__)
        
        if substitute:
            results = self._special_variables.substitute(config_dict, recursive=recursion)
        else:
            results = config_dict.copy()

        if check_cfg:
            self.__parameters__.validate_errors(results, raise_exception=True)
        
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
        result = dict(self.__parameters__)
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

    def saveConfiguration(self, fp, config_dict=None, include_defaults=False):
        """Stores the given configuration to the provided file object.
if no configuration is provided the default one will be used.

:param fp: An object with a readline argument (e.g. as return by :py:func:`open` ) from where the configuration is going to be read.
:param config_dict: a metadict with the configuration to be stored. If none is provided the result from
                    :class:`setupConfiguration` with ``check_cfg=False`` will be used."""
        #store the section header
        if config_dict is None:
            #a default incomplete one
            config_dict = self.setupConfiguration(check_cfg = False, substitute=False)
        fp.write('[%s]\n' % self.__class__.__name__)

        import textwrap
        wrapper = textwrap.TextWrapper(width=80, initial_indent='#: ', subsequent_indent='#:  ', replace_whitespace=False,break_on_hyphens=False,expand_tabs=False)
        
        #preserve order
        for param_name in self.__parameters__:
            if include_defaults:
                param = self.__parameters__.get_parameter(param_name)
                if param.help:
                        #make sure all new lines are comments!
                        help_lines = param.help.splitlines()                    
                        if param.mandatory:
                            help_lines[0] = '[mandatory] ' + help_lines[0]
                        fp.write('\n'.join([wrapper.fill(line) for line in help_lines]))
                        fp.write('\n')
                value = config_dict.get(param_name, None)
                if value is None:
                    #means this is not setup
                    if param.mandatory:
                        value="<THIS MUST BE DEFINED!>"
                    else:
                        value=param.default
                        param_name='#'+ param_name
                fp.write('%s=%s\n\n' % (param_name, value))
                fp.flush()  #in case we want to stream this for a very awkward reason...
                
            elif param_name in config_dict:
                param = self.__parameters__.get_parameter(param_name)
                value = config_dict[param_name]
                key_help = param.help
                isMandatory = param.mandatory
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
                        param_name='#'+ param_name
                fp.write('%s=%s\n\n' % (param_name, value))
                fp.flush()  #in case we want to stream this for a very awkward reason...
        return fp
        
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
        if log.isEnabledFor(logging.DEBUG):
            bash_opt = '-xc'
        else:
            bash_opt = '-c'
        p = Popen(['/bin/bash', bash_opt, cmd_string], stdout=stdout, stderr=stderr)

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
