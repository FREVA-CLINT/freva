'''
Created on 07.01.2013

@author: estani
'''
import os
import unittest
from evaluation_system.api import config 

class Test(unittest.TestCase):


    def testConfigPlugin(self):
        c = config.Configuration()
        conf = c.setupConfiguration()
        self.assertTrue(conf is not None)
        self.assertEquals(conf, c.__config_metadict__)
        self.assertEquals(conf[config.BASE_DIR], 'evaluation_system')
        self.assertEquals(conf[config.CONFIG_FILE], config._DEFAULT_CONFIG_FILE)
        
        #check the environmental variable is being read.
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = '/tmp'
        conf = config.Configuration().setupConfiguration()
        self.assertEquals(conf[config.CONFIG_FILE], '/tmp')
        
    def testGet(self):
        sys_dir = config.get(config.BASE_DIR)
        self.assertEquals(sys_dir, 'evaluation_system')
        self.failUnlessRaises(config.ConfigurationException, config.get, 'non-existing-key')
        self.assertEquals(config.get('non-existing-key', 'default-answer'), 'default-answer')
    
    def testKeys(self):
        keys = config.keys()
        self.assertTrue(len(keys) >= 2)
        self.assertTrue(config.BASE_DIR in keys)
        self.assertTrue(config.CONFIG_FILE in keys)
        
    def testReload(self):
        c1 = config.get(config.CONFIG_FILE)
        self.assertEquals(c1, config._DEFAULT_CONFIG_FILE)
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = '/tmp'
        c2 = config.get(config.CONFIG_FILE)
        self.assertEquals(c1, c2)
        config.reloadConfiguration()
        c3 = config.get(config.CONFIG_FILE)
        self.assertNotEquals(c2, c3)
        self.assertEquals(c3, '/tmp')

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testPlugin']
    unittest.main()