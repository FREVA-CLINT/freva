'''
Created on 23.11.2012

@author: estani
'''


#*** Initialize the plugin
import os
import sys
import evaluation_system.api.plugin as plugin

#get the tools directory from the current one
tools_dir = os.path.join(os.path.abspath(__file__)[:-len('src/evaluation_system/__init__.py')-1],'tools')
#all plugins modules will be dynamically loaded here.
__plugin_modules__ = {}
"""Dictionary of modules holding the plugins"""
__plugins__ = {}
"""Dictionary of plugins"""

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

#This only runs once after start. To load new plugins on the fly we have 2 possibilities
#1) Watch the tool directory
#2) Use the plugin metaclass trigger (see `evaluation_system.api.plugin`


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


