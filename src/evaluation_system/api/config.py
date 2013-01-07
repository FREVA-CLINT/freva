'''
Created on 07.01.2013

@author: estani

This packages handles the configuration of the system.
It defines a plugin like any other.
'''
import os
import logging
log = logging.getLogger(__name__)

from evaluation_system.api import plugin

DIRECTORY_STRUCTURE = type('Struct', (object,), dict(LOCAL='local', CENTRAL='central'))


#Some defaults in case nothing is defined
_DEFAULT_CONFIG_FILE = '~/.evaluation_system'
_DEFAULT_ENV_CONFIG_FILE = 'EVALUATION_SYSTEM_CONFIG_FILE'

#config options
BASE_DIR = 'base_dir'
BASE_DIR_LOCATION = 'base_dir_location'
DIRECTORY_STRUCTURE_TYPE = 'directory_structure_type'
CONFIG_FILE = 'config_file'

_PATH_OPTIONS = [BASE_DIR_LOCATION, CONFIG_FILE]

#prepare the config_metadict for the plugin
meta = plugin.metadict()
meta.put(BASE_DIR, 'evaluation_system', help='The name of the directory storing the evaluation system (output, configuration, etc)')
meta.put(BASE_DIR_LOCATION, '~', help='The location of the directory defined in %s .' % BASE_DIR
                                                + 'It will be used only when %s is set to %s' % (DIRECTORY_STRUCTURE_TYPE, DIRECTORY_STRUCTURE.CENTRAL))
meta.put(DIRECTORY_STRUCTURE_TYPE, DIRECTORY_STRUCTURE.LOCAL, help='''Defines how the directory structure is created:
    local := ~/<base_dir>/...
    central := <base_dir_location>/<base_dir>/<user>/...''')
meta.put(CONFIG_FILE, _DEFAULT_CONFIG_FILE, help='This value points to the system configuration file, which is just a symlink to the ' 
                                                + 'configuration stored in $system_dir. This value will not be stored in the configuration '
                                                + 'as it makes no sense. Use the environmental variable %s to set ' % _DEFAULT_ENV_CONFIG_FILE
                                                + 'when starting the system.')
class Configuration(plugin.PluginAbstract):
    '''This class is just a normal plugin that is used to handle the system configuration.'''
    __short_description__ = "Used to configure the evaluation system" 
    __version__ = (1,0,0)
    __config_metadict__ = meta.copy()   #this is required for the abstract class
    
    def __init__(self, *args, **kwargs):
        #Make sure we always start from scratch though.
        self.__config_metadict__ = meta.copy()

        #now check if we have a configuration file, and read the defaults from there
        config_file = os.environ.get(_DEFAULT_ENV_CONFIG_FILE, _DEFAULT_CONFIG_FILE)
        if os.path.isfile(config_file):
            with open(config_file, 'r') as fp:
                for key, value in self.readConfiguration(fp).items():
                    self.__config_metadict__[key] = value
                log.debug('Configuration loaded from %s', config_file)
        else:
            log.debug('No configuration file found in %s. Using default values.', config_file)

        self.__config_metadict__[CONFIG_FILE] = config_file
        super(Configuration, self).__init__(*args,**kwargs)

    def saveConfiguration(self, fp, config_dict=None):
        #get the config_file value and remove it from the config_dict since it's confusing if we store it
        #(it can't really be used)
        config_file = None
        if config_dict:
            config_file = config_dict.pop('config_file', None)
        if config_file is None:
            config_file = self.__config_metadict__['config_file']

        #store the configuration as usual
        super(Configuration, self).saveConfiguration(fp, config_dict)
        path = fp.name
        if os.path.islink(config_file):
            #allow the link to be recreated
            os.unlink(config_file)
        try:
            os.symlink(path, config_file)
            print "Configuration file linked at %s" % config_file
        except OSError as e:
            if e.errno == 2:
                log.error("Please create the required directory %s if that's where you want the configuration file to be stored.", os.path.dirname(config_file))
            else:
                log.error("Could not create the required symlink %s pointing to %s", config_file, path)
            raise
        
    def runTool(self, config_dict=None):
        print "Showing current configuration:"
        print self.getCurrentConfig(config_dict=config_dict)

class ConfigurationException(Exception):
    """Mark exceptions thrown in this package"""
    pass

_config = Configuration().setupConfiguration()
_nothing = object()

def get(config_prop, default=_nothing):
    """Returns the value stored for the given config_prop.
    If the config_prop is not found and no default value is provided an exception
    will be thrown. If not the default value is returned.
    Parameters:
    config_prop: string
        property for which it's value is looked for
    default: anything
        If property is not found this value is returned
    @return the value associated with the given property, the default one if not found or an
    exception is thrown if no default is provided.
    """
        
    if config_prop in _config:
        value = _config[config_prop]
    elif default != _nothing:
        value = default
    else:
        raise ConfigurationException("No configuration for %s" % config_prop)
    
    if value and config_prop in _PATH_OPTIONS:
        return os.path.expanduser(value)
    else:
        return value

def keys():
    """Returns all configured keys"""
    return _config.keys()

def reloadConfiguration():
    global _config
    _config = Configuration().setupConfiguration()