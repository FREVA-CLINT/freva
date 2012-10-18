'''
Created on 04.10.2012

@author: estani
'''
import unittest
import model.user as user
import subprocess
import os

class DummyUser(user.User):
    """Create a dummy User object that allows testing"""
    def __init__(self, **override):
        user.User.__init__(self)
        
        class DummyUserData(list):
            """Override a normal list and make it work like the pwd read-only struct"""
            _NAMES = 'pw_name pw_passwd pw_uid pw_gid pw_gecos pw_dir pw_shell'.split()
            def __init__(self, arr_list):
                list.__init__(self, arr_list)
            def __getattribute__(self, name):
                #don't access any internal variable (avoid recursion!)
                if name[0] != '_' and name in self._NAMES:
                    return self[self._NAMES.index(name)]
                return list.__getattribute__(self, name)
                    
        
        #copy the current data
        user_data = list(self._userdata[:])
        for key, value in override.items():
            if key in DummyUserData._NAMES:
                user_data[DummyUserData._NAMES.index(key)] = value
        self._userdata = DummyUserData(user_data)
                
        

                    
class Test(unittest.TestCase):
    """Test the User construct used for managing the configuratio of a user"""
    DUMMY_USER = {'pw_dir':'/tmp/test_user', 'pw_name':'someone'}

    def setUp(self):
        self.user = DummyUser(**Test.DUMMY_USER)

    def tearDown(self):
        pass
    
    def testDummyUser(self):
        """Be sure the dummy user is created as expected"""
        dummy_name='non-existing name'
        d_user = DummyUser(pw_name=dummy_name)
        self.assertEqual(dummy_name,d_user.getName())

    def testGetters(self):
        """Test the object creation and some basic return functions"""
        self.assertEqual(Test.DUMMY_USER['pw_name'], self.user.getName())
        self.assertEqual(Test.DUMMY_USER['pw_dir'], self.user.getUserHome())
        self.assertEqual(int(Test.runCmd('id -u')), self.user.getUserID())
        configDir = '/'.join([self.user.getUserHome(), user.User.BASE_DIR])
        self.assertEqual(configDir, self.user.getUserConfigDir())
        tool1Dir = '/'.join([self.user.getUserHome(), user.User.TOOL_DIR, 'tool1'])
        #check we get the configuration directory of the given tool
        self.assertEqual(tool1Dir, self.user.getUserToolConfigDir('tool1'))
        #check we get the general directory of the tools (should be the parent of the previous one)
        self.assertEqual(os.path.dirname(tool1Dir), self.user.getUserToolConfigDir(None))
        
    def testDirectoryCreation(self):
        #assure we have a temp directory as HOME for testing
        try: 
            os.mkdir(self.user.getUserHome())
        except: 
            pass
        configDir = self.user.getUserConfigDir()
        
        self.assertFalse(os.path.isdir(configDir))
        self.user.prepareDir()
        self.assertTrue(os.path.isdir(configDir))
        print self.user.getUserConfigDir()
        os.rmdir(self.user.getUserConfigDir())
        self.assertFalse(os.path.isdir(configDir))
        
        
    @staticmethod
    def runCmd(cmd):
        if isinstance(cmd, basestring): cmd = cmd.split()        
        return subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testCreation']
    unittest.main()