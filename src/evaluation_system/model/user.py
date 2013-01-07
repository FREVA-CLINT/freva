'''
Created on 04.10.2012

@author: estani
'''
import pwd
import os
import sys
from ConfigParser import SafeConfigParser as Config
from evaluation_system.model.db import UserDB
from evaluation_system.api import config

class User(object):
    '''
    This Class encapsulates a user (configurations, etc).
    '''
    
    CONFIG_DIR = 'config'
    CACHE_DIR = 'cache'
    OUTPUT_DIR = 'output'
    PLOTS_DIR = 'plots'
    
    
    EVAL_SYS_CONFIG = os.path.join(CONFIG_DIR,'evaluation_system.config')
    EVAL_SYS_DEFAULT_CONFIG = os.path.normpath(os.path.dirname(sys.modules[__name__].__file__)+'/../../etc/system_default.config')


    def __init__(self, uid = None):
        '''
        Parameters:
        uid: int (optional)
            user id in the local system, if not provided the current user is used.
        
        '''
        self._dir_type = config.get(config.DIRECTORY_STRUCTURE_TYPE)

        if uid is None: uid = os.getuid()
        self._userdata = pwd.getpwuid(uid)
        self._userconfig = Config()
        #try to load teh configuration from the very first time.
        self._userconfig.read([User.EVAL_SYS_DEFAULT_CONFIG, os.path.join(self._userdata.pw_dir, User.EVAL_SYS_CONFIG)])
        
        self._db = UserDB(self)
        
    def getUserConfig(self):
        """Returns user configuration object (ConfigParser)"""
        return self._userconfig
    
    def getUserDB(self):
        """Returns the db abstraction for this user"""
        return self._db
        
    def reloadConfig(self):
        """Reloads user configuration from disk"""
        self._userconfig = Config()
        self._userconfig.read([User.EVAL_SYS_DEFAULT_CONFIG, os.path.join(self.getUserBaseDir(), User.EVAL_SYS_CONFIG)])
        return self._userconfig
    
    def writeConfig(self):
        """Writes user configuration to disk according to User.EVAL_SYS_CONFIG"""
        
        fp = open(os.path.join(self.getUserBaseDir(), User.EVAL_SYS_CONFIG), 'w')
        self._userconfig.write(fp)
        fp.close()
        
    def getName(self):  return self._userdata.pw_name
    def getUserID(self):  return self._userdata.pw_uid
    def getUserHome(self):  return self._userdata.pw_dir
    
    def _getUserBaseDir(self):
        if self._dir_type == config.DIRECTORY_STRUCTURE.LOCAL:
            return os.path.join(self.getUserHome(), config.get(config.BASE_DIR))
        elif self._dir_type == config.DIRECTORY_STRUCTURE.CENTRAL:
            return os.path.join(config.get(config.BASE_DIR_LOCATION), config.get(config.BASE_DIR), str(self.getUserID()))
        
    def _getUserDir(self, dir_type, tool = None, create=False):
        base_dir = dict(base='', config=User.CONFIG_DIR, cache=User.CACHE_DIR, output=User.OUTPUT_DIR, plots=User.PLOTS_DIR)
        if tool is None:
            #return the directory where the tool configuration files are stored
            dir_name = os.path.join(self._getUserBaseDir(), base_dir[dir_type])
        else:
            #return the specific directory for the given tool            
            dir_name =  os.path.join(self._getUserBaseDir(), base_dir[dir_type], tool)
        
        #make sure we have a canonical path
        dir_name = os.path.abspath(dir_name)
        
        if create and not os.path.isdir(dir_name):
            #we are letting this fail in case of problems.
            os.makedirs(dir_name)
            
        return dir_name

    def getUserBaseDir(self, **kwargs): 
        """Return directory where all configurations for this user are stored"""
        #return os.path.join(self.getUserHome(), User.BASE_DIR)
        return self._getUserDir('base', **kwargs)
        
    def getUserToolConfig(self, tool = None, **kwargs):
        """Return directory where all configurations for this user are stored"""
        config_dir = self._getUserDir('config', tool, **kwargs)
        return os.path.join(config_dir,'%s.conf' % tool)

    def getUserConfigDir(self, tool = None, **kwargs):
        """Return directory where all configurations for this user are stored"""
        return self._getUserDir('config', tool, **kwargs)
    
    def getUserCacheDir(self, tool = None, **kwargs):
        """Return directory where cache files for this user (might not be "only" for this user though)"""
        return self._getUserDir('cache', tool, **kwargs)
    
    def getUserOutputDir(self, tool = None, **kwargs):
        """Return directory where output data for this user is stored"""
        return self._getUserDir('output', tool, **kwargs)
    
    def getUserPlotsDir(self, tool = None, **kwargs):
        """Return directory where all plots for this user are stored"""
        return self._getUserDir('plots', tool, **kwargs)
    
    def prepareDir(self):
        """Prepares the configuration directory for this user if it's not already been done."""
        if os.path.isdir(self.getUserBaseDir()):
            #we assume preparation was succesfull... but we might to be sure though... 
            #return
            pass
        
        if not os.path.isdir(self.getUserHome()):
            raise Exception("Can't create configuration, user HOME doesn't exist (%s)" % self.getUserHome())
        
        #create directory for the framework
        
        
        #create all required subdirectories
        dir_creators = [self.getUserBaseDir, self.getUserConfigDir, self.getUserCacheDir, self.getUserOutputDir, self.getUserPlotsDir]
        for f in dir_creators:
            f(create=True)
        
