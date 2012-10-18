'''
Created on 04.10.2012

@author: estani
'''
import pwd
import os

class User(object):
    BASE_DIR = 'ESM'
    TOOL_DIR = os.path.join(BASE_DIR,'tools')
    
    '''
    This Class encapsulates a user (configurations, etc)
    '''


    def __init__(self, uid = None):
        '''
        Constructor for the current user.
        '''
        if uid is None: uid = os.getuid()
        self._userdata = pwd.getpwuid(uid)
        
    def getName(self):  return self._userdata.pw_name
    def getUserID(self):  return self._userdata.pw_uid
    def getUserHome(self):  return self._userdata.pw_dir
    def getUserConfigDir(self): return os.path.join(self.getUserHome(), User.BASE_DIR)
    def getUserToolConfigDir(self, tool = None):
        if tool is None:
            #return the directory where the tool configuration files are stored
            return os.path.join(self.getUserHome(), User.TOOL_DIR)
        else:
            #return the specific directory for the given tool            
            return os.path.join(self.getUserHome(), User.TOOL_DIR, tool)
    
    def prepareDir(self):
        """Prepares the configuration directory for this user if it's not already been done."""
        if os.path.isdir(self.getUserConfigDir()): return
        if not os.path.isdir(self.getUserHome()):
            raise Exception("Can't create configuration, user HOME doesn't exist (%s)" % self.getUserHome())
        os.mkdir(self.getUserConfigDir())
        
        #os.mkdir(self.getUserToolConfigDir())
        