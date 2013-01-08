'''
Created on 07.01.2013

@author: estani
'''
import os
import logging
from ConfigParser import SafeConfigParser
log = logging.getLogger(__name__)


DIRECTORY_STRUCTURE = type('Struct', (object,), dict(LOCAL='local', CENTRAL='central'))
'''Type of directory structure:
   local := ~/<base_dir>/...
   central := <base_dir_location>/<base_dir>/<user>/...'''

#Some defaults in case nothing is defined
_DEFAULT_ENV_CONFIG_FILE = 'EVALUATION_SYSTEM_CONFIG_FILE'

#config options
BASE_DIR = 'base_dir'
'The name of the directory storing the evaluation system (output, configuration, etc)'

DIRECTORY_STRUCTURE_TYPE = 'directory_structure_type'
'''Defines which directory structure is going to be used. See DIRECTORY_STRUCTURE'''

BASE_DIR_LOCATION = 'base_dir_location'
'''The location of the directory defined in $base_dir.'''

#config file section
CONFIG_SECTION_NAME = 'evaluation_system'
'This is the name of the section in the configuration file where the configuration is being stored'

class ConfigurationException(Exception):
    """Mark exceptions thrown in this package"""
    pass

_config = None
def reloadConfiguration():
    global _config
    _config = { BASE_DIR:'evaluation_system',
                 BASE_DIR_LOCATION: os.path.expanduser('~'),
                 DIRECTORY_STRUCTURE_TYPE: DIRECTORY_STRUCTURE.LOCAL}
    
    #now check if we have a configuration file, and read the defaults from there
    config_file = os.environ.get(_DEFAULT_ENV_CONFIG_FILE, None)
    if config_file and os.path.isfile(config_file):
        config_parser = SafeConfigParser()
        with open(config_file, 'r') as fp:
            config_parser.readfp(fp)
            if not config_parser.has_section(CONFIG_SECTION_NAME):
                raise ConfigurationException("Configuration file is missing section %s.\n"
                    + "For Example:\n[%s]\nprop=value\n...", CONFIG_SECTION_NAME, CONFIG_SECTION_NAME)
            else:
                _config.update(config_parser.items(CONFIG_SECTION_NAME))
            log.debug('Configuration loaded from %s', config_file)
    else:
        log.debug('No configuration file found in %s. Using default values.', config_file)

#load the configuration for the first time
reloadConfiguration()

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
        return _config[config_prop]
    elif default != _nothing:
        return default
    else:
        raise ConfigurationException("No configuration for %s" % config_prop)

def keys():
    """Returns all configured keys"""
    return _config.keys()
