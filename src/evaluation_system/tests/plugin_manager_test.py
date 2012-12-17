'''
Created on 23.11.2012

@author: estani
'''
import unittest
import os
import tempfile
import evaluation_system.api.plugin_manager as pm
from evaluation_system.tests.mocks import DummyPlugin, DummyUser

import shutil
import logging
from evaluation_system.api.plugin import ConfigurationError
logging.basicConfig(level=logging.DEBUG)

        
class Test(unittest.TestCase):
    
    def setUp(self):
        pm.reloadPulgins()
    

    def testModules(self):
        pmod = pm.getPulginModules()
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
        conf_file = pm.writeSetup('dummyplugin', config_dict=dict(the_number=42),user=user)
        
        print conf_file
        self.assertTrue(os.path.isfile(conf_file))
        with open(conf_file, 'r')as f:
            print f.read()
            
        #conf_file = pm.readSetup('dummyplugin', config_dict=dict(number=1234),user=user)
        
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
        
        cf = pm.writeSetup('DummyPlugin', dict(the_number=777), user)
        pm.runTool('dummyplugin', user=user)
        run = DummyPlugin._runs.pop()
        
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

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()