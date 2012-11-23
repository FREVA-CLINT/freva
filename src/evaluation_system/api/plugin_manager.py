'''
Created on 23.11.2012

@author: estani
'''

from evaluation_system.api import plugin
from evaluation_system import __plugin_modules__, __plugins__


#get the current directory
def getPulginModules():
    return __plugin_modules__

def getPlugins():
    result = []
    for plugin_name, plugin_class in __plugins__.items():
        result.append(dict(name=plugin_name,
                           plugin_class=plugin_class,
                           version=plugin_class.__version__,
                           description=plugin_class.__short_description__))
    return result
        