'''
Created on 23.11.2012

@author: estani
'''


#*** Initialize the plugin
import os
import sys
import logging
log = logging.getLogger(__name__)

import evaluation_system.api.plugin as plugin
import evaluation_system.model.db as db

#get the tools directory from the current one
tools_dir = os.path.join(os.path.abspath(__file__)[:-len('src/evaluation_system/api/plugin_manager.py')-1],'tools')
#all plugins modules will be dynamically loaded here.
__plugin_modules__ = {}
"""Dictionary of modules holding the plugins"""
__plugins__ = {}
"""Dictionary of plugins class_name=>class)"""
__plugins_meta = {}
"""Dictionary of plugins with more information 
plugin_name=>{
    name=>plugin_name,
    plugin_class=>class,
    version=>(0,0,0)
    description=>"string"}"""
 

def reloadPulgins():
    #get all modules from the tool directory
    for plugin_imp in os.listdir(tools_dir):
        if not plugin_imp.startswith('.'):
            #check if api available
            int_dir = os.path.join(tools_dir,plugin_imp,'integration') 
            if os.path.isdir(int_dir):
                #we have a plugin_imp with defined api
                sys.path.append(int_dir)
                __plugin_modules__[plugin_imp] = __import__(plugin_imp + '.api')
    
    #load all plugin classes found (they are loaded when loading the modules)
    for plug_class in plugin.PluginAbstract.__subclasses__():
        __plugins__[plug_class.__name__] = plug_class

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

from evaluation_system.model.user import User

class PluginManagerException(Exception):
    pass

#get the current directory
def getPulginModules():
    """Return a dictonary with all modules holding the plugins"""
    return __plugin_modules__


def getPlugins():
    """Return a list of plugin dictionary holding the plugin classes and metadata about them"""
    return __plugins_meta

def getPluginDict(plugin_name):
    """Return the requested plugin dictionary entry or raise an exception if not found.
    Parameters
    plugin_name:=string
        Name of the plugin to search for.
    @return: a dictionary with information on the plugin 
            {name=>plugin_name,
            plugin_class=>class,
            version=>(0,0,0)
            description=>"string"}"""
    plugin_name = plugin_name.lower()
    if plugin_name not in getPlugins(): raise PluginManagerException("No plugin named: %s" % plugin_name)
    
    return getPlugins()[plugin_name]

def getPluginInstance(plugin_name):
    """Return an instance of the requested plugin or raise an exception if not found.
    Parameters
    plugin_name:=string
        Name of the plugin to search for.
    @return: an instance of the plugin. Might not be unique"""
    #in case we want to cache the creation of the plugin classes.
    return getPluginDict(plugin_name)['plugin_class']()

def parseArguments(plugin_name, arguments, use_user_defaults=False, user=None, config_file=None):
    """Passes an array of string arguments to the plugin for parsing.
    Parameters
    plugin_name:=string
        Name of the plugin to search for.
    arguments:=[string]
        Array of strings that will be parsed by the plugin (see `evaluation_system.api.plugin.parseArguments`)
    use_user_defaults:=bool
        If the set tu True and a user configuration is found, it will be used as default for all non set arguments.
        So the value will be set according to the first found instance in this order: argument, user default, tool default
    user:=`evaluation_system.model.user.User`
        The user defining the defaults.
    config_file:=string
        path to a file where the setup will be stored. If None, the default user dependent one will be used.
    @return: A dictionary with the configuration"""
    plugin_name = plugin_name.lower()
    
    p = getPluginInstance(plugin_name)
    complete_conf = {}
    if use_user_defaults:
        if config_file is None:
            if user is None:
                user = User()
            config_file = user.getUserToolConfig(plugin_name)
        if os.path.isfile(config_file):
            with open(config_file, 'r') as f:
                complete_conf = p.readConfiguration(f)
    
    #update with user defaults if desired
    complete_conf.update(p.parseArguments(arguments))
    
    return complete_conf

def writeSetup(plugin_name, config_dict=None, user=None, config_file=None):
    """Writes the plugin setup to disk. This is the configuration for the plugin itself and not that
    of the tool. The plugin might not write anything to disk when running the tool and instead configure it
    from the command line, environmental variables or any other method.
    Parameters
    plugin_name:=name of the referred plugin (mandatory)
    config_dict:=config dict or metadict for seting up the configuration
        if None, the default configuration will be stored, this might be incomplete and thus might
        not be enough for triggering the plugin.
    user:=`evaluation_system.model.user.User`
        The user for whom this will be run. If None, then the current user will be used.
    config_file:=string
        path to a file where the setup will be stored. If None, the default user dependent one will be used.
    @return: The path to the written configuration file."""
    plugin_name = plugin_name.lower()
    p = getPluginInstance(plugin_name)
    complete_conf = p.setupConfiguration(config_dict=config_dict, check_cfg=False, recursion=False)
    
    if config_file is None:
        if user is None:
            user = User()
        #make sure the required directory structure and data is in place
        user.prepareDir()
         
        config_file = user.getUserToolConfig(plugin_name, create=True)
        
    with open(config_file, 'w') as f:
        p.saveConfiguration(f, config_dict=complete_conf)
    
    return config_file

def runTool(plugin_name, config_dict=None, user=None):
    """Runs a tool.
    Parameters
    plugin_name:=name of the referred plugin (mandatory)
    config_dict:=config dict or metadict for seting up the configuration
        if None, the default configuration will be stored, this might be incomplete and thus might
        not be enough for triggering the plugin.
    user:=`evaluation_system.model.user.User`
        The user for whom this will be run. If None, then the current user will be used.
    @return: The path to the written configuration file."""
    
    plugin_name = plugin_name.lower()
    if user is None:
        user = User()
    p = getPluginInstance(plugin_name)
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
    result = p.runTool(config_dict=complete_conf)
    
    if user: user.getUserDB().storeHistory(p, complete_conf, result=result)


def getHistory(plugin_name=None, limit=-1, days_span = None, entry_ids=None, user=None):
    """Returns the history from the given user
    This is just a wrapper for the defined db interface accessed via the user object
    See `evaluation_system.model.db.UserDB.getHistory`"""
    if plugin_name is not None: plugin_name = plugin_name.lower()
    if user is None: user = User()
    
    return user.getUserDB().getHistory(plugin_name, limit, days_span=days_span, entry_ids=entry_ids)


