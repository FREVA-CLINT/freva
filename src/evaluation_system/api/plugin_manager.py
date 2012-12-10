'''
Created on 23.11.2012

@author: estani
'''


#*** Initialize the plugin
import os
import sys
import evaluation_system.api.plugin as plugin
import logging
log = logging.getLogger(__name__)

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

def getPlugin(plugin_name):
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

def writeSetup(plugin_name, config_dict=None, user=None):
    """Writes the plugin setup to disk. This is the configuration for the plugin itself and not that
    of the tool. The plugin might not write anything to disk when running the tool and instead configure it
    from the command line, environmental variables or any other method.
    Parameters
    plugin_name:=name of the refered plugin (mandatory)
    config_dict:=config dict or metadict for seting up the configuration
        if None, the default configuration will be stored, this might be incomplete and thus might
        not be enough for triggereing the plugin.
    user:=`evaluation_system.model.user.User`
        The user for whom this will be run. If None, then the current user will be used.
    @return: The path to the written configuration file."""
    plugin_name = plugin_name.lower()
    if user is None:
        user = User()
    #make sure the required directory structure and data is in place
    user.prepareDir()
    
    conf_dir = user.getUserConfigDir(plugin_name, create=True)

    p = getPlugin(plugin_name)['plugin_class']()
    complete_conf = p.setupConfiguration(config_dict=config_dict, check_cfg=False) 
    conf_file = os.path.join(conf_dir,'%s.conf' % plugin_name)
    with open(conf_file, 'w') as f:
        p.saveConfiguration(f, config_dict=complete_conf)
    
    return conf_file

def runTool(plugin_name, config_dict=None, user=None):
    plugin_name = plugin_name.lower()
    if user is None:
        user = User()
    p = getPlugin(plugin_name)['plugin_class']()
    complete_conf = None
    if config_dict is None:
        conf_dir = user.getUserConfigDir(plugin_name)
        conf_file = os.path.join(conf_dir,'%s.conf' % plugin_name)
        if os.path.isfile(conf_file):
            log.debug('Loading config file %s', conf_file)
            with open(conf_file, 'r') as f:
                complete_conf = p.readConfiguration(f)
        else:
            log.debug('No config file was found in %s', conf_file)
    if complete_conf is None:
        complete_conf = p.setupConfiguration(config_dict=config_dict, check_cfg=False) 
    
    #In any case we have now a complete setup in complete_conf
    p.runTool(config_dict=complete_conf)


