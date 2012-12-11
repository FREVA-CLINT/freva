'''
Created on 23.11.2012

@author: estani
'''
import unittest
import os
import tempfile
import evaluation_system.api.plugin_manager as pm
from evaluation_system.api.plugin import PluginAbstract, metadict
from evaluation_system.model.user import User
import shutil
import logging
logging.basicConfig(level=logging.DEBUG)

class DummyPlugin(PluginAbstract):
    """Stub class for implementing the abstrac one"""
    __short_description__ = None
    __version__ = (0,0,0)
    __config_metadict__ =  metadict(compact_creation=True, 
                                    number=(None, dict(type=int,help='This is just a number, not really important')),
                                    the_number=(None, dict(type=int,mandatory=True,help='This is *THE* number. Please provide it')), 
                                    something='test', other=1.4)
    _runs = []
    _template = "${number} - $something - $other"
    def runTool(self, config_dict=None):
        DummyPlugin._runs.append(config_dict)
        print "Dummy tool was run with: %s" % config_dict
        

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
    

    def testModules(self):
        pmod = pm.getPulginModules()
        self.assertTrue(pmod is not None)
        self.assertTrue(len(pmod)>0)

    def testPlugins(self):
        #force reload to be sure the dummy is loaded
        pm.reloadPulgins()
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
        pm.reloadPulgins()
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
        pm.reloadPulgins()
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
        pm.reloadPulgins()
        
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
        pm.reloadPulgins()
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
        pm.reloadPulgins()
        user = DummyUser(random_home=True, pw_name='test_user')
        home = user.getUserHome()
        
        #no confg
        pm.runTool('dummyplugin', user=user)
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs[0]
        self.assertTrue('the_number' in run)
        self.assertTrue(run['the_number'] is None)
        DummyPlugin._runs = []
        
        #direct config
        pm.runTool('dummyplugin', user=user, config_dict=dict(the_number=42))
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs[0]
        self.assertTrue('the_number' in run)
        self.assertTrue(run['the_number'] == 42)
        DummyPlugin._runs = []
        
        #config stored on disk
        cf = pm.writeSetup('DummyPlugin', dict(the_number=777), user)
        self.assertTrue(os.path.isfile(cf))
        print cf
        pm.runTool('dummyplugin', user=user)
        self.assertTrue(len(DummyPlugin._runs) == 1)
        run = DummyPlugin._runs[0]
        self.assertTrue('the_number' in run)
        self.assertTrue(run['the_number'] == 777)
        DummyPlugin._runs = []

        if os.path.isdir(home) and home.startswith(tempfile.gettempdir()):
            #make sure the home is a temporary one!!!
            print "Cleaning up %s" % home
            shutil.rmtree(home)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()