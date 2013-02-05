'''
.. moduleauthor:: estani <estanislao.gonzalez@met.fu-berlin.de>

This module manages the loading and access to all plug-ins. It is designed as a central registration thorugh
which plug-ins can be accessed.

Plug-ins are automatically registered if  found either in a specific directory ``<evaluation_system_root_dir>/tools``
or by using the environmental variable ``EVALUATION_SYSTEM_PLUGINS``.
This variable must to point to the modules implementing :class:`evaluation_system.api.plugin.PluginAbstract`. 

The value stored there is a colon (':') separated list of ``path,package`` comma (',') separated pairs. The path
denotes where the source is to be found, and the package the module name in which the PluginAbstract interface is being implemented. For example::

    EVALUATION_SYSTEM_PLUGINS=/path/to/some/dir/,something.else.myplugin:/other/different/path,some.plugin:/tmp/test,some.other.plugin

'''


#*** Initialize the plugin
import os
import sys
import logging
log = logging.getLogger(__name__)

import evaluation_system.api.plugin as plugin
from evaluation_system.model.user import User
from evaluation_system.misc import config, utils

class PluginManagerException(Exception):
    """For all problems generating while using the plugin manager."""
    pass


PLUGIN_ENV = 'EVALUATION_SYSTEM_PLUGINS'
"""Defines the environmental variable name for pointing to the plug-ins"""
    
#all plugins modules will be dynamically loaded here.
__plugin_modules__ = {}
"""Dictionary of modules holding the plug-ins."""
__plugins__ = {}
"""Dictionary of plug-ins class_name=>class"""
__plugins_meta = {}
"""Dictionary of plug-ins with more information 
plugin_name=>{
    name=>plugin_name,
    plugin_class=>class,
    version=>(0,0,0)
    description=>"string"}"""
 
def munge( seq ):
    """Generator to remove duplicates from a list without changing it's order.
It's used to keep sys.path tidy.

:param seq: any sequence
:returns: a generator returning the same objects in the same sequence but skipping duplicates."""
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add( item )
            yield item
            
def reloadPulgins():
    """Reload all plug-ins. Plug-ins are then loaded first from the :class:`PLUGIN_ENV` environmental
variable and then from the configuration file. This means that the environmental variable has precedence
and can therefore overwrite existing plug-ins (useful for debugging and testing)."""
    #extra_modules = [(path, module) ... ]
    if PLUGIN_ENV in os.environ:
        #now get all modules loaded from the environment
        for path, module_name in map( lambda item: tuple([e.strip() for e in item.split(',')]), 
                                 os.environ[PLUGIN_ENV].split(':')):                
            #extend path to be exact by resolving all "user shortcuts" (e.g. '~' or '$HOME')
            path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
            if os.path.isdir(path):
                #we have a plugin_imp with defined api
                sys.path.append(path)
                #TODO this is not working like in the previous loop. Though we might just want to remove it,
                #as there seem to be no use for this info... 
                __plugin_modules__[module_name] = __import__(module_name)
            else:
                log.warn("Cannot load %s, directory missing: %s", module_name, path)

    #get the tools directory from the current one
    #get all modules from the tool directory
    plugins = list(config.get(config.PLUGINS))
    for plugin_name in plugins:
        py_dir = config.get_plugin(plugin_name, config.PLUGIN_PYTHON_PATH)
        py_mod = config.get_plugin(plugin_name, config.PLUGIN_MODULE)
        if os.path.isdir(py_dir):
            log.debug("Loading %s", plugin_name)
            sys.path.append(py_dir)
            __plugin_modules__[plugin_name] = __import__(py_mod)
        else:
            log.warn("Cannot load %s, directory missing: %s", plugin_name, py_dir)

    #no clean that path from duplicates...
    sys.path = [p for p in munge(sys.path)]
    
    #load all plugin classes found (they are loaded when loading the modules)
    for plug_class in plugin.PluginAbstract.__subclasses__():
        if plug_class.__name__ not in __plugins__:
            __plugins__[plug_class.__name__] = plug_class
        else:
            log.warn("PLUGIN %s is being overwritten.", plug_class.__name__)

    #now fill up the metadata
    for plugin_name, plugin_class in __plugins__.items():
        __plugins_meta[plugin_name.lower()] = dict(name=plugin_name,
                           plugin_class=plugin_class,
                           version=plugin_class.__version__,
                           description=plugin_class.__short_description__)
