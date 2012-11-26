'''
Created on 23.11.2012

@author: estani
'''

from evaluation_system.api import plugin
from evaluation_system import __plugin_modules__, __plugins__

class PluginManagerException(Exception):
    pass

#get the current directory
def getPulginModules():
    """Return a dictonary with all modules holding the plugins"""
    return __plugin_modules__

__plugins = None
def getPlugins():
    """Return a list of plugin dictionary holding the plugin classes and metadata about them"""
    global __plugins
    if __plugins is None:
        __plugins = {}
        for plugin_name, plugin_class in __plugins__.items():
            __plugins[plugin_name.lower()] = dict(name=plugin_name,
                               plugin_class=plugin_class,
                               version=plugin_class.__version__,
                               description=plugin_class.__short_description__)
    return __plugins

def getPlugin(plugin_name):
    """Return the requested plugin or raise an exception if not found."""
    plugin_name = plugin_name.lower()
    if plugin_name not in getPlugins(): raise PluginManagerException("No plugin named: %s" % plugin_name)
    
    return getPlugins()[plugin_name]