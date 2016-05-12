'''
Created on 12.05.2016

@author: Sebastian Illing
'''
import os
import unittest
from evaluation_system.misc import config
import logging
from evaluation_system.misc.config import (ConfigurationException,
                                           reloadConfiguration)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.DEBUG)

class Test(unittest.TestCase):
    
    def tearDown(self):
        if config._DEFAULT_ENV_CONFIG_FILE in os.environ:
            del os.environ[config._DEFAULT_ENV_CONFIG_FILE]
        config.reloadConfiguration()


    def test_get(self):
        base_dir = config.get(config.BASE_DIR)
        self.assertEquals(base_dir, 'evaluation_system')
        self.failUnlessRaises(config.ConfigurationException,
                              config.get, 'non-existing-key')
        self.assertEquals(config.get('non-existing-key',
                                     'default-answer'), 'default-answer')
    
    def test_keys(self):
        keys = config.keys()
        self.assertTrue(len(keys) >= 2)
        self.assertTrue(config.BASE_DIR in keys)
        
    def test_reload(self):
        """Test we can reload the configuration"""
        config._config[config.BASE_DIR_LOCATION] = 'TEST'
        c1 = config.get(config.BASE_DIR_LOCATION)
        self.assertEquals(c1, 'TEST')
        config.reloadConfiguration()
        c2 = config.get(config.BASE_DIR_LOCATION)
        self.assertNotEquals(c1, c2)
        
    def test_DIRECTORY_STRUCTURE(self):
        self.assertTrue(config.DIRECTORY_STRUCTURE.validate('local'))
        self.assertTrue(config.DIRECTORY_STRUCTURE.validate('central'))
        self.assertFalse(config.DIRECTORY_STRUCTURE.validate('asdasdasdasdss'))
        
    def test_config_file(self):
        """If a config file is provided it should be read"""
        import tempfile
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write('[evaluation_system]\n%s=nowhere\n' % config.BASE_DIR)
        
        self.assertEquals(config.get(config.BASE_DIR), 'evaluation_system')
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        config.reloadConfiguration()
        self.assertEquals(config.get(config.BASE_DIR), 'nowhere')

        os.unlink(name)

        #check wrong section        
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write('[wrong_section]\n%s=nowhere\n' % config.BASE_DIR)
        
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        self.failUnlessRaises(ConfigurationException, reloadConfiguration)

        os.unlink(name)
        
        #check directory structure value        
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write('[evaluation_system]\n%s=wrong_value\n' % config.DIRECTORY_STRUCTURE_TYPE)
        
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        self.failUnlessRaises(ConfigurationException, reloadConfiguration)

        os.unlink(name)
        
        #check $EVALUATION_SYSTEM_HOME get's resolved properly        
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write('[evaluation_system]\n%s=$EVALUATION_SYSTEM_HOME\n' % config.BASE_DIR)
        
        self.assertEquals(config.get(config.BASE_DIR), 'evaluation_system')
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        config.reloadConfiguration()
        self.assertEquals(config.get(config.BASE_DIR),
                          '/'.join(__file__.split('/')[:-4]))

        os.unlink(name)

    def test_plugin_conf(self):
        import tempfile
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write("""
[evaluation_system]
base_dir=~

[plugin:pca]
plugin_path=$EVALUATION_SYSTEM_HOME/tool/pca
python_path=$EVALUATION_SYSTEM_HOME/tool/pca/integration
module=pca.api

[plugin:climval]
plugin_path=$EVALUATION_SYSTEM_HOME/tool/climval
python_path=$EVALUATION_SYSTEM_HOME/tool/climval/src
module=climval.tool

""")
        
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        config.reloadConfiguration()
        plugins_dict = config.get(config.PLUGINS)
        self.assertEquals(set(plugins_dict), set(['pca', 'climval']))
        es_home = '/'.join(__file__.split('/')[:-4])
        self.assertEquals(config.get_plugin('pca',config.PLUGIN_PATH),
                          es_home + '/tool/pca')
        self.assertEquals(config.get_plugin('pca', config.PLUGIN_PYTHON_PATH),
                          es_home + '/tool/pca/integration')
        self.assertEquals(config.get_plugin('pca', config.PLUGIN_MODULE),
                          'pca.api')
        self.assertEquals(config.get_plugin('pca', 'not_existing', 'some_default'),
                          'some_default')
        
        self.assertEquals(config.get_plugin('climval', config.PLUGIN_MODULE),
                          'climval.tool')
        os.unlink(name)

    def test_get_section(self):
        import tempfile
        fd, name = tempfile.mkstemp(__name__, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write("""
[evaluation_system]
base_dir=/home/lala

[some_other_section]
param=value
some=val

""")
        os.environ[config._DEFAULT_ENV_CONFIG_FILE] = name
        config.reloadConfiguration()
        eval = config.get_section('evaluation_system')
        self.assertEqual(eval, {'base_dir': '/home/lala'})
        other = config.get_section('some_other_section')
        self.assertEqual(other, {'param': 'value', 'some': 'val'})
        
        # no valid section
        #config.get_section('safasfas')
        self.assertRaises(config.NoSectionError, config.get_section, 'novalid_section')

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testPlugin']
    unittest.main()