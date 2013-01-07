'''
Created on 07.01.2013

@author: estani
'''
import os
import unittest
from evaluation_system.api import config
import logging
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

class Test(unittest.TestCase):
    
    def setUp(self):
        if config._DEFAULT_ENV_CONFIG_FILE in os.environ:
            del os.environ[config._DEFAULT_ENV_CONFIG_FILE]
        config.reloadConfiguration()


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
        base_dir = config.get(config.BASE_DIR)
        self.assertEquals(base_dir, 'evaluation_system')
        self.failUnlessRaises(config.ConfigurationException, config.get, 'non-existing-key')
        self.assertEquals(config.get('non-existing-key', 'default-answer'), 'default-answer')
    
    def testKeys(self):
        keys = config.keys()
        self.assertTrue(len(keys) >= 2)
        self.assertTrue(config.BASE_DIR in keys)
        self.assertTrue(config.CONFIG_FILE in keys)
        
    def testReload(self):
        """Test we can reload the configuration"""
        c1 = config.get(config.CONFIG_FILE)
        self.assertEquals(c1, os.path.expanduser(config._DEFAULT_CONFIG_FILE))
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = '/tmp'
        c2 = config.get(config.CONFIG_FILE)
        self.assertEquals(c1, c2)
        config.reloadConfiguration()
        c3 = config.get(config.CONFIG_FILE)
        self.assertNotEquals(c2, c3)
        self.assertEquals(c3, '/tmp')
        
    def testConfigFile(self):
        """If a config file is provided it should be read"""
        import tempfile
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write('[Configuration]\n%s=nowhere\n' % config.BASE_DIR)
        
        self.assertEquals(config.get(config.BASE_DIR), 'evaluation_system')
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        config.reloadConfiguration()
        self.assertEquals(config.get(config.BASE_DIR), 'nowhere')
        os.unlink(name)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testPlugin']
    unittest.main()