#This only runs once after start. To load new plugins on the fly we have 2 possibilities
#1) Watch the tool directory
#2) Use the plugin metaclass trigger (see `evaluation_system.api.plugin`
reloadPulgins()


def getPlugins():
    """Return a dictionary of plug-ins holding the plug-in classes and meta-data about them.
It's a dictionary with the ``plugin_name`` in lower case of what :class:`getPluginDict` returns.

The dictionary is therefore defined as::

    {plugin_name.lower() : dict(name = plugin_name,
                                plugin_class = plugin_class,
                                version=plugin_class.__version__,
                                description=plugin_class.__short_description__)

This can be used if the plug-in name is unknown."""
    return __plugins_meta

def getPluginDict(plugin_name):
    """Return the requested plug-in dictionary entry or raise an exception if not found.

name
    The class name implementing the plugin (and therefore inheriting from :class:`evaluation_system.api.plugin.PluginAbstract`)
plugin_class
    The class itself.
version
    A 3-value tuple representing the plug-in version (major, minor, build)
description
    A string providing a hort description about what the plugin does.

:type plugin_name: str
:param plugin_name: Name of the plug-in to search for.
:return: a dictionary with information on the plug-in 
"""
    plugin_name = plugin_name.lower()
    if plugin_name not in getPlugins():
        mesg = "No plugin named: %s" % plugin_name
        similar_words = utils.find_similar_words(plugin_name, getPlugins())
        if similar_words: mesg = "%s\n Did you mean?\n\t%s" % (mesg, '\n\t'.join(similar_words))
        mesg = '%s\n\nUse --list-tools to list all available plug-ins.' % mesg
        raise PluginManagerException(mesg)
    
    return getPlugins()[plugin_name]

def getPluginInstance(plugin_name, user = None):
    """Return an instance of the requested plug-in or raise an exception if not found.
At the current time we are just creating new instances, but this might change in the future, so it's
*not* guaranteed that the instances are *unique*, i.e. they might be re-used and/or shared.

:type plugin_name: str
:param plugin_name: Name of the plugin to search for.
:type user: :class:`evaluation_system.model.user.User`
:param user: User for which this plug-in instance is to be acquired. If not given the user running this program will be used.
:return: an instance of the plug-in. Might not be unique."""
    #in case we want to cache the creation of the plugin classes.
    if user is None: user = User()
    return getPluginDict(plugin_name)['plugin_class']()

def parseArguments(plugin_name, arguments, use_user_defaults=False, user=None, config_file=None):
    """Manages the parsing of arguments which are passed as a list of strings. These are in turn
sent to an instance of the plugin, that will handle the parsing. This is why the user is required
to be known at this stage.
    
:type plugin_name: str
:param plugin_name: Name of the plugin to search for.
:type arguments: list of strings
:param arguments: it will be parsed by the plug-in (see :class:`evaluation_system.api.plugin.parseArguments`)
:type use_user_defaults: bool
:param use_user_defaults: If ``True`` and a user configuration is found, this will be used as a default for all non set arguments.
                          So the value will be determined according to the first found instance of: argument, user default, tool default
:type user: :class:`evaluation_system.model.user.User`
:param user: The user for whom this arguments are parsed.
:type config_file: str
:param config_file: path to a file from where the setup will read a configuration. If None, the default user dependent one will be used. 
                    This will be completely skipped if ``use_user_defaults`` is ``False``.
:return: A dictionary with the parsed configuration."""
    plugin_name = plugin_name.lower()
    if user is None: user = User()
    
    p = getPluginInstance(plugin_name, user)
    complete_conf = {}
    
    #if we are using user defaults then load them first
    if use_user_defaults:
        user_config_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(user_config_file):
            with open(user_config_file, 'r') as f:
                complete_conf.update(p.readConfiguration(f))
    #now if we still have a config file update what the configuration with it
    
    if isinstance(config_file, basestring):
        if config_file == '-':
            #reading from stdin
            complete_conf.update(p.readConfiguration(sys.stdin))
        elif config_file is not None:
            with open(config_file, 'r') as f:
                complete_conf.update(p.readConfiguration(f))
    elif config_file is not None:
        #if it's not a string and is something, we asume is something that can be read from
        complete_conf.update(p.readConfiguration(config_file))

    
    #update with user defaults if desired
    complete_conf.update(p.parseArguments(arguments))
    
    return complete_conf

