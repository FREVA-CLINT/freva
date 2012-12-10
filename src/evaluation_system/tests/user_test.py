'''
Created on 04.10.2012

@author: estani
'''
import unittest
from evaluation_system.model.user import User
import subprocess
import os
import tempfile
import shutil

class DummyUser(User):
    """Create a dummy User object that allows testing"""
    def __init__(self, random_home=False, **override):
        if random_home:
            if 'pw_dir' in override:
                raise Exception("Can't define random_home and provide a home directory")
            override['pw_dir'] = tempfile.mkdtemp('_es_userdir')
            
        User.__init__(self)
        
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
    DUMMY_USER = {'pw_name':'someone'}

    def setUp(self):
        self.user = DummyUser(random_home=True, **Test.DUMMY_USER)

    def tearDown(self):
        home = self.user.getUserHome()
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)
    
    def testDummyUser(self):
        """Be sure the dummy user is created as expected"""
        dummy_name='non-existing name'
        
        self.failUnlessRaises(Exception, DummyUser, random_home=True, pw_dir='anything')
        
        d_user = DummyUser(random_home=True, pw_name=dummy_name)
        #populate the test directory as required
        d_user.prepareDir()
        self.assertEqual(dummy_name, d_user.getName())
        cfg_file = os.path.join(d_user.getUserBaseDir(), User.EVAL_SYS_CONFIG)

        #check configuration file writing
        self.assertFalse(os.path.isfile(cfg_file))
        cnfg = d_user.getUserConfig()
        cnfg.add_section("test_section")
        cnfg.set("test_section", 'some_key', 'a text value\nwith many\nlines!')
        d_user.writeConfig()
        self.assertTrue(os.path.isfile(cfg_file))
        fp = open(cfg_file, 'r')
        print fp.read()
        fp.close()
        
        #check configuration file reading
        fp = open(cfg_file, 'w')
        ##Note multi line values in the configuration file need to be indented...
        fp.write("[test2]\nkey1 = 42\nkey2=Some\n\tmany\n\tlines=2\nkey3=%(key1)s0\n")
        fp.close()
        cnfg = d_user.reloadConfig()
        self.assertTrue(cnfg.getint('test2', 'key1') == 42)
        #...but the indentation disappears when returned directly
        self.assertTrue(cnfg.get('test2', 'key2') == 'Some\nmany\nlines=2')
        self.assertTrue(cnfg.getint('test2', 'key3') == 420)
        
        home = d_user.getUserHome()
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            shutil.rmtree(home)
        
        

    def testGetters(self):
        """Test the object creation and some basic return functions"""
        self.assertEqual(Test.DUMMY_USER['pw_name'], self.user.getName())
        self.assertTrue(self.user.getUserHome().startswith(tempfile.gettempdir()))
        self.assertEqual(int(Test.runCmd('id -u')), self.user.getUserID())
        
        db = self.user.getUserDB();
        self.assertTrue(db is not None)
        baseDir = '/'.join([self.user.getUserHome(), User.BASE_DIR])
        self.assertEqual(baseDir, self.user.getUserBaseDir())
        tool1_cnfDir = os.path.join(baseDir, User.CONFIG_DIR, 'tool1')
        tool1_chDir = os.path.join(baseDir, User.CACHE_DIR, 'tool1')
        tool1_outDir = os.path.join(baseDir, User.OUTPUT_DIR, 'tool1')
        tool1_plotDir = os.path.join(baseDir, User.PLOTS_DIR, 'tool1')
        
        #check we get the configuration directory of the given tool
        self.assertEqual(tool1_cnfDir, self.user.getUserConfigDir('tool1'))
        self.assertEqual(tool1_chDir, self.user.getUserCacheDir('tool1'))
        self.assertEqual(tool1_outDir, self.user.getUserOutputDir('tool1'))
        self.assertEqual(tool1_plotDir, self.user.getUserPlotsDir('tool1'))
        #check we get the general directory of the tools (should be the parent of the previous one)
        self.assertEqual(os.path.dirname(tool1_cnfDir), self.user.getUserConfigDir())
        self.assertEqual(os.path.dirname(tool1_chDir), self.user.getUserCacheDir())
        self.assertEqual(os.path.dirname(tool1_outDir), self.user.getUserOutputDir())
        self.assertEqual(os.path.dirname(tool1_plotDir), self.user.getUserPlotsDir())
        
    def testDirectoryCreation(self):
        """This tests assures we always knows what is being created in the framework directory"""
        #assure we have a temp directory as HOME for testing
        testUserDir = tempfile.mkdtemp('_es_userdir')
        testUser = DummyUser(pw_dir=testUserDir)
        #assure we have a home directory setup
        self.assertTrue(os.path.isdir(testUser.getUserHome()))
        
        baseDir = testUser.getUserBaseDir()
        
        #check home is created
        self.assertFalse(os.path.isdir(baseDir))
        testUser.prepareDir()
        self.assertTrue(os.path.isdir(baseDir))
        print "Test user config dir in: ", testUser.getUserBaseDir()
        
        created_dirs = [testUser.getUserConfigDir(), testUser.getUserCacheDir(), 
                        testUser.getUserOutputDir(), testUser.getUserPlotsDir()]
        for directory in created_dirs:
            self.assertTrue(os.path.isdir(directory))
            os.rmdir(directory)

        #clean everything up
        os.rmdir(testUser.getUserBaseDir())
        self.assertFalse(os.path.isdir(baseDir))
        os.rmdir(testUserDir)
        self.assertFalse(os.path.isdir(testUserDir))
        
    def testDirectoryCreation2(self):
        testUser = self.user
        #assure we have a home directory setup
        self.assertTrue(os.path.isdir(testUser.getUserHome()))
        
        dir1 = testUser.getUserConfigDir('test_tool')
        print dir1
        self.assertFalse(os.path.isdir(dir1))
        dir2 = testUser.getUserConfigDir('test_tool', create=True)
        self.assertEquals(dir1, dir2)
        self.assertTrue(os.path.isdir(dir1))
        
        
    @staticmethod
    def runCmd(cmd):
        if isinstance(cmd, basestring): cmd = cmd.split()        
        return subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testCreation']
    unittest.main()