'''
Created on 23.11.2012

@author: estani
'''
import unittest
import os
import tempfile
import shutil
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

from evaluation_system.api.plugin import ConfigurationError
import evaluation_system.api.plugin_manager as pm
from evaluation_system.tests.mocks import DummyPlugin, DummyUser

        
class Test(unittest.TestCase):
    
    def setUp(self):
        pm.reloadPulgins()
    

    def testModules(self):
        pmod = pm.__plugin_modules__
        self.assertTrue(pmod is not None)
        self.assertTrue(len(pmod)>0)

    def testPlugins(self):
        #force reload to be sure the dummy is loaded
        self.assertTrue(len(pm.getPlugins())> 0)
        self.assertTrue('dummyplugin' in pm.getPlugins())
        dummy = pm.getPluginDict('dummyplugin')
        self.assertEqual(dummy['description'], DummyPlugin.__short_description__)
        self.assertEqual(dummy['version'], DummyPlugin.__version__)
        self.assertEqual(dummy['plugin_class'], DummyPlugin)
        
    def testDefaultPluginConfigStorage(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        self.assertTrue(os.path.isdir(home))
        conf_file = pm.writeSetup('dummyplugin', user=user)
        
        print conf_file
        self.assertTrue(os.path.isfile(conf_file))
        with open(conf_file, 'r')as f:
            print f.read()
        
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)
            
    def testPluginConfigStorage(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        self.assertTrue(os.path.isdir(home))
        
        res = pm.getPluginInstance('dummyplugin').setupConfiguration(config_dict=dict(the_number=42))
        self.assertEquals(res['something'], 'test')
        
        #write down this default
        conf_file = pm.writeSetup('dummyplugin', config_dict=dict(the_number=42),user=user)
        
        print conf_file
        self.assertTrue(os.path.isfile(conf_file))
        with open(conf_file, 'r') as f:
            config = f.read()
        self.assertTrue('\nsomething=test\n' in config)
        
        res = pm.parseArguments('dummyplugin', [])
        self.assertEquals(res, {})
        res = pm.parseArguments('dummyplugin', [], user=user)
        self.assertEquals(res, {})        
        res = pm.parseArguments('dummyplugin', [], use_user_defaults=True, user=user)
        self.assertNotEquals(res, {})
        self.assertEquals(res['something'], 'test')
        
        #now change the stored configuration
        config = config.replace('\nsomething=test\n', '\nsomething=super_test\n')
        with open(conf_file, 'w') as f:
            f.write(config)
        res = pm.parseArguments('dummyplugin', [], use_user_defaults=True, user=user)
        self.assertEquals(res['something'], 'super_test')

        
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)
            
    def testParseArguments(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        self.assertTrue(os.path.isdir(home))
        
        #direct parsing
        for args, result in [("number=4", dict(number=4))]:
            d = pm.parseArguments('Dummyplugin', args.split(), user=user)        
            self.assertEquals(d, result)

        #parsing requesting user default but without any
        for args, result in [("number=4", dict(number=4))]:
            d = pm.parseArguments('Dummyplugin', args.split(), use_user_defaults=True, user=user)        
            self.assertEquals(d, result)
            
        pm.writeSetup('DummyPlugin', dict(number=7,the_number=42), user)
        for args, result in [("number=4", dict(number=4, the_number=42,something='test', other=1.4))]:
            d = pm.parseArguments('Dummyplugin', args.split(), use_user_defaults=True, user=user)        
            self.assertEquals(d, result)
        
        
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)
        
    def testWriteSetup(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        f = pm.writeSetup('DummyPlugin', dict(number="$the_number",the_number=42), user)
        
        with open(f) as fp:
            num_line =  [line for line in fp.read().splitlines() if line.startswith('number')][0]
            self.assertEqual(num_line, 'number=$the_number')
        
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)

        
    def testRun(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        
        #no confg
        self.failUnlessRaises(ConfigurationError, pm.runTool,'dummyplugin', user=user)
        self.assertTrue(len(DummyPlugin._runs) == 0)
        
        #direct config
        pm.runTool('dummyplugin', user=user, config_dict=dict(the_number=42))
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs.pop()
        self.assertTrue('the_number' in run)
        self.assertTrue(run['the_number'] == 42)
        DummyPlugin._runs = []
        
        #config stored on disk
        cf = pm.writeSetup('DummyPlugin', dict(the_number=777), user)
        self.assertTrue(os.path.isfile(cf))
        pm.runTool('dummyplugin', user=user)
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs.pop()
        self.assertTrue('the_number' in run)
        self.assertTrue(run['the_number'] == 777)
        DummyPlugin._runs = []

        #check the run was stored
        res =  user.getUserDB().getHistory()
        self.assertEqual(len(res), 2)
        #last call should be first returned
        self.assertEqual(res[0].configuration, run)
        
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)
            
    def testGetHistory(self):
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        
        pm.writeSetup('DummyPlugin', dict(the_number=777), user)
        pm.runTool('dummyplugin', user=user)
        DummyPlugin._runs.pop()
        
        res = pm.getHistory(user=user)
        self.assertEqual(len(res), 1)
        res = res[0]
        import re
        mo = re.search('^([0-9]{1,})[)] ([^ ]{1,}) ([^ ]{1,}) ([^ ]{1,})', res.__str__(compact=False))
        self.assertTrue(mo is not None)
        g1 = mo.groups()
        self.assertTrue(all([g is not None for g in g1]))
        mo = re.search('^([0-9]{1,})[)] ([^ ]{1,}) ([^ ]{1,})', res.__str__())
        g2 = mo.groups()
        self.assertTrue(all([g is not None for g in g2]))
        self.assertEqual(g1[0], g2[0])
        self.assertEqual(g1[1], g2[1])
        self.assertEqual(g1[3], g2[2])
        
        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)
            
    def testDynamicPluginLoading(self):
        basic_plugin = """
from sys import modules
plugin = modules['evaluation_system.api.plugin']

class %s(plugin.PluginAbstract):
    __short_description__ = "Test"
    __version__ = (0,0,1)
    __config_metadict__ =  plugin.metadict(compact_creation=True,                          
                                    output=("/tmp/file", dict(help='output')),
                                    input=(None, dict(type=str, mandatory=True, help="some input")))

    def runTool(self, config_dict=None):
        print "%s", config_dict"""
        path1 = tempfile.mktemp('dyn_plugin')
        
        os.makedirs(os.path.join(path1,'a/b'))
        with open(path1 + '/a/__init__.py', 'w'): pass
        with open(path1 + '/a/b/__init__.py', 'w'): pass
        with open(path1 + '/a/b/blah.py', 'w') as f:
            f.write(basic_plugin % tuple(['TestPlugin1']*2))

        path2 = tempfile.mktemp('dyn_plugin')
        
        os.makedirs(os.path.join(path2,'x/y/z'))
        with open(path2 + '/x/__init__.py', 'w'): pass
        with open(path2 + '/x/y/__init__.py', 'w'): pass
        with open(path2 + '/x/y/z/__init__.py', 'w'): pass
        with open(path2 + '/x/y/z/foo.py', 'w') as f:
            f.write(basic_plugin % tuple(['TestPlugin2']*2))
        
        os.environ[pm.PLUGIN_ENV] = '%s,%s:%s,%s' % \
            ('~/../../../../../..' + path1, 'a.b.blah', #test a relative path starting from ~
             '$HOME/../../../../../..' + path2, 'x.y.z.foo') #test a relative path starting from $HOME
        print os.environ[pm.PLUGIN_ENV]
        log.debug('pre-loading: %s', list(pm.getPlugins()))
        
        self.assertTrue('testplugin1' not in list(pm.getPlugins()))
        self.assertTrue('testplugin2' not in list(pm.getPlugins()))
        pm.reloadPulgins()
        log.debug('post-loading: %s', list(pm.getPlugins()))
        self.assertTrue('testplugin1' in list(pm.getPlugins()))
        self.assertTrue('testplugin2' in list(pm.getPlugins()))
        
        if os.path.isdir(path1) and path1.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            log.debug("Cleaning up %s", path1)
            shutil.rmtree(path1)
            
        if os.path.isdir(path2) and path2.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            log.debug("Cleaning up %s", path2)
            shutil.rmtree(path2)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()