'''
Created on 17.5.2016

@author: Sebastian Illing
'''
import unittest
import subprocess
import os
import tempfile
import shutil

from evaluation_system.model.user import User
from evaluation_system.tests.mocks.dummy import DummyUser
from evaluation_system.misc import config

                
class Test(unittest.TestCase):
    """Test the User construct used for managing the configuratio of a user"""
    DUMMY_USER = {'pw_name':'someone'}

    def setUp(self):
        os.environ['EVALUATION_SYSTEM_CONFIG_FILE'] = os.path.dirname(__file__) + '/test.conf'
        self.user = DummyUser(random_home=True, **Test.DUMMY_USER)

    def tearDown(self):
        self.user.cleanRandomHome()
    
    def testd_ummy_user(self):
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
        
        d_user.cleanRandomHome()

    def test_getters(self):
        """Test the object creation and some basic return functions"""
        self.assertEqual(Test.DUMMY_USER['pw_name'], self.user.getName())
        self.assertTrue(self.user.getUserHome().startswith(tempfile.gettempdir()))
        self.assertEqual(int(Test.runCmd('id -u')), self.user.getUserID())
        
        db = self.user.getUserDB();
        self.assertTrue(db is not None)
        baseDir = '/'.join([self.user.getUserHome(), config.get(config.BASE_DIR)])
        self.assertEqual(baseDir, self.user.getUserBaseDir())
        tool1_cnfDir = os.path.join(baseDir, User.CONFIG_DIR, 'tool1')
        tool1_chDir = os.path.join(baseDir, User.CACHE_DIR, 'tool1')
        tool1_outDir = os.path.join(baseDir, User.OUTPUT_DIR, 'tool1')
        tool1_plotDir = os.path.join(baseDir, User.PLOTS_DIR, 'tool1')
        
        self.assertEqual(self.user.getUserScratch(),
                         '/tmp/scratch/%s' % self.user.getName())
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
        
    def test_directory_creation(self):
        """
        This tests assures we always know what is being created 
        in the framework directory
        """
        #assure we have a temp directory as HOME for testing
        testUserDir = tempfile.mkdtemp('_es_userdir')
        testUser = DummyUser(pw_dir=testUserDir)
        #assure we have a home directory setup
        self.assertTrue(os.path.isdir(testUser.getUserHome()))
        
        baseDir = testUser.getUserBaseDir()
        
        #check home is completely created
        #self.assertFalse(os.path.isdir(baseDir)) Basic dir structure is created when running a tool because of
        #history, so this doesn't apply anymore
        
        testUser.prepareDir()
        self.assertTrue(os.path.isdir(baseDir))
        print "Test user config dir in: ", testUser.getUserBaseDir()
        
        created_dirs = [testUser.getUserConfigDir(), testUser.getUserCacheDir(), 
                        testUser.getUserOutputDir(), testUser.getUserPlotsDir()]
        print created_dirs
        for directory in created_dirs:
            self.assertTrue(os.path.isdir(directory))
 
        
    def test_directory_creation2(self):
        testUser = self.user
        #assure we have a home directory setup
        self.assertTrue(os.path.isdir(testUser.getUserHome()))
        
        dir1 = testUser.getUserConfigDir('test_tool')
        print dir1
        self.assertFalse(os.path.isdir(dir1))
        dir2 = testUser.getUserConfigDir('test_tool', create=True)
        self.assertEquals(dir1, dir2)
        self.assertTrue(os.path.isdir(dir1))
    
    def test_central_directory_Creation(self):
        tmp_dir = tempfile.mkdtemp(__name__)
        config._config[config.BASE_DIR_LOCATION] = tmp_dir
        config._config[config.DIRECTORY_STRUCTURE_TYPE] = config.DIRECTORY_STRUCTURE.CENTRAL
        testUser = DummyUser(random_home=False,  **Test.DUMMY_USER)
        
        dir1 = testUser.getUserBaseDir()
        self.assertEquals(dir1, os.path.join(config.get(config.BASE_DIR_LOCATION), config.get(config.BASE_DIR), str(testUser.getName())))
        dir2 = testUser.getUserOutputDir('sometool')
        self.assertEquals(dir2, 
                          os.path.join(config.get(config.BASE_DIR_LOCATION), config.get(config.BASE_DIR), 
                                       str(testUser.getName()),User.OUTPUT_DIR, 'sometool'))
        print dir2
        
        config.reloadConfiguration()
        
        if os.path.isdir(tmp_dir) and tmp_dir.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % tmp_dir
            shutil.rmtree(tmp_dir)

        
    def test_config_file(self):
        tool = 'test_tool'
        self.assertEquals(self.user.getUserConfigDir(tool) + '/%s.conf' % tool, self.user.getUserToolConfig(tool))
    
    @staticmethod
    def runCmd(cmd):
        if isinstance(cmd, basestring): cmd = cmd.split()        
        return subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testCreation']
    unittest.main()