def writeSetup(plugin_name, config_dict=None, user=None, config_file=None):
    """Writes the plug-in setup to disk. This is the configuration for the plug-in itself and not that
of the tool (which is what normally the plug-in encapsulates). The plug-in is not required to write anything to 
disk when running the tool; it might instead configure it from the command line, environmental variables or 
any other method.

:type plugin_name: str
:param plugin_name: name of the referred plugin.
:type config_dict: dict or metadict 
:param config_dict: The configuration being stored. If is None, the default configuration will be stored, 
    this might be incomplete.
:type user: :class:`evaluation_system.model.user.User`
:param user: The user for whom this arguments are parsed.
:type config_file: str
:param config_file: path to a file  where the setup will be stored. If None, the default user dependent one will be used. 
                    This will be completely skipped if ``use_user_defaults`` is ``False``.
:returns: The path to the configuration file that was written."""
    plugin_name = plugin_name.lower()
    if user is None: user = User()
    
    p = getPluginInstance(plugin_name, user)
    complete_conf = p.setupConfiguration(config_dict=config_dict, check_cfg=False, substitute=False)
    
    if config_file is None:
        #make sure the required directory structure and data is in place
        user.prepareDir()
         
        config_file = user.getUserToolConfig(plugin_name, create=True)

    if config_file == '-':
        p.saveConfiguration(sys.stdout, config_dict=complete_conf)
    else:
        with open(config_file, 'w') as f:
            p.saveConfiguration(f, config_dict=complete_conf)
    
    return config_file

def runTool(plugin_name, config_dict=None, user=None):
    """Runs a tool and stores this "run" in the :class:`evaluation_system.model.db.UserDB`.
    
:type plugin_name: str
:param plugin_name: name of the referred plugin.
:type config_dict: dict or metadict 
:param config_dict: The configuration used for running the tool. If is None, the default configuration will be stored, 
    this might be incomplete.
:type user: :class:`evaluation_system.model.user.User`
"""
    
    plugin_name = plugin_name.lower()
    if user is None: user = User()
    
    p = getPluginInstance(plugin_name, user)
    complete_conf = None
    if config_dict is None:
        conf_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(conf_file):
            log.debug('Loading config file %s', conf_file)
            with open(conf_file, 'r') as f:
                complete_conf = p.readConfiguration(f)
        else:
            log.debug('No config file was found in %s', conf_file)
    if complete_conf is None:
        #at this stage we want to resolve or tokens and perform some kind of sanity check before going further 
        complete_conf = p.setupConfiguration(config_dict=config_dict, recursion=True)
        
    
     
    log.debug('Running %s with %s', plugin_name, complete_conf)
    
    #In any case we have now a complete setup in complete_conf
    result = p._runTool(config_dict=complete_conf)
    
    if user: user.getUserDB().storeHistory(p, complete_conf, result=result)


def getHistory(plugin_name=None, limit=-1, since = None, until = None, entry_ids=None, user=None):
    """Returns the history from the given user.
This is just a wrapper for the defined db interface accessed via the user object.
See :class:`evaluation_system.model.db.UserDB.getHistory` for more information on this interface."""
    if plugin_name is not None: plugin_name = plugin_name.lower()
    if user is None: user = User()
    
    return user.getUserDB().getHistory(plugin_name, limit, since=since, until=until, entry_ids=entry_ids)


